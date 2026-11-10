import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import update_service as updates


class UpdatesTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory(prefix="update-test-", dir=Path(__file__).parent)
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)
        self.installer = b"test installer"
        self.name = "ClaimViewer-Setup-2.6.10.exe"
        self.url = f"https://github.com/{updates.REPO}/releases/download/v2.6.10/{self.name}"
        self.asset = {
            "name": self.name,
            "browser_download_url": self.url,
            "size": len(self.installer),
            "digest": "sha256:" + hashlib.sha256(self.installer).hexdigest(),
        }

    def release(self, tag="v2.6.10"):
        return io.BytesIO(json.dumps({"tag_name": tag, "assets": [self.asset]}).encode())

    def test_current_and_older_versions_never_download(self):
        for tag in (updates.VERSION, "v2.5.9"):
            with self.subTest(tag=tag), patch.object(updates, "_open", return_value=self.release(tag)) as fetch:
                self.assertNotIn("version", updates.download_latest(self.folder))
                fetch.assert_called_once_with(updates.RELEASE)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_verified_installer_is_saved_and_reused(self):
        with patch.object(updates, "_open", side_effect=[self.release(), io.BytesIO(self.installer)]) as fetch:
            self.assertEqual(updates.download_latest(self.folder)["version"], "2.6.10")
            self.assertEqual(fetch.call_args.args, (self.url,))
        self.assertEqual((self.folder / self.name).read_bytes(), self.installer)
        with patch.object(updates, "_open", return_value=self.release()) as fetch:
            self.assertEqual(updates.download_latest(self.folder)["version"], "2.6.10")
            fetch.assert_called_once_with(updates.RELEASE)

    def test_bad_checksum_leaves_no_installer_or_partial_file(self):
        self.asset["digest"] = "sha256:" + "0" * 64
        with patch.object(updates, "_open", side_effect=[self.release(), io.BytesIO(self.installer)]):
            with self.assertRaisesRegex(ValueError, "checksum"):
                updates.download_latest(self.folder)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_untrusted_installer_url_is_never_opened(self):
        self.asset["browser_download_url"] = "https://example.com/" + self.name
        with patch.object(updates, "_open", return_value=self.release()) as fetch:
            with self.assertRaisesRegex(ValueError, "verifiable"):
                updates.download_latest(self.folder)
            fetch.assert_called_once_with(updates.RELEASE)


if __name__ == "__main__":
    unittest.main(verbosity=2)
