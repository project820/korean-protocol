import hashlib
import json
from pathlib import Path
import posixpath
import re
import tempfile
import unittest
from urllib.parse import urlsplit
import zipfile

from distribution.build import INPUTS, PREFIX, build
from distribution.agent_install import VERSION
from distribution.launcher import PREVIEW_VERSION


class DistributionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)/'source'
        self.root.mkdir()
        for name in INPUTS:
            path = self.root/name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(('fixture '+name+'\n').encode())
        for name in ('LICENSE','NOTICE.md'):
            (self.root/name).write_bytes((Path(__file__).resolve().parents[1]/name).read_bytes())
        self.output = Path(self.temp.name)/'preview.zip'

    def test_allowlist_and_checksums_exclude_extra_files(self):
        (self.root/'.env').write_text('not for distribution')
        (self.root/'runtime/private-key').write_text('not for distribution')
        build(self.root,self.output)
        with zipfile.ZipFile(self.output) as archive:
            names = archive.namelist()
            self.assertFalse(any('.env' in name or 'private-key' in name for name in names))
            checksum_name = next(name for name in names if name.endswith('/SHA256SUMS'))
            prefix = checksum_name.removesuffix('SHA256SUMS')
            for line in archive.read(checksum_name).decode().splitlines():
                digest,name = line.split('  ',1)
                self.assertEqual(digest,hashlib.sha256(archive.read(prefix+name)).hexdigest())
            self.assertEqual(len(names)-1,len(archive.read(checksum_name).decode().splitlines()))

    def test_reproducible_bytes(self):
        build(self.root,self.output)
        other = self.output.with_name('second.zip')
        build(self.root,other)
        self.assertEqual(self.output.read_bytes(),other.read_bytes())

    def test_control_documents_and_evidence_are_packaged_without_raw_research(self):
        required = (
            'docs/spec/control-expression.md',
            'docs/distribution/application-controls.md',
            'research/2026-10-13-ellipsis/research-note.md',
            'research/2026-10-13-ellipsis/sourceevidence.json',
        )
        raw = self.root/'research/2026-10-13-ellipsis/source-download.pdf'
        raw.write_bytes(b'local research download')
        build(self.root,self.output)
        with zipfile.ZipFile(self.output) as archive:
            prefix = next(n for n in archive.namelist() if n.endswith('/SHA256SUMS')).removesuffix('SHA256SUMS')
            for source in required:
                self.assertEqual((self.root/source).read_bytes(),archive.read(prefix+source))
            self.assertNotIn(prefix+'research/2026-10-13-ellipsis/source-download.pdf',archive.namelist())

    def test_repository_control_document_links_resolve_in_archive(self):
        build(Path(__file__).resolve().parents[1],self.output)
        with zipfile.ZipFile(self.output) as archive:
            prefix = next(n for n in archive.namelist() if n.endswith('/SHA256SUMS')).removesuffix('SHA256SUMS')
            packaged = {name.removeprefix(prefix) for name in archive.namelist()}
            linked = set()
            for source in ('docs/spec/control-expression.md','docs/distribution/application-controls.md'):
                content = archive.read(prefix+source).decode()
                for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)',content):
                    url = urlsplit(target)
                    if url.scheme or url.netloc or not url.path:
                        continue
                    destination = posixpath.normpath(posixpath.join(posixpath.dirname(source),url.path))
                    self.assertIn(destination,packaged,(source,target))
                    linked.add(destination)
            self.assertIn('specification/rules.json',linked)
            self.assertIn('research/2026-10-13-ellipsis/research-note.md',linked)
            self.assertIn('(docs/distribution/application-controls.md)',archive.read(prefix+'INSTALL.md').decode())
            self.assertIn('(control-expression.md)',archive.read(prefix+'docs/spec/korean-rules.md').decode())

    def test_repository_package_and_offline_defaults_match_source_version(self):
        repo = Path(__file__).resolve().parents[1]
        versions = {json.loads((repo/name).read_text())['version'] for name in
                    ('specification/rules.json', 'lexicon/core.json',
                     'lexicon/domains/software.json')}
        self.assertEqual(1, len(versions))
        version = versions.pop()
        self.assertEqual('korean-protocol-' + version, PREFIX)
        self.assertEqual(version.removesuffix('-draft'), VERSION)
        self.assertEqual(VERSION, PREVIEW_VERSION)
        guide = (repo/'distribution/START-HERE.md').read_text()
        self.assertIn(PREFIX, guide)
        self.assertIn('--version ' + VERSION, guide)

    def test_chat_attachment_preserves_full_rules_and_dictionaries(self):
        build(self.root,self.output)
        with zipfile.ZipFile(self.output) as archive:
            name = next(n for n in archive.namelist() if n.endswith('/KOREAN-PROTOCOL.md'))
            content = archive.read(name)
            for source in ('pack/protocol.md','lexicon/core.json','lexicon/domains/software.json'):
                self.assertIn((self.root/source).read_bytes(),content)

    def test_archive_and_standalone_preserve_full_license_and_notice(self):
        build(self.root,self.output)
        with zipfile.ZipFile(self.output) as archive:
            name = next(n for n in archive.namelist() if n.endswith('/KOREAN-PROTOCOL.md'))
            prefix = name.removesuffix('KOREAN-PROTOCOL.md')
            content = archive.read(name)
            for source in ('LICENSE','NOTICE.md'):
                original = (self.root/source).read_bytes()
                self.assertEqual(original,archive.read(prefix+source))
                self.assertIn(original,content)

    def test_standalone_does_not_duplicate_notices_already_in_pack(self):
        pack = self.root/'pack/protocol.md'
        for source in ('LICENSE','NOTICE.md'):
            pack.write_bytes(pack.read_bytes()+b'\n'+(self.root/source).read_bytes())
        build(self.root,self.output)
        with zipfile.ZipFile(self.output) as archive:
            name = next(n for n in archive.namelist() if n.endswith('/KOREAN-PROTOCOL.md'))
            content = archive.read(name)
            for source in ('LICENSE','NOTICE.md'):
                self.assertEqual(1,content.count((self.root/source).read_bytes()))

    def test_launcher_is_next_to_runtime_in_archive(self):
        build(self.root,self.output)
        with zipfile.ZipFile(self.output) as archive:
            entry = next(n for n in archive.namelist() if n.endswith('/runtime/kproto.py'))
            start = entry.removesuffix('runtime/kproto.py')+'start.py'
            self.assertIn(start,archive.namelist())
            prefix = entry.removesuffix('runtime/kproto.py')
            self.assertIn(prefix+'agent-install.py',archive.namelist())
            self.assertIn(prefix+'INSTALL.md',archive.namelist())
            self.assertIn(prefix+'docs/distribution/signed-install.md',archive.namelist())
            self.assertIn(prefix+'distribution/trust/publisher.pub',archive.namelist())
            self.assertIn(prefix+'distribution/trust/publisher.json',archive.namelist())

    def test_existing_output_is_preserved(self):
        self.output.write_bytes(b'existing')
        with self.assertRaises(FileExistsError):
            build(self.root,self.output)
        self.assertEqual(b'existing',self.output.read_bytes())

    def test_missing_input_produces_no_archive(self):
        (self.root/INPUTS[0]).unlink()
        with self.assertRaises(FileNotFoundError):
            build(self.root,self.output)
        self.assertFalse(self.output.exists())

    def test_symlink_input_is_rejected(self):
        path = self.root/INPUTS[0]
        path.unlink()
        path.symlink_to(self.root/INPUTS[1])
        with self.assertRaises(ValueError):
            build(self.root,self.output)
        self.assertFalse(self.output.exists())


if __name__ == '__main__':
    unittest.main()
