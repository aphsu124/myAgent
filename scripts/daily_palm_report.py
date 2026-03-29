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

# 嘗試註冊 macOS 中文字型以解決 PDF 亂碼
CHINESE_FONT_PATH = "/System/Library/Fonts/STHeiti Light.ttc" # macOS 預設黑體
try:
    pdfmetrics.registerFont(TTFont('ChineseFont', CHINESE_FONT_PATH))
    HAS_CHINESE_FONT = True
except:
    HAS_CHINESE_FONT = False

# 初始化 Gemini
client = genai.Client(api_key=GEMINI_API_KEY, http_options={'api_version': 'v1'})

def create_pdf_report(filename, title, date, ffb, cpo, content):
    """產出支持中文的 PDF 報表並存入 iCloud"""
    try:
        c = canvas.Canvas(filename, pagesize=A4)
        font_name = 'ChineseFont' if HAS_CHINESE_FONT else 'Helvetica'
        
        # 標題
        c.setFont(font_name, 18)
        c.drawString(50, 800, title)
        
        # 基本資訊
        c.setFont(font_name, 12)
        c.drawString(50, 775, f"日期: {date}")
        c.drawString(50, 755, f"FFB 價格: {ffb} | CPO 價格: {cpo}")
        c.line(50, 745, 550, 745)
        
        # 內文處理 (簡單自動換行邏輯)
        c.setFont(font_name, 10)
        y = 720
        clean_content = content.replace('#', '').replace('*', '') # 移除 Markdown 符號
        for line in clean_content.split('\n'):
            if not line.strip(): continue
            # 簡單的分行處理
            text = line.strip()
            while len(text) > 0:
                if y < 50: # 分頁處理
                    c.showPage()
                    c.setFont(font_name, 10)
                    y = 800
                c.drawString(50, y, text[:40])
                text = text[40:]
                y -= 15
        c.save()
        return True
    except Exception as e:
        print(f"PDF 產出出錯: {e}")
        return False

def update_icloud_excel(date_str, ffb, cpo):
    """更新 iCloud 中的總表 Excel，確保目錄存在"""
    try:
        if not os.path.exists(ICLOUD_BASE):
            os.makedirs(ICLOUD_BASE)
            
        new_data = pd.DataFrame({"Date": [date_str], "FFB": [ffb], "CPO": [cpo]})
        if os.path.exists(ICLOUD_EXCEL):
            # 讀取現有 Excel
            df_old = pd.read_excel(ICLOUD_EXCEL)
            # 檢查日期是否重複，若重複則更新當天數據
            if date_str in df_old['Date'].values:
                df_old.loc[df_old['Date'] == date_str, ['FFB', 'CPO']] = [ffb, cpo]
                df_combined = df_old
            else:
                df_combined = pd.concat([df_old, new_data], ignore_index=True)
            df_combined.to_excel(ICLOUD_EXCEL, index=False)
        else:
            new_data.to_excel(ICLOUD_EXCEL, index=False)
        print(f"✅ Excel 已更新至: {ICLOUD_EXCEL}")
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
        prompt = f"你是資深分析師。今天是 {today_str}。撰寫繁體中文「晨間新聞快報」。忽略價格數據。數據：{raw_data}"
    else:
        prompt = f"你是資深分析師。今天是 {today_str}。撰寫繁體中文「每日完整分析報告」。包含 FFB 與 CPO 價格預估。結尾輸出 DATA_JSON: {{\"ffb\": 6.5, \"cpo\": 40.0}}。數據：{raw_data}"
    
    content, price_data = "無法生成 AI 報告。", {"ffb": "N/A", "cpo": "N/A"}
    try:
        resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        if resp.text:
            content = resp.text
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
        mode = "news_only"; title = "📰 泰國棕櫚油晨間新聞快報"; file_suffix = "news_0700"
    elif curr_hm >= "13:30":
        mode = "full"; title = "📊 泰國棕櫚油每日完整報告"; file_suffix = "full_1330"
    else:
        print(f"⏳ 泰國時間尚未 07:00 ({curr_hm})，略過。"); return

    report_name = f"palm_report_{date_today}_{file_suffix}"
    html_path = f"docs/reports/{report_name}.html"
    icloud_pdf_path = os.path.join(ICLOUD_BASE, f"{report_name}.pdf")

    if os.path.exists(html_path): return

    print(f"🚀 開始執行 {mode} 任務...")
    raw_data = get_palm_news()
    content, price_data = extract_data_and_report(raw_data, mode)
    
    ffb = price_data.get("ffb")
    cpo = price_data.get("cpo")

    # 1. 更新 iCloud Excel (不論模式都執行，若無價格則為 N/A)
    update_icloud_excel(date_today, ffb, cpo)

    # 2. 產出 iCloud PDF
    create_pdf_report(icloud_pdf_path, title, date_today, ffb, cpo, content)

    # 3. 產出 HTML 並同步 GitHub
    html_body = markdown.markdown(content)
    final_html = f"<html><body style='background:#121212;color:#e0e0e0;padding:40px;font-family:sans-serif;'><h1>{title}</h1><p>日期：{date_today}</p>{html_body}</body></html>"
    with open(html_path, "w", encoding="utf-8") as f: f.write(final_html)
    with open("docs/index.html", "w", encoding="utf-8") as f: f.write(final_html)

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
