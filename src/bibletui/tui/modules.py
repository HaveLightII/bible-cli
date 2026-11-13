"""TUI 的聖經模組切換（:module）。"""

import os

from ..config import setDefaultId
from ..modules import describe, effectiveDefault, findModule, ModuleLookupError, scanModules
from ..sources.cuv import CuvSource


class ModuleMixin:
    def _currentModuleId(self):
        if not self.strongBiblePath:
            return None
        return os.path.realpath(self.strongBiblePath)

    def _cmdModule(self, tokens):
        infos = [m for m in scanModules() if m.kind == "bible"]
        if not infos:
            self._setCmdError("找不到任何聖經模組（見 bible data install）")
            return
        if not tokens:
            current = self._currentModuleId()
            lines = ["用法：:module <代號> 切換聖經模組（同時記為預設）", ""]
            for m in infos:
                mark = "*" if os.path.realpath(m.path) == current else " "
                abbr = f"［{m.abbr}］" if m.abbr else ""
                lines.append(f"{mark} {m.id} {abbr}{m.description}")
                lines.append(f"    {describe(m)}")
            self._openTextView("聖經模組", "\n".join(lines))
            return
        try:
            info = findModule(" ".join(tokens), infos, kinds=("bible",))
        except ModuleLookupError as e:
            self._setCmdError(str(e))
            return
        self._switchStrongModule(info)

    def _switchStrongModule(self, info):
        if self.strongConn is not None:
            try:
                self.strongConn.close()
            except Exception:
                pass
        self.strongConn = None
        self.strongBiblePath = info.path
        self.hasStrongBible = True
        self.strongModuleLabel = info.abbr or info.id
        self._cuvSearchSource = None
        self._strongWordCodes = {}
        world = self.strongWorld
        world.cacheKey = None
        world.readLines = []
        world.expanded = set()
        world.booksTitle = f" 書卷清單（{self.strongModuleLabel}）"

        conn = self._openStrongConn()
        source = CuvSource(conn) if conn is not None else None
        if self.mode in ("strong_chapters", "strong_read") and source is not None:
            book = world.selectedBookIndex
            if book and self.mode == "strong_chapters":
                world.chapterCount = source.maxChapter(book)
                world.chapterIdx = min(world.chapterIdx, max(0, world.chapterCount - 1))
            elif book and world.selectedChapter:
                if not source.chapterRows(book, world.selectedChapter):
                    self.mode = "strong_books"
                    world.selectedBookIndex = None
                    world.selectedChapter = None
        if self.searchKind == "strong":
            self.searchQuery = ""
            self.searchInputText = ""
            self.searchResults = []
            self.searchScroll = 0
            self.searchIdx = 0
            if self.mode in ("search_input", "search_results"):
                self.mode = "strong_books"
        try:
            setDefaultId("bible", info.id)
            saved = "，已記為預設"
        except OSError:
            saved = "（無法寫入設定檔，僅本次有效）"
        self.statusMessage = f"已切換聖經模組：{self.strongModuleLabel}{saved}"
