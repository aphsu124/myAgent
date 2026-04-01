import os
import re

def is_content_valid(text, raw_source=""):
    """
    檢查報告內容的深度與通順度 (Council V3: 語義優先模式)
    """
    if not text or len(text) < 500:
        return False, "內容太短，分析深度不足"
    
    # 1. 結尾完整性
    last_chunk = text.strip()[-10:]
    if not re.search(r'[。！!」”*]', last_chunk):
        return False, "內容被截斷"

    # 2. 深度分析特徵檢查 (核心：管理層關心的詞彙)
    analysis_keywords = ["影響", "預計", "建議", "風險", "動態", "關鍵", "挑戰", "走勢", "策略"]
    found_count = sum(1 for word in analysis_keywords if word in text)
    if found_count < 3:
        return False, f"分析深度不足 (關鍵特徵字過少: {found_count})"

    # 3. 雜質檢查
    if "DATA_JSON" in text or "```json" in text:
        return False, "包含技術雜質"
            
    return True, "內容檢核通過"

def is_data_valid(data):
    """數據邏輯檢查"""
    try:
        ffb = float(data.get('ffb', 0))
        cpo = float(data.get('cpo', 0))
        if ffb <= 0 or cpo <= 0: return False, "價格數據不可為 0"
        return True, "數據正確"
    except: return False, "數據格式錯誤"

def is_web_ready(html_path):
    """確認網頁發布狀態"""
    return os.path.exists(html_path) and os.path.getsize(html_path) > 1500
