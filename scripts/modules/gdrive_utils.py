import os
import io
import mimetypes
import pandas as pd
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload, MediaIoBaseUpload
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()

SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets',
]
CREDENTIALS_PATH = os.getenv(
    "GDRIVE_CREDENTIALS_PATH",
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "config/gdrive_credentials.json")
)

BASE_DIR_UTILS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OAUTH_TOKEN_PATH = os.path.join(BASE_DIR_UTILS, 'config/oauth_token.json')

_drive_service = None
_user_drive_service = None

def _get_user_drive_service():
    """使用 OAuth2 使用者憑證（用於新建檔案，空間計入使用者帳號）"""
    global _user_drive_service
    if _user_drive_service is not None:
        return _user_drive_service
    if not os.path.exists(OAUTH_TOKEN_PATH):
        return None
    try:
        from google.oauth2.credentials import Credentials as UserCredentials
        from google.auth.transport.requests import Request
        # 僅用 drive scope（token 授權時只申請此 scope）
        _DRIVE_SCOPE = ['https://www.googleapis.com/auth/drive']
        creds = UserCredentials.from_authorized_user_file(OAUTH_TOKEN_PATH, _DRIVE_SCOPE)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(OAUTH_TOKEN_PATH, 'w') as f:
                f.write(creds.to_json())
        _user_drive_service = build('drive', 'v3', credentials=creds)
        return _user_drive_service
    except Exception as e:
        print(f"⚠️ OAuth2 使用者憑證載入失敗: {e}")
        return None

def _get_drive_service():
    """單例：整個程序生命週期只建立一次連線"""
    global _drive_service
    if _drive_service is None:
        try:
            creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES)
            _drive_service = build('drive', 'v3', credentials=creds)
        except Exception as e:
            print(f"⚠️ Google Drive 連線失敗: {e}")
            return None
    return _drive_service

def find_file_id(filename, folder_id):
    """在指定資料夾中尋找檔案，回傳 file_id 或 None"""
    try:
        svc = _get_drive_service()
        if not svc: return None
        q = f"name='{filename}' and '{folder_id}' in parents and trashed=false"
        res = svc.files().list(q=q, fields="files(id, name)").execute()
        files = res.get('files', [])
        return files[0]['id'] if files else None
    except Exception as e:
        print(f"⚠️ Drive 搜尋失敗 ({filename}): {e}")
        return None

def upload_file(local_path, folder_id, mime_type=None):
    """上傳本地檔案至 Drive（已存在則更新，不存在則新建）。回傳 file_id"""
    try:
        svc = _get_drive_service()
        if not svc: return None
        filename = os.path.basename(local_path)
        if not mime_type:
            mime_type, _ = mimetypes.guess_type(local_path)
            mime_type = mime_type or 'application/octet-stream'
        media = MediaFileUpload(local_path, mimetype=mime_type)
        existing_id = find_file_id(filename, folder_id)
        if existing_id:
            svc.files().update(fileId=existing_id, media_body=media).execute()
            print(f"🔄 Drive 更新: {filename}")
            return existing_id
        else:
            meta = {'name': filename, 'parents': [folder_id]}
            f = svc.files().create(body=meta, media_body=media, fields='id').execute()
            print(f"⬆️  Drive 上傳: {filename}")
            return f.get('id')
    except Exception as e:
        print(f"⚠️ Drive 上傳失敗 ({local_path}): {e}")
        return None

def create_file(local_path, folder_id, mime_type=None):
    """用 OAuth2 使用者憑證新建檔案（每次都建新的，保留歷史）。回傳 file_id"""
    if not mime_type:
        mime_type, _ = mimetypes.guess_type(local_path)
        mime_type = mime_type or 'application/octet-stream'
    filename = os.path.basename(local_path)
    svc = _get_user_drive_service()
    if not svc:
        print(f"⚠️ OAuth token 不存在，改用 upload_file() fallback")
        return upload_file(local_path, folder_id, mime_type)
    try:
        media = MediaFileUpload(local_path, mimetype=mime_type)
        meta  = {'name': filename, 'parents': [folder_id]}
        f = svc.files().create(body=meta, media_body=media, fields='id').execute()
        print(f"⬆️  Drive 新建（使用者帳號）: {filename}")
        return f.get('id')
    except Exception as e:
        print(f"⚠️ Drive 新建失敗 ({filename}): {e}")
        return None

def upload_bytes(content, filename, folder_id, mime_type):
    """直接上傳 bytes 物件，不落地磁碟（適用 PNG、PDF 等）。回傳 file_id"""
    try:
        svc = _get_drive_service()
        if not svc: return None
        buf = io.BytesIO(content) if isinstance(content, bytes) else content
        buf.seek(0)
        media = MediaIoBaseUpload(buf, mimetype=mime_type)
        existing_id = find_file_id(filename, folder_id)
        if existing_id:
            svc.files().update(fileId=existing_id, media_body=media).execute()
            print(f"🔄 Drive 更新: {filename}")
            return existing_id
        else:
            meta = {'name': filename, 'parents': [folder_id]}
            f = svc.files().create(body=meta, media_body=media, fields='id').execute()
            print(f"⬆️  Drive 上傳: {filename}")
            return f.get('id')
    except Exception as e:
        print(f"⚠️ Drive bytes 上傳失敗 ({filename}): {e}")
        return None

def download_file(file_id, local_path):
    """從 Drive 下載檔案至本地路徑。回傳 True/False"""
    try:
        svc = _get_drive_service()
        if not svc: return False
        req = svc.files().get_media(fileId=file_id)
        with open(local_path, 'wb') as f:
            downloader = MediaIoBaseDownload(f, req)
            done = False
            while not done:
                _, done = downloader.next_chunk()
        return True
    except Exception as e:
        print(f"⚠️ Drive 下載失敗 ({file_id}): {e}")
        return False

def read_text_file(file_id):
    """直接讀取 Drive 上 txt 檔案內容，不落地。回傳字串或 None"""
    try:
        svc = _get_drive_service()
        if not svc: return None
        content = svc.files().get_media(fileId=file_id).execute()
        return content.decode('utf-8') if isinstance(content, bytes) else content
    except Exception as e:
        print(f"⚠️ Drive 讀取文字失敗 ({file_id}): {e}")
        return None

def write_text_file(file_id, content):
    """覆寫 Drive 上已存在的 txt 檔案內容。回傳 True/False"""
    try:
        svc = _get_drive_service()
        if not svc: return False
        buf = io.BytesIO(content.encode('utf-8'))
        media = MediaIoBaseUpload(buf, mimetype='text/plain')
        svc.files().update(fileId=file_id, media_body=media).execute()
        return True
    except Exception as e:
        print(f"⚠️ Drive 寫入文字失敗 ({file_id}): {e}")
        return False

def read_excel_to_dataframe(file_id):
    """從 Drive 下載 xlsx 至記憶體，直接回傳 DataFrame（不落地）"""
    try:
        svc = _get_drive_service()
        if not svc: return None
        req = svc.files().get_media(fileId=file_id)
        buf = io.BytesIO()
        downloader = MediaIoBaseDownload(buf, req)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        buf.seek(0)
        return pd.read_excel(buf)
    except Exception as e:
        print(f"⚠️ Drive 讀取 Excel 失敗 ({file_id}): {e}")
        return None

def write_dataframe_to_excel(df, file_id, apply_style_fn=None):
    """將 DataFrame 存為 xlsx 上傳至 Drive（可選套用 openpyxl 樣式）。回傳 True/False"""
    try:
        svc = _get_drive_service()
        if not svc: return False
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
            if apply_style_fn:
                apply_style_fn(writer.book)
        buf.seek(0)
        media = MediaIoBaseUpload(buf, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        svc.files().update(fileId=file_id, media_body=media).execute()
        print(f"✅ Drive Excel 更新成功 ({file_id})")
        return True
    except Exception as e:
        print(f"⚠️ Drive 寫入 Excel 失敗 ({file_id}): {e}")
        return False

_sheets_service = None

def _get_sheets_service():
    """單例：Sheets API 連線"""
    global _sheets_service
    if _sheets_service is None:
        try:
            creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES)
            _sheets_service = build('sheets', 'v4', credentials=creds)
        except Exception as e:
            print(f"⚠️ Google Sheets 連線失敗: {e}")
            return None
    return _sheets_service

def _get_sheet_name_by_gid(spreadsheet_id, gid):
    """由 gid（數字）反查 Sheet 分頁名稱"""
    try:
        svc = _get_sheets_service()
        if not svc: return None
        meta = svc.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        for s in meta.get('sheets', []):
            if str(s['properties']['sheetId']) == str(gid):
                return s['properties']['title']
    except Exception as e:
        print(f"⚠️ 無法取得 Sheet 名稱 (gid={gid}): {e}")
    return None

def read_sheet_to_dataframe(spreadsheet_id, gid=None):
    """從 Google Sheet 讀取資料為 DataFrame"""
    try:
        svc = _get_sheets_service()
        if not svc: return None
        sheet_name = _get_sheet_name_by_gid(spreadsheet_id, gid) if gid else None
        range_name = sheet_name if sheet_name else 'Sheet1'
        result = svc.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id, range=range_name
        ).execute()
        values = result.get('values', [])
        if not values: return pd.DataFrame()
        headers = values[0]
        rows = [row + [''] * (len(headers) - len(row)) for row in values[1:]]
        return pd.DataFrame(rows, columns=headers)
    except Exception as e:
        print(f"⚠️ Sheets 讀取失敗 ({spreadsheet_id}): {e}")
        return None

def write_dataframe_to_sheet(df, spreadsheet_id, gid=None):
    """將 DataFrame 寫回 Google Sheet（覆寫全表）"""
    try:
        svc = _get_sheets_service()
        if not svc: return False
        sheet_name = _get_sheet_name_by_gid(spreadsheet_id, gid) if gid else None
        range_name = sheet_name if sheet_name else 'Sheet1'
        values = [df.columns.tolist()] + df.fillna('').astype(str).values.tolist()
        svc.spreadsheets().values().clear(
            spreadsheetId=spreadsheet_id, range=range_name
        ).execute()
        svc.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"{range_name}!A1",
            valueInputOption='RAW',
            body={'values': values}
        ).execute()
        print(f"✅ Sheets 更新成功 ({spreadsheet_id})")
        return True
    except Exception as e:
        print(f"⚠️ Sheets 寫入失敗 ({spreadsheet_id}): {e}")
        return False

def append_row_to_sheet(row_values, spreadsheet_id, gid=None):
    """在 Google Sheet 底部附加一行（不動現有資料）。回傳 True/False"""
    try:
        svc = _get_sheets_service()
        if not svc: return False
        sheet_name = _get_sheet_name_by_gid(spreadsheet_id, gid) if gid else 'Sheet1'
        range_name = sheet_name or 'Sheet1'
        svc.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=f"{range_name}!A1",
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body={'values': [row_values]}
        ).execute()
        return True
    except Exception as e:
        print(f"⚠️ Sheets 附加行失敗 ({spreadsheet_id}): {e}")
        return False

def update_row_in_sheet(df_row_index, row_values, spreadsheet_id, gid=None):
    """只更新 Google Sheet 中的特定一行（不動其他資料）。
    df_row_index 為 DataFrame 的 0-based index（不含標題列）。回傳 True/False"""
    try:
        svc = _get_sheets_service()
        if not svc: return False
        sheet_name = _get_sheet_name_by_gid(spreadsheet_id, gid) if gid else 'Sheet1'
        range_name = sheet_name or 'Sheet1'
        # +1 for header row, +1 because Sheets is 1-indexed
        sheet_row = df_row_index + 2
        svc.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"{range_name}!A{sheet_row}",
            valueInputOption='RAW',
            body={'values': [row_values]}
        ).execute()
        return True
    except Exception as e:
        print(f"⚠️ Sheets 更新行失敗 (row={df_row_index}): {e}")
        return False

def delete_file(file_id):
    """刪除 Drive 上的檔案（等同於「標記為已處理」）。回傳 True/False"""
    try:
        svc = _get_drive_service()
        if not svc: return False
        svc.files().delete(fileId=file_id).execute()
        return True
    except Exception as e:
        print(f"⚠️ Drive 刪除失敗 ({file_id}): {e}")
        return False

def find_file_across_drive(filename):
    """跨所有 Service Account 有權限的資料夾搜尋檔案名稱。回傳 [{'id', 'name', 'parents'}]"""
    try:
        svc = _get_drive_service()
        if not svc: return []
        q = f"name='{filename}' and trashed=false"
        res = svc.files().list(q=q, fields="files(id, name, parents)").execute()
        return res.get('files', [])
    except Exception as e:
        print(f"⚠️ Drive 全域搜尋失敗 ({filename}): {e}")
        return []

def list_files_in_folder(folder_id, extensions=None):
    """列出資料夾中的檔案，回傳 [{'id': ..., 'name': ...}]"""
    try:
        svc = _get_drive_service()
        if not svc: return []
        q = f"'{folder_id}' in parents and trashed=false"
        res = svc.files().list(q=q, fields="files(id, name)").execute()
        files = res.get('files', [])
        if extensions:
            files = [f for f in files if any(f['name'].endswith(ext) for ext in extensions)]
        return files
    except Exception as e:
        print(f"⚠️ Drive 列出檔案失敗 ({folder_id}): {e}")
        return []
