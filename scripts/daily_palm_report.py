import os
import requests
import datetime
import json
import re
import pandas as pd
import matplotlib.pyplot as plt
import subprocess
import markdown
from google import genai
from dotenv import load_dotenv

# === 載入環境變數 ===
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_USER_ID = os.getenv("LINE_USER_ID")
REPORT_DIR = os.getenv("REPORT_DIR", "docs/reports")
DATA_DIR = os.getenv("DATA_DIR", "data")
PRICE_DATA_FILE = f"{DATA_DIR}/palm_prices.csv"
GITHUB_IO_URL = "https://aphsu124.github.io/myAgent"

# 初始化最新版 Gemini Client
client = genai.Client(api_key=GEMINI_API_KEY, http_options={'api_version': 'v1'})

# 使用兩層大括號來轉義 CSS，避免 .format() 報錯
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>泰國棕櫚油產業簡報 - {date}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #121212; color: #e0e0e0; line-height: 1.6; margin: 0; padding: 20px; }}
        .container {{ max-width: 900px; margin: auto; background: #1e1e1e; padding: 40px; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }}
        h1, h2, h3 {{ color: #4CAF50; border-bottom: 1px solid #333; padding-bottom: 10px; }}
        .price-card {{ display: flex; gap: 20px; margin-bottom: 30px; }}
        .card {{ flex: 1; background: #2d2d2d; padding: 20px; border-radius: 8px; text-align: center; border-left: 5px solid #4CAF50; }}
        .card .label {{ font-size: 0.9em; color: #aaa; margin-bottom: 10px; }}
        .card .value {{ font-size: 2em; font-weight: bold; color: #fff; }}
        img {{ max-width: 100%; border-radius: 8px; margin: 20px 0; border: 1px solid #333; }}
        .footer {{ text-align: center; margin-top: 50px; color: #666; font-size: 0.8em; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 泰國棕櫚油每日營運簡報</h1>
        <p style="color: #666;">執行日期：{date}</p>
        <div class="price-card">
            <div class="card"><div class="label">FFB 收購價</div><div class="value">{ffb}</div></div>
            <div class="card"><div class="label">CPO 銷售價</div><div class="value">{cpo}</div></div>
        </div>
        <div class="content">{content}</div>
        <div class="footer">Powered by Jarvis Palm-Oil AI Analysis Service &copy; 2026</div>
    </div>
</body>
</html>
"""

def get_palm_news():
    url = "https://google.serper.dev/search"
    now = datetime.datetime.now()
    today = now.strftime("%Y-%m-%d")
    queries = [f"Thailand palm oil FFB CPO price Krabi {today}", f"Thailand Ministry of Commerce palm oil policy {now.strftime('%B %Y')}"]
    headers = {'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'}
    res = ""
    for q in queries:
        payload = {"q": q, "gl": "th", "hl": "en", "tbs": "qdr:m"}
        try:
            r = requests.post(url, headers=headers, json=payload)
            if r.status_code == 200:
                for o in r.json().get('organic', []):
                    res += f"\n[{o.get('date', 'N/A')}] {o.get('title')}\n{o.get('snippet')}\n"
        except: pass
    return res

def extract_data_and_report(raw_data):
    now = datetime.datetime.now()
    prompt = f"你是資深分析師。今天是 {now.strftime('%Y-%m-%d')}。請根據數據撰寫簡報。忽略 2024/2025。結尾輸出 DATA_JSON: {{\"ffb\": 6.5, \"cpo\": 40.0}}\n\n數據：{raw_data}"
    content, price_data = "無法生成 AI 報告。", {"ffb": "N/A", "cpo": "N/A"}
    try:
        resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        if resp.text:
            content = resp.text
            m = re.search(r'DATA_JSON: ({.*?})', content)
            if m: price_data = json.loads(m.group(1))
    except Exception as e: print(f"AI 錯誤: {e}")
    return content, price_data

def send_line_push_message(text, image_url=None):
    if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_USER_ID:
        print("⚠️ 找不到 LINE Messaging API 設定。")
        return
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}
    messages = [{"type": "text", "text": text}]
    if image_url:
        messages.append({"type": "image", "originalContentUrl": image_url, "previewImageUrl": image_url})
    payload = {"to": LINE_USER_ID, "messages": messages}
    try:
        r = requests.post(url, headers=headers, json=payload)
        if r.status_code == 200: print("✅ LINE 推播成功！")
        else: print(f"❌ LINE 推播失敗: {r.text}")
    except Exception as e: print(f"LINE 錯誤: {e}")

def main():
    ict_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7)))
    date_str = ict_now.strftime("%Y-%m-%d")
    
    if ict_now.hour < 13 or (ict_now.hour == 13 and ict_now.minute < 30):
        print("⏳ 尚未到泰國 13:30，跳過。"); return
    
    print("🚀 啟動全自動網站生成與 LINE 推播系統...")
    raw_data = get_palm_news()
    content, price_data = extract_data_and_report(raw_data)
    
    # 存數據 & 繪圖
    if not os.path.exists(REPORT_DIR): os.makedirs(REPORT_DIR)
    chart_file = None
    if price_data.get("ffb") != "N/A":
        if not os.path.exists(DATA_DIR): os.makedirs(DATA_DIR)
        df_new = pd.DataFrame({"Date": [date_str], "FFB": [price_data.get("ffb")], "CPO": [price_data.get("cpo")]})
        if os.path.exists(PRICE_DATA_FILE):
            df_old = pd.read_csv(PRICE_DATA_FILE)
            if date_str not in df_old['Date'].values:
                pd.concat([df_old, df_new], ignore_index=True).to_csv(PRICE_DATA_FILE, index=False)
        else: df_new.to_csv(PRICE_DATA_FILE, index=False)
        
        df = pd.read_csv(PRICE_DATA_FILE)
        if len(df) >= 2:
            plt.figure(figsize=(10, 5)); plt.plot(df['Date'], df['FFB'], marker='o', color='green'); plt.plot(df['Date'], df['CPO'], marker='s', color='blue'); plt.grid(True)
            chart_file = f"palm_chart_{date_str}.png"
            plt.savefig(os.path.join(REPORT_DIR, chart_file)); plt.close()

    # 生成網頁
    html_content = markdown.markdown(content)
    final_html = HTML_TEMPLATE.format(date=date_str, ffb=price_data.get('ffb'), cpo=price_data.get('cpo'), content=html_content)
    with open(f"docs/reports/palm_oil_report_{date_str}.html", "w", encoding="utf-8") as f: f.write(final_html)

    # 同步至 GitHub
    try:
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", f"🌐 Website Updated: {date_str}"], check=True)
        subprocess.run(["git", "push", "origin", "main"], check=True)
    except: pass

    # LINE 推播
    chart_url = f"{GITHUB_IO_URL}/reports/{chart_file}" if chart_file else None
    msg = f"📊 泰國棕櫚油簡報 ({date_str})\n\n🔸 FFB: {price_data.get('ffb')}\n🔸 CPO: {price_data.get('cpo')}\n\n立即查看網頁：{GITHUB_IO_URL}/reports/palm_oil_report_{date_str}.html"
    send_line_push_message(msg, chart_url)

if __name__ == "__main__":
    main()
