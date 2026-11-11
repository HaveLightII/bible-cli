#!/usr/bin/env python3
"""
bible.py — 恢復本聖經 CLI / TUI 合一版

用法：
    python3 bible.py                    # 不帶參數 -> 依偵測到的檔案自動判斷要開啟的介面
    python3 bible.py --mode recovery    # 強制啟動恢復本 TUI（需 bible.db）
    python3 bible.py --mode strong      # 強制啟動原文 Strong TUI 互動模式（需 .mybible）
    python3 bible.py --db X             # 指定資料庫路徑 -> 仍走上面的自動判斷邏輯
    python3 bible.py list [舊約|新約] [--source cuv|recovery]    # 帶子指令 -> 走 CLI
    python3 bible.py read <書卷> <章>[:節] [--source cuv|recovery] [--en] [--cuv] [--no-outline] [--no-footnote] [--no-color]
    python3 bible.py search <關鍵字> [--source cuv|recovery] [--lang big5|gb|eng]
    python3 bible.py intro <書卷>
    python3 bible.py note <書卷> <章>:<節> <編號>
    python3 bible.py orig <書卷> <章>[:節] [--word N]   # CLI：原文 Strong 對照
    python3 bible.py strong <G26|H157>                    # CLI：查單一 Strong 編號

自動偵測（依序找使用者資料目錄、bible.py 所在資料夾、目前目錄）：
    - 找到 bible.db -> 提供恢復本功能（list/read/search/intro/note，以及互動 TUI）。
    - 找到 *.dct.mybible -> 提供 Strong 字典查詢（strong 指令、原文模式的 w/s 指令）。
    - 找到 *.bbl.mybible（或內含 Bible 表的 .mybible）-> 提供原文 Strong 對照（orig 指令、
      原文模式的 b 指令）。
    - 恢復本與原文 Strong 共用同一個 TUI 介面。若 bible.db 與 Strong 聖經模組同時存在，
      不帶子指令啟動時直接進入恢復本畫面，可在任一畫面按 s 切換到原文 Strong 畫面
      （和合本），在原文 Strong 畫面則按 r 切回恢復本（搜尋輸入畫面除外），也可用
      --mode 直接指定；已存設定 default_mode 優先於上述預設。只有 Strong 聖經模組、
      沒有 bible.db 時，直接進入原文 Strong 畫面；CLI 未指定 --source 時同樣是有恢復本
      用恢復本，否則用和合本。
    - 資料檔路徑優先序：命令列參數（--db、--dict、--strongbible）、環境變數
      （BIBLE_STRONG_DICT、BIBLE_STRONG_BIBLE）、已存設定（recovery_db_path、
      dict_db_path、strong_db_path）、使用者資料目錄、bible.py 所在資料夾、目前目錄。
    - 原文 Strong 讀經畫面中，經文裡標色的原文字可直接用滑鼠點按（或觸控點按）
      叫出／收合該字的 Strong 字義，顯示方式與恢復本點按經文展開註解相同。

互動 TUI 指令模式（: 開頭，類似 vim，可在任何畫面呼叫，按 ? 或 :help 查看完整說明）：
    - 底端狀態列平時不顯示操作提示，只在指令模式輸入中，或剛執行完某個動作
      （複製、儲存筆記等）時顯示訊息。
    - 常用指令：:q（詢問後離開）、:Q（直接離開）、:strong / :S、:recovery / :R
      （切換模式並跳至本章節或指定書卷章節）、:footnote / :F、:intro、:copy / :C、
      :english / :E、:outline / :O、:search / :find（支援多字串交集查詢與 --exclude
      差集查詢，按 / 的搜尋與此指令共用同一套邏輯）、:reference / :ref。
      裸的 :1、:1 1、:genesis 1 1 用於直接跳至指定節／章節／書卷章節。
    - 一般模式仍保留 q/Q 離開、b/B 返回上一頁（含畫面與模式切換的完整紀錄）。
    - 預設不寫入任何檔案；執行 :setup-storage 後才會在使用者資料目錄建立
      bible-note.db（Windows 為 %APPDATA%\\bible-cli，macOS 為
      ~/Library/Application Support/bible-cli，其他為 $XDG_DATA_HOME/bible-cli
      或 ~/.local/share/bible-cli；可用環境變數 BIBLE_CLI_DATA_DIR 覆寫），
      並啟用 :option（設定，一般模式 o/O 同義）、:note／:N（筆記）、
      :bookmark／:M（書籤）、:reference（串珠，顯示於經節後方 a、b、c...，可點按跳轉）
      等指令；下次啟動只要偵測到該檔案仍在，即自動視為已啟用。

本檔案同時相容 Linux / macOS / Windows：
    - Windows 未內建 curses，需先執行 `pip install windows-curses` 才能使用 TUI，
      若未安裝，程式會提示安裝方式並自動退回 CLI 說明，而不會直接崩潰。
    - 啟動時會嘗試開啟 Windows 主控台的 VT100 / UTF-8 支援，讓 ANSI 顏色與中文字元
      在 cmd.exe / PowerShell 下也能正常顯示。
"""

import argparse
import ctypes
import datetime
import io
import locale
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import unicodedata
from html.parser import HTMLParser

from . import __version__
from .paths import (
    appDirName,
    dataDirEnvName,
    findSourceRoot,
    scriptDir,
    userDataDir,
)
from .resources import (
    detectResources,
    resolveResources,
    resourceSearchDirs,
    _sniffMybibleKind,
)
from .books import (
    bookAliasEn,
    bookAliasMap,
    bookAliasZh,
    _buildBookAliasMap,
    enBookNames,
    _normBookKey,
    resolveAnyBookName,
    zhBookNames,
)
from .storage import (
    findLegacyNoteDb,
    legacyDeclinedPath,
    legacyNoteDbPath,
    legacyNoteDbPointerPath,
    migrateLegacyNoteDb,
    noteDbDefaultPath,
    noteDbPointerPath,
    noteSchemaVersion,
    openNoteDb,
    resolveNoteDbPath,
    writeNoteDbPointer,
)
from .constants import (
    bold,
    cyan,
    dim,
    enLangs,
    introTypeLabel,
    missingContentMsg,
    needRecoveryMsg,
    red,
    reset,
    zhLangs,
)
from .console import (
    copyToClipboardText,
    isWindows,
    setupConsole,
    supportsAnsiColor,
)
from .sources.recovery import (
    bookDisplayName,
    connect,
    getFootnotes,
    getOutlines,
    RecoverySource,
    resolveBook,
)
from .sources.cuv import (
    CuvSource,
    strongTagPattern,
)
from .sources.strongdict import (
    connectDict,
    connectSqliteOrExit,
    connectStrongBible,
    normalizeStrongCode,
    StrongDictSource,
)
from .render import (
    DictHtmlRenderer,
    insertFootnoteMarkers,
    renderDictHtml,
    renderStrongVerse,
    splitStrongVerse,
)
from .cli import (
    buildParser,
    checkSourceCapabilities,
    cmdData,
    cmdIntro,
    cmdList,
    cmdNote,
    cmdOrig,
    cmdRead,
    cmdSearch,
    cmdStrong,
    launchInteractive,
    _loadStoredSettingsDict,
    main,
    noDatabaseMsg,
    normalizeModeName,
    printStrongDefinition,
    renderChapter,
    renderCuvChapter,
    resolveSourceKind,
)
from .tui.text import (
    cwidth,
    fitWidth,
    _isWordChar,
    Line,
    plainWrap,
    SegLine,
    wrapMarked,
)
from .tui.theme import (
    colorCmdLine,
    colorFootnote,
    colorHeader,
    colorHelp,
    colorOutline,
    colorSecondary,
    colorSection,
    optionFields,
)
from .tui.world import (
    World,
)
from .tui.app import (
    App,
)
from .tui.runner import (
    runTui,
    _tuiMain,
)
from .tui.repl import (
    _openSqliteSoft,
    _printOrigChapter,
    _printStrongDefinitionSafe,
    runStrongRepl,
)


if __name__ == "__main__":
    main()
