import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_USER_ID = os.getenv("LINE_USER_ID")

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPORT_DIR = os.path.join(BASE_DIR, "docs/reports")
GITHUB_IO_URL = "https://aphsu124.github.io/myAgent"

# 儲存後端切換（gdrive / icloud）
STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "icloud")

# iCloud Paths（保留供 fallback）
ICLOUD_BASE = "/Users/bucksteam/Library/Mobile Documents/com~apple~CloudDocs/泰國/工作/甲米油廠/簡報"
ICLOUD_EXCEL = os.path.join(ICLOUD_BASE, "palm_oil_history.xlsx")
ICLOUD_CHART = os.path.join(ICLOUD_BASE, "2026_Palm_Oil_Trend_Master.png")

# Google Drive Folder IDs
GDRIVE_FOLDER_BRIEFING  = os.getenv("GDRIVE_FOLDER_BRIEFING")   # 簡報
GDRIVE_FOLDER_CMD       = os.getenv("GDRIVE_FOLDER_CMD")         # 指令
GDRIVE_FOLDER_MEETING   = os.getenv("GDRIVE_FOLDER_MEETING")     # 會議
GDRIVE_FOLDER_MONITOR   = os.getenv("GDRIVE_FOLDER_MONITOR")     # 監控/截圖
GDRIVE_FOLDER_CONTACT   = os.getenv("GDRIVE_FOLDER_CONTACT")     # 聯絡人
GDRIVE_FOLDER_TRANSLATE = os.getenv("GDRIVE_FOLDER_TRANSLATE")   # 翻譯

# Google Drive File IDs（首次上傳後填入 .env）
GDRIVE_EXCEL_FILE_ID    = os.getenv("GDRIVE_EXCEL_FILE_ID")
GDRIVE_CMD_FILE_ID      = os.getenv("GDRIVE_CMD_FILE_ID")
GDRIVE_CONTACT_FILE_ID  = os.getenv("GDRIVE_CONTACT_FILE_ID")

# Fonts
CHINESE_FONT = '/System/Library/Fonts/STHeiti Light.ttc'
MS_JH_FONT = 'Microsoft JhengHei'
