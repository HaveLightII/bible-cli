""": 指令模式與搜尋指令。"""

from ..books import resolveAnyBookName
from ..constants import (
    introTypeLabel,
    missingContentMsg,
    needRecoveryMsg,
)
from ..sources.cuv import CuvSource
from ..sources.recovery import bookDisplayName


class CommandMixin:
    def _searchKindHere(self):
        if self.mode in ("strong_books", "strong_chapters", "strong_read"):
            return "strong"
        if self.mode in ("search_input", "search_results"):
            return self.searchKind
        return "recovery"

    def _openSearch(self):
        kind = self._searchKindHere()
        self._pushHistory()
        if self.searchKind != kind:
            self.searchKind = kind
            self.searchQuery = ""
            self.searchInputText = ""
            self.searchResults = []
            self.searchScroll = 0
            self.searchIdx = 0
        if self.searchQuery and self.searchResults:
            self.mode = "search_results"
        else:
            self.mode = "search_input"

    def _setCmdError(self, message):
        self.cmdError = message

    def _cmdHelp(self):
        self.modeStack.append(self.mode)
        self.helpScroll = 0
        self._helpTextLines = self._buildHelpLines()
        self.mode = "help"

    def _handleCommandModeKey(self, ch):
        curses = self.curses
        if ch in (10, 13, curses.KEY_ENTER):
            cmdline = self.cmdBuffer
            self.commandMode = False
            self.cmdBuffer = ""
            self._executeCommand(cmdline)
            if self._wantQuit:
                return False
            return True
        if ch == 27:
            self.commandMode = False
            self.cmdBuffer = ""
            return True
        if ch in (curses.KEY_BACKSPACE, 127, 8):
            self.cmdBuffer = self.cmdBuffer[:-1]
            return True
        if 32 <= ch < 0x110000:
            try:
                self.cmdBuffer += chr(ch)
            except ValueError:
                pass
            return True
        return True

    def _executeCommand(self, cmdline):
        cmdline = cmdline.strip()
        self.cmdError = None
        if not cmdline:
            return
        tokens = cmdline.split()
        head = tokens[0]
        rest = tokens[1:]
        headLower = head.lower()
        try:
            if head == "q":
                self._quitPromptFrom = self.mode
                self.mode = "confirm_quit"
            elif head == "Q":
                self._wantQuit = True
            elif headLower == "strong" or head == "S":
                self._cmdSwitchMode(rest, toStrong=True)
            elif headLower == "recovery" or head == "R":
                self._cmdSwitchMode(rest, toStrong=False)
            elif headLower == "footnote" or head == "F":
                self._cmdFootnote(rest)
            elif headLower == "intro":
                self._cmdIntro(rest)
            elif headLower == "copy" or head == "C":
                self._cmdCopy(rest)
            elif headLower == "english" or head == "E":
                self._cmdToggle(rest, "showEn", "英文對照")
            elif headLower == "outline" or head == "O":
                self._cmdToggle(rest, "showOutline", "綱目及註解")
            elif headLower in ("search", "find"):
                self._cmdSearch(rest)
            elif headLower == "help":
                self._cmdHelp()
            elif headLower == "setup-storage":
                self._cmdSetupStorage()
            elif headLower == "option":
                self._cmdOption(rest)
            elif headLower == "note" or head == "N":
                self._cmdNote(rest)
            elif headLower in ("bookmark", "mark") or head == "M":
                self._cmdBookmark(rest)
            elif headLower in ("reference", "ref"):
                self._cmdReference(rest)
            else:
                self._cmdGoto(tokens)
        except Exception as e:
            self.cmdError = f"指令執行錯誤: {e}"

    def _cmdGoto(self, tokens):
        inStrongWorld = self.mode.startswith("strong")
        ctxBook, ctxChapter, _ = self._currentContextRef()
        if ctxBook is None:
            if inStrongWorld:
                ctxBook, ctxChapter = self.strongWorld.selectedBookIndex, self.strongWorld.selectedChapter
            else:
                ctxBook, ctxChapter = self.recoveryWorld.selectedBookIndex, self.recoveryWorld.selectedChapter
        try:
            bookIndex, chapter, section = self._parseRefArgs(tokens, ctxBook, ctxChapter)
        except ValueError as e:
            self._setCmdError(str(e))
            return
        if inStrongWorld:
            if not self.hasStrongBible:
                self._setCmdError("找不到原文 Strong 聖經模組")
                return
            self._jumpStrong(bookIndex, chapter, section)
        else:
            if not self.hasDb:
                self._setCmdError("找不到恢復本資料庫")
                return
            self._jumpRecovery(bookIndex, chapter, section)

    def _cmdSwitchMode(self, tokens, toStrong):
        if not tokens:
            if self.mode == "read" and self.recoveryWorld.selectedBookIndex and self.recoveryWorld.selectedChapter:
                ctxBook, ctxChapter = self.recoveryWorld.selectedBookIndex, self.recoveryWorld.selectedChapter
            elif self.mode == "strong_read" and self.strongWorld.selectedBookIndex and self.strongWorld.selectedChapter:
                ctxBook, ctxChapter = self.strongWorld.selectedBookIndex, self.strongWorld.selectedChapter
            else:
                ctxBook, ctxChapter = None, None
            if ctxBook and ctxChapter:
                if toStrong:
                    if not self.hasStrongBible:
                        self._setCmdError("找不到原文 Strong 聖經模組")
                        return
                    self._jumpStrong(ctxBook, ctxChapter, None)
                else:
                    if not self.hasDb:
                        self._setCmdError("找不到恢復本資料庫")
                        return
                    self._jumpRecovery(ctxBook, ctxChapter, None)
            else:
                if toStrong and not self.hasStrongBible:
                    self._setCmdError("找不到原文 Strong 聖經模組")
                    return
                if (not toStrong) and not self.hasDb:
                    self._setCmdError("找不到恢復本資料庫")
                    return
                self._pushHistory()
                self.mode = "strong_books" if toStrong else "books"
            return
        ctxBook, ctxChapter, _ = self._currentContextRef()
        try:
            bookIndex, chapter, section = self._parseRefArgs(tokens, ctxBook, ctxChapter)
        except ValueError as e:
            self._setCmdError(str(e))
            return
        if toStrong:
            if not self.hasStrongBible:
                self._setCmdError("找不到原文 Strong 聖經模組")
                return
            self._jumpStrong(bookIndex, chapter, section)
        else:
            if not self.hasDb:
                self._setCmdError("找不到恢復本資料庫")
                return
            self._jumpRecovery(bookIndex, chapter, section)

    def _cmdFootnote(self, tokens):
        if not self.hasDb:
            self._setCmdError(needRecoveryMsg)
            return
        if not tokens:
            if self.mode == "read" and self.recoveryWorld.selectedBookIndex and self.recoveryWorld.selectedChapter:
                section = self._currentReadSection()
                if section is None:
                    self._setCmdError("目前沒有可顯示註解的經節")
                    return
                self._forceExpandSection(section)
                return
            if self.mode == "strong_read" and self.strongWorld.selectedBookIndex and self.strongWorld.selectedChapter:
                verse = self._currentStrongReadVerse()
                if verse is None:
                    self._setCmdError("目前沒有可顯示註解的經節")
                    return
                self._jumpRecovery(self.strongWorld.selectedBookIndex, self.strongWorld.selectedChapter, verse)
                self._forceExpandSection(verse)
                return
            self._setCmdError("目前不在章節內，請提供完整卷章節")
            return
        ctxBook, ctxChapter, _ = self._currentContextRef()
        try:
            bookIndex, chapter, section = self._parseRefArgs(tokens, ctxBook, ctxChapter)
        except ValueError as e:
            self._setCmdError(str(e))
            return
        if section is None:
            self._setCmdError("請指定節數")
            return
        self._jumpRecovery(bookIndex, chapter, section)
        self._forceExpandSection(section)

    def _cmdIntro(self, tokens):
        if not self.hasDb:
            self._setCmdError(needRecoveryMsg)
            return
        if tokens:
            name = " ".join(tokens)
            bookIndex = resolveAnyBookName(name, self.conn)
            if bookIndex is None:
                self._setCmdError(f"找不到書卷: {name}")
                return
        else:
            bookIndex = self._currentAnyBook()
            if bookIndex is None:
                self._setCmdError("目前未選擇書卷")
                return
        bookName = bookDisplayName(self.conn, bookIndex, "big5")
        rows = self.source.intros(bookIndex)
        if not rows:
            text = "（查無書卷簡介）"
        else:
            parts = []
            for r in rows:
                label = introTypeLabel.get(r["type"], f"type{r['type']}")
                parts.append(f"{label}\n{r['intro']}")
            text = "\n\n".join(parts)
        self._openTextView(f"{bookName} 書卷簡介", text)

    def _cmdCopy(self, tokens):
        if not tokens:
            if self.mode == "read":
                self._copyCurrentVerse()
            elif self.mode == "strong_read":
                self._copyCurrentStrongVerse()
            else:
                self._setCmdError("目前沒有可複製的經節")
            return
        footnoteMode = tokens[0].startswith("#")
        sections = []
        for tok in tokens:
            if footnoteMode != tok.startswith("#"):
                self._setCmdError("請統一使用 # 前綴以複製註解，或省略以複製經文")
                return
            t = tok[1:] if footnoteMode else tok
            try:
                if "-" in t:
                    a, b = t.split("-", 1)
                    a, b = int(a), int(b)
                    sections.extend(range(min(a, b), max(a, b) + 1))
                else:
                    sections.append(int(t))
            except ValueError:
                self._setCmdError("格式錯誤，請用 1 3-5 7 這樣的格式")
                return
        ctxBook, ctxChapter, _ = self._currentContextRef()
        if ctxBook is None or ctxChapter is None:
            self._setCmdError("目前不在章節內")
            return
        if footnoteMode:
            self._copyFootnotesForSections(ctxBook, ctxChapter, sections)
        else:
            self._copyVersesForSections(ctxBook, ctxChapter, sections, fromStrong=(self.mode == "strong_read"))

    def _cmdToggle(self, tokens, attrName, label):
        if self.mode.startswith("strong"):
            self._setCmdError(missingContentMsg)
            return
        if not tokens:
            setattr(self, attrName, not getattr(self, attrName))
        elif tokens[0].lower() == "on":
            setattr(self, attrName, True)
        elif tokens[0].lower() == "off":
            setattr(self, attrName, False)
        else:
            self._setCmdError("請用 on 或 off，或不帶參數直接切換")
            return
        self.recoveryWorld.cacheKey = None
        state = "開啟" if getattr(self, attrName) else "關閉"
        self.statusMessage = f"已{state}{label}"

    def _parseSearchTokens(self, tokens):
        useEnglish = False
        if tokens and tokens[0] == "-e":
            useEnglish = True
            tokens = tokens[1:]
        includeTerms, excludeTerms = [], []
        excludeMode = False
        for tok in tokens:
            if tok == "--exclude":
                excludeMode = True
                continue
            (excludeTerms if excludeMode else includeTerms).append(tok)
        if not includeTerms:
            return None
        return useEnglish, includeTerms, excludeTerms

    def _searchLabel(self, includeTerms, excludeTerms):
        label = "／".join(includeTerms)
        if excludeTerms:
            label += "　排除：" + "／".join(excludeTerms)
        return label

    def _execSearchQuery(self, useEnglish, includeTerms, excludeTerms):
        lang = "eng" if useEnglish else ("cuv_big5" if self.showCuv else "big5")
        results = self.source.search(lang, includeTerms, excludeTerms)
        return self._searchLabel(includeTerms, excludeTerms), results

    def _execStrongSearch(self, includeTerms, excludeTerms):
        if self._cuvSearchSource is None:
            self._cuvSearchSource = CuvSource(self._openStrongConn())
        results = self._cuvSearchSource.search(includeTerms, excludeTerms)
        return self._searchLabel(includeTerms, excludeTerms), results

    def _searchUnavailable(self, kind, useEnglish=False):
        if kind == "strong":
            if not self.hasStrongBible or self._openStrongConn() is None:
                return "找不到和合本資料庫"
            if useEnglish:
                return "和合本不含英文，-e 不適用"
            return None
        if not self.hasDb:
            return "找不到恢復本資料庫"
        return None

    def _cmdSearch(self, tokens):
        kind = self._searchKindHere()
        parsed = self._parseSearchTokens(tokens)
        problem = self._searchUnavailable(kind, bool(parsed and parsed[0]))
        if problem:
            self._setCmdError(problem)
            return
        if parsed is None:
            self._setCmdError("請至少輸入一個搜尋字串")
            return
        useEnglish, includeTerms, excludeTerms = parsed
        if kind == "strong":
            label, results = self._execStrongSearch(includeTerms, excludeTerms)
        else:
            label, results = self._execSearchQuery(useEnglish, includeTerms, excludeTerms)
        self._pushHistory()
        self.searchKind = kind
        self.searchInputText = " ".join(tokens)
        self.searchQuery = label
        self.searchResults = results
        self.searchIdx = 0
        self.searchScroll = 0
        self.mode = "search_results"
