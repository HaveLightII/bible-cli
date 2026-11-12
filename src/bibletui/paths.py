"""資料目錄與原始碼根目錄的路徑判斷。"""

import os
import sys


def findSourceRoot():
    root = os.path.abspath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir
    ))
    if os.path.isfile(os.path.join(root, "pyproject.toml")) and os.path.isfile(
        os.path.join(root, "bible.py")
    ):
        return root
    return None


scriptDir = findSourceRoot()


def launchCommand(argv0=None, platform=None):
    if argv0 is None:
        argv0 = sys.argv[0] if sys.argv else ""
    python = "python" if (platform or sys.platform).startswith("win") else "python3"
    name = os.path.basename(argv0)
    if name == "bible.py":
        return f"{python} bible.py"
    if name == "__main__.py":
        return f"{python} -m bibletui"
    return "bible"

dataDirEnvName = "BIBLE_CLI_DATA_DIR"
appDirName = "bible-cli"


def userDataDir(platform=None, env=None, home=None):
    env = os.environ if env is None else env
    platform = platform or sys.platform
    home = home or os.path.expanduser("~")
    override = env.get(dataDirEnvName)
    if override:
        return os.path.abspath(os.path.expanduser(override))
    if platform.startswith("win"):
        base = env.get("APPDATA") or os.path.join(home, "AppData", "Roaming")
        return os.path.join(base, appDirName)
    if platform == "darwin":
        return os.path.join(home, "Library", "Application Support", appDirName)
    xdg = env.get("XDG_DATA_HOME")
    if not (xdg and os.path.isabs(xdg)):
        xdg = os.path.join(home, ".local", "share")
    return os.path.join(xdg, appDirName)
