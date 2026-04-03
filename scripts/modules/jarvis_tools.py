import os
import re
import subprocess
import datetime
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
from .config import (
    BASE_DIR, GEMINI_API_KEY,
    GDRIVE_FOLDER_BRIEFING, GDRIVE_FOLDER_MEETING,
    GDRIVE_FOLDER_TRANSLATE, GDRIVE_FOLDER_CONTACT, GDRIVE_FOLDER_MONITOR,
)

# ── 資料夾關鍵字對應表 ──────────────────────────────────────────
FOLDER_MAP = {
    '簡報': GDRIVE_FOLDER_BRIEFING,
    '會議': GDRIVE_FOLDER_MEETING,
    '翻譯': GDRIVE_FOLDER_TRANSLATE,
    '聯絡人': GDRIVE_FOLDER_CONTACT,
    '監控': GDRIVE_FOLDER_MONITOR,
}

# ── Drive 網址解析 ──────────────────────────────────────────────
def extract_drive_file_id(text):
    """從 Google Drive 網址提取 file_id，非網址回傳 None"""
    patterns = [
        r'/d/([a-zA-Z0-9_-]{25,})',
        r'[?&]id=([a-zA-Z0-9_-]{25,})',
    ]
    for pattern in patterns:
        m = re.search(pattern, text)
        if m:
            return m.group(1)
    return None

# ── 工具實作 ────────────────────────────────────────────────────

def convert_to_pdf(filename, folder_hint=None):
    """從 Drive 下載 Excel，用 Microsoft Excel 原生匯出 PDF，回傳本地 PDF 路徑"""
    from .gdrive_utils import find_file_id, find_file_across_drive, download_file

    # 1. 決定 file_id
    file_id = extract_drive_file_id(filename)

    if not file_id:
        # 先嘗試資料夾縮小範圍搜尋
        if folder_hint:
            folder_id = FOLDER_MAP.get(folder_hint)
            if folder_id:
                file_id = find_file_id(filename, folder_id)

        # 全域搜尋兜底
        if not file_id:
            results = find_file_across_drive(filename)
            if not results:
                return f"❌ 在 Drive 上找不到檔案：{filename}"
            if len(results) > 1:
                names = "\n".join([f"- {r['name']}" for r in results])
                return f"⚠️ 找到多個同名檔案，請提供資料夾名稱縮小範圍：\n{names}"
            file_id = results[0]['id']
            filename = results[0]['name']

    # 2. 下載到 /tmp/
    base_name = os.path.splitext(os.path.basename(filename))[0]
    local_xlsx = f"/tmp/{base_name}.xlsx"
    local_pdf  = f"/tmp/{base_name}.pdf"

    if not download_file(file_id, local_xlsx):
        return f"❌ 下載失敗：{filename}"

    # 3. AppleScript 控制 Excel 匯出 PDF
    script = f'''
    tell application "Microsoft Excel"
        set wb to open workbook workbook file name "{local_xlsx}"
        save as wb filename "{local_pdf}" file format PDF file format
        close wb saving no
    end tell
    '''
    try:
        subprocess.run(['osascript', '-e', script], check=True, timeout=60, capture_output=True)
    except subprocess.CalledProcessError as e:
        err = e.stderr.decode('utf-8', errors='ignore').strip()
        return f"❌ Excel 轉換失敗：{err[:100]}"
    except subprocess.TimeoutExpired:
        return "❌ Excel 轉換逾時（超過 60 秒）"

    if not os.path.exists(local_pdf):
        return "❌ PDF 未產生，請確認 Excel 可正常開啟該檔案"

    return local_pdf  # 讓 telegram_bot 用 sendDocument 傳送

def run_daily_report():
    """立即產出今日棕櫚油報告"""
    try:
        result = subprocess.run(
            ['python3', os.path.join(BASE_DIR, 'scripts/daily_palm_report.py')],
            cwd=BASE_DIR, capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            return "✅ 日報已產出並發布。"
        else:
            return f"⚠️ 日報產出異常：{result.stderr[:100]}"
    except subprocess.TimeoutExpired:
        return "⚠️ 日報產出逾時，已在背景繼續執行。"
    except Exception as e:
        return f"❌ 執行失敗：{e}"

def list_drive_files(folder_name):
    """列出指定資料夾的檔案清單"""
    from .gdrive_utils import list_files_in_folder
    folder_id = FOLDER_MAP.get(folder_name)
    if not folder_id:
        available = '、'.join(FOLDER_MAP.keys())
        return f"❌ 未知資料夾「{folder_name}」，可用：{available}"
    files = list_files_in_folder(folder_id)
    if not files:
        return f"📂 {folder_name} 資料夾目前沒有檔案。"
    lines = [f"📂 {folder_name} 資料夾（{len(files)} 個檔案）："]
    for f in files:
        lines.append(f"  • {f['name']}")
    return "\n".join(lines)

def capture_camera():
    """拍攝監控截圖，回傳本地圖片路徑"""
    try:
        result = subprocess.run(
            ['python3', '-c',
             f'import sys; sys.path.insert(0, "{BASE_DIR}/scripts"); '
             f'from camera_manager import capture_frame; '
             f'path = capture_frame(0); print(path or "")'],
            cwd=BASE_DIR, capture_output=True, text=True, timeout=30
        )
        path = result.stdout.strip()
        if path and os.path.exists(path):
            return path
        return "❌ 截圖失敗，請確認攝影機已連接。"
    except Exception as e:
        return f"❌ 截圖錯誤：{e}"

def get_token_usage():
    """回報三家 AI 今日 token 用量與本月累計費用"""
    from .token_tracker import get_today_summary, get_month_summary, get_month_total_cost
    import datetime

    today   = get_today_summary()
    month_total = get_month_total_cost()
    month_name  = datetime.date.today().strftime('%m月')

    if not today:
        return "📊 今日尚無 API 呼叫紀錄。"

    lines = ["📊 *AI Token 用量報告*\n"]
    provider_label = {'google': 'Gemini', 'anthropic': 'Claude', 'openai': 'OpenAI'}

    for d in today:
        label = provider_label.get(d['provider'], d['provider'])
        inp   = d['input_tokens']
        out   = d['output_tokens']
        cost  = d['cost_usd']

        if d['has_free_tier'] and d['usage_percent'] is not None:
            pct_str = f"  免費額度：{d['usage_percent']:.1f}%"
            if d['usage_percent'] >= 90:
                pct_str += " 🔴"
            elif d['usage_percent'] >= 80:
                pct_str += " 🟡"
            else:
                pct_str += " 🟢"
        else:
            pct_str = ""

        cost_str = f"{cost*100:.1f}¢" if cost < 1 else f"${cost:.2f}"
        lines.append(f"▪ {label}：↑{inp:,} ↓{out:,} tokens  今日 {cost_str}{pct_str}")

    lines.append(f"\n💰 {month_name}累計總費用：${month_total:.4f}")
    return "\n".join(lines)

def get_status():
    """回報 Jarvis 系統狀態"""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_path = os.path.join(BASE_DIR, 'data/jarvis_tg.log')
    last_lines = ""
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            last_lines = "".join(lines[-5:]).strip()
    except Exception:
        last_lines = "（無法讀取 log）"
    return (
        f"🟢 Jarvis 運行中\n"
        f"🕐 現在時間：{now}\n"
        f"📋 最新 Log：\n{last_lines}"
    )

# ── 工具分發器 ──────────────────────────────────────────────────
TOOL_REGISTRY = {
    'convert_to_pdf':   convert_to_pdf,
    'run_daily_report': run_daily_report,
    'list_drive_files': list_drive_files,
    'capture_camera':   capture_camera,
    'get_status':       get_status,
    'get_token_usage':  get_token_usage,
}

def dispatch(tool_name, args):
    """呼叫對應工具，回傳結果（字串 or 本地檔案路徑）"""
    fn = TOOL_REGISTRY.get(tool_name)
    if not fn:
        return f"❌ 未知工具：{tool_name}"
    try:
        return fn(**args)
    except Exception as e:
        return f"❌ 工具執行失敗 ({tool_name}): {e}"

# ── Gemini 工具宣告 ─────────────────────────────────────────────
TOOL_DECLARATIONS = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name='convert_to_pdf',
            description=(
                '將 Google Drive 上的 Excel 檔案轉換成可列印的 PDF，'
                '使用 Microsoft Excel 原生匯出以保留完整格式。'
                'filename 可以是檔案名稱（如 report.xlsx）或直接貼上 Google Drive 分享連結。'
            ),
            parameters=types.Schema(
                type='OBJECT',
                properties={
                    'filename': types.Schema(
                        type='STRING',
                        description='檔案名稱（如 palm_oil_history.xlsx）或 Google Drive 網址'
                    ),
                    'folder_hint': types.Schema(
                        type='STRING',
                        description='可選：縮小搜尋範圍的資料夾名稱，如「簡報」「翻譯」「會議」「聯絡人」「監控」'
                    ),
                },
                required=['filename']
            )
        ),
        types.FunctionDeclaration(
            name='run_daily_report',
            description='立即產出今日棕櫚油市場分析報告並推送至 LINE 與網頁',
        ),
        types.FunctionDeclaration(
            name='list_drive_files',
            description='列出 Google Drive 指定資料夾中的所有檔案',
            parameters=types.Schema(
                type='OBJECT',
                properties={
                    'folder_name': types.Schema(
                        type='STRING',
                        description='資料夾名稱：簡報、會議、翻譯、聯絡人、監控'
                    ),
                },
                required=['folder_name']
            )
        ),
        types.FunctionDeclaration(
            name='capture_camera',
            description='拍攝工廠監控攝影機的即時截圖並傳回',
        ),
        types.FunctionDeclaration(
            name='get_status',
            description='回報 Jarvis 目前的運行狀態與最新 log',
        ),
        types.FunctionDeclaration(
            name='get_token_usage',
            description='回報今日三家 AI（Gemini、Claude、OpenAI）的 token 用量、費用與本月累計總費用',
        ),
    ]
)

SYSTEM_INSTRUCTION = """你是 Jarvis，泰國甲米棕櫚油廠的 AI 助理。
根據使用者的需求選擇最適合的工具執行。
若需求與可用工具無關，直接用繁體中文回答即可，不要強行使用工具。
回應時使用繁體中文。"""
