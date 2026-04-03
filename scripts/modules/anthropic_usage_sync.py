"""
anthropic_usage_sync.py

從 Anthropic Admin API 同步今日用量，補捉 Claude Code CLI 的 token 消耗。
原理：API 回傳的全日累計 - 本地 DB 已記錄的 api_factory 用量 = Claude Code CLI 用量

需要在 .env 設定 ANTHROPIC_ADMIN_KEY=sk-ant-admin-...
（從 Claude Console → API Keys → 建立 Admin Key）
"""
import os
import json
import datetime
import requests
from . import token_tracker as tt

BASE_DIR        = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SYNC_STATE_PATH = os.path.join(BASE_DIR, 'data', 'anthropic_sync.json')

def _load_state():
    if os.path.exists(SYNC_STATE_PATH):
        try:
            with open(SYNC_STATE_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def _save_state(state):
    try:
        with open(SYNC_STATE_PATH, 'w') as f:
            json.dump(state, f)
    except Exception as e:
        print(f"⚠️ anthropic_sync state 儲存失敗: {e}")

def _get_local_anthropic_totals(today):
    """查本地 DB 今日 provider=anthropic 的累計 token 數"""
    import sqlite3
    try:
        conn = sqlite3.connect(tt.DB_PATH)
        rows = conn.execute('''
            SELECT SUM(input_tokens), SUM(output_tokens)
            FROM usage
            WHERE provider='anthropic' AND timestamp >= ?
        ''', (today,)).fetchone()
        conn.close()
        return (rows[0] or 0), (rows[1] or 0)
    except Exception:
        return 0, 0

def sync_today():
    """同步今日 Claude Code CLI 用量至本地 DB（每次呼叫只記錄增量）"""
    admin_key = os.getenv('ANTHROPIC_ADMIN_KEY')
    if not admin_key:
        return

    today = datetime.date.today().isoformat()
    state = _load_state()
    prev = state.get(today, {
        'api_input': 0, 'api_output': 0,
        'local_input': 0, 'local_output': 0,
    })

    # ── 查詢 Anthropic API ──
    try:
        r = requests.get(
            'https://api.anthropic.com/v1/organizations/usage_report/messages',
            headers={
                'x-api-key': admin_key,
                'anthropic-version': '2023-06-01',
            },
            params={'start_date': today, 'end_date': today},
            timeout=10,
        )
    except Exception as e:
        print(f"⚠️ Anthropic sync 請求失敗: {e}")
        return

    if r.status_code != 200:
        print(f"⚠️ Anthropic sync 失敗: HTTP {r.status_code}")
        return

    data = r.json()
    api_input_now  = 0
    api_output_now = 0
    for item in data.get('results', []):
        api_input_now  += (item.get('input_tokens', 0)
                           + item.get('cache_read_input_tokens', 0)
                           + item.get('cache_creation_input_tokens', 0))
        api_output_now += item.get('output_tokens', 0)

    # ── 查本地 DB 目前累計 ──
    local_input_now, local_output_now = _get_local_anthropic_totals(today)

    # ── 計算 Claude Code CLI 增量 ──
    new_api_in  = api_input_now  - prev['api_input']
    new_api_out = api_output_now - prev['api_output']
    new_loc_in  = local_input_now  - prev['local_input']
    new_loc_out = local_output_now - prev['local_output']

    cc_in  = max(0, new_api_in  - new_loc_in)
    cc_out = max(0, new_api_out - new_loc_out)

    if cc_in > 0 or cc_out > 0:
        tt.record('anthropic', 'claude-code-cli', cc_in, cc_out)
        print(f"🔄 Claude Code CLI 同步：+{cc_in:,} input / +{cc_out:,} output tokens")

    # ── 更新 state（local 需加上剛記錄的量）──
    state[today] = {
        'api_input':   api_input_now,
        'api_output':  api_output_now,
        'local_input':  local_input_now  + cc_in,
        'local_output': local_output_now + cc_out,
    }
    _save_state(state)
