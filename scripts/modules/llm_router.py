"""
llm_router.py — 根據任務類型自動選擇最適合且有額度的模型
"""

# ── 路由表：任務類型 → 模型優先順序 ────────────────────────────
ROUTING_TABLE = {
    'code':      ['claude-sonnet-4-6', 'gpt-4o',           'gemini-2.5-flash'],
    'analysis':  ['claude-sonnet-4-6', 'gpt-4o',           'gemini-2.5-flash'],
    'translate': ['gemini-2.5-flash',  'claude-haiku-4-5', 'claude-sonnet-4-6'],
    'summary':   ['gemini-2.5-flash',  'claude-haiku-4-5', 'claude-sonnet-4-6'],
    'general':   ['gemini-2.5-flash',  'claude-haiku-4-5', 'claude-sonnet-4-6'],
}

# ── 關鍵字分類表 ─────────────────────────────────────────────────
CODE_KEYWORDS      = ['程式', '代碼', '代码', 'code', 'debug', '函數', '函数',
                      '錯誤', '错误', 'bug', '寫一個', '写一个', '腳本', '脚本',
                      'python', 'javascript', 'function', 'class', '寫程式']
TRANSLATE_KEYWORDS = ['翻譯', '翻译', 'translate', '中文', '英文', '泰文',
                      '日文', '韓文', '한국어', 'thai', '換成', '改成']
SUMMARY_KEYWORDS   = ['摘要', '總結', '总结', '重點', '重点', 'summarize',
                      '整理', '歸納', '归纳', '簡述', '简述']
ANALYSIS_KEYWORDS  = ['分析', '報告', '报告', '趨勢', '趋势', '市場', '市场',
                      '建議', '建议', '預測', '预测', '評估', '评估']

MODEL_TO_PROVIDER = {
    'gemini-2.5-flash': 'google',
    'claude-sonnet-4-6': 'anthropic',
    'claude-haiku-4-5':  'anthropic',
    'gpt-4o':            'openai',
}

# Claude / OpenAI 月費超過此值視為「額度吃緊」
COST_LIMIT_USD = 18.0

# ── 任務分類 ─────────────────────────────────────────────────────
def classify(text):
    t = text.lower()
    if any(k in t for k in CODE_KEYWORDS):      return 'code'
    if any(k in t for k in TRANSLATE_KEYWORDS): return 'translate'
    if any(k in t for k in SUMMARY_KEYWORDS):   return 'summary'
    if any(k in t for k in ANALYSIS_KEYWORDS):  return 'analysis'
    return 'general'

# ── 額度檢查 ─────────────────────────────────────────────────────
def is_available(model):
    """True = 此模型還有足夠額度可用"""
    try:
        from .token_tracker import get_usage_percent, get_month_summary
        if model.startswith('gemini'):
            pct = get_usage_percent(model)
            return pct is None or pct < 0.9
        else:
            provider = MODEL_TO_PROVIDER.get(model)
            if not provider:
                return True
            month = get_month_summary()
            cost  = sum(d['cost_usd'] for d in month if d['provider'] == provider)
            return cost < COST_LIMIT_USD
    except Exception:
        return True   # 查詢失敗時不阻擋

# ── 路由選擇 ─────────────────────────────────────────────────────
def route(text):
    """回傳 (task_type, selected_model)"""
    task = classify(text)
    for model in ROUTING_TABLE[task]:
        if is_available(model):
            return task, model
    return task, 'gemini-2.5-flash'   # 所有模型都吃緊時兜底

# ── 統一詢問入口 ─────────────────────────────────────────────────
def ask(text):
    """分類 → 選模型 → 呼叫 AI → 回傳 (答案, task_type, model_used)"""
    from .ai_factory import AIFactory
    task, model = route(text)
    factory = AIFactory()

    try:
        if model.startswith('gemini'):
            answer = factory.ask_gemini(text, model=model)
        elif model.startswith('claude'):
            answer = factory.ask_claude(text)
        elif model == 'gpt-4o':
            answer = factory.ask_chatgpt(text)
        else:
            answer = factory.ask_gemini(text)
    except Exception as e:
        answer = f"⚠️ {model} 呼叫失敗：{e}"

    return answer, task, model
