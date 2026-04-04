import os
import requests
import json
import subprocess
import time
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OFFSET_FILE = "data/tg_offset.txt"
ICLOUD_BASE = "/Users/bucksteam/Library/Mobile Documents/com~apple~CloudDocs/泰國/工作/甲米油廠/簡報"

def get_offset():
    if os.path.exists(OFFSET_FILE):
        with open(OFFSET_FILE, "r") as f: return int(f.read().strip())
    return 0

def save_offset(offset):
    with open(OFFSET_FILE, "w") as f: f.write(str(offset))

def main():
    offset = get_offset()
    # 每次連線極短，抓完就撤
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    try:
        r = requests.get(url, params={"offset": offset, "timeout": 5}, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("ok") and data.get("result"):
                for update in data["result"]:
                    u_id = update["update_id"]
                    msg = update.get("message", {})
                    chat_id = msg.get("chat", {}).get("id")
                    text = msg.get("text", "").strip()
                    
                    if text == "/ping":
                        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={"chat_id": chat_id, "text": "🏓 **Pong!** 我還活著。"})
                    elif text == "/report":
                        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={"chat_id": chat_id, "text": "📊 **收到指令**，正在生成日報..."})
                        subprocess.run(["python3", "scripts/daily_palm_report.py"])
                        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={"chat_id": chat_id, "text": "✅ **日報更新成功！**"})
                    elif text == "/excel":
                        excel_path = os.path.join(ICLOUD_BASE, "palm_oil_history.xlsx")
                        with open(excel_path, "rb") as f:
                            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendDocument", data={"chat_id": chat_id}, files={"document": f})

                    elif text == "/dream_status":
                        state_path = os.path.expanduser("~/.claude/autodream/state.json")
                        try:
                            with open(state_path, "r") as f:
                                s = json.load(f)
                            msg = (
                                f"🌙 *autoDream 狀態*\n\n"
                                f"夢境次數：{s.get('dream_count', 0)} 次\n"
                                f"上次整合：{s.get('last_dream_time', 'N/A')[:10]}\n"
                                f"累積對話：{s.get('conversation_count', 0)} 次\n"
                                f"下次觸發需：{max(0, 5 - s.get('conversation_count', 0))} 次對話"
                            )
                        except Exception:
                            msg = "❌ 無法讀取狀態檔案"
                        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                            data={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"})

                    elif text == "/dream_tasks":
                        tasks_path = os.path.expanduser("~/.claude/projects/-Users-bucksteam/memory/tasks.md")
                        try:
                            with open(tasks_path, "r") as f:
                                content = f.read()
                            # 只取 frontmatter 之後的內容
                            lines = content.split("---", 2)
                            body = lines[2].strip() if len(lines) >= 3 else content
                            msg = f"📋 *任務紀錄*\n\n```\n{body[:3000]}\n```"
                        except Exception:
                            msg = "❌ 無法讀取任務檔案"
                        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                            data={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"})

                    elif text == "/dream_report":
                        report_path = os.path.expanduser("~/.claude/autodream/last_report.md")
                        try:
                            with open(report_path, "r") as f:
                                content = f.read()
                            msg = f"📄 *最近一次夢境報告*\n\n{content[:3500]}"
                        except FileNotFoundError:
                            msg = "📄 尚無夢境報告（autoDream 尚未執行過）"
                        except Exception:
                            msg = "❌ 無法讀取報告檔案"
                        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                            data={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"})

                    save_offset(u_id + 1)
    except Exception as e:
        pass # 靜默處理，交給外部 Daemon 重試

if __name__ == "__main__":
    main()
