"""畫面繪製與顯示行建構。"""

from ..books import (
    enBookNames,
    zhBookNames,
)
from ..render import (
    renderDictHtml,
    splitStrongVerse,
)
from ..sources.cuv import CuvSource
from ..sources.recovery import (
    bookDisplayName,
    getFootnotes,
    getOutlines,
)
from ..sources.strongdict import StrongDictSource
from .repl import _openSqliteSoft
from .text import (
    Line,
    SegLine,
    cwidth,
    fitWidth,
    plainWrap,
    wrapMarked,
)
from .theme import (
    colorCmdLine,
    colorFootnote,
    colorHeader,
    colorHelp,
    colorOutline,
    colorSecondary,
    colorSection,
    optionFields,
)


class DrawMixin:
    def draw(self):
        self.stdscr.erase()
        h, w = self.stdscr.getmaxyx()
        if self.mode == "confirm_quit":
            drawMode = self._quitPromptFrom
        elif self.mode == "confirm_option_reset":
            drawMode = self._prevModeBeforeConfirm
        else:
            drawMode = self.mode
        if drawMode == "books":
            self._drawBooksFor(self.recoveryWorld, h, w)
        elif drawMode == "chapters":
            self._drawChaptersFor(self.recoveryWorld, h, w)
        elif drawMode == "read":
            self.drawRead(h, w)
        elif drawMode == "search_input":
            self.drawSearchInput(h, w)
        elif drawMode == "search_results":
            self.drawSearchResults(h, w)
        elif drawMode == "strong_books":
            self._drawBooksFor(self.strongWorld, h, w)
        elif drawMode == "strong_chapters":
            self._drawChaptersFor(self.strongWorld, h, w)
        elif drawMode == "strong_read":
            self.drawStrongRead(h, w)
        elif drawMode == "help":
            self.drawHelp(h, w)
        elif drawMode == "option":
            self.drawOption(h, w)
        elif drawMode == "text_view":
            self.drawTextView(h, w)
        if self.mode == "confirm_quit":
            self._drawConfirmPrompt(h, w, " 確定要離開程式嗎？(y/n) ")
        elif self.mode == "confirm_option_reset":
            self._drawConfirmPrompt(h, w, " 確定要重設所有設定嗎？(y/n) ")
        self.drawStatus(h, w)
        self.stdscr.refresh()

    def _drawConfirmPrompt(self, h, w, text):
        curses = self.curses
        y = h // 2
        x = max(0, (w - len(text)) // 2)
        try:
            self.stdscr.addstr(y, x, text[: max(0, w - 1)], curses.color_pair(colorHeader) | curses.A_BOLD)
        except curses.error:
            pass

    def drawStatus(self, h, w):
        curses = self.curses
        if self.commandMode:
            text = ":" + self.cmdBuffer
            attr = curses.color_pair(colorCmdLine) | curses.A_BOLD
            text = text[: max(0, w - 1)]
            try:
                self.stdscr.move(h - 1, 0)
                self.stdscr.clrtoeol()
                self.stdscr.addstr(h - 1, 0, text, attr)
            except curses.error:
                pass
            return
        if self.cmdError:
            text = self.cmdError
        else:
            text = self.statusMessage or ""
        text = text[: max(0, w - 1)]
        try:
            self.stdscr.addstr(h - 1, 0, text.ljust(w - 1), curses.color_pair(colorHelp))
        except curses.error:
            pass

    def _title(self, text, w):
        curses = self.curses
        try:
            self.stdscr.addstr(0, 0, fitWidth(text, w - 1), curses.color_pair(colorHeader) | curses.A_BOLD)
        except curses.error:
            pass

    def _bookNameFor(self, world, bookIndex):
        if world.kind == "strong":
            return zhBookNames[bookIndex - 1]
        return bookDisplayName(self.conn, bookIndex, "big5")

    def _drawBooksFor(self, world, h, w):
        curses = self.curses
        self._title(world.booksTitle, w)
        visible = h - 2
        if world.bookIdx < world.bookScroll:
            world.bookScroll = world.bookIdx
        if world.bookIdx >= world.bookScroll + visible:
            world.bookScroll = world.bookIdx - visible + 1

        self.clickMap = {}
        for rowI, (idx, name) in enumerate(world.books[world.bookScroll:world.bookScroll + visible]):
            y = rowI + 1
            testament = "舊約" if idx <= 39 else "新約"
            label = f"{idx:>3}  {name}  ({testament})"
            attr = curses.A_REVERSE if world.bookScroll + rowI == world.bookIdx else 0
            try:
                self.stdscr.addstr(y, 0, label[: w - 1].ljust(w - 1), attr)
            except curses.error:
                pass
            self.clickMap[y] = (world.bookClickTag, world.bookScroll + rowI)

    def _drawChaptersFor(self, world, h, w):
        curses = self.curses
        name = self._bookNameFor(world, world.selectedBookIndex)
        self._title(f" {name}{world.chaptersTitleSuffix}", w)
        visible = h - 2
        cols = max(1, (w - 1) // 8)
        self.clickMap = {}
        for i in range(world.chapterCount):
            row = i // cols
            col = i % cols
            y = row + 1 - world.chapterScroll
            if y < 1 or y > h - 2:
                continue
            x = col * 8
            label = f"第{i+1:>3}章"
            attr = curses.A_REVERSE if i == world.chapterIdx else 0
            try:
                self.stdscr.addstr(y, x, label, attr)
            except curses.error:
                pass
            self.clickMap[(y, col)] = (world.chapterClickTag, i)

    def _buildReadLines(self, w):
        curses = self.curses
        bookIndex = self.recoveryWorld.selectedBookIndex
        chapter = self.recoveryWorld.selectedChapter
        langPrimary = "cuv_big5" if self.showCuv else "big5"
        rows = self.source.chapterRows(bookIndex, chapter, langPrimary)
        outlines = getOutlines(self.conn, langPrimary, bookIndex, chapter) if self.showOutline else {}
        secondaryMap = {}
        if self.showEn:
            srows = self.source.chapterRows(bookIndex, chapter, "eng")
            secondaryMap = {r["section"]: r["content"] for r in srows}

        fnEnabled = self.showOutline
        refsBySection = {}
        if self.storageEnabled:
            noteConn = self._openNoteDb()
            if noteConn is not None:
                for rr in noteConn.execute(
                    "SELECT section, label, target_book, target_chapter, target_section FROM refs "
                    "WHERE book=? AND chapter=? ORDER BY section, label",
                    (bookIndex, chapter),
                ).fetchall():
                    refsBySection.setdefault(rr["section"], []).append(rr)

        lines = []
        verseRow = {}
        indentUnit = "  "
        for r in rows:
            section = r["section"]
            for o in outlines.get(section, []):
                indent = indentUnit * (o["level"] - 1)
                for wl in plainWrap(indent + o["outline"], w - 1):
                    lines.append(Line([("".join(c for c, _ in wl), colorOutline | curses.A_BOLD, None)]))
            fn = getFootnotes(self.conn, langPrimary, bookIndex, chapter, section) if fnEnabled else []
            fnPairs = [(f["location"], f["seq"]) for f in fn]
            chars = []
            content = r["content"]
            marks = {loc - 1: seq for loc, seq in fnPairs}
            for i, c in enumerate(content):
                if i in marks:
                    for mc in str(marks[i]):
                        chars.append((mc, colorFootnote))
                chars.append((c, 0))
            for rr in refsBySection.get(section, []):
                target = (rr["target_book"], rr["target_chapter"], rr["target_section"])
                chars.append((rr["label"], ("ref", target)))
            prefix = f"{section:>3}  "
            wrapped = wrapMarked([(c, 0) for c in prefix] + chars, w - 1)
            verseRow[section] = len(lines)
            for wi, wl in enumerate(wrapped):
                segs = []
                curFlag = None
                buf = ""
                for c, flag in wl:
                    if flag != curFlag:
                        if buf:
                            segs.append(self._readSegment(buf, curFlag))
                        buf = c
                        curFlag = flag
                    else:
                        buf += c
                if buf:
                    segs.append(self._readSegment(buf, curFlag))
                lines.append(Line(segs, section=section, clickable=True))

            if self.showEn and section in secondaryMap:
                for wl in plainWrap("     " + secondaryMap[section], w - 1):
                    lines.append(Line([("".join(c for c, _ in wl), colorSecondary, None)], section=section))

            if fnEnabled and section in self.recoveryWorld.expanded:
                for f in fn:
                    label = f"      [{f['seq']}] "
                    for wl in plainWrap(label + (f["note"] or ""), w - 1):
                        lines.append(Line([("".join(c for c, _ in wl), colorSecondary, None)]))
            lines.append(Line([("", 0, None)]))
        return lines, verseRow

    @staticmethod
    def _readSegment(text, flag):
        if isinstance(flag, tuple) and flag and flag[0] == "ref":
            return (text, colorSection, flag[1])
        return (text, flag if isinstance(flag, int) else 0, None)

    def drawRead(self, h, w):
        curses = self.curses
        world = self.recoveryWorld
        name = bookDisplayName(self.conn, world.selectedBookIndex, "big5")
        flags = []
        if self.showEn:
            flags.append("英文")
        if self.showCuv:
            flags.append("和合本")
        flagS = ("　[" + "／".join(flags) + "]") if flags else ""
        self._title(f" {name} 第{world.selectedChapter}章{flagS}", w)

        cacheKey = (
            world.selectedBookIndex,
            world.selectedChapter,
            self.showEn,
            self.showCuv,
            self.showOutline,
            frozenset(world.expanded),
        )
        if cacheKey != world.cacheKey or w != world.cacheW:
            world.readLines, world.verseRow = self._buildReadLines(w)
            world.cacheKey = cacheKey
            world.cacheW = w
        visible = h - 2
        maxScroll = max(0, len(world.readLines) - visible)
        world.readScroll = max(0, min(world.readScroll, maxScroll))

        self.clickMapRead = {}
        self.clickMapReadRefs = {}
        for rowI, line in enumerate(world.readLines[world.readScroll:world.readScroll + visible]):
            y = rowI + 1
            x = 0
            regions = []
            for text, attr, refTarget in line.segments:
                color = curses.color_pair(attr & 0xF) if attr else 0
                try:
                    self.stdscr.addstr(y, x, text, color | (curses.A_BOLD if attr == (colorOutline | curses.A_BOLD) else 0))
                except curses.error:
                    pass
                textWidth = sum(cwidth(c) for c in text)
                if refTarget is not None:
                    regions.append((x, x + textWidth, refTarget))
                x += textWidth
            if regions:
                self.clickMapReadRefs[y] = regions
            if line.clickable:
                self.clickMapRead[y] = line.section

    def drawSearchInput(self, h, w):
        self._title(" 搜尋經文", w)
        try:
            self.stdscr.addstr(2, 0, "關鍵字：" + self.searchInputText)
        except self.curses.error:
            pass

    def drawSearchResults(self, h, w):
        curses = self.curses
        self._title(f" 搜尋「{self.searchQuery}」共 {len(self.searchResults)} 筆", w)
        visible = h - 2
        if self.searchIdx < self.searchScroll:
            self.searchScroll = self.searchIdx
        if self.searchIdx >= self.searchScroll + visible:
            self.searchScroll = self.searchIdx - visible + 1
        self.clickMap = {}
        for rowI, r in enumerate(self.searchResults[self.searchScroll:self.searchScroll + visible]):
            y = rowI + 1
            label = f"{r['acr']} {r['chapter']}:{r['section']}  {r['content']}"
            attr = curses.A_REVERSE if self.searchScroll + rowI == self.searchIdx else 0
            try:
                self.stdscr.addstr(y, 0, fitWidth(label, w - 1), attr)
            except curses.error:
                pass
            self.clickMap[y] = ("search_result", self.searchScroll + rowI)

    def _openStrongConn(self):
        if self.strongConn is None and self.strongBiblePath:
            self.strongConn = _openSqliteSoft(self.strongBiblePath)
        return self.strongConn

    def _openDictConn(self):
        if self.dictConn is None and self.dictPath:
            self.dictConn = _openSqliteSoft(self.dictPath)
        return self.dictConn

    def _strongDefinitionLines(self, code):
        if code in self.strongDefCache:
            return self.strongDefCache[code]
        if code in ("G0", "H0"):
            lines = [f"[{code} 為佔位符，無對應字典資料]"]
            self.strongDefCache[code] = lines
            return lines
        dconn = self._openDictConn()
        if dconn is None:
            lines = ["尚未偵測到 Strong 字典（.dct.mybible），無法查字義。"]
            self.strongDefCache[code] = lines
            return lines
        row = StrongDictSource(dconn).lookup(code)
        if not row:
            lines = [f"查無 Strong 編號: {code}"]
        else:
            header = f"── Strong {row['word']} ──"
            body = renderDictHtml(row["data"], color=False)
            lines = [header] + body.split("\n")
        self.strongDefCache[code] = lines
        return lines

    def _buildStrongReadLines(self, w):
        world = self.strongWorld
        bookIndex = world.selectedBookIndex
        chapter = world.selectedChapter
        conn = self._openStrongConn()
        self._strongWordCodes = {}
        world.verseRow = {}
        lines = []
        if conn is None:
            lines.append(SegLine([("找不到 Strong 原文聖經模組", 0, None)]))
            return lines

        rows = CuvSource(conn).chapterRows(bookIndex, chapter)
        if not rows:
            lines.append(SegLine([("查無此章節", 0, None)]))
            return lines

        for r in rows:
            verse = r["Verse"]
            segments = splitStrongVerse(r["Scripture"])
            prefix = f"{verse:>3}  "
            chars = [(c, None) for c in prefix]
            wordIdx = 0
            for text, codes in segments:
                if codes:
                    wordIdx += 1
                    key = (bookIndex, chapter, verse, wordIdx)
                    self._strongWordCodes[key] = codes
                    chars.extend((c, key) for c in text)
                else:
                    chars.extend((c, None) for c in text)

            wrapped = wrapMarked(chars, w - 1)
            world.verseRow[verse] = len(lines)
            for wl in wrapped:
                segs = []
                curKey = "__NONE__"
                buf = ""
                for c, key in wl:
                    if key != curKey:
                        if buf:
                            attr = 0
                            if curKey != "__NONE__" and curKey is not None:
                                attr = colorSection if curKey in world.expanded else colorFootnote
                            segs.append((buf, attr, None if curKey == "__NONE__" else curKey))
                        buf = c
                        curKey = key
                    else:
                        buf += c
                if buf:
                    attr = 0
                    if curKey != "__NONE__" and curKey is not None:
                        attr = colorSection if curKey in world.expanded else colorFootnote
                    segs.append((buf, attr, None if curKey == "__NONE__" else curKey))
                lines.append(SegLine(segs, verse=verse))

            for wi in range(1, wordIdx + 1):
                key = (bookIndex, chapter, verse, wi)
                if key not in world.expanded:
                    continue
                for code in self._strongWordCodes.get(key, []):
                    for defLine in self._strongDefinitionLines(code):
                        for wl2 in plainWrap("      " + defLine, w - 1):
                            text = "".join(c for c, _ in wl2)
                            lines.append(SegLine([(text, colorSecondary, None)]))

            lines.append(SegLine([("", 0, None)]))
        return lines

    def drawStrongRead(self, h, w):
        curses = self.curses
        world = self.strongWorld
        name = zhBookNames[world.selectedBookIndex - 1]
        self._title(f" {name} 第{world.selectedChapter}章（原文 Strong）", w)

        cacheKey = (
            world.selectedBookIndex,
            world.selectedChapter,
            frozenset(world.expanded),
        )
        if cacheKey != world.cacheKey or w != world.cacheW:
            world.readLines = self._buildStrongReadLines(w)
            world.cacheKey = cacheKey
            world.cacheW = w

        visible = h - 2
        maxScroll = max(0, len(world.readLines) - visible)
        world.readScroll = max(0, min(world.readScroll, maxScroll))

        self.clickMapStrongWords = {}
        for rowI, line in enumerate(
            world.readLines[world.readScroll:world.readScroll + visible]
        ):
            y = rowI + 1
            x = 0
            regions = []
            for text, attr, key in line.segments:
                color = curses.color_pair(attr & 0xF) if attr else 0
                try:
                    self.stdscr.addstr(y, x, text, color)
                except curses.error:
                    pass
                textWidth = sum(cwidth(c) for c in text)
                if key is not None:
                    regions.append((x, x + textWidth, key))
                x += textWidth
            if regions:
                self.clickMapStrongWords[y] = regions

    def _buildHelpLines(self):
        lines = []
        lines.append("↑↓／j k／PageUp／PageDown／Space 捲動本頁，按 b/B/Esc 或其他鍵關閉")
        lines.append("")
        lines.append("一般模式：")
        lines.append("  ↑↓ 或 j k 移動／捲動，Enter 或滑鼠左鍵點擊 選取")
        lines.append("  PageUp/PageDown 或 Space  整頁上下捲動（類似 w3m）")
        lines.append("  讀經畫面 ←→ 切換上下章；e 英文對照；c 恢復本／和合本；n 大綱")
        lines.append("  讀經畫面點擊經文或 Enter 對準該節  展開／收合該節註解")
        lines.append("  y   複製目前經節　　/   搜尋全經文")
        lines.append("  b 或 B   返回上一頁（含畫面／模式切換的完整紀錄）")
        lines.append("  q   離開程式（詢問 y/n）　　Q   直接離開程式")
        lines.append("  :   進入指令模式（類似 vim），可輸入以下指令")
        if self.hasStrongBible:
            lines.append("  s   快速切換到原文 Strong 畫面")
        if self.hasDb:
            lines.append("  r   快速切回恢復本畫面")
        if self.storageEnabled:
            lines.append("  o 或 O   開啟設定（同 :option）")
        lines.append("")
        lines.append("指令模式：")
        lines.append("  :q                    結束程式 (Y/n)")
        lines.append("  :Q                    直接結束程式")
        lines.append("  :strong 或 :S         切換為 Strong 模式並跳至本章節")
        lines.append("                        （不在章節內時跳至目錄）")
        lines.append("  :recovery 或 :R       切換為恢復本，規則同上")
        lines.append("  :strong genesis 1 1   切換至 Strong 模式並跳至指定書卷章節")
        lines.append("                        （參數可只給部分：:strong 1／:strong 1 1）")
        lines.append("  :recovery genesis 1 1 同上，切換至恢復本")
        lines.append("  :1                    跳至本章指定節")
        lines.append("  :1 1                  跳至本卷指定章節")
        lines.append("  :genesis 1 1          跳至指定書卷章節")
        lines.append("  :footnote 或 :F       顯示本節註解（參數規則同 :strong）")
        lines.append("  :intro [書卷]         顯示書卷簡介（省略書卷則用目前書卷）")
        lines.append("  :copy 或 :C           複製目前經文")
        lines.append("  :copy 1 3-5 7         複製本章指定經節（x-y 連續／空白分隔不連續）")
        lines.append("  :copy #1              複製本章指定節的註解")
        lines.append("  :english on/off 或 :E 開關英文對照（不帶參數則切換）")
        lines.append("  :outline on/off 或 :O 開關綱目及註解顯示（不帶參數則切換）")
        lines.append("  :search 或 :find      在目前經文版本搜尋（可多字串，交集查詢）")
        lines.append("  :search -e Christ     在英文經文搜尋")
        lines.append("  :search a b --exclude c   同時含 a、b 後再扣除含 c 的結果")
        lines.append("  按 / 搜尋             與 :search 同一套查詢邏輯（交集／-e／--exclude）")
        lines.append("  Strong 畫面的搜尋     搜尋和合本（忽略標記與全形空格），不支援 -e")
        lines.append("  :help                 顯示本說明")
        lines.append("")
        lines.append("　（註：:S 已配給 :strong、:R 已配給 :recovery，")
        lines.append("　  :search／:reference 則另有 :find／:ref 簡寫）")
        lines.append("")
        if self.storageEnabled:
            lines.append(f"儲存功能（已啟用，資料存於 {self.noteDbPath}）：")
            lines.append("  :setup-storage        （已啟用，無需再次執行）")
            lines.append("  :option               進入設定模式；一般模式 o/O 同此")
            lines.append("  :option reset         重設所有設定 (Y/n)")
            lines.append("  :note 或 :N           對目前經節做筆記（開啟外部編輯器）")
            lines.append("  :note show            顯示目前經節的筆記（參數規則同 :strong）")
            lines.append("  :bookmark／:M／:mark  將目前經節加入書籤")
            lines.append("  :bookmark show        顯示所有書籤")
            lines.append("  :reference 或 :ref    為目前經節加上指向本章指定節的串珠")
            lines.append("  :reference 1          （同上，指向本章指定節）")
            lines.append("  :reference genesis 1 1 genesis 2 2")
            lines.append("                        在兩個完整經節之間建立串珠")
            lines.append("                        （串珠顯示於經節後方 a,b,...，可點按跳轉）")
        else:
            lines.append("儲存功能尚未啟用：執行 :setup-storage 以啟用")
            lines.append("設定／筆記／書籤／串珠功能（會在使用者資料目錄建立 bible-note.db，路徑可用 bible.py data 查看）")
        lines.append("")
        lines.append("新舊約書卷中英對照：")
        for i, (zh, en) in enumerate(zip(zhBookNames, enBookNames), start=1):
            lines.append(f"  {i:>2}  {zh:<6}{en}")
        return lines

    def drawHelp(self, h, w):
        self._title(" 說明", w)
        visible = h - 2
        lines = self._helpTextLines
        maxScroll = max(0, len(lines) - visible)
        self.helpScroll = max(0, min(self.helpScroll, maxScroll))
        for i, l in enumerate(lines[self.helpScroll:self.helpScroll + visible]):
            try:
                self.stdscr.addstr(i + 1, 1, l[: max(0, w - 2)])
            except self.curses.error:
                pass

    def drawOption(self, h, w):
        curses = self.curses
        self._title(" 設定 (Enter 編輯／儲存，Esc 取消編輯，b 返回)", w)
        for i, (key, label) in enumerate(optionFields):
            y = i + 1
            if y > h - 2:
                break
            if self._optionEditing and i == self._optionFieldIdx:
                line = f"{label}: {self._optionEditBuffer}"
            else:
                curVal = self.settings.get(key, "") or ""
                line = f"{label}: {curVal}"
            attr = curses.A_REVERSE if i == self._optionFieldIdx else 0
            try:
                self.stdscr.addstr(y, 0, line[: w - 1].ljust(w - 1), attr)
            except curses.error:
                pass

    def drawTextView(self, h, w):
        self._title(f" {self._textViewTitle}", w)
        if w != self._textViewCacheW:
            wrapped = []
            for raw in self._textViewRaw.split("\n"):
                if raw == "":
                    wrapped.append("")
                    continue
                for wl in plainWrap(raw, max(1, w - 1)):
                    wrapped.append("".join(c for c, _ in wl))
            self._textViewLines = wrapped
            self._textViewCacheW = w
        lines = self._textViewLines
        visible = h - 2
        maxScroll = max(0, len(lines) - visible)
        self._textViewScroll = max(0, min(self._textViewScroll, maxScroll))
        for i, l in enumerate(lines[self._textViewScroll:self._textViewScroll + visible]):
            try:
                self.stdscr.addstr(i + 1, 0, l[: max(0, w - 1)])
            except self.curses.error:
                pass
