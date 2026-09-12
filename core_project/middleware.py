import time
import logging
from django.db import connection
from django.shortcuts import redirect
from django.urls import reverse

logger = logging.getLogger('telemetry')

class TelemetryAndSecurityMiddleware:
    """
    ميدلوير مراقبة الأداء المتقدم (Telemetry) وتعزيز الأمان (Security Hardening).
    يقيس وقت استجابة الطلبات وعدد استعلامات قاعدة البيانات بدقة عالية بالمللي ثانية،
    ويحقن ترويسات Server-Timing و X-Response-Time لمراقبة السرعة في أدوات المطورين،
    كما يفرض ترويسات أمان متقدمة لحماية الموقع من الثغرات الأمنية الشائعة.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.perf_counter()
        initial_queries = len(connection.queries)

        response = self.get_response(request)

        duration_ms = (time.perf_counter() - start_time) * 1000
        query_count = max(0, len(connection.queries) - initial_queries)

        # 1. Telemetry Headers (قياس الأداء والمراقبة)
        response['X-Response-Time'] = f"{duration_ms:.2f}ms"
        response['X-DB-Queries'] = str(query_count)
        response['Server-Timing'] = f'total;dur={duration_ms:.2f};desc="Total Time", db;desc="{query_count} queries"'

        # تسجيل تحذير في السجلات إذا كان الطلب بطيئاً (> 500ms) للمراقبة والتحسين المستمر
        if duration_ms > 500 and not request.path.startswith('/static/'):
            logger.warning(
                f"[TELEMETRY] Slow Request Detected: {request.method} {request.path} "
                f"took {duration_ms:.2f}ms with {query_count} DB queries"
            )

        # 2. Security Hardening Headers (سد الثغرات والحماية القصوى)
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'

        return response


class EnforceLoginMiddleware:
    """
    ميدلوير فرض تسجيل الدخول لحماية كافة صفحات النظام ERP،
    مع استثناء صفحة الدخول وروابط المشاركة العامة فقط.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        # 1. إذا كان المستخدم مسجلاً لدخوله بالفعل، اترك الطلب يمر
        if request.user.is_authenticated:
            return self.get_response(request)

        # 2. الاستثناءات المسموح بها بدون تسجيل دخول:
        # - صفحة تسجيل الدخول والخروج وإنشاء حساب جديد
        # - لوحة إدارة أدمن درانجو /admin/
        # - الملفات الاستاتيكية والميديا
        # - روابط المشاركة العامة للعملاء والتي تحتوي على /public/
        # - لوحة تحكم المالك (تتحقق من is_superuser داخلياً)
        if (
            path == '/' or
            path.startswith('/desktop/') or
            path.startswith('/login/') or
            path.startswith('/forgot-password/') or
            path.startswith('/logout/') or
            path.startswith('/register/') or
            path.startswith('/superadmin/') or
            path.startswith('/admin/') or
            path.startswith('/static/') or
            path.startswith('/media/') or
            path.startswith('/api/') or
            path == '/manifest.json' or
            path == '/sw.js' or
            '/public/' in path
        ):
            return self.get_response(request)

        # 3. توجيه باقي المحاولات غير المصرح بها إلى صفحة تسجيل الدخول
        login_url = reverse('login')
        return redirect(f"{login_url}?next={path}")
