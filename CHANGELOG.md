# Changelog

版本號依 [Semantic Versioning](https://semver.org/lang/zh-TW/)。

## [Unreleased]

### 新增

- 多聖經模組：新增 `bible data list`（列出已安裝資料庫與使用中的項目）、`bible data use <代號>`（設定預設聖經模組或字典，寫入 `config.json`）、`bible data uninstall <代號>`（只移除使用者資料目錄內的檔案）；`list`、`read`、`search`、`orig` 新增 `--module`，`bible --module` 可指定 TUI 的聖經模組。
- TUI 新增 `:module`（別名 `:mod`）：列出模組、切換模組並記為預設；Strong 畫面標題顯示目前模組。
- `bible data install` 可直接安裝 `.zip`（內含多個 `.mybible` 時各自安裝），`--from-dir` 改為收錄資料夾內所有 `bible.db`、`*.bbl.mybible`、`*.dct.mybible`；`.bbl.mybible` 內容不是聖經模組、`.dct.mybible` 不是字典時拒絕。
- 其他 MySword 模組的顯示：去除 GBF 格式標記（標題、譯註、斜體、串珠、形態標記、HTML 標籤與實體），搜尋改為不分大小寫並合併空白；`orig` 對不含 Strong 的模組印出說明並以離開碼 1 結束。
- 沒有設定預設時，有 `cuvt.bbl.mybible` 就用它，不再因為安裝其他模組而改變預設（`cuvt.bbl.mybible` 與其他模組位於不同搜尋目錄時亦同）。
- `bible data install`：檔名為 `.gz` 但內容其實是未壓縮的 SQLite 時（例如瀏覽器下載時已自動解壓縮），直接當成 `.mybible` 安裝。

### 變更

- 優先序新增 `config.json` 的預設模組：位於環境變數之後、TUI 設定畫面的路徑之前。

### 修正

- Windows：驗證資料檔失敗時 SQLite 連線未關閉，導致 `bible data install` 解壓縮後的 `.part` 暫存檔無法刪除；改以 `contextlib.closing` 確保連線關閉（`resources.py`、`install.py`、`cli.py`）。
- `userDataDir` 依 `platform` 參數選用 `ntpath` 或 `posixpath`，不再受主機的 `os.path` 影響；Python 3.13 起 Windows 的 `os.path.isabs("/data")` 為 `False`，使測試在 Windows 主機上模擬 Linux 時失敗。真實主機的行為不變。

## [0.1.0] - 2026-11-12

首次公開發布。以下為自 0.0.1 以來的變更。

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

- 重整為可安裝的 Python 套件 `bibletui`（`src/bibletui/`，`pyproject.toml`，Python 3.10 以上），提供 `bible` 指令，也可用 `python -m bibletui`；根目錄 `bible.py` 保留為啟動檔，`python3 bible.py` 照舊可用
- 程式拆成 `cli`、`paths`、`resources`、`books`、`storage`、`install`、`render`、`sources/`、`tui/` 等模組；依賴改寫在 `pyproject.toml`（Windows 自動安裝 `windows-curses`），移除 `requirement.txt`；`tools/` 改名 `bin/`
- 新增 `bible data install [--from-dir DIR] [--from-file FILE] [--force]`：不連網，驗證 SHA-256 後安裝資料檔案到使用者資料目錄；找不到資料庫時的提示改為指向此指令
- 安裝版不再搜尋程式所在目錄，只搜尋命令列、環境變數、已存設定、使用者資料目錄與目前目錄；舊筆記資料庫遷移只在從原始碼執行時進行
- `--version` 改印 `bible <版本>`（原為 `bible.py <版本>`）；錯誤提示與說明依啟動方式顯示 `bible`、`python3 bible.py` 或 `python3 -m bibletui`
- 取得資料檔案改為手動下載後本機安裝，不做自動連網下載；恢復本不提供下載，README 新增「取得恢復本資料庫」說明
- 授權：MIT
- 新增單元與煙霧測試（`tests/`，標準函式庫 `unittest`，使用虛構的合成資料）與 GitHub Actions 工作流程（Linux、macOS、Windows，Python 3.10 至 3.14）
- 最低支援的 Python 版本由 3.9 改為 3.10：CI 首次執行時，`ubuntu-latest`（Ubuntu 26.04）上找不到 Python 3.9，且 CPython 3.9 已於 2025 年 10 月結束支援

### 已完成（資料散布調整）

- 和合本 `cuvt.bbl.mybible` 不再由 README 提供下載連結，改指引自行從 MySword 官方網站或應用程式取得（README 新增「取得和合本」）；Strong 字典的連結不變
- `bible data install`：`.mybible` 改為檢查資料表結構，SHA-256 與作者版本不同時只警告、不再拒絕（`--force` 只用於目標已存在且內容不同時覆蓋）；可直接安裝 MySword 網站的 `.gz` 壓縮檔

### 發布準備（階段 9b）

- 新增 `THIRD_PARTY_NOTICES.md`，載明 Strong 字典的版權聲明與散布條件，以及和合本、恢復本的資料來源說明
- 新增 `.github/workflows/release.yml`：推送 `v*` 標籤時建置並以 PyPI Trusted Publishing 發布，建置時檢查標籤與套件版本一致
- 發行套件名定為 `bible-strong-tui`（PyPI 以 `bibletui` 與既有的 `bible-tui` 過於相似而拒絕登記）；匯入套件 `bibletui` 與指令 `bible` 不變
- README 內指向 CHANGELOG、LICENSE、THIRD_PARTY_NOTICES 的相對連結改為絕對網址，避免在 PyPI 頁面失效
- 版本改為 0.1.0，補上 `pyproject.toml` 的關鍵字、分類與專案連結

### 計畫中

- 確認 CI 在各平台與 Python 版本全數通過，必要時調整支援範圍
- 視需求：curses 不可用時的純文字後備、單檔執行檔

## [0.0.1] - 基準版本

- 單檔 `bible.py`，提供恢復本 CLI / TUI 與原文 Strong 對照
- 新增 `--version` 參數
- 發行內容不再附帶任何資料庫檔案，改以連結提供（見 README「資料檔案」）
