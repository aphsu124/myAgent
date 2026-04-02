import os
import re

def is_meeting_valid(text):
    """檢查會議分析品質：必須具備主題、重點、結論"""
    if not text: return False, "內容為空"
    
    requirements = {
        "會議主題": ["會議主題", "主題", "Subject"],
        "重點內容": ["重點內容", "重點摘要", "Key Points", "主要議題"],
        "議題結論": ["議題結論", "決策", "Conclusions", "決議", "待辦事項"]
    }
    
    missing = []
    for label, keywords in requirements.items():
        found = False
        for kw in keywords:
            if kw in text:
                found = True
                break
        if not found:
            missing.append(label)
            
    if missing:
        return False, f"缺少必要區塊: {', '.join(missing)}"
    
    if len(text) < 300:
        return False, "分析內容過於簡略 (低於 300 字)"
        
    return True, "會議分析品質達標"

def is_report_valid(text):
    """檢查市場報告品質 (V3 語義優先模式)"""
    if not text or len(text) < 500: 
        return False, f"報告字數不足 ({len(text) if text else 0} < 500)"
    
    # 深度特徵檢查
    keywords = ["影響", "風險", "建議", "策略", "動態"]
    found_keywords = [k for k in keywords if k in text]
    if len(found_keywords) < 2:
        return False, f"缺乏管理深度 (僅偵測到: {', '.join(found_keywords)})"

    # 結構檢查 (彈性匹配 一、二、 或 1. 2.)
    if not (re.search(r'[一1][.、]', text) and re.search(r'[二2][.、]', text)):
        return False, "缺少必要分析章節 (需包含至少兩個章節)"

    if "DATA_JSON" in text: 
        return False, "包含技術雜質 (DATA_JSON 未清理乾淨)"
        
    return True, "市場報告品質通過 (V3)"

def is_translation_valid(path):
    """檢查翻譯產出"""
    if not os.path.exists(path): return False, "產出檔案不存在"
    if os.path.getsize(path) < 100: return False, "檔案大小異常 (過小)"
    return True, "翻譯產出通過"

def is_data_valid(data):
    """檢查價格數據邏輯"""
    try:
        ffb = float(data.get('ffb', 0))
        cpo = float(data.get('cpo', 0))
        if ffb <= 0 or cpo <= 0: return False, "價格數據不可為 0"
        return True, "數據正確"
    except: return False, "格式錯誤"
