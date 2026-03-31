import os
import requests
import time
import subprocess
from dotenv import load_dotenv

load_dotenv()
TOKEN = "8742999308:AAGnTs71g-2JmKc21Ifw1fS_DtnfOg-PYFo"
OFFSET_FILE = "data/tg_offset.txt"

def main():
    print("🚀 [Jarvis 實時監聽] 啟動成功！我正在聽您的每一句話...")
    offset = 0
    if os.path.exists(OFFSET_FILE):
        with open(OFFSET_FILE, "r") as f: offset = int(f.read().strip())

    while True:
        try:
            # 1. 抓取訊息
            url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
            r = requests.get(url, params={"offset": offset, "timeout": 20}, timeout=25)
            
            if r.status_code == 200:
                data = r.json()
                if data.get("ok") and data.get("result"):
                    for update in data["result"]:
                        msg = update.get("message", {})
                        text = msg.get("text", "")
                        chat_id = msg.get("chat", {}).get("id")
                        offset = update["update_id"] + 1
                        
                        # 紀錄最後讀取位置
                        with open(OFFSET_FILE, "w") as f: f.write(str(offset))
                        
                        print(f"📩 收到指令: [{text}]")
                        
                        # 2. 邏輯處理
                        if text == "/ping":
                            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={"chat_id": chat_id, "text": "🏓 **Jarvis 在線！** 連線非常穩定。"})
                        elif text == "/report":
                            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={"chat_id": chat_id, "text": "📊 收到！正在生成報告..."})
                            subprocess.run(["python3", "scripts/daily_palm_report.py"])
                            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={"chat_id": chat_id, "text": "✅ 報告已產出！"})
            
        except Exception as e:
            print(f"⚠️ 連線小波動: {e}")
            time.sleep(2) # 發生錯誤休息一下再繼續，絕不停止
            
        time.sleep(0.5) # 極速循環

if __name__ == "__main__":
    main()
