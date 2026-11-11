"""筆記資料庫（bible-note.db）的路徑、遷移與開啟。"""

import os
import sqlite3
import sys

from .paths import scriptDir, userDataDir


noteDbDefaultPath = os.path.join(userDataDir(), "bible-note.db")
noteDbPointerPath = os.path.join(userDataDir(), "bible-note.db.path")
legacyNoteDbPath = os.path.join(scriptDir, ".bible-note.db") if scriptDir else None
legacyNoteDbPointerPath = os.path.join(scriptDir, ".bible-note.db.path") if scriptDir else None
legacyDeclinedPath = os.path.join(userDataDir(), ".legacy-declined")
noteSchemaVersion = 1


def resolveNoteDbPath():
    try:
        with open(noteDbPointerPath, "r", encoding="utf-8") as f:
            p = f.read().strip()
    except OSError:
        p = ""
    if p and os.path.isfile(p):
        return p
    if os.path.isfile(noteDbDefaultPath):
        return noteDbDefaultPath
    return None


def writeNoteDbPointer(value):
    try:
        os.makedirs(os.path.dirname(noteDbPointerPath), exist_ok=True)
        with open(noteDbPointerPath, "w", encoding="utf-8") as f:
            f.write(value)
    except OSError:
        pass


def findLegacyNoteDb():
    if not scriptDir:
        return None
    if resolveNoteDbPath() or os.path.exists(legacyDeclinedPath):
        return None
    if os.path.isfile(legacyNoteDbPath):
        return ("copy", legacyNoteDbPath)
    try:
        with open(legacyNoteDbPointerPath, "r", encoding="utf-8") as f:
            p = f.read().strip()
    except OSError:
        p = ""
    if p and os.path.isfile(p):
        return ("link", p)
    return None


def migrateLegacyNoteDb(askFunc=input, out=None):
    out = out or sys.stderr
    found = findLegacyNoteDb()
    if not found:
        return None
    kind, src = found
    if kind == "copy":
        question = (f"偵測到舊版筆記資料庫：{src}\n"
                    f"是否複製到 {noteDbDefaultPath}？（原檔會保留）[Y/n] ")
    else:
        question = (f"偵測到舊版筆記資料庫路徑設定：{src}\n"
                    "是否沿用該檔案？[Y/n] ")
    try:
        answer = askFunc(question).strip().lower()
    except (EOFError, KeyboardInterrupt):
        return None
    try:
        os.makedirs(os.path.dirname(noteDbDefaultPath), exist_ok=True)
        if answer in ("", "y", "yes"):
            if kind == "copy":
                import shutil
                shutil.copy2(src, noteDbDefaultPath)
            else:
                writeNoteDbPointer(src)
            out.write("已完成筆記資料庫遷移。\n")
            return "migrated"
        with open(legacyDeclinedPath, "w", encoding="utf-8") as f:
            f.write("declined\n")
    except OSError as e:
        out.write(f"遷移失敗: {e}\n")
        return None
    return "declined"


def openNoteDb(path):
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS notes "
        "(book INTEGER, chapter INTEGER, section INTEGER, note TEXT, "
        "PRIMARY KEY(book, chapter, section))"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS bookmarks "
        "(book INTEGER, chapter INTEGER, section INTEGER, added_at TEXT, "
        "PRIMARY KEY(book, chapter, section))"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS refs "
        "(book INTEGER, chapter INTEGER, section INTEGER, label TEXT, "
        "target_book INTEGER, target_chapter INTEGER, target_section INTEGER, "
        "PRIMARY KEY(book, chapter, section, label))"
    )
    if conn.execute("PRAGMA user_version").fetchone()[0] == 0:
        conn.execute(f"PRAGMA user_version = {noteSchemaVersion}")
    conn.commit()
    return conn
