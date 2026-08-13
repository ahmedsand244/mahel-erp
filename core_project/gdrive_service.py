import os
import json
import time
import requests
from datetime import datetime
from django.conf import settings
from django.core.management import call_command

def perform_gdrive_upload(backup_file_path=None):
    """
    يقوم بحفظ نسخة احتياطية فورية في مجلد backups بالمشروع،
    ويرفعها أوتوماتيكياً إلى Google Drive إذا كان الربط مفعلاً.
    """
    import shutil
    now_str = datetime.now().strftime('%Y_%m_%d_%H%M%S')
    backups_dir = os.path.join(settings.BASE_DIR, 'backups')
    os.makedirs(backups_dir, exist_ok=True)
    
    # 1. تحديد ملف قاعدة البيانات الأساسي
    if not backup_file_path:
        db_path = settings.DATABASES['default']['NAME']
        if isinstance(db_path, (str, os.PathLike)) and os.path.exists(db_path):
            backup_file_path = db_path

    if not backup_file_path or not os.path.exists(backup_file_path):
        return False, "ملف قاعدة البيانات غير موجود."

    filename = f"elnamaa_db_backup_{now_str}.sqlite3"
    local_saved_path = os.path.join(backups_dir, filename)

    try:
        shutil.copy2(backup_file_path, local_saved_path)
    except Exception as e:
        return False, f"فشل حفظ النسخة المحلية: {str(e)}"

    # فحص وحفظ النسخة تلقائياً في مجلد السحابة المباشر مثل OneDrive أو Google Drive Desktop
    cloud_synced = False
    cloud_msg = ""
    user_home = os.environ.get('USERPROFILE', '')
    possible_cloud_dirs = [
        os.path.join(user_home, 'OneDrive', 'Elnamaa_ERP_Backups'),
        os.path.join(user_home, 'Google Drive', 'Elnamaa_ERP_Backups'),
        r'G:\My Drive\Elnamaa_ERP_Backups',
    ]
    for c_dir in possible_cloud_dirs:
        parent_dir = os.path.dirname(c_dir)
        if os.path.exists(parent_dir):
            try:
                os.makedirs(c_dir, exist_ok=True)
                shutil.copy2(backup_file_path, os.path.join(c_dir, filename))
                cloud_synced = True
                cloud_msg = f" وتم رفعها تلقائياً إلى مجلد السحابة ({os.path.basename(parent_dir)}) ☁️"
                break
            except Exception:
                pass

    # 2. الترفيع السحابي لـ Google Drive إذا وجد Webhook
    gdrive_webhook_url = os.getenv('GDRIVE_WEBHOOK_URL', '').strip()
    if gdrive_webhook_url:
        try:
            with open(local_saved_path, 'rb') as f:
                file_bytes = f.read()
                import base64
                encoded_file = base64.b64encode(file_bytes).decode('utf-8')
                
            payload = {
                'filename': filename,
                'filedata': encoded_file,
                'mimeType': 'application/x-sqlite3'
            }
            res = requests.post(
                gdrive_webhook_url,
                data=json.dumps(payload),
                headers={'Content-Type': 'application/json'},
                timeout=60
            )

            if res.status_code == 200 and 'success' in res.text:
                return True, f"✅ تم حفظ النسخة الاحتياطية '{filename}' محلياً ورفعها بنجاح إلى Google Drive ☁️!"
            elif res.status_code == 401:
                return False, f"⚠️ حظر من جوجل (401)! يرجى تعديل النشر في Google Apps Script وتغيير 'من لديه صلاحية الوصول (Who has access)' إلى 'أي شخص (Anyone)' ثم الضغط على تحديث (Update)."
            else:
                return True, f"✅ تم حفظ النسخة الفورية '{filename}' في مجلد backups بالمشروع! (استجابة السحابة: كود {res.status_code})"
        except Exception as e:
            return True, f"✅ تم حفظ النسخة الفورية '{filename}' محلياً في مجلد backups! (تعذر الاتصال بـ Google Drive: {str(e)})"

    # 3. الترفيع السحابي عبر Service Account إذا وجد credentials.json
    credentials_path = os.path.join(settings.BASE_DIR, 'credentials.json')
    if os.path.exists(credentials_path):
        try:
            with open(credentials_path, 'r', encoding='utf-8') as f:
                creds = json.load(f)

            client_email = creds.get('client_email')
            private_key = creds.get('private_key')

            if client_email and private_key:
                import jwt
                now = int(time.time())
                payload = {
                    "iss": client_email,
                    "sub": client_email,
                    "aud": "https://oauth2.googleapis.com/token",
                    "exp": now + 3600,
                    "iat": now,
                    "scope": "https://www.googleapis.com/auth/drive.file"
                }
                token_jwt = jwt.encode(payload, private_key, algorithm="RS256")
                token_res = requests.post("https://oauth2.googleapis.com/token", data={
                    "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                    "assertion": token_jwt
                })
                token_data = token_res.json()
                access_token = token_data.get("access_token")

                if access_token:
                    metadata = {'name': filename, 'mimeType': 'application/x-sqlite3'}
                    files = {
                        'data': ('metadata', json.dumps(metadata), 'application/json; charset=UTF-8'),
                        'file': (filename, open(local_saved_path, 'rb'), 'application/x-sqlite3')
                    }
                    headers = {'Authorization': f'Bearer {access_token}'}
                    upload_res = requests.post(
                        'https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart',
                        headers=headers,
                        files=files
                    )
                    if upload_res.status_code in [200, 201]:
                        return True, f"✅ تم حفظ النسخة '{filename}' ورفعها بنجاح إلى Google Drive ☁️!"
        except Exception as e:
            pass

    if cloud_synced:
        return True, f"✅ تم إنشاء وحفظ النسخة '{filename}' بنجاح محلياً{cloud_msg}! 💾☁️"

    return True, f"✅ تم إنشاء وحفظ النسخة الاحتياطية الفورية '{filename}' بنجاح داخل مجلد المشروع (backups)! 💾"
