"""和合本（含 Strong 標記）資料來源。"""

import re
from html import unescape

from ..books import zhBookNames

strongTagPattern = re.compile(r"<W([GH]\d*)>")

_noteBlock = re.compile(r"<RF[^>]*>.*?<Rf>", re.S)
_titleBlock = re.compile(r"<TS\d*>(.*?)<Ts>", re.S)
_otherTag = re.compile(r"<(?!W[GH]\d*>)/?[A-Za-z][^<>]*>")
_entity = re.compile(r"&(?:[A-Za-z][A-Za-z0-9]*|#[0-9]+|#[xX][0-9A-Fa-f]+);")
_spaceRun = re.compile(r" {2,}")


def prepareScripture(text, keepTitles=True):
    """去除 MySword 的格式標記，只保留 Strong 標記 <WG..>、<WH..>。

    譯註（RF）整段移除，標題（TS）改成〔標題〕或移除，其餘標記（斜體、
    耶穌的話、形態標記 WT、串珠 RX、HTML 標籤等）只去標記、留文字。
    不含任何其他標記時原樣回傳。
    """
    if "<" not in text and "&" not in text:
        return text
    out = _noteBlock.sub("", text)

    def title(m):
        body = m.group(1).strip()
        return f"〔{body}〕" if keepTitles and body else ""

    out = _titleBlock.sub(title, out)
    out = _otherTag.sub("", out)
    if out != text:
        out = _spaceRun.sub(" ", out).strip(" ")
    if "&" in out:
        out = _entity.sub(lambda m: unescape(m.group(0)), out)
    return out


def plainText(text, keepTitles=True):
    return strongTagPattern.sub("", prepareScripture(text, keepTitles))


class CuvSource:
    def __init__(self, conn):
        self.conn = conn
        self._plain = None
        self._folded = None

    def maxChapter(self, bookIndex):
        row = self.conn.execute(
            "SELECT MAX(Chapter) AS m FROM Bible WHERE Book=?", (bookIndex,)
        ).fetchone()
        return row["m"] or 1

    def chapterRows(self, bookIndex, chapter):
        return self.conn.execute(
            "SELECT Verse, Scripture FROM Bible WHERE Book=? AND Chapter=? ORDER BY Verse",
            (bookIndex, chapter),
        ).fetchall()

    def verseRaw(self, bookIndex, chapter, verse):
        return self.conn.execute(
            "SELECT Scripture FROM Bible WHERE Book=? AND Chapter=? AND Verse=?",
            (bookIndex, chapter, verse),
        ).fetchone()

    def plainVerses(self):
        if self._plain is None:
            rows = self.conn.execute(
                "SELECT Book, Chapter, Verse, Scripture FROM Bible ORDER BY Book, Chapter, Verse"
            ).fetchall()
            self._plain = [
                (r["Book"], r["Chapter"], r["Verse"],
                 plainText(r["Scripture"] or "", keepTitles=False))
                for r in rows
            ]
        return self._plain

    def foldedVerses(self):
        if self._folded is None:
            self._folded = [
                (b, c, v, t, " ".join(t.replace("\u3000", "").casefold().split()))
                for b, c, v, t in self.plainVerses()
            ]
        return self._folded

    def search(self, includeTerms, excludeTerms=()):
        def fold(t):
            return " ".join(t.replace("\u3000", "").casefold().split())

        include = [fold(t) for t in includeTerms]
        exclude = [fold(t) for t in excludeTerms]
        results = []
        for book, chapter, verse, text, flat in self.foldedVerses():
            if all(t in flat for t in include) and not any(t in flat for t in exclude):
                results.append({
                    "book_index": book,
                    "acr": zhBookNames[book - 1] if 1 <= book <= len(zhBookNames) else str(book),
                    "chapter": chapter,
                    "section": verse,
                    "content": text,
                })
        return results

