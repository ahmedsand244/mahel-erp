import os
import sys
import socket
import threading
import time
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
    # 1. Start Django server in background thread
    server_thread = threading.Thread(target=start_django_server, daemon=True)
    server_thread.start()
    
    # Wait 2 seconds for server startup
    time.sleep(2)
    
    local_ip = get_local_ip()
    title = f"نظام النماء ERP - إدارة المحل والمخازن (رابط الموبايل: http://{local_ip}:8000)"
    
    print("=" * 60)
    print("🚀 تم تشغيل تطبيق النماء ERP لسطح المكتب بنجاح!")
    print(f"💻 رابط الجهاز المحلي: http://127.0.0.1:8000")
    print(f"📱 رابط الموبايل من داخل المحل (نفس الـ Wi-Fi): http://{local_ip}:8000")
    print("=" * 60)

    # 2. Create Native Desktop Application Window
    window = webview.create_window(
        title=title,
        url='http://127.0.0.1:8000',
        width=1366,
        height=768,
        resizable=True,
        min_size=(1024, 700),
        confirm_close=True
    )
    
    webview.start(private_mode=False)

if __name__ == '__main__':
    main()
