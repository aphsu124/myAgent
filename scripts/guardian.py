import sys
import subprocess
import os
import re
from google import genai
from modules import config, validator, line_handler

def run_task_with_guardian(task_name, command):
    """
    通用執行守護者：執行 -> 監聽 -> 診斷 -> 品質檢核
    """
    max_retries = 3
    attempt = 0
    success = False
    error_log = ""

    print(f"🛡️ [Jarvis Guardian] 開始監督任務: {task_name}")

    while attempt < max_retries and not success:
        attempt += 1
        print(f"🔄 嘗試第 {attempt}/{max_retries} 次執行...")
        
        # 1. 執行外部腳本
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            stdout = result.stdout
            stderr = result.stderr
            
            if result.returncode == 0:
                # 2. 腳本本身運行成功，進行「品質審查」
                # 這裡我們會根據不同的 task_name 讀取其產出檔案進行驗證
                is_valid = True
                msg = "通過基本校對"
                
                # 特定任務的品質門檻
                if "report" in task_name:
                    # 讀取偵錯檔案驗證
                    debug_path = os.path.join(config.BASE_DIR, "data/DEBUG_CONTENT.txt")
                    if os.path.exists(debug_path):
                        with open(debug_path, "r") as f: content = f.read()
                        is_valid, msg = validator.is_report_valid(content)
                
                elif "meeting" in task_name:
                    # 假設會議分析產出在特定路徑
                    meeting_path = os.path.join(config.BASE_DIR, "data/DEBUG_MEETING.txt")
                    if os.path.exists(meeting_path):
                        with open(meeting_path, "r") as f: content = f.read()
                        is_valid, msg = validator.is_meeting_valid(content)

                if is_valid:
                    print(f"✅ 任務 {task_name} 執行成功且通過品質審查。")
                    success = True
                else:
                    print(f"❌ 品質不合格: {msg}")
                    error_log = msg
            else:
                # 3. 腳本崩潰，進入 AI 診斷
                print(f"⚠️ 腳本崩潰 (Exit Code: {result.returncode})")
                error_log = stderr
                _diagnose_and_alert(task_name, error_log)
                
        except Exception as e:
            error_log = str(e)
            print(f"🚨 系統級錯誤: {error_log}")

    if not success:
        _final_failure_alert(task_name, error_log)

def _diagnose_and_alert(task, error):
    """調用 AI 分析錯誤原因並記錄"""
    client = genai.Client(api_key=config.GEMINI_API_KEY)
    prompt = f"任務 {task} 失敗了。錯誤日誌如下：\n{error}\n請簡短分析原因並提供 1 句修正建議。"
    try:
        resp = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        try:
            from modules.token_tracker import record as _tt
            _tt('google', 'gemini-2.0-flash', resp.usage_metadata.prompt_token_count or 0, resp.usage_metadata.candidates_token_count or 0)
        except Exception: pass
        analysis = resp.text if resp.text else "無法分析"
        print(f"🤖 AI 診斷建議: {analysis}")
    except Exception as e:
        print(f"⚠️ AI 診斷失敗 (不影響主流程): {e}")

def _final_failure_alert(task, error):
    """發送最終失敗警報到 LINE"""
    msg = f"🚨 任務多次重試失敗\n任務：{task}\n原因：{error[:100]}..."
    line_handler.send_push_notification("Jarvis Guardian 警報", "即時", 0, 0, msg)
    print(f"🛑 任務 {task} 已終止。")

if __name__ == "__main__":
    if len(sys.argv) > 2:
        task = sys.argv[1]
        cmd = " ".join(sys.argv[2:])
        run_task_with_guardian(task, cmd)
    else:
        print("使用方式: python3 guardian.py [任務名] [執行命令]")
