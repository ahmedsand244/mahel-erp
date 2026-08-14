from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.views import View
from django.utils import timezone
from django.utils.text import slugify
from datetime import timedelta
import re

from tenants.models import Tenant, TenantUser


# ─────────────────────────────────────────────────
# Helper: sanitize slug to ASCII-safe
# ─────────────────────────────────────────────────
def make_slug(text):
    """يحول النص لـ slug آمن للـ URL (حروف إنجليزية + أرقام + -)."""
    text = text.strip().lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text).strip('-')
    return text or 'company'


# ─────────────────────────────────────────────────
# 1. Landing Page — الصفحة الرئيسية التسويقية
# ─────────────────────────────────────────────────
class LandingView(View):
    def get(self, request):
        if request.user.is_authenticated:
            membership = TenantUser.objects.filter(user=request.user).order_by('-joined_at').first()
            if membership:
                return redirect(f'/t/{membership.tenant.slug}/')
        return render(request, 'tenants/landing.html')


# ─────────────────────────────────────────────────
# 2. Register — تسجيل شركة جديدة
# ─────────────────────────────────────────────────
class RegisterView(View):
    template_name = 'tenants/register.html'

    def get(self, request):
        if request.user.is_authenticated:
            return self._redirect_to_dashboard(request.user)
        return render(request, self.template_name)

    def post(self, request):
        company_name = request.POST.get('company_name', '').strip()
        username     = request.POST.get('username', '').strip()
        password     = request.POST.get('password', '')
        password2    = request.POST.get('confirm_password', '') or request.POST.get('password2', '')
        slug_input   = request.POST.get('slug', '').strip() or username or company_name

        # Validation
        if not company_name or not username or not password:
            messages.error(request, 'جميع الحقول مطلوبة.')
            return render(request, self.template_name, {'form_data': request.POST})

        if password2 and password != password2:
            messages.error(request, 'كلمتا المرور غير متطابقتان.')
            return render(request, self.template_name, {'form_data': request.POST})

        if len(password) < 6:
            messages.error(request, 'كلمة المرور يجب أن تكون 6 أحرف على الأقل.')
            return render(request, self.template_name, {'form_data': request.POST})

        # Generate unique ASCII slug
        base_slug = make_slug(slug_input)
        slug = base_slug
        counter = 1
        while Tenant.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        if User.objects.filter(username=username).exists():
            messages.error(request, f'اسم المستخدم "{username}" مستخدم بالفعل. اختر اسم مستخدم آخر.')
            return render(request, self.template_name, {'form_data': request.POST})

        # Create User + Tenant
        user = User.objects.create_user(username=username, password=password)
        tenant = Tenant.objects.create(
            name=company_name,
            slug=slug,
            owner=user,
            plan='trial',
            trial_ends_at=timezone.now() + timedelta(days=14),
        )
        TenantUser.objects.create(tenant=tenant, user=user, role='admin')

        # Auto-login
        login(request, user)
        request.session['tenant_id'] = tenant.id
        messages.success(request, f'🎉 مرحباً! تم إنشاء حساب شركة "{company_name}" بنجاح. فترة التجربة 14 يوم مجاناً.')
        return redirect(f'/t/{slug}/')


    def _redirect_to_dashboard(self, user):
        membership = TenantUser.objects.filter(user=user).first()
        if membership:
            return redirect(f'/t/{membership.tenant.slug}/')
        return redirect('/register/')


# ─────────────────────────────────────────────────
# 3. Login
# ─────────────────────────────────────────────────
class TenantLoginView(View):
    template_name = 'tenants/login.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            if user.is_superuser:
                return redirect('/superadmin/')
            membership = TenantUser.objects.filter(user=user).order_by('-joined_at').first()
            if membership:
                request.session['tenant_id'] = membership.tenant.id
                return redirect(f'/t/{membership.tenant.slug}/')
            return redirect('/register/')
        else:
            messages.error(request, 'اسم المستخدم أو كلمة المرور غير صحيحة.')
            return render(request, self.template_name, {'username': username})


# ─────────────────────────────────────────────────
# 4. Logout
# ─────────────────────────────────────────────────
class TenantLogoutView(View):
    def get(self, request):
        logout(request)
        request.session.flush()
        return redirect('/login/')


# ─────────────────────────────────────────────────
# 5. Tenant Dashboard Redirect — /t/{slug}/
# ─────────────────────────────────────────────────
class TenantHomeView(View):
    """بوابة الدخول — بتحول للـ dashboard الرئيسي للنظام."""
    def get(self, request, slug):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return redirect('/login/')
        # حفظ الـ tenant في الـ session
        request.session['tenant_id'] = tenant.id
        # إعادة توجيه للـ dashboard الموجود
        return redirect(f'/t/{slug}/dashboard/')


# ─────────────────────────────────────────────────
# 6. Superadmin Panel — لك أنت فقط
# ─────────────────────────────────────────────────
class SuperAdminView(View):
    def get(self, request):
        if not request.user.is_superuser:
            return redirect('/login/')
        tenants = Tenant.objects.all().order_by('-created_at')
        total_tenants = tenants.count()
        active_tenants = tenants.filter(is_active=True).count()
        trial_tenants = tenants.filter(plan='trial').count()
        return render(request, 'tenants/superadmin.html', {
            'tenants': tenants,
            'total_tenants': total_tenants,
            'active_tenants': active_tenants,
            'trial_tenants': trial_tenants,
        })

    def post(self, request):
        if not request.user.is_superuser:
            return redirect('/login/')
        action    = request.POST.get('action')
        tenant_id = request.POST.get('tenant_id')
        try:
            tenant = Tenant.objects.get(id=tenant_id)
            if action == 'toggle_active':
                tenant.is_active = not tenant.is_active
                tenant.save()
                status = 'مفعّل' if tenant.is_active else 'موقوف'
                messages.success(request, f'تم تغيير حالة "{tenant.name}" إلى {status}.')
            elif action == 'upgrade_pro':
                tenant.plan = 'pro'
                tenant.save()
                messages.success(request, f'تم ترقية "{tenant.name}" إلى الباقة الاحترافية.')
            elif action == 'delete_tenant':
                name = tenant.name
                owner = tenant.owner
                tenant.delete()
                if owner and not owner.is_superuser:
                    owner.delete()
                messages.success(request, f'🗑️ تم حذف شركة "{name}" وكافة بياناتها بنجاح.')
        except Tenant.DoesNotExist:
            messages.error(request, 'الشركة غير موجودة.')
        return redirect('/superadmin/')
