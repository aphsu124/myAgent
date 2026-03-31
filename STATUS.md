# 🌴 泰國棕櫚油 AI 監控專案 - 現況紀錄 (Status Report)

## 📅 最後更新日期：2026-03-31

### 1. 專案核心架構 (System Core)
- **AI 引擎**：Gemini 2.5-Flash (分析/翻譯) + OpenAI Whisper-1 (轉錄)。
- **自動化邏輯**：
    - 晨報 (M) / 日報 (D) 自動排程 (07:00 / 13:30 ICT)。
    - 基差監控：CPO 現貨 vs BMD 期貨。
- **數據呈現**：GitHub Pages 網站 + iCloud 歸檔。

### 2. 檔案與報表規範 (Standardized)
- **命名**：`YYYYMMDD_[M/D]_report` (例如：20260331_D_report)。
- **Excel**：`palm_oil_history.xlsx` (14 號大字版、內建公式與術語指南)。
- **趨勢圖**：`2026_Palm_Oil_Trend_Master.png` (包含基差分析與大事記標註)。

### 3. 手機遙控開發紀錄 (Research & Debugging)
- **網路環境分析**：當前網路環境具備強大的入站過濾與長連線偵測，不建議繼續嘗試 LINE/Discord。
- **已部署工具**：`scripts/line_server.py`, `scripts/discord_bot.py`, `scripts/telegram_bot.py` (皆已完成邏輯開發，待硬體環境更換後可直接啟用)。
- **保底方案**：**iCloud 指令信箱法** (透過 `scripts/remote_watcher.py` 監控 `CMD.txt`) 為目前最穩定之遠端觸發手段。

### 4. 會議錄音分支 (Operational)
- **路徑**：`iCloud/會議/錄音` -> `摘要/` + `逐字稿/`。
- **單字本**：`泰國商務單字本_最新版.pdf` (自動累積、不顯示次數、完美泰文渲染)。

### 5. API 配置 (.env)
- `GEMINI_API_KEY`, `SERPER_API_KEY`, `OPENAI_API_KEY`
- `LINE_CHANNEL_ACCESS_TOKEN`, `LINE_USER_ID`, `TELEGRAM_BOT_TOKEN`, `DISCORD_BOT_TOKEN`

---
**Jarvis 隨時待命。核心功能已固若金湯，手機遙控將於硬體遷移時再行優化。**
