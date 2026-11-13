"""資料檔（bible.db、Strong 字典與和合本模組）的偵測與路徑解析。"""

import os
import sqlite3
from contextlib import closing

from .config import getDefaultId
from .paths import scriptDir, userDataDir

preferredBibleFile = "cuvt.bbl.mybible"
moduleSuffix = {"bible": ".bbl.mybible", "dict": ".dct.mybible"}


def _sniffMybibleKind(path):
    try:
        with closing(sqlite3.connect(path)) as c:
            tables = {
                r[0] for r in c.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
    except sqlite3.Error:
        return None
    if "dictionary" in tables:
        return "dict"
    if "Bible" in tables:
        return "bible"
    return None


def detectResources(baseDir=None):
    baseDir = baseDir or scriptDir or os.getcwd()
    resources = {"db": None, "dict": None, "strongBible": None}

    dbPath = os.path.join(baseDir, "bible.db")
    if os.path.isfile(dbPath):
        resources["db"] = dbPath

    try:
        entries = sorted(os.listdir(baseDir))
    except OSError:
        entries = []

    for fname in entries:
        full = os.path.join(baseDir, fname)
        if not os.path.isfile(full):
            continue
        lower = fname.lower()
        if lower.endswith(".dct.mybible"):
            resources["dict"] = resources["dict"] or full
        elif lower.endswith(".bbl.mybible"):
            if lower == preferredBibleFile:
                resources["strongBible"] = full
            else:
                resources["strongBible"] = resources["strongBible"] or full
        elif lower.endswith(".mybible"):
            kind = _sniffMybibleKind(full)
            if kind == "dict":
                resources["dict"] = resources["dict"] or full
            elif kind == "bible":
                resources["strongBible"] = resources["strongBible"] or full

    return resources


def _isPreferredBible(path):
    return bool(path) and os.path.basename(path).lower() == preferredBibleFile


def resourceSearchDirs():
    dirs = []
    for d in (userDataDir(), scriptDir, os.getcwd()):
        if not d:
            continue
        d = os.path.abspath(d)
        if d not in dirs:
            dirs.append(d)
    return dirs


def pathForModuleId(kind, ident):
    if not ident:
        return None
    want = (ident + moduleSuffix[kind]).lower()
    for d in resourceSearchDirs():
        try:
            entries = os.listdir(d)
        except OSError:
            continue
        for fname in sorted(entries):
            if fname.lower() == want and os.path.isfile(os.path.join(d, fname)):
                return os.path.join(d, fname)
    return None


def resolveResources(args=None, settings=None):
    settings = settings or {}
    found = {"db": None, "dict": None, "strongBible": None}
    for d in resourceSearchDirs():
        extra = detectResources(d)
        if _isPreferredBible(extra["strongBible"]) and not _isPreferredBible(found["strongBible"]):
            found["strongBible"] = extra["strongBible"]
        found = {k: found[k] or extra[k] for k in found}
    argDb = getattr(args, "db", None)
    argDict = getattr(args, "dict", None)
    argStrong = getattr(args, "strongbible", None)
    chains = {
        "db": ([argDb, settings.get("recovery_db_path"), found["db"]],
               argDb or os.path.join(scriptDir or userDataDir(), "bible.db")),
        "dict": ([argDict, os.environ.get("BIBLE_STRONG_DICT"),
                  pathForModuleId("dict", getDefaultId("dict")),
                  settings.get("dict_db_path"), found["dict"]],
                 argDict or os.environ.get("BIBLE_STRONG_DICT")),
        "strongBible": ([argStrong, os.environ.get("BIBLE_STRONG_BIBLE"),
                         pathForModuleId("bible", getDefaultId("bible")),
                         settings.get("strong_db_path"), found["strongBible"]],
                        argStrong or os.environ.get("BIBLE_STRONG_BIBLE")),
    }
    resolved = {}
    for key, (chain, fallback) in chains.items():
        resolved[key] = next((p for p in chain if p and os.path.isfile(p)), fallback)
    return resolved
