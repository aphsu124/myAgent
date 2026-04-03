import os
import time
import subprocess
import datetime
import requests
from dotenv import load_dotenv

load_dotenv()
from modules.config import STORAGE_BACKEND, GDRIVE_CMD_FILE_ID
LINE_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
USER_ID = os.getenv("LINE_USER_ID")

ICLOUD_CMD_FILE = "/Users/bucksteam/Library/Mobile Documents/com~apple~CloudDocs/泰國/工作/甲米油廠/指令/CMD.txt"

def send_line_notification(text):
    if not LINE_TOKEN or not USER_ID: return
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_TOKEN}"}
    try:
        requests.post(url, headers=headers, json={"to": USER_ID, "messages": [{"type": "text", "text": text}]}, timeout=15)
    except Exception as e:
        print(f"⚠️ LINE 通知失敗: {e}")

def read_command():
    if STORAGE_BACKEND == 'gdrive' and GDRIVE_CMD_FILE_ID:
        from modules.gdrive_utils import read_text_file
        content = read_text_file(GDRIVE_CMD_FILE_ID)
        return content.strip() if content else ""
    else:
        if os.path.exists(ICLOUD_CMD_FILE) and os.path.getsize(ICLOUD_CMD_FILE) > 0:
            with open(ICLOUD_CMD_FILE, "r", encoding="utf-8") as f:
                return f.read().strip()
        return ""

def clear_command():
    if STORAGE_BACKEND == 'gdrive' and GDRIVE_CMD_FILE_ID:
        from modules.gdrive_utils import write_text_file
        write_text_file(GDRIVE_CMD_FILE_ID, "")
    else:
        try:
            with open(ICLOUD_CMD_FILE, "w", encoding="utf-8") as f:
                f.write("")
        except Exception as e:
            print(f"⚠️ 清空 CMD.txt 失敗: {e}")

def main():
    mode = "Google Drive" if (STORAGE_BACKEND == 'gdrive' and GDRIVE_CMD_FILE_ID) else f"iCloud ({os.path.basename(ICLOUD_CMD_FILE)})"
    print(f"🕵️ Jarvis 指令監聽器已啟動... (監控來源: {mode})")

    # iCloud 模式：確保檔案存在
    if STORAGE_BACKEND != 'gdrive' and not os.path.exists(ICLOUD_CMD_FILE):
        try:
            with open(ICLOUD_CMD_FILE, "w", encoding="utf-8") as f: f.write("")
        except Exception as e:
            print(f"⚠️ 無法建立 CMD.txt: {e}")

    while True:
        try:
            command = read_command()

            if command:
                timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                print(f"📩 [{timestamp}] 偵測到手機指令: {command}")

                if command == "日報":
                    send_line_notification("🚀 收到手機指令：正在產出日報...")
                    subprocess.run(["python3", "scripts/daily_palm_report.py"])
                    send_line_notification("✅ 日報產出完畢！")

                elif command == "試算":
                    send_line_notification("📊 收到手機指令：正在刷新 Excel...")
                    subprocess.run(["python3", "-c", "from scripts.modules.excel_handler import generate_trend_chart; generate_trend_chart()"])
                    send_line_notification("✅ Excel 樣式已刷新。")

                else:
                    print(f"❓ 未知指令: {command}")

                clear_command()
                print(f"🧹 指令 [{command}] 處理完成，已重置指令檔。")

            time.sleep(30)

        except Exception as e:
            print(f"❌ 發生錯誤: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
