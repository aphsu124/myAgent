import os
import requests
import time
import subprocess
import random
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OFFSET_FILE = "data/tg_offset.txt"

# 模擬瀏覽器標頭，降低被過濾風險
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

def get_offset():
    if os.path.exists(OFFSET_FILE):
        try:
            with open(OFFSET_FILE, "r") as f: return int(f.read().strip())
        except: return 0
    return 0

def save_offset(offset):
    with open(OFFSET_FILE, "w") as f: f.write(str(offset))

def send_msg(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": chat_id, "text": text}, headers={"Connection": "close"})

def main():
    print("🕵️ Jarvis 特種連線監聽器已啟動...")
    offset = get_offset()
    retry_delay = 2 # 初始退避時間
    
    while True:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
            headers = {
                "User-Agent": random.choice(USER_AGENTS),
                "Connection": "close"
            }
            
            # 使用較短的連線時間，並隱藏特徵
            r = requests.get(url, params={"offset": offset, "timeout": 10}, timeout=15, headers=headers)
            
            if r.status_code == 200:
                retry_delay = 2 # 成功連線，重置退避時間
                data = r.json()
                if data.get("ok") and data.get("result"):
                    for update in data["result"]:
                        offset = update["update_id"] + 1
                        save_offset(offset)
                        
                        msg = update.get("message", {})
                        text = msg.get("text", "").strip()
                        chat_id = msg.get("chat", {}).get("id")
                        
                        print(f"📩 成功接收指令: [{text}]")
                        if text == "/ping":
                            send_msg(chat_id, "🏓 **突圍測試成功！** Jarvis 正在待命。")
                        elif text == "/report":
                            send_msg(chat_id, "📊 正在背景執行日報分析...")
                            subprocess.run(["python3", "scripts/daily_palm_report.py"])
                            send_msg(chat_id, "✅ 日報已發送至網頁與 iCloud。")
            
            # 正常間隔
            time.sleep(1)
            
        except Exception as e:
            print(f"⚠️ 連線受阻，實施退避重試... ({retry_delay}s)")
            time.sleep(retry_delay)
            # 指數退避，最高休息 60 秒
            retry_delay = min(retry_delay * 2, 60)

if __name__ == "__main__":
    main()
