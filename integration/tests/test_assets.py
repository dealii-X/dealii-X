import json
from pathlib import Path
import shutil
import tempfile
import unittest

from dealiix.asset_release import package_assets
from dealiix.assets import download_assets


class ReleaseAssets(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.source = self.root / "source"
        self.source.mkdir()
        (self.source / "heart.csv").write_text("time,Q\n0,1\n1,2\n")
        self.release = self.root / "release"
        self.local = self.root / "local"
        self.requests = []
        package_assets(self.source, self.release)

    def tearDown(self):
        self.temporary.cleanup()

    def fetch(self, url, destination):
        self.requests.append(url)
        shutil.copyfile(self.release / url.rsplit("/", 1)[-1], destination)

    def download(self):
        return download_assets(self.local, "https://example.invalid/releases/download/assets", self.fetch)

    def test_fresh_update_and_added_files(self):
        self.download()
        (self.local / "local-notes.txt").write_text("preserve")
        (self.source / "heart.csv").write_text("new cardiac data")
        (self.source / "organs").mkdir()
        (self.source / "organs/brain.json").write_text('{"case":1}')
        package_assets(self.source, self.release)
        self.download()
        self.assertEqual((self.local / "heart.csv").read_text(), "new cardiac data")
        self.assertEqual((self.local / "organs/brain.json").read_text(), '{"case":1}')
        self.assertEqual((self.local / "local-notes.txt").read_text(), "preserve")
        self.requests.clear()
        self.download()
        self.assertEqual(len(self.requests), 1)  # Refresh manifest, reuse matching local data.

    def test_modified_local_file_preserved(self):
        self.download()
        (self.local / "heart.csv").write_text("local edits")
        (self.source / "heart.csv").write_text("upstream update")
        package_assets(self.source, self.release)
        with self.assertRaisesRegex(ValueError, "Local asset changed"):
            self.download()
        self.assertEqual((self.local / "heart.csv").read_text(), "local edits")

    def test_bad_archive_preserves_existing_files(self):
        self.download()
        before = (self.local / "heart.csv").read_bytes()
        (self.source / "heart.csv").write_text("upstream update")
        package_assets(self.source, self.release)
        (self.release / "assets.zip").write_bytes(b"corrupt download")
        with self.assertRaisesRegex(ValueError, "checksum"):
            self.download()
        self.assertEqual((self.local / "heart.csv").read_bytes(), before)

    def test_manifest_escape_rejected(self):
        path = self.release / "assets-manifest.json"
        manifest = json.loads(path.read_text())
        manifest["files"][0]["name"] = "../outside.csv"
        path.write_text(json.dumps(manifest))
        with self.assertRaises(ValueError): self.download()
        self.assertFalse((self.root / "outside.csv").exists())

    def test_bad_sha1_rejected_even_with_correct_sha256(self):
        path = self.release / "assets-manifest.json"
        manifest = json.loads(path.read_text())
        manifest["files"][0]["sha1"] = "0" * 40
        path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "checksum"):
            self.download()
        self.assertFalse((self.local / "heart.csv").exists())

    def test_removed_assets_retained_and_package_is_reproducible(self):
        (self.source / ".private-note").write_text("do not upload")
        first = package_assets(self.source, self.release)
        self.assertEqual(first, package_assets(self.source, self.release))
        self.assertEqual(len(first["files"]), 1)
        self.download()
        (self.source / "heart.csv").unlink()
        (self.source / "new.csv").write_text("new")
        package_assets(self.source, self.release)
        self.download()
        self.assertTrue((self.local / "heart.csv").exists())
        self.assertTrue((self.local / "new.csv").exists())


if __name__ == "__main__": unittest.main()
