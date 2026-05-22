import unittest

from main import extract_mod_name


class ExtractModNameTests(unittest.TestCase):
    def test_documented_examples(self) -> None:
        cases = {
            "sodium-fabric-0.5.8+mc1.21.jar": "sodium",
            "JourneyMap-1.21-5.10.0-fabric.jar": "journeymap",
            "bactromod-3.4.jar": "bactromod",
            "malilib-fabric-0.16.3+1.21.jar": "malilib",
            "Xaeros_Minimap_24.6.0_Forge_1.21.jar": "xaeros-minimap",
        }

        for filename, expected in cases.items():
            with self.subTest(filename=filename):
                self.assertEqual(extract_mod_name(filename), expected)

    def test_numeric_prefix_is_preserved(self) -> None:
        self.assertEqual(
            extract_mod_name("3dskinlayers-fabric-1.7.4.jar"),
            "3dskinlayers",
        )


if __name__ == "__main__":
    unittest.main()
