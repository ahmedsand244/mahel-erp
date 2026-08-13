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
from django.shortcuts import redirect
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
    يضيف request.tenant لكل request.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info

        # الصفحات العامة التي لا تحتاج Tenant
        PUBLIC_PATHS = ['/login/', '/logout/', '/register/', '/superadmin/', '/admin/', '/static/', '/media/']
        if any(path.startswith(p) for p in PUBLIC_PATHS):
            clear_current_tenant()
            request.tenant = None
            return self.get_response(request)

        # استخراج slug من /t/{slug}/...
        if path.startswith('/t/'):
            parts = path.split('/')
            # parts = ['', 't', 'slug', ...]
            if len(parts) >= 3:
                slug = parts[2]
                try:
                    tenant = Tenant.objects.get(slug=slug, is_active=True)
                    set_current_tenant(tenant)
                    request.tenant = tenant
                except Tenant.DoesNotExist:
                    clear_current_tenant()
                    request.tenant = None
                    raise Http404(f"الشركة '{slug}' غير موجودة أو غير مفعّلة")
            else:
                clear_current_tenant()
                request.tenant = None
        else:
            # روابط بدون /t/ prefix — للتوافق مع النظام القديم
            # نحاول نجيب الـ Tenant من الـ session
            tenant_id = request.session.get('tenant_id')
            if tenant_id:
                try:
                    tenant = Tenant.objects.get(id=tenant_id, is_active=True)
                    set_current_tenant(tenant)
                    request.tenant = tenant
                except Tenant.DoesNotExist:
                    clear_current_tenant()
                    request.tenant = None
            else:
                clear_current_tenant()
                request.tenant = None

        response = self.get_response(request)
        clear_current_tenant()
        return response
