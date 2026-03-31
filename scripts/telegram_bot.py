import os
import requests
import time
import subprocess
from dotenv import load_dotenv

# 載入配置
load_dotenv()
TOKEN = "8347859510:AAELsV2182Ma_qAuuTKDKdE4PrWNCpik2l0"
OFFSET_FILE = "data/tg_offset.txt"

def get_offset():
    if os.path.exists(OFFSET_FILE):
        try:
            with open(OFFSET_FILE, "r") as f: return int(f.read().strip())
        except: return 0
    return 0

def save_offset(offset):
    with open(OFFSET_FILE, "w") as f: f.write(str(offset))

def main():
    print("🕵️ Jarvis 隱形監聽器已啟動...")
    print("💡 採用 [快閃連線策略] 以避開防火牆截斷。")
    
    offset = get_offset()
    
    while True:
        try:
            # 1. 建立一個極短的連線 (timeout 非常短，且強制不維持連線)
            url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
            # 關鍵：不使用 long polling，而是直接抓取即時狀態
            r = requests.get(
                url, 
                params={"offset": offset, "limit": 10}, 
                timeout=5,
                headers={'Connection': 'close'} # 強制伺服器在傳完後立刻關閉連線
            )
            
            if r.status_code == 200:
                data = r.json()
                if data.get("ok") and data.get("result"):
                    for update in data["result"]:
                        offset = update["update_id"] + 1
                        save_offset(offset)
                        
                        msg = update.get("message", {})
                        text = msg.get("text", "").strip()
                        chat_id = msg.get("chat", {}).get("id")
                        
                        print(f"📩 收到指令: [{text}]")
                        
                        if text == "/ping":
                            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={"chat_id": chat_id, "text": "✅ **Jarvis 在線！** 快閃連線成功。"})
                        elif text == "/report":
                            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={"chat_id": chat_id, "text": "📊 正在為您生成報告..."})
                            subprocess.run(["python3", "scripts/daily_palm_report.py"])
                            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={"chat_id": chat_id, "text": "✅ **報告完成！**"})
            
            # 2. 正常心跳日誌 (確認程式沒死)
            # print(".", end="", flush=True) 
            
        except Exception as e:
            print(f"\n⚠️ 重新撥號中... ({e})")
            
        # 3. 每 2 秒發起一次全新的請求
        time.sleep(2)

if __name__ == "__main__":
    main()
