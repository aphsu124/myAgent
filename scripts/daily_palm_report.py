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
LINE_NOTIFY_TOKEN = os.getenv("LINE_NOTIFY_TOKEN")
REPORT_DIR = os.getenv("REPORT_DIR", "docs/reports")
DATA_DIR = os.getenv("DATA_DIR", "data")
PRICE_DATA_FILE = f"{DATA_DIR}/palm_prices.csv"

# 初始化最新版 Gemini Client
client = genai.Client(api_key=GEMINI_API_KEY, http_options={'api_version': 'v1'})

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
        a {{ color: #81c784; text-decoration: none; }}
        .price-card {{ display: flex; gap: 20px; margin-bottom: 30px; }}
        .card {{ flex: 1; background: #2d2d2d; padding: 20px; border-radius: 8px; text-align: center; border-left: 5px solid #4CAF50; }}
        .card .label {{ font-size: 0.9em; color: #aaa; margin-bottom: 10px; }}
        .card .value {{ font-size: 2em; font-weight: bold; color: #fff; }}
        img {{ max-width: 100%; border-radius: 8px; margin: 20px 0; border: 1px solid #333; }}
        .footer {{ text-align: center; margin-top: 50px; color: #666; font-size: 0.8em; }}
        pre {{ background: #000; padding: 15px; border-radius: 5px; overflow-x: auto; font-size: 0.9em; }}
        code {{ color: #f4b400; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 泰國棕櫚油每日營運簡報</h1>
        <p style="color: #666;">執行日期：{date}</p>
        
        <div class="price-card">
            <div class="card">
                <div class="label">FFB 收購價 (預估)</div>
                <div class="value">{ffb} <small style="font-size: 0.5em;">Baht/kg</small></div>
            </div>
            <div class="card">
                <div class="label">CPO 銷售價 (預估)</div>
                <div class="value">{cpo} <small style="font-size: 0.5em;">Baht/kg</small></div>
            </div>
        </div>

        <div class="content">
            {content}
        </div>

        <div class="footer">
            Powered by Jarvis Palm-Oil AI Analysis Service &copy; 2026
        </div>
    </div>
</body>
</html>
"""

def get_palm_news():
    url = "https://google.serper.dev/search"
    now = datetime.datetime.now()
    curr_date = now.strftime("%Y-%m-%d")
    queries = [f"Thailand palm oil FFB CPO price Krabi {curr_date}", f"Thailand Ministry of Commerce palm oil policy {now.strftime('%B %Y')}", f"Thailand crude palm oil export news {curr_date} -2024 -2025"]
    headers = {'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'}
    all_results = f"--- 基準日期: {curr_date} ---\n"
    for query in queries:
        payload = {"q": query, "gl": "th", "hl": "en", "tbs": "qdr:m"}
        try:
            resp = requests.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                for o in resp.json().get('organic', []):
                    all_results += f"\n[{o.get('date', 'N/A')}] {o.get('title')}\n{o.get('snippet')}\n"
        except: pass
    return all_results

def extract_data_and_report(raw_data):
    now = datetime.datetime.now()
    prompt = f"你是資深泰國棕櫚油產業分析師。今天是 {now.strftime('%Y-%m-%d')}。請根據數據撰寫簡報。忽略 2024/2025 數據。最後輸出 DATA_JSON: {{\"ffb\": 6.5, \"cpo\": 40.0}}\n\n數據：{raw_data}"
    content = "無法生成 AI 報告。"
    price_data = {"ffb": "N/A", "cpo": "N/A"}
    try:
        resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        if resp.text:
            content = resp.text
            match = re.search(r'DATA_JSON: ({.*?})', content)
            if match: price_data = json.loads(match.group(1))
    except Exception as e: print(f"AI 出錯: {e}")
    return content, price_data

def update_web_index(date_str, ffb, cpo):
    """更新 GitHub Pages 首頁 (docs/index.html)"""
    index_path = "docs/index.html"
    report_link = f"reports/palm_oil_report_{date_str}.html"
    
    # 讀取現有報告清單（如果存在）
    items = []
    if os.path.exists(index_path):
        # 這裡可以加入讀取舊列表的邏輯，為求簡單，我們直接用最新資料覆蓋首頁，或保留連結
        pass

    # 簡易首頁模板
    index_html = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>棕櫚油產業門戶網</title>
    <style>
        body {{ font-family: sans-serif; background: #121212; color: #fff; text-align: center; padding: 50px; }}
        .box {{ max-width: 600px; margin: auto; background: #1e1e1e; padding: 30px; border-radius: 15px; border-top: 5px solid #4CAF50; }}
        h1 {{ color: #4CAF50; }}
        .btn {{ display: block; background: #4CAF50; color: #white; padding: 15px; margin-top: 20px; border-radius: 5px; text-decoration: none; font-weight: bold; }}
        .history {{ margin-top: 30px; text-align: left; font-size: 0.9em; color: #888; }}
    </style>
</head>
<body>
    <div class="box">
        <h1>🌴 棕櫚油數據中心</h1>
        <p>今日更新 ({date_str})</p>
        <div style="font-size: 1.2em; margin: 20px 0;">
            FFB: {ffb} | CPO: {cpo}
        </div>
        <a href="{report_link}" class="btn">閱讀今日完整分析報告</a>
        
        <div class="history">
            <h3>歷史報告：</h3>
            <ul id="report-list">
                <!-- 這裡可以手動累積或自動讀取目錄 -->
                <li><a href="{report_link}" style="color: #4CAF50;">{date_str} - 今日報告</a></li>
            </ul>
        </div>
    </div>
</body>
</html>
"""
    with open(index_path, "w", encoding="utf-8") as f: f.write(index_html)

def main():
    ict_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7)))
    date_str = ict_now.strftime("%Y-%m-%d")
    
    if ict_now.hour < 13 or (ict_now.hour == 13 and ict_now.minute < 30):
        print("⏳ 尚未到泰國 13:30，略過。"); return

    print("🚀 啟動全自動網站生成系統...")
    raw_data = get_palm_news()
    content, price_data = extract_data_and_report(raw_data)
    
    # 1. 處理數據與繪圖
    if not os.path.exists(REPORT_DIR): os.makedirs(REPORT_DIR)
    chart_file = None
    if price_data.get("ffb") != "N/A":
        # 存入 CSV
        df_new = pd.DataFrame({"Date": [date_str], "FFB": [price_data.get("ffb")], "CPO": [price_data.get("cpo")]})
        if os.path.exists(PRICE_DATA_FILE):
            df_old = pd.read_csv(PRICE_DATA_FILE)
            if date_str not in df_old['Date'].values:
                pd.concat([df_old, df_new], ignore_index=True).to_csv(PRICE_DATA_FILE, index=False)
        else: df_new.to_csv(PRICE_DATA_FILE, index=False)
        
        # 繪圖
        df = pd.read_csv(PRICE_DATA_FILE)
        if len(df) >= 2:
            plt.figure(figsize=(10, 5)); plt.plot(df['Date'], df['FFB'], marker='o', label='FFB', color='green'); plt.plot(df['Date'], df['CPO'], marker='s', label='CPO', color='blue'); plt.legend(); plt.grid(True)
            chart_file = f"palm_chart_{date_str}.png"
            plt.savefig(os.path.join(REPORT_DIR, chart_file)); plt.close()

    # 2. 生成 HTML 報告
    html_content = markdown.markdown(content)
    if chart_file:
        html_content += f'<br><h2>📈 價格趨勢圖</h2><img src="{chart_file}" alt="Trend">'
    
    final_html = HTML_TEMPLATE.format(
        date=date_str, 
        ffb=price_data.get('ffb'), 
        cpo=price_data.get('cpo'), 
        content=html_content
    )
    
    html_filename = f"docs/reports/palm_oil_report_{date_str}.html"
    with open(html_filename, "w", encoding="utf-8") as f: f.write(final_html)
    
    # 3. 更新首頁
    update_web_index(date_str, price_data.get('ffb'), price_data.get('cpo'))

    # 4. LINE 通知 (嘗試發送，若解析失敗會跳過)
    try:
        msg = f"\n📊 簡報已更新至網頁！\n🔸 FFB: {price_data.get('ffb')}\n🔸 CPO: {price_data.get('cpo')}\n\n立即查看：https://aphsu124.github.io/myAgent/"
        requests.post("https://notify-api.line.me/api/notify", headers={"Authorization": f"Bearer {LINE_NOTIFY_TOKEN}"}, data={"message": msg})
    except: pass

    # 5. 同步至 GitHub
    try:
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", f"🌐 Website Updated: {date_str}"], check=True)
        subprocess.run(["git", "push", "origin", "main"], check=True)
        print("✅ 網頁已發布至 GitHub Pages！")
    except Exception as e: print(f"❌ Git 同步失敗: {e}")

if __name__ == "__main__":
    main()
