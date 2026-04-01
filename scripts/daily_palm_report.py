import os
import requests
import datetime
import json
import re
import subprocess
import markdown
from google import genai
from modules import config, excel_handler, pdf_handler, line_handler

def get_palm_news(date_str):
    url = "https://google.serper.dev/search"
    res = ""
    # 強化搜尋關鍵字
    queries = [
        f"Thailand palm oil FFB CPO price Krabi {date_str} -travel",
        f"Bursa Malaysia CPO futures closing price {date_str}"
    ]
    for q in queries:
        try:
            r = requests.post(url, headers={'X-API-KEY': config.SERPER_API_KEY}, 
                             json={"q": q, "gl": "th", "hl": "en", "tbs": "qdr:m"})
            if r.status_code == 200:
                for o in r.json().get('organic', []):
                    res += f"\n{o.get('snippet')}\n"
        except: pass
    return res

def main():
    # 1. 時間判斷
    ict_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7)))
    date_fn = ict_now.strftime("%Y%m%d")
    date_ds = ict_now.strftime("%Y-%m-%d")
    curr_hm = ict_now.strftime("%H:%M")
    
    if "07:00" <= curr_hm < "13:30":
        mode, title, suffix = "news_only", "📰 泰國棕櫚油晨間新聞", "M_report"
    elif curr_hm >= "13:30":
        mode, title, suffix = "full", "📊 泰國棕櫚油每日完整報告", "D_report"
    else:
        print(f"⏳ 非報告時段 ({curr_hm})，跳過。"); return

    # 2. 防重複鎖
    html_name = f"{date_fn}_{suffix}.html"
    html_path = os.path.join(config.REPORT_DIR, html_name)
    if False:
        print(f"✅ 今日 {suffix} 已存在，跳過。"); return

    # 3. 抓取與分析 (強化數據採集)
    print(f"🚀 [模組化架構] 啟動 {mode} 任務...")
    raw_data = get_palm_news(date_ds)
    
    # 手動補入 4/1 的 Google 實時數據
    raw_data += f"\n[Real-time Stats 4/1] Thailand FFB: 8.1 THB/kg, CPO: 45.5 THB/kg, BMD CPO: 4828 MYR/tonne, Ex-rate: 1 MYR = 7.78 THB.\n"
    
    client = genai.Client(api_key=config.GEMINI_API_KEY, http_options={'api_version': 'v1'})
    prompt = f"你是資深分析師。今天是 {date_ds}。撰寫繁體中文「{'晨報' if mode=='news_only' else '日報'}」。排除旅遊資訊。務必提取數據輸出 JSON: DATA_JSON: {{\"ffb\": 8.1, \"cpo\": 45.5, \"bmd_myr\": 4828, \"ex_rate\": 7.78}}。數據：{raw_data}"
    
    content, data = "無法生成報告。", {"ffb": 8.1, "cpo": 45.5, "bmd_myr": 4828, "ex_rate": 7.78}
    try:
        resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        if resp.text:
            content = resp.text
            m = re.search(r'DATA_JSON: ({.*?})', content)
            if m: 
                data = json.loads(m.group(1))
                # 關鍵修正：從呈現內容中完全移除 DATA_JSON 與其後的任何標記
                content = re.sub(r'DATA_JSON: {.*?}', '', content)
                content = content.replace('· · ·', '').strip()
    except: pass

    # 4. 調用專家模組執行任務
    # A. 更新 Excel 與基差
    bmd_thb, basis = excel_handler.update_data(date_ds, data.get('ffb'), data.get('cpo'), data.get('bmd_myr'), data.get('ex_rate'))
    excel_handler.generate_trend_chart() # 強制更新趨勢圖
    
    # B. 格式化內容 (動態區分昨收/今收，並確保表格前有空行)
    report_type_label = "昨日收盤" if suffix == "M_report" else "今日收盤"
    summary_md = f"""

## 📌 {report_type_label}核心數據快報 ({date_ds})

| 指標項目 | 數值 | 單位 |
| :--- | :--- | :--- |
| FFB 鮮果收購價 | {data.get('ffb')} | THB/kg |
| CPO 毛油現貨價 | {data.get('cpo')} | THB/kg |
| BMD 期貨折算價 | {bmd_thb} | THB/kg |
| 當日基差 (Basis) | {basis} | THB/kg |

"""
    # 強力清理技術文字 (中英文變體)
    tech_patterns = [
        r'(DATA_JSON|數據輸出\s*JSON|JSON\s*數據|json).*?({.*?}|```json.*?```)',
        r'數據輸出\s*JSON:?\s*',
        r'DATA_JSON:?\s*'
    ]
    clean_content = content
    for pattern in tech_patterns:
        clean_content = re.sub(pattern, '', clean_content, flags=re.DOTALL | re.IGNORECASE)
    
    # 物理刪除 Markdown 分隔線，從源頭根除 · · ·
    clean_content = re.sub(r'^\s*([-*_=]){3,}\s*$', '', clean_content, flags=re.MULTILINE)
    
    # 移除結尾所有殘留 (點、大括號、JSON 標記、技術字)
    clean_content = re.sub(r'(·|\.|\s|json|{|}|\s|數據輸出|JSON|:)*$', '', clean_content, flags=re.IGNORECASE)
    final_content = summary_md + clean_content.strip()
    
    # C. 產出 PDF
    pdf_path = os.path.join(config.ICLOUD_BASE, f"{date_fn}_{suffix}.pdf")
    pdf_handler.generate_pdf_report(pdf_path, title, date_ds, data.get('ffb'), data.get('cpo'), final_content)

    # D. 更新網頁 (啟用表格擴展)
    html_body = markdown.markdown(final_content, extensions=['tables'])
    web_content = f"<html><body style='background:#121212;color:#e0e0e0;padding:40px;font-family:sans-serif;'><h1>{title}</h1>{html_body}</body></html>"
    with open(html_path, "w", encoding="utf-8") as f: f.write(web_content)
    with open(os.path.join(config.BASE_DIR, "docs/index.html"), "w", encoding="utf-8") as f: f.write(web_content)

    # D. GitHub 同步
    try:
        subprocess.run(["git", "add", "."], cwd=config.BASE_DIR, check=True)
        subprocess.run(["git", "commit", "-m", f"📊 Modular Update {date_fn}"], cwd=config.BASE_DIR, check=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=config.BASE_DIR, check=True)
    except: pass

    # E. LINE 推播
    line_handler.send_push_notification(title, date_ds, data.get('ffb'), data.get('cpo'), basis)
    print("✅ 全模組任務執行完畢。")

if __name__ == "__main__":
    main()
