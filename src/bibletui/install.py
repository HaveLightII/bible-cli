"""資料檔安裝：驗證資料表結構後複製到使用者資料目錄，不連網；可直接吃 .gz 與 .zip 壓縮檔。"""

import gzip
import hashlib
import os
import posixpath
import shutil
import sqlite3
import zipfile
import zlib
from contextlib import closing

from .resources import _sniffMybibleKind

knownDataFiles = {
    "cuvt.bbl.mybible": {
        "sha256": "946ad2a51d6666a7df6ebb9fc753f0f05a9fbf371730f39ee8e4e5ac5a8f37ec",
        "kind": "bible",
        "label": "和合本",
    },
    "strong_lite.dct.mybible": {
        "sha256": "077b01dc7c3bab17d8497993016b4e72b1b5c637571a7cc0df323910a6df3cd5",
        "kind": "dict",
        "label": "Strong 字典",
    },
    "bible.db": {
        "sha256": "1ef6a0fbf1434a0fc27757afbcf73f92e5d7a893d4556d5b067caabce39dab7d",
        "kind": None,
        "label": "恢復本",
    },
}

recoveryTables = ("content", "book_name")


def stripGz(name):
    return name[:-3] if name.lower().endswith(".gz") else name


def stripArchive(name):
    lower = name.lower()
    for ext in (".gz", ".zip"):
        if lower.endswith(ext):
            return name[:-len(ext)]
    return name


def normalizeDataName(name):
    return stripArchive(name).lower().replace("_", ".")


def matchKnownName(fileName):
    key = normalizeDataName(fileName)
    for known in knownDataFiles:
        if normalizeDataName(known) == key:
            return known
    return None


def sha256Of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def hasTables(path, names):
    try:
        with closing(sqlite3.connect(path)) as c:
            have = {
                r[0] for r in c.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
    except sqlite3.Error:
        return False
    return all(n in have for n in names)


def findInDir(dirPath):
    try:
        entries = sorted(os.listdir(dirPath))
    except OSError:
        return []
    return [
        os.path.join(dirPath, n) for n in entries
        if matchKnownName(n) and os.path.isfile(os.path.join(dirPath, n))
    ]


def findInstallable(dirPath):
    try:
        entries = sorted(os.listdir(dirPath))
    except OSError:
        return []
    found = []
    for n in entries:
        full = os.path.join(dirPath, n)
        if not os.path.isfile(full):
            continue
        base = stripArchive(n).lower()
        if matchKnownName(n) or base.endswith((".bbl.mybible", ".dct.mybible")):
            found.append(full)
    return found


def removeQuietly(path):
    try:
        os.remove(path)
    except OSError:
        pass


def _stageFrom(openSrc, destName, known, destDir, force, label):
    destPath = os.path.join(destDir, destName)
    partPath = destPath + ".part"
    try:
        os.makedirs(destDir, exist_ok=True)
        with openSrc() as fin, open(partPath, "wb") as fout:
            shutil.copyfileobj(fin, fout)
    except (OSError, EOFError, zlib.error, zipfile.BadZipFile) as e:
        removeQuietly(partPath)
        return "error", f"{label}: 解壓縮失敗: {e}"

    status, message = _installFrom(partPath, destName, known, destPath, force)
    if status == "installed":
        try:
            os.replace(partPath, destPath)
        except OSError as e:
            removeQuietly(partPath)
            return "error", f"{destName}: 安裝失敗: {e}"
    else:
        removeQuietly(partPath)
    return status, message


def _destNameFor(name):
    known = matchKnownName(name)
    if known:
        return known, known
    if name.lower().endswith(".mybible"):
        return name, None
    return None, None


def _installZip(srcPath, destDir, force):
    try:
        zf = zipfile.ZipFile(srcPath)
    except (OSError, zipfile.BadZipFile) as e:
        return [("error", f"{srcPath}: 不是有效的 zip 檔: {e}")]
    results = []
    with zf:
        members = []
        for info in zf.infolist():
            if info.is_dir():
                continue
            base = posixpath.basename(info.filename.replace("\\", "/"))
            if base.lower().endswith(".mybible") and not base.startswith("."):
                members.append((info, base))
        if not members:
            return [("error", f"{srcPath}: 壓縮檔內沒有 .mybible 模組")]
        for info, base in members:
            destName, known = _destNameFor(base)
            results.append(_stageFrom(
                lambda info=info: zf.open(info), destName, known, destDir, force,
                f"{srcPath}（{base}）",
            ))
    return results


def installMany(srcPath, destDir, force=False):
    if not os.path.isfile(srcPath):
        return [("error", f"{srcPath}: 找不到檔案")]
    if srcPath.lower().endswith(".zip"):
        return _installZip(srcPath, destDir, force)
    return [installOne(srcPath, destDir, force)]


def installOne(srcPath, destDir, force=False):
    if not os.path.isfile(srcPath):
        return "error", f"{srcPath}: 找不到檔案"
    if srcPath.lower().endswith(".zip"):
        results = _installZip(srcPath, destDir, force)
        if len(results) == 1:
            return results[0]
        return "error", f"{srcPath}: 內含多個模組，請改用 installMany"
    name = stripGz(os.path.basename(srcPath))
    gz = name != os.path.basename(srcPath)
    known = matchKnownName(name)
    if known:
        destName = known
    elif name.lower().endswith(".mybible"):
        destName = name
    else:
        return "error", f"{srcPath}: 無法辨識的資料檔（支援 bible.db 與 .mybible 模組，可為 .gz 或 .zip）"

    if gz:
        return _stageFrom(
            lambda: gzip.open(srcPath, "rb"), destName, known, destDir, force, srcPath,
        )
    destPath = os.path.join(destDir, destName)
    return _installFrom(srcPath, destName, known, destPath, force)


def _installFrom(workPath, destName, known, destPath, force):
    destDir = os.path.dirname(destPath)
    if destName.lower().endswith(".mybible"):
        kind = _sniffMybibleKind(workPath)
        if kind is None:
            return "error", f"{destName}: 不是有效的 MySword 模組（缺少 Bible 或 dictionary 資料表）"
        if known and knownDataFiles[known]["kind"] != kind:
            return "error", f"{destName}: 內容不是{knownDataFiles[known]['label']}模組"
        lowerName = destName.lower()
        if not known and lowerName.endswith(".bbl.mybible") and kind != "bible":
            return "error", f"{destName}: 內容不是聖經模組（.bbl）"
        if not known and lowerName.endswith(".dct.mybible") and kind != "dict":
            return "error", f"{destName}: 內容不是字典模組（.dct）"
    elif destName == "bible.db" and not hasTables(workPath, recoveryTables):
        return "error", f"{workPath}: 不是恢復本資料庫（缺少 {'、'.join(recoveryTables)} 資料表）"

    digest = sha256Of(workPath)
    if os.path.isfile(destPath) and sha256Of(destPath) == digest:
        return "skipped", f"{destName}: 已是相同內容，略過"
    note = ""
    if known and digest != knownDataFiles[known]["sha256"]:
        note = "（SHA-256 與作者版本不同）"
    if os.path.isfile(destPath) and not force:
        return "error", f"{destName}: 目標已存在且內容不同；若要覆蓋請加 --force"

    if workPath == destPath + ".part":
        return "installed", f"{destName}: 已安裝{note}"
    partPath = destPath + ".part"
    try:
        os.makedirs(destDir, exist_ok=True)
        shutil.copyfile(workPath, partPath)
        os.replace(partPath, destPath)
    except OSError as e:
        removeQuietly(partPath)
        return "error", f"{destName}: 複製失敗: {e}"
    return "installed", f"{destName}: 已安裝{note}"
