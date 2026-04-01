import os
import re

def is_content_valid(text):
    """檢查報告內容完整性"""
    if not text or len(text) < 800:
        return False, f"字數不足 ({len(text) if text else 0} 字，門檻 800)"
    
    # 檢查是否包含必要的大標題
    required_sections = ["一、", "二、", "三、"]
    for section in required_sections:
        if section not in text:
            return False, f"缺少必要章節: {section}"
            
    # 檢查是否有技術雜質
    blacklisted = ["DATA_JSON", "```json", "{", "}"]
    # 只檢查正文（排除第一行可能的數據行，如果有的話）
    body = "\n".join(text.split('\n')[1:])
    for word in blacklisted:
        if word in body:
            return False, f"正文包含技術雜質: {word}"
            
    return True, "內容檢核通過"

def is_data_valid(data):
    """檢查價格數據邏輯"""
    ffb = data.get('ffb', 0)
    cpo = data.get('cpo', 0)
    
    if not ffb or float(ffb) <= 0:
        return False, "FFB 數據異常 (為 0 或負數)"
    if not cpo or float(cpo) <= 0:
        return False, "CPO 數據異常 (為 0 或負數)"
        
    return True, "數據邏輯通過"

def is_web_ready(html_path):
    """確認網頁檔案是否寫入成功且完整"""
    if not os.path.exists(html_path):
        return False, "網頁檔案不存在"
    
    size = os.path.getsize(html_path)
    if size < 2000: # 正常網頁包含樣式應大於 2KB
        return False, f"網頁檔案異常過小 ({size} bytes)"
        
    return True, "網頁校對通過"
