# 🌴 泰國棕櫚油 AI 監控專案 - 現況紀錄 (Status Report)

## 📅 最後更新日期：2026-03-28

### 1. 專案目標 (Project Goal)
為泰國甲米 (Krabi) 壓榨廠 (CPO Mill) 提供每日自動化的市場情報監控。系統會自動抓取當日實時數據，進行 AI 分析，並透過 LINE 與網頁同步更新資訊。

### 2. 系統架構 (System Architecture)
- **AI 引擎**：Google Gemini 2.5-Flash (最新版本，過濾 2024/2025 過時資訊)。
- **搜尋引擎**：Serper.dev API (實時 Google 搜尋)。
- **數據分析**：Pandas (處理價格 CSV)、Matplotlib (繪製趨勢圖)。
- **前端呈現**：GitHub Pages (Static Site Generator)，位於 `docs/` 資料夾。
- **手機推播**：LINE Messaging API (Push Message)，包含文字摘要與圖表連結。

### 3. API 設定與金鑰 (位於 .env)
- `GEMINI_API_KEY`: Google AI Studio 申請。
- `SERPER_API_KEY`: 實時搜尋服務。
- `LINE_CHANNEL_ACCESS_TOKEN`: Messaging API 推播權限。
- `LINE_USER_ID`: 接收推播的目標 ID (Uf45f5c3efc5fcd2df55a873c9d7b98c1)。

### 4. 關鍵路徑
- **分析腳本**：`scripts/daily_palm_report.py`
- **數據存儲**：`data/palm_prices.csv`
- **雲端網站**：[https://aphsu124.github.io/myAgent/](https://aphsu124.github.io/myAgent/)
- **日誌記錄**：`cron_log.txt`

### 5. 自動化邏輯 (Automation)
- **觸發時間**：泰國時間每天 13:30 (ICT)。
- **執行頻率**：Crontab 設定為每 15 分鐘執行一次檢查。
- **時區彈性**：程式內建時區轉換，支援日本/泰國等跨時區電腦執行。

### 6. 待辦事項 (Backlog)
- [ ] 考慮增加出口航運運費 (Freight Rate) 監控。
- [ ] 增加化肥價格趨勢分析。
- [ ] 串接更多的南部產區 (如 Surat Thani, Chumphon) 的價格對比。

---
**Jarvis 隨時待命。如有需要調整系統或重啟工作，請直接讀取此檔案即可。**
