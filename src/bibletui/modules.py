"""已安裝資料庫的登錄：掃描、查找、Strong 判斷。"""

import os
import re
import sqlite3
from contextlib import closing
from dataclasses import dataclass

from .config import getDefaultId
from .paths import userDataDir
from .resources import _sniffMybibleKind, preferredBibleFile, resourceSearchDirs

kindLabels = {"bible": "聖經模組", "dict": "Strong 字典", "recovery": "恢復本"}
kindOrder = ("bible", "dict", "recovery")
_skipTypes = (".cmt.mybible", ".bok.mybible", ".jor.mybible")
_idPattern = re.compile(r"\.(bbl|dct)$", re.I)


class ModuleLookupError(Exception):
    pass


@dataclass
class ModuleInfo:
    kind: str
    id: str
    path: str
    abbr: str = ""
    description: str = ""
    language: str = ""
    strong: object = None
    ot: object = None
    nt: object = None
    size: int = 0
    managed: bool = False

    def matchKeys(self):
        keys = {self.id.lower()}
        if self.abbr:
            keys.add(self.abbr.lower())
        if self.kind == "bible":
            keys.add(f"{self.id}.bbl".lower())
        elif self.kind == "dict":
            keys.add(f"{self.id}.dct".lower())
        elif self.kind == "recovery":
            keys.update({"bible.db", "bible", "recovery"})
        return keys

    def coverage(self):
        if self.ot is None and self.nt is None:
            return "未知"
        parts = []
        if self.ot:
            parts.append("舊約")
        if self.nt:
            parts.append("新約")
        return "＋".join(parts) or "無"


def moduleIdFromFile(fileName):
    stem = fileName[:-len(".mybible")] if fileName.lower().endswith(".mybible") else fileName
    return _idPattern.sub("", stem)


def _flag(value):
    if value is None or value == "":
        return None
    try:
        return int(value) == 1
    except (TypeError, ValueError):
        return None


def readDetails(path):
    try:
        with closing(sqlite3.connect(path)) as c:
            cur = c.execute("SELECT * FROM Details LIMIT 1")
            row = cur.fetchone()
            if row is None:
                return {}
            return {d[0].lower(): v for d, v in zip(cur.description, row)}
    except sqlite3.Error:
        return {}


def _text(value):
    return str(value).strip() if value not in (None, "") else ""


def _makeInfo(kind, ident, path, managed):
    info = ModuleInfo(kind=kind, id=ident, path=path, managed=managed)
    try:
        info.size = os.path.getsize(path)
    except OSError:
        pass
    if kind == "recovery":
        info.abbr = "恢復本"
        info.description = "恢復本聖經資料庫（bible.db）"
        return info
    d = readDetails(path)
    info.abbr = _text(d.get("abbreviation"))
    info.description = _text(d.get("description") or d.get("title"))
    info.language = _text(d.get("language"))
    info.strong = _flag(d.get("strong"))
    if kind == "bible":
        info.ot = _flag(d.get("ot"))
        info.nt = _flag(d.get("nt"))
    return info


def scanModules(dirs=None):
    dirs = dirs if dirs is not None else resourceSearchDirs()
    userDir = os.path.abspath(userDataDir())
    seen, found = set(), []
    for d in dirs:
        try:
            entries = sorted(os.listdir(d))
        except OSError:
            continue
        managed = os.path.abspath(d) == userDir
        for fname in entries:
            full = os.path.join(d, fname)
            lower = fname.lower()
            if not os.path.isfile(full):
                continue
            if lower == "bible.db":
                kind, ident = "recovery", "recovery"
            elif lower.endswith(_skipTypes) or not lower.endswith(".mybible"):
                continue
            elif lower.endswith(".bbl.mybible"):
                kind, ident = "bible", moduleIdFromFile(fname)
            elif lower.endswith(".dct.mybible"):
                kind, ident = "dict", moduleIdFromFile(fname)
            else:
                sniffed = _sniffMybibleKind(full)
                if sniffed is None:
                    continue
                kind, ident = sniffed, moduleIdFromFile(fname)
            key = (kind, ident.lower())
            if key in seen:
                continue
            seen.add(key)
            found.append(_makeInfo(kind, ident, full, managed))
    found.sort(key=lambda m: (kindOrder.index(m.kind), m.id.lower()))
    return found


def findModule(query, infos, kinds=("bible", "dict", "recovery")):
    q = (query or "").strip().lower()
    pool = [m for m in infos if m.kind in kinds]
    exact = [m for m in pool if m.id.lower() == q]
    cands = exact if len(exact) == 1 else [m for m in pool if q in m.matchKeys()]
    if not cands:
        names = "、".join(m.id for m in pool) or "（無）"
        raise ModuleLookupError(f"找不到資料庫「{query}」。可用的代號: {names}")
    if len(cands) > 1:
        names = "、".join(f"{m.id}（{kindLabels[m.kind]}）" for m in cands)
        raise ModuleLookupError(
            f"「{query}」對應到多個資料庫: {names}；請加上 .bbl 或 .dct，例如 {cands[0].id}.bbl"
        )
    return cands[0]


def effectiveDefault(kind, infos):
    pool = [m for m in infos if m.kind == kind]
    want = getDefaultId(kind)
    if want:
        for m in pool:
            if m.id.lower() == want.lower():
                return m
    if kind == "bible":
        for m in pool:
            if os.path.basename(m.path).lower() == preferredBibleFile:
                return m
    return pool[0] if pool else None


def connHasStrong(conn):
    try:
        row = conn.execute("SELECT Strong FROM Details LIMIT 1").fetchone()
        flag = _flag(row[0]) if row else None
    except sqlite3.Error:
        flag = None
    if flag is not None:
        return flag
    try:
        return conn.execute(
            "SELECT 1 FROM Bible WHERE Scripture LIKE '%<WG%' OR Scripture LIKE '%<WH%' LIMIT 1"
        ).fetchone() is not None
    except sqlite3.Error:
        return False


def formatSize(n):
    if n >= 1 << 20:
        return f"{n / (1 << 20):.1f} MB"
    return f"{max(1, n // 1024)} KB" if n else "0 KB"


def describe(m):
    where = "使用者資料目錄" if m.managed else m.path
    strong = {True: "有", False: "無", None: "未知"}[m.strong]
    if m.kind == "bible":
        return f"Strong：{strong}　範圍：{m.coverage()}　大小：{formatSize(m.size)}　位置：{where}"
    if m.kind == "dict":
        return f"大小：{formatSize(m.size)}　位置：{where}"
    return f"大小：{formatSize(m.size)}　位置：{where}"
