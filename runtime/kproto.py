# MIT License
#
# Copyright (c) 2026 Korean Protocol contributors
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""Content-only installer; uses Python stdlib and optional OpenSSH verification.

Run ``python3 -m runtime.kproto --help``. No code is downloaded or executed.
"""
import argparse
import base64
from contextlib import contextmanager, nullcontext
from datetime import datetime, timedelta, timezone
import hashlib
import http.client
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import stat
import subprocess
import sys
import time
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import uuid

if os.name == 'posix':
    import fcntl

ENGINE_VERSION = '0.1.0'
MAX_PROFILE_BYTES = 28 * 1024
MAX_MANAGED_BYTES = 30 * 1024
MAX_FILE_BYTES = 1024 * 1024
MAX_DOWNLOAD_REQUEST_BYTES = 64 * 1024
MAX_TOTAL_BYTES = 4 * 1024 * 1024
MAX_JOURNAL_BYTES = ((MAX_TOTAL_BYTES + 2) // 3) * 4 + 128 * 1024
CONTENT_PATHS = (
    'profiles/coding-agent.md', 'profiles/chat.md', 'profiles/work-document.md',
    'specification/rules.json', 'lexicon/core.json',
    'lexicon/domains/software.json', 'pack/protocol.md',
)
BEGIN = b'<!-- korean-protocol:begin id=kproto -->'
END = b'<!-- korean-protocol:end id=kproto -->'


class ProtocolError(Exception):
    code = 2


class InputError(ProtocolError):
    pass


class NetworkError(ProtocolError):
    code = 3


class MissingError(ProtocolError):
    code = 4


class TrustError(ProtocolError):
    code = 5


class CompatibilityError(ProtocolError):
    code = 6


class ConflictError(ProtocolError):
    code = 7


class WriteError(ProtocolError):
    code = 8


def digest(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')


def strict_json(data):
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise InputError('JSON has duplicate keys')
            value[key] = item
        return value

    def constant(_):
        raise InputError('JSON has a non-finite number')

    try:
        return json.loads(data.decode('utf-8'), object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, UnicodeError, RecursionError):
        raise InputError('Invalid UTF-8 JSON') from None


def version_tuple(value):
    if not isinstance(value, str) or len(value) > 32 or not re.fullmatch(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)', value):
        raise InputError('Version must be MAJOR.MINOR.PATCH')
    return tuple(int(n) for n in value.split('.'))


def safe_path(path):
    """Reject links before opening. Paths supplied by callers are explicit roots."""
    path = Path(path).absolute()
    for item in reversed((path,) + tuple(path.parents)):
        try:
            info = item.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise InputError('Symbolic links and reparse points are not supported')
        if item == path and stat.S_ISREG(info.st_mode) and info.st_nlink != 1:
            raise InputError('Hardlinked files are not supported')
        if item != path and not stat.S_ISDIR(info.st_mode):
            raise InputError('Parent path is not a directory')
    return path


def read_bytes(path, maximum=MAX_FILE_BYTES):
    path = safe_path(path)
    try:
        parent_fd = open_directory(path.parent)
        try:
            fd = os.open(path.name, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0), dir_fd=parent_fd)
        finally:
            os.close(parent_fd)
    except FileNotFoundError:
        raise MissingError('Required local file is missing') from None
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > maximum:
            raise InputError('Local file is not a bounded regular file')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            data = stream.read(maximum + 1)
        if len(data) > maximum:
            raise InputError('File exceeds size limit')
        return data
    finally:
        os.close(fd)


def open_directory(path):
    """Walk components through descriptors so a parent symlink cannot redirect I/O."""
    path = Path(path).absolute()
    if os.name != 'posix':
        raise CompatibilityError('Descriptor-based path protection requires POSIX')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parts[1:]:
            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        return fd
    except BaseException:
        os.close(fd)
        raise


def atomic_write(path, data, expected=None):
    """Replace within an opened parent directory; do not follow final links."""
    path = safe_path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    safe_path(path.parent)
    if os.name != 'posix':
        raise CompatibilityError('Atomic installer currently supports POSIX only')
    parent_fd = open_directory(path.parent)
    temp_name = '.kproto-' + uuid.uuid4().hex
    temp_created = False
    try:
        parent_info = os.fstat(parent_fd)
        original_info = path.lstat() if path.exists() else None
        mode = stat.S_IMODE(original_info.st_mode) if original_info else 0o600
        fd = os.open(temp_name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), mode, dir_fd=parent_fd)
        temp_created = True
        try:
            with os.fdopen(fd, 'wb', closefd=False) as stream:
                stream.write(data)
                stream.flush()
                os.fsync(fd)
            os.fchmod(fd, mode)
        finally:
            os.close(fd)
        safe_path(path)
        current_parent = path.parent.stat()
        if (current_parent.st_dev, current_parent.st_ino) != (parent_info.st_dev, parent_info.st_ino):
            raise ConflictError('Target parent changed during write')
        if expected is not None:
            actual = read_bytes(path, MAX_TOTAL_BYTES) if path.exists() else b''
            if actual != expected:
                raise ConflictError('Target changed during write')
        current_info = path.lstat() if path.exists() else None
        if original_info is not None and (current_info is None or (current_info.st_dev, current_info.st_ino) != (original_info.st_dev, original_info.st_ino)):
            raise ConflictError('Target identity changed during write')
        os.replace(temp_name, path.name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
        temp_created = False
        os.fsync(parent_fd)
    finally:
        if temp_created:
            os.unlink(temp_name, dir_fd=parent_fd)
        os.close(parent_fd)


def key_fingerprint(public_key):
    data = read_bytes(public_key, 16384).decode('ascii').strip().split()
    if len(data) < 2 or data[0] != 'ssh-ed25519':
        raise InputError('Trust key must be an Ed25519 public key')
    try:
        raw = base64.b64decode(data[1], validate=True)
    except ValueError:
        raise InputError('Invalid public key encoding') from None
    if len(raw) != 51 or raw[:19] != b'\x00\x00\x00\x0bssh-ed25519\x00\x00\x00 ':
        raise InputError('Invalid Ed25519 public key')
    return 'SHA256:' + base64.b64encode(hashlib.sha256(raw).digest()).decode().rstrip('=')


def launchctl(*arguments):
    """Never interpolate shell input or expose launchctl's diagnostic output."""
    try:
        return subprocess.run(['/bin/launchctl', *arguments], capture_output=True,
                              text=True, timeout=15, check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise WriteError('launchctl is unavailable or exceeded its time limit') from None


def scheduler_probe(record):
    """Read live state; an unrecognized print layout never authorizes removal.

    launchctl documents print as an unstable diagnostic format. Only its exit
    status establishes presence; path/program/arguments checks fail closed.
    """
    domain = 'gui/' + str(os.getuid())
    if (not isinstance(record, dict) or not re.fullmatch(r'com\.korean-protocol\.update\.[0-9a-f]{12}', str(record.get('label', ''))) or
            not isinstance(record.get('path'), str) or not isinstance(record.get('arguments'), list) or
            not record['arguments'] or any(not isinstance(arg, str) for arg in record['arguments'])):
        return {'registered': None, 'live_owned': False, 'error': 'Invalid scheduler ownership record'}
    try:
        result = launchctl('print', domain + '/' + record['label'])
        if result.returncode == 113 and launchctl('print', domain).returncode == 0:
            return {'registered': False, 'live_owned': False}
        if result.returncode != 0:
            return {'registered': None, 'live_owned': False, 'error': 'Unable to query GUI launchd service'}
        paths = re.findall(r'^\tpath = (.+)$', result.stdout, re.MULTILINE)
        programs = re.findall(r'^\tprogram = (.+)$', result.stdout, re.MULTILINE)
        blocks = re.findall(r'^\targuments = \{\n(.*?)^\t\}', result.stdout, re.MULTILINE | re.DOTALL)
        arguments = [line.strip() for line in blocks[0].splitlines()] if len(blocks) == 1 else []
        owned = (paths == [record['path']] and programs == [record['arguments'][0]] and
                 arguments == record['arguments'])
        return {'registered': True, 'live_owned': owned}
    except ProtocolError:
        return {'registered': None, 'live_owned': False, 'error': 'Unable to query GUI launchd service'}


def scheduler_status(config, state_dir):
    scheduler = dict(config.get('scheduler', {'status': 'disabled', 'registered': False}))
    record = scheduler.get('launch_agent')
    if record:
        scheduler.update(scheduler_probe(record))
        try:
            path = safe_path(record['path'])
            info = path.stat()
            label = 'com.korean-protocol.update.' + digest(str(state_dir).encode())[:12]
            data = read_bytes(path)
            job = plistlib.loads(data)
            scheduler['persisted'] = (path == safe_path(Path.home()/'Library/LaunchAgents'/(label+'.plist')) and
                                      record['label'] == label and info.st_uid == os.getuid() and
                                      not stat.S_IMODE(info.st_mode) & 0o022 and digest(data) == record['hash'] and
                                      isinstance(job, dict) and job.get('Label') == label and job.get('ProgramArguments') == record['arguments'])
        except (ProtocolError, OSError, KeyError, TypeError, ValueError, plistlib.InvalidFileException):
            scheduler['persisted'] = False
        scheduler['status'] = ('unknown' if scheduler['registered'] is None else
                               'registered' if scheduler['registered'] and scheduler['live_owned'] and scheduler['persisted'] else
                               'conflict' if scheduler['registered'] else 'unloaded')
    return scheduler


def remove_owned_file(path, expected):
    """Remove only the previously checked single-link regular file."""
    path = safe_path(path)
    if read_bytes(path) != expected:
        raise ConflictError('Owned file changed before removal; file preserved')
    info = path.stat()
    parent_fd = open_directory(path.parent)
    try:
        current = os.stat(path.name, dir_fd=parent_fd, follow_symlinks=False)
        if (info.st_dev, info.st_ino) != (current.st_dev, current.st_ino):
            raise ConflictError('Owned file identity changed; file preserved')
        os.unlink(path.name, dir_fd=parent_fd)
        os.fsync(parent_fd)
    finally:
        os.close(parent_fd)


def content_files(bundle):
    bundle = safe_path(bundle)
    files = {}
    total = 0
    for name in CONTENT_PATHS:
        data = read_bytes(bundle / name)
        if not data:
            raise InputError('Content file is empty')
        if name.startswith('profiles/') and len(data) > MAX_PROFILE_BYTES:
            raise InputError('Profile exceeds 28 KiB budget')
        try:
            data.decode('utf-8')
        except UnicodeError:
            raise InputError('Content must use UTF-8') from None
        if name.endswith('.json'):
            document=strict_json(data)
            array_name='rules' if name.startswith('specification/') else 'entries'
            if not isinstance(document,dict):
                raise InputError('Content JSON must be a top-level object')
            if document.get('schema_version')!='1.0':
                raise CompatibilityError('Content JSON schema version is incompatible')
            if not isinstance(document.get('version'),str) or not document['version']:
                raise InputError('Content JSON needs a version')
            array=document.get(array_name)
            if not isinstance(array,list) or not array or any(not isinstance(item,dict) for item in array):
                raise InputError('Content JSON needs a nonempty object array')
        files[name] = data
        total += len(data)
    if total > MAX_TOTAL_BYTES:
        raise InputError('Content exceeds total size budget')
    return files


def make_manifest(bundle, version, sequence, fingerprint):
    """Build bytes metadata only. Signing is a separate publisher operation."""
    version_tuple(version)
    files = content_files(bundle)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    return {
        'schema_version': 1, 'version': version, 'channel': 'stable', 'sequence': sequence,
        'issued_at': now.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'expires_at': (now + timedelta(days=30)).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'compatibility': {'engine_min': ENGINE_VERSION, 'engine_max_exclusive': '1.0.0', 'rules_schema_version': 1, 'lexicon_schema_version': 1},
        'signing': {'format': 'openssh-sshsig', 'key_id': fingerprint, 'namespace': 'kproto-release-v1', 'principal': 'kproto-release'},
        'files': [{'path': name, 'role': 'profile' if name.startswith('profiles/') else 'rules' if name.startswith('specification/') else 'lexicon' if name.startswith('lexicon/') else 'protocol', 'size': len(data), 'sha256': digest(data)} for name, data in files.items()],
    }


def validate_manifest(value, fresh=True):
    required = {'schema_version','version','channel','sequence','issued_at','expires_at','compatibility','signing','files'}
    if not isinstance(value, dict) or set(value) != required:
        raise InputError('Manifest fields are invalid')
    if type(value['schema_version']) is not int or value['schema_version'] != 1:
        raise CompatibilityError('Unsupported manifest schema')
    version_tuple(value['version'])
    if value['channel'] != 'stable' or type(value['sequence']) is not int or not 1 <= value['sequence'] <= 9007199254740991:
        raise InputError('Invalid channel or release sequence')
    try:
        for field in ['issued_at','expires_at']:
            if not isinstance(value[field],str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z',value[field]):
                raise ValueError()
        issued = datetime.strptime(value['issued_at'],'%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
        expires = datetime.strptime(value['expires_at'],'%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
    except (ValueError,TypeError):
        raise InputError('Invalid release dates') from None
    if issued >= expires:
        raise InputError('Release expiration must follow issue time')
    if fresh and (issued > datetime.now(timezone.utc) or expires <= datetime.now(timezone.utc)):
        raise TrustError('Release is expired or future-issued')
    compat = value['compatibility']
    if not isinstance(compat,dict) or set(compat) - {'engine_min','engine_max_exclusive','rules_schema_version','lexicon_schema_version','hosts'} or not {'engine_min','engine_max_exclusive','rules_schema_version','lexicon_schema_version'} <= set(compat):
        raise InputError('Invalid compatibility fields')
    low, high = version_tuple(compat['engine_min']), version_tuple(compat['engine_max_exclusive'])
    if low >= high:
        raise InputError('Invalid engine version range')
    if not low <= version_tuple(ENGINE_VERSION) < high or type(compat['rules_schema_version']) is not int or compat['rules_schema_version'] != 1 or type(compat['lexicon_schema_version']) is not int or compat['lexicon_schema_version'] != 1:
        raise CompatibilityError('Content is incompatible with this engine')
    if compat.get('hosts'):
        # Host range detection is not implemented; fail closed rather than guessing.
        raise CompatibilityError('Host-specific ranges require a verified host adapter')
    signing = value['signing']
    if not isinstance(signing,dict) or set(signing) != {'format','key_id','namespace','principal'} or signing['format'] != 'openssh-sshsig' or signing['namespace'] != 'kproto-release-v1' or signing['principal'] != 'kproto-release' or not isinstance(signing['key_id'],str) or not re.fullmatch(r'SHA256:[A-Za-z0-9+/]{43}',signing['key_id']):
        raise InputError('Invalid manifest signing metadata')
    entries = value['files']
    if not isinstance(entries,list) or len(entries) != len(CONTENT_PATHS):
        raise InputError('Manifest must list all seven content files')
    seen, total = set(), 0
    for item in entries:
        if not isinstance(item,dict) or set(item) != {'path','role','size','sha256'}:
            raise InputError('Invalid content metadata')
        name = item['path']
        if not isinstance(name,str) or name not in CONTENT_PATHS or name in seen:
            raise InputError('Content path is not uniquely allowlisted')
        role = 'profile' if name.startswith('profiles/') else 'rules' if name.startswith('specification/') else 'lexicon' if name.startswith('lexicon/') else 'protocol'
        if item['role'] != role or type(item['size']) is not int or not 1 <= item['size'] <= MAX_FILE_BYTES or not isinstance(item['sha256'],str) or not re.fullmatch('[a-f0-9]{64}',item['sha256']):
            raise InputError('Invalid content role, size or hash')
        if role == 'profile' and item['size'] > MAX_PROFILE_BYTES:
            raise InputError('Profile exceeds budget')
        total += item['size']
        seen.add(name)
    if total > MAX_TOTAL_BYTES:
        raise InputError('Manifest exceeds total size budget')
    return value


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise NetworkError('Redirects are not allowed')


def validate_source(source):
    try:
        parts = urllib.parse.urlsplit(source)
        if parts.scheme != 'https' or not parts.hostname or parts.username or parts.password or parts.query or parts.fragment or parts.port not in (None,443):
            raise ValueError()
    except (ValueError,TypeError):
        raise InputError('Source must be credential-free HTTPS on port 443') from None
    return source.rstrip('/')


def download_worker(url,headers,maximum):
    """Return only a status byte and a bounded body, never exception text."""
    try:
        opener=urllib.request.build_opener(NoRedirect())
        with opener.open(urllib.request.Request(url,headers=headers),timeout=15) as response:
            data=response.read(maximum+1)
        return b'\x01'+data if len(data)<=maximum else b'\x00'
    except Exception:
        # Even malformed HTTP response exceptions can contain credentials/body text.
        return b'\x00'


def download_worker_main():
    """Read credentials from a bounded private pipe in a fresh interpreter."""
    result=b'\x00'
    try:
        raw=sys.stdin.buffer.read(MAX_DOWNLOAD_REQUEST_BYTES+1)
        if len(raw)>MAX_DOWNLOAD_REQUEST_BYTES:
            raise InputError('Download request exceeds size limit')
        request=strict_json(raw)
        if not isinstance(request,dict) or set(request)!={'url','headers','maximum'}:
            raise InputError('Invalid download request')
        maximum=request['maximum']
        if type(maximum) is not int or not 0<=maximum<=MAX_FILE_BYTES:
            raise InputError('Invalid download limit')
        if not isinstance(request['url'],str) or not isinstance(request['headers'],dict) or any(not isinstance(k,str) or not isinstance(v,str) for k,v in request['headers'].items()):
            raise InputError('Invalid download request')
        result=download_worker(request['url'],request['headers'],maximum)
    except Exception:
        pass
    sys.stdout.buffer.write(result)
    sys.stdout.buffer.flush()
    return 0


def application_settings(state):
    enabled = state.get('protocol_enabled', True)
    honorifics = state.get('honorifics', False)
    if type(enabled) is not bool or type(honorifics) is not bool:
        raise InputError('Application settings must be booleans')
    return enabled, honorifics


def speech_overlay(honorifics):
    level = ('새 설명·보고 문장의 종결형만 존댓말(~습니다/~ㅂ니다)로 맞춘다. 행위자와 뜻을 바꾸지 않는다.'
             if honorifics else
             '새 설명·보고 문장의 종결형만 ~다/~한다로 맞춘다. 뜻을 유지하며 불필요한 주체 높임을 줄인다.')
    return ('말투(프로필보다 우선):\n- ' + level + '\n'
            "- 짧은 상태 표시('표기된 담당자 없음.')는 유지한다. 종결형을 맞추려고 문장을 늘리지 않는다.\n"
            '- 절차 주체를 분명히 쓴다. 행위자를 지어내거나 모델 자신의 실행 계획으로 바꾸지 않는다.\n'
            '- 뜻·행위자·조건·발화 기능을 보존한다. 허락·요청·제안·질문을 명령이나 단정으로 바꾸지 않는다.\n'
            '- 인용·코드·식별자·기존 문체는 보존한다. 사용자 지정 말투·장르를 우선한다.\n').encode()


class Controller:
    def __init__(self, state_dir):
        self.root = safe_path(state_dir)
        if os.name != 'posix':
            raise CompatibilityError('Installer writes currently support POSIX only')
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        info = self.root.stat()
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o022:
            raise InputError('State directory must be owned by user and not writable by others')
        self.state_path = self.root/'state.json'
        self.config_path = self.root/'config.json'
        self.journal_path = self.root/'journal.json'
        self.scheduler_journal_path = self.root/'scheduler-migration.json'

    def _json(self, path, default):
        return strict_json(read_bytes(path,MAX_TOTAL_BYTES)) if path.exists() else default

    def _state(self):
        return self._json(self.state_path, {})

    def _config(self):
        return self._json(self.config_path, {'mode':'off','interval_hours':24})

    @contextmanager
    def lock(self):
        path = self.root/'write.lock'
        safe_path(path)
        parent_fd = open_directory(path.parent)
        try:
            fd = os.open(path.name,os.O_RDWR|os.O_NONBLOCK|os.O_CREAT|os.O_NOFOLLOW,0o600,dir_fd=parent_fd)
        finally:
            os.close(parent_fd)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o022:
                raise ConflictError('State lock has unsafe ownership or type')
            try:
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:
                raise ConflictError('Another writer owns this state') from None
            os.ftruncate(fd,0)
            os.write(fd,json_bytes({'pid':os.getpid(),'started':time.time()}))
            os.fsync(fd)
            yield
        finally:
            os.close(fd)

    @contextmanager
    def _target_lock(self,target):
        path = target.parent/('.'+target.name+'.kproto-lock')
        safe_path(path)
        parent_fd = open_directory(path.parent)
        try:
            fd=os.open(path.name,os.O_RDWR|os.O_NONBLOCK|os.O_CREAT|os.O_NOFOLLOW,0o600,dir_fd=parent_fd)
        finally:
            os.close(parent_fd)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o022:
                raise ConflictError('Target lock has unsafe ownership or type')
            try:
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:
                raise ConflictError('Another state is writing this target') from None
            yield
        finally:
            os.close(fd)

    def status(self):
        state = self._state()
        result = dict(state)
        result['installed'] = bool(state.get('target'))
        enabled, honorifics = application_settings(state)
        result.update(enabled=result['installed'] and enabled, honorifics=honorifics)
        result['recovery_required'] = self.journal_path.exists() or self.scheduler_journal_path.exists()
        result['autoupdate'] = self._config().get('mode','off')
        result['scheduler'] = scheduler_status(self._config(), self.root)
        return result

    def _agent_path(self):
        label = 'com.korean-protocol.update.' + digest(str(self.root).encode())[:12]
        return safe_path(Path.home()/'Library/LaunchAgents'/(label+'.plist')), label

    def _agent_bytes(self, record):
        path, label = self._agent_path()
        if record.get('path') != str(path) or record.get('label') != label:
            raise ConflictError('Scheduler ownership path or label differs; job preserved')
        if not path.exists():
            return path, None
        info = path.stat()
        data = read_bytes(path)
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o022 or digest(data) != record.get('hash'):
            raise ConflictError('LaunchAgent is unowned or modified; job preserved')
        try:
            job = plistlib.loads(data)
        except (ValueError, plistlib.InvalidFileException):
            raise ConflictError('Invalid owned LaunchAgent; job preserved') from None
        if not isinstance(job, dict) or job.get('Label') != label or job.get('ProgramArguments') != record.get('arguments'):
            raise ConflictError('LaunchAgent identity differs; job preserved')
        return path, data

    def _unregister_scheduler(self, cfg, locked=False):
        record = cfg.get('scheduler', {}).get('launch_agent')
        if not record:
            return
        path, _ = self._agent_bytes(record)
        with nullcontext() if locked else self._target_lock(path):
            path, data = self._agent_bytes(record)
            probe = scheduler_probe(record)
            if probe['registered'] is None:
                raise WriteError('Scheduler status is unknown; job preserved')
            if probe['registered']:
                if data is None or not probe['live_owned']:
                    raise ConflictError('Loaded scheduler identity is not owned; job preserved')
                if self._agent_bytes(record)[1] != data:
                    raise ConflictError('LaunchAgent changed during removal; job preserved')
                result = launchctl('bootout', 'gui/'+str(os.getuid())+'/'+record['label'])
                after = scheduler_probe(record)
                if result.returncode != 0 or after['registered'] is not False:
                    raise WriteError('Scheduler removal was not confirmed; plist preserved for retry')
            if data is not None:
                remove_owned_file(path, data)
            cfg['scheduler'].pop('launch_agent', None)

    def unregister_scheduler(self):
        with self.lock():
            self._recover()
            cfg = self._config()
            self._unregister_scheduler(cfg)
            atomic_write(self.config_path, json_bytes(cfg))
        return self.status()['scheduler']

    def _disable_scheduler(self, cfg):
        scheduler = cfg.get('scheduler', {})
        path = safe_path(scheduler['path']) if scheduler.get('path') else None
        data = read_bytes(path) if path and path.exists() else None
        if data is not None and digest(data) != scheduler.get('hash'):
            raise ConflictError('User modified scheduler output; file preserved')
        self._unregister_scheduler(cfg)
        if data is not None:
            remove_owned_file(path, data)
        cfg['scheduler'] = {'status': 'disabled', 'registered': False}

    def register_scheduler(self):
        with self.lock():
            self._recover()
            self._register_scheduler(self._config())
        return self.status()['scheduler']

    def _register_scheduler(self,cfg):
        if sys.platform != 'darwin':
            raise CompatibilityError('Scheduler registration supports macOS only')
        if cfg.get('mode') != 'scheduled' or self._state().get('trust') != 'signed':
            raise TrustError('Scheduler registration requires a signed installation and scheduled mode')
        validate_source(cfg.get('source', ''))
        if cfg.get('token_env'):
            raise InputError('Scheduler registration cannot persist a private endpoint shell credential')
        runtime = safe_path(__file__)
        if self.root not in runtime.parents or not runtime.is_file():
            raise InputError('Scheduler registration requires the durable runtime inside its state directory')
        runtime_info = runtime.stat()
        if runtime_info.st_uid != os.getuid() or stat.S_IMODE(runtime_info.st_mode) & 0o022:
            raise InputError('Durable runtime has unsafe ownership or permissions')
        for parent in runtime.parents:
            info = parent.stat()
            if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o022:
                raise InputError('Durable runtime directory has unsafe ownership or permissions')
            if parent == self.root:
                break
        path, label = self._agent_path()
        args = [str(Path(sys.executable).resolve()), str(runtime), '--state-dir', str(self.root), 'update', '--scheduled']
        if any('\n' in arg or '\r' in arg for arg in [str(path), *args]):
            raise InputError('Scheduler paths cannot contain line breaks')
        job = {'Label': label, 'ProgramArguments': args, 'RunAtLoad': True,
               'StartCalendarInterval': {'Minute': 0}, 'Umask': 0o077,
               'StandardOutPath': str(self.root/'scheduled.stdout.log'),
               'StandardErrorPath': str(self.root/'scheduled.stderr.log')}
        safe_path(job['StandardOutPath'])
        safe_path(job['StandardErrorPath'])
        data = plistlib.dumps(job, sort_keys=True)
        record = {'path': str(path), 'label': label, 'hash': digest(data), 'arguments': args}
        previous = cfg.get('scheduler', {}).get('launch_agent')
        if previous:
            _, previous_data = self._agent_bytes(previous)
            probe = scheduler_probe(previous)
            if previous_data == data and probe['registered'] is True and probe['live_owned']:
                return scheduler_status(cfg, self.root)
            self._unregister_scheduler(cfg)
            atomic_write(self.config_path, json_bytes(cfg))
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        safe_path(path.parent)
        info = path.parent.stat()
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o022:
            raise InputError('LaunchAgents directory has unsafe ownership or permissions')
        with self._target_lock(path):
            if path.exists():
                raise ConflictError('Existing LaunchAgent is not owned; file preserved')
            probe = scheduler_probe(record)
            if probe['registered'] is not False:
                raise ConflictError('Scheduler label is already loaded or its status is unknown; job preserved')
            cfg['scheduler']['launch_agent'] = record
            # Persist ownership before loading: a failed final state write
            # must still leave a safe, explicit removal route.
            atomic_write(self.config_path, json_bytes(cfg))
            try:
                atomic_write(path, data, expected=b'')
                result = launchctl('bootstrap', 'gui/'+str(os.getuid()), str(path))
                probe = scheduler_probe(record)
                if result.returncode != 0 or probe['registered'] is not True or not probe['live_owned']:
                    raise WriteError('Scheduler registration was not confirmed')
            except (ProtocolError, OSError):
                try:
                    self._unregister_scheduler(cfg, locked=True)
                    atomic_write(self.config_path, json_bytes(cfg))
                except (ProtocolError, OSError):
                    raise WriteError('Scheduler registration failed and cleanup is incomplete; use scheduler status/unregister') from None
                raise WriteError('Scheduler registration failed; owned LaunchAgent was removed') from None

    def configure(self,mode=None,source=None,token_env=None,interval_hours=None,emit=None):
        with self.lock():
            self._recover()
            cfg=self._config()
            if mode is not None:
                if mode not in ('off','interval','scheduled'):
                    raise CompatibilityError('Unsupported auto update mode')
                cfg['mode']=mode
            if source is not None:
                cfg['source']=validate_source(source)
            if token_env is not None:
                if not re.fullmatch('[A-Za-z_][A-Za-z0-9_]*',token_env):
                    raise InputError('Invalid token environment variable name')
                cfg['token_env']=token_env
            if interval_hours is not None:
                if not 1 <= interval_hours <= 168:
                    raise InputError('Interval must be 1 through 168 hours')
                cfg['interval_hours']=interval_hours
            if mode == 'scheduled':
                if sys.platform != 'darwin':
                    raise CompatibilityError('Scheduler generation currently supports macOS only')
                scheduler=cfg.get('scheduler',{})
                path=safe_path(emit or self.root/'autoupdate.plist')
                previous_data = read_bytes(path) if path.exists() else b''
                if path.exists() and (scheduler.get('path')!=str(path) or digest(previous_data)!=scheduler.get('hash')):
                    raise ConflictError('Existing scheduler output is not owned or was modified')
                label='com.korean-protocol.update.'+digest(str(self.root).encode())[:12]
                args=[str(Path(sys.executable).resolve()),str(Path(__file__).resolve()),'--state-dir',str(self.root),'update','--scheduled']
                job={'Label':label,'ProgramArguments':args,'RunAtLoad':True,'StartInterval':3600*cfg.get('interval_hours',24),'StandardOutPath':str(self.root/'scheduled.stdout.log'),'StandardErrorPath':str(self.root/'scheduled.stderr.log')}
                data=plistlib.dumps(job,sort_keys=True)
                atomic_write(path,data,expected=previous_data)
                cfg['scheduler']={'status':'generated','registered':False,'path':str(path),'label':label,'hash':digest(data),
                                  **({'launch_agent': scheduler['launch_agent']} if scheduler.get('launch_agent') else {})}
            elif mode in ('off','interval'):
                self._disable_scheduler(cfg)
            atomic_write(self.config_path,json_bytes(cfg))
            return cfg

    def pin(self,version):
        with self.lock():
            self._recover()
            state=self._state()
            if not state:
                raise MissingError('No installed protocol')
            if version is not None:
                version_tuple(version)
                if version != state['version']:
                    raise InputError('Pin current version or rollback to a cached version first')
            state['pin']=version
            atomic_write(self.state_path,json_bytes(state))

    def trust_key(self,public_key,expected_fingerprint):
        fingerprint=key_fingerprint(public_key)
        if fingerprint != expected_fingerprint:
            raise TrustError('Public key fingerprint differs from expected trust anchor')
        fields=read_bytes(public_key,16384).decode('ascii').strip().split()
        with self.lock():
            self._recover()
            folder=self.root/'trust'
            folder.mkdir(exist_ok=True,mode=0o700)
            atomic_write(folder/'public_key',(fields[0]+' '+fields[1]+'\n').encode())
            atomic_write(folder/'allowed_signers',('kproto-release namespaces="kproto-release-v1" '+fields[0]+' '+fields[1]+'\n').encode())
        return fingerprint

    def _verify_signature(self,bundle,raw,manifest):
        public=self.root/'trust/public_key'
        allowed=self.root/'trust/allowed_signers'
        if not public.exists() or not allowed.exists():
            raise TrustError('A separately verified local trust key is required')
        if key_fingerprint(public) != manifest['signing']['key_id']:
            raise TrustError('Manifest signer does not match local trust anchor')
        for path in (public,allowed):
            info=safe_path(path).stat()
            if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode)&0o022:
                raise TrustError('Trust file ownership or permissions are unsafe')
        verifier=shutil.which('ssh-keygen')
        if not verifier:
            raise TrustError('OpenSSH signature verifier is unavailable')
        verifier=str(Path(verifier).resolve())
        signature=bundle/'release.json.sig'
        read_bytes(signature,16384)
        env={key:value for key,value in os.environ.items() if key in ('LANG','LC_ALL','SYSTEMROOT')}
        try:
            checked=subprocess.run([verifier,'-Y','verify','-f',str(allowed),'-I','kproto-release','-n','kproto-release-v1','-s',str(signature)],input=raw,capture_output=True,timeout=10,env=env)
        except (OSError,subprocess.SubprocessError):
            raise TrustError('OpenSSH signature verification failed') from None
        if checked.returncode:
            raise TrustError('Content publisher signature is invalid')

    def _load_signed(self,bundle,fresh=True):
        bundle=safe_path(bundle)
        raw=read_bytes(bundle/'release.json',65536)
        manifest=validate_manifest(strict_json(raw),fresh=fresh)
        self._verify_signature(bundle,raw,manifest)
        files=content_files(bundle)
        for entry in manifest['files']:
            data=files[entry['path']]
            if len(data) != entry['size'] or digest(data) != entry['sha256']:
                raise TrustError('Content hash or size differs from authenticated manifest')
        return manifest,raw,files

    def install_snapshot(self,bundle,target,version,profile='coding-agent',budget=32768,host_context=None):
        version_tuple(version)
        files=content_files(bundle)
        raw=json_bytes({'snapshot_version':version,'files':{name:digest(data) for name,data in files.items()}})
        with self.lock():
            self._recover()
            return self._activate(version,raw,files,target,profile,'local-snapshot',0,budget,host_context=host_context)

    def install_signed(self,bundle,target,profile='coding-agent',budget=32768,remote_config=None,host_context=None):
        with self.lock():
            self._recover()
            manifest,raw,files=self._load_signed(bundle)
            state=self._state()
            if remote_config is not None:
                current=self._config()
                if state.get('pin') or current.get('source') != remote_config.get('source') or current.get('mode','off') != remote_config.get('mode','off'):
                    return False
                if not state.get('target'):
                    return False
                target=Path(state['target'])
                profile=state['profile']
                budget=state['budget']
            seq=manifest['sequence']
            if seq < state.get('highest_sequence',0) or (seq == state.get('highest_sequence') and digest(raw) != state.get('highest_manifest_hash')):
                raise TrustError('Release sequence was replayed or reused')
            if state.get('version') and version_tuple(manifest['version']) < version_tuple(state['version']):
                raise TrustError('Remote downgrades require explicit cached rollback')
            return self._activate(manifest['version'],raw,files,target,profile,'signed',seq,budget,read_bytes(Path(bundle)/'release.json.sig',16384),host_context=host_context)

    def _split(self,data,state):
        if data.count(BEGIN) != data.count(END) or data.count(BEGIN)>1:
            raise ConflictError('Managed block markers are duplicate or incomplete')
        if BEGIN not in data:
            if state.get('target'):
                raise ConflictError('Managed block was removed outside installer')
            return data,b'',b''
        if not state.get('target'):
            raise ConflictError('Managed block belongs to another installation')
        start=data.index(BEGIN)
        end=data.index(END)+len(END)
        if end <= start:
            raise ConflictError('Managed block order is invalid')
        block=data[start:end]
        if digest(block) != state.get('block_hash'):
            raise ConflictError('User modified managed block; original preserved')
        return data[:start],block,data[end:]

    def _activate(self,version,raw,files,target,profile,trust,sequence,budget,signature=None,pin=None,host_context=None,settings=None):
        if profile not in ('coding-agent','chat','work-document'):
            raise InputError('Unknown protocol profile')
        target=safe_path(target)
        target.parent.mkdir(parents=True,exist_ok=True)
        state=self._state()
        context=host_context or state.get('host_context')
        if context:
            context=dict(context)
            if context.get('host')=='claude-code':
                if context.get('scope')=='user':
                    context['claude_home']=str(claude_home(argparse.Namespace(**context)))
                else:
                    context.pop('claude_home',None)
            for key in ('project_root','codex_home','claude_home'):
                if context.get(key) is not None:
                    context[key]=str(safe_path(context[key]))
            if host_target(argparse.Namespace(**context)) != target:
                raise ConflictError('Host now selects a different instruction file; user override preserved')
            budget=host_budget(argparse.Namespace(**context),target)
        if state.get('target') and state['target'] != str(target):
            raise ConflictError('This state owns a different host target')
        cache_id=version+'-'+digest(raw)
        cache=self.root/'releases'/cache_id
        enabled, honorifics = application_settings(state)
        if settings is not None:
            enabled, honorifics = settings
        cache_bytes = dict(files)
        cache_bytes['metadata.json'] = json_bytes({'version':version,'trust':trust,'hash':digest(raw),'files':{name:digest(data) for name,data in files.items()}})
        cache_bytes['release.json'] = raw
        if signature is not None:
            cache_bytes['release.json.sig'] = signature
        if cache.exists():
            for name, data in cache_bytes.items():
                if read_bytes(cache/name) != data:
                    raise TrustError('Cached content changed; existing cache preserved')
        else:
            cache.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
            staged=Path(tempfile.mkdtemp(prefix='.cache-',dir=cache.parent))
            for name, data in cache_bytes.items():
                atomic_write(staged/name,data,expected=b'')
            parent=open_directory(cache.parent)
            try:
                if cache.exists():
                    raise ConflictError('Release cache appeared during staging; existing cache preserved')
                os.rename(staged.name,cache.name,src_dir_fd=parent,dst_dir_fd=parent)
                os.fsync(parent)
            finally:
                os.close(parent)
        with self._target_lock(target):
            old=read_bytes(target,MAX_TOTAL_BYTES) if target.exists() else b''
            if context and context.get('host')=='claude-code':
                # Conservatively reject frontmatter without parsing or changing user metadata.
                header=old[3:] if old.startswith(b'\xef\xbb\xbf') else old
                if header.lstrip(b' \t\r\n').split(b'\n',1)[0].strip(b' \t\r')==b'---':
                    raise ConflictError('Claude rule file has a YAML frontmatter delimiter; startup-wide protocol requires an unscoped file; existing content preserved')
            prefix,block,suffix=self._split(old,state)
            body=files['profiles/'+profile+'.md']
            if enabled:
                new_block=BEGIN+b'\n'+('Korean Protocol '+version+'\n').encode()+body.rstrip(b'\n')+b'\n'+speech_overlay(honorifics)+('전체 규칙·사전: '+str(cache)+'\n').encode()+END
            else:
                new_block=BEGIN+b'\nKorean Protocol is disabled.\n'+END
            if len(new_block)>MAX_MANAGED_BYTES:
                raise InputError('Managed block exceeds 30 KiB budget')
            separator=state.get('separator','').encode('ascii') if block else (b'' if not old or old.endswith(b'\n') else b'\n')
            after=prefix+separator+new_block+suffix if not block else prefix+new_block+suffix
            if len(after)>budget or len(after)>MAX_TOTAL_BYTES:
                raise InputError('Instruction or installer file budget exceeded; existing instructions preserved')
            new=dict(state)
            new.update({'version':version,'cache_id':cache_id,'trust':trust,'target':str(target),'profile':profile,'budget':budget,'block_hash':digest(new_block),'separator':separator.decode('ascii'),'pin':pin,'highest_sequence':max(sequence,state.get('highest_sequence',0))})
            new.update({'profile_bytes':len(body),'managed_bytes':len(new_block),'protocol_enabled':enabled,'honorifics':honorifics})
            if context:
                new['host_context']=context
            new['budget_kind']='codex-project-chain-remaining' if context and context['host']=='codex' and context['scope']=='project' else 'installer-file-safety' if context else 'caller-file-bound'
            if sequence and sequence >= state.get('highest_sequence',0):
                new['highest_manifest_hash']=digest(raw)
            if not state:
                new['original_exists']=target.exists()
                new['original_prefix_hash']=digest(prefix+separator)
            if state==new and old==after:
                return False
            self._transaction(target,old,after,new)
            return True

    def _transaction(self,target,before,after,new_state):
        journal={'target':str(target),'before':base64.b64encode(before).decode(),'after_hash':digest(after),'old_state':self._state(),'new_state':new_state}
        backup=self.root/'backups'/uuid.uuid4().hex
        backup.mkdir(parents=True,mode=0o700)
        atomic_write(backup/'original',before)
        atomic_write(self.journal_path,json_bytes(journal))
        try:
            atomic_write(target,after,expected=before)
            atomic_write(self.state_path,json_bytes(new_state))
            self.journal_path.unlink()
        except OSError:
            self._recover(locked_target=target)
            raise WriteError('Atomic update failed; previous content restored') from None

    def _recover(self,locked_target=None):
        self._recover_scheduler()
        if not self.journal_path.exists():
            return
        j=strict_json(read_bytes(self.journal_path,MAX_JOURNAL_BYTES))
        target=safe_path(j['target'])
        with nullcontext() if target==locked_target else self._target_lock(target):
            before=base64.b64decode(j['before'],validate=True)
            current=read_bytes(target,MAX_TOTAL_BYTES) if target.exists() else b''
            state=self._state()
            if state==j['new_state'] and digest(current)==j['after_hash']:
                self.journal_path.unlink()
                return
            if current != before and digest(current) != j['after_hash']:
                raise ConflictError('Interrupted target changed; recovery preserves user content')
            if current != before:
                atomic_write(target,before,expected=current)
            if state != j['old_state']:
                atomic_write(self.state_path,json_bytes(j['old_state']))
            self.journal_path.unlink()

    def recover(self):
        with self.lock():
            self._recover()

    def _load_cache(self,cache_id,version,trust):
        if not isinstance(cache_id,str) or not re.fullmatch(re.escape(version)+r'-[0-9a-f]{64}',cache_id):
            raise TrustError('Invalid cached release identity')
        cache=safe_path(self.root/'releases'/cache_id)
        metadata=self._json(cache/'metadata.json',{})
        files=content_files(cache)
        raw=read_bytes(cache/'release.json',65536)
        hashes={name:digest(data) for name,data in files.items()}
        if (cache_id != version+'-'+digest(raw) or metadata.get('version') != version or
                metadata.get('trust') != trust or digest(raw) != metadata.get('hash') or
                hashes != metadata.get('files')):
            raise TrustError('Cached content changed')
        sig=None
        seq=0
        if trust=='signed':
            manifest,raw,files=self._load_signed(cache,fresh=False)
            if manifest['version'] != version:
                raise TrustError('Cached release version differs from state')
            seq=manifest['sequence']
            sig=read_bytes(cache/'release.json.sig',16384)
        elif trust=='local-snapshot':
            manifest=strict_json(raw)
            if manifest.get('snapshot_version') != version or manifest.get('files') != hashes:
                raise TrustError('Cached snapshot manifest changed')
        else:
            raise TrustError('Unknown cached release trust')
        return raw,files,seq,sig

    def _recover_scheduler(self):
        if not self.scheduler_journal_path.exists():
            return
        journal=strict_json(read_bytes(self.scheduler_journal_path,MAX_JOURNAL_BYTES))
        if not isinstance(journal,dict) or set(journal) != {'target','before','after_hash','old_config','new_config'}:
            raise ConflictError('Invalid scheduler migration journal; files preserved')
        target=safe_path(journal['target'])
        before=base64.b64decode(journal['before'],validate=True)
        old_config=base64.b64decode(journal['old_config'],validate=True)
        new_config=base64.b64decode(journal['new_config'],validate=True)
        old=strict_json(old_config)
        new=strict_json(new_config)
        if (not isinstance(old,dict) or not isinstance(new,dict) or
                old.get('scheduler',{}).get('path') != str(target) or
                new.get('scheduler',{}).get('path') != str(target) or
                old.get('scheduler',{}).get('hash') != digest(before) or
                new.get('scheduler',{}).get('hash') != journal['after_hash']):
            raise ConflictError('Scheduler recovery target has no ownership; files preserved')
        with self._target_lock(target):
            current=read_bytes(target)
            config=read_bytes(self.config_path,MAX_TOTAL_BYTES)
            if config not in (old_config,new_config) or (current != before and digest(current) != journal['after_hash']):
                raise ConflictError('Interrupted scheduler migration changed; user files preserved')
            if config == new_config and digest(current) == journal['after_hash']:
                self.scheduler_journal_path.unlink()
                return
            if current != before:
                atomic_write(target,before,expected=current)
            if config != old_config:
                atomic_write(self.config_path,old_config,expected=config)
            self.scheduler_journal_path.unlink()

    def _scheduler_transaction(self,target,before,after,cfg):
        old_config=read_bytes(self.config_path,MAX_TOTAL_BYTES)
        new_config=json_bytes(cfg)
        journal={'target':str(target),'before':base64.b64encode(before).decode(),
                 'after_hash':digest(after),'old_config':base64.b64encode(old_config).decode(),
                 'new_config':base64.b64encode(new_config).decode()}
        journal_bytes=json_bytes(journal)
        if len(journal_bytes) > MAX_JOURNAL_BYTES:
            raise InputError('Scheduler migration journal exceeds safety budget')
        with self._target_lock(target):
            atomic_write(self.scheduler_journal_path,journal_bytes,expected=b'')
            try:
                atomic_write(target,after,expected=before)
                atomic_write(self.config_path,new_config,expected=old_config)
                self.scheduler_journal_path.unlink()
            except OSError:
                # Release the target lock before the common journal recovery path.
                pass
            else:
                return
        self._recover_scheduler()
        raise WriteError('Scheduler migration failed; previous generated output restored')

    def _refresh_application_scheduler(self):
        cfg=self._config()
        scheduler=cfg.get('scheduler',{})
        current=str(safe_path(__file__))
        record=scheduler.get('launch_agent')
        generated=safe_path(scheduler['path']) if scheduler.get('path') else None
        data=read_bytes(generated) if generated and generated.exists() else None
        job=None
        if data is not None:
            if digest(data) != scheduler.get('hash'):
                raise ConflictError('User modified scheduler output; file preserved')
            try:
                job=plistlib.loads(data)
            except (ValueError,plistlib.InvalidFileException):
                raise ConflictError('Invalid owned scheduler output; file preserved') from None
            if (not isinstance(job,dict) or job.get('Label') != scheduler.get('label') or
                    not isinstance(job.get('ProgramArguments'),list) or len(job['ProgramArguments']) < 2):
                raise ConflictError('Generated scheduler identity differs; file preserved')
        if record and (not isinstance(record,dict) or not isinstance(record.get('arguments'),list) or len(record['arguments']) < 2):
            raise ConflictError('Recorded scheduler arguments are invalid; job preserved')
        migrate_record=record and record['arguments'][1] != current
        migrate_output=job and job['ProgramArguments'][1] != current
        pending=scheduler.get('runtime_migration_registration_required',False)
        if not migrate_record and not migrate_output and not pending:
            return
        runtime=Path(current)
        if self.root not in runtime.parents or not runtime.is_file():
            raise InputError('Scheduler migration requires the durable runtime inside its state directory')
        info=runtime.stat()
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o022:
            raise InputError('Durable runtime has unsafe ownership or permissions')
        # Stop the old executable before committing application settings. A failed
        # migration leaves the requested settings unchanged and fails closed.
        if migrate_record:
            self._unregister_scheduler(cfg)
            scheduler['runtime_migration_registration_required']=True
        if migrate_output:
            job['ProgramArguments'][1]=current
            updated=plistlib.dumps(job,sort_keys=True)
            scheduler['hash']=digest(updated)
            self._scheduler_transaction(generated,data,updated,cfg)
        if migrate_record or pending:
            self._register_scheduler(cfg)
            cfg['scheduler'].pop('runtime_migration_registration_required',None)
            atomic_write(self.config_path,json_bytes(cfg))

    def configure_application(self,enabled=None,honorifics=None):
        if enabled is None and honorifics is None:
            raise InputError('Choose --protocol or --honorifics')
        if any(value is not None and type(value) is not bool for value in (enabled,honorifics)):
            raise InputError('Application settings must be booleans')
        with self.lock():
            self._recover()
            state=self._state()
            if not state.get('target'):
                raise MissingError('No installed protocol')
            current_enabled,current_honorifics=application_settings(state)
            settings=(current_enabled if enabled is None else enabled,
                      current_honorifics if honorifics is None else honorifics)
            raw,files,seq,sig=self._load_cache(state.get('cache_id'),state['version'],state['trust'])
            self._refresh_application_scheduler()
            return self._activate(state['version'],raw,files,Path(state['target']),state['profile'],state['trust'],seq,state['budget'],sig,pin=state.get('pin'),settings=settings)

    def rollback(self,version):
        version_tuple(version)
        with self.lock():
            self._recover()
            state=self._state()
            if not state.get('target'):
                raise MissingError('No installed protocol')
            candidates=list((self.root/'releases').glob(version+'-*'))
            if len(candidates)!=1:
                raise MissingError('Requested cached version is missing or ambiguous')
            cache=candidates[0]
            metadata=self._json(cache/'metadata.json',{})
            raw,files,seq,sig=self._load_cache(cache.name,version,metadata.get('trust'))
            self._activate(version,raw,files,Path(state['target']),state['profile'],metadata['trust'],seq,state['budget'],sig,pin=version)

    def uninstall(self):
        with self.lock():
            self._recover()
            state=self._state()
            if not state.get('target'):
                raise MissingError('No installed protocol')
            target=safe_path(state['target'])
            with self._target_lock(target):
                before=read_bytes(target,MAX_TOTAL_BYTES)
                prefix,block,suffix=self._split(before,state)
                separator=state.get('separator','').encode('ascii')
                if separator and prefix.endswith(separator) and digest(prefix)==state.get('original_prefix_hash'):
                    prefix=prefix[:-len(separator)]
                cfg = self._config()
                self._disable_scheduler(cfg)
                cfg['mode'] = 'off'
                atomic_write(self.config_path, json_bytes(cfg))
                self._transaction(target,before,prefix+suffix,{})

    def fetch(self,url,maximum,deadline=None):
        if type(maximum) is not int or not 0<=maximum<=MAX_FILE_BYTES:
            raise InputError('Invalid download limit')
        cfg=self._config()
        source=validate_source(cfg.get('source',''))
        base=urllib.parse.urlsplit(source)
        parts=urllib.parse.urlsplit(url)
        if parts.scheme!='https' or parts.netloc!=base.netloc or parts.query or parts.fragment or parts.username:
            raise InputError('Fetch URL differs from configured origin')
        headers={'User-Agent':'KoreanProtocol/'+ENGINE_VERSION}
        if cfg.get('token_env'):
            token=os.environ.get(cfg['token_env'])
            if not token:
                raise NetworkError('Private endpoint credential is unavailable')
            if '\r' in token or '\n' in token:
                raise InputError('Invalid endpoint credential')
            headers['Authorization']='Bearer '+token
        deadline=deadline if deadline is not None else time.monotonic()+15
        remaining=deadline-time.monotonic()
        if remaining<=0:
            raise NetworkError('Network time budget exhausted')
        request=json_bytes({'url':url,'headers':headers,'maximum':maximum})
        if len(request)>MAX_DOWNLOAD_REQUEST_BYTES:
            raise InputError('Download request exceeds size limit')
        worker=None
        try:
            # macOS urllib proxy discovery uses CoreFoundation, which is unsafe
            # after a Python fork. Exec also supports dynamically loaded runtimes.
            worker=subprocess.Popen([sys.executable,'-I','-B',str(Path(__file__).resolve()),'--download-worker'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
            remaining=deadline-time.monotonic()
            if remaining<=0:
                raise NetworkError('Network time budget exhausted')
            # The local worker writes at most maximum+1 bytes and no diagnostics.
            response,_=worker.communicate(input=request,timeout=min(15,remaining))
            if time.monotonic()>deadline:
                raise NetworkError('Network time budget exhausted')
            if worker.returncode or not response or response[0]!=1 or len(response)>maximum+1:
                raise NetworkError('HTTPS content download failed')
            return response[1:]
        except subprocess.TimeoutExpired:
            raise NetworkError('Network time budget exhausted') from None
        except (OSError,EOFError,ValueError,http.client.HTTPException):
            raise NetworkError('HTTPS content download failed') from None
        finally:
            if worker is not None:
                try:
                    if worker.poll() is None:
                        worker.kill()
                    try:
                        worker.wait(timeout=0.2)
                    except subprocess.TimeoutExpired:
                        worker.kill()
                        worker.wait(timeout=0.2)
                except (OSError,subprocess.TimeoutExpired):
                    raise NetworkError('HTTPS worker termination failed') from None
                finally:
                    for stream in (worker.stdin,worker.stdout):
                        if stream is not None:
                            stream.close()

    def _download(self,url,maximum,deadline):
        if time.monotonic()>=deadline:
            raise NetworkError('Update time budget exhausted')
        data=self.fetch(url,maximum,deadline=deadline)
        if time.monotonic()>=deadline:
            raise NetworkError('Update time budget exhausted')
        return data

    def update(self,scheduled=False):
        deadline=time.monotonic()+60
        cfg=self._config()
        state=self._state()
        if not state.get('target'):
            raise MissingError('No installed protocol')
        if state.get('pin') or (scheduled and cfg.get('mode','off')=='off'):
            return False
        now=time.time()
        if scheduled and now < cfg.get('next_attempt',0):
            return False
        if state.get('trust')!='signed':
            raise TrustError('Local snapshots require explicit signed bootstrap before remote updates')
        source=validate_source(cfg.get('source',''))
        stage=self.root/'downloads'/uuid.uuid4().hex
        stage.mkdir(parents=True,mode=0o700)
        try:
            raw=self._download(source+'/stable/release.json',65536,deadline)
            atomic_write(stage/'release.json',raw)
            atomic_write(stage/'release.json.sig',self._download(source+'/stable/release.json.sig',16384,deadline))
            manifest=validate_manifest(strict_json(raw))
            self._verify_signature(stage,raw,manifest)
            for entry in manifest['files']:
                if time.monotonic()>deadline:
                    raise NetworkError('Update time budget exhausted')
                data=self._download(source+'/releases/'+manifest['version']+'/'+entry['path'],entry['size'],deadline)
                atomic_write(stage/entry['path'],data)
            changed=self.install_signed(stage,Path(state['target']),state['profile'],state['budget'],remote_config=cfg)
        except ProtocolError:
            self._record_attempt(now,False)
            raise
        self._record_attempt(now,True)
        return changed

    def _record_attempt(self,when,success):
        with self.lock():
            cfg=self._config()
            cfg['last_attempt']=when
            if success:
                cfg.update({'last_success':when,'failures':0,'next_attempt':when+3600*cfg.get('interval_hours',24)})
            else:
                cfg['failures']=cfg.get('failures',0)+1
                cfg['next_attempt']=when+3600*min(24,2**min(cfg['failures']-1,5))
            atomic_write(self.config_path,json_bytes(cfg))


def default_state_dir():
    if sys.platform=='darwin':
        return Path.home()/'Library/Application Support/KoreanProtocol'
    if os.name=='nt':
        return Path(os.environ.get('LOCALAPPDATA',str(Path.home()/'AppData/Local')))/'KoreanProtocol'
    return Path(os.environ.get('XDG_DATA_HOME',str(Path.home()/'.local/share')))/'korean-protocol'


def claude_home(args):
    return safe_path(getattr(args,'claude_home',None) or os.environ.get('CLAUDE_CONFIG_DIR') or Path.home()/'.claude')


def host_target(args):
    if args.host not in ('codex','claude-code','gemini-cli'):
        raise CompatibilityError('Only Codex, Claude Code and Gemini Markdown adapters are implemented')
    if args.scope=='project':
        if not args.project_root:
            raise InputError('Project scope requires --project-root')
        root=safe_path(args.project_root)
    else:
        root=Path(getattr(args,'codex_home',None) or os.environ.get('CODEX_HOME',str(Path.home()/'.codex'))) if args.host=='codex' else claude_home(args) if args.host=='claude-code' else Path.home()/'.gemini'
        root=safe_path(root)
    if args.host=='codex':
        override=root/'AGENTS.override.md'
        return override if override.exists() and read_bytes(override).strip() else root/'AGENTS.md'
    if args.host=='claude-code':
        return safe_path((root/'.claude' if args.scope=='project' else root)/'rules/korean-protocol.md')
    return root/'GEMINI.md'


def host_budget(args,target):
    # These are installer file bounds, not model context limits.
    if args.host != 'codex' or args.scope=='user':
        return MAX_TOTAL_BYTES
    home=safe_path(getattr(args,'codex_home',None) or os.environ.get('CODEX_HOME',str(Path.home()/'.codex')))
    limit=32768
    config=home/'config.toml'
    if config.exists():
        # Python 3.9 has no TOML parser. Accept only a simple top-level integer.
        text=read_bytes(config).decode('utf-8')
        top=re.split(r'^\s*\[',text,maxsplit=1,flags=re.MULTILINE)[0]
        if 'project_doc_max_bytes' in top:
            found=re.search(r'^project_doc_max_bytes\s*=\s*([0-9]+)\s*(?:#.*)?$',top,re.MULTILINE)
            if not found:
                raise CompatibilityError('Instruction limit needs an explicit supported TOML integer')
            limit=int(found.group(1))
        if 'project_doc_fallback_filenames' in top:
            raise CompatibilityError('Custom fallback discovery requires a verified adapter')
        if 'project_root_markers' in top:
            raise CompatibilityError('Custom project root discovery requires a verified adapter')
    directory=safe_path(args.project_root)
    # Native 0.162.1 applies this cap only to the project discovery chain.
    # The nearest .git directory/file marks its root; absent a marker, only
    # the explicitly selected working directory participates in discovery.
    root=directory
    for ancestor in (directory,)+tuple(directory.parents):
        marker=ancestor/'.git'
        if marker.exists():
            safe_path(marker)
            root=ancestor
            break
    chain=[]
    current=directory
    while current!=root:
        chain.append(current)
        current=current.parent
    chain.append(root)
    for ancestor in reversed(chain):
        override=ancestor/'AGENTS.override.md'
        selected=override if override.exists() and read_bytes(override).strip() else ancestor/'AGENTS.md'
        if selected!=target and selected.exists():
            limit-=len(read_bytes(selected,MAX_TOTAL_BYTES))
    if limit<=0:
        raise InputError('Ancestor project instructions exhaust the project chain budget')
    return min(limit,MAX_TOTAL_BYTES)


def main(argv=None):
    parser=argparse.ArgumentParser(description='Offline content-only Korean Protocol installer')
    parser.add_argument('--state-dir',type=Path,default=default_state_dir())
    sub=parser.add_subparsers(dest='command',required=True)
    install=sub.add_parser('install')
    install.add_argument('--bundle',type=Path,required=True)
    install.add_argument('--host',choices=['codex','claude-code','gemini-cli'],default='codex')
    install.add_argument('--scope',choices=['user','project'],default='project')
    install.add_argument('--project-root',type=Path)
    install.add_argument('--codex-home',type=Path)
    install.add_argument('--claude-home',type=Path)
    install.add_argument('--profile',choices=['coding-agent','chat','work-document'],default='coding-agent')
    install.add_argument('--local-snapshot',action='store_true')
    install.add_argument('--version',default='0.1.0')
    install.add_argument('--trust-key',type=Path)
    install.add_argument('--expected-fingerprint')
    install.add_argument('--source')
    install.add_argument('--autoupdate',choices=['off','interval'],default='off')
    status=sub.add_parser('status');status.add_argument('--json',action='store_true')
    sub.add_parser('uninstall')
    rollback=sub.add_parser('rollback');rollback.add_argument('--version',required=True)
    update=sub.add_parser('update');update.add_argument('--scheduled',action='store_true')
    update.add_argument('--pin');update.add_argument('--unpin',action='store_true')
    sub.add_parser('recover')
    scheduler = sub.add_parser('scheduler')
    scheduler.add_argument('action', choices=['register', 'unregister', 'status'])
    auto=sub.add_parser('autoupdate');auto.add_argument('action',choices=['configure'])
    auto.add_argument('--mode',choices=['off','interval','scheduled'],required=True)
    auto.add_argument('--source');auto.add_argument('--token-env');auto.add_argument('--interval-hours',type=int)
    auto.add_argument('--emit',type=Path)
    run=sub.add_parser('run');run.add_argument('host_command',nargs=argparse.REMAINDER)
    args=parser.parse_args(argv)
    try:
        ctrl=Controller(args.state_dir)
        if args.command=='install':
            if args.trust_key:
                if not args.expected_fingerprint:
                    raise InputError('A separately verified fingerprint is required')
                ctrl.trust_key(args.trust_key,args.expected_fingerprint)
            target=host_target(args)
            budget=host_budget(args,target)
            context={'host':args.host,'scope':args.scope,'project_root':str(args.project_root) if args.project_root else None,'codex_home':str(args.codex_home or os.environ.get('CODEX_HOME',str(Path.home()/'.codex')))}
            if args.host=='claude-code':
                context.pop('codex_home')
                if args.scope=='user':
                    context['claude_home']=str(claude_home(args))
            if args.local_snapshot:
                ctrl.install_snapshot(args.bundle,target,args.version,args.profile,budget,host_context=context)
            else:
                ctrl.install_signed(args.bundle,target,args.profile,budget,host_context=context)
            ctrl.configure(mode=args.autoupdate,source=args.source)
        elif args.command=='status':
            print(json.dumps(ctrl.status(),ensure_ascii=False,sort_keys=True))
        elif args.command=='uninstall':
            ctrl.uninstall()
        elif args.command=='rollback':
            ctrl.rollback(args.version)
        elif args.command=='recover':
            ctrl.recover()
        elif args.command=='update':
            if args.pin or args.unpin:
                ctrl.pin(args.pin if args.pin else None)
            else:
                ctrl.update(scheduled=args.scheduled)
        elif args.command=='autoupdate':
            ctrl.configure(args.mode,args.source,args.token_env,args.interval_hours,args.emit)
        elif args.command=='scheduler':
            if args.action == 'register':
                result = ctrl.register_scheduler()
            elif args.action == 'unregister':
                result = ctrl.unregister_scheduler()
            else:
                result = ctrl.status()['scheduler']
            print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        elif args.command=='run':
            if not ctrl.status()['installed']:
                raise MissingError('No local protocol is installed')
            command=args.host_command
            if command and command[0]=='--':
                command=command[1:]
            if not command:
                raise InputError('run requires a host command')
            try:
                ctrl.update(scheduled=True)
            except ProtocolError as exc:
                print('Protocol update failed; local profile retained: '+str(exc),file=sys.stderr)
            except OSError:
                print('Protocol update filesystem failed; local profile retained',file=sys.stderr)
            if ctrl.status()['recovery_required']:
                ctrl.recover()
            return subprocess.run(command,shell=False).returncode
        return 0
    except ProtocolError as exc:
        print(str(exc),file=sys.stderr)
        return exc.code
    except OSError:
        print('Local filesystem or host process failed',file=sys.stderr)
        return 8


if __name__=='__main__':
    sys.exit(download_worker_main() if sys.argv[1:]==['--download-worker'] else main())
