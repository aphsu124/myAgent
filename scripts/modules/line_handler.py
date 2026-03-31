import requests
import os
from .config import LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID, GITHUB_IO_URL

def send_push_notification(title, date_str, ffb, cpo, basis):
    """發送 LINE 推播訊息"""
    if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_USER_ID: return
    
    # 格式化數值
    disp_f = f"{ffb} Baht/kg" if str(ffb) != "N/A" and ffb != 0 else "市場未開盤"
    disp_c = f"{cpo} Baht/kg" if str(cpo) != "N/A" and fpo != 0 else "市場未開盤"
    
    msg = f"{title} ({date_str})\n"
    msg += f"🔸 FFB: {disp_f}\n"
    msg += f"🔸 CPO: {disp_c}\n"
    msg += f"🔸 基差: {basis if disp_c != '市場未開盤' else 'N/A'}\n"
    msg += f"\n👉 查看網頁：{GITHUB_IO_URL}/index.html"
    
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}
    payload = {"to": LINE_USER_ID, "messages": [{"type": "text", "text": msg}]}
    
    try:
        r = requests.post(url, headers=headers, json=payload)
        return r.status_code == 200
    except: return False
