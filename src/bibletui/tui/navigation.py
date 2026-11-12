"""導覽狀態、歷史與跳轉。"""

from ..books import resolveAnyBookName
from ..sources.cuv import (
    CuvSource,
    strongTagPattern,
)


class NavigationMixin:
    def _loadBooks(self):
        return self.source.listBooks()

    def _maxChapterFor(self, world, bookIndex):
        if world.kind == "strong":
            conn = self._openStrongConn()
            if conn is None:
                return 1
            return CuvSource(conn).maxChapter(bookIndex)
        return self.source.maxChapter(bookIndex)

    def _pageStep(self):
        h, _w = self.stdscr.getmaxyx()
        return max(1, (h - 2) - 1)

    def _snapshotWorld(self, world):
        snap = {}
        for key in self._WORLD_NAV_KEYS:
            val = getattr(world, key)
            if isinstance(val, set):
                val = set(val)
            elif isinstance(val, list):
                val = list(val)
            snap[key] = val
        return snap

    def _snapshot(self):
        snap = {}
        for key in self._NAV_KEYS:
            val = getattr(self, key)
            if isinstance(val, set):
                val = set(val)
            elif isinstance(val, list):
                val = list(val)
            snap[key] = val
        snap["recoveryWorld"] = self._snapshotWorld(self.recoveryWorld)
        snap["strongWorld"] = self._snapshotWorld(self.strongWorld)
        return snap

    def _pushHistory(self):
        self.history.append(self._snapshot())

    def _goBack(self):
        if not self.history:
            return False
        snap = self.history.pop()
        for key, val in snap.items():
            if key == "recoveryWorld":
                for k2, v2 in val.items():
                    setattr(self.recoveryWorld, k2, v2)
            elif key == "strongWorld":
                for k2, v2 in val.items():
                    setattr(self.strongWorld, k2, v2)
            else:
                setattr(self, key, val)
        self.recoveryWorld.cacheKey = None
        self.strongWorld.cacheKey = None
        return True

    def _currentReadSection(self):
        world = self.recoveryWorld
        for line in world.readLines[world.readScroll:]:
            if line.section is not None:
                return line.section
        for line in world.readLines[:world.readScroll]:
            if line.section is not None:
                return line.section
        return None

    def _currentStrongReadVerse(self):
        world = self.strongWorld
        for line in world.readLines[world.readScroll:]:
            if line.verse is not None:
                return line.verse
        for line in world.readLines[:world.readScroll]:
            if line.verse is not None:
                return line.verse
        return None

    def _currentContextRef(self):
        r, s = self.recoveryWorld, self.strongWorld
        if self.mode == "read" and r.selectedBookIndex and r.selectedChapter:
            return r.selectedBookIndex, r.selectedChapter, self._currentReadSection()
        if self.mode == "strong_read" and s.selectedBookIndex and s.selectedChapter:
            return s.selectedBookIndex, s.selectedChapter, self._currentStrongReadVerse()
        return None, None, None

    def _currentAnyBook(self):
        r, s = self.recoveryWorld, self.strongWorld
        if self.mode in ("read", "chapters") and r.selectedBookIndex:
            return r.selectedBookIndex
        if self.mode == "books" and r.books:
            return r.books[r.bookIdx][0]
        if self.mode in ("strong_read", "strong_chapters") and s.selectedBookIndex:
            return s.selectedBookIndex
        if self.mode == "strong_books" and s.books:
            return s.books[s.bookIdx][0]
        return None

    def _parseRefArgs(self, tokens, ctxBook, ctxChapter):
        if len(tokens) == 0:
            if ctxBook is None or ctxChapter is None:
                raise ValueError("目前不在章節內，請提供完整卷章節")
            return ctxBook, ctxChapter, None
        if len(tokens) == 1:
            if ctxBook is None or ctxChapter is None:
                raise ValueError("目前不在章節內，請提供完整卷章節")
            if not tokens[0].isdigit():
                raise ValueError("節數需為數字")
            return ctxBook, ctxChapter, int(tokens[0])
        if len(tokens) == 2:
            if ctxBook is None:
                raise ValueError("目前未選擇書卷")
            if not (tokens[0].isdigit() and tokens[1].isdigit()):
                raise ValueError("章節需為數字")
            return ctxBook, int(tokens[0]), int(tokens[1])
        if len(tokens) == 3:
            bIdx = resolveAnyBookName(tokens[0], self.conn if self.hasDb else None)
            if bIdx is None:
                raise ValueError(f"找不到書卷: {tokens[0]}")
            if not (tokens[1].isdigit() and tokens[2].isdigit()):
                raise ValueError("章節需為數字")
            return bIdx, int(tokens[1]), int(tokens[2])
        raise ValueError("參數過多")

    def _toggleExpandSection(self, section):
        expanded = self.recoveryWorld.expanded
        if section in expanded:
            expanded.discard(section)
        else:
            expanded.add(section)

    def _forceExpandSection(self, section):
        self.recoveryWorld.expanded.add(section)
        self.recoveryWorld.cacheKey = None

    def _versePreview(self, bookIndex, chapter, section):
        if self.hasDb:
            langPrimary = "cuv_big5" if self.showCuv else "big5"
            row = self.source.verseText(bookIndex, chapter, section, langPrimary)
            if row:
                return row["content"]
        conn = self._openStrongConn()
        if conn is not None:
            row = CuvSource(conn).verseRaw(bookIndex, chapter, section)
            if row:
                return strongTagPattern.sub("", row["Scripture"])
        return ""

    @staticmethod
    def _scrollTargetRow(verseRow, section):
        if not section or not verseRow:
            return 0
        if section in verseRow:
            return verseRow[section]
        nearest = min(verseRow, key=lambda s: (abs(s - section), s))
        return verseRow[nearest]

    def _jumpRecovery(self, bookIndex, chapter, section):
        world = self.recoveryWorld
        self._pushHistory()
        world.selectedBookIndex = bookIndex
        world.chapterCount = self._maxChapterFor(world, bookIndex)
        chapter = max(1, min(chapter, world.chapterCount))
        world.selectedChapter = chapter
        world.expanded = set()
        self.mode = world.readMode
        h, w = self.stdscr.getmaxyx()
        w = max(1, w)
        world.readLines, world.verseRow = self._buildReadLines(w)
        world.cacheKey = (
            bookIndex, chapter, self.showEn, self.showCuv, self.showOutline, frozenset(world.expanded),
        )
        world.cacheW = w
        world.readScroll = self._scrollTargetRow(world.verseRow, section)

    def _jumpStrong(self, bookIndex, chapter, section):
        world = self.strongWorld
        self._pushHistory()
        world.selectedBookIndex = bookIndex
        world.chapterCount = self._maxChapterFor(world, bookIndex)
        chapter = max(1, min(chapter, world.chapterCount))
        world.selectedChapter = chapter
        world.expanded = set()
        self.mode = world.readMode
        h, w = self.stdscr.getmaxyx()
        w = max(1, w)
        world.readLines = self._buildStrongReadLines(w)
        world.cacheKey = (bookIndex, chapter, frozenset(world.expanded))
        world.cacheW = w
        world.readScroll = self._scrollTargetRow(world.verseRow, section)
