import os
import sys
import socket
import threading
import time
import urllib.request
import webview

def get_local_ip():
    """احضار عنوان الـ IP الداخلي للجهاز على شبكة الـ Wi-Fi"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'

def check_internet(url='https://webservises.pythonanywhere.com', timeout=1.5):
    """التحقق من توفر اتصال الإنترنت بالسيرفر السحابي"""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'AlNamaa-Desktop/1.0'})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status < 500
    except Exception:
        return False

def start_django_server():
    """تشغيل خادم تطبيق النماء ERP في الخلفية على المنفذ 8000"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core_project.settings')
    try:
        from django.core.management import execute_from_command_line
        # Run server listening on 0.0.0.0 so both laptop and local network phones can access
        execute_from_command_line(['manage.py', 'runserver', '0.0.0.0:8000', '--noreload'])
    except Exception as e:
        print(f"Error starting Django server: {e}")

def main():
    # 1. Start local Django server in background
    server_thread = threading.Thread(target=start_django_server, daemon=True)
    server_thread.start()
    time.sleep(1.5)

    local_ip = get_local_ip()
    local_url = 'http://127.0.0.1:8000'
    cloud_url = 'https://webservises.pythonanywhere.com'

    target_url = os.environ.get('APP_URL')
    if len(sys.argv) > 1:
        arg = sys.argv[1].strip()
        if arg.lower() in ('local', 'offline'):
            target_url = local_url
        elif arg.lower() in ('cloud', 'online'):
            target_url = cloud_url
        else:
            target_url = arg

    if not target_url:
        # Auto-detect internet connection
        print("🔍 جاري فحص اتصال الإنترنت بالسيرفر السحابي...")
        if check_internet(cloud_url, timeout=1.5):
            target_url = cloud_url
            mode_label = "🌐 السحابي (متصل بالإنترنت)"
        else:
            target_url = local_url
            mode_label = "⚡ المحلي (يعمل أوفلاين بدون إنترنت بنجاح)"
    else:
        mode_label = "المحلي أوفلاين" if target_url == local_url else "السحابي"

    title = f"نظام النماء ERP - {mode_label}"
    
    print("=" * 60)
    print("🚀 تم تشغيل تطبيق النماء ERP لسطح المكتب بنجاح!")
    print(f"📌 وضع التشغيل: {mode_label}")
    print(f"🌐 الرابط النشط: {target_url}")
    print(f"📱 رابط الموبايل من داخل المحل (نفس الـ Wi-Fi): http://{local_ip}:8000")
    print("=" * 60)

    # 2. Create Native Desktop Application Window
    window = webview.create_window(
        title=title,
        url=target_url,
        width=1366,
        height=768,
        resizable=True,
        min_size=(1024, 700),
        confirm_close=True
    )
    
    webview.start(private_mode=False)

if __name__ == '__main__':
    main()
