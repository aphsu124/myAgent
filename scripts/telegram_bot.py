import os
import sys
import json
import requests
import time
import random
import atexit
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ICLOUD_BRIEFING = "/Users/bucksteam/Library/Mobile Documents/com~apple~CloudDocs/泰國/工作/甲米油廠/簡報"
TASKS_PATH = os.path.expanduser("~/.claude/projects/-Users-bucksteam-myAgent/memory/tasks.md")
AUTODREAM_STATE = os.path.expanduser("~/.claude/autodream/state.json")
AUTODREAM_REPORT = os.path.expanduser("~/.claude/autodream/last_report.md")
OFFSET_FILE = os.path.join(BASE_DIR, "data/tg_offset.txt")
PID_FILE = os.path.join(BASE_DIR, "data/telegram_bot.pid")


def acquire_lock():
    """確保只有一個 instance 在執行，否則立即退出"""
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE) as f:
                old_pid = int(f.read().strip())
            # 確認 PID 是否仍在執行
            os.kill(old_pid, 0)
            print(f"⛔ 已有 instance 在執行 (PID {old_pid})，退出。")
            sys.exit(1)
        except (ProcessLookupError, ValueError):
            pass  # 舊 PID 已不存在，繼續
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))
    atexit.register(lambda: os.path.exists(PID_FILE) and os.remove(PID_FILE))

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

def handle_command(text, chat_id):
    """處理斜線指令，回傳 True 表示已處理"""
    cmd = text.split()[0].lower()

    if cmd == "/ping":
        send_msg(chat_id, "🏓 Pong! 我還活著。")

    elif cmd == "/report":
        send_msg(chat_id, "📊 收到指令，正在產出日報...")
        result = dispatch("run_daily_report", {})
        send_msg(chat_id, str(result))

    elif cmd == "/excel":
        excel_path = os.path.join(ICLOUD_BRIEFING, "palm_oil_history.xlsx")
        if os.path.exists(excel_path):
            send_document(chat_id, excel_path)
        else:
            send_msg(chat_id, "❌ 找不到 Excel 檔案，請確認 iCloud 路徑。")

    elif cmd == "/dream_status":
        try:
            with open(AUTODREAM_STATE, "r") as f:
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
        try:
            requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                data={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"},
                headers={"Connection": "close"}, timeout=15
            )
        except Exception as e:
            print(f"⚠️ 訊息發送失敗: {e}")

    elif cmd == "/dream_tasks":
        try:
            with open(TASKS_PATH, "r", encoding="utf-8") as f:
                content = f.read()
            parts = content.split("---", 2)
            body = parts[2].strip() if len(parts) >= 3 else content
            msg = f"📋 *任務紀錄*\n\n```\n{body[:3000]}\n```"
        except Exception:
            msg = "❌ 無法讀取任務檔案"
        try:
            requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                data={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"},
                headers={"Connection": "close"}, timeout=15
            )
        except Exception as e:
            print(f"⚠️ 訊息發送失敗: {e}")

    elif cmd == "/dream_report":
        try:
            with open(AUTODREAM_REPORT, "r", encoding="utf-8") as f:
                content = f.read()
            msg = f"📄 *最近一次夢境報告*\n\n{content[:3500]}"
        except FileNotFoundError:
            msg = "📄 尚無夢境報告（autoDream 尚未執行過）"
        except Exception:
            msg = "❌ 無法讀取報告檔案"
        try:
            requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                data={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"},
                headers={"Connection": "close"}, timeout=15
            )
        except Exception as e:
            print(f"⚠️ 訊息發送失敗: {e}")

    else:
        cmds = "/ping /report /excel /dream_status /dream_tasks /dream_report"
        send_msg(chat_id, f"❓ 未知指令：{cmd}\n可用指令：{cmds}")

    return True


def handle_document(doc, chat_id):
    """接收 PDF 文件，用 Gemini Vision 辨識內容並回傳分析"""
    mime_type = doc.get("mime_type", "")
    file_name = doc.get("file_name", "document")
    if mime_type != "application/pdf":
        send_msg(chat_id, f"⚠️ 目前只支援 PDF 格式（收到：{mime_type}）")
        return

    send_msg(chat_id, f"📄 收到 {file_name}，辨識中...")
    print(f"📩 收到文件：{file_name} ({mime_type})")

    try:
        import fitz
        import tempfile

        # 下載 PDF
        file_id = doc["file_id"]
        r = requests.get(f"https://api.telegram.org/bot{TOKEN}/getFile",
                         params={"file_id": file_id}, timeout=15)
        file_path = r.json()["result"]["file_path"]
        pdf_bytes = requests.get(
            f"https://api.telegram.org/file/bot{TOKEN}/{file_path}", timeout=60
        ).content

        # PDF → 圖片（最多前 5 頁）
        pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        image_parts = []
        for i in range(min(5, len(pdf_doc))):
            page = pdf_doc[i]
            pix = page.get_pixmap(dpi=150)
            image_parts.append(
                types.Part.from_bytes(data=pix.tobytes("png"), mime_type="image/png")
            )
        pdf_doc.close()

        prompt = (
            "這是一份掃描文件的圖片。請用繁體中文完成以下三項：\n"
            "1. 【文件種類】：這是什麼類型的文件？用途是什麼？\n"
            "2. 【內容翻譯】：將文件主要內容翻譯成繁體中文（若已是中文則整理條列）\n"
            "3. 【內容摘要】：用 3-5 點條列出關鍵重點\n\n"
            "請依序回答，結構清晰。"
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt] + image_parts,
        )
        answer = response.text
        # Telegram 單則訊息上限 4096 字
        for i in range(0, len(answer), 4000):
            send_msg(chat_id, answer[i:i+4000])

    except Exception as e:
        print(f"❌ handle_document 失敗: {e}")
        send_msg(chat_id, f"⚠️ 文件辨識失敗：{str(e)[:150]}")


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
                'convert_to_pdf':       'Excel → PDF 轉換',
                'run_daily_report':     '產出日報',
                'list_drive_files':     '列出 Drive 檔案',
                'capture_camera':       '拍攝截圖',
                'get_status':           '查詢系統狀態',
                'get_token_usage':      '查詢 Token 用量',
                'search_breaking_news': '即時新聞掃描',
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
    acquire_lock()
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
                        chat_id = msg.get("chat", {}).get("id")
                        if not chat_id:
                            continue

                        # ── 身份驗證：只接受授權用戶 ──
                        if TELEGRAM_ALLOWED_CHAT_ID and chat_id != TELEGRAM_ALLOWED_CHAT_ID:
                            print(f"🚫 拒絕未授權訊息 (chat_id={chat_id})")
                            continue

                        # ── 文件訊息 ──
                        if msg.get("document"):
                            handle_document(msg["document"], chat_id)
                            continue

                        # ── 文字訊息 ──
                        text = msg.get("text", "").strip()
                        if not text:
                            # 判斷是哪種不支援的類型
                            if msg.get("photo"):
                                send_msg(chat_id, "⚠️ 目前不支援圖片，請傳 PDF 文件。")
                            elif msg.get("voice") or msg.get("audio"):
                                send_msg(chat_id, "⚠️ 目前不支援語音/音訊。")
                            elif msg.get("sticker"):
                                send_msg(chat_id, "⚠️ 收到貼圖，但我不懂這個語言 😅")
                            elif msg:
                                send_msg(chat_id, "⚠️ 收到未支援的訊息格式，請傳文字或 PDF 文件。")
                            continue

                        print(f"📩 收到：{text}")
                        if text.startswith("/"):
                            handle_command(text, chat_id)
                            continue
                        handle_message(text, chat_id)

            time.sleep(1)

        except Exception as e:
            print(f"⚠️ 連線受阻，退避重試... ({retry_delay}s): {e}")
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 60)

if __name__ == "__main__":
    main()
