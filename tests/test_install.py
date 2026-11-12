import os
import sqlite3
import unittest

import fixtures
from bibletui import install as ins


def makeDb(path, tables):
    c = sqlite3.connect(path)
    for t in tables:
        c.execute(f"CREATE TABLE {t} (x)")
    c.commit()
    c.close()


class InstallUnitTests(fixtures.TempCase):
    def setUp(self):
        super().setUp()
        self.dest = os.path.join(self.tmp, "dest")

    def test_matchKnownName(self):
        self.assertEqual(ins.matchKnownName("cuvt_bbl.mybible"), "cuvt.bbl.mybible")
        self.assertEqual(ins.matchKnownName("Strong_Lite.dct.mybible"), "strong_lite.dct.mybible")
        self.assertEqual(ins.matchKnownName("bible.db"), "bible.db")
        self.assertIsNone(ins.matchKnownName("other.db"))

    def test_strictHashMismatchRefusedUnlessForced(self):
        fake = os.path.join(self.files, "cuvt.bbl.mybible")
        makeDb(fake, ["Bible"])
        status, msg = ins.installOne(fake, self.dest)
        self.assertEqual(status, "error")
        self.assertIn("SHA-256 不符", msg)
        self.assertFalse(os.path.exists(self.dest))
        status, _ = ins.installOne(fake, self.dest, force=True)
        self.assertEqual(status, "installed")
        self.assertTrue(os.path.isfile(os.path.join(self.dest, "cuvt.bbl.mybible")))
        self.assertEqual([n for n in os.listdir(self.dest) if n.endswith(".part")], [])
        self.assertEqual(ins.installOne(fake, self.dest)[0], "skipped")

    def test_differentContentNeedsForce(self):
        a = os.path.join(self.files, "cuvt.bbl.mybible")
        makeDb(a, ["Bible"])
        ins.installOne(a, self.dest, force=True)
        other = os.path.join(self.files, "other", "cuvt.bbl.mybible")
        os.makedirs(os.path.dirname(other))
        makeDb(other, ["Bible", "Details"])
        self.assertEqual(ins.installOne(other, self.dest)[0], "error")
        self.assertEqual(ins.installOne(other, self.dest, force=True)[0], "installed")

    def test_customModuleAndJunk(self):
        custom = os.path.join(self.files, "my.bbl.mybible")
        makeDb(custom, ["Bible"])
        self.assertEqual(ins.installOne(custom, self.dest)[0], "installed")
        self.assertTrue(os.path.isfile(os.path.join(self.dest, "my.bbl.mybible")))
        junk = os.path.join(self.files, "junk.mybible")
        with open(junk, "w") as f:
            f.write("not sqlite")
        self.assertEqual(ins.installOne(junk, self.dest)[0], "error")
        self.assertEqual(ins.installOne(os.path.join(self.files, "nope.txt"), self.dest)[0], "error")

    def test_recoveryDbChecks(self):
        bad = os.path.join(self.files, "bible.db")
        makeDb(bad, ["foo"])
        status, msg = ins.installOne(bad, self.dest)
        self.assertEqual(status, "error")
        self.assertIn("不是恢復本", msg)
        os.remove(bad)
        good = os.path.join(self.files, "bible_db")
        makeDb(good, ["content", "book_name"])
        status, msg = ins.installOne(good, self.dest)
        self.assertEqual(status, "installed")
        self.assertIn("作者版本不同", msg)
        self.assertTrue(os.path.isfile(os.path.join(self.dest, "bible.db")))

    def test_findInDir(self):
        makeDb(os.path.join(self.files, "bible_db"), ["content", "book_name"])
        makeDb(os.path.join(self.files, "cuvt.bbl.mybible"), ["Bible"])
        found = [os.path.basename(p) for p in ins.findInDir(self.files)]
        self.assertEqual(found, ["bible_db", "cuvt.bbl.mybible"])
        self.assertEqual(ins.findInDir(os.path.join(self.tmp, "missing")), [])


class InstallCliTests(fixtures.TempCase):
    def test_installThenRead(self):
        fixtures.makeCuvModule(os.path.join(self.files, "cuvt_bbl.mybible"))
        fixtures.makeDictModule(os.path.join(self.files, "strong_lite.dct.mybible"))
        p = self.run_(["data", "install", "--from-dir", self.files])
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.dataDir, "cuvt.bbl.mybible")))
        p = self.run_(["data", "install", "--from-dir", self.files, "--force"])
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertTrue(os.path.isfile(os.path.join(self.dataDir, "cuvt.bbl.mybible")))
        self.assertTrue(os.path.isfile(os.path.join(self.dataDir, "strong_lite.dct.mybible")))
        p = self.run_(["read", "創", "1:1", "--no-color"])
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("甲乙丙", p.stdout)
        p = self.run_(["data", "install", "--from-dir", self.files, "--force"])
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_noSourceExitCode2(self):
        p = self.run_(["data", "install"])
        self.assertEqual(p.returncode, 2, p.stderr)
        empty = os.path.join(self.tmp, "empty")
        os.makedirs(empty)
        p = self.run_(["data", "install", "--from-dir", empty])
        self.assertEqual(p.returncode, 2, p.stderr)


if __name__ == "__main__":
    unittest.main()
