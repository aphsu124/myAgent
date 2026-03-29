import os
import requests
import datetime
import json
import re
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
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
ICLOUD_MASTER_CHART = os.path.join(ICLOUD_BASE, "2026_Palm_Oil_Trend_Master.png")

# 中文字型設定
CHINESE_FONT_PATH = "/System/Library/Fonts/STHeiti Light.ttc"
try:
    pdfmetrics.registerFont(TTFont('ChineseFont', CHINESE_FONT_PATH))
    MY_FONT = fm.FontProperties(fname=CHINESE_FONT_PATH)
    HAS_CHINESE = True
except:
    HAS_CHINESE = False

MARKET_EVENTS = {
    '2026-02-28': '中東局勢緊張',
    '2026-03-13': '能源成本激增',
    '2026-03-23': '政策介入前高點',
    '2026-03-28': '政府價格管制生效'
}

client = genai.Client(api_key=GEMINI_API_KEY, http_options={'api_version': 'v1'})

def generate_master_chart():
    try:
        if not os.path.exists(ICLOUD_EXCEL): return None
        df = pd.read_excel(ICLOUD_EXCEL)
        df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%m-%d')
        fig, ax1 = plt.subplots(figsize=(12, 7))
        ax1.set_xlabel('日期 (2026)', fontproperties=MY_FONT)
        ax1.set_ylabel('CPO 價格 (Baht/kg)', color='tab:blue', fontproperties=MY_FONT)
        ax1.plot(df['Date'], df['CPO'], color='tab:blue', marker='s', linewidth=2, label='CPO')
        ax2 = ax1.twinx()
        ax2.set_ylabel('FFB 價格 (Baht/kg)', color='tab:green', fontproperties=MY_FONT)
        ax2.plot(df['Date'], df['FFB'], color='tab:green', marker='o', linewidth=2, linestyle='--', label='FFB')
        for date_full, txt in MARKET_EVENTS.items():
            date_short = date_full[5:10].replace('-', '-') # 轉 MM-DD
            if date_short in df['Date'].values:
                y_val = df.loc[df['Date'] == date_short, 'CPO'].values[0]
                ax1.annotate(txt, xy=(date_short, y_val), xytext=(10, 20),
                             textcoords='offset points', arrowprops=dict(arrowstyle='->', color='red'),
                             fontproperties=MY_FONT, fontsize=9, color='red', backgroundcolor='white')
        plt.title('2026年泰國棕櫚油價格趨勢總表', fontproperties=MY_FONT, fontsize=16)
        ax1.grid(True, linestyle=':', alpha=0.6)
        plt.savefig(ICLOUD_MASTER_CHART, dpi=300); plt.close()
    except Exception as e: print(f"Master Chart 失敗: {e}")

def create_pdf_report(filename, title, date, ffb, cpo, content):
    try:
        c = canvas.Canvas(filename, pagesize=A4)
        font_n = 'ChineseFont' if HAS_CHINESE else 'Helvetica'
        c.setFont(font_n, 18); c.drawString(50, 800, title)
        c.setFont(font_n, 12); c.drawString(50, 775, f"日期: {date} | FFB: {ffb} | CPO: {cpo}")
        c.line(50, 765, 550, 765); c.setFont(font_n, 10); y = 740
        clean = content.replace('#', '').replace('*', '')
        for line in clean.split('\n'):
            if not line.strip(): continue
            txt = line.strip()
            while len(txt) > 0:
                if y < 50: c.showPage(); c.setFont(font_n, 10); y = 800
                c.drawString(50, y, txt[:45]); txt = txt[45:]; y -= 15
        c.save()
    except Exception as e: print(f"PDF 錯誤: {e}")

def update_icloud_excel(date_str, ffb, cpo):
    try:
        if not os.path.exists(ICLOUD_BASE): os.makedirs(ICLOUD_BASE)
        new_data = pd.DataFrame({"Date": [date_str], "FFB": [ffb], "CPO": [cpo]})
        if os.path.exists(ICLOUD_EXCEL):
            df_old = pd.read_excel(ICLOUD_EXCEL)
            if date_str in df_old['Date'].values:
                df_old.loc[df_old['Date'] == date_str, ['FFB', 'CPO']] = [ffb, cpo]
                df_old.to_excel(ICLOUD_EXCEL, index=False)
            else: pd.concat([df_old, new_data], ignore_index=True).to_excel(ICLOUD_EXCEL, index=False)
        else: new_data.to_excel(ICLOUD_EXCEL, index=False)
    except Exception as e: print(f"Excel 錯誤: {e}")

def get_palm_news():
    url = "https://google.serper.dev/search"
    now = datetime.datetime.now(); today = now.strftime("%Y-%m-%d")
    queries = [f"Thailand palm oil price Krabi {today}", f"Thailand Ministry of Commerce palm oil policy {now.strftime('%B %Y')}"]
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
    now = datetime.datetime.now(); today_str = now.strftime("%Y-%m-%d")
    prompt = f"你是資深分析師。今天是 {today_str}。撰寫繁體中文「{'晨間新聞快報' if mode=='news_only' else '每日分析報告'}」。結尾輸出 DATA_JSON: {{\"ffb\": 6.5, \"cpo\": 40.0}}。數據：{raw_data}"
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
    # 新命規格式
    date_filename = ict_now.strftime("%Y%m%d")
    date_display = ict_now.strftime("%Y-%m-%d")
    curr_hm = ict_now.strftime("%H:%M")
    
    if "07:00" <= curr_hm < "13:30":
        mode = "news_only"; title = "📰 泰國棕櫚油晨間新聞"; suffix = "M_report"
    elif curr_hm >= "13:30":
        mode = "full"; title = "📊 泰國棕櫚油完整報告"; suffix = "D_report"
    else: return

    report_name = f"{date_filename}_{suffix}"
    html_path = f"docs/reports/{report_name}.html"
    if os.path.exists(html_path): return

    print(f"🚀 啟動 {mode} 任務 (新檔名格式)...")
    raw_data = get_palm_news()
    content, price_data = extract_data_and_report(raw_data, mode)
    
    # 1. 更新數據庫 (使用 2026-03-29 格式存檔)
    update_icloud_excel(date_display, price_data.get("ffb"), price_data.get("cpo"))
    generate_master_chart()

    # 2. 產出 PDF
    create_pdf_report(os.path.join(ICLOUD_BASE, f"{report_name}.pdf"), title, date_display, price_data.get("ffb"), price_data.get("cpo"), content)

    # 3. 網頁同步
    html_body = markdown.markdown(content)
    web_content = f"<html><body style='background:#121212;color:#e0e0e0;padding:40px;font-family:sans-serif;'><h1>{title}</h1>{html_body}</body></html>"
    with open(html_path, "w", encoding="utf-8") as f: f.write(web_content)
    with open("docs/index.html", "w", encoding="utf-8") as f: f.write(web_content)
    
    try:
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", f"📊 Rename Update {date_filename}"], check=True)
        subprocess.run(["git", "push", "origin", "main"], check=True)
    except: pass

    # 4. LINE 推播
    msg = f"{title}\n🔸 FFB: {price_data.get('ffb')}\n🔸 CPO: {price_data.get('cpo')}\n👉 報告 {report_name} 已存入 iCloud"
    line_url = f"https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}
    requests.post(line_url, headers=headers, json={"to": LINE_USER_ID, "messages": [{"type": "text", "text": msg}]})

if __name__ == "__main__":
    main()
