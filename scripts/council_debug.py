import sys
from modules.ai_factory import AIFactory

def main():
    if len(sys.argv) < 2:
        print("使用方式: python3 scripts/council_debug.py \"錯誤訊息或描述\"")
        return

    query = sys.argv[1]
    factory = AIFactory()

    print("\n🏛️  **Jarvis AI 議會正在進行會診...**")
    print("-" * 50)

    # 1. 諮詢 Gemini
    print("🔍 正在獲取 Google Gemini 的分析...")
    gemini_res = factory.ask_gemini(f"請針對此 Bug 提供專業建議：{query}")

    # 2. 諮詢 Claude
    print("🎭 正在獲取 Anthropic Claude 的分析...")
    claude_res = factory.ask_claude(f"你是一位資深工程師，請深度分析此問題並提供修正代碼：{query}")

    # 3. 諮詢 ChatGPT
    print("🤖 正在獲取 OpenAI ChatGPT 的分析...")
    chatgpt_res = factory.ask_chatgpt(f"請檢查此報錯的常見原因與解決方案：{query}")

    # 4. 總結報告
    report = f"""
# 🏛️ Jarvis AI 議會：Bug 診斷報告

## 🔴 問題描述
{query}

---

## 🔍 Google Gemini 的觀點 (數據與搜尋專家)
{gemini_res}

---

## 🎭 Anthropic Claude 的觀點 (邏輯與代碼專家)
{claude_res}

---

## 🤖 OpenAI ChatGPT 的觀點 (通用解決方案專家)
{chatgpt_res}

---

## 💡 Jarvis 綜合建議
根據會診結果，建議優先執行 Claude 提供的代碼修正，並參考 ChatGPT 提到的環境設定檢查。
"""
    
    with open("DEBUG_REPORT.md", "w", encoding="utf-8") as f:
        f.write(report)
    
    print("-" * 50)
    print("✅ 會診結束！診斷報告已生成至: DEBUG_REPORT.md")

if __name__ == "__main__":
    main()
