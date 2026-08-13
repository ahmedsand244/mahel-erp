"""
TenantMixin — يُضاف لكل view يحتاج Tenant.

الاستخدام:
    class MyView(TenantMixin, TemplateView):
        ...
        def get_queryset(self):
            return MyModel.objects.filter(tenant=self.tenant)
"""
from django.shortcuts import redirect
from django.contrib import messages


class TenantMixin:
    """
    Mixin يتأكد إن الـ request عنده tenant صح
    ويوفر self.tenant لكل الـ methods.
    """
    def dispatch(self, request, *args, **kwargs):
        tenant = getattr(request, 'tenant', None)
        if tenant is None:
            messages.error(request, 'يرجى تسجيل الدخول لشركتك أولاً.')
            return redirect('tenants:login')

        if tenant.is_trial_expired:
            messages.warning(request, 'انتهت فترة التجربة المجانية. يرجى الترقية للاستمرار.')
            # يمكن إعادة توجيه لصفحة الترقية لاحقاً
            # return redirect('tenants:upgrade')

        self.tenant = tenant
        return super().dispatch(request, *args, **kwargs)
