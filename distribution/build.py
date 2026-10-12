"""Build a deterministic, unsigned offline preview from an explicit allowlist."""
import argparse
import hashlib
import io
from pathlib import Path
import stat
import zipfile


PREFIX = 'korean-protocol-0.2.0-draft'
INPUTS = (
    'runtime/__init__.py', 'runtime/kproto.py',
    'profiles/coding-agent.md', 'profiles/chat.md', 'profiles/work-document.md',
    'specification/rules.json', 'specification/ste-crosswalk.json',
    'lexicon/core.json', 'lexicon/domains/software.json', 'pack/protocol.md',
    'schemas/lexicon.schema.json', 'schemas/release.schema.json',
    'docs/spec/toc.md', 'docs/spec/architecture.md',
    'docs/spec/coverage-policy.md', 'docs/spec/korean-rules.md',
    'docs/spec/lexicon.md', 'examples/rule-cases.json',
    'examples/lexicon-cases.json', 'distribution/START-HERE.md',
)


def build(root, output):
    root, output = Path(root).resolve(), Path(output)
    files = {}
    for name in INPUTS:
        path = root/name
        for part in (path,*path.parents):
            if part == root:
                break
            if part.is_symlink():
                raise ValueError('Distribution input is a symlink: '+name)
        if not path.is_file():
            raise FileNotFoundError('Missing distribution input: '+name)
        destination = 'START-HERE.md' if name == 'distribution/START-HERE.md' else name
        files[destination] = path.read_bytes()
    files['docs/distribution/README.md'] = (
        '# Installation\n\nSee [the offline preview guide](../../START-HERE.md). '
        'This archive is unsigned and does not enable remote updates.\n'
    ).encode()
    files['SHA256SUMS'] = ''.join(
        hashlib.sha256(data).hexdigest()+'  '+name+'\n'
        for name,data in sorted(files.items())
    ).encode()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for name,data in sorted(files.items()):
            info = zipfile.ZipInfo(PREFIX+'/'+name,date_time=(1980,1,1,0,0,0))
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info,data)
    # Do not silently replace an earlier artifact or an unrelated file.
    with output.open('xb') as handle:
        handle.write(buffer.getvalue())
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path('.'))
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    try:
        result = build(args.root,args.output)
    except (OSError,ValueError) as error:
        parser.exit(1,str(error)+'\n')
    print(str(result.resolve()))


if __name__ == '__main__':
    main()
