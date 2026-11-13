import gzip
import os
import sqlite3
import unittest
from unittest import mock

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
        self.assertEqual(ins.matchKnownName("cuvt.bbl.mybible.gz"), "cuvt.bbl.mybible")
        self.assertEqual(ins.matchKnownName("CUVT_bbl.mybible.GZ"), "cuvt.bbl.mybible")
        self.assertEqual(ins.matchKnownName("cuvt.bbl.mybible.zip"), "cuvt.bbl.mybible")

    def gzipFile(self, path):
        gzPath = path + ".gz"
        with open(path, "rb") as fin, gzip.open(gzPath, "wb") as fout:
            fout.write(fin.read())
        return gzPath

    def test_hashMismatchWarnsButInstalls(self):
        fake = os.path.join(self.files, "cuvt.bbl.mybible")
        makeDb(fake, ["Bible"])
        status, msg = ins.installOne(fake, self.dest)
        self.assertEqual(status, "installed")
        self.assertIn("SHA-256 與作者版本不同", msg)
        self.assertTrue(os.path.isfile(os.path.join(self.dest, "cuvt.bbl.mybible")))
        self.assertEqual([n for n in os.listdir(self.dest) if n.endswith(".part")], [])
        self.assertEqual(ins.installOne(fake, self.dest)[0], "skipped")

    def test_wrongKindRefused(self):
        notBible = os.path.join(self.files, "cuvt.bbl.mybible")
        makeDb(notBible, ["dictionary"])
        status, msg = ins.installOne(notBible, self.dest)
        self.assertEqual(status, "error")
        self.assertIn("不是和合本", msg)
        notDict = os.path.join(self.files, "other", "strong_lite.dct.mybible")
        os.makedirs(os.path.dirname(notDict))
        makeDb(notDict, ["Bible"])
        status, msg = ins.installOne(notDict, self.dest)
        self.assertEqual(status, "error")
        self.assertIn("不是Strong 字典", msg)
        self.assertFalse(os.path.exists(self.dest))

    def test_gzInstall(self):
        src = os.path.join(self.files, "cuvt.bbl.mybible")
        fixtures.makeCuvModule(src)
        gzPath = self.gzipFile(src)
        os.remove(src)
        status, msg = ins.installOne(gzPath, self.dest)
        self.assertEqual(status, "installed", msg)
        dest = os.path.join(self.dest, "cuvt.bbl.mybible")
        self.assertTrue(os.path.isfile(dest))
        self.assertEqual(os.listdir(self.dest), ["cuvt.bbl.mybible"])
        c = sqlite3.connect(dest)
        self.assertEqual(c.execute("SELECT COUNT(*) FROM Bible").fetchone()[0], 4)
        c.close()
        self.assertEqual(ins.installOne(gzPath, self.dest)[0], "skipped")
        self.assertEqual(os.listdir(self.dest), ["cuvt.bbl.mybible"])

    def test_gzBadContentLeavesNothing(self):
        junk = os.path.join(self.files, "cuvt.bbl.mybible.gz")
        with gzip.open(junk, "wb") as f:
            f.write(b"not sqlite")
        status, msg = ins.installOne(junk, self.dest)
        self.assertEqual(status, "error")
        self.assertEqual(os.listdir(self.dest), [])
        truncated = os.path.join(self.files, "strong_lite.dct.mybible.gz")
        src = os.path.join(self.files, "strong_lite.dct.mybible")
        fixtures.makeDictModule(src)
        full = self.gzipFile(src)
        with open(full, "rb") as f:
            data = f.read()
        with open(truncated, "wb") as f:
            f.write(data[:len(data) // 2])
        status, msg = ins.installOne(truncated, self.dest)
        self.assertEqual(status, "error")
        self.assertIn("解壓縮失敗", msg)
        self.assertEqual(os.listdir(self.dest), [])

    def test_sniffAndHasTablesCloseConnectionOnError(self):
        junk = os.path.join(self.tmp, "junk.db")
        with open(junk, "wb") as f:
            f.write(b"not sqlite")
        opened = []
        real = sqlite3.connect

        def spy(*args, **kwargs):
            c = real(*args, **kwargs)
            opened.append(c)
            return c

        with mock.patch.object(sqlite3, "connect", spy):
            self.assertIsNone(ins._sniffMybibleKind(junk))
            self.assertFalse(ins.hasTables(junk, ["Bible"]))
        self.assertEqual(len(opened), 2)
        for c in opened:
            with self.assertRaises(sqlite3.ProgrammingError):
                c.execute("SELECT 1")
        os.remove(junk)

    def test_gzCustomModuleKeepsName(self):
        custom = os.path.join(self.files, "my.bbl.mybible")
        makeDb(custom, ["Bible"])
        gzPath = self.gzipFile(custom)
        status, _ = ins.installOne(gzPath, self.dest)
        self.assertEqual(status, "installed")
        self.assertEqual(os.listdir(self.dest), ["my.bbl.mybible"])

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
        with open(os.path.join(self.files, "strong_lite.dct.mybible.gz"), "wb") as f:
            f.write(b"x")
        found = [os.path.basename(p) for p in ins.findInDir(self.files)]
        self.assertEqual(found, ["bible_db", "cuvt.bbl.mybible", "strong_lite.dct.mybible.gz"])
        self.assertEqual(ins.findInDir(os.path.join(self.tmp, "missing")), [])


class InstallCliTests(fixtures.TempCase):
    def test_installThenRead(self):
        fixtures.makeCuvModule(os.path.join(self.files, "cuvt_bbl.mybible"))
        fixtures.makeDictModule(os.path.join(self.files, "strong_lite.dct.mybible"))
        p = self.run_(["data", "install", "--from-dir", self.files])
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("SHA-256 與作者版本不同", p.stdout)
        self.assertTrue(os.path.isfile(os.path.join(self.dataDir, "cuvt.bbl.mybible")))
        self.assertTrue(os.path.isfile(os.path.join(self.dataDir, "strong_lite.dct.mybible")))
        p = self.run_(["read", "創", "1:1", "--no-color"])
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("甲乙丙", p.stdout)
        p = self.run_(["data", "install", "--from-dir", self.files])
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("略過", p.stdout)

    def test_installGzThenRead(self):
        src = os.path.join(self.files, "cuvt.bbl.mybible")
        fixtures.makeCuvModule(src)
        gzPath = src + ".gz"
        with open(src, "rb") as fin, gzip.open(gzPath, "wb") as fout:
            fout.write(fin.read())
        os.remove(src)
        p = self.run_(["data", "install", "--from-file", gzPath])
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(os.listdir(self.dataDir), ["cuvt.bbl.mybible"])
        p = self.run_(["read", "創", "1:1", "--no-color"])
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("甲乙丙", p.stdout)
        p = self.run_(["data", "install", "--from-dir", self.files])
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("略過", p.stdout)

    def test_noSourceExitCode2(self):
        p = self.run_(["data", "install"])
        self.assertEqual(p.returncode, 2, p.stderr)
        empty = os.path.join(self.tmp, "empty")
        os.makedirs(empty)
        p = self.run_(["data", "install", "--from-dir", empty])
        self.assertEqual(p.returncode, 2, p.stderr)


if __name__ == "__main__":
    unittest.main()
