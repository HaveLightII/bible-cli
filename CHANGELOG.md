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

### 計畫中

- 重整為可用 pipx / uv 安裝的套件，提供 `bible` 指令
- 資料檔案的取得方式（首次下載）
- 加入測試與跨平台 CI

## [0.0.1] - 基準版本

- 單檔 `bible.py`，提供恢復本 CLI / TUI 與原文 Strong 對照
- 新增 `--version` 參數
- 發行內容不再附帶任何資料庫檔案，改以連結提供（見 README「資料檔案」）
