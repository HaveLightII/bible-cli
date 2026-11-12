"""複製經文與註解到剪貼簿。"""

import os

from ..books import zhBookNames
from ..console import copyToClipboardText
from ..constants import needRecoveryMsg
from ..sources.cuv import (
    CuvSource,
    strongTagPattern,
)
from ..sources.recovery import (
    bookDisplayName,
    getFootnotes,
)


class ClipboardMixin:
    def _copyToClipboard(self, text):
        return copyToClipboardText(text)

    def _copyTextSmart(self, text, label="經文"):
        if not text:
            return "沒有內容可複製"
        if self._copyToClipboard(text):
            return f"已複製{label}到剪貼簿"
        home = os.path.expanduser("~")
        path = os.path.join(home, ".bible-clipboard.txt")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            return f"找不到剪貼簿工具，已改將{label}存到 {path}"
        except OSError:
            return "找不到可用的剪貼簿工具，且無法寫入家目錄，複製失敗"

    def _copyCurrentVerse(self):
        world = self.recoveryWorld
        section = self._currentReadSection()
        if section is None:
            self.statusMessage = "目前沒有可複製的經節"
            return
        langPrimary = "cuv_big5" if self.showCuv else "big5"
        row = self.source.verseText(
            world.selectedBookIndex, world.selectedChapter, section, langPrimary
        )
        if not row:
            self.statusMessage = "查無經文內容"
            return
        bookName = bookDisplayName(self.conn, world.selectedBookIndex, "big5")
        text = f"{bookName} {world.selectedChapter}:{section}　{row['content']}"
        self.statusMessage = self._copyTextSmart(text, label=f"{bookName} {world.selectedChapter}:{section}")

    def _copyCurrentStrongVerse(self):
        world = self.strongWorld
        verse = self._currentStrongReadVerse()
        if verse is None:
            self.statusMessage = "目前沒有可複製的經節"
            return
        conn = self._openStrongConn()
        if conn is None:
            self.statusMessage = "找不到原文 Strong 聖經模組"
            return
        row = CuvSource(conn).verseRaw(world.selectedBookIndex, world.selectedChapter, verse)
        if not row:
            self.statusMessage = "查無經文內容"
            return
        text = strongTagPattern.sub("", row["Scripture"])
        bookName = zhBookNames[world.selectedBookIndex - 1]
        full = f"{bookName} {world.selectedChapter}:{verse}　{text}"
        self.statusMessage = self._copyTextSmart(full, label=f"{bookName} {world.selectedChapter}:{verse}")

    def _copyVersesForSections(self, bookIndex, chapter, sections, fromStrong):
        parts = []
        if fromStrong:
            conn = self._openStrongConn()
            if conn is None:
                self.statusMessage = "找不到原文 Strong 聖經模組"
                return
            bookName = zhBookNames[bookIndex - 1]
            for s in sections:
                row = CuvSource(conn).verseRaw(bookIndex, chapter, s)
                if row:
                    text = strongTagPattern.sub("", row["Scripture"])
                    parts.append(f"{bookName} {chapter}:{s}　{text}")
        else:
            langPrimary = "cuv_big5" if self.showCuv else "big5"
            bookName = bookDisplayName(self.conn, bookIndex, "big5")
            for s in sections:
                row = self.source.verseText(bookIndex, chapter, s, langPrimary)
                if row:
                    parts.append(f"{bookName} {chapter}:{s}　{row['content']}")
        if not parts:
            self.statusMessage = "查無指定經節"
            return
        self.statusMessage = self._copyTextSmart("\n".join(parts), label=f"{len(parts)} 節經文")

    def _copyFootnotesForSections(self, bookIndex, chapter, sections):
        if not self.hasDb:
            self.statusMessage = needRecoveryMsg
            return
        langPrimary = "cuv_big5" if self.showCuv else "big5"
        parts = []
        for s in sections:
            for f in getFootnotes(self.conn, langPrimary, bookIndex, chapter, s):
                if f["note"]:
                    parts.append(f["note"])
        if not parts:
            self.statusMessage = "查無指定經節的註解"
            return
        self.statusMessage = self._copyTextSmart("\n".join(parts), label="註解")
