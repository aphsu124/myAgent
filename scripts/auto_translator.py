import os
import re
import fitz
import io
import json
from PIL import Image
from google import genai
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
from modules.config import STORAGE_BACKEND, GDRIVE_FOLDER_TRANSLATE

client_gemini = genai.Client(api_key=GEMINI_API_KEY, http_options={'api_version': 'v1'})

def process_file_with_layout(file_path, file_id=None):
    fn = os.path.basename(file_path)
    print(f"🎨 [視覺佈局模式] 正在複刻原件風格: {fn}")

    # 1. 轉換 PDF 為圖片供 AI 參考樣式
    doc = fitz.open(file_path)
    pix = doc[0].get_pixmap(matrix=fitz.Matrix(2, 2))
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    doc.close()

    # 2. 調用 Gemini 同時進行翻譯與 CSS 佈局建模
    prompt = """
    任務：將這份文件內容翻譯成繁體中文，並產出一個【單頁 HTML】來複刻原件的視覺佈局。

    要求：
    1. 使用內聯 CSS (Inline CSS) 來設定佈局。
    2. 模仿原件的字體大小、加粗、文字位置 (左、中、右對齊) 與表格結構。
    3. 背景設為白色，文字設為黑色。
    4. 必須使用 "Microsoft JhengHei" 或 "PingFang TC" 作為字體。
    5. 只回傳完整的 HTML 程式碼，不要有其他廢話。
    """

    try:
        resp = client_gemini.models.generate_content(model="gemini-2.5-flash", contents=[prompt, img])
        try:
            from modules.token_tracker import record as _tt
            _tt('google', 'gemini-2.5-flash', resp.usage_metadata.prompt_token_count or 0, resp.usage_metadata.candidates_token_count or 0)
        except Exception: pass
        html_match = re.search(r"<html>.*</html>", resp.text, re.DOTALL | re.IGNORECASE)
        html_code = html_match.group(0) if html_match else resp.text

        out_filename = f"佈局還原_{fn}.html"

        if STORAGE_BACKEND == 'gdrive' and GDRIVE_FOLDER_TRANSLATE:
            from modules.gdrive_utils import upload_bytes, delete_file
            upload_bytes(html_code.encode('utf-8'), out_filename, GDRIVE_FOLDER_TRANSLATE, "text/html")
            print(f"✅ 佈局還原成功！已上傳至 Google Drive：{out_filename}")
            # 刪除來源檔（已處理）
            if file_id:
                delete_file(file_id)
                print(f"🗑️  來源檔已從 Drive 刪除：{fn}")
        else:
            base_dir = "/Users/bucksteam/Library/Mobile Documents/com~apple~CloudDocs/翻譯"
            out_html_path = os.path.join(base_dir, f"佈局還原_{fn}.html")
            with open(out_html_path, "w", encoding="utf-8") as f:
                f.write(html_code)
            proc_dir = os.path.join(base_dir, "processed")
            if not os.path.exists(proc_dir): os.makedirs(proc_dir)
            import shutil
            shutil.move(file_path, os.path.join(proc_dir, fn))
            print(f"✅ 佈局還原成功！已產出網頁版報告：{out_html_path}")

    except Exception as e:
        print(f"❌ 佈局還原失敗: {e}")

def main():
    print("🕵️ Jarvis 智慧翻譯中心 [風格複刻版] 啟動中...")

    if STORAGE_BACKEND == 'gdrive' and GDRIVE_FOLDER_TRANSLATE:
        from modules.gdrive_utils import list_files_in_folder, download_file
        files = list_files_in_folder(GDRIVE_FOLDER_TRANSLATE, ['.pdf'])
        if not files:
            print("📂 Drive 翻譯資料夾中無待處理 PDF。")
            return
        for f in files:
            tmp_path = f"/tmp/{f['name']}"
            if download_file(f['id'], tmp_path):
                process_file_with_layout(tmp_path, file_id=f['id'])
                try: os.remove(tmp_path)
                except: pass
    else:
        base_dir = "/Users/bucksteam/Library/Mobile Documents/com~apple~CloudDocs/翻譯"
        files = [os.path.join(base_dir, f) for f in os.listdir(base_dir) if os.path.isfile(os.path.join(base_dir, f)) and f.lower().endswith('.pdf')]
        for f in files:
            process_file_with_layout(f)

if __name__ == "__main__":
    main()
