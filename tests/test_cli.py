import os
import shutil
import unittest

import fixtures


class CliBase(fixtures.TempCase):
    def putModules(self):
        os.makedirs(self.dataDir, exist_ok=True)
        shutil.copy(self.cuvPath, self.dataDir)
        shutil.copy(self.dictPath, self.dataDir)

    def withRecovery(self, *args):
        return ["--db", self.dbPath] + list(args)


class RecoveryTests(CliBase):
    def setUp(self):
        super().setUp()
        self.makeAll()
        self.putModules()

    def test_version(self):
        p = self.run_(["--version"])
        self.assertEqual(p.returncode, 0)
        self.assertRegex(p.stdout.strip(), r"^bible \d+\.\d+\.\d+$")

    def test_readDefaultsToRecovery(self):
        p = self.run_(self.withRecovery("read", "創世記", "1", "--no-color"))
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("恢復本測試甲乙丙1", p.stdout.replace("恢1復本", "恢復本"))
        self.assertIn("測試綱目", p.stdout)

    def test_readNoOutline(self):
        p = self.run_(self.withRecovery("read", "創", "1:2", "--no-outline", "--no-color"))
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("恢復本測試甲乙丙2", p.stdout)
        self.assertNotIn("測試綱目", p.stdout)

    def test_readWithEnglish(self):
        p = self.run_(self.withRecovery("read", "Genesis", "1:1", "--en", "--no-color"))
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("english test line 1", p.stdout)

    def test_sourceCuvOverridesRecovery(self):
        p = self.run_(self.withRecovery("read", "創", "1:2", "--source", "cuv", "--no-color"))
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("第二節文字庚辛。", p.stdout)
        self.assertNotIn("<WH>", p.stdout)

    def test_searchRecoveryAndCuv(self):
        p = self.run_(self.withRecovery("search", "甲乙丙"))
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stdout.count("甲乙丙"), 3)
        p = self.run_(self.withRecovery("search", "甲乙丙", "--source", "cuv"))
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("約翰福音 3:1", p.stdout)

    def test_searchNoMatch(self):
        p = self.run_(self.withRecovery("search", "不存在的詞語"))
        self.assertEqual(p.returncode, 0)
        self.assertIn("沒有找到符合的經文", p.stdout)

    def test_cuvSearchIgnoresFullWidthSpace(self):
        p = self.run_(self.withRecovery("search", "，詞甲", "--source", "cuv"))
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("創世記 1:1", p.stdout)

    def test_listAndTestament(self):
        p = self.run_(self.withRecovery("list", "舊約"))
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(len([l for l in p.stdout.splitlines() if l.strip()]), 39)
        p = self.run_(self.withRecovery("list", "新約"))
        self.assertEqual(len([l for l in p.stdout.splitlines() if l.strip()]), 27)

    def test_introAndNote(self):
        p = self.run_(self.withRecovery("intro", "創世記"))
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("測試簡介", p.stdout)
        p = self.run_(self.withRecovery("note", "創世記", "1:1", "1"))
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("測試註解", p.stdout)

    def test_unknownBookAndChapter(self):
        p = self.run_(self.withRecovery("read", "不存在的書", "1"))
        self.assertEqual(p.returncode, 1)
        self.assertIn("找不到書卷", p.stderr)
        p = self.run_(self.withRecovery("read", "創世記", "99", "--no-color"))
        self.assertNotEqual(p.returncode, 0)

    def test_strongAndOrig(self):
        p = self.run_(["strong", "G26"])
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("測試字義", p.stdout)
        p = self.run_(["orig", "創世記", "1:1", "--word", "1"])
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("甲乙丙[3]", p.stdout)

    def test_dataSubcommandListsDetection(self):
        p = self.run_(self.withRecovery("data"))
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn(self.dbPath, p.stdout)
        self.assertIn("cuvt.bbl.mybible", p.stdout)


class CuvOnlyTests(CliBase):
    def setUp(self):
        super().setUp()
        fixtures.makeCuvModule(self.cuvPath)
        fixtures.makeDictModule(self.dictPath)
        self.putModules()

    def test_defaultsToCuvWithoutRecovery(self):
        p = self.run_(["read", "創", "1:1", "--no-color"])
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("測試，　詞甲乙丙。", p.stdout)

    def test_aliasBookNames(self):
        for name in ("創", "gen", "Genesis", "1"):
            p = self.run_(["read", name, "1:2", "--no-color"])
            self.assertEqual(p.returncode, 0, (name, p.stderr))
            self.assertIn("第二節文字庚辛。", p.stdout)

    def test_searchAndList(self):
        p = self.run_(["search", "甲乙丙"])
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("約翰福音 3:1", p.stdout)
        p = self.run_(["list", "新約"])
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(len([l for l in p.stdout.splitlines() if l.strip()]), 27)

    def test_unsupportedOptionsExitCode2(self):
        for extra in (["--en"], ["--no-outline"], ["--no-footnote"]):
            p = self.run_(["read", "創", "1:1"] + extra)
            self.assertEqual(p.returncode, 2, (extra, p.stderr))
            self.assertIn("此資料來源不含此內容", p.stderr)
        p = self.run_(["search", "甲乙丙", "--lang", "eng"])
        self.assertEqual(p.returncode, 2, p.stderr)

    def test_recoveryOnlyCommandsExitCode1(self):
        for args in (["intro", "創世記"], ["note", "創世記", "1:1", "1"], ["read", "創", "1:1", "--source", "recovery"]):
            p = self.run_(args)
            self.assertEqual(p.returncode, 1, (args, p.stderr))
            self.assertIn("恢復本", p.stderr)


class NoDataTests(CliBase):
    def test_noDatabaseMessage(self):
        p = self.run_(["read", "創", "1:1"])
        self.assertEqual(p.returncode, 1)
        self.assertIn("找不到可用的聖經資料庫", p.stderr)
        self.assertIn("data install", p.stderr)

    def test_dataWorksWithoutFiles(self):
        p = self.run_(["data"])
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("使用者資料目錄", p.stdout)


if __name__ == "__main__":
    unittest.main()
