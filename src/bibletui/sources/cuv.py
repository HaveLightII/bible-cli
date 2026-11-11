"""和合本（含 Strong 標記）資料來源。"""

import re

from ..books import zhBookNames


class CuvSource:
    def __init__(self, conn):
        self.conn = conn
        self._plain = None

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
                (r["Book"], r["Chapter"], r["Verse"], strongTagPattern.sub("", r["Scripture"]))
                for r in rows
            ]
        return self._plain

    def search(self, includeTerms, excludeTerms=()):
        include = [t.replace("\u3000", "") for t in includeTerms]
        exclude = [t.replace("\u3000", "") for t in excludeTerms]
        results = []
        for book, chapter, verse, text in self.plainVerses():
            flat = text.replace("\u3000", "")
            if all(t in flat for t in include) and not any(t in flat for t in exclude):
                results.append({
                    "book_index": book,
                    "acr": zhBookNames[book - 1] if 1 <= book <= len(zhBookNames) else str(book),
                    "chapter": chapter,
                    "section": verse,
                    "content": text,
                })
        return results


strongTagPattern = re.compile(r"<W([GH]\d*)>")
