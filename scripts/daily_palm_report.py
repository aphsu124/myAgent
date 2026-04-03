import os
import requests
import datetime
import json
import re
import subprocess
import markdown
from google import genai
from modules import config, excel_handler, pdf_handler, line_handler, validator
import sys
import argparse

def get_palm_news(date_str):
    url = "https://google.serper.dev/search"
    res = ""
    queries = [f"Thailand palm oil FFB CPO market news {date_str}", f"BMD palm oil futures analysis {date_str}"]
    for q in queries:
        try:
            r = requests.post(url, headers={'X-API-KEY': config.SERPER_API_KEY}, json={"q": q, "gl": "th", "hl": "en", "tbs": "qdr:m"}, timeout=15)
            if r.status_code == 200:
                for o in r.json().get('organic', []): res += f"\n{o.get('snippet')}\n"
            else:
                print(f"⚠️ Serper API 回應異常: HTTP {r.status_code}")
        except requests.exceptions.Timeout:
            print(f"⚠️ Serper 搜尋逾時 (query: {q[:50]})")
        except Exception as e:
            print(f"⚠️ Serper 搜尋失敗: {e}")
    return res

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--morning', action='store_true')
    parser.add_argument('--full', action='store_true')
    args = parser.parse_args()

    ict_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7)))
    date_fn, date_ds, curr_hm = ict_now.strftime("%Y%m%d"), ict_now.strftime("%Y-%m-%d"), ict_now.strftime("%H:%M")
    
    if args.morning or ("07:00" <= curr_hm < "13:30"): mode, title, suffix = "news_only", "📰 泰國棕櫚油晨間新聞", "M_report"
    elif args.full or (curr_hm >= "13:30"): mode, title, suffix = "full", "📊 泰國棕櫚油每日完整報告", "D_report"
    else: return

    html_path = os.path.join(config.REPORT_DIR, f"{date_fn}_{suffix}.html")
    sent_log = os.path.join(config.BASE_DIR, "data/line_sent.txt")
    today_key = f"{date_fn}_{suffix}"
    
    if os.path.exists(html_path) and os.path.getsize(html_path) > 2500:
        print(f"⏭️  今日 {today_key} 已發布高品質版本，跳過。")
        return

    print(f"🚀 啟動 {mode} 任務 (高容錯深度模式)...")
    raw_data = get_palm_news(date_ds)
    raw_data += f"\n[Market Stats 4/1] FFB: 8.1, CPO: 45.5, BMD: 4828, EX: 7.78\n"
    
    client = genai.Client(api_key=config.GEMINI_API_KEY, http_options={'api_version': 'v1'})
    
    attempts, max_attempts = 0, 3
    is_valid, error_msg = False, ""
    content, data = "", {"ffb": 8.1, "cpo": 45.5, "bmd_myr": 4828, "ex_rate": 7.78}

    while attempts < max_attempts and not is_valid:
        attempts += 1
        import time; time.sleep(5); print(f"🔄 正在進行第 {attempts} 次產出嘗試...")
        
        prompt = f"""你是泰國甲米棕櫚油廠的首席營運官。今天是 {date_ds}。
請根據搜尋資料撰寫報告，並嚴格遵守以下格式規範：

【格式規範 — 必須完全照此結構輸出，不得更改標題文字與順序】

主旨：{date_ds}棕櫚油市場動態分析及營運策略調整報告

高層主管們，

（一段連貫的市場概況段落，直接分析今日最重要的棕櫚油市場動態與價格走勢，不使用標題，不分點）

對我們油廠的實質影響

1. 獲利能力
（說明市場動態對獲利的具體衝擊，不少於3句，文字連貫）

2. 庫存價值
（說明庫存面臨的風險或機會，不少於3句，文字連貫）

3. 產能利用與效率
（說明產能與效率層面的影響，不少於3句，文字連貫）

具體策略建議

### 1. 獲利能力提升策略
· （具體行動建議，每點用 · 開頭，至少3點，每點一段完整說明）
· （...）

### 2. 庫存管理策略
· （具體行動建議，每點用 · 開頭，至少3點，每點一段完整說明）
· （...）

### 3. 產能與運營策略
· （具體行動建議，每點用 · 開頭，至少3點，每點一段完整說明）
· （...）

DATA_JSON: {{"ffb": 8.1, "cpo": 45.5, "bmd_myr": 4828, "ex_rate": 7.78}}

【寫作規範】
- 受眾為高層主管，嚴禁解釋 FFB、CPO 等基本名詞定義
- 嚴禁簽名落款
- 嚴禁包含與棕櫚油無關的內容
- 每個 · 建議點必須是獨立完整的一段，不可只寫一行短句
- DATA_JSON 中的數值必須根據搜尋資料更新為當日實際數字

搜尋資料：{raw_data}"""
        
        try:
            resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt, config={"max_output_tokens": 4096})
            try:
                from modules.token_tracker import record as _tt
                _tt('google', 'gemini-2.5-flash', resp.usage_metadata.prompt_token_count or 0, resp.usage_metadata.candidates_token_count or 0)
            except Exception: pass
            if resp.text:
                raw_text = resp.text
                with open(os.path.join(config.BASE_DIR, "data/DEBUG_RAW.txt"), "w") as f: f.write(raw_text)
                
                # [ 高容錯 JSON 提取 ]
                m = re.search(r'DATA_JSON[:：]?\s*({.*?})', raw_text, flags=re.DOTALL)
                if m:
                    try: data = json.loads(m.group(1))
                    except: pass
                
                # 段落修復與 Markdown 結構強化
                body = re.sub(r'DATA_JSON:.*?$', '', raw_text, flags=re.MULTILINE).strip()
                
                # 修正冒號與加粗標題 (只針對行首或雙星號包裹的項目)
                body = re.sub(r'^\s*[\-\*]\s*\*\*([^\*：\n]+)：\*\*', r'\n- **\1：**', body, flags=re.MULTILINE)
                # 修正章節標題 (必須在行首)
                body = re.sub(r'^\s*([0-9一二三四五][.、])\s*', r'\n\n### \1 ', body, flags=re.MULTILINE)
                
                lines, processed = body.split('\n'), []
                for line in lines:
                    l = line.strip()
                    if not l: processed.append("")
                    elif l.startswith(('#', '|', '-', '1.', '2.', '3.', '4.', '・', '*')): 
                        if processed and processed[-1] == "": # 如果前一行是空行，則不重複加
                            processed.append(l)
                        else:
                            processed.append("\n" + l)
                    else:
                        if processed and processed[-1] != "" and not processed[-1].startswith(('#', '|', '-', '1.', '2.', '3.', '4.', '・', '*', '###')): 
                            processed[-1] += l
                        else: processed.append(l)
                
                content = "\n".join(processed).replace("\n\n\n", "\n\n").replace("\n\n###", "\n###").strip()
                if "。" in content: content = content[:content.rfind("。")+1]
                
                # 品質審查
                res_c, msg_c = validator.is_report_valid(content)
                res_d, msg_d = validator.is_data_valid(data)
                if res_c and res_d: is_valid = True
                else: error_msg = f"{msg_c} | {msg_d}"
        except Exception as e:
            error_msg = str(e)

    if is_valid:
        bmd_thb, basis = excel_handler.update_data(date_ds, data.get('ffb'), data.get('cpo'), data.get('bmd_myr'), data.get('ex_rate'))
        excel_handler.generate_trend_chart()
        report_label = "昨日收盤" if suffix == "M_report" else "今日收盤"
        summary_md = f"## 📌 {report_label}核心數據快報 ({date_ds})\n\n| 指標項目 | 數值 | 單位 |\n| :--- | :--- | :--- |\n| FFB 鮮果收購價 | {data.get('ffb')} | THB/kg |\n| CPO 毛油現貨價 | {data.get('cpo')} | THB/kg |\n| BMD 期貨折算價 | {bmd_thb} | THB/kg |\n| 當日基差 (Basis) | {basis} | THB/kg |\n\n---\n"
        final_content = summary_md + "\n" + content
        pdf_path = f"/tmp/{date_fn}_{suffix}.pdf"
        pdf_handler.generate_pdf_report(pdf_path, title, date_ds, data.get('ffb'), data.get('cpo'), final_content)
        if config.STORAGE_BACKEND == 'gdrive' and config.GDRIVE_FOLDER_BRIEFING:
            from modules.gdrive_utils import create_file
            create_file(pdf_path, config.GDRIVE_FOLDER_BRIEFING, "application/pdf")
        else:
            try:
                import shutil
                shutil.copy(pdf_path, os.path.join(config.ICLOUD_BASE, f"{date_fn}_{suffix}.pdf"))
            except Exception as e:
                print(f"⚠️ PDF 複製至 iCloud 失敗: {e}")
        # [ 視覺大升級：高品質網頁模板 ]
        css = """
        :root {
            --bg-color: #0f172a;
            --card-bg: #1e293b;
            --text-main: #f1f5f9;
            --text-dim: #94a3b8;
            --accent-green: #10b981;
            --accent-blue: #38bdf8;
            --border-color: #334155;
        }
        body {
            background-color: var(--bg-color);
            color: var(--text-main);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            display: flex;
            justify-content: center;
        }
        .container {
            max-width: 900px;
            width: 100%;
            background: var(--card-bg);
            padding: 40px;
            border-radius: 16px;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
            border: 1px solid var(--border-color);
        }
        h1 { color: var(--accent-blue); font-size: 2.2rem; margin-bottom: 30px; border-bottom: 2px solid var(--accent-blue); padding-bottom: 10px; }
        h2 { color: var(--accent-green); font-size: 1.5rem; margin-top: 40px; }
        h3 { color: var(--text-main); border-left: 4px solid var(--accent-green); padding-left: 15px; margin-top: 30px; }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 25px 0;
            font-size: 1.1rem;
            background: rgba(15, 23, 42, 0.5);
            border-radius: 8px;
            overflow: hidden;
        }
        th {
            background-color: var(--accent-blue);
            color: #000;
            text-align: left;
            padding: 15px;
            font-weight: bold;
        }
        td {
            padding: 15px;
            border-bottom: 1px solid var(--border-color);
        }
        tr:nth-child(even) { background-color: rgba(255, 255, 255, 0.03); }
        tr:hover { background-color: rgba(56, 189, 248, 0.1); }
        hr { border: 0; border-top: 1px solid var(--border-color); margin: 40px 0; }
        ul, li { margin-bottom: 10px; }
        .meta-info { color: var(--text-dim); font-size: 0.9rem; margin-bottom: 20px; }
        """

        html_body = markdown.markdown(final_content, extensions=['tables'])
        web_content = f"""
        <!DOCTYPE html>
        <html lang="zh-TW">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <meta http-equiv="cache-control" content="no-cache">
            <meta http-equiv="pragma" content="no-cache">
            <title>{title}</title>
            <style>{css}</style>
        </head>
        <body>
            <div class="container">
                <div class="meta-info">系統：Jarvis Intelligence | 狀態：已通過品質檢核</div>
                <h1>{title}</h1>
                {html_body}
                <div style="margin-top:50px; text-align:center; color:var(--text-dim); font-size:0.8rem;">
                    © 2026 甲米棕櫚油廠 營運指揮中心
                </div>
            </div>
        </body>
        </html>
        """

        with open(html_path, "w", encoding="utf-8") as f: f.write(web_content)
        with open(os.path.join(config.BASE_DIR, "docs/index.html"), "w", encoding="utf-8") as f: f.write(web_content)

        try:
            subprocess.run(["git", "add", "."], check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", f"📊 Insight {date_fn}"], check=True, capture_output=True)
            subprocess.run(["git", "push", "origin", "main"], check=True, capture_output=True)
            print("✅ Git push 成功。")
        except subprocess.CalledProcessError as e:
            err_msg = e.stderr.decode('utf-8', errors='ignore').strip()
            print(f"⚠️ Git 操作失敗: {err_msg}")
            line_handler.send_push_notification("🚨 網頁未更新警報", date_ds, 0, 0, f"Git push 失敗，網頁版報告未更新。\n原因：{err_msg[:80]}")
        
        # 僅在尚未發送過的情況下發送 LINE
        try:
            sent_content = open(sent_log, encoding="utf-8").read() if os.path.exists(sent_log) else ""
        except Exception as e:
            print(f"⚠️ 讀取發送日誌失敗: {e}")
            sent_content = ""
        if today_key not in sent_content:
            line_handler.send_push_notification(title, date_ds, data.get('ffb'), data.get('cpo'), basis)
            with open(sent_log, "a") as f: f.write(today_key + "\n")
            print("✅ 深度報告發布成功。")
    else:
        line_handler.send_push_notification("🚨 品質異常警報", date_ds, 0, 0, f"修正失敗：{error_msg}")

if __name__ == "__main__":
    main()
