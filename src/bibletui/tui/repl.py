"""純文字原文 Strong 互動模式（目前無呼叫端）。"""

import os
import sqlite3
import sys

from ..books import (
    resolveAnyBookName,
    zhBookNames,
)
from ..console import supportsAnsiColor
from ..constants import (
    bold,
    dim,
    reset,
)
from ..render import (
    renderDictHtml,
    renderStrongVerse,
    splitStrongVerse,
)
from ..sources.cuv import CuvSource
from ..sources.strongdict import (
    StrongDictSource,
    normalizeStrongCode,
)


def _openSqliteSoft(path):
    if not path or not os.path.exists(path):
        return None
    c = sqlite3.connect(path)
    c.row_factory = sqlite3.Row
    return c


def _printStrongDefinitionSafe(dictPath, code, color):
    if code in ("G0", "H0"):
        msg = f"[{code} 為佔位符，無對應字典資料]"
        print(f"{dim}{msg}{reset}" if color else msg)
        return
    dconn = _openSqliteSoft(dictPath)
    if dconn is None:
        print("尚未偵測到 Strong 字典（.dct.mybible），無法查字義。")
        return
    row = StrongDictSource(dconn).lookup(code)
    if not row:
        print(f"查無 Strong 編號: {code}")
        return
    header = f"Strong {row['word']}"
    print(f"\n{bold}{header}{reset}\n" if color else f"\n{header}\n")
    print(renderDictHtml(row["data"], color=color))


def _printOrigChapter(bconn, bookIndex, chapter, verseFilter, color):
    rows = CuvSource(bconn).chapterRows(bookIndex, chapter)
    if not rows:
        print("查無此章節")
        return None

    bookName = zhBookNames[bookIndex - 1]
    header = f"{bookName} 第{chapter}章"
    print(f"{bold}{header}{reset}\n" if color else f"{header}\n")

    targetLegend = None
    for r in rows:
        verse = r["Verse"]
        if verseFilter and verse != verseFilter:
            continue
        segments = splitStrongVerse(r["Scripture"])
        lineText, legend = renderStrongVerse(segments, color)
        verseLabel = f"{dim}{verse:>3}{reset}" if color else f"{verse:>3}"
        print(f"{verseLabel}  {lineText}")
        if verseFilter and verse == verseFilter:
            targetLegend = legend

    if verseFilter and targetLegend is not None:
        legendParts = [f"[{n}] {'/'.join(c)}" for n, c in sorted(targetLegend.items())]
        print("  ".join(legendParts))
    return targetLegend


def runStrongRepl(strongBiblePath, dictPath, canSwitchToRecovery=False):
    color = supportsAnsiColor()
    bconn = _openSqliteSoft(strongBiblePath)
    if bconn is None:
        sys.stderr.write(f"找不到 Strong 原文聖經模組: {strongBiblePath}\n")
        return None

    title = "原文 Strong 查詢模式"
    print(f"{bold}{title}{reset}" if color else title)
    print("指令：")
    print("  b <書卷> <章>[:節]   顯示原文對照經文（指定節時，末尾會列出標號對照 Strong 編號）")
    print("  w <編號>            查詢上一次顯示的節中，第 N 個標號字的字義")
    print("  s <G26|H157>        直接查 Strong 編號")
    if canSwitchToRecovery:
        print("  r                   切換回恢復本介面")
    print("  q                   離開")

    lastLegend = None
    while True:
        try:
            line = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return None
        if not line:
            continue
        parts = line.split()
        cmd = parts[0].lower()

        if cmd == "q":
            return None
        if cmd in ("r", "recovery", "restore") and canSwitchToRecovery:
            return "recovery"
        if cmd == "b" and len(parts) >= 3:
            bookIndex = resolveAnyBookName(parts[1])
            if bookIndex is None:
                print(f"找不到書卷: {parts[1]}（請用中／英文書卷名或 1-66 的編號）")
                continue
            chapterArg = parts[2]
            verseFilter = None
            try:
                if ":" in chapterArg:
                    chapterS, verseS = chapterArg.split(":")
                    chapter, verseFilter = int(chapterS), int(verseS)
                else:
                    chapter = int(chapterArg)
            except ValueError:
                print("章節格式錯誤，需為 章 或 章:節，例如 1 或 1:1")
                continue
            lastLegend = _printOrigChapter(bconn, bookIndex, chapter, verseFilter, color)
        elif cmd == "w" and len(parts) >= 2:
            if not lastLegend:
                print("請先用 b 指令顯示含節號的經文（需含 :節）")
                continue
            try:
                n = int(parts[1])
            except ValueError:
                print("請輸入數字編號")
                continue
            if n not in lastLegend:
                print(f"這一節沒有第 {n} 個標號字")
                continue
            for code in lastLegend[n]:
                _printStrongDefinitionSafe(dictPath, code, color)
        elif cmd == "s" and len(parts) >= 2:
            code = normalizeStrongCode(parts[1])
            if not code:
                print("請在編號前加上 G（希臘文）或 H（希伯來文），例如 G26 或 H157")
                continue
            _printStrongDefinitionSafe(dictPath, code, color)
        else:
            options = "b / w / s" + (" / r" if canSwitchToRecovery else "") + " / q"
            print(f"無法辨識的指令，可用: {options}")
