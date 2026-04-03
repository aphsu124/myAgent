"""
一次性執行：授權 Google Drive OAuth2，產生 config/oauth_token.json
之後每次 token 過期會自動 refresh，不需重新跑此腳本。
"""
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIENT_FILE = os.path.join(BASE_DIR, 'config/oauth_client.json')
TOKEN_FILE  = os.path.join(BASE_DIR, 'config/oauth_token.json')

SCOPES = ['https://www.googleapis.com/auth/drive']

if not os.path.exists(CLIENT_FILE):
    print(f"❌ 找不到 {CLIENT_FILE}")
    print("   請先從 Google Cloud Console 下載 OAuth2 憑證並存至此路徑。")
    sys.exit(1)

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    print("❌ 缺少套件，請執行：pip3 install google-auth-oauthlib")
    sys.exit(1)

print("🌐 即將開啟瀏覽器進行 Google 授權...")
print("   請用你的 Google 帳號登入並點選「允許」。\n")

flow = InstalledAppFlow.from_client_secrets_file(CLIENT_FILE, SCOPES)
creds = flow.run_local_server(port=0)

with open(TOKEN_FILE, 'w') as f:
    f.write(creds.to_json())

print(f"\n✅ 授權完成！Token 已存至：{TOKEN_FILE}")
print("   之後 Drive 新建檔案將以你的 Google 帳號身份執行。")
