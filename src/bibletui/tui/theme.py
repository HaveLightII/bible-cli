"""TUI 的色彩配對編號與設定欄位。"""


colorOutline = 1


colorFootnote = 2


colorSection = 3


colorSecondary = 4


colorHeader = 5


colorHelp = 6


colorCmdLine = 7


optionFields = [
    ("recovery_db_path", "恢復本資料庫路徑 (bible.db)"),
    ("strong_db_path", "Strong 原文聖經模組路徑 (.bbl.mybible)"),
    ("dict_db_path", "Strong 原文字典路徑 (.dct.mybible)"),
    ("default_mode", "預設啟動模式 (recovery 或 strong)"),
    ("default_english", "預設顯示英文對照 (1 或 0)"),
    ("default_outline", "預設顯示綱目及註解 (1 或 0)"),
    ("note_db_path", "筆記資料庫路徑 (bible-note.db)"),
]
