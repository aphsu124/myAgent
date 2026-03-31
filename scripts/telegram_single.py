import os
import subprocess
import json
import requests
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
# 使用一個本地檔案來記錄已經處理過的最後一個 update_id
OFFSET_FILE = "data/tg_offset.txt"

def get_last_offset():
    if os.path.exists(OFFSET_FILE):
        with open(OFFSET_FILE, "r") as f:
            return int(f.read().strip())
    return None

def set_last_offset(offset):
    with open(OFFSET_FILE, "w") as f:
        f.write(str(offset))

def main():
    offset = get_last_offset()
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    # 設定超時極短，確保程式快速結束
    params = {"timeout": 5, "offset": offset}
    
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
            updates = r.json()
            if updates.get("ok") and updates.get("result"):
                for update in updates["result"]:
                    msg = update.get("message", {})
                    chat_id = msg.get("chat", {}).get("id")
                    text = msg.get("text", "")
                    up_id = update["update_id"]
                    
                    print(f"📩 收到指令: {text}")
                    if text == "/report":
                        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={"chat_id": chat_id, "text": "📊 正在生成報告..."})
                        subprocess.run(["python3", "scripts/daily_palm_report.py"])
                        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={"chat_id": chat_id, "text": "✅ 報告完成！"})
                    elif text == "/ping":
                        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={"chat_id": chat_id, "text": "🏓 Pong! 實時連線測試成功。"})
                    
                    # 更新 offset 避免重複處理
                    set_last_offset(up_id + 1)
    except Exception as e:
        print(f"連線異常: {e}")

if __name__ == "__main__":
    main()
