import os
import subprocess
import time
import requests
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ICLOUD_BASE = "/Users/bucksteam/Library/Mobile Documents/com~apple~CloudDocs/泰國/工作/甲米油廠/簡報"

def get_updates(offset=None):
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    params = {"timeout": 10, "offset": offset}
    try:
        r = requests.get(url, params=params, timeout=15)
        return r.json()
    except:
        return None

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": chat_id, "text": text})

def main():
    print("🚀 啟動 [高頻率暴力監聽版] Telegram 助手...")
    last_update_id = None
    
    while True:
        # 每次循環都是一次全新的 HTTP 請求，徹底避開長連線阻斷問題
        updates = get_updates(last_update_id)
        
        if updates and updates.get("ok"):
            for update in updates.get("result", []):
                last_update_id = update["update_id"] + 1
                msg = update.get("message", {})
                chat_id = msg.get("chat", {}).get("id")
                text = msg.get("text", "")
                
                if text == "/report":
                    send_message(chat_id, "📊 收到！正在生成報告...")
                    subprocess.run(["python3", "scripts/daily_palm_report.py"])
                    send_message(chat_id, "✅ 報告已產出！")
                elif text == "/ping":
                    send_message(chat_id, "🏓 Pong! 本次連線成功。")
        
        # 休息 2 秒後立即發起下一次全新連線
        time.sleep(2)

if __name__ == "__main__":
    main()
