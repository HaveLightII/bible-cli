# 恢復本聖經 CLI / TUI

單一 Python 檔案（`bible.py`）提供的聖經查詢工具，同時支援命令列（CLI）批次查詢與互動式終端機（TUI）瀏覽，並可對照原文 Strong 編號查字義。不需要額外安裝資料庫伺服器，僅依賴 sqlite 檔案（`bible.db`、MySword 的 `.mybible` 模組）運作。

恢復本 `bible.db` 為選用：偵測到時預設使用恢復本；沒有時以和合本（`cuvt.bbl.mybible`）為預設，仍可閱讀、搜尋與查 Strong 字義，只是沒有大綱、註解、書卷簡介與英文對照。


## Features

- 恢復本經文瀏覽：書卷／章／節查詢，含大綱、註解、英文對照、和合本正文切換
- 和合本經文瀏覽與全文搜尋：不需要恢復本，CLI 以 `--source cuv|recovery` 選擇資料來源
- 原文 Strong 編號對照：逐字標色顯示 Strong 編號，可查希臘文／希伯來文字義
- 恢復本與原文 Strong 畫面可在 TUI 中以 `s` / `r` 即時切換，兩邊瀏覽狀態互不干擾
- 全文搜尋：支援多字串交集查詢、`--exclude` 差集查詢
- 類 vim 的 `:` 指令模式，可直接輸入 `:創世記 1 1` 之類的參照跳轉
- 滑鼠／觸控支援：點擊書卷、章節、經文展開註解、原文標色字查字義
- 選用的筆記／書籤／串珠功能（需執行 `:setup-storage` 啟用，才會在使用者資料目錄建立本機資料庫）
- 同時相容 Linux / macOS / Windows（Windows 需另外安裝 `windows-curses`）


## Tech Stack

**執行環境：** Python 3

**核心套件：** `sqlite3`、`curses`（Windows 為 `windows-curses`）、`argparse`

**資料來源：** `bible.db`（恢復本內容，選用）、MySword 格式的 `.dct.mybible`（Strong 字典）與 `.bbl.mybible`（含 Strong 編號的和合本）

**本倉庫不附帶任何資料庫檔案。和合本與 Strong 字典請依下方「資料檔案」章節的連結自行下載；恢復本 `bible.db` 不提供下載，請依「取得恢復本資料庫」自行取得。使用前請確認符合各自的授權條款。**


## 資料檔案

下列檔案不納入版本控制（已列入 `.gitignore`），請取得後放在 `bible.py` 同一個目錄，或下方「資料目錄與偵測順序」列出的其他位置：

| 檔案 | 用途 | 下載連結 | SHA-256 |
| :--- | :--- | :--- | :--- |
| `bible.db` | 恢復本內容（選用） | 不提供，見「取得恢復本資料庫」 | `1ef6a0fbf1434a0fc27757afbcf73f92e5d7a893d4556d5b067caabce39dab7d` |
| `cuvt.bbl.mybible` | 和合本（含 Strong 編號），沒有恢復本時的預設經文 | [Google Drive 資料夾](https://drive.google.com/drive/folders/1X1sSrIra8it3SX0nDbnuU_4PVSLj1_kt) | `946ad2a51d6666a7df6ebb9fc753f0f05a9fbf371730f39ee8e4e5ac5a8f37ec` |
| `strong_lite.dct.mybible` | Strong 字典 | [Google Drive 資料夾](https://drive.google.com/drive/folders/1X1sSrIra8it3SX0nDbnuU_4PVSLj1_kt) | `077b01dc7c3bab17d8497993016b4e72b1b5c637571a7cc0df323910a6df3cd5` |

`bible.db` 欄位的 SHA-256 是作者所用版本的雜湊，僅供參考；自行取得的檔案可能因應用程式版本不同而不同。若取得的 `bible.db` 是分割檔，可使用 `./bin/merge_db.sh` 合併。

只有 `cuvt.bbl.mybible` 就能啟動；加上 `strong_lite.dct.mybible` 可查 Strong 字義；加上 `bible.db` 才有恢復本、大綱、註解、書卷簡介與英文對照。

`strong_lite.dct.mybible` 的版權聲明與散布條件記載於該檔 `details` 表的 `comments` 欄位，使用與轉散布時請一併遵守。


### 取得恢復本資料庫

恢復本內容有版權，本專案不散布。作者使用的 `bible.db` 來自官方 Play 商店版應用程式：資料庫存放在應用程式的私有目錄，可用 adb 取出。大致流程如下，實際路徑與可行的方法依裝置與應用程式版本而異，本文件不保證特定路徑或方法：

1. 在電腦安裝 Android 平台工具（adb），手機開啟開發人員選項與 USB 偵錯。
2. 以 adb 取得應用程式私有目錄中的資料庫檔案（一般裝置需要 root 或應用程式允許備份）。
3. 以 `sqlite3 bible.db ".tables"` 確認含有 `content`、`footnote`、`outline`、`book_intro`、`book_name` 等資料表。
4. 將檔案命名為 `bible.db`，放進資料目錄（見下方「資料目錄與偵測順序」），或以 `bible data` 查看偵測結果。

請自行確認取得與使用方式符合該應用程式的使用條款與著作權規定。沒有 `bible.db` 時，程式仍可用和合本與 Strong 字典。


## 版本

目前版本：0.0.1（`python3 bible.py --version`）。下一個目標版本為 0.1.0，變更內容見 [CHANGELOG.md](CHANGELOG.md)。

## 資料目錄與偵測順序

資料檔案的偵測順序（前者優先，每一層只取實際存在的檔案）：

1. 命令列參數：`--db`、`--dict`、`--strongbible`
2. 環境變數：`BIBLE_STRONG_DICT`、`BIBLE_STRONG_BIBLE`
3. 已存設定（TUI 設定畫面中的資料庫路徑）
4. 使用者資料目錄
5. `bible.py` 所在目錄
6. 目前工作目錄

使用者資料目錄依作業系統而定：

| 系統 | 路徑 |
| :--- | :--- |
| Windows | `%APPDATA%\bible-cli` |
| macOS | `~/Library/Application Support/bible-cli` |
| Linux／Termux | `$XDG_DATA_HOME/bible-cli`（未設定時為 `~/.local/share/bible-cli`） |

筆記、書籤、串珠與設定存放於該目錄的 `bible-note.db`（執行 `:setup-storage` 後才會建立）。若 `bible.py` 同目錄有舊版的 `.bible-note.db`，互動式啟動時會詢問是否複製到新位置（複製而非搬移，原檔保留）。

執行 `python3 bible.py data` 可查看資料目錄、搜尋順序與實際偵測到的檔案。


## Environment Variables

以下環境變數為選用：

`BIBLE_STRONG_DICT`　Strong 字典 `.dct.mybible` 檔案路徑

`BIBLE_STRONG_BIBLE`　含 Strong 編號的聖經模組路徑，例如 `cuvt.bbl.mybible`

`BIBLE_CLI_DATA_DIR`　覆寫使用者資料目錄（筆記資料庫與資料檔案偵測都會使用）


## Installation

將 `bible.py` 與所需的資料檔案（`bible.db` 及／或 `*.mybible`）放在同一個目錄下即可（也可放在使用者資料目錄），不需要額外安裝套件。

Windows 使用者若要使用互動式 TUI，需另外安裝 `windows-curses`：

```bash
  pip install windows-curses
```

未安裝時程式會自動偵測並提示安裝方式，退回可用的 CLI 說明，不會直接崩潰。


## Run Locally

不帶任何子指令執行，程式會依偵測到的檔案自動判斷要開啟的介面：有恢復本時開啟恢復本，否則開啟和合本（Strong）畫面；若已在 TUI 設定中存過預設模式，則以該設定優先：

```bash
  python3 bible.py
```

強制指定介面：

```bash
  python3 bible.py --mode recovery
  python3 bible.py --mode strong
```


## Usage/Examples

`list`、`read`、`search` 預設使用恢復本（有 `bible.db` 時），沒有恢復本時自動改用和合本；也可用 `--source cuv|recovery` 明確指定，和合本模組路徑可用 `--strongbible` 指定。

列出書卷：

```bash
  python3 bible.py list
  python3 bible.py list 新約
  python3 bible.py list --source cuv
```

讀取經文（書卷名支援中／英文，也可用 1-66 的編號）：

```bash
  python3 bible.py read 創世記 1
  python3 bible.py read Genesis 1:1 --en --cuv
  python3 bible.py read 創 1:1 --source cuv
```

沒有恢復本時，書卷名可用全名、英文名、編號，或常用縮寫（如 `創`、`撒上`、`林前`、`gen`、`1sam`）。

全文搜尋：

```bash
  python3 bible.py search 起初 --lang big5
  python3 bible.py search 神創造 --source cuv
```

查看書卷簡介、經文註解（需要恢復本）：

```bash
  python3 bible.py intro 創世記
  python3 bible.py note 創世記 1:1 1
```

原文 Strong 對照與查詢：

```bash
  python3 bible.py orig 創世記 1:1 --word 1
  python3 bible.py strong G26
```

以和合本為來源時（或沒有恢復本時），下列項目不可用，程式會印出「此資料來源不含此內容」並以離開碼 2 結束：`--en`、`--no-outline`、`--no-footnote`、`--lang` 指定 `big5` 以外的語言。`intro`、`note` 需要恢復本，找不到時以離開碼 1 結束。

以上指令列出的行說明如下：

1：查看整本書卷的簡介
2：查看指定章節第 1 個註解的內容
4：顯示創世記 1:1 的原文對照，並直接查第 1 個標號字的字義
5：直接以 Strong 編號查希臘文字義（G 開頭為希臘文，H 開頭為希伯來文）


## Appendix

互動式 TUI 中常用按鍵（完整說明可在程式內按 `?` 或輸入 `:help` 查看）：

| 按鍵 | 功能 |
| :--- | :--- |
| `↑` `↓` / `j` `k` | 移動／捲動 |
| `PageUp` `PageDown` / `Space` | 整頁捲動 |
| `Enter` | 選取／展開收合經節註解 |
| `←` `→` | 讀經畫面切換上下章 |
| `e` / `c` / `n` | 讀經畫面切換英文對照／和合本正文／大綱顯示 |
| `y` | 複製目前經節 |
| `/` | 全文搜尋 |
| `s` / `r` | 切換到原文 Strong 畫面／切回恢復本畫面 |
| `b` / `B` | 返回上一頁 |
| `:` | 進入指令模式（類 vim，如 `:strong`、`:copy`、`:note`） |
| `q` / `Q` | 離開程式（詢問後離開／直接離開） |

滑鼠／觸控：可直接點擊書卷、章節、經文展開註解，或點擊原文 Strong 畫面中標色的原文字查字義。

## 人工智慧使用聲明

- 本程式有使用AI輔助開發與優化。
