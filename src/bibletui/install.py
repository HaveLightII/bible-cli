"""資料檔安裝：驗證 SHA-256 後複製到使用者資料目錄，不連網。"""

import hashlib
import os
import shutil
import sqlite3

from .resources import _sniffMybibleKind

knownDataFiles = {
    "cuvt.bbl.mybible": {
        "sha256": "946ad2a51d6666a7df6ebb9fc753f0f05a9fbf371730f39ee8e4e5ac5a8f37ec",
        "strict": True,
    },
    "strong_lite.dct.mybible": {
        "sha256": "077b01dc7c3bab17d8497993016b4e72b1b5c637571a7cc0df323910a6df3cd5",
        "strict": True,
    },
    "bible.db": {
        "sha256": "1ef6a0fbf1434a0fc27757afbcf73f92e5d7a893d4556d5b067caabce39dab7d",
        "strict": False,
    },
}

recoveryTables = ("content", "book_name")


def normalizeDataName(name):
    return name.lower().replace("_", ".")


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
        c = sqlite3.connect(path)
        have = {
            r[0] for r in c.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        c.close()
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


def installOne(srcPath, destDir, force=False):
    if not os.path.isfile(srcPath):
        return "error", f"{srcPath}: 找不到檔案"
    name = os.path.basename(srcPath)
    known = matchKnownName(name)
    if known:
        destName = known
    elif name.lower().endswith(".mybible") and _sniffMybibleKind(srcPath):
        destName = name
    else:
        return "error", f"{srcPath}: 無法辨識的資料檔（支援 bible.db 與 .mybible 模組）"

    digest = sha256Of(srcPath)
    destPath = os.path.join(destDir, destName)
    if os.path.isfile(destPath) and sha256Of(destPath) == digest:
        return "skipped", f"{destName}: 已是相同內容，略過"
    note = ""
    if known:
        info = knownDataFiles[known]
        if digest != info["sha256"]:
            if info["strict"] and not force:
                return "error", (
                    f"{destName}: SHA-256 不符（預期 {info['sha256']}，實際 {digest}）；"
                    "若確定要安裝請加 --force"
                )
            note = "（SHA-256 與作者版本不同）"
    if destName == "bible.db" and not hasTables(srcPath, recoveryTables):
        return "error", f"{srcPath}: 不是恢復本資料庫（缺少 {'、'.join(recoveryTables)} 資料表）"

    if os.path.isfile(destPath) and not force:
        return "error", f"{destName}: 目標已存在且內容不同；若要覆蓋請加 --force"

    partPath = destPath + ".part"
    try:
        os.makedirs(destDir, exist_ok=True)
        shutil.copyfile(srcPath, partPath)
        os.replace(partPath, destPath)
    except OSError as e:
        try:
            os.remove(partPath)
        except OSError:
            pass
        return "error", f"{destName}: 複製失敗: {e}"
    return "installed", f"{destName}: 已安裝{note}"
