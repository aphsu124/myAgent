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
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

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

# iCloud 路徑
ICLOUD_BASE = "/Users/bucksteam/Library/Mobile Documents/com~apple~CloudDocs/泰國/工作/甲米油廠/簡報"
ICLOUD_EXCEL = os.path.join(ICLOUD_BASE, "palm_oil_history.xlsx")

# 初始化 Gemini
client = genai.Client(api_key=GEMINI_API_KEY, http_options={'api_version': 'v1'})

def create_pdf_report(filename, title, date, ffb, cpo, content):
    """產出簡易 PDF 報表並存入 iCloud"""
    try:
        c = canvas.Canvas(filename, pagesize=A4)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, 800, title)
        c.setFont("Helvetica", 10)
        c.drawString(50, 780, f"Date: {date}")
        c.drawString(50, 760, f"FFB: {ffb} | CPO: {cpo}")
        
        # 簡單內容寫入 (由於 reportlab 處理中文較複雜，這裡先以英文/數字核心為主，若需完整中文 PDF 需安裝字體)
        c.setFont("Helvetica", 12)
        y = 730
        lines = content.split('\n')
        for line in lines[:30]: # 先截取前30行避免溢出
            if y < 50: break
            c.drawString(50, y, line[:80])
            y -= 15
        c.save()
        return True
    except Exception as e:
        print(f"PDF 產出出錯: {e}")
        return False

def update_icloud_excel(date_str, ffb, cpo):
    """更新 iCloud 中的總表 Excel"""
    try:
        new_data = pd.DataFrame({"Date": [date_str], "FFB": [ffb], "CPO": [cpo]})
        if os.path.exists(ICLOUD_EXCEL):
            df_old = pd.read_excel(ICLOUD_EXCEL)
            if date_str not in df_old['Date'].values:
                df_combined = pd.concat([df_old, new_data], ignore_index=True)
                df_combined.to_excel(ICLOUD_EXCEL, index=False)
        else:
            new_data.to_excel(ICLOUD_EXCEL, index=False)
        return True
    except Exception as e:
        print(f"Excel 更新出錯: {e}")
        return False

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
        prompt = f"你是分析師。今天是 {today_str}。撰寫「晨間新聞快報」。忽略價格數據。數據：{raw_data}"
    else:
        prompt = f"你是分析師。今天是 {today_str}。撰寫「每日完整分析」。含價格。結尾輸出 DATA_JSON: {{\"ffb\": 6.5, \"cpo\": 40.0}}。數據：{raw_data}"
    
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

def main():
    ict_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7)))
    date_today = ict_now.strftime("%Y-%m-%d")
    curr_hm = ict_now.strftime("%H:%M")
    
    mode = None
    if "07:00" <= curr_hm < "13:30":
        mode = "news_only"
        title = "📰 Thailand Palm Oil Morning News"
        file_suffix = "news_0700"
    elif curr_hm >= "13:30":
        mode = "full"
        title = "📊 Thailand Palm Oil Full Report"
        file_suffix = "full_1330"
    else:
        return

    report_name = f"palm_report_{date_today}_{file_suffix}"
    html_path = f"docs/reports/{report_name}.html"
    icloud_pdf_path = os.path.join(ICLOUD_BASE, f"{report_name}.pdf")

    if os.path.exists(html_path): return

    print(f"🚀 開始執行 {mode} 任務...")
    raw_data = get_palm_news()
    content, price_data = extract_data_and_report(raw_data, mode)
    
    ffb = price_data.get("ffb") if price_data else "N/A"
    cpo = price_data.get("cpo") if price_data else "N/A"

    # 1. 更新 iCloud Excel
    if mode == "full" and price_data:
        update_icloud_excel(date_today, ffb, cpo)

    # 2. 產出 iCloud PDF
    create_pdf_report(icloud_pdf_path, title, date_today, ffb, cpo, content)

    # 3. 產出本地 HTML 與同步 GitHub (保持與之前一致)
    html_body = markdown.markdown(content)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(f"<html><body style='background:#121212;color:white;font-family:sans-serif;'><h1>{title}</h1>{html_body}</body></html>")
    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(f"<html><body style='background:#121212;color:white;font-family:sans-serif;'><h1>{title}</h1>{html_body}</body></html>")

    try:
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", f"🌐 {mode} Updated: {date_today}"], check=True)
        subprocess.run(["git", "push", "origin", "main"], check=True)
    except: pass

    # 4. LINE 推播
    msg = f"{title}\n🔸 FFB: {ffb}\n🔸 CPO: {cpo}\n👉 報告已存入 iCloud"
    line_url = f"https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}
    requests.post(line_url, headers=headers, json={"to": LINE_USER_ID, "messages": [{"type": "text", "text": msg}]})

if __name__ == "__main__":
    main()
