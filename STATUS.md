# 🌴 泰國棕櫚油 AI 監控專案 - 現況紀錄 (Status Report)

## 📅 最後更新日期：2026-03-29

### 1. 專案核心架構 (System Core)
- **AI 引擎**：Gemini 2.5-Flash (最新跨年度動態校準版)。
- **自動化邏輯**：分流雙時段執行 (07:00 晨間新聞 / 13:30 完整報告)。
- **手機推播**：LINE Messaging API (Push Message)。
- **雲端呈現**：GitHub Pages 靜態網站 ([https://aphsu124.github.io/myAgent/](https://aphsu124.github.io/myAgent/))。

### 2. 關鍵檔案路徑
- **主腳本**：`scripts/daily_palm_report.py` (包含分析、網頁生成、Git 同步、LINE 推播)。
- **數據庫**：`data/palm_prices.csv` (存放 FFB/CPO 歷史價格)。
- **網頁首頁**：`docs/index.html` (永遠顯示當日最新產出的報告內容)。
- **歷史報告**：`docs/reports/` (存放所有 HTML 格式的歷史簡報)。

### 3. API 配置 (位於 .env)
- `GEMINI_API_KEY`: AI 分析。
- `SERPER_API_KEY`: 實時 Google 搜尋。
- `LINE_CHANNEL_ACCESS_TOKEN`: Messaging API 權杖。
- `LINE_USER_ID`: 您的專屬接收 ID (Uf45f5c3efc5fcd2df55a873c9d7b98c1)。

### 4. 運作說明
- **執行頻率**：Crontab 每 15 分鐘檢查一次。
- **時區**：支援跨時區執行，自動以泰國 (ICT, UTC+7) 時間為準。
- **防重複機制**：各時段報告產出後，當日不再重複發送 LINE 或更新檔案。

### 5. 後續優化方向 (Backlog)
- [ ] 增加南部多個主要收購點的價格對照。
- [ ] 串接生質柴油 (Biodiesel) 政策變動的深度追蹤。
- [ ] 增加肥料與農資成本的月度趨勢分析。

---
**Jarvis 隨時待命。系統已處於全自動運行狀態。**
