# 🌴 泰國棕櫚油 AI 監控專案 - 現況紀錄 (Status Report)

## 📅 最後更新日期：2026-03-29

### 1. 專案核心架構 (System Core)
- **AI 引擎**：Gemini 2.5-Flash (負責棕櫚油分析與泰文商務翻譯)。
- **自動化邏輯**：
    - 棕櫚油監控：07:00 晨間新聞 / 13:30 完整報告。
    - 會議處理：手動觸發或偵測 iCloud 錄音檔。
- **手機推播**：LINE Messaging API。
- **雲端呈現**：GitHub Pages 靜態網站 與 iCloud Drive 資料夾。

### 2. 關鍵檔案路徑
- **棕櫚油監控**：`scripts/daily_palm_report.py`
- **會議學習系統**：`scripts/process_meeting.py`
- **歷史數據**：`data/palm_prices.csv` (價格) / `data/thai_vocab.json` (單字)
- **iCloud 歸檔**：`泰國/工作/甲米油廠/` 下的簡報與會議目錄。

### 3. 會議錄音與泰文學習分支 (New!)
- **功能**：掃描錄音轉文字 -> 生成中文摘要 -> 提取商務泰文單字。
- **單字本**：`泰國商務單字本_最新版.pdf`。
- **特點**：
    - 完美解決泰文 CTL (母音疊加) 與中文字體亂碼。
    - 單字按出現頻率排序，介面極簡不顯示次數。
    - 自動化累積，每次會議後自動更新。

### 4. API 配置 (位於 .env)
- `GEMINI_API_KEY`: 核心分析引擎。
- `SERPER_API_KEY`: Google 實時搜尋。
- `LINE_CHANNEL_ACCESS_TOKEN`: Messaging API。
- `LINE_USER_ID`: Uf45f5c3efc5fcd2df55a873c9d7b98c1。
- `OPENAI_API_KEY`: (待填寫) 用於 Whisper 轉錄。

### 5. 後續擴充方向
- 整合生質柴油政策追蹤。
- 完善會議自動錄音處理流程。
- 增加泰南口音 (Pasa Tai) 特有詞彙標註。

---
**Jarvis 隨時待命。系統已成功整合營運監控與語言學習雙功能。**
