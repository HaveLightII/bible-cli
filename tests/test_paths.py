import os
import unittest

import fixtures  # noqa: F401
from bibletui import __version__
from bibletui.paths import launchCommand, userDataDir


class UserDataDirTests(unittest.TestCase):
    def test_envOverrideWins(self):
        got = userDataDir("linux", {"BIBLE_CLI_DATA_DIR": "/x/y"}, "/home/u")
        self.assertEqual(got, os.path.abspath("/x/y"))

    def test_linuxDefaultAndXdg(self):
        self.assertEqual(
            userDataDir("linux", {}, "/home/u"),
            os.path.join("/home/u", ".local", "share", "bible-cli"),
        )
        self.assertEqual(
            userDataDir("linux", {"XDG_DATA_HOME": "/data"}, "/home/u"),
            os.path.join("/data", "bible-cli"),
        )

    def test_relativeXdgIgnored(self):
        self.assertEqual(
            userDataDir("linux", {"XDG_DATA_HOME": "relative"}, "/home/u"),
            os.path.join("/home/u", ".local", "share", "bible-cli"),
        )

    def test_macos(self):
        self.assertEqual(
            userDataDir("darwin", {}, "/Users/u"),
            os.path.join("/Users/u", "Library", "Application Support", "bible-cli"),
        )

    def test_windows(self):
        self.assertEqual(
            userDataDir("win32", {"APPDATA": "C:\\AppData"}, "C:\\Users\\u"),
            os.path.join("C:\\AppData", "bible-cli"),
        )
        self.assertEqual(
            userDataDir("win32", {}, "C:\\Users\\u"),
            os.path.join("C:\\Users\\u", "AppData", "Roaming", "bible-cli"),
        )


class LaunchCommandTests(unittest.TestCase):
    def test_variants(self):
        self.assertEqual(launchCommand("/x/bible", "linux"), "bible")
        self.assertEqual(launchCommand("C:\\Scripts\\bible.exe", "win32"), "bible")
        self.assertEqual(launchCommand("/x/bible.py", "linux"), "python3 bible.py")
        self.assertEqual(launchCommand("bible.py", "win32"), "python bible.py")
        self.assertEqual(launchCommand("/x/bibletui/__main__.py", "linux"), "python3 -m bibletui")
        self.assertEqual(launchCommand("-c", "linux"), "bible")
        self.assertEqual(launchCommand("", "linux"), "bible")


class VersionTests(unittest.TestCase):
    def test_versionFormat(self):
        parts = __version__.split(".")
        self.assertEqual(len(parts), 3)
        self.assertTrue(all(p.isdigit() for p in parts))


if __name__ == "__main__":
    unittest.main()
