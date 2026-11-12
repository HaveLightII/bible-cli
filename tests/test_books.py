import unittest

import fixtures  # noqa: F401  (設定 sys.path)
from bibletui import books


class BookNameTests(unittest.TestCase):
    def test_tableSizes(self):
        self.assertEqual(len(books.zhBookNames), 66)
        self.assertEqual(len(books.enBookNames), 66)
        self.assertEqual(len(books.bookAliasZh), 66)
        self.assertEqual(len(books.bookAliasEn), 66)

    def test_fullNamesResolve(self):
        for i, name in enumerate(books.zhBookNames, start=1):
            self.assertEqual(books.resolveAnyBookName(name, None), i, name)
        for i, name in enumerate(books.enBookNames, start=1):
            self.assertEqual(books.resolveAnyBookName(name, None), i, name)

    def test_numbersResolve(self):
        self.assertEqual(books.resolveAnyBookName("1", None), 1)
        self.assertEqual(books.resolveAnyBookName("66", None), 66)
        self.assertIsNone(books.resolveAnyBookName("67", None))

    def test_aliasesResolveToOwnBook(self):
        for i, alias in enumerate(books.bookAliasZh, start=1):
            self.assertEqual(books.resolveAnyBookName(alias, None), i, alias)
        for i, group in enumerate(books.bookAliasEn, start=1):
            for alias in group:
                self.assertEqual(books.resolveAnyBookName(alias, None), i, alias)

    def test_englishAliasesDoNotCollide(self):
        seen = {}
        for i, group in enumerate(books.bookAliasEn, start=1):
            for alias in group:
                key = books._normBookKey(alias)
                self.assertNotIn(key, seen, f"{alias} 與第 {seen.get(key)} 卷衝突")
                seen[key] = i

    def test_normalizesSpacesAndPeriods(self):
        cases = {"Gen.": 1, "1 Sam.": 9, "1 Chron.": 13, "S.S.": 22, "Philem.": 57, "1 Thes.": 52, "Rev.": 66, "gen": 1}
        for text, index in cases.items():
            self.assertEqual(books.resolveAnyBookName(text, None), index, text)

    def test_johnEpistles(self):
        self.assertEqual(books.resolveAnyBookName("約壹", None), 62)
        self.assertEqual(books.resolveAnyBookName("約二", None), 63)
        self.assertEqual(books.resolveAnyBookName("猶", None), 65)

    def test_ambiguousAndUnknownReturnNone(self):
        self.assertIsNone(books.resolveAnyBookName("約翰", None))
        self.assertIsNone(books.resolveAnyBookName("不存在的書", None))


if __name__ == "__main__":
    unittest.main()
