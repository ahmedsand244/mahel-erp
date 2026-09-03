from django.shortcuts import redirect
from django.urls import reverse

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
            path.startswith('/login/') or
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
