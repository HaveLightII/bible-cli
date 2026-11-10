# Changelog

版本號依 [Semantic Versioning](https://semver.org/lang/zh-TW/)。

## [Unreleased] - 目標 0.1.0

- 以公開的和合本為預設資料來源；偵測到恢復本 `bible.db` 與 Strong 資料庫時仍可使用
- 建立資料來源抽象層，TUI 與 CLI 不再直接存取 SQL
- 使用者資料（筆記、書卷、設定）改放各作業系統的使用者資料目錄
- 重整為可用 pipx / uv 安裝的套件，提供 `bible` 指令
- 加入測試與跨平台 CI

## [0.0.1] - 基準版本

- 單檔 `bible.py`，提供恢復本 CLI / TUI 與原文 Strong 對照
- 新增 `--version` 參數
- 發行內容不再附帶任何資料庫檔案，改以連結提供（見 README「資料檔案」）
