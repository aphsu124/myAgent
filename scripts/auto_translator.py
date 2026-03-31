import os
import shutil
import re
import fitz
import anthropic
from google import genai
from dotenv import load_dotenv
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

load_dotenv()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
BASE_DIR = "/Users/bucksteam/Library/Mobile Documents/com~apple~CloudDocs/翻譯"
FONT_PATH = '/System/Library/Fonts/STHeiti Light.ttc'

pdfmetrics.registerFont(TTFont('Chinese', FONT_PATH))

client_claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
client_gemini = genai.Client(api_key=GEMINI_API_KEY, http_options={'api_version': 'v1'})

def generate_pdf(text, save_path, title):
    try:
        doc = SimpleDocTemplate(save_path, pagesize=A4)
        p_style = ParagraphStyle('CN', fontName='Chinese', fontSize=11, leading=16, spaceAfter=8)
        t_style = ParagraphStyle('T', fontName='Chinese', fontSize=16, leading=22, alignment=1, spaceAfter=20)
        story = [Paragraph(title, t_style), Spacer(1, 12)]
        for p in text.split('\n'):
            if p.strip():
                story.append(Paragraph(p.replace("<", "&lt;").replace(">", "&gt;"), p_style))
        doc.build(story)
        return True
    except: return False

def process_file(file_path):
    fn = os.path.basename(file_path)
    if fn.startswith(".") or not fn.lower().endswith(".pdf"): return
    
    print(f"📄 正在全量翻譯: {fn}")
    try:
        doc = fitz.open(file_path)
        content = "".join([page.get_text() for page in doc])
        doc.close()
        
        prompt = f"你是一位法律翻譯專家。請將以下內容完整翻譯成繁體中文，保留所有編號格式。\n\n內容：\n{content}"
        
        translated_text = None
        # 嘗試 Claude (多重探路者模式)
        try:
            print("  嘗試使用 Claude 3.5 Sonnet (20240620)...")
            message = client_claude.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )
            translated_text = message.content[0].text
        except Exception as e:
            print(f"  ❌ Claude 3.5 失敗，嘗試 Claude 3 Sonnet... ({e})")
            try:
                message = client_claude.messages.create(
                    model="claude-3-sonnet-20240229",
                    max_tokens=4096,
                    messages=[{"role": "user", "content": prompt}]
                )
                translated_text = message.content[0].text
            except:
                # 終極備援
                print("  ⚠️ Claude 全線受限，切換至 Gemini 2.5-Flash 進行翻譯...")
                resp = client_gemini.models.generate_content(model="gemini-2.5-flash", contents=prompt)
                translated_text = resp.text

        if translated_text:
            target = "日文" if any(k in translated_text for k in ["日", "日本"]) else "其他"
            out_path = os.path.join(BASE_DIR, target, f"中文版_{fn}")
            if generate_pdf(translated_text, out_path, f"翻譯：{fn}"):
                proc_dir = os.path.join(BASE_DIR, "processed")
                if not os.path.exists(proc_dir): os.makedirs(proc_dir)
                shutil.move(file_path, os.path.join(proc_dir, fn))
                print(f"✅ 翻譯成功！存入: {target}")
            
    except Exception as e: print(f"❌ 翻譯出錯: {e}")

def main():
    print("🕵️ Jarvis 智慧翻譯中心 [雙引擎版] 啟動中...")
    # 這裡加入容錯，即使在 crontab 下也能報錯
    try:
        files = [os.path.join(BASE_DIR, f) for f in os.listdir(BASE_DIR) if os.path.isfile(os.path.join(BASE_DIR, f)) and f.lower().endswith('.pdf')]
        for f in files: process_file(f)
    except Exception as e:
        print(f"目錄存取失敗: {e}")

if __name__ == "__main__":
    main()
