import cv2
import os
import time
import datetime
from PIL import Image
from google import genai
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
LOCAL_IMG_DIR = "data/snapshots"

from modules.config import STORAGE_BACKEND, GDRIVE_FOLDER_MONITOR

# 初始化 Gemini
client = genai.Client(api_key=GEMINI_API_KEY, http_options={'api_version': 'v1'})

def capture_frame(camera_url):
    """強化版截取：包含暖身與緩衝清空"""
    if not os.path.exists(LOCAL_IMG_DIR): os.makedirs(LOCAL_IMG_DIR)
    
    cap = cv2.VideoCapture(camera_url)
    if not cap.isOpened():
        print("❌ 無法連線至攝影機。")
        return None
    
    print("⏳ 攝影機暖身中 (2秒)...")
    time.sleep(2)
    
    # 連續讀取幾張圖以清空緩衝區
    for _ in range(5):
        ret, frame = cap.read()
    
    cap.release()
    
    if ret:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"snapshot_{timestamp}.jpg"
        
        # 本地備份
        local_path = os.path.join(LOCAL_IMG_DIR, filename)
        cv2.imwrite(local_path, frame)

        try:
            if STORAGE_BACKEND == 'gdrive' and GDRIVE_FOLDER_MONITOR:
                from modules.gdrive_utils import upload_file
                upload_file(local_path, GDRIVE_FOLDER_MONITOR, "image/jpeg")
                print(f"📸 截圖成功！已上傳至 Google Drive 與本地。")
            else:
                icloud_dir = "/Users/bucksteam/Library/Mobile Documents/com~apple~CloudDocs/泰國/工作/甲米油廠/監控/截圖"
                if os.path.exists(icloud_dir):
                    cv2.imwrite(os.path.join(icloud_dir, filename), frame)
                    print(f"📸 截圖成功！已存至 iCloud 與本地。")
        except Exception as e:
            print(f"⚠️ 備份失敗，僅保留本地: {e}")
        return local_path
    return None

def analyze_image(image_path):
    print("🤖 AI 正在進行深度物件辨識...")
    img = Image.open(image_path)
    prompt = "請詳細描述這張照片中的物件、場景、以及是否有任何異常。請用繁體中文回報。"
    
    try:
        resp = client.models.generate_content(model="gemini-2.5-flash", contents=[prompt, img])
        try:
            from modules.token_tracker import record as _tt
            _tt('google', 'gemini-2.5-flash', resp.usage_metadata.prompt_token_count or 0, resp.usage_metadata.candidates_token_count or 0)
        except Exception: pass
        print(f"✅ AI 分析結果：\n{resp.text}")
        return resp.text
    except Exception as e:
        print(f"❌ AI 分析失敗: {e}")
        return None

if __name__ == "__main__":
    # 使用 0 (內建) 或您的攝影機位址
    CAMERA_URL = 0
    path = capture_frame(CAMERA_URL)
    if path:
        analyze_image(path)
