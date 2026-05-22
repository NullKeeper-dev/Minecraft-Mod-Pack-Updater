import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import updater


class UpdaterVersionTests(unittest.TestCase):
    def test_get_local_version_prefers_external_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            external = base / "external_version.txt"
            embedded = base / "embedded_version.txt"
            external.write_text("2.0.0\n", encoding="utf-8")
            embedded.write_text("1.0.0\n", encoding="utf-8")

            with patch.object(updater, "get_version_file", return_value=external):
                with patch.object(updater, "get_embedded_version_file", return_value=embedded):
                    self.assertEqual(updater.get_local_version(), "2.0.0")

    def test_get_local_version_falls_back_to_embedded_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            external = base / "external_version.txt"
            embedded = base / "embedded_version.txt"
            embedded.write_text("1.0.0\n", encoding="utf-8")

            with patch.object(updater, "get_version_file", return_value=external):
                with patch.object(updater, "get_embedded_version_file", return_value=embedded):
                    self.assertEqual(updater.get_local_version(), "1.0.0")

    def test_select_release_download_url_prefers_supported_assets(self) -> None:
        release_data = {
            "assets": [
                {
                    "name": "notes.txt",
                    "browser_download_url": "https://example.com/notes.txt",
                },
                {
                    "name": "MCModUpdater.V1.0.0.rar",
                    "browser_download_url": "https://example.com/release.rar",
                },
            ],
            "zipball_url": "https://example.com/source.zip",
        }

        self.assertEqual(
            updater._select_release_download_url(release_data),
            "https://example.com/release.rar",
        )

    def test_select_release_download_url_falls_back_to_zipball(self) -> None:
        release_data = {
            "assets": [],
            "zipball_url": "https://example.com/source.zip",
        }

        self.assertEqual(
            updater._select_release_download_url(release_data),
            "https://example.com/source.zip",
        )


if __name__ == "__main__":
    unittest.main()
