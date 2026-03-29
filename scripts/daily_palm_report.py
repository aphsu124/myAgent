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

# 初始化 Gemini Client
client = genai.Client(api_key=GEMINI_API_KEY, http_options={'api_version': 'v1'})

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - {date}</title>
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
        .nav-links {{ text-align: center; margin-bottom: 20px; }}
        .nav-links a {{ color: #4CAF50; margin: 0 10px; text-decoration: none; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="nav-links">
            <a href="{root_url}/index.html">🏠 回到今日最新</a>
        </div>
        <h1>{title}</h1>
        <p style="color: #666;">執行日期：{date}</p>
        {price_html}
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
    queries = [f"Thailand palm oil FFB CPO news Krabi {today}", f"Thailand Ministry of Commerce palm oil policy {now.strftime('%B %Y')}"]
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

def extract_data_and_report(raw_data, mode="full"):
    now = datetime.datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    if mode == "news_only":
        prompt = f"你是資深泰國棕櫚油分析師。今天是 {today_str}。撰寫「晨間新聞快報」。忽略價格數據。數據：{raw_data}"
    else:
        prompt = f"你是資深泰國棕櫚油分析師。今天是 {today_str}。撰寫「每日完整分析」。含價格與建議。結尾輸出 DATA_JSON: {{\"ffb\": 6.5, \"cpo\": 40.0}}。數據：{raw_data}"
    
    content, price_data = "無法生成 AI 報告。", None
    try:
        resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        if resp.text:
            content = resp.text
            if mode == "full":
                m = re.search(r'DATA_JSON: ({.*?})', content)
                if m: price_data = json.loads(m.group(1))
    except Exception as e: print(f"AI 出錯: {e}")
    return content, price_data

def send_line_push_message(text, image_url=None):
    if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_USER_ID: return
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}
    messages = [{"type": "text", "text": text}]
    if image_url:
        messages.append({"type": "image", "originalContentUrl": image_url, "previewImageUrl": image_url})
    requests.post(url, headers=headers, json={"to": LINE_USER_ID, "messages": messages})

def main():
    ict_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7)))
    date_today = ict_now.strftime("%Y-%m-%d")
    curr_hm = ict_now.strftime("%H:%M")
    
    mode = None
    if "07:00" <= curr_hm < "13:30":
        mode = "news_only"
        title = "📰 泰國棕櫚油晨間新聞快報"
        file_suffix = "news_0700"
    elif curr_hm >= "13:30":
        mode = "full"
        title = "📊 泰國棕櫚油每日營運全報告"
        file_suffix = "full_1330"
    else:
        print(f"⏳ 尚未到 07:00 (目前: {curr_hm})，略過。"); return

    report_filename = f"palm_oil_report_{date_today}_{file_suffix}.html"
    report_path = os.path.join(REPORT_DIR, report_filename)

    if os.path.exists(report_path):
        print(f"✅ 今日 {mode} 報告已存在，跳過。"); return

    print(f"🚀 開始執行 {mode} 分析任務...")
    raw_data = get_palm_news()
    content, price_data = extract_data_and_report(raw_data, mode)
    
    price_html = ""
    chart_file = None
    if mode == "full" and price_data:
        # 數據存檔 & 繪圖 (保持與之前一致)
        df_new = pd.DataFrame({"Date": [date_today], "FFB": [price_data.get("ffb")], "CPO": [price_data.get("cpo")]})
        if not os.path.exists(DATA_DIR): os.makedirs(DATA_DIR)
        if os.path.exists(PRICE_DATA_FILE):
            df_old = pd.read_csv(PRICE_DATA_FILE)
            if date_today not in df_old['Date'].values:
                pd.concat([df_old, df_new], ignore_index=True).to_csv(PRICE_DATA_FILE, index=False)
        else: df_new.to_csv(PRICE_DATA_FILE, index=False)
        df = pd.read_csv(PRICE_DATA_FILE)
        if len(df) >= 2:
            plt.figure(figsize=(10, 5)); plt.plot(df['Date'], df['FFB'], marker='o', color='green'); plt.plot(df['Date'], df['CPO'], marker='s', color='blue'); plt.grid(True)
            chart_file = f"palm_chart_{date_today}.png"
            plt.savefig(os.path.join(REPORT_DIR, chart_file)); plt.close()
        
        price_html = f'<div class="price-card"><div class="card"><div class="label">FFB</div><div class="value">{price_data.get("ffb")}</div></div><div class="card"><div class="label">CPO</div><div class="value">{price_data.get("cpo")}</div></div></div>'

    # 生成 HTML 內容
    html_body = markdown.markdown(content)
    if chart_file:
        html_body += f'<br><h2>📈 價格趨勢圖</h2><img src="{chart_file}" alt="Trend">'
    
    # 產出報告檔案
    final_html = HTML_TEMPLATE.format(title=title, date=date_today, price_html=price_html, content=html_body, root_url=GITHUB_IO_URL)
    if not os.path.exists(REPORT_DIR): os.makedirs(REPORT_DIR)
    with open(report_path, "w", encoding="utf-8") as f: f.write(final_html)
    
    # [核心修復] 將 index.html 作為最新報告的內容拷貝，而非跳轉
    with open("docs/index.html", "w", encoding="utf-8") as f: f.write(final_html)

    # 同步 GitHub
    try:
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", f"🌐 {mode} Updated: {date_today}"], check=True)
        subprocess.run(["git", "push", "origin", "main"], check=True)
        print("✅ 網頁已同步至 GitHub。")
    except: pass

    # LINE 推播 (使用絕對路徑報告網址)
    msg = f"{title} ({date_today})\n"
    if mode == "full" and price_data:
        msg += f"\n🔸 FFB: {price_data.get('ffb')}\n🔸 CPO: {price_data.get('cpo')}\n"
    msg += f"\n👉 查看完整網頁：{GITHUB_IO_URL}/index.html"
    
    chart_url = f"{GITHUB_IO_URL}/reports/{chart_file}" if chart_file else None
    send_line_push_message(msg, chart_url)

if __name__ == "__main__":
    main()
