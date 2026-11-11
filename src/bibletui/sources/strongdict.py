"""Strong 字典資料來源與 .mybible 連線輔助函式。"""

import os
import sqlite3
import sys


class StrongDictSource:
    def __init__(self, conn):
        self.conn = conn

    def lookup(self, code):
        return self.conn.execute(
            "SELECT word, data FROM dictionary WHERE word = ?", (code,)
        ).fetchone()


def connectSqliteOrExit(path, missingPathHint):
    if not path:
        sys.stderr.write(missingPathHint + "\n")
        sys.exit(1)
    if not os.path.exists(path):
        sys.stderr.write(f"找不到檔案: {path}\n")
        sys.exit(1)
    c = sqlite3.connect(path)
    c.row_factory = sqlite3.Row
    return c


def connectDict(dictPath):
    return connectSqliteOrExit(
        dictPath,
        "尚未指定 Strong 字典路徑。請用 --dict 指定 .dct.mybible 檔案路徑，"
        "或設定環境變數 BIBLE_STRONG_DICT。",
    )


def connectStrongBible(biblePath):
    return connectSqliteOrExit(
        biblePath,
        "尚未指定含 Strong 編號的聖經模組路徑。請用 --strongbible 指定，"
        "例如 MySword 的 cuvt_bbl.mybible（或設定環境變數 BIBLE_STRONG_BIBLE）。",
    )


def normalizeStrongCode(code):
    code = code.strip().upper()
    if not code:
        return None
    if code[0] not in ("G", "H"):
        return None
    return code
