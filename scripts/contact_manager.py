import os
import json
import shutil
import re
import pandas as pd
import fitz
from PIL import Image
from google import genai
from dotenv import load_dotenv
from openpyxl import load_workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
BASE_DIR = "/Users/bucksteam/Library/Mobile Documents/com~apple~CloudDocs/泰國/工作/聯絡人"
EXCEL_PATH = os.path.join(BASE_DIR, "人脈總表.xlsx")

client = genai.Client(api_key=GEMINI_API_KEY, http_options={'api_version': 'v1'})

def clean_str(s):
    return str(s).strip().lower() if s else ""

def style_excel():
    if not os.path.exists(EXCEL_PATH): return
    try:
        wb = load_workbook(EXCEL_PATH); ws = wb.active
        for m_range in list(ws.merged_cells.ranges): ws.unmerge_cells(str(m_range))
        f_n = 'Microsoft JhengHei'; h_f = Font(name=f_n, size=14, bold=True, color="FFFFFF")
        d_f = Font(name=f_n, size=14); h_fill = PatternFill('solid', '1565C0')
        border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
        
        for c in range(1, ws.max_column + 1):
            cell = ws.cell(1, c)
            cell.font = h_f; cell.fill = h_fill; cell.alignment = Alignment('center', 'center', wrap_text=True); cell.border = border
            # 依據內容設定寬度
            ws.column_dimensions[cell.column_letter].width = 45 if cell.value in ['備註', '地址'] else 30
            
            for r in range(2, ws.max_row + 1):
                cell = ws.cell(r, c); cell.font = d_f; cell.border = border
                cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        wb.save(EXCEL_PATH)
    except: pass

def save_to_excel_smart(data):
    """極致去重且支援新欄位"""
    c_name_cn = clean_str(data.get('姓名(中)'))
    c_name_en = clean_str(data.get('姓名(英)'))
    c_comp = clean_str(data.get('公司'))

    if os.path.exists(EXCEL_PATH):
        df = pd.read_excel(EXCEL_PATH).fillna("")
        mask = (
            ((df['姓名(中)'].apply(clean_str) == c_name_cn) & (c_name_cn != "")) | 
            ((df['姓名(英)'].apply(clean_str) == c_name_en) & (c_name_en != ""))
        ) & (df['公司'].apply(clean_str) == c_comp)
        
        match = df[mask]
        if not match.empty:
            print(f"🔄 更新資料: {data['姓名(中)']}")
            idx = match.index[0]
            for key in data.keys():
                if data[key]: df.at[idx, key] = data[key]
            df.to_excel(EXCEL_PATH, index=False)
        else:
            df_new = pd.DataFrame([data])
            pd.concat([df, df_new], ignore_index=True).to_excel(EXCEL_PATH, index=False)
    else:
        pd.DataFrame([data]).to_excel(EXCEL_PATH, index=False)
    style_excel()

def process_contact_file(file_path):
    fn = os.path.basename(file_path)
    if fn.startswith(".") or fn == "人脈總表.xlsx": return
    print(f"📇 執行精確分類辨識: {fn}")
    
    prompt = """
    任務：提取聯絡資訊。
    【欄位規範】：
    1. 姓名：拆分 [姓名(中)] 與 [姓名(英)]。
    2. 稅號：提取統一編號或 Tax ID。
    3. 網址：提取公司官網。
    4. 電話：格式 [手機: xxx\\n公司: xxx]。
    5. 備註：類別化，且每一類之間必須加入「兩個換行符號」以利閱讀。範例:「類別: 內容\\n\\n類別: 內容」。
    
    JSON: {"姓名(中)": "", "姓名(英)": "", "公司": "", "職稱": "", "稅號": "", "網址": "", "電話": "", "Email": "", "地址": "", "備註": ""}
    """
    
    try:
        resp = client.models.generate_content(model="gemini-2.5-flash", contents=[prompt, Image.open(file_path)])
        m = re.search(r'({.*?})', resp.text, re.DOTALL)
        if m:
            data = json.loads(m.group(1))
            save_to_excel_smart(data)
            shutil.move(file_path, os.path.join(BASE_DIR, "processed", fn))
            print(f"✅ 完成")
    except Exception as e: print(f"❌ 錯誤: {e}")

def main():
    files = [os.path.join(BASE_DIR, f) for f in os.listdir(BASE_DIR) if os.path.isfile(os.path.join(BASE_DIR, f)) and not f.startswith(".")]
    for f in files: process_contact_file(f)

if __name__ == "__main__":
    main()
