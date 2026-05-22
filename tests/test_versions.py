import unittest

from versions import MINECRAFT_VERSIONS, SORTED_VERSIONS


class VersionDataTests(unittest.TestCase):
    def test_recent_release_versions_are_present(self) -> None:
        expected = {
            "1.7.3",
            "1.9.3",
            "1.10.1",
            "1.11.1",
            "1.21.6",
            "1.21.7",
            "1.21.8",
            "1.21.9",
            "1.21.10",
            "1.21.11",
            "26.1",
            "26.1.1",
            "26.1.2",
        }
        self.assertTrue(expected.issubset(MINECRAFT_VERSIONS))

    def test_removed_non_modrinth_release_is_absent(self) -> None:
        self.assertNotIn("1.5", MINECRAFT_VERSIONS)

    def test_sorted_versions_use_numeric_order(self) -> None:
        self.assertEqual(
            SORTED_VERSIONS,
            sorted(MINECRAFT_VERSIONS, key=lambda v: tuple(int(x) for x in v.split("."))),
        )


if __name__ == "__main__":
    unittest.main()
