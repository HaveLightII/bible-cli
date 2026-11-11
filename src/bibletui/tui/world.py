"""恢復本與原文 Strong 兩套畫面共用的導覽狀態。"""


class World:
    """恢復本／原文 Strong 兩套平行畫面共用的導覽狀態容器。

    recovery 與 strong 兩個模式在書卷清單／章節清單／讀經畫面上的捲動位置、
    目前選取的書卷章節、展開狀態、讀經內容快取等，結構完全相同，僅差在
    存取的資料來源與畫面文字／代號。這裡把該結構抽成一份，App 各持有一個
    self.recoveryWorld 與 self.strongWorld 實例，避免同一組欄位在 __init__
    寫兩次、且日後修改時忘了同步另一份。
    """

    __slots__ = (
        "kind", "books",
        "bookIdx", "bookScroll",
        "selectedBookIndex", "chapterCount", "chapterIdx", "chapterScroll",
        "selectedChapter", "expanded",
        "readLines", "readScroll", "verseRow", "cacheKey", "cacheW",
        "booksTitle", "chaptersTitleSuffix",
        "bookClickTag", "chapterClickTag",
        "booksMode", "chaptersMode", "readMode",
        "backKeys", "supportsSearch",
    )

    def __init__(self, kind, books, booksTitle, chaptersTitleSuffix,
                 bookClickTag, chapterClickTag,
                 booksMode, chaptersMode, readMode,
                 backKeys, supportsSearch=False):
        self.kind = kind
        self.books = books

        self.bookIdx = 0
        self.bookScroll = 0

        self.selectedBookIndex = None
        self.chapterCount = 0
        self.chapterIdx = 0
        self.chapterScroll = 0

        self.selectedChapter = None
        self.expanded = set()

        self.readLines = []
        self.readScroll = 0
        self.verseRow = {}
        self.cacheKey = None
        self.cacheW = None

        self.booksTitle = booksTitle
        self.chaptersTitleSuffix = chaptersTitleSuffix
        self.bookClickTag = bookClickTag
        self.chapterClickTag = chapterClickTag
        self.booksMode = booksMode
        self.chaptersMode = chaptersMode
        self.readMode = readMode
        self.backKeys = backKeys
        self.supportsSearch = supportsSearch
