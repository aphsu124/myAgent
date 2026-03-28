import os
import requests
import datetime
import json
import re
import pandas as pd
import matplotlib.pyplot as plt
import subprocess
from google import genai
from dotenv import load_dotenv

# === 載入環境變數 ===
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
LINE_NOTIFY_TOKEN = os.getenv("LINE_NOTIFY_TOKEN")
REPORT_DIR = os.getenv("REPORT_DIR", "docs/reports")
DATA_DIR = os.getenv("DATA_DIR", "data")
PRICE_DATA_FILE = f"{DATA_DIR}/palm_prices.csv"

# 基礎檢查
if not GEMINI_API_KEY or not SERPER_API_KEY:
    print("❌ 錯誤：請確保在 .env 檔案中填入了 GEMINI_API_KEY 與 SERPER_API_KEY！")
    exit(1)

# 初始化最新版 Gemini Client
client = genai.Client(api_key=GEMINI_API_KEY, http_options={'api_version': 'v1'})

def get_palm_news():
    """使用動態日期搜尋最新泰國棕櫚油資訊，自動過濾過時資料"""
    url = "https://google.serper.dev/search"
    now = datetime.datetime.now()
    curr_year = now.strftime("%Y")
    curr_month_name = now.strftime("%B")
    today_str = now.strftime("%Y-%m-%d")
    
    queries = [
        f"Thailand palm oil FFB CPO price Krabi {today_str}",
        f"Thailand Ministry of Commerce palm oil policy {curr_month_name} {curr_year}",
        f"Thailand crude palm oil export regulation news {curr_year} -2024 -2025"
    ]
    
    headers = {'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'}
    all_results = f"--- 搜尋基準日期: {today_str} ---\n"
    for query in queries:
        payload = {"q": query, "gl": "th", "hl": "en", "tbs": "qdr:m"}
        try:
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                results = response.json()
                for organic in results.get('organic', []):
                    all_results += f"\n[來源日期: {organic.get('date', 'N/A')}] 標題: {organic.get('title')}\n摘要: {organic.get('snippet')}\n"
        except Exception as e:
            print(f"搜尋出錯: {e}")
    return all_results

def extract_data_and_report(raw_data):
    """AI 生成報告與提取價格數據"""
    now = datetime.datetime.now()
    today_full = now.strftime("%Y年%m月%d日")
    curr_year = now.strftime("%Y")
    
    prompt = f"""
    你是一位資深的泰國棕櫚油產業策略師。今天是 {today_full}。
    請根據數據，為一位在泰國甲米(Krabi)經營壓榨廠的老闆撰寫每日簡報。
    基準年是 {curr_year}。請過濾 2024/2025 舊數據。
    
    數據：{raw_data}
    
    輸出格式：Markdown 簡報，結尾需有 DATA_JSON: {{"ffb": 6.5, "cpo": 40.0}}
    """
    
    content = "無法生成 AI 報告，請檢查 API Key 權限。"
    price_data = None
    try:
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        if response and response.text:
            content = response.text
            match = re.search(r'DATA_JSON: ({.*?})', content)
            if match:
                price_data = json.loads(match.group(1))
    except Exception as e:
        print(f"AI 生成出錯: {e}")
    return content, price_data

def save_price_data(price_dict):
    """將價格存入 CSV"""
    if not os.path.exists(DATA_DIR): os.makedirs(DATA_DIR)
    date_today = datetime.datetime.now().strftime("%Y-%m-%d")
    df_new = pd.DataFrame({"Date": [date_today], "FFB": [price_dict.get("ffb", 0)], "CPO": [price_dict.get("cpo", 0)]})
    if os.path.exists(PRICE_DATA_FILE):
        df_old = pd.read_csv(PRICE_DATA_FILE)
        if date_today not in df_old['Date'].values:
            pd.concat([df_old, df_new], ignore_index=True).to_csv(PRICE_DATA_FILE, index=False)
    else:
        df_new.to_csv(PRICE_DATA_FILE, index=False)

def generate_chart():
    """繪製價格趨勢圖"""
    if not os.path.exists(PRICE_DATA_FILE): return None
    df = pd.read_csv(PRICE_DATA_FILE)
    if len(df) < 2: return None
    plt.figure(figsize=(10, 6))
    plt.plot(df['Date'], df['FFB'], marker='o', label='FFB (Baht/kg)', color='green')
    plt.plot(df['Date'], df['CPO'], marker='s', label='CPO (Baht/kg)', color='blue')
    plt.title('Thailand Palm Oil Price Trend (Krabi)', fontsize=14)
    plt.legend(); plt.grid(True); plt.tight_layout()
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    chart_filename = f"palm_chart_{date_str}.png"
    plt.savefig(os.path.join(REPORT_DIR, chart_filename)); plt.close()
    return chart_filename

def send_line_notify(message, image_path=None):
    """發送到 LINE Notify"""
    if not LINE_NOTIFY_TOKEN: return
    url = "https://notify-api.line.me/api/notify"
    headers = {"Authorization": f"Bearer {LINE_NOTIFY_TOKEN}"}
    files = {"imageFile": open(image_path, "rb")} if image_path and os.path.exists(image_path) else None
    try:
        requests.post(url, headers=headers, data={"message": message}, files=files)
        print("✅ LINE 通知已發送！")
    except Exception as e: print(f"LINE 失敗: {e}")

def github_sync(date_str):
    """同步至 GitHub"""
    print("🚀 同步至 GitHub...")
    try:
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", f"📊 Daily Report: {date_str}"], check=True)
        subprocess.run(["git", "push", "origin", "main"], check=True)
        print("✅ GitHub 同步完成！")
    except Exception as e: print(f"❌ GitHub 失敗: {e}")

def main():
    ict_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7)))
    date_today = ict_now.strftime("%Y-%m-%d")
    if ict_now.hour < 13 or (ict_now.hour == 13 and ict_now.minute < 30):
        print("⏳ 泰國時間尚未 13:30，跳過。"); return
    
    filename = f"{REPORT_DIR}/palm_oil_report_{date_today}.md"
    if os.path.exists(filename):
        print(f"✅ 今日報告已存在。"); return

    print("🚀 開始執行每日分析任務...")
    raw_data = get_palm_news()
    content, price_data = extract_data_and_report(raw_data)
    
    chart_file = None
    if price_data:
        save_price_data(price_data)
        chart_file = generate_chart()

    full_report = content + (f"\n\n## 📈 價格趨勢\n![Trend]({chart_file})" if chart_file else "")
    with open(filename, "w", encoding="utf-8") as f: f.write(full_report)

    # 發送通知
    msg = f"\n📊 泰國棕櫚油簡報 ({date_today})\n"
    if price_data: msg += f"🔸 FFB: {price_data.get('ffb')} 泰銖/kg\n🔸 CPO: {price_data.get('cpo')} 泰銖/kg"
    send_line_notify(msg, os.path.join(REPORT_DIR, chart_file) if chart_file else None)
    
    # 同步雲端
    github_sync(date_today)

if __name__ == "__main__":
    main()
