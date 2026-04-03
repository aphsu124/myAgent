import os
import requests
import time
import random
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OFFSET_FILE = os.path.join(BASE_DIR, "data/tg_offset.txt")

from modules.config import TELEGRAM_ALLOWED_CHAT_ID, GEMINI_API_KEY
from google import genai
from google.genai import types
from modules.jarvis_tools import TOOL_DECLARATIONS, SYSTEM_INSTRUCTION, dispatch

client = genai.Client(api_key=GEMINI_API_KEY, http_options={'api_version': 'v1beta'})

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
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
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={"chat_id": chat_id, "text": text},
            headers={"Connection": "close"},
            timeout=15
        )
    except Exception as e:
        print(f"⚠️ 訊息發送失敗: {e}")

def send_document(chat_id, file_path):
    try:
        with open(file_path, 'rb') as f:
            requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendDocument",
                data={"chat_id": chat_id},
                files={"document": f},
                timeout=60
            )
    except Exception as e:
        print(f"⚠️ 檔案發送失敗: {e}")

def handle_message(text, chat_id):
    """將訊息送給 Gemini Function Calling，執行對應工具或直接回答"""
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=text,
            config=types.GenerateContentConfig(
                tools=[TOOL_DECLARATIONS],
                system_instruction=SYSTEM_INSTRUCTION
            )
        )

        # 遍歷所有 parts，找到 function_call（跳過 thought_signature 等非動作 parts）
        fc_part = None
        for p in response.candidates[0].content.parts:
            if hasattr(p, 'function_call') and p.function_call:
                fc_part = p
                break

        if fc_part:
            fc = fc_part.function_call
            tool_names_zh = {
                'convert_to_pdf':   'Excel → PDF 轉換',
                'run_daily_report': '產出日報',
                'list_drive_files': '列出 Drive 檔案',
                'capture_camera':   '拍攝截圖',
                'get_status':       '查詢系統狀態',
                'get_token_usage':  '查詢 Token 用量',
            }
            send_msg(chat_id, f"⚙️ 執行中：{tool_names_zh.get(fc.name, fc.name)}...")
            print(f"📩 Function Call: {fc.name}({dict(fc.args)})")

            result = dispatch(fc.name, dict(fc.args))

            # 若結果是存在的本地檔案路徑，直接傳檔案
            if isinstance(result, str) and os.path.exists(result):
                send_document(chat_id, result)
                try: os.remove(result)
                except: pass
            else:
                send_msg(chat_id, str(result))
        else:
            from modules.llm_router import ask as router_ask
            answer, task, model_used = router_ask(text)
            print(f"🧭 Router: [{task}] → {model_used}")
            send_msg(chat_id, answer)

    except Exception as e:
        print(f"❌ handle_message 失敗: {e}")
        send_msg(chat_id, f"⚠️ Jarvis 發生錯誤：{str(e)[:100]}")

def main():
    print("🕵️ Jarvis 特種連線監聽器已啟動...")
    print(f"🔐 授權 chat_id：{TELEGRAM_ALLOWED_CHAT_ID}")
    offset = get_offset()
    retry_delay = 2

    while True:
        try:
            headers = {"User-Agent": random.choice(USER_AGENTS), "Connection": "close"}
            r = requests.get(
                f"https://api.telegram.org/bot{TOKEN}/getUpdates",
                params={"offset": offset, "timeout": 10},
                timeout=15,
                headers=headers
            )

            if r.status_code == 200:
                retry_delay = 2
                data = r.json()
                if data.get("ok") and data.get("result"):
                    for update in data["result"]:
                        offset = update["update_id"] + 1
                        save_offset(offset)

                        msg = update.get("message", {})
                        text = msg.get("text", "").strip()
                        chat_id = msg.get("chat", {}).get("id")

                        if not text or not chat_id:
                            continue

                        # ── 身份驗證：只接受授權用戶 ──
                        if TELEGRAM_ALLOWED_CHAT_ID and chat_id != TELEGRAM_ALLOWED_CHAT_ID:
                            print(f"🚫 拒絕未授權訊息 (chat_id={chat_id})")
                            continue

                        print(f"📩 收到：{text}")
                        handle_message(text, chat_id)

            time.sleep(1)

        except Exception as e:
            print(f"⚠️ 連線受阻，退避重試... ({retry_delay}s): {e}")
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 60)

if __name__ == "__main__":
    main()
