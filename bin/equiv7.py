import os
import subprocess
import sys

root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir))
sys.path.insert(0, os.path.join(root, "src"))

from bibletui import __version__
from bibletui.paths import launchCommand

assert launchCommand("/x/bible", "linux") == "bible"
assert launchCommand("C:\\Scripts\\bible.exe", "win32") == "bible"
assert launchCommand("/x/bible.py", "linux") == "python3 bible.py"
assert launchCommand("bible.py", "win32") == "python bible.py"
assert launchCommand("/x/bibletui/__main__.py", "linux") == "python3 -m bibletui"
assert launchCommand("-c", "linux") == "bible"
assert launchCommand("", "linux") == "bible"


def run(args):
    env = dict(os.environ, PYTHONPATH=os.path.join(root, "src"))
    return subprocess.run(
        [sys.executable] + args, capture_output=True, text=True, env=env,
        cwd=os.path.join(root, "bin"),
    )


for args in (
    [os.path.join(root, "bible.py"), "--version"],
    ["-m", "bibletui", "--version"],
):
    p = run(args)
    assert p.stdout.strip() == f"bible {__version__}", (args, p.stdout, p.stderr)

p = run([os.path.join(root, "bible.py"), "--help"])
assert "usage: python3 bible.py" in p.stdout or "usage: python bible.py" in p.stdout, p.stdout
p = run(["-m", "bibletui", "--help"])
assert "-m bibletui" in p.stdout, p.stdout
print("launch ok")
