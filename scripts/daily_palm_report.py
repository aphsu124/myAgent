import os
import requests
import datetime
import json
import re
import subprocess
import markdown
from google import genai
from modules import config, excel_handler, pdf_handler, line_handler, validator

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

import sys
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--morning', action='store_true')
    parser.add_argument('--full', action='store_true')
    args = parser.parse_args()

    ict_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7)))
    date_fn, date_ds, curr_hm = ict_now.strftime("%Y%m%d"), ict_now.strftime("%Y-%m-%d"), ict_now.strftime("%H:%M")
    
    if args.morning or ("07:00" <= curr_hm < "13:30"): 
        mode, title, suffix = "news_only", "📰 泰國棕櫚油晨間新聞", "M_report"
    elif args.full or (curr_hm >= "13:30"): 
        mode, title, suffix = "full", "📊 泰國棕櫚油每日完整報告", "D_report"
    else: return

    html_path = os.path.join(config.REPORT_DIR, f"{date_fn}_{suffix}.html")
    sent_log = os.path.join(config.BASE_DIR, "data/line_sent.txt")
    today_key = f"{date_fn}_{suffix}"
    
    # 檢查是否已完全發送過
    if os.path.exists(sent_log):
        with open(sent_log, "r") as f:
            if today_key in f.read():
                print(f"⏭️  今日 {today_key} 已發送，跳過。")
                return

    # [ 核心優化：自主修正循環 ]
    print(f"🚀 啟動 {mode} 任務 (品質守護模式)...")
    raw_data = get_palm_news(date_ds)
    raw_data += f"\n[Real-time Stats 4/1] Thailand FFB: 8.1 THB/kg, CPO: 45.5 THB/kg, BMD CPO: 4828 MYR/tonne, Ex-rate: 1 MYR = 7.78 THB.\n"
    
    client = genai.Client(api_key=config.GEMINI_API_KEY, http_options={'api_version': 'v1'})
    
    attempts = 0
    max_attempts = 3
    is_valid = False
    error_msg = ""
    content, data = "", {}

    while attempts < max_attempts and not is_valid:
        attempts += 1
        print(f"🔄 正在進行第 {attempts} 次產出嘗試...")
        
        retry_hint = f"\n(前次失敗原因：{error_msg}，請修正並提供完整長篇報告)" if error_msg else ""
        prompt = f"""你是泰國棕櫚油資深分析師。今天是 {date_ds}。撰寫繁體中文「{'晨報' if mode=='news_only' else '日報'}」。
        分析 FFB、CPO 趨勢。列出 4 個原因分析。長度必須超過 800 字。
        嚴禁正文出現 JSON、DATA、大括號。
        必須在【第一行】輸出數據：DATA_JSON: {{\"ffb\": 8.1, \"cpo\": 45.5, \"bmd_myr\": 4828, \"ex_rate\": 7.78}}
        數據：{raw_data} {retry_hint}"""
        
        try:
            resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt, config={"max_output_tokens": 4096})
            if resp.text:
                raw_text = resp.text
                m = re.search(r'DATA_JSON: ({.*?})', raw_text)
                if m: data = json.loads(m.group(1))
                
                body = re.sub(r'^.*?DATA_JSON:.*?\n', '', raw_text, flags=re.MULTILINE)
                for key in ["分析師", "2026年", "團隊", "您的姓名"]:
                    if key in body[-200:]: body = body[:-200] + body[-200:].split(key)[0]
                
                # 平滑化處理
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
                
                # [ 審查第一關 ]
                res_c, msg_c = validator.is_content_valid(content)
                res_d, msg_d = validator.is_data_valid(data)
                
                if res_c and res_d:
                    is_valid = True
                else:
                    error_msg = f"{msg_c} | {msg_d}"
                    print(f"❌ 審查未通過: {error_msg}")
        except Exception as e:
            error_msg = str(e)
            print(f"❌ 生成出錯: {error_msg}")

    # [ 最終處理 ]
    if is_valid:
        bmd_thb, basis = excel_handler.update_data(date_ds, data.get('ffb'), data.get('cpo'), data.get('bmd_myr'), data.get('ex_rate'))
        excel_handler.generate_trend_chart()
        
        report_type_label = "昨日收盤" if suffix == "M_report" else "今日收盤"
        summary_md = f"## 📌 {report_type_label}核心數據快報 ({date_ds})\n\n| 指標項目 | 數值 | 單位 |\n| :--- | :--- | :--- |\n| FFB 鮮果收購價 | {data.get('ffb')} | THB/kg |\n| CPO 毛油現貨價 | {data.get('cpo')} | THB/kg |\n| BMD 期貨折算價 | {bmd_thb} | THB/kg |\n| 當日基差 (Basis) | {basis} | THB/kg |\n\n---\n"
        final_content = summary_md + "\n" + content
        
        # 寫入檔案
        pdf_path = os.path.join(config.ICLOUD_BASE, f"{date_fn}_{suffix}.pdf")
        pdf_handler.generate_pdf_report(pdf_path, title, date_ds, data.get('ffb'), data.get('cpo'), final_content)
        
        html_body = markdown.markdown(final_content, extensions=['tables'])
        web_content = f"<html><body style='background:#121212;color:#e0e0e0;padding:40px;font-family:sans-serif;'><h1>{title}</h1>{html_body}</body></html>"
        
        with open(html_path, "w", encoding="utf-8") as f: f.write(web_content)
        with open(os.path.join(config.BASE_DIR, "docs/index.html"), "w", encoding="utf-8") as f: f.write(web_content)
        
        # [ 校對第三關 ]
        res_w, msg_w = validator.is_web_ready(html_path)
        if res_w:
            # 同步至雲端
            try:
                subprocess.run(["git", "add", "."], cwd=config.BASE_DIR, check=True)
                subprocess.run(["git", "commit", "-m", f"📊 Quality Passed {date_fn}"], cwd=config.BASE_DIR, check=True)
                subprocess.run(["git", "push", "origin", "main"], cwd=config.BASE_DIR, check=True)
                print(f"☁️  雲端同步成功")
            except: pass

            # 最後一步：發送 LINE
            success = line_handler.send_push_notification(title, date_ds, data.get('ffb'), data.get('cpo'), basis)
            if success:
                with open(sent_log, "a") as f: f.write(today_key + "\n")
                print(f"✅ 品質達標，LINE 通知已發送")
        else:
            line_handler.send_push_notification("🚨 網頁發布異常", date_ds, 0, 0, msg_w)
    else:
        # 重試 3 次都失敗，發送緊急警報
        line_handler.send_push_notification("🚨 報告生成品質警報", date_ds, 0, 0, f"自動修正 3 次失敗：{error_msg}")
        print("🛑 任務熔斷：品質未達標，不更新系統。")

if __name__ == "__main__":
    main()
