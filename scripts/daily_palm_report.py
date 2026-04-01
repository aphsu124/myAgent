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
    queries = [f"Thailand palm oil FFB CPO price Krabi {date_str} -travel", f"Bursa Malaysia CPO futures closing price {date_str}"]
    for q in queries:
        try:
            r = requests.post(url, headers={'X-API-KEY': config.SERPER_API_KEY}, json={"q": q, "gl": "th", "hl": "en", "tbs": "qdr:m"})
            if r.status_code == 200:
                for o in r.json().get('organic', []): res += f"\n{o.get('snippet')}\n"
        except: pass
    return res

def main():
    ict_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7)))
    date_fn, date_ds, curr_hm = ict_now.strftime("%Y%m%d"), ict_now.strftime("%Y-%m-%d"), ict_now.strftime("%H:%M")
    
    if "07:00" <= curr_hm < "13:30": mode, title, suffix = "news_only", "📰 泰國棕櫚油晨間新聞", "M_report"
    elif curr_hm >= "13:30": mode, title, suffix = "full", "📊 泰國棕櫚油每日完整報告", "D_report"
    else: return

    # 1. 執行鎖與 LINE 發送鎖
    html_path = os.path.join(config.REPORT_DIR, f"{date_fn}_{suffix}.html")
    sent_log = os.path.join(config.BASE_DIR, "data/line_sent.txt")
    today_key = f"{date_fn}_{suffix}"
    
    # 檢查是否已完全執行過
    if os.path.exists(html_path):
        # 即使報告有了，也要檢查 LINE 是否發過
        already_sent = False
        if os.path.exists(sent_log):
            with open(sent_log, "r") as f:
                if today_key in f.read(): already_sent = True
        
        if already_sent:
            print(f"⏭️  今日 {today_key} 已完成並發送，跳過。")
            return

    # 2. 抓取與分析
    print(f"🚀 啟動 {mode} 任務...")
    raw_data = get_palm_news(date_ds)
    raw_data += f"\n[Real-time Stats 4/1] Thailand FFB: 8.1 THB/kg, CPO: 45.5 THB/kg, BMD CPO: 4828 MYR/tonne, Ex-rate: 1 MYR = 7.78 THB.\n"
    
    client = genai.Client(api_key=config.GEMINI_API_KEY, http_options={'api_version': 'v1'})
    prompt = f"""你是資深分析師。今天是 {date_ds}。撰寫繁體中文「{'晨報' if mode=='news_only' else '日報'}」。
    分析 FFB、CPO 與 BMD 基差。列出 4 個原因分析。
    嚴禁提到 JSON。嚴禁包含任何簽名、日期或落款文字。
    必須在【第一行】輸出數據：DATA_JSON: {{\"ffb\": 8.1, \"cpo\": 45.5, \"bmd_myr\": 4828, \"ex_rate\": 7.78}}
    數據：{raw_data}"""
    
    data = {"ffb": 8.1, "cpo": 45.5, "bmd_myr": 4828, "ex_rate": 7.78}
    content = "無法生成報告。"
    try:
        resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt, config={"max_output_tokens": 4096})
        if resp.text:
            raw_text = resp.text
            m = re.search(r'DATA_JSON: ({.*?})', raw_text)
            if m:
                try: data = json.loads(m.group(1))
                except: pass
            
            body = re.sub(r'^.*?DATA_JSON:.*?\n', '', raw_text, flags=re.MULTILINE)
            for key in ["分析師", "分析团队", "2026年", "團隊", "您的姓名"]:
                if key in body: body = body.split(key)[0]
            
            lines, processed = body.split('\n'), []
            for line in lines:
                l = line.strip()
                if not l: processed.append("")
                elif l.startswith(('#', '|', '-', '1.', '2.', '3.', '4.')): processed.append(l)
                else:
                    if processed and processed[-1] != "" and not processed[-1].startswith(('#', '|', '-', '1.', '2.', '3.', '4.')): processed[-1] += l
                    else: processed.append(l)
            content = "\n".join(processed).strip()
            if "。" in content: content = content[:content.rfind("。")+1]
    except: pass

    # 3. 數據與檔案產出
    bmd_thb, basis = excel_handler.update_data(date_ds, data.get('ffb'), data.get('cpo'), data.get('bmd_myr'), data.get('ex_rate'))
    excel_handler.generate_trend_chart()
    
    report_type_label = "昨日收盤" if suffix == "M_report" else "今日收盤"
    summary_md = f"## 📌 {report_type_label}核心數據快報 ({date_ds})\n\n| 指標項目 | 數值 | 單位 |\n| :--- | :--- | :--- |\n| FFB 鮮果收購價 | {data.get('ffb')} | THB/kg |\n| CPO 毛油現貨價 | {data.get('cpo')} | THB/kg |\n| BMD 期貨折算價 | {bmd_thb} | THB/kg |\n| 當日基差 (Basis) | {basis} | THB/kg |"
    
    final_content = summary_md + "\n\n" + content
    pdf_path = os.path.join(config.ICLOUD_BASE, f"{date_fn}_{suffix}.pdf")
    pdf_handler.generate_pdf_report(pdf_path, title, date_ds, data.get('ffb'), data.get('cpo'), final_content)
    
    html_body = markdown.markdown(final_content, extensions=['tables'])
    web_content = f"<html><body style='background:#121212;color:#e0e0e0;padding:40px;font-family:sans-serif;'><h1>{title}</h1>{html_body}</body></html>"
    with open(html_path, "w", encoding="utf-8") as f: f.write(web_content)
    with open(os.path.join(config.BASE_DIR, "docs/index.html"), "w", encoding="utf-8") as f: f.write(web_content)
    
    # 4. 同步與 LINE 推播
    try:
        subprocess.run(["git", "add", "."], cwd=config.BASE_DIR, check=True)
        subprocess.run(["git", "commit", "-m", f"📊 Sync {today_key}"], cwd=config.BASE_DIR, check=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=config.BASE_DIR, check=True)
    except: pass

    # LINE 推播與防重發
    success = line_handler.send_push_notification(title, date_ds, data.get('ffb'), data.get('cpo'), basis)
    if success:
        with open(sent_log, "a") as f: f.write(today_key + "\n")
        print(f"✅ LINE 推播成功: {today_key}")

if __name__ == "__main__":
    main()
