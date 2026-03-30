# 🌴 泰國棕櫚油 AI 監控專案 - 現況紀錄 (Status Report)

## 📅 最後更新日期：2026-03-30

### 1. 專案核心架構 (System Core)
- **AI 引擎**：Gemini 2.5-Flash (分析與翻譯) + OpenAI Whisper-1 (錄音轉錄)。
- **自動化邏輯**：07:00 晨報 (M) / 13:30 日報 (D)。
- **通訊管道**：LINE Messaging API 24H 穩定推播。
- **雲端呈現**：GitHub Pages 網站 + iCloud 專業歸檔。

### 2. 智慧油廠轉型提案 (Management Proposal)
- **定稿文件**：`AI_Management_Proposal_V10.pdf` (位於 iCloud)。
- **精確型號**：
    - 伺服器：Apple Mac Mini (M4 Pro, MC6P3TA/A) / 48GB RAM。
    - 供電：APC Back-UPS Pro BR1000G-TW。
    - 影像：Hikvision DS-2CD2043G2-I (10台)。
    - 網路：UniFi USW-Lite-16-PoE + U6-Lite。
- **排版引擎**：ReportLab Platypus (確保多語言排版絕不重疊)。

### 3. 數據庫與報表規範
- **Excel 檔案**：`palm_oil_history.xlsx` (14號微軟正黑體、內建計算指南與公式說明)。
- **趨勢圖**：`2026_Palm_Oil_Trend_Master.png` (包含 FFB, CPO, BMD 三線對比及大事記標註)。
- **基差監控**：`Basis = CPO - (BMD/1000 * EX_Rate)`。

### 4. 會議錄音處理邏輯
- **主腳本**：`scripts/process_meeting.py`。
- **功能**：泰文轉錄 -> 中文摘要 -> 泰文逐字稿存檔 -> 商務單字本 PDF 更新。
- **分流機制**：針對標記檔案（如：品川）自動跳過單字更新，保持數據庫純淨。

### 5. 後續里程碑 (Next Milestones)
- [ ] 採購 M4 Pro Mac Mini 並執行系統遷移。
- [ ] 開發 LINE Webhook 伺服器實現手機指令回傳。
- [ ] 整合 10 路影像辨識模型 (Phase 2)。

---
**Jarvis 隨時待命。系統已完成從「資料收集」到「決策支持」的初步轉型。**
