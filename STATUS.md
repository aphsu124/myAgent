# 🌴 泰國棕櫚油 AI 監控專案 - 現況紀錄 (Status Report)

## 📅 最後更新日期：2026-03-29

### 1. 專案核心架構 (System Core)
- **AI 引擎**：Gemini 2.5-Flash (分析/翻譯) + OpenAI Whisper-1 (語音轉文字)。
- **自動化邏輯**：
    - 棕櫚油監控：07:00 晨報 (M) / 13:30 日報 (D)。
    - 會議處理：掃描 `iCloud/會議/錄音/` 下的新音檔。
- **手機推播**：LINE Messaging API (含網頁連結與圖表通知)。
- **雲端呈現**：GitHub Pages 靜態網站 與 iCloud Drive 多格式歸檔。

### 2. 檔案命名與儲存規範 (Standardized)
- **命名規則**：`YYYYMMDD_[M/D]_report` (例如：20260329_D_report)。
- **HTML 路徑**：`docs/reports/` (GitHub 線上版)。
- **PDF/Excel 路徑**：`泰國/工作/甲米油廠/簡報/` (iCloud 存檔)。
- **逐字稿路徑**：`泰國/工作/甲米油廠/會議/逐字稿/` (存放原始泰文)。

### 3. 會議與泰文學習分支 (Fully Operational)
- **主腳本**：`scripts/process_meeting.py`。
- **智慧模式分流**：
    - **一般會議**：轉錄 + 摘要 + 待辦事項 + 提取 10 個核心單字並更新 PDF。
    - **學習/個人 (檔名含「品川」)**：轉錄 + 摘要，但排除單字更新邏輯。
- **渲染引擎**：Matplotlib 繪圖引擎 (解決泰文 CTL 音標疊加與中文顯示問題)。

### 4. API 配置 (位於 .env)
- `GEMINI_API_KEY`: 核心分析引擎。
- `SERPER_API_KEY`: Google 實時搜尋 (已加入旅遊資訊過濾器)。
- `LINE_CHANNEL_ACCESS_TOKEN` & `LINE_USER_ID`: 官方帳號推播。
- `OPENAI_API_KEY`: Whisper 泰語語音轉錄專用。

### 5. 待辦事項 (Backlog)
- [ ] 串接生質柴油 (Biodiesel) 政策變動的深度追蹤。
- [ ] 針對錄音檔加入情緒分析 (Sentiment Analysis)。
- [ ] 優化單字本 PDF，加入「棕櫚油商務情境」的 AI 生成例句。

---
**Jarvis 隨時待命。系統已處於智慧化全自動運行狀態。**
