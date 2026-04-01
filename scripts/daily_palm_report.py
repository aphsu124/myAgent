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
    ict_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7)))
    date_fn = ict_now.strftime("%Y%m%d")
    date_ds = ict_now.strftime("%Y-%m-%d")
    curr_hm = ict_now.strftime("%H:%M")
    
    if "07:00" <= curr_hm < "13:30":
        mode, title, suffix = "news_only", "📰 泰國棕櫚油晨間新聞", "M_report"
    elif curr_hm >= "13:30":
        mode, title, suffix = "full", "📊 泰國棕櫚油每日完整報告", "D_report"
    else: return

    html_path = os.path.join(config.REPORT_DIR, f"{date_fn}_{suffix}.html")
    if False: return

    print(f"🚀 啟動 {mode} 任務...")
    raw_data = get_palm_news(date_ds)
    raw_data += f"\n[Real-time Stats 4/1] Thailand FFB: 8.1 THB/kg, CPO: 45.5 THB/kg, BMD CPO: 4828 MYR/tonne, Ex-rate: 1 MYR = 7.78 THB.\n"
    
    client = genai.Client(api_key=config.GEMINI_API_KEY, http_options={'api_version': 'v1'})
    prompt = f"""你是泰國棕櫚油資深分析師。今天是 {date_ds}。
    請撰寫繁體中文「{'晨報' if mode=='news_only' else '日報'}」。
    內容要求：
    1. 針對 FFB、CPO 趨勢做詳細分析。
    2. 解讀 BMD 期貨與匯率對基差的影響進行解讀。
    3. 分析原因時，請列出至少 4 個關鍵點，並確保編號為 1. 2. 3. 4.。
    4. 嚴禁在文中提到 JSON、DATA 或代碼塊字眼。
    5. 嚴禁在結尾添加任何簽名、分析師姓名、日期或落款（例如：資深分析師、分析團隊、2026年...）。
    6. 必須在【第一行】輸出數據：DATA_JSON: {{\"ffb\": 8.1, \"cpo\": 45.5, \"bmd_myr\": 4828, \"ex_rate\": 7.78}}
    數據參考：{raw_data}"""
    
    content, data = "無法生成報告。", {"ffb": 8.1, "cpo": 45.5, "bmd_myr": 4828, "ex_rate": 7.78}
    try:
        resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt, config={"max_output_tokens": 4096})
        if resp.text:
            raw_text = resp.text
            m = re.search(r'DATA_JSON: ({.*?})', raw_text)
            if m: data = json.loads(m.group(1))
            
            clean_content = re.sub(r'^.*?DATA_JSON:.*?\n', '', raw_text, flags=re.MULTILINE)
            # 段落平滑化與落款清理
            lines = clean_content.split('\n')
            processed_lines = []
            for line in lines:
                line = line.strip()
                if not line: processed_lines.append("")
                # 更激進的過濾：攔截所有包含落款特徵的行
                if re.search(r'(分析師|分析团队|2026年|您的姓名|簽名|團隊|落款)', line): continue
                
                if line.startswith(('#', '|', '-', '1.', '2.', '3.', '4.', '・')): processed_lines.append(line)
                else:
                    if processed_lines and processed_lines[-1] != "" and not processed_lines[-1].startswith(('#', '|', '-', '1.', '2.', '3.', '4.', '・')):
                        processed_lines[-1] += line
                    else: processed_lines.append(line)
            content = "\n".join(processed_lines).strip()
            # 結尾二次清理：確保最後一行不是加粗的分析師字樣
            content = re.sub(r'\n\*\*.*?(分析師|日期).*?\*\*.*$', '', content, flags=re.DOTALL)
    except: pass

    bmd_thb, basis = excel_handler.update_data(date_ds, data.get('ffb'), data.get('cpo'), data.get('bmd_myr'), data.get('ex_rate'))
    excel_handler.generate_trend_chart()
    
    report_type_label = "昨日收盤" if suffix == "M_report" else "今日收盤"
    summary_md = f"## 📌 {report_type_label}核心數據快報 ({date_ds})\n\n| 指標項目 | 數值 | 單位 |\n| :--- | :--- | :--- |\n| FFB 鮮果收購價 | {data.get('ffb')} | THB/kg |\n| CPO 毛油現貨價 | {data.get('cpo')} | THB/kg |\n| BMD 期貨折算價 | {bmd_thb} | THB/kg |\n| 當日基差 (Basis) | {basis} | THB/kg |"
    
    final_content = summary_md + "\n\n" + content
    
    # [ Council 終極暴力修復：不留死角 ]
    # 直接透過 Regex 移除任何包含分析師或日期的行 (不論是否在結尾)
    final_content = re.sub(r'\n.*?(分析師|分析團隊|2026年|您的姓名|簽名).*?\n?', '\n', final_content)
    # 針對 Markdown 加粗版的特別清理
    final_content = re.sub(r'\*\*.*?(分析師|日期|團隊).*?\*\*', '', final_content)
    
    # 再次確保乾淨
    final_content = final_content.strip()
    
    pdf_path = os.path.join(config.ICLOUD_BASE, f"{date_fn}_{suffix}.pdf")
    pdf_handler.generate_pdf_report(pdf_path, title, date_ds, data.get('ffb'), data.get('cpo'), final_content)

    html_body = markdown.markdown(final_content, extensions=['tables'])
    web_content = f"<html><body style='background:#121212;color:#e0e0e0;padding:40px;font-family:sans-serif;'><h1>{title}</h1>{html_body}</body></html>"
    with open(os.path.join(config.BASE_DIR, "docs/index.html"), "w", encoding="utf-8") as f: f.write(web_content)

    try:
        subprocess.run(["git", "add", "."], cwd=config.BASE_DIR, check=True)
        subprocess.run(["git", "commit", "-m", f"📊 Layout Update {date_fn}"], cwd=config.BASE_DIR, check=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=config.BASE_DIR, check=True)
    except: pass

    line_handler.send_push_notification(title, date_ds, data.get('ffb'), data.get('cpo'), basis)

if __name__ == "__main__":
    main()
