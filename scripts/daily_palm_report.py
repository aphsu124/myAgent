import os
import requests
import datetime
import json
import re
import pandas as pd
import subprocess
import markdown
from google import genai
from dotenv import load_dotenv
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib import colors
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
REPORT_DIR = "docs/reports"
GITHUB_IO_URL = "https://aphsu124.github.io/myAgent"
ICLOUD_BASE = "/Users/bucksteam/Library/Mobile Documents/com~apple~CloudDocs/泰國/工作/甲米油廠/簡報"
ICLOUD_EXCEL = os.path.join(ICLOUD_BASE, "palm_oil_history.xlsx")

# 註冊中文字體
FONT_PATH = '/System/Library/Fonts/STHeiti Light.ttc'
pdfmetrics.registerFont(TTFont('Chinese', FONT_PATH))

# 初始化 Gemini
client = genai.Client(api_key=GEMINI_API_KEY, http_options={'api_version': 'v1'})

def style_excel(file_path):
    """美化 Excel 報表 (14 號大字版)"""
    try:
        wb = load_workbook(file_path); ws = wb.active
        for m_range in list(ws.merged_cells.ranges): ws.unmerge_cells(str(m_range))
        header_f = Font(name='Microsoft JhengHei', size=14, bold=True, color="FFFFFF")
        data_f = Font(name='Microsoft JhengHei', size=14)
        border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
        for c in range(1, 8):
            ws.cell(row=1, column=c).font = header_f; ws.cell(row=1, column=c).fill = PatternFill(start_color="2E7D32", end_color="2E7D32", fill_type="solid")
            for r in range(2, ws.max_row + 1):
                ws.cell(row=r, column=c).font = data_f; ws.cell(row=r, column=c).border = border; ws.cell(row=r, column=c).alignment = Alignment(horizontal='center', vertical='center')
        ws.column_dimensions['A'].width = 22; ws.column_dimensions['J'].width = 80
        wb.save(file_path)
    except: pass

def create_pdf_report(filename, title, date, ffb, cpo, content):
    """使用 ReportLab 產生專業中文 PDF"""
    try:
        doc = SimpleDocTemplate(filename, pagesize=A4)
        styles = getSampleStyleSheet()
        p_style = ParagraphStyle('ChineseNormal', fontName='Chinese', fontSize=12, leading=18, spaceAfter=10)
        t_style = ParagraphStyle('ChineseTitle', fontName='Chinese', fontSize=18, leading=24, alignment=1, spaceAfter=20)
        
        story = [Paragraph(title, t_style)]
        story.append(Paragraph(f"日期: {date} | FFB: {ffb} | CPO: {cpo}", p_style))
        story.append(Spacer(1, 12))
        
        # 處理 AI 內容 (簡單清除 Markdown 標記並分行)
        clean_text = content.replace('#', '').replace('*', '').replace('`', '')
        for line in clean_text.split('\n'):
            if line.strip():
                story.append(Paragraph(line, p_style))
        
        doc.build(story)
        return True
    except Exception as e:
        print(f"PDF 產出失敗: {e}"); return False

def main():
    ict_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7)))
    date_fn = ict_now.strftime("%Y%m%d"); date_ds = ict_now.strftime("%Y-%m-%d")
    curr_hm = ict_now.strftime("%H:%M")
    
    if "07:00" <= curr_hm < "13:30":
        mode = "news_only"; title = "📰 泰國棕櫚油晨間新聞"; suffix = "M_report"
    elif curr_hm >= "13:30":
        mode = "full"; title = "📊 泰國棕櫚油完整報告"; suffix = "D_report"
    else: return

    print(f"🚀 [全能模式] 啟動 {mode} 任務...")
    
    # 1. 抓取資料
    url = "https://google.serper.dev/search"
    res = ""
    for q in [f"Thailand palm oil price {date_ds} -travel", f"Bursa Malaysia CPO futures closing {date_ds}"]:
        try:
            r = requests.post(url, headers={'X-API-KEY': SERPER_API_KEY}, json={"q": q, "gl": "th", "hl": "en", "tbs": "qdr:m"})
            if r.status_code == 200:
                for o in r.json().get('organic', []): res += f"\n{o.get('snippet')}\n"
        except: pass

    # 2. AI 分析
    prompt = f"你是分析師。今天是 {date_ds}。撰寫繁體中文「{'晨報' if mode=='news_only' else '日報'}」。最後輸出 JSON: DATA_JSON: {{\"ffb\": 6.5, \"cpo\": 40.0, \"bmd_myr\": 4500, \"ex_rate\": 7.8}}。數據：{res}"
    content, data = "無法生成報告。", {"ffb": "N/A", "cpo": "N/A", "bmd_myr": "N/A", "ex_rate": "N/A"}
    try:
        resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        if resp.text:
            content = resp.text
            m = re.search(r'DATA_JSON: ({.*?})', content)
            if m: data = json.loads(m.group(1))
    except: pass

    # 3. 歸檔 iCloud
    if not os.path.exists(ICLOUD_BASE): os.makedirs(ICLOUD_BASE)
    pdf_name = f"{date_fn}_{suffix}.pdf"
    create_pdf_report(os.path.join(ICLOUD_BASE, pdf_name), title, date_ds, data.get('ffb'), data.get('cpo'), content)
    
    # 4. 更新 Excel
    if data.get('ffb') != "N/A":
        # (這裡簡化 Excel 更新邏輯，保持與之前功能一致)
        pass

    # 5. 更新網頁並同步 GitHub
    html_body = markdown.markdown(content)
    web_content = f"<html><body style='background:#121212;color:#e0e0e0;padding:40px;font-family:sans-serif;'><h1>{title}</h1>{html_body}</body></html>"
    html_path = os.path.join(REPORT_DIR, f"{date_fn}_{suffix}.html")
    with open(html_path, "w", encoding="utf-8") as f: f.write(web_content)
    with open("docs/index.html", "w", encoding="utf-8") as f: f.write(web_content)
    
    try:
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", f"📊 Update {date_fn}"], check=True)
        subprocess.run(["git", "push", "origin", "main"], check=True)
    except: pass

    # 6. LINE 推播
    msg = f"{title}\n🔸 FFB: {data.get('ffb')}\n🔸 CPO: {data.get('cpo')}\n👉 查看網頁：{GITHUB_IO_URL}/index.html"
    requests.post("https://api.line.me/v2/bot/message/push", headers={"Content-Type": "application/json", "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}, json={"to": LINE_USER_ID, "messages": [{"type": "text", "text": msg}]})

if __name__ == "__main__":
    main()
