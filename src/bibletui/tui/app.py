"""curses 互動介面主體。"""

import os

from ..books import zhBookNames
from ..sources.recovery import RecoverySource
from .theme import (
    colorCmdLine,
    colorFootnote,
    colorHeader,
    colorHelp,
    colorOutline,
    colorSecondary,
    colorSection,
)
from .world import World
from .clipboard import ClipboardMixin
from .commands import CommandMixin
from .draw import DrawMixin
from .keys import KeyMixin
from .modules import ModuleMixin
from .navigation import NavigationMixin
from .notes import NotesMixin


class App(NavigationMixin, ClipboardMixin, NotesMixin, DrawMixin, KeyMixin, CommandMixin,
          ModuleMixin):
    _NAV_KEYS = (
        "mode", "showEn", "showCuv", "showOutline",
        "searchQuery", "searchInputText", "searchResults", "searchScroll", "searchIdx",
        "searchKind",
    )
    _WORLD_NAV_KEYS = (
        "bookIdx", "bookScroll",
        "selectedBookIndex", "chapterCount", "chapterIdx", "chapterScroll",
        "selectedChapter", "expanded", "readScroll",
    )

    def __init__(self, curses_mod, stdscr, conn, strongBiblePath=None,
                 dictPath=None, initialMode="books"):
        self.curses = curses_mod
        self.stdscr = stdscr
        self.conn = conn
        self.hasDb = conn is not None
        self.source = RecoverySource(conn) if conn is not None else None

        self.strongBiblePath = strongBiblePath
        self.dictPath = dictPath
        self.hasStrongBible = bool(strongBiblePath)
        self.strongModuleLabel = self._labelForModulePath(strongBiblePath)
        self.strongConn = None
        self.dictConn = None
        self.strongDefCache = {}

        self.mode = initialMode
        self.modeStack = []
        self.history = []
        self._quitPromptFrom = None
        self.statusMessage = None

        self.recoveryWorld = World(
            kind="recovery",
            books=self._loadBooks() if self.hasDb else [],
            booksTitle=" 書卷清單",
            chaptersTitleSuffix="",
            bookClickTag="book",
            chapterClickTag="chapter",
            booksMode="books",
            chaptersMode="chapters",
            readMode="read",
            backKeys=(27,),
            supportsSearch=True,
        )
        self.showEn = False
        self.showCuv = False
        self.showOutline = True

        self.searchQuery = ""
        self.searchInputText = ""
        self.searchResults = []
        self.searchScroll = 0
        self.searchIdx = 0
        self.searchKind = "recovery"
        self._cuvSearchSource = None

        self.strongWorld = World(
            kind="strong",
            books=list(enumerate(zhBookNames, start=1)) if self.hasStrongBible else [],
            booksTitle=(f" 書卷清單（{self.strongModuleLabel}）" if self.strongModuleLabel
                        else " 書卷清單（原文 Strong）"),
            chaptersTitleSuffix="（原文 Strong）",
            bookClickTag="strongbook",
            chapterClickTag="strongchapter",
            booksMode="strong_books",
            chaptersMode="strong_chapters",
            readMode="strong_read",
            backKeys=(27, self.curses.KEY_BACKSPACE, 127, 8),
            supportsSearch=True,
        )
        self._strongWordCodes = {}
        self.clickMapStrongWords = {}

        self.commandMode = False
        self.cmdBuffer = ""
        self.cmdError = None
        self._wantQuit = False
        self.helpScroll = 0
        self._helpTextLines = []

        self._textViewTitle = ""
        self._textViewRaw = ""
        self._textViewLines = []
        self._textViewScroll = 0
        self._textViewCacheW = None

        self.clickMapReadRefs = {}

        self.storageEnabled = False
        self.noteDbPath = None
        self.noteConn = None
        self.settings = {}
        self._optionFieldIdx = 0
        self._optionEditing = False
        self._optionEditBuffer = ""
        self._prevModeBeforeConfirm = None
        self._detectStorage()

    @staticmethod
    def _labelForModulePath(path):
        if not path:
            return ""
        from ..modules import moduleIdFromFile
        return moduleIdFromFile(os.path.basename(path))

    def run(self):
        curses = self.curses
        curses.curs_set(0)
        try:
            curses.mousemask(curses.ALL_MOUSE_EVENTS)
            curses.mouseinterval(0)
        except curses.error:
            pass
        self.stdscr.keypad(True)
        try:
            curses.start_color()
            curses.use_default_colors()
            curses.init_pair(colorOutline, curses.COLOR_YELLOW, -1)
            curses.init_pair(colorFootnote, curses.COLOR_RED, -1)
            curses.init_pair(colorSection, curses.COLOR_CYAN, -1)
            curses.init_pair(colorSecondary, curses.COLOR_WHITE, -1)
            curses.init_pair(colorHeader, curses.COLOR_BLACK, curses.COLOR_YELLOW)
            curses.init_pair(colorHelp, curses.COLOR_BLACK, curses.COLOR_WHITE)
            curses.init_pair(colorCmdLine, curses.COLOR_WHITE, -1)
        except curses.error:
            pass

        while True:
            self.draw()
            try:
                ch = self.stdscr.get_wch()
            except curses.error:
                continue
            if not self.handleKey(ch):
                break
