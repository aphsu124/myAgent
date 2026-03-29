import os
import json
import datetime
import requests
import pandas as pd
from pythainlp.tokenize import word_tokenize
from pythainlp.corpus import thai_stopwords
from google import genai
from dotenv import load_dotenv
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# === 配置區 ===
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ICLOUD_PATH = "/Users/bucksteam/Library/Mobile Documents/com~apple~CloudDocs/泰國/工作/甲米油廠/會議"
VOCAB_DB = "data/thai_vocab.json"
CHINESE_FONT = "/System/Library/Fonts/STHeiti Light.ttc"
THAI_FONT = "/Library/Fonts/Arial Unicode.ttf" # 通用泰文支持

# 初始化 Gemini
client = genai.Client(api_key=GEMINI_API_KEY, http_options={'api_version': 'v1'})

try:
    pdfmetrics.registerFont(TTFont('ThaiFont', '/System/Library/Fonts/KohinoorBangla.ttc')) # macOS 泰文字型
    HAS_FONTS = True
except:
    HAS_FONTS = False

def update_vocab_db(thai_text):
    """分析泰文分詞，過濾停用詞，更新數據庫"""
    if not os.path.exists("data"): os.makedirs("data")
    
    # 讀取現有單字本
    vocab = {}
    if os.path.exists(VOCAB_DB):
        with open(VOCAB_DB, 'r', encoding='utf-8') as f:
            vocab = json.load(f)
    
    # 分詞並過濾
    tokens = word_tokenize(thai_text, engine="newmm")
    stopwords = thai_stopwords()
    
    new_words = []
    for word in tokens:
        word = word.strip()
        if len(word) > 1 and word not in stopwords and not word.isnumeric():
            if word in vocab:
                vocab[word]["count"] += 1
            else:
                vocab[word] = {"count": 1, "translation": "", "example": ""}
                new_words.append(word)
    
    # 針對新單字，使用 AI 進行批量翻譯與例句生成
    if new_words:
        print(f"🔍 發現 {len(new_words)} 個新泰文單字，正在翻譯中...")
        prompt = f"請將以下泰文單字翻譯成繁體中文，並各提供一個與「棕櫚油工廠營運」相關的簡單例句。格式：JSON {{'單字': {{'trans': '中文', 'ex': '例句'}}}} \n單字列表：{new_words[:20]}"
        try:
            resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
            # 這裡簡化處理，實際建議解析 JSON
            # vocab 更新邏輯...
        except: pass

    with open(VOCAB_DB, 'w', encoding='utf-8') as f:
        json.dump(vocab, f, ensure_ascii=False, indent=2)
    return vocab

def generate_vocab_pdf(vocab_data):
    """生成泰文學習單字本 PDF"""
    pdf_path = os.path.join(ICLOUD_PATH, "泰文學習/泰國商務單字本_最新版.pdf")
    c = canvas.Canvas(pdf_path, pagesize=A4)
    font_name = 'ThaiFont' if HAS_FONTS else 'Helvetica'
    
    c.setFont(font_name, 20)
    c.drawString(50, 800, "🗂️ 泰國甲米油廠 - 商務泰文單字本")
    c.setFont(font_name, 10)
    c.drawString(50, 780, f"更新日期: {datetime.datetime.now().strftime('%Y-%m-%d')}")
    c.line(50, 770, 550, 770)
    
    # 按照詞頻排序
    sorted_vocab = sorted(vocab_data.items(), key=lambda x: x[1]['count'], reverse=True)
    
    y = 740
    for word, info in sorted_vocab[:50]: # 取前50個常用字
        if y < 100:
            c.showPage()
            y = 800
        c.setFont(font_name, 14)
        c.drawString(50, y, f"{word}")
        c.setFont(font_name, 10)
        c.drawString(150, y, f"出現次數: {info['count']} | 翻譯: {info.get('translation', '待更新')}")
        y -= 25
        
    c.save()
    print(f"✅ 泰文單字本已更新: {pdf_path}")

def main():
    # 模擬流程：
    # 1. 掃描 iCloud/錄音 資料夾中的新音檔
    # 2. 調用 OpenAI Whisper API 轉錄 (這裡需 API Key)
    # 3. 獲取泰文文本
    # 4. 執行 update_vocab_db
    # 5. 執行 generate_vocab_pdf
    
    print("🚀 會議處理系統已啟動，正在等待新錄音檔...")
    # 此處為未來擴充預留
    pass

if __name__ == "__main__":
    main()
