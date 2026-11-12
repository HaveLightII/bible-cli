"""啟動 curses 並執行 TUI。"""

import locale
import os
import sys

from ..console import isWindows
from ..paths import launchCommand
from ..sources.recovery import connect
from .app import App


def _tuiMain(stdscr, curses_mod, dbPath, strongBiblePath, dictPath, initialMode):
    conn = connect(dbPath) if dbPath else None
    app = App(
        curses_mod, stdscr, conn,
        strongBiblePath=strongBiblePath, dictPath=dictPath, initialMode=initialMode,
    )
    app.run()


def runTui(dbPath, strongBiblePath=None, dictPath=None, initialMode="books"):
    try:
        import curses
    except ImportError:
        sys.stderr.write(
            "無法載入 curses 模組，互動式 TUI 需要它才能執行。\n"
        )
        if isWindows:
            sys.stderr.write(
                "偵測到目前為 Windows 系統，請先執行下列指令安裝後再試一次：\n"
                "    pip install windows-curses\n\n"
            )
        sys.stderr.write("在此之前，您仍可使用 CLI 模式，例如：\n")
        sys.stderr.write(f"    {launchCommand()} list\n")
        sys.stderr.write(f"    {launchCommand()} read 創世記 1\n")
        sys.stderr.write(f"    {launchCommand()} orig 創世記 1\n")
        sys.exit(1)

    if dbPath and not os.path.exists(dbPath):
        dbPath = None

    try:
        locale.setlocale(locale.LC_ALL, "")
    except locale.Error:
        pass
    os.environ.setdefault("ESCDELAY", "25")

    curses.wrapper(_tuiMain, curses, dbPath, strongBiblePath, dictPath, initialMode)
