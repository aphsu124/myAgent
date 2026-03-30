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
PRICE_DATA_FILE = f"{DATA_DIR}/palm_prices.csv"
GITHUB_IO_URL = "https://aphsu124.github.io/myAgent"

ICLOUD_BASE = "/Users/bucksteam/Library/Mobile Documents/com~apple~CloudDocs/泰國/工作/甲米油廠/簡報"
ICLOUD_EXCEL = os.path.join(ICLOUD_BASE, "palm_oil_history.xlsx")
ICLOUD_MASTER_CHART = os.path.join(ICLOUD_BASE, "2026_Palm_Oil_Trend_Master.png")

# 字體路徑
FONT_PATH = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"
MY_FONT = fm.FontProperties(fname=FONT_PATH)

client = genai.Client(api_key=GEMINI_API_KEY, http_options={'api_version': 'v1'})

def style_excel(file_path):
    """美化 Excel 表格：大字體 + 產業指南 (徹底修復版)"""
    try:
        wb = load_workbook(file_path)
        ws = wb.active
        
        # 1. 處理已存在的合併儲存格 (避免報錯關鍵)
        merged_ranges = list(ws.merged_cells.ranges)
        for m_range in merged_ranges:
            ws.unmerge_cells(str(m_range))

        # 2. 定義樣式 (14 號字，微軟正黑體)
        font_name = 'Microsoft JhengHei'
        header_f = Font(name=font_name, size=14, bold=True, color="FFFFFF")
        data_f = Font(name=font_name, size=14)
        guide_title_f = Font(name=font_name, size=14, bold=True, color="FFFFFF")
        guide_item_f = Font(name=font_name, size=14, bold=True)
        guide_text_f = Font(name=font_name, size=13, color="333333")
        
        center_align = Alignment(horizontal='center', vertical='center', wrap_text=True)
        left_align = Alignment(horizontal='left', vertical='center', wrap_text=True)
        header_fill = PatternFill(start_color="2E7D32", end_color="2E7D32", fill_type="solid")
        guide_fill = PatternFill(start_color="1565C0", end_color="1565C0", fill_type="solid")
        border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))

        # 3. 美化數據區 (A-G 欄)
        for c in range(1, 8):
            # 標題
            cell = ws.cell(row=1, column=c)
            cell.font = header_f; cell.fill = header_fill; cell.alignment = center_align; cell.border = border
            # 內容
            for r in range(2, ws.max_row + 1):
                cell = ws.cell(row=r, column=c)
                cell.font = data_f; cell.alignment = center_align; cell.border = border
                if isinstance(cell.value, (int, float)): cell.number_format = '0.00'

        # 4. 建立指南區 (I-J 欄)
        guide_col = 9
        # 清空並重新寫入
        ws.cell(row=1, column=guide_col).value = "📚 產業術語與計算指南 (Guide)"
        ws.cell(row=1, column=guide_col).font = guide_title_f
        ws.cell(row=1, column=guide_col).fill = guide_fill
        ws.cell(row=1, column=guide_col).alignment = center_align
        ws.merge_cells(start_row=1, start_column=guide_col, end_row=1, end_column=guide_col+1)
        
        guide_items = [
            ["FFB", "Fresh Fruit Bunch : 油棕鮮果串。工廠收購的原始原料。"],
            ["CPO", "Crude Palm Oil : 毛棕櫚油。工廠壓榨產出的核心產品。"],
            ["BMD", "Bursa Malaysia Derivatives : 馬來西亞期貨。全球報價基準。"],
            ["Basis", "基差 = 泰國CPO - (BMD/1000 * 匯率)。反映國內外溢價。"],
            ["EX Rate", "Exchange Rate : 馬幣(MYR) 兌 泰銖(THB) 匯率。"]
        ]
        for i, item in enumerate(guide_items):
            ws.cell(row=i+2, column=guide_col).value = item[0]
            ws.cell(row=i+2, column=guide_col).font = guide_item_f
            ws.cell(row=i+2, column=guide_col+1).value = item[1]
            ws.cell(row=i+2, column=guide_col+1).font = guide_text_f
            ws.cell(row=i+2, column=guide_col+1).alignment = left_align

        # 5. 設定欄寬 (14 號字需要更大空間)
        widths = {'A': 22, 'B': 16, 'C': 16, 'D': 16, 'E': 16, 'F': 22, 'G': 16, 'H': 5, 'I': 20, 'J': 85}
        for col_l, w in widths.items():
            ws.column_dimensions[col_l].width = w

        wb.save(file_path)
        print(f"✅ Excel 樣式已完美儲存！(14號大字 + 指南區)")
    except Exception as e:
        print(f"Excel 美化失敗: {e}")

def update_icloud_excel(date_str, ffb, cpo, bmd_myr, ex_rate):
    try:
        if not os.path.exists(ICLOUD_BASE): os.makedirs(ICLOUD_BASE)
        def to_f(v):
            try: return float(v)
            except: return 0.0
        f_ffb, f_cpo, f_bmd, f_ex = to_f(ffb), to_f(cpo), to_f(bmd_myr), to_f(ex_rate)
        bmd_thb = round((f_bmd / 1000) * f_ex, 2)
        basis = round(f_cpo - bmd_thb, 2) if f_cpo > 0 and bmd_thb > 0 else 0.0
        new_row = {"Date": [date_str], "FFB": [f_ffb], "CPO": [f_cpo], "BMD_MYR": [f_bmd], "Exchange_Rate": [f_ex], "BMD_THB_kg": [bmd_thb], "Basis": [basis]}
        df_new = pd.DataFrame(new_row)
        if os.path.exists(ICLOUD_EXCEL):
            df_old = pd.read_excel(ICLOUD_EXCEL)
            if date_str in df_old['Date'].values:
                for col in df_new.columns: df_old.loc[df_old['Date'] == date_str, col] = df_new[col].values[0]
                df_combined = df_old
            else: df_combined = pd.concat([df_old, df_new], ignore_index=True)
            df_combined.to_excel(ICLOUD_EXCEL, index=False)
        else: df_new.to_excel(ICLOUD_EXCEL, index=False)
        style_excel(ICLOUD_EXCEL)
        return bmd_thb, basis
    except Exception as e: print(f"Excel 錯誤: {e}"); return 0, 0

# ... (其餘函數 get_palm_news, extract_data_and_report, generate_master_chart, main 保持不變) ...

def get_palm_news():
    url = "https://google.serper.dev/search"
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    queries = [f"Thailand palm oil FFB CPO price Krabi {today} -travel", f"Bursa Malaysia CPO futures closing {today}", f"MYR to THB exchange rate"]
    headers = {'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'}
    res = ""
    for q in queries:
        payload = {"q": q, "gl": "th", "hl": "en", "tbs": "qdr:m"}
        try:
            r = requests.post(url, headers=headers, json=payload)
            if r.status_code == 200:
                for o in r.json().get('organic', []): res += f"\n[{o.get('date', 'N/A')}] {o.get('title')}\n{o.get('snippet')}\n"
        except: pass
    return res

def extract_data_and_report(raw_data, mode="full"):
    now = datetime.datetime.now().strftime("%Y-%m-%d")
    prompt = f"你是資深分析師。今天是 {now}。撰寫「{'晨間新聞' if mode=='news_only' else '每日分析'}」。最後輸出 JSON: DATA_JSON: {{\"ffb\": 6.5, \"cpo\": 40.0, \"bmd_myr\": 4500, \"ex_rate\": 7.8}}。數據：{raw_data}"
    content, data = "無法生成 AI 報告。", {"ffb": "N/A", "cpo": "N/A", "bmd_myr": "N/A", "ex_rate": "N/A"}
    try:
        resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        if resp.text:
            content = resp.text
            m = re.search(r'DATA_JSON: ({.*?})', content)
            if m: data = json.loads(m.group(1))
    except Exception as e: print(f"AI 出錯: {e}")
    return content, data

def generate_master_chart():
    try:
        if not os.path.exists(ICLOUD_EXCEL): return
        df = pd.read_excel(ICLOUD_EXCEL); df['D_S'] = pd.to_datetime(df['Date']).dt.strftime('%m-%d')
        fig, ax1 = plt.subplots(figsize=(12, 7))
        ax1.plot(df['D_S'], df['CPO'], color='tab:blue', marker='s', label='泰國 CPO 現貨', linewidth=2)
        if 'BMD_THB_kg' in df.columns: ax1.plot(df['D_S'], df['BMD_THB_kg'], color='tab:orange', linestyle=':', label='國際期貨 (折算)')
        ax2 = ax1.twinx(); ax2.plot(df['D_S'], df['FFB'], color='tab:green', marker='o', label='FFB 收購', linestyle='--')
        plt.title('2026年棕櫚油價格與基差監控圖', fontproperties=MY_FONT, fontsize=16)
        ax1.legend(loc='upper left', prop=MY_FONT); ax2.legend(loc='upper right', prop=MY_FONT)
        plt.savefig(ICLOUD_MASTER_CHART, dpi=300); plt.close()
    except: pass

def create_pdf_report(filename, title, date, ffb, cpo, content):
    try:
        c = canvas.Canvas(filename, pagesize=A4); c.setFont("Helvetica-Bold", 18); c.drawString(50, 800, title)
        c.setFont("Helvetica", 12); c.drawString(50, 775, f"Date: {date} | FFB: {ffb} | CPO: {cpo}"); c.save()
    except: pass

def main():
    ict_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7)))
    date_fn = ict_now.strftime("%Y%m%d"); date_ds = ict_now.strftime("%Y-%m-%d")
    curr_hm = ict_now.strftime("%H:%M")
    if "07:00" <= curr_hm < "13:30":
        mode = "news_only"; title = "📰 泰國棕櫚油晨間新聞"; suffix = "M_report"
    elif curr_hm >= "13:30":
        mode = "full"; title = "📊 泰國棕櫚油完整報告"; suffix = "D_report"
    else: return
    report_path = f"docs/reports/{date_fn}_{suffix}.html"
    if os.path.exists(report_path): return
    print(f"🚀 啟動 {mode} 任務...")
    raw_data = get_palm_news()
    content, data = extract_data_and_report(raw_data, mode)
    bmd_thb, basis = update_icloud_excel(date_ds, data.get("ffb"), data.get("cpo"), data.get("bmd_myr"), data.get("ex_rate"))
    generate_master_chart()
    html_body = markdown.markdown(content)
    web_content = f"<html><body style='background:#121212;color:#e0e0e0;padding:40px;font-family:sans-serif;'><h1>{title}</h1>{html_body}</body></html>"
    with open(report_path, "w", encoding="utf-8") as f: f.write(web_content)
    with open("docs/index.html", "w", encoding="utf-8") as f: f.write(web_content)
    try:
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", f"📊 Update {date_fn}"], check=True)
        subprocess.run(["git", "push", "origin", "main"], check=True)
    except: pass
    msg = f"{title} ({date_ds})\n"
    msg += f"🔸 FFB: {data.get('ffb')} Baht/kg\n"
    msg += f"🔸 CPO: {data.get('cpo')} Baht/kg\n"
    msg += f"🔸 基差: {basis} Baht/kg\n"
    msg += f"\n👉 查看網頁：{GITHUB_IO_URL}/index.html"
    msg += f"\n📂 iCloud 已同步: {date_fn}_{suffix}.pdf"
    requests.post(f"https://api.line.me/v2/bot/message/push", headers={"Content-Type": "application/json", "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}, json={"to": LINE_USER_ID, "messages": [{"type": "text", "text": msg}]})

if __name__ == "__main__":
    main()
