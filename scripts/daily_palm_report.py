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
from openai import OpenAI
from dotenv import load_dotenv
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from openpyxl import load_workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

# === 配置區 ===
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_USER_ID = os.getenv("LINE_USER_ID")
REPORT_DIR = os.getenv("REPORT_DIR", "docs/reports")
DATA_DIR = os.getenv("DATA_DIR", "data")
GITHUB_IO_URL = "https://aphsu124.github.io/myAgent"

ICLOUD_BASE = "/Users/bucksteam/Library/Mobile Documents/com~apple~CloudDocs/泰國/工作/甲米油廠/簡報"
ICLOUD_EXCEL = os.path.join(ICLOUD_BASE, "palm_oil_history.xlsx")
ICLOUD_MASTER_CHART = os.path.join(ICLOUD_BASE, "2026_Palm_Oil_Trend_Master.png")

# 初始化 Gemini
client = genai.Client(api_key=GEMINI_API_KEY, http_options={'api_version': 'v1'})

def style_excel(file_path):
    try:
        wb = load_workbook(file_path); ws = wb.active
        for m_range in list(ws.merged_cells.ranges): ws.unmerge_cells(str(m_range))
        font_name = 'Microsoft JhengHei'; header_f = Font(name=font_name, size=14, bold=True, color="FFFFFF")
        data_f = Font(name=font_name, size=14); border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
        for c in range(1, 8):
            ws.cell(row=1, column=c).font = header_f; ws.cell(row=1, column=c).fill = PatternFill(start_color="2E7D32", end_color="2E7D32", fill_type="solid")
            for r in range(2, ws.max_row + 1):
                ws.cell(row=r, column=c).font = data_f; ws.cell(row=r, column=c).alignment = Alignment(horizontal='center', vertical='center')
        # 指南區
        guide_col = 9
        ws.cell(row=1, column=guide_col).value = "📚 產業指南"; ws.cell(row=1, column=guide_col).font = header_f; ws.cell(row=1, column=guide_col).fill = PatternFill(start_color="1565C0", end_color="1565C0", fill_type="solid")
        ws.merge_cells(start_row=1, start_column=guide_col, end_row=1, end_column=guide_col+1)
        ws.column_dimensions['J'].width = 80
        wb.save(file_path)
    except: pass

def update_icloud_excel(date_str, ffb, cpo, bmd_myr, ex_rate):
    try:
        def to_f(v):
            try: return float(v)
            except: return 0.0
        f_ffb, f_cpo, f_bmd, f_ex = to_f(ffb), to_f(cpo), to_f(bmd_myr), to_f(ex_rate)
        bmd_thb = round((f_bmd / 1000) * f_ex, 2)
        basis = round(f_cpo - bmd_thb, 2) if f_cpo > 0 else 0.0
        new_row = {"Date": [date_str], "FFB": [f_ffb], "CPO": [f_cpo], "BMD_MYR": [f_bmd], "Exchange_Rate": [f_ex], "BMD_THB_kg": [bmd_thb], "Basis": [basis]}
        df_new = pd.DataFrame(new_row)
        if os.path.exists(ICLOUD_EXCEL):
            df_old = pd.read_excel(ICLOUD_EXCEL)
            if date_str in df_old['Date'].values:
                for col in df_new.columns: df_old.loc[df_old['Date'] == date_str, col] = df_new[col].values[0]
                df_old.to_excel(ICLOUD_EXCEL, index=False)
            else: pd.concat([df_old, df_new], ignore_index=True).to_excel(ICLOUD_EXCEL, index=False)
        else: df_new.to_excel(ICLOUD_EXCEL, index=False)
        style_excel(ICLOUD_EXCEL)
        return bmd_thb, basis
    except: return 0, 0

def create_pdf_report(filename, title, date, ffb, cpo, content):
    try:
        c = canvas.Canvas(filename, pagesize=A4)
        c.setFont("Helvetica-Bold", 18); c.drawString(50, 800, title)
        c.setFont("Helvetica", 12); c.drawString(50, 775, f"Date: {date} | FFB: {ffb} | CPO: {cpo}")
        c.save()
    except: pass

def main():
    ict_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7)))
    date_fn = ict_now.strftime("%Y%m%d"); date_ds = ict_now.strftime("%Y-%m-%d")
    curr_hm = ict_now.strftime("%H:%M")
    
    # 決定模式
    if "07:00" <= curr_hm < "13:30":
        mode = "news_only"; title = "📰 泰國棕櫚油晨間新聞"; suffix = "M_report"
    elif curr_hm >= "13:30":
        mode = "full"; title = "📊 泰國棕櫚油完整報告"; suffix = "D_report"
    else: return

    report_name = f"{date_fn}_{suffix}"
    html_path = os.path.join(REPORT_DIR, f"{report_name}.html")
    icloud_pdf = os.path.join(ICLOUD_BASE, f"{report_name}.pdf")

    # 移除跳過邏輯，強制執行與覆蓋
    print(f"🚀 開始執行 {mode} 任務並強制同步...")
    
    url = "https://google.serper.dev/search"
    queries = [f"Thailand palm oil price Krabi {date_ds} -travel", f"Bursa Malaysia CPO futures closing {date_ds}"]
    headers = {'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'}
    res = ""
    for q in queries:
        try:
            r = requests.post(url, headers=headers, json={"q": q, "gl": "th", "hl": "en", "tbs": "qdr:m"})
            if r.status_code == 200:
                for o in r.json().get('organic', []): res += f"\n[{o.get('date', 'N/A')}] {o.get('title')}\n{o.get('snippet')}\n"
        except: pass

    # AI 生成
    prompt = f"你是資深分析師。今天是 {date_ds}。撰寫繁體中文「{'晨間新聞' if mode=='news_only' else '每日分析'}」。最後輸出 JSON: DATA_JSON: {{\"ffb\": 6.5, \"cpo\": 40.0, \"bmd_myr\": 4500, \"ex_rate\": 7.8}}。數據：{res}"
    content, data = "無法生成 AI 報告。", {"ffb": "N/A", "cpo": "N/A", "bmd_myr": "N/A", "ex_rate": "N/A"}
    try:
        resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        if resp.text:
            content = resp.text
            m = re.search(r'DATA_JSON: ({.*?})', content)
            if m: data = json.loads(m.group(1))
    except: pass

    # 存數據 & PDF
    bmd_thb, basis = update_icloud_excel(date_ds, data.get("ffb"), data.get("cpo"), data.get("bmd_myr"), data.get("ex_rate"))
    create_pdf_report(icloud_pdf, title, date_ds, data.get("ffb"), data.get("cpo"), content)

    # 網頁
    html_body = markdown.markdown(content)
    web_content = f"<html><body style='background:#121212;color:#e0e0e0;padding:40px;font-family:sans-serif;'><h1>{title}</h1>{html_body}</body></html>"
    with open(html_path, "w", encoding="utf-8") as f: f.write(web_content)
    with open("docs/index.html", "w", encoding="utf-8") as f: f.write(web_content)
    
    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(["git", "commit", "-m", f"📊 Forced Update {date_fn}"], check=True)
    subprocess.run(["git", "push", "origin", "main"], check=True)

    msg = f"{title} ({date_ds})\n🔸 FFB: {data.get('ffb')}\n🔸 CPO: {data.get('cpo')}\n🔸 基差: {basis}\n👉 查看網頁：{GITHUB_IO_URL}/index.html"
    requests.post(f"https://api.line.me/v2/bot/message/push", headers={"Content-Type": "application/json", "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}, json={"to": LINE_USER_ID, "messages": [{"type": "text", "text": msg}]})

if __name__ == "__main__":
    main()
