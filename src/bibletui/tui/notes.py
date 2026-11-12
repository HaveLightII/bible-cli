"""本機儲存：設定、筆記、書籤與串珠。"""

import datetime
import os
import sqlite3
import subprocess
import tempfile

from ..books import (
    resolveAnyBookName,
    zhBookNames,
)
from ..console import isWindows
from ..storage import (
    noteDbDefaultPath,
    openNoteDb,
    resolveNoteDbPath,
    writeNoteDbPointer,
)


class NotesMixin:
    def _detectStorage(self):
        path = resolveNoteDbPath()
        if not path:
            return
        try:
            conn = openNoteDb(path)
        except sqlite3.Error:
            return
        self.noteConn = conn
        self.noteDbPath = path
        self.storageEnabled = True
        self._loadSettings()

    def _openNoteDb(self):
        if self.noteConn is None and self.noteDbPath:
            try:
                self.noteConn = openNoteDb(self.noteDbPath)
            except sqlite3.Error:
                self.noteConn = None
        return self.noteConn

    def _loadSettings(self):
        conn = self._openNoteDb()
        if conn is None:
            return
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
        self.settings = {r["key"]: r["value"] for r in rows}
        if self.settings.get("default_english") == "1":
            self.showEn = True
        elif self.settings.get("default_english") == "0":
            self.showEn = False
        if self.settings.get("default_outline") == "1":
            self.showOutline = True
        elif self.settings.get("default_outline") == "0":
            self.showOutline = False

    def _saveSetting(self, key, value):
        conn = self._openNoteDb()
        if conn is None:
            self.statusMessage = "無法開啟設定資料庫"
            return
        conn.execute(
            "INSERT INTO settings(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        conn.commit()
        self.settings[key] = value

    def _resetSettings(self):
        conn = self._openNoteDb()
        if conn is not None:
            conn.execute("DELETE FROM settings")
            conn.commit()
        self.settings = {}
        self.statusMessage = "已重設所有設定"

    def _cmdSetupStorage(self):
        if self.storageEnabled:
            self.statusMessage = "儲存功能已啟用"
            return
        try:
            conn = openNoteDb(noteDbDefaultPath)
        except sqlite3.Error as e:
            self._setCmdError(f"無法建立儲存資料庫: {e}")
            return
        self.noteConn = conn
        self.noteDbPath = noteDbDefaultPath
        self.storageEnabled = True
        self.statusMessage = f"已啟用儲存功能（{noteDbDefaultPath}）"

    def _cmdOption(self, rest):
        if not self.storageEnabled:
            self._setCmdError("請先執行 :setup-storage 啟用儲存功能")
            return
        if rest and rest[0] == "reset":
            self._prevModeBeforeConfirm = self.mode
            self.mode = "confirm_option_reset"
            return
        self._pushHistory()
        self.mode = "option"
        self._optionFieldIdx = 0
        self._optionEditing = False

    def _applyOptionValue(self, key, value):
        if key == "note_db_path" and value and value != self.noteDbPath:
            try:
                newConn = openNoteDb(value)
            except sqlite3.Error as e:
                self.statusMessage = f"無法開啟資料庫: {e}"
                return
            if self.noteConn is not None:
                try:
                    self.noteConn.close()
                except sqlite3.Error:
                    pass
            self.noteConn = newConn
            self.noteDbPath = value
            writeNoteDbPointer(value)
        self._saveSetting(key, value)
        self.statusMessage = "已儲存設定"

    def _cmdNote(self, tokens):
        if not self.storageEnabled:
            self._setCmdError("請先執行 :setup-storage 啟用儲存功能")
            return
        show = False
        if tokens and tokens[0] == "show":
            show = True
            tokens = tokens[1:]
        ctxBook, ctxChapter, ctxSection = self._currentContextRef()
        try:
            bookIndex, chapter, section = self._parseRefArgs(tokens, ctxBook, ctxChapter)
        except ValueError as e:
            self._setCmdError(str(e))
            return
        if section is None:
            section = ctxSection
        if section is None:
            self._setCmdError("請指定節數")
            return
        if show:
            self._showNote(bookIndex, chapter, section)
        else:
            self._editNote(bookIndex, chapter, section)

    def _showNote(self, bookIndex, chapter, section):
        conn = self._openNoteDb()
        text = ""
        if conn is not None:
            row = conn.execute(
                "SELECT note FROM notes WHERE book=? AND chapter=? AND section=?",
                (bookIndex, chapter, section),
            ).fetchone()
            text = row["note"] if row else ""
        bookName = zhBookNames[bookIndex - 1] if 1 <= bookIndex <= 66 else str(bookIndex)
        self._openTextView(f"{bookName} {chapter}:{section} 筆記", text or "（尚無筆記）")

    def _editNote(self, bookIndex, chapter, section):
        conn = self._openNoteDb()
        if conn is None:
            self.statusMessage = "無法開啟筆記資料庫"
            return
        row = conn.execute(
            "SELECT note FROM notes WHERE book=? AND chapter=? AND section=?",
            (bookIndex, chapter, section),
        ).fetchone()
        existing = row["note"] if row else ""
        editor = os.environ.get("EDITOR") or ("notepad" if isWindows else "nano")
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False, encoding="utf-8"
            ) as tf:
                tf.write(existing)
                tmpPath = tf.name
        except OSError as e:
            self.statusMessage = f"無法建立暫存筆記檔: {e}"
            return
        curses = self.curses
        try:
            curses.def_prog_mode()
        except curses.error:
            pass
        curses.endwin()
        editorOk = True
        try:
            subprocess.run([editor, tmpPath])
        except (FileNotFoundError, OSError) as e:
            editorOk = False
            self.statusMessage = (
                f"無法開啟編輯器 {editor}: {e}　"
                f"（可設定環境變數 EDITOR 指定其他編輯器）"
            )
        finally:
            try:
                curses.reset_prog_mode()
            except curses.error:
                pass
            self.stdscr.refresh()
        if not editorOk:
            try:
                os.unlink(tmpPath)
            except OSError:
                pass
            return
        try:
            with open(tmpPath, "r", encoding="utf-8") as f:
                newText = f.read()
        except OSError:
            newText = existing
        finally:
            try:
                os.unlink(tmpPath)
            except OSError:
                pass
        newText = newText.rstrip("\n")
        if newText.strip():
            conn.execute(
                "INSERT INTO notes(book, chapter, section, note) VALUES(?, ?, ?, ?) "
                "ON CONFLICT(book, chapter, section) DO UPDATE SET note=excluded.note",
                (bookIndex, chapter, section, newText),
            )
        else:
            conn.execute(
                "DELETE FROM notes WHERE book=? AND chapter=? AND section=?",
                (bookIndex, chapter, section),
            )
        conn.commit()
        self.statusMessage = "已儲存筆記"

    def _cmdBookmark(self, tokens):
        if not self.storageEnabled:
            self._setCmdError("請先執行 :setup-storage 啟用儲存功能")
            return
        if tokens and tokens[0] == "show":
            self._showBookmarks()
            return
        ctxBook, ctxChapter, ctxSection = self._currentContextRef()
        if ctxBook is None or ctxChapter is None or ctxSection is None:
            self._setCmdError("目前沒有可加入書籤的經節")
            return
        conn = self._openNoteDb()
        if conn is None:
            self.statusMessage = "無法開啟書籤資料庫"
            return
        conn.execute(
            "INSERT INTO bookmarks(book, chapter, section, added_at) VALUES(?, ?, ?, ?) "
            "ON CONFLICT(book, chapter, section) DO UPDATE SET added_at=excluded.added_at",
            (ctxBook, ctxChapter, ctxSection, datetime.datetime.now().isoformat(timespec="seconds")),
        )
        conn.commit()
        self.statusMessage = "已加入書籤"

    def _showBookmarks(self):
        conn = self._openNoteDb()
        lines = []
        if conn is not None:
            rows = conn.execute(
                "SELECT book, chapter, section, added_at FROM bookmarks ORDER BY book, chapter, section"
            ).fetchall()
            for r in rows:
                bookName = zhBookNames[r["book"] - 1] if 1 <= r["book"] <= 66 else str(r["book"])
                preview = self._versePreview(r["book"], r["chapter"], r["section"])
                lines.append(f"{bookName} {r['chapter']}:{r['section']}　{preview}")
        text = "\n".join(lines) if lines else "（尚無書籤）"
        self._openTextView("書籤", text)

    def _cmdReference(self, tokens):
        if not self.storageEnabled:
            self._setCmdError("請先執行 :setup-storage 啟用儲存功能")
            return
        if len(tokens) == 6:
            try:
                srcBook = resolveAnyBookName(tokens[0], self.conn if self.hasDb else None)
                if srcBook is None:
                    raise ValueError(f"找不到書卷: {tokens[0]}")
                if not (tokens[1].isdigit() and tokens[2].isdigit()):
                    raise ValueError("章節需為數字")
                srcChapter, srcSection = int(tokens[1]), int(tokens[2])
                tgtBook = resolveAnyBookName(tokens[3], self.conn if self.hasDb else None)
                if tgtBook is None:
                    raise ValueError(f"找不到書卷: {tokens[3]}")
                if not (tokens[4].isdigit() and tokens[5].isdigit()):
                    raise ValueError("章節需為數字")
                tgtChapter, tgtSection = int(tokens[4]), int(tokens[5])
            except ValueError as e:
                self._setCmdError(str(e))
                return
        else:
            ctxBook, ctxChapter, ctxSection = self._currentContextRef()
            if ctxBook is None or ctxChapter is None or ctxSection is None:
                self._setCmdError("目前沒有可加上串珠的經節")
                return
            try:
                tgtBook, tgtChapter, tgtSection = self._parseRefArgs(tokens, ctxBook, ctxChapter)
            except ValueError as e:
                self._setCmdError(str(e))
                return
            if tgtSection is None:
                self._setCmdError("請指定目標節數")
                return
            srcBook, srcChapter, srcSection = ctxBook, ctxChapter, ctxSection
        conn = self._openNoteDb()
        if conn is None:
            self.statusMessage = "無法開啟串珠資料庫"
            return
        existing = conn.execute(
            "SELECT label FROM refs WHERE book=? AND chapter=? AND section=?",
            (srcBook, srcChapter, srcSection),
        ).fetchall()
        used = {r["label"] for r in existing}
        label = None
        for i in range(26):
            cand = chr(ord("a") + i)
            if cand not in used:
                label = cand
                break
        if label is None:
            self.statusMessage = "本節串珠已達上限"
            return
        conn.execute(
            "INSERT INTO refs(book, chapter, section, label, target_book, target_chapter, target_section) "
            "VALUES(?, ?, ?, ?, ?, ?, ?)",
            (srcBook, srcChapter, srcSection, label, tgtBook, tgtChapter, tgtSection),
        )
        conn.commit()
        if self.mode == "read" and srcBook == self.recoveryWorld.selectedBookIndex and srcChapter == self.recoveryWorld.selectedChapter:
            self.recoveryWorld.cacheKey = None
        self.statusMessage = f"已加上串珠 {label}"
