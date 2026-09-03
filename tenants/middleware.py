"""
Tenant Middleware — يحدد الـ Tenant الحالي من الـ URL.

روابط الشكل:  /t/{slug}/...
مثال:         /t/mahel/pos/
              /t/nile-farm/inventory/

يحفظ الـ Tenant في:
  - request.tenant  (للاستخدام في الـ views)
  - _thread_locals  (للاستخدام في الـ models/managers)
"""
import threading
from django.shortcuts import render, redirect
from django.http import Http404
from django.urls import resolve
from tenants.models import Tenant

_thread_locals = threading.local()


def get_current_tenant():
    """يجيب الـ Tenant الحالي من أي مكان في الكود."""
    return getattr(_thread_locals, 'tenant', None)


def set_current_tenant(tenant):
    _thread_locals.tenant = tenant


def clear_current_tenant():
    _thread_locals.tenant = None


class TenantMiddleware:
    """
    يستخرج slug الشركة من الـ URL ويحدد الـ Tenant.
    يتحقق من سريان الاشتراك ويقفل الوصول فوراً في حال الانتهاء.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info

        # الصفحات العامة التي لا تحتاج Tenant
        PUBLIC_PATHS = ['/login/', '/logout/', '/register/', '/superadmin/', '/admin/', '/static/', '/media/', '/api/', '/manifest.json', '/sw.js']
        if any(path.startswith(p) for p in PUBLIC_PATHS):
            clear_current_tenant()
            request.tenant = None
            return self.get_response(request)

        tenant = None
        # استخراج slug من /t/{slug}/...
        if path.startswith('/t/'):
            parts = path.split('/')
            if len(parts) >= 3:
                slug = parts[2]
                try:
                    tenant = Tenant.objects.get(slug=slug)
                except Tenant.DoesNotExist:
                    clear_current_tenant()
                    request.tenant = None
                    raise Http404(f"الشركة '{slug}' غير موجودة")
        else:
            tenant_id = request.session.get('tenant_id')
            if tenant_id:
                try:
                    tenant = Tenant.objects.get(id=tenant_id)
                except Tenant.DoesNotExist:
                    tenant = None

        if tenant:
            set_current_tenant(tenant)
            request.tenant = tenant

            # قفل الوصول فوراً إذا كانت الشركة موقوفة أو انتهت فترة التجديد والاشتراك
            if not tenant.is_active or tenant.is_subscription_expired:
                # إذا كان المشاهد هو السوبر أدمن ولكن يتصفح موقع الشركة، نعرض له شاشة القفل أيضاً ليرى النتيجة
                return render(request, 'tenants/subscription_expired.html', {'tenant': tenant}, status=403)
        else:
            clear_current_tenant()
            request.tenant = None

        response = self.get_response(request)
        clear_current_tenant()
        return response
