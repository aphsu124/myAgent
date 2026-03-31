import os
import subprocess
import datetime
from flask import Flask, request
from dotenv import load_dotenv
import requests
import json

load_dotenv()
ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

app = Flask(__name__)

@app.route("/", methods=['POST', 'GET'])
@app.route("/callback", methods=['POST', 'GET'])
def webhook():
    if request.method == 'GET': return "Jarvis Server is Online!", 200
    
    body = request.get_data(as_text=True)
    try:
        data = json.loads(body)
        if not data.get("events"): return "OK", 200
        for event in data.get("events", []):
            token = event.get("replyToken")
            msg = event.get("message", {}).get("text", "").strip()
            if token:
                if msg == "日報":
                    reply = "🚀 收到！正在為您產出今日最新報告..."
                    subprocess.run(["python3", "scripts/daily_palm_report.py"])
                    reply += "\n✅ 報告已更新！"
                else:
                    reply = f"Jarvis 已連線！指令：{msg}"
                requests.post("https://api.line.me/v2/bot/message/reply", headers={"Content-Type": "application/json", "Authorization": f"Bearer {ACCESS_TOKEN}"}, json={"replyToken": token, "messages": [{"type": "text", "text": reply}]})
    except: pass
    return "OK", 200

if __name__ == "__main__":
    # 強制監聽 0.0.0.0 確保 Ngrok 能轉發進來
    app.run(port=8888, host='0.0.0.0')
