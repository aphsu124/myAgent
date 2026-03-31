import os
import time
import subprocess
import datetime
import requests
from dotenv import load_dotenv

load_dotenv()
CMD_FILE = "/Users/bucksteam/Library/Mobile Documents/com~apple~CloudDocs/泰國/工作/甲米油廠/指令/CMD.txt"
LINE_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
USER_ID = os.getenv("LINE_USER_ID")

def send_line_notification(text):
    if not LINE_TOKEN or not USER_ID: return
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_TOKEN}"}
    requests.post(url, headers=headers, json={"to": USER_ID, "messages": [{"type": "text", "text": text}]})

def main():
    print(f"🕵️ Jarvis 指令監聽器已啟動... (監控檔案: {os.path.basename(CMD_FILE)})")
    
    # 如果檔案不存在，先建立一個空白的
    if not os.path.exists(CMD_FILE):
        with open(CMD_FILE, "w", encoding="utf-8") as f: f.write("")

    while True:
        try:
            # 讀取指令
            if os.path.exists(CMD_FILE) and os.path.getsize(CMD_FILE) > 0:
                with open(CMD_FILE, "r", encoding="utf-8") as f:
                    command = f.read().strip()
                
                if command:
                    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                    print(f"📩 [{timestamp}] 偵測到手機指令: {command}")
                    
                    if command == "日報":
                        send_line_notification("🚀 收到手機指令：正在產出日報...")
                        subprocess.run(["python3", "scripts/daily_palm_report.py"])
                        send_line_notification("✅ 日報產出完畢！")
                    
                    elif command == "試算":
                        send_line_notification("📊 收到手機指令：正在刷新 Excel...")
                        path = "/Users/bucksteam/Library/Mobile Documents/com~apple~CloudDocs/泰國/工作/甲米油廠/簡報/palm_oil_history.xlsx"
                        subprocess.run(["python3", "-c", f"from scripts.daily_palm_report import style_excel; style_excel('{path}')"])
                        send_line_notification("✅ Excel 樣式已刷新。")
                    
                    else:
                        print(f"❓ 未知指令: {command}")
                    
                    # 執行完畢，清空檔案，等待下一個指令
                    with open(CMD_FILE, "w", encoding="utf-8") as f:
                        f.write("")
                    print(f"🧹 指令 [{command}] 處理完成，已重置 CMD.txt。")
            
            # 每 30 秒檢查一次 (平衡即時性與省電)
            time.sleep(30)
            
        except Exception as e:
            print(f"❌ 發生錯誤: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
