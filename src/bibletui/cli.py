"""命令列子指令與程式進入點。"""

import argparse
import os
import re
import sqlite3
import sys

from . import __version__
from .books import (
    resolveAnyBookName,
    zhBookNames,
)
from .console import (
    setupConsole,
    supportsAnsiColor,
)
from .constants import (
    bold,
    dim,
    enLangs,
    introTypeLabel,
    missingContentMsg,
    needRecoveryMsg,
    red,
    reset,
    zhLangs,
)
from .install import findInDir, installOne
from .paths import launchCommand, userDataDir
from .render import (
    insertFootnoteMarkers,
    renderDictHtml,
    renderStrongVerse,
    splitStrongVerse,
)
from .resources import (
    resolveResources,
    resourceSearchDirs,
)
from .sources.cuv import (
    CuvSource,
    strongTagPattern,
)
from .sources.recovery import (
    RecoverySource,
    bookDisplayName,
    connect,
    getFootnotes,
    getOutlines,
)
from .sources.strongdict import (
    StrongDictSource,
    connectDict,
    connectStrongBible,
    normalizeStrongCode,
)
from .storage import (
    migrateLegacyNoteDb,
    noteDbDefaultPath,
    resolveNoteDbPath,
)

__all__ = ["main"]


def cmdData(args, _conn):
    resources = resolveResources(args, _loadStoredSettingsDict())
    labels = (
        ("db", "恢復本 bible.db"),
        ("strongBible", "和合本/Strong 模組 .bbl.mybible"),
        ("dict", "Strong 字典 .dct.mybible"),
    )
    print(f"使用者資料目錄: {userDataDir()}")
    print("資料庫搜尋順序（前者優先）:")
    for d in resourceSearchDirs():
        print(f"  {d}")
    print("偵測結果:")
    for key, label in labels:
        p = resources.get(key)
        print(f"  {label}: {p if p and os.path.isfile(p) else '（未找到）'}")
    notePath = resolveNoteDbPath()
    print(f"筆記資料庫: {notePath or '（未啟用）'}")
    print(f"預設筆記資料庫位置: {noteDbDefaultPath}")


def cmdDataInstall(args, _conn):
    sources = list(args.fromFile or [])
    if args.fromDir:
        found = findInDir(args.fromDir)
        if not found:
            sys.stderr.write(
                f"{args.fromDir}: 找不到可安裝的檔案"
                "（cuvt.bbl.mybible、strong_lite.dct.mybible、bible.db）\n"
            )
            sys.exit(2)
        sources.extend(found)
    if not sources:
        sys.stderr.write("請以 --from-dir 或 --from-file 指定要安裝的檔案。\n")
        sys.exit(2)
    destDir = userDataDir()
    failed = 0
    for src in sources:
        status, message = installOne(src, destDir, force=args.force)
        if status == "error":
            failed += 1
            sys.stderr.write(message + "\n")
        else:
            print(message)
    print(f"安裝目錄: {destDir}")
    if failed:
        sys.exit(1)


def cmdStrong(args, _conn):
    code = normalizeStrongCode(args.code)
    if not code:
        sys.stderr.write(
            "請在編號前加上 G（希臘文）或 H（希伯來文），例如 G26 或 H157\n"
        )
        sys.exit(1)

    dconn = connectDict(args.dict)
    row = StrongDictSource(dconn).lookup(code)
    if not row:
        sys.stderr.write(f"查無 Strong 編號: {code}\n")
        sys.exit(1)

    color = (not args.noColor) and supportsAnsiColor()
    header = f"Strong {row['word']}"
    print(f"{bold}{header}{reset}\n" if color else f"{header}\n")
    print(renderDictHtml(row["data"], color=color))


def printStrongDefinition(dictPath, code, color):
    if code in ("G0", "H0"):
        print(f"{dim}[{code} 為佔位符，無對應字典資料]{reset}" if color
              else f"[{code} 為佔位符，無對應字典資料]")
        return
    dconn = connectDict(dictPath)
    row = StrongDictSource(dconn).lookup(code)
    if not row:
        sys.stderr.write(f"查無 Strong 編號: {code}\n")
        return
    header = f"Strong {row['word']}"
    print(f"\n{bold}{header}{reset}\n" if color else f"\n{header}\n")
    print(renderDictHtml(row["data"], color=color))


def cmdOrig(args, _conn):
    bookIndex = resolveAnyBookName(args.book)
    if bookIndex is None:
        sys.stderr.write(f"找不到書卷: {args.book}（請用中／英文書卷名或 1-66 的編號）\n")
        sys.exit(1)

    chapterArg = str(args.chapter)
    verseFilter = None
    if ":" in chapterArg:
        chapterS, verseS = chapterArg.split(":")
        chapter = int(chapterS)
        verseFilter = int(verseS)
    else:
        chapter = int(chapterArg)

    if args.word is not None and verseFilter is None:
        sys.stderr.write("使用 --word 查詢原文字義時，請同時指定確切的節，例如 3:16\n")
        sys.exit(1)

    bconn = connectStrongBible(args.strongbible)
    rows = CuvSource(bconn).chapterRows(bookIndex, chapter)
    if not rows:
        sys.stderr.write("查無此章節\n")
        sys.exit(1)

    color = (not args.noColor) and supportsAnsiColor()
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

    if verseFilter and targetLegend is not None and args.word is None:
        print()
        legendParts = [f"[{n}] {'/'.join(c)}" for n, c in sorted(targetLegend.items())]
        print("  ".join(legendParts))

    if args.word is not None:
        if targetLegend is None or args.word not in targetLegend:
            sys.stderr.write(f"這一節沒有第 {args.word} 個字\n")
            sys.exit(1)
        for code in targetLegend[args.word]:
            printStrongDefinition(args.dict, code, color)


def cmdList(args, conn):
    if getattr(args, "sourceKind", "recovery") == "cuv":
        rows = list(enumerate(zhBookNames, start=1))
    else:
        rows = RecoverySource(conn).listBooks()
    start, end = 1, 66
    if args.testament == "舊約":
        start, end = 1, 39
    elif args.testament == "新約":
        start, end = 40, 66
    for bookIndex, name in rows:
        if start <= bookIndex <= end:
            print(f"{bookIndex:>3}  {name}")


def cmdIntro(args, conn):
    bookIndex = resolveAnyBookName(args.book, conn)
    if bookIndex is None:
        sys.stderr.write(f"找不到書卷: {args.book}\n")
        sys.exit(1)
    name = bookDisplayName(conn, bookIndex, "big5")
    rows = RecoverySource(conn).intros(bookIndex)
    print(f"{bold}{name} 書卷簡介{reset}\n")
    for r in rows:
        label = introTypeLabel.get(r["type"], f"type{r['type']}")
        print(f"{dim}{label}{reset}  {r['intro']}\n")


def cmdNote(args, conn):
    bookIndex = resolveAnyBookName(args.book, conn)
    if bookIndex is None:
        sys.stderr.write(f"找不到書卷: {args.book}\n")
        sys.exit(1)
    try:
        chapterS, sectionS = args.ref.split(":")
        chapter, section = int(chapterS), int(sectionS)
    except ValueError:
        sys.stderr.write("章節格式錯誤，需為 章:節，例如 1:1\n")
        sys.exit(1)
    row = RecoverySource(conn).footnote(bookIndex, chapter, section, args.seq)
    if not row:
        sys.stderr.write("查無此註解\n")
        sys.exit(1)
    name = bookDisplayName(conn, bookIndex, "big5")
    print(f"{bold}{name} {chapter}:{section} 註{args.seq}{reset}\n")
    print(row["note"])


def cmdSearch(args, conn):
    cuv = getattr(args, "sourceKind", "recovery") == "cuv"
    if cuv:
        results = CuvSource(conn).search([args.query])
        queryPattern = re.compile(
            "\u3000?".join(re.escape(ch) for ch in args.query.replace("\u3000", ""))
        ) if args.query.replace("\u3000", "") else None
    else:
        results = RecoverySource(conn).search(args.lang or "big5", [args.query])
    if not results:
        print("沒有找到符合的經文")
        return
    for r in results:
        if cuv and queryPattern is not None:
            highlighted = queryPattern.sub(lambda m: f"{red}{m.group(0)}{reset}", r["content"])
        else:
            highlighted = r["content"].replace(
                args.query, f"{red}{args.query}{reset}"
            )
        print(f"{dim}{r['acr']} {r['chapter']}:{r['section']}{reset}  {highlighted}")


def renderChapter(conn, bookIndex, chapter, sectionFilter, langPrimary,
                   langSecondary, showOutline, showFootnote, color):
    source = RecoverySource(conn)
    rows = source.chapterRows(bookIndex, chapter, langPrimary)
    if not rows:
        sys.stderr.write("查無此章節\n")
        sys.exit(1)

    outlines = getOutlines(conn, langPrimary, bookIndex, chapter) if showOutline else {}

    secondaryMap = {}
    if langSecondary:
        srows = source.chapterRows(bookIndex, chapter, langSecondary)
        secondaryMap = {r["section"]: r["content"] for r in srows}

    indentUnit = "  "
    for r in rows:
        section = r["section"]
        if sectionFilter and section != sectionFilter:
            continue

        for o in outlines.get(section, []):
            indent = indentUnit * (o["level"] - 1)
            text = o["outline"]
            if color:
                print(f"{bold}{indent}{text}{reset}")
            else:
                print(f"{indent}{text}")

        content = r["content"]
        if showFootnote:
            fn = getFootnotes(conn, langPrimary, bookIndex, chapter, section)
            content = insertFootnoteMarkers(
                content, [(f["location"], f["seq"]) for f in fn], color=color
            )
        secLabel = f"{dim}{section:>3}{reset}" if color else f"{section:>3}"
        print(f"{secLabel}  {content}")

        if langSecondary and section in secondaryMap:
            secText = secondaryMap[section]
            if color:
                print(f"     {dim}{secText}{reset}")
            else:
                print(f"     {secText}")
        print()


def renderCuvChapter(conn, bookIndex, chapter, sectionFilter, color):
    rows = CuvSource(conn).chapterRows(bookIndex, chapter)
    if not rows:
        sys.stderr.write("查無此章節\n")
        sys.exit(1)
    for r in rows:
        verse = r["Verse"]
        if sectionFilter and verse != sectionFilter:
            continue
        text = strongTagPattern.sub("", r["Scripture"])
        label = f"{dim}{verse:>3}{reset}" if color else f"{verse:>3}"
        print(f"{label}  {text}")
        print()


def cmdRead(args, conn):
    cuv = getattr(args, "sourceKind", "recovery") == "cuv"
    bookIndex = resolveAnyBookName(args.book, None if cuv else conn)
    if bookIndex is None:
        sys.stderr.write(f"找不到書卷: {args.book}\n")
        sys.exit(1)

    chapter = args.chapter
    sectionFilter = None
    if ":" in str(chapter):
        chapterS, sectionS = str(chapter).split(":")
        chapter = int(chapterS)
        sectionFilter = int(sectionS)
    else:
        chapter = int(chapter)

    if cuv:
        color = (not args.noColor) and supportsAnsiColor()
        header = f"{zhBookNames[bookIndex - 1]} 第{chapter}章"
        print(f"{bold}{header}{reset}\n" if color else f"{header}\n")
        renderCuvChapter(conn, bookIndex, chapter, sectionFilter, color)
        return

    langPrimary = "cuv_big5" if args.cuv else "big5"
    langSecondary = "eng" if args.en else None

    name = bookDisplayName(conn, bookIndex, "big5")
    color = (not args.noColor) and supportsAnsiColor()
    header = f"{name} 第{chapter}章"
    if color:
        print(f"{bold}{header}{reset}\n")
    else:
        print(f"{header}\n")

    renderChapter(
        conn, bookIndex, chapter, sectionFilter,
        langPrimary, langSecondary,
        showOutline=not args.noOutline,
        showFootnote=not args.noFootnote,
        color=color,
    )


def normalizeModeName(value):
    return "recovery" if value == "restore" else value


def buildParser():
    p = argparse.ArgumentParser(prog=launchCommand(), description="恢復本聖經 CLI / TUI")
    p.add_argument(
        "--version", action="version", version=f"bible {__version__}",
    )
    p.add_argument("--db", default=None, help="sqlite 資料庫路徑")
    p.add_argument(
        "--mode", choices=["auto", "recovery", "strong"], default="auto",
        type=normalizeModeName,
        help="不帶子指令時要啟動的介面："
             "auto=依偵測到的檔案自動判斷（兩者皆有時預設恢復本）、"
             "recovery=強制恢復本 TUI、strong=強制原文 Strong TUI",
    )
    sub = p.add_subparsers(dest="cmd")

    colorParent = argparse.ArgumentParser(add_help=False)
    colorParent.add_argument("--no-color", dest="noColor", action="store_true")

    sourceParent = argparse.ArgumentParser(add_help=False)
    sourceParent.add_argument(
        "--source", choices=["cuv", "recovery"], default=None,
        help="資料來源：cuv=和合本、recovery=恢復本；"
             "未指定時有恢復本就用恢復本，否則用和合本",
    )
    sourceParent.add_argument(
        "--strongbible", default=None,
        help="和合本模組 .bbl.mybible 路徑（--source cuv 或無恢復本時使用）",
    )

    pList = sub.add_parser("list", parents=[sourceParent], help="列出書卷")
    pList.add_argument("testament", nargs="?", choices=["舊約", "新約"], default=None)
    pList.set_defaults(func=cmdList)

    pRead = sub.add_parser("read", parents=[colorParent, sourceParent], help="讀取經文")
    pRead.add_argument("book")
    pRead.add_argument("chapter", help="章數，或 章:節")
    pRead.add_argument("--en", action="store_true", help="附加英文對照(恢復本英文，需恢復本)")
    pRead.add_argument("--cuv", action="store_true", help="改用和合本正文（恢復本內附的和合本）")
    pRead.add_argument("--no-outline", dest="noOutline", action="store_true")
    pRead.add_argument("--no-footnote", dest="noFootnote", action="store_true")
    pRead.set_defaults(func=cmdRead)

    pSearch = sub.add_parser("search", parents=[sourceParent], help="全文搜尋")
    pSearch.add_argument("query")
    pSearch.add_argument(
        "--lang", default=None, choices=zhLangs + enLangs,
        help="搜尋語言（預設 big5；和合本來源只支援 big5）",
    )
    pSearch.set_defaults(func=cmdSearch)

    pIntro = sub.add_parser("intro", help="書卷簡介")
    pIntro.add_argument("book")
    pIntro.set_defaults(func=cmdIntro)

    pNote = sub.add_parser("note", help="查看註解")
    pNote.add_argument("book")
    pNote.add_argument("ref", help="章:節，例如 1:1")
    pNote.add_argument("seq", type=int, help="註解編號")
    pNote.set_defaults(func=cmdNote)

    pStrong = sub.add_parser(
        "strong", parents=[colorParent], help="查詢 Strong 原文編號（需 MySword .dct.mybible 字典）"
    )
    pStrong.add_argument("code", help="Strong 編號，例如 G26 或 H157")
    pStrong.add_argument(
        "--dict", default=None,
        help="Strong 字典 .dct.mybible 檔案路徑（預設讀環境變數 BIBLE_STRONG_DICT）",
    )
    pStrong.set_defaults(func=cmdStrong)

    pOrig = sub.add_parser(
        "orig", parents=[colorParent],
        help="顯示和合本原文 Strong 編號對照（需 CUV+Strong 聖經模組，如 cuvt_bbl.mybible）",
    )
    pOrig.add_argument("book", help="書卷名（中／英文皆可），或 1-66 的編號")
    pOrig.add_argument("chapter", help="章數，或 章:節")
    pOrig.add_argument(
        "--strongbible", default=None,
        help="含 Strong 編號的聖經模組路徑，如 cuvt_bbl.mybible"
             "（預設讀環境變數 BIBLE_STRONG_BIBLE）",
    )
    pOrig.add_argument(
        "--dict", default=None,
        help="配合 --word 查字義用，Strong 字典 .dct.mybible 路徑"
             "（預設讀環境變數 BIBLE_STRONG_DICT）",
    )
    pOrig.add_argument(
        "--word", type=int,
        help="直接查詢第 N 個標號字對應的原文字義（需同時指定確切的節，如 3:16）",
    )
    pOrig.set_defaults(func=cmdOrig)

    pData = sub.add_parser("data", help="顯示資料目錄與偵測到的資料庫；install 安裝資料檔")
    pData.set_defaults(func=cmdData)
    dataSub = pData.add_subparsers(dest="dataCmd")
    pInstall = dataSub.add_parser(
        "install", help="驗證後把資料檔複製到使用者資料目錄（不連網）"
    )
    pInstall.add_argument(
        "--from-dir", dest="fromDir", default=None,
        help="含 cuvt.bbl.mybible、strong_lite.dct.mybible、bible.db 的資料夾",
    )
    pInstall.add_argument(
        "--from-file", dest="fromFile", action="append", default=[],
        help="單一資料檔路徑，可重複指定",
    )
    pInstall.add_argument(
        "--force", action="store_true", help="SHA-256 不符或目標已存在時仍安裝",
    )
    pInstall.set_defaults(func=cmdDataInstall)

    return p


noDatabaseMsg = (
    "找不到可用的聖經資料庫。\n"
    "請將 bible.db（恢復本）或 .mybible 檔案放在使用者資料目錄或目前目錄"
    "（從原始碼執行時也包含 bible.py 所在目錄），\n"
    f"並可執行 `{launchCommand()} data` 查看搜尋位置與偵測結果；"
    f"下載資料檔後可用 `{launchCommand()} data install --from-dir <資料夾>` 安裝。\n"
)


def resolveSourceKind(args):
    hasDb = bool(args.db and os.path.isfile(args.db))
    strongPath = getattr(args, "strongbible", None)
    hasCuv = bool(strongPath and os.path.isfile(strongPath))
    want = getattr(args, "source", None)
    if want == "recovery":
        if not hasDb:
            sys.stderr.write(f"找不到恢復本資料庫: {args.db}\n")
            sys.exit(1)
        return "recovery"
    if want == "cuv":
        if not hasCuv:
            sys.stderr.write("找不到和合本模組 (.bbl.mybible)，可用 --strongbible 指定路徑。\n")
            sys.exit(1)
        return "cuv"
    if hasDb:
        return "recovery"
    if hasCuv:
        return "cuv"
    sys.stderr.write(noDatabaseMsg)
    sys.exit(1)


def checkSourceCapabilities(args, kind):
    if kind != "cuv":
        return
    problems = []
    if args.cmd == "read":
        if args.en:
            problems.append("--en（英文對照）")
        if args.noOutline:
            problems.append("--no-outline（綱目）")
        if args.noFootnote:
            problems.append("--no-footnote（註腳）")
    if args.cmd == "search" and args.lang not in (None, "big5"):
        problems.append(f"--lang {args.lang}")
    if problems:
        sys.stderr.write(
            f"{missingContentMsg}：和合本來源不支援 {'、'.join(problems)}；"
            "請改用 --source recovery（需要恢復本 bible.db）。\n"
        )
        sys.exit(2)


def _loadStoredSettingsDict():
    path = resolveNoteDbPath()
    if not path:
        return {}
    try:
        conn = sqlite3.connect(path)
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
        conn.close()
    except sqlite3.Error:
        return {}
    return {k: v for k, v in rows}


def launchInteractive(args, resources):
    storedSettings = _loadStoredSettingsDict()

    dbPath = resources["db"]
    hasDb = bool(dbPath and os.path.exists(dbPath))

    strongBiblePath = resources["strongBible"]
    hasStrongBible = bool(strongBiblePath and os.path.exists(strongBiblePath))

    dictPath = resources["dict"]
    if not (dictPath and os.path.exists(dictPath)):
        dictPath = None

    mode = args.mode
    if mode == "auto":
        stored = normalizeModeName(storedSettings.get("default_mode"))
        if stored == "strong" and hasStrongBible:
            mode = "strong"
        elif stored == "recovery" and hasDb:
            mode = "recovery"
        elif hasDb:
            mode = "recovery"
        elif hasStrongBible:
            mode = "strong"
        else:
            sys.stderr.write(noDatabaseMsg)
            sys.exit(1)
    elif mode == "recovery" and not hasDb:
        sys.stderr.write(f"找不到恢復本資料庫: {dbPath}\n")
        sys.exit(1)
    elif mode == "strong" and not hasStrongBible:
        sys.stderr.write("找不到 Strong 原文聖經模組 (.bbl.mybible)。\n")
        sys.exit(1)

    from .tui.runner import runTui

    initialMode = "books" if mode == "recovery" else "strong_books"
    runTui(
        dbPath if hasDb else None,
        strongBiblePath if hasStrongBible else None,
        dictPath,
        initialMode=initialMode,
    )


def main():
    setupConsole()
    parser = buildParser()
    args = parser.parse_args()

    resources = resolveResources(args, _loadStoredSettingsDict())
    args.db = resources["db"]
    if hasattr(args, "dict"):
        args.dict = resources["dict"]
    if hasattr(args, "strongbible"):
        args.strongbible = resources["strongBible"]

    if getattr(args, "cmd", None) is None:
        if sys.stdin.isatty():
            if migrateLegacyNoteDb():
                resources = resolveResources(args, _loadStoredSettingsDict())
                args.db = resources["db"]
                args.dict = resources["dict"]
                args.strongbible = resources["strongBible"]
        launchInteractive(args, resources)
        return

    if args.cmd in ("strong", "orig", "data"):
        args.func(args, None)
        return

    if args.cmd in ("list", "read", "search"):
        kind = resolveSourceKind(args)
        checkSourceCapabilities(args, kind)
        args.sourceKind = kind
        if kind == "recovery":
            conn = connect(args.db)
        else:
            conn = connectStrongBible(args.strongbible)
        args.func(args, conn)
        return

    if not os.path.exists(args.db):
        sys.stderr.write(f"找不到恢復本資料庫: {args.db}\n{needRecoveryMsg}\n")
        sys.exit(1)

    conn = connect(args.db)
    args.func(args, conn)
