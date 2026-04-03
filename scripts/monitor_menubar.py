import os
import sys
import subprocess
import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, 'scripts'))

from AppKit import NSBundle
NSBundle.mainBundle().infoDictionary()['LSUIElement'] = '1'

import rumps
from modules.token_tracker import get_today_summary, get_month_summary, get_month_total_cost, WARN_THRESHOLD, ALERT_THRESHOLD

# 付費模型（Claude/OpenAI）月費用警告門檻（USD）
COST_BUDGET     = 20.0
COST_WARN_USD   = 16.0   # 80% of $20 → 🟡
COST_ALERT_USD  = 18.0   # 90% of $20 → 🔴

def fmt_cost(usd):
    """自動選擇最短的金額格式：< $1 用分，>= $1 用美元"""
    if usd < 1.0:
        return f"{usd * 100:.1f}¢"
    return f"${usd:.2f}"

PROVIDER_SHORT = {
    'google':    'G',
    'anthropic': 'C',
    'openai':    'O',
}

class JarvisMonitor(rumps.App):
    def __init__(self):
        super().__init__('🟢 Monitor', quit_button=None)
        self.menu = [
            rumps.MenuItem('詳細資訊', callback=None),
            None,
            rumps.MenuItem('開啟儀表板', callback=self.open_dashboard),
            None,
            rumps.MenuItem('結束', callback=rumps.quit_application),
        ]
        self._last_alert = {}
        self.update(None)

    @rumps.timer(30)
    def update(self, _):
        try:
            try:
                from modules.anthropic_usage_sync import sync_today
                sync_today()
            except Exception:
                pass

            summary       = get_today_summary()
            month_summary = get_month_summary()
            month_total   = get_month_total_cost()

            if not summary:
                self.title = '⚪ No data'
                self.menu['詳細資訊'].title = '尚無 API 呼叫紀錄'
                return

            # ── 本月各 provider 累計費用 ──
            month_cost_by_provider = {}
            for d in month_summary:
                month_cost_by_provider[d['provider']] = \
                    month_cost_by_provider.get(d['provider'], 0) + d['cost_usd']

            # ── Menu Bar 標題（緊湊格式）──
            provider_order = ['google', 'anthropic', 'openai']
            summary_map    = {d['provider']: d for d in summary}
            parts = []
            for prov in provider_order:
                d = summary_map.get(prov)
                if not d:
                    continue
                short        = PROVIDER_SHORT.get(prov, prov[0].upper())
                month_cost   = month_cost_by_provider.get(prov, 0)
                pct          = d['usage_percent']

                # 顯示值：Gemini 用今日 %，Claude/OpenAI 用今日費用
                if d['has_free_tier']:
                    val = f"{pct:.0f}%" if pct is not None else '-'
                else:
                    val = fmt_cost(d['cost_usd'])

                # 燈號判斷：Gemini 看今日用量 %，Claude/OpenAI 看月累計費用
                # usage_percent 已是 0-100，直接與閾值*100 比較
                if d['has_free_tier']:
                    if pct is not None and pct >= ALERT_THRESHOLD * 100:
                        indicator = '🔴'
                    elif pct is not None and pct >= WARN_THRESHOLD * 100:
                        indicator = '🟡'
                    else:
                        indicator = ''
                else:
                    if month_cost >= COST_ALERT_USD:
                        indicator = '🔴'
                    elif month_cost >= COST_WARN_USD:
                        indicator = '🟡'
                    else:
                        indicator = ''

                parts.append(f"{indicator}{short}:{val}")

            self.title = ' '.join(parts) if parts else '⚪'

            # ── 下拉選單詳細資訊 ──
            lines = []
            for d in summary:
                inp  = d['input_tokens']
                out  = d['output_tokens']
                cost = d['cost_usd']
                pct  = d['usage_percent']
                pct_str = f" ({pct:.1f}%)" if pct is not None else ''
                lines.append(
                    f"{d['model']}{pct_str}  ↑{inp:,} ↓{out:,}  ${cost:.4f}"
                )
            lines.append('─' * 36)
            lines.append(f"本月累計：${month_total:.4f}")
            if os.getenv('ANTHROPIC_ADMIN_KEY'):
                lines.append('※ Claude Code 用量已同步（Admin API）')
            else:
                lines.append('※ Claude Code CLI 未設定 Admin Key')
            self.menu['詳細資訊'].title = '\n'.join(lines)

            # ── 系統通知（每個指標只通知一次）──
            for d in summary:
                model = d['model']
                prov  = d['provider']
                pct   = d['usage_percent']

                # Gemini：今日用量 %（usage_percent 已是 0-100）
                if pct is not None:
                    last = self._last_alert.get(model, 0)
                    if pct >= ALERT_THRESHOLD * 100 and last < ALERT_THRESHOLD * 100:
                        os.system(f'osascript -e \'display notification "{model} 用量已達 {pct:.0f}%！" with title "Jarvis Monitor 🔴"\'')
                        self._last_alert[model] = ALERT_THRESHOLD * 100
                    elif pct >= WARN_THRESHOLD * 100 and last < WARN_THRESHOLD * 100:
                        os.system(f'osascript -e \'display notification "{model} 用量達 {pct:.0f}%，請注意" with title "Jarvis Monitor 🟡"\'')
                        self._last_alert[model] = WARN_THRESHOLD * 100

                # Claude / OpenAI：月累計費用
                if not d['has_free_tier']:
                    mc   = month_cost_by_provider.get(prov, 0)
                    key  = f"{prov}_cost"
                    last = self._last_alert.get(key, 0)
                    if mc >= COST_ALERT_USD and last < COST_ALERT_USD:
                        os.system(f'osascript -e \'display notification "{PROVIDER_SHORT[prov]} 本月費用已達 ${mc:.2f}！" with title "Jarvis Monitor 🔴"\'')
                        self._last_alert[key] = COST_ALERT_USD
                    elif mc >= COST_WARN_USD and last < COST_WARN_USD:
                        os.system(f'osascript -e \'display notification "{PROVIDER_SHORT[prov]} 本月費用達 ${mc:.2f}，接近 $20" with title "Jarvis Monitor 🟡"\'')
                        self._last_alert[key] = COST_WARN_USD

        except Exception as e:
            self.title = '⚠️ Error'
            print(f"Monitor 更新失敗: {e}")

    def open_dashboard(self, _):
        subprocess.Popen(['open', 'http://localhost:5001'])


if __name__ == '__main__':
    print("📊 Jarvis Monitor Menu Bar 啟動")
    JarvisMonitor().run()
