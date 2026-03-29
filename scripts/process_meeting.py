import os
import json
import datetime
import re
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from pythainlp.tokenize import word_tokenize
from google import genai
from dotenv import load_dotenv

# === 配置區 ===
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ICLOUD_PATH = "/Users/bucksteam/Library/Mobile Documents/com~apple~CloudDocs/泰國/工作/甲米油廠/會議"
VOCAB_DB = "data/thai_vocab.json"

# 使用 macOS 內建支援泰文與中文的字型
FONT_PATH = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf" 
if not os.path.exists(FONT_PATH):
    FONT_PATH = "/System/Library/Fonts/STHeiti Light.ttc" # 備選

MY_FONT = fm.FontProperties(fname=FONT_PATH)
client = genai.Client(api_key=GEMINI_API_KEY, http_options={'api_version': 'v1'})

def translate_new_words(vocab):
    words_to_trans = [w for w, info in vocab.items() if info.get('translation') in ["待翻譯", "待更新", ""]]
    if not words_to_trans: return vocab
    
    print(f"🤖 正在為 {len(words_to_trans)} 個新單字請求 AI 翻譯...")
    prompt = f"請將以下泰文單字翻譯成繁體中文。只回傳 JSON 格式 {{\"單字\": \"翻譯\"}}。列表：{words_to_trans[:20]}"
    try:
        resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        json_match = re.search(r'({.*})', resp.text, re.DOTALL)
        if json_match:
            trans_map = json.loads(json_match.group(1))
            for word, trans in trans_map.items():
                if word in vocab: vocab[word]['translation'] = trans
    except Exception as e:
        print(f"翻譯出錯: {e}")
    return vocab

def generate_vocab_pdf_with_plot(vocab_data):
    """利用 Matplotlib 繪製完美的 PDF 報表"""
    pdf_path = os.path.join(ICLOUD_PATH, "泰文學習/泰國商務單字本_最新版.pdf")
    if not os.path.exists(os.path.dirname(pdf_path)): os.makedirs(os.path.dirname(pdf_path))
    
    # 準備數據並排序
    sorted_vocab = sorted(vocab_data.items(), key=lambda x: x[1]['count'], reverse=True)[:40]
    
    fig, ax = plt.subplots(figsize=(10, 14))
    ax.axis('off')
    
    # 標題
    plt.text(0.5, 0.98, "🗂️ 泰國甲米油廠 - 商務泰文單字本", fontproperties=MY_FONT, 
             fontsize=20, ha='center', color='#2E7D32')
    plt.text(0.95, 0.96, f"更新日期: {datetime.datetime.now().strftime('%Y-%m-%d')}", 
             fontproperties=MY_FONT, fontsize=10, ha='right', color='gray')
    
    # 表頭
    plt.text(0.05, 0.93, "泰文單字 (Thai Vocabulary)", fontproperties=MY_FONT, fontsize=14, weight='bold')
    plt.text(0.50, 0.93, "中文翻譯 (Chinese Translation)", fontproperties=MY_FONT, fontsize=14, weight='bold')
    plt.axhline(0.92, 0.05, 0.95, color='black', lw=1)
    
    # 填入單字
    y = 0.89
    for word, info in sorted_vocab:
        # 泰文
        plt.text(0.05, y, word, fontproperties=MY_FONT, fontsize=15, color='#1B5E20')
        # 中文
        trans = info.get('translation', '待更新')
        plt.text(0.50, y, trans, fontproperties=MY_FONT, fontsize=12)
        
        y -= 0.025 # 稍微加大行距，視覺更舒服
        if y < 0.05: break 
        
    plt.savefig(pdf_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✅ 完美 PDF 已產出: {pdf_path}")

def main():
    print("🚀 啟動泰文單字本生成 (繪圖引擎版)...")
    if not os.path.exists("data"): os.makedirs("data")
    vocab = {}
    if os.path.exists(VOCAB_DB):
        with open(VOCAB_DB, 'r', encoding='utf-8') as f: vocab = json.load(f)
    
    # 模擬數據確保內容豐富
    sample = "น้ำมันปาล์ม การผลิต กระบี่ ราคา สต็อก โรงงาน ตลาด การขนส่ง กำไร ขาดทุน พนักงาน การซ่อมแซม"
    tokens = word_tokenize(sample, engine="newmm")
    for word in tokens:
        word = word.strip()
        if len(word) > 1:
            if word in vocab: vocab[word]["count"] += 1
            else: vocab[word] = {"count": 1, "translation": ""}
    
    vocab = translate_new_words(vocab)
    with open(VOCAB_DB, 'w', encoding='utf-8') as f: json.dump(vocab, f, ensure_ascii=False, indent=2)
    
    generate_vocab_pdf_with_plot(vocab)

if __name__ == "__main__":
    main()
