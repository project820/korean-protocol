import hashlib
from pathlib import Path
import tempfile
import unittest
import zipfile

from distribution.build import INPUTS, build


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
