import os
import json
import datetime
import re
import shutil
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from pythainlp.tokenize import word_tokenize
from google import genai
from openai import OpenAI
from dotenv import load_dotenv

# === 配置區 ===
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
from modules.config import STORAGE_BACKEND, GDRIVE_FOLDER_MEETING

ICLOUD_BASE = "/Users/bucksteam/Library/Mobile Documents/com~apple~CloudDocs/泰國/工作/甲米油廠/會議"
VOCAB_DB = "data/thai_vocab.json"

# 字體設定
FONT_PATH = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"
MY_FONT = fm.FontProperties(fname=FONT_PATH)

# 初始化 Clients
client_gemini = genai.Client(api_key=GEMINI_API_KEY, http_options={'api_version': 'v1'})
client_openai = OpenAI(api_key=OPENAI_API_KEY)

def transcribe_audio(file_path):
    print(f"🎙️ 正在轉錄音檔: {os.path.basename(file_path)}...")
    try:
        with open(file_path, "rb") as audio:
            transcript = client_openai.audio.transcriptions.create(
                model="whisper-1",
                file=audio,
                language="th"
            )
            return transcript.text
    except Exception as e:
        print(f"❌ 轉錄失敗: {e}")
        return None

def _save_text(content, filename):
    """依照 STORAGE_BACKEND 儲存文字檔（Drive 或本機）"""
    if STORAGE_BACKEND == 'gdrive' and GDRIVE_FOLDER_MEETING:
        from modules.gdrive_utils import upload_bytes
        upload_bytes(content.encode('utf-8'), filename, GDRIVE_FOLDER_MEETING, "text/plain")
        print(f"⬆️  已上傳至 Drive：{filename}")
    else:
        summary_dir = os.path.join(ICLOUD_BASE, "摘要")
        os.makedirs(summary_dir, exist_ok=True)
        path = os.path.join(summary_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"📄 已儲存至本機：{path}")

def generate_simple_summary(thai_text, filename):
    """針對個人用途檔案：僅做內容摘要"""
    print("📝 偵測為個人用途，僅進行內容摘要...")
    prompt = f"請將以下泰文內容翻譯並摘要為繁體中文重點：\n\n{thai_text}"
    try:
        resp = client_gemini.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        try:
            from modules.token_tracker import record as _tt
            _tt('google', 'gemini-2.5-flash', resp.usage_metadata.prompt_token_count or 0, resp.usage_metadata.candidates_token_count or 0)
        except Exception: pass
        _save_text(resp.text, f"{filename}_內容摘要.txt")
    except Exception as e:
        print(f"AI 摘要失敗: {e}")

def generate_business_report(thai_text, filename):
    """針對商務會議：生成完整分析並更新單字本"""
    print("💼 正在執行商務會議完整處理 (含單字更新)...")
    prompt = f"""
    你是資深特助。請針對這段泰國油廠會議逐字稿進行：
    1. 繁體中文摘要。
    2. 提取 Action Items。
    3. 提取 10 個核心泰文單字並翻譯。
    格式要求：最後務必包含 DATA_JSON: {{"vocab": {{"泰文": "中文"}}}}
    逐字稿：{thai_text}
    """
    try:
        resp = client_gemini.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        try:
            from modules.token_tracker import record as _tt
            _tt('google', 'gemini-2.5-flash', resp.usage_metadata.prompt_token_count or 0, resp.usage_metadata.candidates_token_count or 0)
        except Exception: pass
        content = resp.text
        _save_text(content, f"{filename}_會議摘要.txt")

        match = re.search(r'DATA_JSON: ({.*?})', content, re.DOTALL)
        if match:
            new_vocab = json.loads(match.group(1)).get("vocab", {})
            update_db_with_new_words(new_vocab)
            generate_vocab_pdf_final()
    except Exception as e:
        print(f"商務分析失敗: {e}")

def update_db_with_new_words(new_vocab_map):
    if not os.path.exists("data"): os.makedirs("data")
    db = {}
    if os.path.exists(VOCAB_DB):
        with open(VOCAB_DB, 'r', encoding='utf-8') as f: db = json.load(f)
    for th, cn in new_vocab_map.items():
        if th in db: db[th]["count"] += 1
        else: db[th] = {"count": 1, "translation": cn}
    with open(VOCAB_DB, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

def generate_vocab_pdf_final():
    if not os.path.exists(VOCAB_DB): return
    with open(VOCAB_DB, 'r', encoding='utf-8') as f:
        vocab_data = json.load(f)
    pdf_filename = "泰國商務單字本_最新版.pdf"
    pdf_path = f"/tmp/{pdf_filename}"
    sorted_vocab = sorted(vocab_data.items(), key=lambda x: x[1]['count'], reverse=True)[:50]
    fig, ax = plt.subplots(figsize=(10, 14)); ax.axis('off')
    plt.text(0.5, 0.98, "🗂️ 泰國甲米油廠 - 商務泰文單字本", fontproperties=MY_FONT, fontsize=20, ha='center', color='#2E7D32')
    plt.text(0.05, 0.93, "泰文單字 (Thai)", fontproperties=MY_FONT, fontsize=14, weight='bold')
    plt.text(0.50, 0.93, "中文翻譯 (Chinese)", fontproperties=MY_FONT, fontsize=14, weight='bold')
    plt.axhline(0.92, 0.05, 0.95, color='black', lw=1)
    y = 0.89
    for word, info in sorted_vocab:
        plt.text(0.05, y, word, fontproperties=MY_FONT, fontsize=15, color='#1B5E20')
        plt.text(0.50, y, info.get('translation', ''), fontproperties=MY_FONT, fontsize=12)
        y -= 0.025
        if y < 0.05: break
    plt.savefig(pdf_path, dpi=300, bbox_inches='tight'); plt.close()

    if STORAGE_BACKEND == 'gdrive' and GDRIVE_FOLDER_MEETING:
        from modules.gdrive_utils import upload_file
        upload_file(pdf_path, GDRIVE_FOLDER_MEETING, "application/pdf")
        print(f"📚 單字本 PDF 已上傳至 Drive")
    else:
        vocab_dir = os.path.join(ICLOUD_BASE, "泰文學習")
        os.makedirs(vocab_dir, exist_ok=True)
        shutil.copy(pdf_path, os.path.join(vocab_dir, pdf_filename))
        print(f"📚 單字本 PDF 已存至本機")

def main():
    if STORAGE_BACKEND == 'gdrive' and GDRIVE_FOLDER_MEETING:
        from modules.gdrive_utils import list_files_in_folder, download_file, upload_bytes, delete_file
        audio_exts = ('.mp3', '.m4a', '.wav')
        files = list_files_in_folder(GDRIVE_FOLDER_MEETING)
        audio_files = [f for f in files if any(f['name'].lower().endswith(ext) for ext in audio_exts)]
        if not audio_files:
            print("📭 Drive 會議資料夾目前沒有新音檔。")
            return
        for f in audio_files:
            tmp_path = f"/tmp/{f['name']}"
            if download_file(f['id'], tmp_path):
                text = transcribe_audio(tmp_path)
                if text:
                    # 上傳逐字稿
                    upload_bytes(text.encode('utf-8'), f"{f['name']}_逐字稿.txt", GDRIVE_FOLDER_MEETING, "text/plain")
                    print(f"📄 逐字稿已上傳至 Drive")
                    if "品川" in f['name']:
                        generate_simple_summary(text, f['name'])
                    else:
                        generate_business_report(text, f['name'])
                    # 刪除來源音檔
                    delete_file(f['id'])
                    print(f"✅ 檔案 {f['name']} 已完成智慧處理並從 Drive 刪除。")
                try: os.remove(tmp_path)
                except: pass
    else:
        record_dir = os.path.join(ICLOUD_BASE, "錄音")
        transcript_dir = os.path.join(ICLOUD_BASE, "逐字稿")
        processed_dir = os.path.join(record_dir, "processed")
        os.makedirs(processed_dir, exist_ok=True)
        os.makedirs(transcript_dir, exist_ok=True)

        audio_files = [f for f in os.listdir(record_dir) if f.lower().endswith(('.mp3', '.m4a', '.wav'))]
        if not audio_files:
            print("📭 錄音資料夾目前沒有新檔案。")
            return

        for file in audio_files:
            full_path = os.path.join(record_dir, file)
            text = transcribe_audio(full_path)
            if text:
                transcript_path = os.path.join(transcript_dir, f"{file}_逐字稿.txt")
                with open(transcript_path, "w", encoding="utf-8") as f:
                    f.write(text)
                print(f"📄 原始泰文逐字稿已存至: {transcript_path}")
                if "品川" in file:
                    generate_simple_summary(text, file)
                else:
                    generate_business_report(text, file)
                shutil.move(full_path, os.path.join(processed_dir, file))
                print(f"✅ 檔案 {file} 已完成智慧處理並歸檔。")

if __name__ == "__main__":
    main()
