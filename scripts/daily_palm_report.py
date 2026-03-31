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
pdfmetrics.registerFont(TTFont('Chinese', '/System/Library/Fonts/STHeiti Light.ttc'))
client = genai.Client(api_key=GEMINI_API_KEY, http_options={'api_version': 'v1'})

# --- 1. Excel 樣式固化函數 ---
def style_excel(file_path):
    try:
        wb = load_workbook(file_path); ws = wb.active
        for m_range in list(ws.merged_cells.ranges): ws.unmerge_cells(str(m_range))
        f_n = 'Microsoft JhengHei'; h_f = Font(name=f_n, size=14, bold=True, color="FFFFFF")
        d_f = Font(name=f_n, size=14); border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
        for c in range(1, 8):
            ws.cell(1, c).font = h_f; ws.cell(1, c).fill = PatternFill('solid', '2E7D32')
            ws.cell(1, c).alignment = Alignment('center', 'center')
            for r in range(2, ws.max_row + 1):
                cell = ws.cell(r, c); cell.font = d_f; cell.border = border; cell.alignment = Alignment('center', 'center')
                if isinstance(cell.value, (int, float)): cell.number_format = '0.00'
        # 指南區
        g_c = 9; ws.cell(1, g_c).value = "📚 產業術語與計算指南"; ws.cell(1, g_c).font = h_f; ws.cell(1, g_c).fill = PatternFill('solid', '1565C0')
        ws.merge_cells(start_row=1, start_column=g_c, end_row=1, end_column=g_c+1)
        ws.cell(1, g_c).alignment = Alignment('center', 'center')
        # 最終寬度
        ws.column_dimensions['A'].width = 25; ws.column_dimensions['D'].width = 22; ws.column_dimensions['E'].width = 22; ws.column_dimensions['J'].width = 110
        wb.save(file_path)
    except: pass

# --- 2. PDF 產出 ---
def create_pdf_report(filename, title, date, ffb, cpo, content):
    try:
        doc = SimpleDocTemplate(filename, pagesize=A4)
        p_s = ParagraphStyle('CN', fontName='Chinese', fontSize=12, leading=18, spaceAfter=10)
        t_s = ParagraphStyle('T', fontName='Chinese', fontSize=18, leading=24, alignment=1, spaceAfter=20)
        story = [Paragraph(title, t_s), Paragraph(f"日期: {date} | FFB: {ffb} | CPO: {cpo}", p_s), Spacer(1, 12)]
        for line in content.replace('#','').replace('*','').split('\n'):
            if line.strip(): story.append(Paragraph(line, p_s))
        doc.build(story)
    except: pass

def main():
    ict_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7)))
    date_fn, date_ds, curr_hm = ict_now.strftime("%Y%m%d"), ict_now.strftime("%Y-%m-%d"), ict_now.strftime("%H:%M")
    
    # 【第一道防線】嚴格時段檢查
    is_morning = "07:00" <= curr_hm < "08:00"
    is_afternoon = "13:30" <= curr_hm < "14:30"
    
    # 判斷模式
    if is_morning:
        mode, title, suffix = "news_only", "📰 泰國棕櫚油晨間新聞", "M_report"
    elif is_afternoon:
        mode, title, suffix = "full", "📊 泰國棕櫚油完整報告", "D_report"
    else:
        print(f"⏳ 非報告發送時段 ({curr_hm})，Jarvis 休息中。"); return

    # 【第二道防線】防重複鎖
    report_name = f"{date_fn}_{suffix}"
    html_path = os.path.join(REPORT_DIR, f"{report_name}.html")
    if os.path.exists(html_path):
        print(f"✅ 今日 {suffix} 已經發送過，不再重複。"); return

    print(f"🚀 開始執行 {mode} 任務...")
    
    # 抓取數據與 AI 分析 (省略部分代碼以保長度，邏輯與之前一致)
    url = "https://google.serper.dev/search"; res = ""
    for q in [f"Thailand palm oil price {date_ds} -travel", f"Bursa Malaysia CPO futures closing {date_ds}"]:
        try:
            r = requests.post(url, headers={'X-API-KEY': SERPER_API_KEY}, json={"q": q, "gl": "th", "hl": "en", "tbs": "qdr:m"})
            if r.status_code == 200:
                for o in r.json().get('organic', []): res += f"\n{o.get('snippet')}\n"
        except: pass

    content, data = "無法生成分析。", {"ffb": "N/A", "cpo": "N/A", "bmd_myr": "N/A", "ex_rate": "N/A"}
    try:
        resp = client.models.generate_content(model="gemini-2.5-flash", contents=f"撰寫繁體中文報告並輸出 JSON: DATA_JSON: {{...}} \n 數據：{res}")
        if resp.text:
            content = resp.text
            m = re.search(r'DATA_JSON: ({.*?})', content)
            if m: data = json.loads(m.group(1))
    except: pass

    # 存數據
    def to_f(v):
        try: return float(v)
        except: return 0.0
    f_ffb, f_cpo, f_bmd, f_ex = to_f(data.get('ffb')), to_f(data.get('cpo')), to_f(data.get('bmd_myr')), to_f(data.get('ex_rate'))
    bmd_thb = round((f_bmd / 1000) * f_ex, 2); basis = round(f_cpo - bmd_thb, 2) if f_cpo > 0 else 0.0

    if is_afternoon: # 只有下午才更新 Excel
        new_r = pd.DataFrame({"Date": [date_ds], "FFB": [f_ffb], "CPO": [f_cpo], "BMD_MYR": [f_bmd], "Exchange_Rate": [f_ex], "BMD_THB_kg": [bmd_thb], "Basis": [basis]})
        if os.path.exists(ICLOUD_EXCEL):
            df_old = pd.read_excel(ICLOUD_EXCEL)
            if date_ds not in df_old['Date'].values:
                pd.concat([df_old, new_r], ignore_index=True).to_excel(ICLOUD_EXCEL, index=False)
        else: new_r.to_excel(ICLOUD_EXCEL, index=False)
        style_excel(ICLOUD_EXCEL)

    create_pdf_report(os.path.join(ICLOUD_BASE, f"{report_name}.pdf"), title, date_ds, data.get('ffb'), data.get('cpo'), content)

    # 網頁
    html_body = markdown.markdown(content)
    web_c = f"<html><body style='background:#121212;color:#e0e0e0;padding:40px;font-family:sans-serif;'><h1>{title}</h1>{html_body}</body></html>"
    with open(html_path, "w", encoding="utf-8") as f: f.write(web_c)
    with open("docs/index.html", "w", encoding="utf-8") as f: f.write(web_c)
    
    try:
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", f"📊 Stable Update {date_fn}"], check=True)
        subprocess.run(["git", "push", "origin", "main"], check=True)
    except: pass

    # 【第三道防線】LINE 通知數值格式化
    disp_ffb = f"{data.get('ffb')} Baht/kg" if f_ffb > 0 else "等待市場開盤"
    disp_cpo = f"{data.get('cpo')} Baht/kg" if f_cpo > 0 else "等待市場開盤"
    msg = f"{title}\n🔸 FFB: {disp_ffb}\n🔸 CPO: {disp_cpo}\n🔸 基差: {basis if f_cpo > 0 else 'N/A'}\n👉 查看網頁：{GITHUB_IO_URL}/index.html"
    requests.post("https://api.line.me/v2/bot/message/push", headers={"Content-Type": "application/json", "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}, json={"to": LINE_USER_ID, "messages": [{"type": "text", "text": msg}]})

if __name__ == "__main__":
    main()
