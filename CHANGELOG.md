# Changelog

版本號依 [Semantic Versioning](https://semver.org/lang/zh-TW/)。

## [Unreleased] - 目標 0.1.0

### 已完成（階段 1 至 4，已合併到 `main`）

- 建立資料來源抽象層（`RecoverySource`、`CuvSource`、`StrongDictSource`），TUI 與 CLI 不再直接存取 SQL
- 沒有恢復本時以公開的和合本為資料來源；偵測到恢復本 `bible.db` 時預設用恢復本，CLI 與 TUI 皆是
- 和合本來源支援讀經與搜尋（在去除 Strong 標記的純文字上搜尋，忽略全形空格）；缺少的功能（英文對照、綱目、註腳、簡介）顯示「此資料來源不含此內容」
- Strong 畫面可用 `/` 搜尋與 `y` 複製；章節選擇畫面可按 `/`；搜尋結果依顯示寬度截斷，不再折行
- CLI `list`、`read`、`search` 新增 `--source cuv|recovery` 與 `--strongbible`；沒有恢復本時內建書名別名表
- TUI `--mode` 改為 `auto|recovery|strong`（`restore` 仍接受為別名）
- 資料檔偵測順序：命令列、環境變數、已存設定、使用者資料目錄、程式所在目錄、目前目錄；新增 `bible.py data` 子指令顯示偵測結果
- 使用者資料（筆記、書籤、串珠、設定）改放各作業系統的使用者資料目錄，可用環境變數 `BIBLE_CLI_DATA_DIR` 覆寫；舊位置的 `.bible-note.db` 於互動啟動時詢問是否複製
- 修正：空的 Strong 標記、跨來源跳轉時節編號不存在的後備、舊版 ncurses 的滾輪向下

### 已完成（階段 5 至 7，已合併到 `main`）

- 重整為可安裝的 Python 套件 `bibletui`（`src/bibletui/`，`pyproject.toml`，Python 3.9 以上），提供 `bible` 指令，也可用 `python -m bibletui`；根目錄 `bible.py` 保留為啟動檔，`python3 bible.py` 照舊可用
- 程式拆成 `cli`、`paths`、`resources`、`books`、`storage`、`install`、`render`、`sources/`、`tui/` 等模組；依賴改寫在 `pyproject.toml`（Windows 自動安裝 `windows-curses`），移除 `requirement.txt`；`tools/` 改名 `bin/`
- 新增 `bible data install [--from-dir DIR] [--from-file FILE] [--force]`：不連網，驗證 SHA-256 後安裝資料檔案到使用者資料目錄；找不到資料庫時的提示改為指向此指令
- 安裝版不再搜尋程式所在目錄，只搜尋命令列、環境變數、已存設定、使用者資料目錄與目前目錄；舊筆記資料庫遷移只在從原始碼執行時進行
- `--version` 改印 `bible <版本>`（原為 `bible.py <版本>`）；錯誤提示與說明依啟動方式顯示 `bible`、`python3 bible.py` 或 `python3 -m bibletui`
- 取得資料檔案改為手動下載後本機安裝，不做自動連網下載；恢復本不提供下載，README 新增「取得恢復本資料庫」說明
- 授權：MIT
- 新增單元與煙霧測試（`tests/`，標準函式庫 `unittest`，使用虛構的合成資料）與 GitHub Actions 工作流程（Linux、macOS、Windows，Python 3.9 至 3.14）

### 計畫中

- 確認 CI 在各平台與 Python 版本全數通過，必要時調整支援範圍
- 發布 0.1.0（GitHub release，PyPI 視情況）
- 視需求：curses 不可用時的純文字後備、單檔執行檔

## [0.0.1] - 基準版本

- 單檔 `bible.py`，提供恢復本 CLI / TUI 與原文 Strong 對照
- 新增 `--version` 參數
- 發行內容不再附帶任何資料庫檔案，改以連結提供（見 README「資料檔案」）
