"""恢復本（bible.db）資料來源。"""

import os
import sqlite3
import sys

from ..constants import zhLangs


def connect(dbPath):
    if not os.path.exists(dbPath):
        sys.stderr.write(f"找不到資料庫檔案: {dbPath}\n")
        sys.exit(1)
    conn = sqlite3.connect(dbPath)
    conn.row_factory = sqlite3.Row
    return conn


class RecoverySource:
    def __init__(self, conn, lang="big5"):
        self.conn = conn
        self.lang = lang

    def resolveBook(self, name):
        name = name.strip()
        cur = self.conn.cursor()
        row = cur.execute(
            "SELECT book_index FROM book_name WHERE name = ? OR acronym_name = ? LIMIT 1",
            (name, name),
        ).fetchone()
        if row:
            return row["book_index"]

        row = cur.execute(
            "SELECT book_index FROM book_name WHERE lower(name) = lower(?) "
            "OR lower(acronym_name) = lower(?) LIMIT 1",
            (name, name),
        ).fetchone()
        if row:
            return row["book_index"]

        row = cur.execute(
            "SELECT book_index FROM book_name WHERE name LIKE ? OR acronym_name LIKE ? LIMIT 1",
            (f"%{name}%", f"%{name}%"),
        ).fetchone()
        if row:
            return row["book_index"]
        return None

    def bookName(self, bookIndex, lang=None):
        lang = self.lang if lang is None else lang
        cur = self.conn.cursor()
        row = cur.execute(
            "SELECT name FROM book_name WHERE book_index=? AND language=?",
            (bookIndex, lang),
        ).fetchone()
        return row["name"] if row else f"[book {bookIndex}]"

    def bookAcronym(self, bookIndex, lang, default=None):
        cur = self.conn.cursor()
        row = cur.execute(
            "SELECT acronym_name FROM book_name WHERE book_index=? AND language=?",
            (bookIndex, lang),
        ).fetchone()
        return row["acronym_name"] if row else default

    def listBooks(self, lang=None):
        lang = self.lang if lang is None else lang
        cur = self.conn.cursor()
        rows = cur.execute(
            "SELECT book_index, name FROM book_name WHERE language=? ORDER BY book_index",
            (lang,),
        ).fetchall()
        return [(r["book_index"], r["name"]) for r in rows]

    def outlines(self, lang, bookIndex, chapter):
        cur = self.conn.cursor()
        rows = cur.execute(
            "SELECT section, flag, level, outline FROM outline "
            "WHERE language=? AND book_index=? AND chapter=? "
            "ORDER BY section ASC, flag ASC, level ASC",
            (lang, bookIndex, chapter),
        ).fetchall()
        bySection = {}
        for r in rows:
            bySection.setdefault(r["section"], []).append(r)
        return bySection

    def footnotes(self, lang, bookIndex, chapter, section):
        cur = self.conn.cursor()
        rows = cur.execute(
            "SELECT location, seq, note FROM footnote "
            "WHERE language=? AND book_index=? AND chapter=? AND section=? "
            "ORDER BY seq ASC",
            (lang, bookIndex, chapter, section),
        ).fetchall()
        return rows

    def footnote(self, bookIndex, chapter, section, seq, lang=None):
        lang = self.lang if lang is None else lang
        cur = self.conn.cursor()
        return cur.execute(
            "SELECT note FROM footnote WHERE language=? AND book_index=? "
            "AND chapter=? AND section=? AND seq=?",
            (lang, bookIndex, chapter, section, seq),
        ).fetchone()

    def maxChapter(self, bookIndex):
        cur = self.conn.cursor()
        row = cur.execute(
            "SELECT MAX(chapter) AS m FROM content WHERE language=? AND book_index=?",
            (self.lang, bookIndex),
        ).fetchone()
        return row["m"] or 1

    def chapterRows(self, bookIndex, chapter, lang):
        cur = self.conn.cursor()
        return cur.execute(
            "SELECT section, content FROM content WHERE language=? AND book_index=? "
            "AND chapter=? ORDER BY section",
            (lang, bookIndex, chapter),
        ).fetchall()

    def verseText(self, bookIndex, chapter, section, lang):
        cur = self.conn.cursor()
        return cur.execute(
            "SELECT content FROM content WHERE language=? AND book_index=? "
            "AND chapter=? AND section=?",
            (lang, bookIndex, chapter, section),
        ).fetchone()

    def search(self, lang, includeTerms, excludeTerms=()):
        where = " AND ".join(["content LIKE ?"] * len(includeTerms))
        params = [lang] + [f"%{t}%" for t in includeTerms]
        sql = f"SELECT book_index, chapter, section, content FROM content WHERE language=? AND ({where})"
        if excludeTerms:
            notWhere = " OR ".join(["content LIKE ?"] * len(excludeTerms))
            sql += f" AND NOT ({notWhere})"
            params += [f"%{t}%" for t in excludeTerms]
        sql += " ORDER BY book_index, chapter, section"
        cur = self.conn.cursor()
        rows = cur.execute(sql, params).fetchall()
        acrLang = lang if lang in zhLangs else "big5"
        results = []
        for r in rows:
            results.append({
                "book_index": r["book_index"],
                "acr": self.bookAcronym(r["book_index"], acrLang, str(r["book_index"])),
                "chapter": r["chapter"],
                "section": r["section"],
                "content": r["content"],
            })
        return results

    def intros(self, bookIndex, lang=None):
        lang = self.lang if lang is None else lang
        cur = self.conn.cursor()
        return cur.execute(
            "SELECT type, intro FROM book_intro WHERE language=? AND book_index=? ORDER BY type",
            (lang, bookIndex),
        ).fetchall()


def resolveBook(conn, name):
    return RecoverySource(conn).resolveBook(name)


def bookDisplayName(conn, bookIndex, lang="big5"):
    return RecoverySource(conn).bookName(bookIndex, lang)


def getOutlines(conn, lang, bookIndex, chapter):
    return RecoverySource(conn).outlines(lang, bookIndex, chapter)


def getFootnotes(conn, lang, bookIndex, chapter, section):
    return RecoverySource(conn).footnotes(lang, bookIndex, chapter, section)
