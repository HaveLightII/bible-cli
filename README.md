# bible-cli：聖經 CLI / TUI

以指令 `bible`（Python 套件 `bibletui`）提供的聖經查詢工具，同時支援命令列（CLI）批次查詢與互動式終端機（TUI）瀏覽，並可對照原文 Strong 編號查字義。不需要額外安裝資料庫伺服器，僅依賴 sqlite 檔案（`bible.db`、MySword 的 `.mybible` 模組）運作。

恢復本 `bible.db` 為選用：偵測到時預設使用恢復本；沒有時以和合本（`cuvt.bbl.mybible`）為預設，仍可閱讀、搜尋與查 Strong 字義，只是沒有大綱、註解、書卷簡介與英文對照。


## Features

- 恢復本經文瀏覽：書卷／章／節查詢，含大綱、註解、英文對照、和合本正文切換
- 和合本經文瀏覽與全文搜尋：不需要恢復本，CLI 以 `--source cuv|recovery` 選擇資料來源
- 原文 Strong 編號對照：逐字標色顯示 Strong 編號，可查希臘文／希伯來文字義
- 恢復本與原文 Strong 畫面可在 TUI 中以 `s` / `r` 即時切換，兩邊瀏覽狀態互不干擾
- 全文搜尋：支援多字串交集查詢、`--exclude` 差集查詢
- 類 vim 的 `:` 指令模式，可直接輸入 `:創世記 1 1` 之類的參照跳轉
- 滑鼠／觸控支援：點擊書卷、章節、經文展開註解、原文標色字查字義
- 資料檔案安裝指令 `bible data install`：驗證資料表結構後安裝到使用者資料目錄，不連網，可直接安裝 MySword 的 `.gz` 與 `.zip` 壓縮檔
- 多個 MySword 聖經模組並存：`bible data list` 查看、`bible data use` 切換預設、`bible data uninstall` 移除；CLI 用 `--module` 臨時指定，TUI 用 `:module` 切換
- 選用的筆記／書籤／串珠功能（需執行 `:setup-storage` 啟用，才會在使用者資料目錄建立本機資料庫）
- 同時相容 Linux / macOS / Windows（Windows 需另外安裝 `windows-curses`）


## Tech Stack

**執行環境：** Python 3.10 以上

**核心套件：** `sqlite3`、`curses`（Windows 為 `windows-curses`）、`argparse`

**資料來源：** `bible.db`（恢復本內容，選用）、MySword 格式的 `.dct.mybible`（Strong 字典）與 `.bbl.mybible`（含 Strong 編號的和合本）

**本倉庫不附帶任何資料庫檔案。和合本請依「取得和合本」從 MySword 官方網站自行下載；Strong 字典請依下方「資料檔案」章節的連結下載；恢復本 `bible.db` 不提供下載，請依「取得恢復本資料庫」自行取得。使用前請確認符合各自的授權條款。**


## 資料檔案

下列檔案不納入版本控制（已列入 `.gitignore`），請取得後以 `bible data install` 安裝（見下方「安裝資料檔案」），或直接放進「資料目錄與偵測順序」列出的位置：

| 檔案 | 用途 | 下載連結 | SHA-256 |
| :--- | :--- | :--- | :--- |
| `bible.db` | 恢復本內容（選用） | 不提供，見「取得恢復本資料庫」 | `1ef6a0fbf1434a0fc27757afbcf73f92e5d7a893d4556d5b067caabce39dab7d` |
| `cuvt.bbl.mybible` | 和合本（含 Strong 編號），沒有恢復本時的預設經文 | MySword 官方下載頁，見「取得和合本」 | `946ad2a51d6666a7df6ebb9fc753f0f05a9fbf371730f39ee8e4e5ac5a8f37ec` |
| `strong_lite.dct.mybible` | Strong 字典 | [Google Drive 資料夾](https://drive.google.com/drive/folders/1X1sSrIra8it3SX0nDbnuU_4PVSLj1_kt) | `077b01dc7c3bab17d8497993016b4e72b1b5c637571a7cc0df323910a6df3cd5` |

表格中的 SHA-256 是作者所用版本的雜湊，僅供參考；自行取得的檔案可能因來源或版本不同而不同，安裝時只會顯示警告，不會拒絕。若取得的 `bible.db` 是分割檔，可使用 `./bin/merge_db.sh` 合併。

只有 `cuvt.bbl.mybible` 就能啟動；加上 `strong_lite.dct.mybible` 可查 Strong 字義；加上 `bible.db` 才有恢復本、大綱、註解、書卷簡介與英文對照。

`strong_lite.dct.mybible` 的版權聲明與散布條件記載於該檔 `details` 表的 `comments` 欄位（摘要見 [THIRD_PARTY_NOTICES.md](https://github.com/HaveLightII/bible-cli/blob/main/THIRD_PARTY_NOTICES.md)），使用與轉散布時請一併遵守。


### 安裝資料檔案

把下載的檔案放進同一個資料夾，再安裝到使用者資料目錄：

```bash
  bible data install --from-dir ~/Downloads/bible-data
  bible data install --from-file cuvt.bbl.mybible.gz --from-file strong_lite.dct.mybible
```

1：安裝資料夾第一層中的 `bible.db`、`*.bbl.mybible`、`*.dct.mybible`（含 `.gz`、`.zip`）  
2：逐一指定檔案，可重複使用

說明：

- 不會連網；`.mybible` 檔會檢查資料表結構（和合本須含 `Bible` 表、Strong 字典須含 `dictionary` 表，`bible.db` 須含 `content`、`book_name`），SHA-256 與作者版本不同時只顯示警告
- 可直接安裝 `.gz` 與 `.zip` 壓縮檔（MySword 網站兩種都有）；`.zip` 內每個 `.mybible` 檔各自安裝，只取檔名，不依壓縮檔內的路徑建立資料夾；都會先解壓縮到 `.part` 再驗證
- `.bbl.mybible` 內容必須是聖經模組、`.dct.mybible` 必須是字典，否則拒絕
- 檔名比對忽略大小寫，並把底線視為點（雲端硬碟下載時常把 `cuvt.bbl.mybible` 改成 `cuvt_bbl.mybible`，安裝後會還原為正確檔名）
- 目標已有相同內容的檔案時略過；內容不同時需加 `--force` 才會覆蓋
- 安裝完成後可用 `bible data list` 查看已安裝的資料庫，`bible data` 查看偵測結果


### 取得和合本

和合本模組 `cuvt.bbl.mybible` 取自 MySword 的模組。本專案不提供它的下載連結，請自行向 MySword 取得：

- 網站：開啟 [MySword 的 Bibles 下載頁](https://www.mysword.info/download-mysword/bibles)，在 Chinese 區找到「Chinese Union Version 和合本 - Traditional with Strong's numbers 繁體中文版連史特朗經文滙篇」（簡稱 Cuv/T，檔名 `cuvt.bbl.mybible.gz`，頁面標示下載約 2.1 MB、解壓後約 6.5 MB），下載後直接安裝：

  ```bash
  bible data install --from-file cuvt.bbl.mybible.gz
  ```

- 應用程式：在 MySword 應用程式內的模組下載畫面（Download modules）下載同一個模組，再從 MySword 的模組資料夾（首次執行時選擇的 Modules Path）取出 `cuvt.bbl.mybible`，以 `--from-file` 安裝。

下載頁沒有標示此模組的授權條款；使用前請自行確認 MySword 的授權說明與經文版權。MySword 目前提供的檔案與表格中的 SHA-256 是否相同，作者未驗證；不同時 `bible data install` 只會警告。


### 取得恢復本資料庫

恢復本內容有版權，本專案不散布。作者使用的 `bible.db` 來自官方 Play 商店版應用程式：資料庫存放在應用程式的私有目錄，可用 adb 取出。大致流程如下，實際路徑與可行的方法依裝置與應用程式版本而異，本文件不保證特定路徑或方法：

1. 在電腦安裝 Android 平台工具（adb），手機開啟開發人員選項與 USB 偵錯。
2. 以 adb 取得應用程式私有目錄中的資料庫檔案（一般裝置需要 root 或應用程式允許備份）。
3. 以 `sqlite3 bible.db ".tables"` 確認含有 `content`、`footnote`、`outline`、`book_intro`、`book_name` 等資料表。
4. 將檔案命名為 `bible.db`，放進資料目錄（見下方「資料目錄與偵測順序」），或以 `bible data` 查看偵測結果。

請自行確認取得與使用方式符合該應用程式的使用條款與著作權規定。沒有 `bible.db` 時，程式仍可用和合本與 Strong 字典。


### 多個聖經模組

使用者資料目錄可同時放多個 MySword 聖經模組（`*.bbl.mybible`），代號為檔名去掉 `.bbl.mybible`（例如 `kjv.bbl.mybible` 的代號是 `kjv`）；也可用模組內的簡稱（如 `Cuv/T`），不分大小寫。

```bash
  bible data list
  bible data use kjv
  bible data use --reset
  bible data uninstall kjv
  bible read 創 1:1 --module cuvt
  bible --module kjv
```

1：列出已安裝的聖經模組、字典與恢復本，`*` 為目前使用中  
2：設定預設聖經模組（寫入使用者資料目錄的 `config.json`）  
3：清除預設，改回自動選擇  
4：移除使用者資料目錄內的資料庫（互動環境會詢問；非互動環境需加 `--yes`）  
5：只這一次改用指定模組，不改預設  
6：以指定模組啟動 TUI

說明：

- 沒有設定預設時，有 `cuvt` 就用 `cuvt`，否則取檔名排序第一個；安裝新模組不會改變預設
- `uninstall` 只移除使用者資料目錄內的檔案；位於目前目錄或原始碼目錄的檔案會拒絕並印出路徑，請自行刪除。`recovery` 代表恢復本 `bible.db`
- 代號同時對應聖經模組與字典時，加 `.bbl` 或 `.dct` 區分（如 `eng.bbl`）
- TUI 的原文 Strong 畫面使用目前的聖經模組：輸入 `:module` 列出模組，`:module kjv` 切換並記為預設
- 字典也可用 `data use` 切換預設
- 命令列參數與環境變數（`BIBLE_STRONG_BIBLE`、`BIBLE_STRONG_DICT`）優先於 `data use` 的預設；`data use` 的預設則優先於 TUI 設定畫面中的 `strong_db_path`、`dict_db_path`

### 其他 MySword 聖經模組的相容性

`.bbl.mybible` 都是 SQLite，內含 `Details`（一筆說明）與 `Bible(Book, Chapter, Verse, Scripture)`，格式見 [MySword Modules' Format](https://mysword.info/modules-format)。程式讀取其中的簡稱、說明、`OT`、`NT`、`Strong` 欄位，經文中的 GBF 標記會去除後顯示（標題 `<TS>` 顯示為〔標題〕、譯註 `<RF>` 不顯示、斜體與耶穌的話等只去標記、Strong 標記 `<WG>`、`<WH>` 保留供查字義）。

限制：

- 只支援 66 卷的書卷編號；書名一律顯示繁體中文，不隨模組語言變換
- 只有 `Strong` 欄位為 1（或經文內含 Strong 標記）的模組可用 `orig`、可在 TUI 點字查字義
- 逐字對照（interlinear，含 `<Q>`、`<E>` 等區塊標記）的模組只去標記，各層文字會串在一起，未做版面處理
- 搜尋會一次載入整個模組；數百 MB 的模組（如 BHSE、OHB）會很慢、很吃記憶體
- 只測過 `Cuv/T` 與測試用的虛構模組；MySword 網站上的其他模組未逐一實測
- 商業或有版權的模組，授權由使用者自行確認

## 版本

目前版本：0.2.0（`bible --version`），變更內容見 [CHANGELOG.md](https://github.com/HaveLightII/bible-cli/blob/main/CHANGELOG.md)。

## 資料目錄與偵測順序

資料檔案的偵測順序（前者優先，每一層只取實際存在的檔案）：

1. 命令列參數：`--db`、`--dict`、`--strongbible`、`--module`
2. 環境變數：`BIBLE_STRONG_DICT`、`BIBLE_STRONG_BIBLE`
3. `bible data use` 設定的預設模組（`config.json`）
4. 已存設定（TUI 設定畫面中的資料庫路徑）
5. 使用者資料目錄
6. 目前工作目錄
7. 倉庫根目錄（只有從原始碼執行時才搜尋，安裝版不依賴倉庫）

使用者資料目錄依作業系統而定：

| 系統 | 路徑 |
| :--- | :--- |
| Windows | `%APPDATA%\bible-cli` |
| macOS | `~/Library/Application Support/bible-cli` |
| Linux／Termux | `$XDG_DATA_HOME/bible-cli`（未設定時為 `~/.local/share/bible-cli`） |

筆記、書籤、串珠與設定存放於該目錄的 `bible-note.db`（執行 `:setup-storage` 後才會建立）。從原始碼執行時，若倉庫根目錄有舊版的 `.bible-note.db`，互動式啟動時會詢問是否複製到新位置（複製而非搬移，原檔保留）；安裝版不處理舊檔。

執行 `bible data` 可查看資料目錄、搜尋順序與實際偵測到的檔案。


## Environment Variables

以下環境變數為選用：

`BIBLE_STRONG_DICT`　Strong 字典 `.dct.mybible` 檔案路徑

`BIBLE_STRONG_BIBLE`　含 Strong 編號的聖經模組路徑，例如 `cuvt.bbl.mybible`

`BIBLE_CLI_DATA_DIR`　覆寫使用者資料目錄（筆記資料庫與資料檔案偵測都會使用）


## Installation

建議以 `uv tool` 從 GitHub 安裝，會建立 `bible` 指令：

```bash
  uv tool install git+https://github.com/HaveLightII/bible-cli
```

更新到最新版：

```bash
  uv tool install --reinstall git+https://github.com/HaveLightII/bible-cli
```

發行於 PyPI 的套件名為 `bible-strong-tui`（安裝後指令仍為 `bible`，程式匯入名稱為 `bibletui`）；PyPI 安裝尚待首次發布後實測，目前請以上述 GitHub 方式安裝。

`pipx install git+https://github.com/HaveLightII/bible-cli` 理論上同樣可行，但作者尚未實測。已在 Android Termux 實測 `uv tool`；macOS 與 Windows 尚未實測。

從原始碼執行（不安裝）：

```bash
  git clone https://github.com/HaveLightII/bible-cli
  cd bible-cli
  python3 bible.py
```

以可編輯模式安裝（開發用）：

```bash
  pip install -e .
```

Windows 以 `pip` 或 `uv` 安裝時會自動安裝 `windows-curses`；從原始碼直接執行時，需自行安裝：

```bash
  pip install windows-curses
```

未安裝時程式會自動偵測並提示安裝方式，退回可用的 CLI 說明，不會直接崩潰。

安裝後請先安裝資料檔案（見上方「安裝資料檔案」）；找不到任何資料庫時，程式會印出提示並以離開碼 1 結束。


## Run

不帶任何子指令執行，程式會依偵測到的檔案自動判斷要開啟的介面：有恢復本時開啟恢復本，否則開啟和合本（Strong）畫面；若已在 TUI 設定中存過預設模式，則以該設定優先：

```bash
  bible
```

強制指定介面：

```bash
  bible --mode recovery
  bible --mode strong
```


## Usage/Examples

以下以安裝版的 `bible` 指令為例；從原始碼執行時，請把 `bible` 換成 `python3 bible.py`，也可用 `python3 -m bibletui`。

`list`、`read`、`search` 預設使用恢復本（有 `bible.db` 時），沒有恢復本時自動改用和合本；也可用 `--source cuv|recovery` 明確指定，聖經模組可用 `--module 代號` 或 `--strongbible 路徑` 指定（見「多個聖經模組」）。

列出書卷：

```bash
  bible list
  bible list 新約
  bible list --source cuv
```

讀取經文（書卷名支援中／英文，也可用 1-66 的編號）：

```bash
  bible read 創世記 1
  bible read Genesis 1:1 --en --cuv
  bible read 創 1:1 --source cuv
```

沒有恢復本時，書卷名可用全名、英文名、編號，或常用縮寫（如 `創`、`撒上`、`林前`、`gen`、`1sam`）。

全文搜尋：

```bash
  bible search 起初 --lang big5
  bible search 神創造 --source cuv
```

查看書卷簡介、經文註解（需要恢復本）：

```bash
  bible intro 創世記
  bible note 創世記 1:1 1
```

原文 Strong 對照與查詢：

```bash
  bible orig 創世記 1:1 --word 1
  bible strong G26
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
| `s` / `r` | 切換到原文 Strong 畫面，已在該畫面時依序輪替已安裝的聖經模組（不改變預設）／切回恢復本畫面 |
| `b` / `B` | 返回上一頁 |
| `:` | 進入指令模式（類 vim，如 `:strong`、`:copy`、`:note`） |
| `q` / `Q` | 離開程式（詢問後離開／直接離開） |

滑鼠／觸控：可直接點擊書卷、章節、經文展開註解，或點擊原文 Strong 畫面中標色的原文字查字義。

## 人工智慧使用聲明

- 本程式有使用AI輔助開發與優化。


## Development

測試使用標準函式庫的 `unittest`，不需要額外套件；測試資料全部是虛構的合成資料，不含任何聖經經文或版權內容：

```bash
  python3 -m unittest discover -s tests -v
```

GitHub Actions 會在 Linux、macOS、Windows 與 Python 3.10 至 3.14 上執行同一組測試（`.github/workflows/tests.yml`）。TUI 的煙霧測試使用偽終端機，只在 Linux 與 macOS 執行。

另有 `bin/baseline.sh` 與 `bin/equiv*.py`：前者以真實資料庫比對 CLI 輸出，需要自備三份資料庫，不納入 CI。


## License

以 [MIT 授權](https://github.com/HaveLightII/bible-cli/blob/main/LICENSE) 發布。本倉庫不含任何聖經資料庫，資料檔案各自的授權請見「資料檔案」章節與 [THIRD_PARTY_NOTICES.md](https://github.com/HaveLightII/bible-cli/blob/main/THIRD_PARTY_NOTICES.md)。
