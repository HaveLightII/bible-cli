import os
import select
import shutil
import subprocess
import sys
import time
import unittest

import fixtures

hasPty = sys.platform != "win32"
if hasPty:
    import fcntl
    import pty
    import struct
    import termios


@unittest.skipUnless(hasPty, "偽終端機只在 POSIX 系統可用")
class TuiSmokeTests(fixtures.TempCase):
    def drive(self, args, keys, expect, timeout=20):
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 30, 100, 0, 0))
        env = dict(os.environ)
        env.update({
            "PYTHONPATH": fixtures.installedLikeSite(),
            "BIBLE_CLI_DATA_DIR": self.dataDir,
            "TERM": "xterm-256color",
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PYTHONIOENCODING": "utf-8",
        })
        proc = subprocess.Popen(
            [sys.executable, "-m", "bibletui"] + list(args),
            stdin=slave, stdout=slave, stderr=slave, env=env, cwd=self.work,
            close_fds=True,
        )
        os.close(slave)
        out = b""
        sent = False
        deadline = time.time() + timeout
        try:
            while time.time() < deadline:
                ready, _, _ = select.select([master], [], [], 0.2)
                if ready:
                    try:
                        chunk = os.read(master, 65536)
                    except OSError:
                        break
                    if not chunk:
                        break
                    out += chunk
                if not sent and expect.encode("utf-8") in out:
                    time.sleep(0.3)
                    os.write(master, keys)
                    sent = True
                if proc.poll() is not None and not ready:
                    break
            code = proc.wait(timeout=5)
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()
            os.close(master)
        return code, out.decode("utf-8", errors="replace")

    def test_startsInRecoveryAndQuits(self):
        self.makeAll()
        code, out = self.drive(["--db", self.dbPath], b"Q", "創世記")
        self.assertEqual(code, 0, out[-400:])
        self.assertIn("創世記", out)

    def test_startsInStrongWithoutRecoveryAndQuits(self):
        fixtures.makeCuvModule(self.cuvPath)
        fixtures.makeDictModule(self.dictPath)
        os.makedirs(self.dataDir)
        shutil.copy(self.cuvPath, self.dataDir)
        shutil.copy(self.dictPath, self.dataDir)
        code, out = self.drive([], b"Q", "創世記")
        self.assertEqual(code, 0, out[-400:])
        self.assertIn("創世記", out)

    def test_moduleCommandSwitchesAndPersists(self):
        os.makedirs(self.dataDir)
        fixtures.makeCuvModule(os.path.join(self.dataDir, "cuvt.bbl.mybible"))
        fixtures.makeGbfModule(os.path.join(self.dataDir, "eng.bbl.mybible"), "Eng/T")
        code, out = self.drive([], b":module eng\rQ", "創世記")
        self.assertEqual(code, 0, out[-400:])
        with open(os.path.join(self.dataDir, "config.json"), encoding="utf-8") as f:
            self.assertIn('"eng"', f.read())


if __name__ == "__main__":
    unittest.main()
