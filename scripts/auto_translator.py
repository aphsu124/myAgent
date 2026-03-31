import os
import shutil
import datetime
import re
import fitz  
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from google import genai
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
BASE_DIR = "/Users/bucksteam/Library/Mobile Documents/com~apple~CloudDocs/翻譯"
FONT_PATH = "/System/Library/Fonts/STHeiti Light.ttc"
MY_FONT = fm.FontProperties(fname=FONT_PATH)

client = genai.Client(api_key=GEMINI_API_KEY, http_options={'api_version': 'v1'})

def generate_pdf(text, save_path, title):
    fig, ax = plt.subplots(figsize=(8.27, 11.69))
    ax.axis('off')
    y = 0.95
    plt.text(0.5, y, title, fontproperties=MY_FONT, fontsize=16, ha='center', weight='bold')
    y -= 0.05
    lines = text.split('\n')
    for line in lines:
        if not line.strip(): continue
        content = line.strip()
        while len(content) > 0:
            plt.text(0.1, y, content[:45], fontproperties=MY_FONT, fontsize=11)
            content = content[45:]
            y -= 0.025
            if y < 0.05: break
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()

def extract_pdf_text(file_path):
    try:
        doc = fitz.open(file_path)
        text = "".join([page.get_text() for page in doc])
        doc.close()
        return text
    except: return None

def process_file(file_path):
    filename = os.path.basename(file_path)
    if filename.startswith(".") or not filename.lower().endswith(".pdf"): return
    
    print(f"📄 偵測到檔案，開始處理: {filename}")
    content = extract_pdf_text(file_path)
    if not content or len(content.strip()) < 5:
        print("⚠️ 無法讀取文字內容。")
        return

    prompt = f"任務：將此 PDF 翻譯成繁體中文。辨識語言(Thai, English, Japanese, Other)。標題建議。格式：\n語言: [Lang]\n標題: [Title]\n內容: [Content]\n\n內容：{content[:3000]}"
    
    try:
        resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        res = resp.text
        
        lang = re.search(r"語言: (.*)", res).group(1).strip() if re.search(r"語言: (.*)", res) else "其他"
        title = re.search(r"標題: (.*)", res).group(1).strip() if re.search(r"標題: (.*)", res) else filename
        translated = re.search(r"內容: (.*)", res, re.DOTALL).group(1).strip() if re.search(r"內容: (.*)", res, re.DOTALL) else res
        
        # 歸檔路徑
        target = "其他"
        if any(k in lang for k in ["Thai", "泰"]): target = "泰文"
        elif any(k in lang for k in ["Eng", "英"]): target = "英文"
        elif any(k in lang for k in ["Jap", "日"]): target = "日文"
        
        out_name = f"中文版_{filename}"
        out_path = os.path.join(BASE_DIR, target, out_name)
        generate_pdf(translated, out_path, title)
        
        # 歸檔原檔 (若 processed 資料夾不存在則建立)
        proc_dir = os.path.join(BASE_DIR, "processed")
        if not os.path.exists(proc_dir): os.makedirs(proc_dir)
        shutil.move(file_path, os.path.join(proc_dir, filename))
        print(f"✅ 成功歸檔至: {target}")
    except Exception as e: print(f"❌ 錯誤: {e}")

def main():
    print("🕵️ Jarvis 智慧翻譯中心監聽中...")
    # 列出根目錄下所有非隱藏檔案
    all_files = [os.path.join(BASE_DIR, f) for f in os.listdir(BASE_DIR) if os.path.isfile(os.path.join(BASE_DIR, f)) and not f.startswith(".")]
    if not all_files:
        print("📭 目前沒有待處理的檔案。")
    for f in all_files:
        process_file(f)

if __name__ == "__main__":
    main()
