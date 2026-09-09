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


class GoogleLoginView(View):
    """
    بدء مصادقة Google OAuth 2.0 الحقيقية.
    يحول المستخدم إلى شاشة تفويض واختيار الحساب في Google.
    """
    def get(self, request):
        import os
        import urllib.parse
        from django.conf import settings

        if request.user.is_authenticated:
            membership = TenantUser.objects.filter(user=request.user).first()
            if membership:
                return redirect(f'/t/{membership.tenant.slug}/')
            return redirect('/')

        client_id = getattr(settings, 'GOOGLE_CLIENT_ID', '') or os.environ.get('GOOGLE_CLIENT_ID', '')
        if not client_id:
            messages.error(
                request,
                '⚠️ لم يتم ضبط GOOGLE_CLIENT_ID في إعدادات النظام (.env). يرجى إضافة بيانات الاعتماد لتفعيل تسجيل الدخول بجوجل.'
            )
            return redirect('/login/')

        # تحديد رابط الـ Callback بدقة (يدعم localhost و pythonanywhere)
        scheme = 'https' if request.is_secure() or request.headers.get('x-forwarded-proto') == 'https' else 'http'
        host = request.get_host()
        redirect_uri = f"{scheme}://{host}/login/google/callback/"
        request.session['google_oauth_redirect_uri'] = redirect_uri

        params = {
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': 'openid email profile',
            'access_type': 'online',
            'prompt': 'select_account'
        }
        google_auth_url = 'https://accounts.google.com/o/oauth2/v2/auth?' + urllib.parse.urlencode(params)
        return redirect(google_auth_url)


class GoogleCallbackView(View):
    """
    استقبال رمز التفويض (code) من Google، استبداله بالـ Token، وجلب بيانات المستخدم وتوثيقه في Django.
    """
    def get(self, request):
        import os
        import requests
        from django.conf import settings

        code = request.GET.get('code')
        error = request.GET.get('error')

        if error or not code:
            messages.error(request, 'تم إلغاء تسجيل الدخول بحساب Google أو حدث خطأ أثناء التفويض.')
            return redirect('/login/')

        client_id = getattr(settings, 'GOOGLE_CLIENT_ID', '') or os.environ.get('GOOGLE_CLIENT_ID', '')
        client_secret = getattr(settings, 'GOOGLE_CLIENT_SECRET', '') or os.environ.get('GOOGLE_CLIENT_SECRET', '')

        if not client_id or not client_secret:
            messages.error(request, 'بيانات اعتماد Google OAuth غير مكتملة في ملف .env.')
            return redirect('/login/')

        scheme = 'https' if request.is_secure() or request.headers.get('x-forwarded-proto') == 'https' else 'http'
        host = request.get_host()
        default_redirect_uri = f"{scheme}://{host}/login/google/callback/"
        redirect_uri = request.session.get('google_oauth_redirect_uri', default_redirect_uri)

        # 1. تبديل الـ Code بـ Access Token من سيرفرات جوجل الرسمية
        token_url = 'https://oauth2.googleapis.com/token'
        token_data = {
            'code': code,
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code'
        }

        try:
            token_resp = requests.post(token_url, data=token_data, timeout=10)
            token_json = token_resp.json()
            access_token = token_json.get('access_token')

            if not access_token:
                messages.error(request, f"فشل مصادقة Google: {token_json.get('error_description', 'رمز التفويض منتهي أو غير صالح')}")
                return redirect('/login/')

            # 2. جلب بيانات البروفايل من Google UserInfo API
            userinfo_url = 'https://www.googleapis.com/oauth2/v3/userinfo'
            userinfo_resp = requests.get(userinfo_url, headers={'Authorization': f'Bearer {access_token}'}, timeout=10)
            user_info = userinfo_resp.json()

            email = user_info.get('email')
            name = user_info.get('name') or user_info.get('given_name') or 'مستخدم جوجل'

            if not email:
                messages.error(request, 'تعذر جلب البريد الإلكتروني لحساب Google.')
                return redirect('/login/')

            # 3. التحقق من وجود المستخدم بالبريد الإلكتروني
            user = User.objects.filter(email=email).first()
            if not user:
                # إنشاء اسم مستخدم فريد
                base_username = email.split('@')[0].replace('.', '_').replace('-', '_')
                candidate_username = base_username
                counter = 1
                while User.objects.filter(username=candidate_username).exists():
                    candidate_username = f"{base_username}_{counter}"
                    counter += 1

                user = User.objects.create_user(
                    username=candidate_username,
                    email=email,
                    first_name=name[:30]
                )
                user.set_unusable_password()
                user.save()

                # إنشاء شركة جديدة وربطها بالمستخدم مع باقة تجريبية
                tenant_slug = make_slug(f"{candidate_username}-co")
                tenant = Tenant.objects.create(
                    name=f"شركة {name}",
                    slug=tenant_slug,
                    owner=user,
                    plan='trial',
                    trial_ends_at=timezone.now() + timedelta(days=14),
                )
                TenantUser.objects.create(tenant=tenant, user=user, role='admin')
            else:
                membership = TenantUser.objects.filter(user=user).order_by('-joined_at').first()
                tenant = membership.tenant if membership else Tenant.objects.filter(owner=user).first()
                if not tenant:
                    tenant_slug = make_slug(f"{user.username}-co")
                    tenant = Tenant.objects.create(
                        name=f"شركة {user.first_name or user.username}",
                        slug=tenant_slug,
                        owner=user,
                        plan='trial',
                        trial_ends_at=timezone.now() + timedelta(days=14),
                    )
                    TenantUser.objects.create(tenant=tenant, user=user, role='admin')

            # 4. تسجيل الدخول للجلسة بنجاح
            login(request, user)
            request.session['tenant_id'] = tenant.id
            messages.success(request, f"🎉 مرحباً بك يا {name}! تم تسجيل الدخول بحساب Google بنجاح.")
            return redirect(f'/t/{tenant.slug}/dashboard/')

        except requests.RequestException as req_err:
            messages.error(request, f"حدث خطأ في الاتصال بسيرفرات Google: {str(req_err)}")
            return redirect('/login/')
        except Exception as e:
            messages.error(request, f"حدث خطأ أثناء معالجة تسجيل الدخول: {str(e)}")
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
            elif action == 'update_subscription_date':
                new_date = request.POST.get('expiry_date')
                new_plan = request.POST.get('plan')
                if new_date:
                    from django.utils.dateparse import parse_date
                    import datetime
                    parsed = parse_date(new_date)
                    if parsed:
                        dt = datetime.datetime.combine(parsed, datetime.time.max)
                        if timezone.is_naive(dt):
                            dt = timezone.make_aware(dt)
                        tenant.trial_ends_at = dt
                if new_plan and new_plan in ['trial', 'basic', 'pro']:
                    tenant.plan = new_plan
                tenant.save()
                messages.success(request, f'🎉 تم تحديث تمديد/تاريخ اشتراك شركة "{tenant.name}" إلى ({new_date or "بدون تغيير"}) بنجاح.')
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
