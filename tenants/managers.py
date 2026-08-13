from django.db import models


class TenantManager(models.Manager):
    """
    Manager يفلتر البيانات تلقائياً بناءً على الشركة الحالية (Tenant)
    المحددة في الميدلوير (thread-local).

    إذا كان المستخدم داخل سياق شركة (/t/{slug}/...)، سيتم عرض بيانات هذه الشركة فقط.
    إذا كان الخادم ينفذ أمراً عاماً (مثل superadmin أو admin دون سياق شركة)، يعرض الكل.
    """
    def get_queryset(self):
        from tenants.middleware import get_current_tenant
        tenant = get_current_tenant()
        qs = super().get_queryset()
        if tenant is not None:
            return qs.filter(tenant=tenant)
        return qs
