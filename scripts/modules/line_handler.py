import requests
import os
from .config import LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID, GITHUB_IO_URL

def send_push_notification(title, date_str, ffb, cpo, basis):
    """發送 LINE 推播訊息 (修復基差 0 與美化版)"""
    if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_USER_ID: return
    
    # 格式化數值與防呆
    is_open = str(cpo) != "N/A" and float(cpo) > 0
    disp_f = f"฿{ffb}" if str(ffb) != "N/A" and float(ffb) > 0 else "---"
    disp_c = f"฿{cpo}" if is_open else "市場未開盤"
    
    # 基差處理 (如果 CPO 有開盤但基差為 0，通常是 BMD 抓取失敗)
    if is_open:
        disp_b = f"฿{basis}" if basis != 0 else "⚠️ 數據延遲"
    else:
        disp_b = "N/A"
    
    msg = f"【{title}】\n"
    msg += f"📅 日期：{date_str}\n"
    msg += f"────────────────\n"
    msg += f"🌿 FFB 收購價：{disp_f}\n"
    msg += f"💧 CPO 現貨價：{disp_c}\n"
    msg += f"📈 價差 (Basis)：{disp_b}\n"
    msg += f"────────────────\n"
    msg += f"🔗 最新完整報告與趨勢圖：\n{GITHUB_IO_URL}/index.html"
    
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}
    payload = {"to": LINE_USER_ID, "messages": [{"type": "text", "text": msg}]}

    import time
    for attempt in range(3):
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=15)
            if r.status_code == 200:
                return True
            print(f"⚠️ LINE 推播失敗 (attempt {attempt+1}/3): HTTP {r.status_code} - {r.text[:100]}")
        except requests.exceptions.Timeout:
            print(f"⚠️ LINE 推播逾時 (attempt {attempt+1}/3)")
        except Exception as e:
            print(f"⚠️ LINE 推播錯誤 (attempt {attempt+1}/3): {e}")
        if attempt < 2:
            time.sleep(5)
    print("🚨 LINE 推播 3 次重試全部失敗")
    return False
