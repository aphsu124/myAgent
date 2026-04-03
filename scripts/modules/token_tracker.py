import os
import sqlite3
import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, 'data', 'token_usage.db')

# ── 價格表（每 1M tokens，USD）────────────────────────────────────
PRICE_TABLE = {
    'claude-sonnet-4-6':   {'input': 3.00,  'output': 15.00},
    'claude-haiku-4-5':    {'input': 0.80,  'output': 4.00},
    'gpt-4o':              {'input': 2.50,  'output': 10.00},
    'gpt-4o-mini':         {'input': 0.15,  'output': 0.60},
    'gemini-2.5-flash':    {'input': 0.075, 'output': 0.30},
    'gemini-2.0-flash':    {'input': 0.075, 'output': 0.30},
    'gemini-1.5-flash':    {'input': 0.075, 'output': 0.30},
}

# ── 免費額度上限（每日）──────────────────────────────────────────
FREE_LIMITS = {
    'gemini-2.5-flash': {'tpd': 1_000_000, 'rpd': 1500},
    'gemini-2.0-flash': {'tpd': 1_000_000, 'rpd': 1500},
    'gemini-1.5-flash': {'tpd': 1_000_000, 'rpd': 1500},
}

# ── 警告閾值 ────────────────────────────────────────────────────
WARN_THRESHOLD  = 0.80   # 80% → 黃色警告
ALERT_THRESHOLD = 0.90   # 90% → 紅色 + 系統通知

# ── 初始化資料庫 ────────────────────────────────────────────────
def _init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS usage (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp    TEXT    NOT NULL,
            provider     TEXT    NOT NULL,
            model        TEXT    NOT NULL,
            input_tokens  INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            cost_usd     REAL    DEFAULT 0.0
        )
    ''')
    conn.commit()
    conn.close()

_init_db()

# ── 計算費用 ────────────────────────────────────────────────────
def calculate_cost(model, input_tokens, output_tokens):
    price = PRICE_TABLE.get(model)
    if not price:
        return 0.0
    return (input_tokens * price['input'] + output_tokens * price['output']) / 1_000_000

# ── 記錄一次呼叫 ─────────────────────────────────────────────────
def record(provider, model, input_tokens, output_tokens):
    cost = calculate_cost(model, input_tokens, output_tokens)
    now  = datetime.datetime.now().isoformat()
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            'INSERT INTO usage (timestamp, provider, model, input_tokens, output_tokens, cost_usd) VALUES (?,?,?,?,?,?)',
            (now, provider, model, input_tokens, output_tokens, cost)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"⚠️ token_tracker 記錄失敗: {e}")

    _check_alert(model)

# ── 警告檢查 ────────────────────────────────────────────────────
def _check_alert(model):
    pct = get_usage_percent(model)
    if pct is None:
        return
    if pct >= ALERT_THRESHOLD:
        msg = f"{model} 今日用量已達 {int(pct*100)}%"
        os.system(f'osascript -e \'display notification "{msg}" with title "Jarvis Monitor ⚠️"\'')
        print(f"🔴 {msg}")
    elif pct >= WARN_THRESHOLD:
        print(f"🟡 {model} 今日用量 {int(pct*100)}%，接近上限")

# ── 查詢：今日各模型摘要 ─────────────────────────────────────────
def get_today_summary():
    today = datetime.date.today().isoformat()
    conn  = sqlite3.connect(DB_PATH)
    rows  = conn.execute('''
        SELECT model, provider,
               SUM(input_tokens), SUM(output_tokens), SUM(cost_usd)
        FROM usage
        WHERE timestamp >= ?
        GROUP BY model
    ''', (today,)).fetchall()
    conn.close()
    result = []
    for model, provider, inp, out, cost in rows:
        pct = get_usage_percent(model)
        result.append({
            'model':         model,
            'provider':      provider,
            'input_tokens':  inp  or 0,
            'output_tokens': out  or 0,
            'cost_usd':      round(cost or 0, 4),
            'usage_percent': round(pct * 100, 1) if pct is not None else None,
            'has_free_tier': model in FREE_LIMITS,
        })
    return result

# ── 查詢：本月各模型累計 ─────────────────────────────────────────
def get_month_summary():
    first_day = datetime.date.today().replace(day=1).isoformat()
    conn  = sqlite3.connect(DB_PATH)
    rows  = conn.execute('''
        SELECT model, provider,
               SUM(input_tokens), SUM(output_tokens), SUM(cost_usd)
        FROM usage
        WHERE timestamp >= ?
        GROUP BY model
    ''', (first_day,)).fetchall()
    conn.close()
    result = []
    for model, provider, inp, out, cost in rows:
        result.append({
            'model':         model,
            'provider':      provider,
            'input_tokens':  inp  or 0,
            'output_tokens': out  or 0,
            'cost_usd':      round(cost or 0, 4),
        })
    return result

# ── 查詢：當月總費用 ─────────────────────────────────────────────
def get_month_total_cost():
    first_day = datetime.date.today().replace(day=1).isoformat()
    conn  = sqlite3.connect(DB_PATH)
    total = conn.execute(
        'SELECT SUM(cost_usd) FROM usage WHERE timestamp >= ?', (first_day,)
    ).fetchone()[0]
    conn.close()
    return round(total or 0, 4)

# ── 查詢：今日用量百分比（僅有免費額度的模型） ───────────────────
def get_usage_percent(model):
    limit = FREE_LIMITS.get(model)
    if not limit:
        return None
    today = datetime.date.today().isoformat()
    conn  = sqlite3.connect(DB_PATH)
    row   = conn.execute('''
        SELECT SUM(input_tokens + output_tokens)
        FROM usage WHERE model=? AND timestamp >= ?
    ''', (model, today)).fetchone()
    conn.close()
    used = row[0] or 0
    return min(used / limit['tpd'], 1.0)
