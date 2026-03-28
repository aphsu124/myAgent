import os
from google import genai
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# 初始化 Client
client = genai.Client(api_key=GEMINI_API_KEY, http_options={'api_version': 'v1'})

print("🔍 正在查詢您的 API Key 支援的所有模型名稱...")

try:
    # 取得模型列表
    models = client.models.list()
    print("\n✅ 查詢成功，模型清單如下：")
    print("-" * 30)
    for model in models:
        # 由於新 SDK 的屬性可能不同，我們直接印出名稱
        print(f"👉 {model.name}")
    print("-" * 30)
except Exception as e:
    print(f"❌ 查詢失敗：{e}")
