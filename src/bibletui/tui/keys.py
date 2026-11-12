"""按鍵、滑鼠與各畫面的輸入處理。"""

from ..constants import missingContentMsg
from .theme import optionFields


class KeyMixin:
    def _isTypingText(self):
        return self.mode == "search_input" or (self.mode == "option" and self._optionEditing)

    def _keyBooksFor(self, world, ch):
        curses = self.curses
        n = len(world.books)
        if ch in (curses.KEY_UP, ord("k")):
            world.bookIdx = max(0, world.bookIdx - 1)
        elif ch in (curses.KEY_DOWN, ord("j")):
            world.bookIdx = min(n - 1, world.bookIdx + 1)
        elif ch == curses.KEY_NPAGE or ch == ord(" "):
            world.bookIdx = min(n - 1, world.bookIdx + self._pageStep())
        elif ch == curses.KEY_PPAGE:
            world.bookIdx = max(0, world.bookIdx - self._pageStep())
        elif ch in (10, 13, curses.KEY_ENTER):
            self._enterBookFor(world)
        elif world.supportsSearch and ch == ord("/"):
            self._openSearch()
        elif ch in world.backKeys:
            self._goBack()
        return True

    def _enterBookFor(self, world):
        self._pushHistory()
        world.selectedBookIndex = world.books[world.bookIdx][0]
        world.chapterCount = self._maxChapterFor(world, world.selectedBookIndex)
        world.chapterIdx = 0
        world.chapterScroll = 0
        self.mode = world.chaptersMode

    def _keyChaptersFor(self, world, ch):
        curses = self.curses
        cols = max(1, (curses.COLS - 1) // 8) if hasattr(curses, "COLS") else 8
        if ch in (curses.KEY_UP, ord("k")):
            world.chapterIdx = max(0, world.chapterIdx - cols)
        elif ch in (curses.KEY_DOWN, ord("j")):
            world.chapterIdx = min(world.chapterCount - 1, world.chapterIdx + cols)
        elif ch in (curses.KEY_LEFT, ord("h")):
            world.chapterIdx = max(0, world.chapterIdx - 1)
        elif ch in (curses.KEY_RIGHT, ord("l")):
            world.chapterIdx = min(world.chapterCount - 1, world.chapterIdx + 1)
        elif ch == curses.KEY_NPAGE or ch == ord(" "):
            world.chapterIdx = min(
                world.chapterCount - 1, world.chapterIdx + self._pageStep() * cols
            )
        elif ch == curses.KEY_PPAGE:
            world.chapterIdx = max(0, world.chapterIdx - self._pageStep() * cols)
        elif ch in (10, 13, curses.KEY_ENTER):
            self._enterChapterFor(world)
        elif world.supportsSearch and ch == ord("/"):
            self._openSearch()
        elif ch in (27, curses.KEY_BACKSPACE, 127, 8):
            self._goBack()
        return True

    def _enterChapterFor(self, world):
        self._pushHistory()
        world.selectedChapter = world.chapterIdx + 1
        world.readScroll = 0
        world.expanded = set()
        self.mode = world.readMode

    def _keyStrongRead(self, ch):
        curses = self.curses
        world = self.strongWorld
        if ch in (curses.KEY_UP, ord("k")):
            world.readScroll = max(0, world.readScroll - 1)
        elif ch in (curses.KEY_DOWN, ord("j")):
            world.readScroll += 1
        elif ch == curses.KEY_NPAGE or ch == ord(" "):
            world.readScroll += self._pageStep()
        elif ch == curses.KEY_PPAGE:
            world.readScroll = max(0, world.readScroll - self._pageStep())
        elif ch in (curses.KEY_LEFT, ord("h")):
            if world.selectedChapter > 1:
                world.selectedChapter -= 1
                world.readScroll = 0
                world.expanded = set()
        elif ch in (curses.KEY_RIGHT, ord("l")):
            if world.selectedChapter < world.chapterCount:
                world.selectedChapter += 1
                world.readScroll = 0
                world.expanded = set()
        elif ch in (ord("e"), ord("c"), ord("n")):
            self.statusMessage = missingContentMsg
        elif ch in (ord("y"), ord("Y")):
            self._copyCurrentStrongVerse()
        elif ch == ord("/"):
            self._openSearch()
        elif ch in (27, curses.KEY_BACKSPACE, 127, 8):
            self._goBack()
        return True

    def _openTextView(self, title, bodyText):
        self._pushHistory()
        self._textViewTitle = title
        self._textViewRaw = bodyText
        self._textViewScroll = 0
        self._textViewCacheW = None
        self._textViewLines = []
        self.mode = "text_view"

    def _keyTextView(self, ch):
        curses = self.curses
        if ch in (curses.KEY_UP, ord("k")):
            self._textViewScroll = max(0, self._textViewScroll - 1)
        elif ch in (curses.KEY_DOWN, ord("j")):
            self._textViewScroll += 1
        elif ch == curses.KEY_NPAGE or ch == ord(" "):
            self._textViewScroll += self._pageStep()
        elif ch == curses.KEY_PPAGE:
            self._textViewScroll = max(0, self._textViewScroll - self._pageStep())
        elif ch in (27, curses.KEY_BACKSPACE, 127, 8):
            self._goBack()
        return True

    def _keyOption(self, ch):
        curses = self.curses
        if self._optionEditing:
            if ch in (10, 13, curses.KEY_ENTER):
                key, _label = optionFields[self._optionFieldIdx]
                self._applyOptionValue(key, self._optionEditBuffer.strip())
                self._optionEditing = False
            elif ch == 27:
                self._optionEditing = False
            elif ch in (curses.KEY_BACKSPACE, 127, 8):
                self._optionEditBuffer = self._optionEditBuffer[:-1]
            elif 32 <= ch < 0x110000:
                try:
                    self._optionEditBuffer += chr(ch)
                except ValueError:
                    pass
            return True
        if ch in (curses.KEY_UP, ord("k")):
            self._optionFieldIdx = max(0, self._optionFieldIdx - 1)
        elif ch in (curses.KEY_DOWN, ord("j")):
            self._optionFieldIdx = min(len(optionFields) - 1, self._optionFieldIdx + 1)
        elif ch in (10, 13, curses.KEY_ENTER):
            key, _label = optionFields[self._optionFieldIdx]
            self._optionEditBuffer = self.settings.get(key, "") or ""
            self._optionEditing = True
        elif ch in (27, curses.KEY_BACKSPACE, 127, 8):
            self._goBack()
        return True

    def _keyHelp(self, ch):
        curses = self.curses
        if ch in (curses.KEY_UP, ord("k")):
            self.helpScroll = max(0, self.helpScroll - 1)
        elif ch in (curses.KEY_DOWN, ord("j")):
            self.helpScroll += 1
        elif ch == curses.KEY_NPAGE or ch == ord(" "):
            self.helpScroll += self._pageStep()
        elif ch == curses.KEY_PPAGE:
            self.helpScroll = max(0, self.helpScroll - self._pageStep())
        else:
            self.mode = self.modeStack.pop() if self.modeStack else "books"
        return True

    def handleKey(self, ch):
        curses = self.curses
        if isinstance(ch, str):
            ch = ord(ch)
        self.statusMessage = None
        self.cmdError = None

        if ch == curses.KEY_MOUSE:
            if self.commandMode:
                try:
                    curses.getmouse()
                except curses.error:
                    pass
                return True
            try:
                _, mx, my, _, bstate = curses.getmouse()
            except curses.error:
                if not hasattr(curses, "BUTTON5_PRESSED"):
                    self._scrollCurrent(3)
                return True
            self._handleMouse(my, mx, bstate)
            return True

        if self.commandMode:
            return self._handleCommandModeKey(ch)

        if self.mode == "confirm_quit":
            if ch in (ord("y"), ord("Y")):
                return False
            if ch in (ord("n"), ord("N"), 27):
                self.mode = self._quitPromptFrom
                self._quitPromptFrom = None
            return True

        if self.mode == "confirm_option_reset":
            if ch in (ord("y"), ord("Y")):
                self._resetSettings()
                self.mode = self._prevModeBeforeConfirm or "books"
                self._prevModeBeforeConfirm = None
            elif ch in (ord("n"), ord("N"), 27):
                self.mode = self._prevModeBeforeConfirm or "books"
                self._prevModeBeforeConfirm = None
            return True

        if ch == ord("?") and self.mode != "help":
            self._cmdHelp()
            return True
        if self.mode == "help":
            return self._keyHelp(ch)

        if ch == ord(":") and not self._isTypingText():
            self.commandMode = True
            self.cmdBuffer = ""
            self.cmdError = None
            return True

        if ch == ord("Q") and not self._isTypingText():
            return False
        if ch == ord("q") and not self._isTypingText():
            self._quitPromptFrom = self.mode
            self.mode = "confirm_quit"
            return True
        if ch in (ord("b"), ord("B")) and not self._isTypingText():
            self._goBack()
            return True

        if not self._isTypingText():
            if ch in (ord("s"), ord("S")) and self.hasStrongBible and not self.mode.startswith("strong"):
                self._pushHistory()
                self.mode = "strong_books"
                return True
            if ch in (ord("r"), ord("R")) and self.hasDb and self.mode.startswith("strong"):
                self._pushHistory()
                self.mode = "books"
                return True
            if ch in (ord("o"), ord("O")) and self.storageEnabled and self.mode != "option":
                self._cmdOption([])
                return True

        if self.mode == "books":
            return self._keyBooksFor(self.recoveryWorld, ch)
        elif self.mode == "chapters":
            return self._keyChaptersFor(self.recoveryWorld, ch)
        elif self.mode == "read":
            return self._keyRead(ch)
        elif self.mode == "search_input":
            return self._keySearchInput(ch)
        elif self.mode == "search_results":
            return self._keySearchResults(ch)
        elif self.mode == "strong_books":
            return self._keyBooksFor(self.strongWorld, ch)
        elif self.mode == "strong_chapters":
            return self._keyChaptersFor(self.strongWorld, ch)
        elif self.mode == "strong_read":
            return self._keyStrongRead(ch)
        elif self.mode == "option":
            return self._keyOption(ch)
        elif self.mode == "text_view":
            return self._keyTextView(ch)
        return True

    def _handleMouse(self, y, x, bstate):
        curses = self.curses
        if bstate & getattr(curses, "BUTTON4_PRESSED", 0):
            self._scrollCurrent(-3)
            return
        if bstate & getattr(curses, "BUTTON5_PRESSED", 0):
            self._scrollCurrent(3)
            return
        clicked = bool(bstate & (curses.BUTTON1_CLICKED | curses.BUTTON1_PRESSED | curses.BUTTON1_DOUBLE_CLICKED))
        if not clicked:
            return
        if self.mode == "books":
            item = self.clickMap.get(y)
            if item and item[0] == self.recoveryWorld.bookClickTag:
                self.recoveryWorld.bookIdx = item[1]
                self._enterBookFor(self.recoveryWorld)
        elif self.mode == "chapters":
            for key, item in self.clickMap.items():
                if isinstance(key, tuple) and key[0] == y:
                    self.recoveryWorld.chapterIdx = item[1]
                    self._enterChapterFor(self.recoveryWorld)
                    break
        elif self.mode == "read":
            refRegions = self.clickMapReadRefs.get(y)
            jumped = False
            if refRegions:
                for xs, xe, target in refRegions:
                    if xs <= x < xe:
                        tb, tc, ts = target
                        self._jumpRecovery(tb, tc, ts)
                        jumped = True
                        break
            if not jumped:
                section = self.clickMapRead.get(y)
                if section is not None:
                    self._toggleExpandSection(section)
        elif self.mode == "search_results":
            item = self.clickMap.get(y)
            if item and item[0] == "search_result":
                self.searchIdx = item[1]
                self._gotoSearchResult()
        elif self.mode == "strong_books":
            item = self.clickMap.get(y)
            if item and item[0] == self.strongWorld.bookClickTag:
                self.strongWorld.bookIdx = item[1]
                self._enterBookFor(self.strongWorld)
        elif self.mode == "strong_chapters":
            for key, item in self.clickMap.items():
                if isinstance(key, tuple) and key[0] == y:
                    self.strongWorld.chapterIdx = item[1]
                    self._enterChapterFor(self.strongWorld)
                    break
        elif self.mode == "strong_read":
            regions = self.clickMapStrongWords.get(y)
            if regions:
                for xs, xe, key in regions:
                    if xs <= x < xe:
                        expanded = self.strongWorld.expanded
                        if key in expanded:
                            expanded.discard(key)
                        else:
                            expanded.add(key)
                        break

    def _scrollCurrent(self, delta):
        if self.mode == "books":
            r = self.recoveryWorld
            r.bookIdx = max(0, min(len(r.books) - 1, r.bookIdx + delta))
        elif self.mode == "chapters":
            self.recoveryWorld.chapterScroll = max(0, self.recoveryWorld.chapterScroll + delta)
        elif self.mode == "read":
            self.recoveryWorld.readScroll = max(0, self.recoveryWorld.readScroll + delta)
        elif self.mode == "search_results":
            self.searchIdx = max(0, min(len(self.searchResults) - 1, self.searchIdx + delta))
        elif self.mode == "strong_books":
            s = self.strongWorld
            s.bookIdx = max(0, min(len(s.books) - 1, s.bookIdx + delta))
        elif self.mode == "strong_chapters":
            self.strongWorld.chapterScroll = max(0, self.strongWorld.chapterScroll + delta)
        elif self.mode == "strong_read":
            self.strongWorld.readScroll = max(0, self.strongWorld.readScroll + delta)
        elif self.mode == "text_view":
            self._textViewScroll = max(0, self._textViewScroll + delta)
        elif self.mode == "help":
            self.helpScroll = max(0, self.helpScroll + delta)

    def _keyRead(self, ch):
        curses = self.curses
        world = self.recoveryWorld
        if ch in (curses.KEY_UP, ord("k")):
            world.readScroll = max(0, world.readScroll - 1)
        elif ch in (curses.KEY_DOWN, ord("j")):
            world.readScroll += 1
        elif ch == curses.KEY_NPAGE or ch == ord(" "):
            world.readScroll += self._pageStep()
        elif ch == curses.KEY_PPAGE:
            world.readScroll = max(0, world.readScroll - self._pageStep())
        elif ch in (curses.KEY_LEFT, ord("h")):
            if world.selectedChapter > 1:
                world.selectedChapter -= 1
                world.readScroll = 0
                world.expanded = set()
        elif ch in (curses.KEY_RIGHT, ord("l")):
            if world.selectedChapter < world.chapterCount:
                world.selectedChapter += 1
                world.readScroll = 0
                world.expanded = set()
        elif ch == ord("e"):
            self.showEn = not self.showEn
        elif ch == ord("c"):
            self.showCuv = not self.showCuv
        elif ch == ord("n"):
            self.showOutline = not self.showOutline
        elif ch in (10, 13, curses.KEY_ENTER):
            section = self._currentReadSection()
            if section is not None:
                self._toggleExpandSection(section)
        elif ch in (ord("y"), ord("Y")):
            self._copyCurrentVerse()
        elif ch == ord("/"):
            self._openSearch()
        elif ch in (27, curses.KEY_BACKSPACE, 127, 8):
            self._goBack()
        return True

    def _keySearchInput(self, ch):
        curses = self.curses
        if ch in (10, 13, curses.KEY_ENTER):
            self._runSearch()
            self.mode = "search_results"
        elif ch == 27:
            self._goBack()
        elif ch in (curses.KEY_BACKSPACE, 127, 8):
            self.searchInputText = self.searchInputText[:-1]
        elif 32 <= ch < 0x110000:
            try:
                self.searchInputText += chr(ch)
            except ValueError:
                pass
        return True

    def _runSearch(self):
        kind = self.searchKind
        tokens = self.searchInputText.split()
        parsed = self._parseSearchTokens(tokens)
        problem = self._searchUnavailable(kind, bool(parsed and parsed[0]))
        if problem:
            self.statusMessage = problem
            self.searchResults = []
            return
        if parsed is None:
            self.searchResults = []
            return
        useEnglish, includeTerms, excludeTerms = parsed
        if kind == "strong":
            label, results = self._execStrongSearch(includeTerms, excludeTerms)
        else:
            label, results = self._execSearchQuery(useEnglish, includeTerms, excludeTerms)
        self.searchQuery = label
        self.searchResults = results
        self.searchIdx = 0
        self.searchScroll = 0

    def _keySearchResults(self, ch):
        curses = self.curses
        if ch in (curses.KEY_UP, ord("k")):
            self.searchIdx = max(0, self.searchIdx - 1)
        elif ch in (curses.KEY_DOWN, ord("j")):
            self.searchIdx = min(len(self.searchResults) - 1, self.searchIdx + 1)
        elif ch == curses.KEY_NPAGE or ch == ord(" "):
            self.searchIdx = min(len(self.searchResults) - 1, self.searchIdx + self._pageStep())
        elif ch == curses.KEY_PPAGE:
            self.searchIdx = max(0, self.searchIdx - self._pageStep())
        elif ch in (10, 13, curses.KEY_ENTER):
            self._gotoSearchResult()
        elif ch == ord("/"):
            self._pushHistory()
            self.mode = "search_input"
        elif ch in (27, curses.KEY_BACKSPACE, 127, 8):
            self._goBack()
        return True

    def _gotoSearchResult(self):
        if not self.searchResults:
            return
        r = self.searchResults[self.searchIdx]
        if self.searchKind == "strong":
            self._jumpStrong(r["book_index"], r["chapter"], r["section"])
            return
        self._pushHistory()
        world = self.recoveryWorld
        world.selectedBookIndex = r["book_index"]
        world.chapterCount = self._maxChapterFor(world, world.selectedBookIndex)
        world.selectedChapter = r["chapter"]
        world.readScroll = 0
        world.expanded = {r["section"]}
        self.mode = "read"
