"""
breaking_news.py — 棕櫚油即時重要訊息掃描與 Telegram 推播

每 30 分鐘由 crontab 呼叫，或由 jarvis_tools.search_breaking_news() 手動觸發。
靜音模式：無重要事件時不發送任何訊息。
"""

import os
import sys
import json
import hashlib
import datetime
import requests
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from modules import config

IMPORTANCE_THRESHOLD = 4

HIGH_IMPACT_KEYWORDS = {
    # 高衝擊（3分）
    "ban": 3, "禁令": 3, "禁止": 3,
    "crash": 3, "collapse": 3, "暴跌": 3, "崩盤": 3,
    "surge": 3, "soar": 3, "急漲": 3, "暴漲": 3,
    "emergency": 3, "緊急": 3,
    "halt": 3, "suspend": 3,
    # 中衝擊（2分）
    "export": 2, "levy": 2, "quota": 2, "tariff": 2,
    "flood": 2, "drought": 2, "typhoon": 2,
    "policy": 2, "政策": 2, "出口": 2,
    "record": 2, "historic": 2,
    "restriction": 2, "shortage": 2,
    # 低衝擊（1分）
    "rises": 1, "falls": 1, "higher": 1, "lower": 1,
    "outlook": 1, "forecast": 1, "production": 1,
}

CACHE_FILE = os.path.join(config.BASE_DIR, "data/breaking_news_sent.json")
CACHE_TTL_HOURS = 48


def fetch_news_with_sources():
    """從 Serper 搜尋過去 24 小時的棕櫚油新聞，回傳結構化清單"""
    url = "https://google.serper.dev/search"
    queries = [
        "palm oil price shock surge crash export ban CPO BMD",
        "Malaysia Indonesia palm oil policy flood harvest",
    ]
    items = []
    for q in queries:
        try:
            r = requests.post(
                url,
                headers={"X-API-KEY": config.SERPER_API_KEY},
                json={"q": q, "gl": "my", "hl": "en", "tbs": "qdr:d"},
                timeout=15,
            )
            if r.status_code == 200:
                for o in r.json().get("organic", []):
                    items.append({
                        "title": o.get("title", ""),
                        "snippet": o.get("snippet", ""),
                        "link": o.get("link", ""),
                        "source": o.get("source", ""),
                    })
        except requests.exceptions.Timeout:
            print(f"⚠️ Serper 搜尋逾時 (query: {q[:50]})")
        except Exception as e:
            print(f"⚠️ Serper 搜尋失敗: {e}")
    return items


def score_importance(items):
    """關鍵字加權評分，回傳分數 >= IMPORTANCE_THRESHOLD 的項目（去重後排序）"""
    scored = []
    seen_links = set()
    for item in items:
        if item["link"] in seen_links:
            continue
        seen_links.add(item["link"])
        text = (item["title"] + " " + item["snippet"]).lower()
        score = 0
        for kw, pts in HIGH_IMPACT_KEYWORDS.items():
            if kw.lower() in text:
                score += pts
        if score >= IMPORTANCE_THRESHOLD:
            item["score"] = score
            scored.append(item)
    return sorted(scored, key=lambda x: x["score"], reverse=True)


def load_sent_cache():
    """讀取已發送紀錄，清除超過 TTL 的過期項目"""
    if not os.path.exists(CACHE_FILE):
        return {}
    try:
        with open(CACHE_FILE, "r") as f:
            cache = json.load(f)
        now = datetime.datetime.now().timestamp()
        return {k: v for k, v in cache.items() if now - v < CACHE_TTL_HOURS * 3600}
    except Exception:
        return {}


def save_sent_cache(cache):
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(cache, f)
    except Exception as e:
        print(f"⚠️ 寫入快取失敗: {e}")


def make_hash(item):
    """取 title + snippet 前 60 字作為去重 key"""
    text = (item["title"] + item["snippet"])[:60]
    return hashlib.md5(text.encode()).hexdigest()


def shorten_url(long_url):
    """使用 TinyURL 縮短網址（免 API key）"""
    try:
        r = requests.get(
            f"https://tinyurl.com/api-create.php?url={long_url}",
            timeout=5,
        )
        if r.status_code == 200:
            short = r.text.strip()
            if short.startswith("http"):
                return short
    except Exception:
        pass
    return long_url


def translate_items(items):
    """用 Gemini 將新聞標題與摘要翻譯成繁體中文，回傳 JSON 格式確保解析可靠"""
    try:
        import json as _json
        import re as _re
        from google import genai
        client = genai.Client(api_key=config.GEMINI_API_KEY, http_options={'api_version': 'v1'})

        input_list = [
            {"id": i, "title": item["title"], "snippet": item.get("snippet", "")}
            for i, item in enumerate(items)
        ]
        prompt = (
            "你是專業翻譯。請將以下 JSON 陣列中每筆新聞的 title 和 snippet 翻譯成繁體中文，"
            "無論原文是英文、泰文、馬來文還是其他語言。\n"
            "直接回傳 JSON 陣列，格式與輸入相同（包含 id），不要加任何說明文字：\n\n"
            + _json.dumps(input_list, ensure_ascii=False)
        )
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={"max_output_tokens": 2048},
        )
        # 從回傳中提取 JSON（處理 Gemini 可能包的 markdown code block）
        raw = resp.text.strip()
        m = _re.search(r'\[.*\]', raw, flags=_re.DOTALL)
        if m:
            translated = _json.loads(m.group(0))
            for entry in translated:
                idx = entry.get("id")
                if idx is not None and idx < len(items):
                    if entry.get("title"):
                        items[idx]["zh_title"] = entry["title"]
                    if entry.get("snippet"):
                        items[idx]["zh_snippet"] = entry["snippet"]
    except Exception as e:
        print(f"⚠️ 翻譯失敗（將使用原文）: {e}")
    return items


def send_telegram(chat_id, text):
    """直接呼叫 Telegram Bot API 發送訊息"""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token or not chat_id:
        print("⚠️ 未設定 TELEGRAM_BOT_TOKEN 或 chat_id")
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id": chat_id, "text": text},
            headers={"Connection": "close"},
            timeout=15,
        )
    except Exception as e:
        print(f"⚠️ Telegram 發送失敗: {e}")


def format_and_push(items, chat_id):
    """翻譯為中文後格式化訊息並推送至 Telegram（最多 5 則）"""
    ict_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7)))
    time_str = ict_now.strftime("%Y-%m-%d %H:%M ICT")

    items = translate_items(items[:5])

    lines = ["🚨 棕櫚油即時快訊\n"]
    for item in items:
        short_url = shorten_url(item["link"])
        domain = item.get("source") or (
            item["link"].split("/")[2] if item.get("link") else ""
        )
        title = item.get("zh_title") or item["title"]
        snippet = item.get("zh_snippet") or item.get("snippet", "")
        lines.append(f"▪ {title}")
        if snippet:
            lines.append(f"  {snippet}")
        lines.append(f"  來源：{domain} | {short_url}\n")

    lines.append(f"⏱ 檢查時間：{time_str}")
    send_telegram(chat_id, "\n".join(lines)[:4000])


def check_and_push(force=False):
    """
    主入口：搜尋重要新聞，過濾已發送，有新重要訊息才推 Telegram。

    force=True：跳過重要性門檻，強制推播（手動觸發時使用）。
    回傳操作結果的描述字串。
    """
    items = fetch_news_with_sources()
    if not items:
        return "⚠️ Serper 未回傳任何結果"

    if force:
        # 強制模式：取前 3 筆，不看分數
        important = sorted(items, key=lambda x: len(x.get("snippet", "")), reverse=True)[:3]
    else:
        important = score_importance(items)
        if not important:
            return "✅ 無重要新聞（分數未達門檻）"

    # 防重複發送
    cache = load_sent_cache()
    new_items = [item for item in important if make_hash(item) not in cache]

    if not new_items:
        return "✅ 所有重要新聞已在近 48 小時內發送過"

    chat_id = config.TELEGRAM_ALLOWED_CHAT_ID
    format_and_push(new_items, chat_id)

    # 更新快取
    now = datetime.datetime.now().timestamp()
    for item in new_items:
        cache[make_hash(item)] = now
    save_sent_cache(cache)

    return f"✅ 已推播 {len(new_items)} 則重要新聞至 Telegram"


if __name__ == "__main__":
    result = check_and_push(force=False)
    print(result)
