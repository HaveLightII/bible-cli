import gzip
import json
import os
import shutil
import sqlite3
import unittest
import zipfile

import fixtures
from bibletui import config, install as ins, modules
from bibletui.sources.cuv import CuvSource, plainText, prepareScripture


def readJson(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class TagCleaningTests(unittest.TestCase):
    def test_cuvTextUnchanged(self):
        raw = "測試<WH1>，\u3000詞<WH2>甲乙丙<WG3>。"
        self.assertEqual(prepareScripture(raw), raw)
        self.assertEqual(plainText(raw), "測試，\u3000詞甲乙丙。")
        self.assertEqual(plainText("第二節<WH>文字<WG0>庚辛。"), "第二節文字庚辛。")

    def test_gbfTagsRemoved(self):
        raw = "<TS>Sample Title<Ts><FI>Lorem<Fi> ipsum<RF>a note<Rf> dolor<WTN-NSF> sit<CM>"
        self.assertEqual(plainText(raw), "〔Sample Title〕Lorem ipsum dolor sit")
        self.assertEqual(plainText(raw, keepTitles=False), "Lorem ipsum dolor sit")
        self.assertEqual(
            plainText("Amet&nbsp;consectetur   <FR>adipiscing<Fr> elit<RX43.3.16>."),
            "Amet\u00a0consectetur adipiscing elit.",
        )

    def test_strongTagsSurviveWhenOtherTagsPresent(self):
        out = prepareScripture("<FI>In<Fi> the<WG3588> word<WG3056>")
        self.assertEqual(out, "In the<WG3588> word<WG3056>")


class GbfSearchTests(fixtures.TempCase):
    def test_caseAndWhitespaceInsensitive(self):
        path = os.path.join(self.files, "eng.bbl.mybible")
        fixtures.makeGbfModule(path)
        c = sqlite3.connect(path)
        c.row_factory = sqlite3.Row
        src = CuvSource(c)
        self.assertEqual([r["section"] for r in src.search(["PLAIN text"])], [3])
        self.assertEqual([r["section"] for r in src.search(["lorem", "dolor"])], [1])
        self.assertEqual(src.search(["lorem"], ["dolor"]), [])
        self.assertEqual(src.search(["a note"]), [])
        c.close()


class InstallZipTests(fixtures.TempCase):
    def setUp(self):
        super().setUp()
        self.dest = os.path.join(self.tmp, "dest")

    def makeZip(self, name, members):
        path = os.path.join(self.files, name)
        with zipfile.ZipFile(path, "w") as z:
            for arcname, src in members:
                z.write(src, arcname)
        return path

    def test_singleMemberZip(self):
        src = os.path.join(self.files, "kjv.bbl.mybible")
        fixtures.makeGbfModule(src, "KJV")
        z = self.makeZip("kjv.bbl.mybible.zip", [("kjv.bbl.mybible", src)])
        results = ins.installMany(z, self.dest)
        self.assertEqual([r[0] for r in results], ["installed"])
        self.assertEqual(os.listdir(self.dest), ["kjv.bbl.mybible"])
        self.assertEqual(ins.installOne(z, self.dest)[0], "skipped")

    def test_multiMemberZipAndPathTraversal(self):
        a = os.path.join(self.files, "a.bbl.mybible")
        fixtures.makeGbfModule(a, "A")
        d = os.path.join(self.files, "d.dct.mybible")
        fixtures.makeDictModule(d)
        z = self.makeZip("pack.zip", [("x/../../evil.bbl.mybible", a), ("sub/d.dct.mybible", d)])
        results = ins.installMany(z, self.dest)
        self.assertEqual([r[0] for r in results], ["installed", "installed"])
        self.assertEqual(sorted(os.listdir(self.dest)), ["d.dct.mybible", "evil.bbl.mybible"])
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "evil.bbl.mybible")))
        self.assertEqual(ins.installOne(z, self.dest)[0], "error")

    def test_badZipAndEmptyZip(self):
        junk = os.path.join(self.files, "junk.zip")
        with open(junk, "wb") as f:
            f.write(b"not a zip")
        self.assertEqual(ins.installMany(junk, self.dest)[0][0], "error")
        txt = os.path.join(self.files, "a.txt")
        with open(txt, "w") as f:
            f.write("x")
        z = self.makeZip("empty.zip", [("a.txt", txt)])
        status, msg = ins.installMany(z, self.dest)[0]
        self.assertEqual(status, "error")
        self.assertIn("沒有 .mybible", msg)
        self.assertEqual(os.listdir(self.dest) if os.path.isdir(self.dest) else [], [])

    def test_zipMemberNotSqliteLeavesNothing(self):
        bad = os.path.join(self.files, "bad.bbl.mybible")
        with open(bad, "wb") as f:
            f.write(b"junk")
        z = self.makeZip("bad.zip", [("bad.bbl.mybible", bad)])
        self.assertEqual(ins.installMany(z, self.dest)[0][0], "error")
        self.assertEqual([n for n in os.listdir(self.dest)], [])

    def test_suffixKindMismatchRefused(self):
        wrong = os.path.join(self.files, "x.bbl.mybible")
        fixtures.makeDictModule(wrong)
        status, msg = ins.installOne(wrong, self.dest)
        self.assertEqual(status, "error")
        self.assertIn("不是聖經模組", msg)
        wrong2 = os.path.join(self.files, "y.dct.mybible")
        fixtures.makeCuvModule(wrong2)
        self.assertIn("不是字典模組", ins.installOne(wrong2, self.dest)[1])

    def test_findInstallable(self):
        for name in ("kjv.bbl.mybible.zip", "web.bbl.mybible.gz", "s.dct.mybible", "readme.txt", "x.cmt.mybible"):
            with open(os.path.join(self.files, name), "wb") as f:
                f.write(b"x")
        found = [os.path.basename(p) for p in ins.findInstallable(self.files)]
        self.assertEqual(found, ["kjv.bbl.mybible.zip", "s.dct.mybible", "web.bbl.mybible.gz"])


class ModuleCliTests(fixtures.TempCase):
    def setUp(self):
        super().setUp()
        os.makedirs(self.dataDir)
        fixtures.makeCuvModule(os.path.join(self.dataDir, "cuvt.bbl.mybible"))
        fixtures.makeGbfModule(os.path.join(self.dataDir, "eng.bbl.mybible"), "Eng/T")
        fixtures.makeDictModule(os.path.join(self.dataDir, "strong_lite.dct.mybible"))

    def test_listMarksCurrent(self):
        p = self.run_(["data", "list"])
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("* cuvt", p.stdout)
        self.assertIn("  eng ［Eng/T］", p.stdout)
        self.assertIn("* strong_lite", p.stdout)
        self.assertIn("Strong：無", p.stdout)

    def test_useSwitchesDefault(self):
        p = self.run_(["data", "use", "ENG/T"])
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(readJson(os.path.join(self.dataDir, "config.json"))["defaultBible"], "eng")
        p = self.run_(["read", "創", "1:3", "--no-color"])
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("Text Verse", p.stdout)
        self.assertIn("* eng", self.run_(["data", "list"]).stdout)
        p = self.run_(["data", "use", "--reset"])
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("甲乙丙", self.run_(["read", "創", "1:1", "--no-color"]).stdout)

    def test_moduleOptionDoesNotChangeDefault(self):
        p = self.run_(["read", "創", "1:1", "--module", "eng", "--no-color"])
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("〔Sample Title〕Lorem ipsum dolor sit", p.stdout)
        self.assertNotIn("<", p.stdout)
        self.assertFalse(os.path.exists(os.path.join(self.dataDir, "config.json")))
        p = self.run_(["search", "ELIT", "-m", "eng"])
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("1:2", p.stdout)

    def test_envOverridesConfig(self):
        self.run_(["data", "use", "eng"])
        env = {"BIBLE_STRONG_BIBLE": os.path.join(self.dataDir, "cuvt.bbl.mybible")}
        p = self.run_(["data", "use", "eng"], extraEnv=env)
        self.assertIn("蓋過", p.stdout)

    def test_unknownAndAmbiguous(self):
        p = self.run_(["read", "創", "1:1", "--module", "nope"])
        self.assertEqual(p.returncode, 1)
        self.assertIn("找不到資料庫", p.stderr)
        p = self.run_(["read", "創", "1:1", "--module", "x", "--source", "recovery"])
        self.assertEqual(p.returncode, 2)
        fixtures.makeDictModule(os.path.join(self.dataDir, "eng.dct.mybible"))
        p = self.run_(["data", "use", "eng"])
        self.assertEqual(p.returncode, 1)
        self.assertIn("eng.bbl", p.stderr)
        self.assertEqual(self.run_(["data", "use", "eng.bbl"]).returncode, 0)

    def test_origNeedsStrongModule(self):
        p = self.run_(["orig", "創", "1:1", "--module", "eng"])
        self.assertEqual(p.returncode, 1)
        self.assertIn("不含 Strong", p.stderr)
        p = self.run_(["orig", "創", "1:1"])
        self.assertEqual(p.returncode, 0, p.stderr)

    def test_uninstall(self):
        self.run_(["data", "use", "eng"])
        p = self.run_(["data", "uninstall", "eng"])
        self.assertEqual(p.returncode, 1)
        self.assertIn("--yes", p.stderr)
        self.assertTrue(os.path.isfile(os.path.join(self.dataDir, "eng.bbl.mybible")))
        p = self.run_(["data", "uninstall", "eng", "--yes"])
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.dataDir, "eng.bbl.mybible")))
        self.assertNotIn("defaultBible", readJson(os.path.join(self.dataDir, "config.json")))
        self.assertIn("甲乙丙", self.run_(["read", "創", "1:1", "--no-color"]).stdout)
        p = self.run_(["data", "uninstall", "eng", "-y"])
        self.assertEqual(p.returncode, 1)

    def test_uninstallRefusesOutsideUserDir(self):
        fixtures.makeGbfModule(os.path.join(self.work, "loose.bbl.mybible"), "Loose")
        p = self.run_(["data", "uninstall", "loose", "-y"])
        self.assertEqual(p.returncode, 1)
        self.assertIn("使用者資料目錄之外", p.stderr)
        self.assertTrue(os.path.isfile(os.path.join(self.work, "loose.bbl.mybible")))

    def test_installZipThenUse(self):
        src = os.path.join(self.files, "web.bbl.mybible")
        fixtures.makeGbfModule(src, "WEB")
        zpath = src + ".zip"
        with zipfile.ZipFile(zpath, "w") as z:
            z.write(src, "web.bbl.mybible")
        p = self.run_(["data", "install", "--from-dir", self.files])
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("data use", p.stdout)
        self.assertEqual(self.run_(["data", "use", "web"]).returncode, 0)
        self.assertIn("Text Verse", self.run_(["read", "創", "1:3", "--no-color"]).stdout)

    def test_corruptConfigIgnored(self):
        with open(os.path.join(self.dataDir, "config.json"), "w") as f:
            f.write("{broken")
        self.assertIn("甲乙丙", self.run_(["read", "創", "1:1", "--no-color"]).stdout)


class DefaultSelectionTests(fixtures.TempCase):
    def test_preferCuvtOverAlphabeticalFirst(self):
        os.makedirs(self.dataDir)
        fixtures.makeGbfModule(os.path.join(self.dataDir, "asv.bbl.mybible"), "ASV")
        fixtures.makeCuvModule(os.path.join(self.dataDir, "cuvt.bbl.mybible"))
        p = self.run_(["read", "創", "1:1", "--no-color"])
        self.assertIn("甲乙丙", p.stdout)

    def test_preferCuvtAcrossSearchDirs(self):
        os.makedirs(self.dataDir)
        fixtures.makeGbfModule(os.path.join(self.dataDir, "asv.bbl.mybible"), "ASV")
        fixtures.makeCuvModule(os.path.join(self.work, "cuvt.bbl.mybible"))
        p = self.run_(["read", "創", "1:1", "--no-color"])
        self.assertIn("甲乙丙", p.stdout)

    def test_moduleIdFromFile(self):
        self.assertEqual(modules.moduleIdFromFile("cuvt.bbl.mybible"), "cuvt")
        self.assertEqual(modules.moduleIdFromFile("Strong_Lite.DCT.mybible"), "Strong_Lite")
        self.assertEqual(modules.moduleIdFromFile("plain.mybible"), "plain")


class SwitchStubTests(fixtures.TempCase):
    def test_switchResetsState(self):
        from bibletui.tui.modules import ModuleMixin
        from bibletui.tui.world import World

        class Stub(ModuleMixin):
            def __init__(self, path):
                self.strongConn = None
                self.strongBiblePath = None
                self.hasStrongBible = False
                self.strongModuleLabel = ""
                self._cuvSearchSource = object()
                self._strongWordCodes = {1: 2}
                self.mode = "strong_read"
                self.searchKind = "strong"
                self.searchQuery = "x"
                self.searchInputText = "x"
                self.searchResults = [1]
                self.searchScroll = 3
                self.searchIdx = 2
                self.statusMessage = None
                w = World("strong", [], "t", "", "a", "b", "m1", "m2", "m3", (27,))
                w.selectedBookIndex, w.selectedChapter = 43, 3
                w.readLines = ["old"]
                self.strongWorld = w

            def _openStrongConn(self):
                if self.strongConn is None and self.strongBiblePath:
                    self.strongConn = sqlite3.connect(self.strongBiblePath)
                    self.strongConn.row_factory = sqlite3.Row
                return self.strongConn

        os.makedirs(self.dataDir)
        os.environ["BIBLE_CLI_DATA_DIR"] = self.dataDir
        self.addCleanup(os.environ.pop, "BIBLE_CLI_DATA_DIR", None)
        path = os.path.join(self.dataDir, "eng.bbl.mybible")
        fixtures.makeGbfModule(path, "Eng/T", ot=1, nt=0)
        info = modules.findModule("eng", modules.scanModules([self.dataDir]))
        app = Stub(path)
        app._switchStrongModule(info)
        self.assertEqual(app.strongModuleLabel, "Eng/T")
        self.assertIsNone(app._cuvSearchSource)
        self.assertEqual(app.searchResults, [])
        self.assertEqual(app.strongWorld.readLines, [])
        self.assertIn("已切換", app.statusMessage)
        self.assertEqual(config.getDefaultId("bible"), "eng")
        app.strongConn.close()


if __name__ == "__main__":
    unittest.main()
