from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.views import View
from django.utils import timezone
from django.utils.text import slugify
from datetime import timedelta
import re

from tenants.models import Tenant, TenantUser, UserSocialAuth


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
        from dashboard.audit import log_activity
        log_activity(request, module='auth', action_type='create', description=f"إنشاء وتسجيل حساب شركة جديد '{company_name}' باسم المستخدم '{username}'", severity='info', user=user, tenant=tenant)
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
        from dashboard.audit import log_activity
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            log_activity(request, module='auth', action_type='login', description=f"تسجيل دخول ناجح للمستخدم '{user.username}'", severity='info', user=user)
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
            log_activity(request, module='auth', action_type='login', description=f"محاولة تسجيل دخول فاشلة باسم المستخدم: '{username}'", severity='warning')
            messages.error(request, 'اسم المستخدم أو كلمة المرور غير صحيحة.')
            return render(request, self.template_name, {'username': username})


# ─────────────────────────────────────────────────
# 4. Logout
# ─────────────────────────────────────────────────
class TenantLogoutView(View):
    def get(self, request):
        from dashboard.audit import log_activity
        if request.user.is_authenticated:
            log_activity(request, module='auth', action_type='logout', description=f"تسجيل خروج للمستخدم '{request.user.username}'", severity='info')
        logout(request)
        request.session.flush()
        return redirect('/login/')


class ForgotPasswordView(View):
    """
    معالجة نسيان كلمة المرور:
    - فحص اسم المستخدم أو البريد الإلكتروني
    - توجيه المستخدم لحساب Google المربوط إن وجد (تسجيل دخول فوري)
    - أو إعطاء تعليمات الاسترجاع والتواصل
    """
    def post(self, request):
        from django.db.models import Q
        identifier = request.POST.get('identifier', '').strip()

        if not identifier:
            messages.error(request, 'يرجى إدخال اسم المستخدم أو البريد الإلكتروني المسجل.')
            return redirect('/login/')

        user = User.objects.filter(Q(username__iexact=identifier) | Q(email__iexact=identifier)).first()

        if not user:
            messages.error(request, f'لم يتم العثور على أي حساب مسجل بالبيانات: "{identifier}". تأكد من صحة الاسم أو الإيميل.')
            return redirect('/login/')

        social = getattr(user, 'social_auth', None)
        if social:
            messages.info(
                request,
                f'💡 حسابك ({user.username}) مربوط بحساب Google ({social.google_email or "الموثق"}). يمكنك الدخول فوراً بضغطة زر عبر "المتابعة باستخدام حساب Google" في الأعلى دون الحاجة لكلمة المرور!'
            )
            return redirect('/login/')

        if user.email:
            messages.info(
                request,
                f'تم التعرف على حسابك ({user.username}) وبريدك ({user.email}). إذا كان هذا البريد تابعاً لـ Google، يمكنك الدخول به مباشرة بزر Google أعلاه، أو تواصل مع إدارة النظام لإعادة التعيين.'
            )
        else:
            messages.info(
                request,
                f'تم التعرف على حسابك ({user.username})، ولكن لا يوجد بريد مسجل به. يرجى التواصل مع مسؤول النظام لتعيين كلمة مرور جديدة لك.'
            )

        return redirect('/login/')



class GoogleLoginView(View):
    """
    بدء مصادقة Google OAuth 2.0 الحقيقية.
    يحول المستخدم إلى شاشة تفويض واختيار الحساب في Google.
    يدعم:
    - تسجيل دخول / إنشاء حساب جديد (?action=login)
    - ربط الحساب الحالي للمستخدم المسجل دخوله (?action=link)
    """
    def get(self, request):
        import os
        import urllib.parse
        from django.conf import settings

        client_id = getattr(settings, 'GOOGLE_CLIENT_ID', '') or os.environ.get('GOOGLE_CLIENT_ID', '')
        if not client_id:
            messages.error(
                request,
                '⚠️ لم يتم ضبط GOOGLE_CLIENT_ID في إعدادات النظام (.env). يرجى إضافة بيانات الاعتماد لتفعيل تسجيل الدخول بجوجل.'
            )
            return redirect('/login/')

        # حفظ نوع الإجراء (ربط حساب حالي أو تسجيل دخول)
        action = request.GET.get('action', 'login')
        if action == 'link' and request.user.is_authenticated:
            request.session['google_oauth_action'] = 'link'
            request.session['google_oauth_user_id'] = request.user.id
        else:
            request.session['google_oauth_action'] = 'login'
            request.session.pop('google_oauth_user_id', None)

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
    استقبال رمز التفويض (code) من Google، استبداله بالـ Token، وجلب بيانات المستخدم.
    يدعم:
    1. ربط الحساب الحالي (Account Linking) مع منع تكرار نفس حساب Google.
    2. تسجيل الدخول والربط التلقائي عبر البريد الإلكتروني (Auto Linking by Email).
    """
    def get(self, request):
        import os
        import requests
        from django.conf import settings

        code = request.GET.get('code')
        error = request.GET.get('error')

        action = request.session.get('google_oauth_action', 'login')
        if error or not code:
            messages.error(request, 'تم إلغاء عملية التفويض بحساب Google.')
            return redirect('/profile/' if action == 'link' else '/login/')

        client_id = getattr(settings, 'GOOGLE_CLIENT_ID', '') or os.environ.get('GOOGLE_CLIENT_ID', '')
        client_secret = getattr(settings, 'GOOGLE_CLIENT_SECRET', '') or os.environ.get('GOOGLE_CLIENT_SECRET', '')

        if not client_id or not client_secret:
            messages.error(request, 'بيانات اعتماد Google OAuth غير مكتملة في ملف .env.')
            return redirect('/login/')

        scheme = 'https' if request.is_secure() or request.headers.get('x-forwarded-proto') == 'https' else 'http'
        host = request.get_host()
        default_redirect_uri = f"{scheme}://{host}/login/google/callback/"
        redirect_uri = request.session.get('google_oauth_redirect_uri', default_redirect_uri)
        action = request.session.pop('google_oauth_action', 'login')
        link_user_id = request.session.pop('google_oauth_user_id', None)

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
                return redirect('/profile/' if action == 'link' else '/login/')

            # 2. جلب بيانات البروفايل من Google UserInfo API
            userinfo_url = 'https://www.googleapis.com/oauth2/v3/userinfo'
            userinfo_resp = requests.get(userinfo_url, headers={'Authorization': f'Bearer {access_token}'}, timeout=10)
            user_info = userinfo_resp.json()

            google_id = str(user_info.get('sub') or user_info.get('id') or '')
            email = (user_info.get('email') or '').strip().lower()
            name = user_info.get('name') or user_info.get('given_name') or 'مستخدم جوجل'

            if not email or not google_id:
                messages.error(request, 'تعذر جلب البريد الإلكتروني أو معرّف الحساب من Google.')
                return redirect('/profile/' if action == 'link' else '/login/')

            # ── الحالة الأولى: ربط حساب حالي مسجل دخوله (Account Linking - يدعم ربط أكثر من حساب) ──
            if action == 'link':
                target_user = request.user if request.user.is_authenticated else User.objects.filter(id=link_user_id).first()
                if not target_user:
                    messages.error(request, 'انتهت الجلسة. يرجى تسجيل الدخول أولاً ثم المحاولة مجدداً.')
                    return redirect('/login/')

                # الأمان: فحص ما إذا كان حساب Google مربوطاً بالفعل بمستخدم آخر
                other_social = UserSocialAuth.objects.filter(google_id=google_id).exclude(user=target_user).first()
                if other_social:
                    messages.error(request, f'⚠️ لا يمكن الربط: حساب Google هذا ({email}) مربوط بالفعل بمستخدم آخر ({other_social.user.username})!')
                    return redirect('/profile/')

                # فحص ما إذا كان هذا الحساب مربوطاً بالفعل لنفس المستخدم
                my_existing = UserSocialAuth.objects.filter(user=target_user, google_id=google_id).first()
                if my_existing:
                    messages.info(request, f'💡 حساب Google هذا ({email}) مربوط بالفعل بحسابك مسبقاً.')
                    return redirect('/profile/')

                # إضافة الحساب الجديد لقائمة حسابات Google المربوطة
                UserSocialAuth.objects.create(
                    user=target_user,
                    google_id=google_id,
                    google_email=email
                )
                if not target_user.email:
                    target_user.email = email
                    target_user.save(update_fields=['email'])

                messages.success(request, f'🎉 تم ربط حساب Google بنجاح ({email})! أصبح بإمكانك تسجيل الدخول به إلى جانب حساباتك الأخرى.')
                return redirect('/profile/')

            # ── الحالة الثانية: تسجيل الدخول والربط التلقائي (Login & Auto-Link) ──
            user = None

            # أ) فحص وجود حساب مربوط مسبقاً بنفس الـ google_id
            social = UserSocialAuth.objects.filter(google_id=google_id).select_related('user').first()
            if social:
                user = social.user

            # ب) إذا لم يوجد بالـ ID، فحص وجود حساب بنفس البريد الإلكتروني (Auto Linking by Email)
            if not user and email:
                user = User.objects.filter(email__iexact=email).first()
                if user:
                    UserSocialAuth.objects.get_or_create(
                        user=user,
                        google_id=google_id,
                        defaults={'google_email': email}
                    )

            # ج) فحص وجود حساب باسم مستخدم مطابق لاسم الإيميل
            if not user and email:
                base_username = email.split('@')[0].replace('.', '_').replace('-', '_')
                user = User.objects.filter(username__iexact=base_username).first()
                if user:
                    if not user.email:
                        user.email = email
                        user.save(update_fields=['email'])
                    UserSocialAuth.objects.get_or_create(
                        user=user,
                        google_id=google_id,
                        defaults={'google_email': email}
                    )

            # د) إذا لم يوجد مستخدم مسبق، إنشاء مستخدم + شركة جديدة
            if not user:
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

                tenant_slug = make_slug(f"{candidate_username}-co")
                tenant = Tenant.objects.create(
                    name=f"شركة {name}",
                    slug=tenant_slug,
                    owner=user,
                    plan='trial',
                    trial_ends_at=timezone.now() + timedelta(days=14),
                )
                TenantUser.objects.create(tenant=tenant, user=user, role='admin')

                UserSocialAuth.objects.create(
                    user=user,
                    google_id=google_id,
                    google_email=email
                )
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

            # تسجيل الدخول للجلسة
            login(request, user)
            request.session['tenant_id'] = tenant.id
            messages.success(request, f"🎉 مرحباً بك يا {user.first_name or user.username}! تم تسجيل الدخول بحساب Google بنجاح.")
            return redirect(f'/t/{tenant.slug}/dashboard/')

        except requests.RequestException as req_err:
            messages.error(request, f"حدث خطأ في الاتصال بسيرفرات Google: {str(req_err)}")
            return redirect('/login/')
        except Exception as e:
            messages.error(request, f"حدث خطأ أثناء معالجة الحساب: {str(e)}")
            return redirect('/login/')


class GoogleUnlinkView(View):
    """
    إلغاء ربط حساب Google محدد (يدعم الحسابات المتعددة)
    """
    def post(self, request):
        if not request.user.is_authenticated:
            return redirect('/login/')

        user = request.user
        social_id = request.POST.get('social_id')

        # العثور على الحساب المطلوب حذفه الخاص بهذا المستخدم حصراً
        if social_id:
            social = user.social_auths.filter(id=social_id).first()
        else:
            social = user.social_auths.first()

        if not social:
            messages.info(request, 'الحساب المحدد غير مربوط أو تم حذفه مسبقاً.')
            return redirect('/profile/')

        # الأمان: إذا كان هذا هو آخر حساب Google للمستخدم وليس لديه كلمة مرور
        remaining_count = user.social_auths.count()
        if remaining_count <= 1 and not user.has_usable_password():
            messages.error(
                request,
                '⚠️ لا يمكنك إلغاء ربط آخر حساب Google لأنك لا تملك كلمة مرور مسجلة لحسابك! يرجى تعيين كلمة مرور في الأسفل أولاً حتى لا تفقد إمكانية الدخول.'
            )
            return redirect('/profile/')

        deleted_email = social.google_email or social.google_id
        social.delete()
        messages.success(request, f'✅ تم إلغاء ربط حساب Google ({deleted_email}) بنجاح.')
        return redirect('/profile/')


class UserProfileView(View):
    """
    شاشة الملف الشخصي وإعدادات الحساب وربط Google المتعدد
    """
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('/login/?next=/profile/')

        user = request.user
        social_auths = user.social_auths.all().order_by('-linked_at')
        membership = TenantUser.objects.filter(user=user).order_by('-joined_at').first()
        tenant = membership.tenant if membership else Tenant.objects.filter(owner=user).first()

        context = {
            'profile_user': user,
            'social_auths': social_auths,
            'social_count': social_auths.count(),
            'tenant': tenant,
            'membership': membership,
            'has_password': user.has_usable_password(),
        }
        return render(request, 'tenants/profile.html', context)

    def post(self, request):
        if not request.user.is_authenticated:
            return redirect('/login/')

        user = request.user
        action = request.POST.get('action', 'change_password')

        # ── 1. تعديل اسم المحل/المؤسسة والاسم الشخصي ──
        if action == 'update_store_info':
            store_name = request.POST.get('store_name', '').strip()
            first_name = request.POST.get('first_name', '').strip()

            if first_name:
                user.first_name = first_name
                user.save()

            membership = TenantUser.objects.filter(user=user).order_by('-joined_at').first()
            tenant = membership.tenant if membership else Tenant.objects.filter(owner=user).first()

            if tenant and store_name:
                old_name = tenant.name
                tenant.name = store_name
                tenant.save()
                from dashboard.audit import log_activity
                log_activity(
                    request,
                    module='tenants',
                    action_type='update',
                    description=f"تعديل وتحديث اسم المنشأة/المحل من '{old_name}' إلى '{store_name}'",
                    severity='info',
                    user=user,
                    tenant=tenant
                )
                messages.success(request, f"🎉 تم تحديث اسم المحل/المؤسسة بنجاح إلى '{store_name}' وحفظ بيانات الحساب.")
            else:
                messages.success(request, "🎉 تم حفظ بيانات الملف الشخصي بنجاح.")

            return redirect('/profile/')

        # ── 2. تحديث كلمة المرور ──
        old_password = request.POST.get('old_password', '')
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if user.has_usable_password():
            if not user.check_password(old_password):
                messages.error(request, 'كلمة المرور الحالية غير صحيحة.')
                return redirect('/profile/')

        if len(new_password) < 6:
            messages.error(request, 'كلمة المرور الجديدة يجب أن تكون 6 أحرف على الأقل.')
            return redirect('/profile/')

        if new_password != confirm_password:
            messages.error(request, 'كلمتا المرور غير متطابقتين.')
            return redirect('/profile/')

        user.set_password(new_password)
        user.save()
        from django.contrib.auth import update_session_auth_hash
        update_session_auth_hash(request, user)
        messages.success(request, '🎉 تم تحديث/تعيين كلمة المرور بنجاح! يمكنك الآن استخدامها لتسجيل الدخول في أي وقت.')
        return redirect('/profile/')


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

        tenants = Tenant.objects.all().select_related('owner').order_by('-created_at')
        total_tenants = tenants.count()
        active_tenants = tenants.filter(is_active=True).count()
        suspended_tenants = tenants.filter(is_active=False).count()
        trial_tenants = tenants.filter(plan='trial').count()
        pro_tenants = tenants.filter(plan='pro').count()
        basic_tenants = tenants.filter(plan='basic').count()

        now = timezone.now()
        expiring_soon_tenants = tenants.filter(
            is_active=True,
            trial_ends_at__isnull=False,
            trial_ends_at__lte=now + timedelta(days=7),
            trial_ends_at__gte=now
        ).count()

        # حساب الأيام المتبقية وحالة كل شركة للعرض المباشر
        tenants_data = []
        for t in tenants:
            days_left = None
            if t.trial_ends_at:
                delta = t.trial_ends_at - now
                days_left = delta.days
            tenants_data.append({
                'obj': t,
                'days_left': days_left,
                'is_expired': t.is_subscription_expired,
            })

        return render(request, 'tenants/superadmin.html', {
            'tenants': tenants,
            'tenants_data': tenants_data,
            'total_tenants': total_tenants,
            'active_tenants': active_tenants,
            'suspended_tenants': suspended_tenants,
            'trial_tenants': trial_tenants,
            'pro_tenants': pro_tenants,
            'basic_tenants': basic_tenants,
            'expiring_soon_tenants': expiring_soon_tenants,
        })

    def post(self, request):
        if not request.user.is_superuser:
            return redirect('/login/')

        action = request.POST.get('action')
        tenant_id = request.POST.get('tenant_id')

        # ── إنشاء شركة جديدة يدوياً من لوحة Superadmin ──
        if action == 'create_tenant':
            name = request.POST.get('name', '').strip()
            slug_input = request.POST.get('slug', '').strip() or name
            username = request.POST.get('username', '').strip()
            password = request.POST.get('password', '').strip()
            plan = request.POST.get('plan', 'trial')
            phone = request.POST.get('phone', '').strip()
            try:
                days = int(request.POST.get('days', 30))
            except (ValueError, TypeError):
                days = 30

            if not name or not username:
                messages.error(request, 'يرجى إدخال اسم الشركة واسم المستخدم على الأقل.')
                return redirect('/superadmin/')

            base_slug = make_slug(slug_input)
            slug = base_slug
            counter = 1
            while Tenant.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            # فحص أو إنشاء المستخدم
            user = User.objects.filter(username=username).first()
            if not user:
                if not password:
                    password = User.objects.make_random_password()
                user = User.objects.create_user(username=username, password=password)
            elif password:
                user.set_password(password)
                user.save()

            trial_ends_at = timezone.now() + timedelta(days=days)
            new_tenant = Tenant.objects.create(
                name=name,
                slug=slug,
                owner=user,
                plan=plan,
                trial_ends_at=trial_ends_at,
                is_active=True,
                phone=phone
            )
            TenantUser.objects.get_or_create(tenant=new_tenant, user=user, defaults={'role': 'admin'})
            messages.success(request, f'🎉 تم إنشاء شركة "{name}" بنجاح وتفعيل اشتراكها لمدة {days} يوماً (الرابط: /t/{slug}/).')
            return redirect('/superadmin/')

        # بقية الإجراءات تتطلب معرف الشركة
        try:
            tenant = Tenant.objects.get(id=tenant_id)
            now = timezone.now()

            if action == 'toggle_active':
                tenant.is_active = not tenant.is_active
                tenant.save()
                status = 'مفعّلة ✅' if tenant.is_active else 'موقوفة ⛔'
                messages.success(request, f'تم تغيير حالة شركة "{tenant.name}" إلى {status}.')

            elif action == 'upgrade_pro':
                tenant.plan = 'pro'
                tenant.is_active = True
                tenant.save()
                messages.success(request, f'🚀 تم ترقية شركة "{tenant.name}" إلى الباقة الاحترافية بنجاح.')

            elif action == 'quick_extend':
                try:
                    days = int(request.POST.get('days', 30))
                except (ValueError, TypeError):
                    days = 30
                base_date = tenant.trial_ends_at if tenant.trial_ends_at and tenant.trial_ends_at > now else now
                tenant.trial_ends_at = base_date + timedelta(days=days)
                tenant.is_active = True
                tenant.save()
                messages.success(request, f'🎉 تم تمديد اشتراك "{tenant.name}" بمقدار {days} يوماً بنجاح حتى ({tenant.trial_ends_at.strftime("%Y-%m-%d")}).')

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
                messages.success(request, f'🎉 تم تحديث بيانات واشتراك شركة "{tenant.name}" بنجاح.')

            elif action == 'impersonate':
                # ضمان صلاحية الإدارة للسوبر يوزر على هذا المتجر
                TenantUser.objects.get_or_create(tenant=tenant, user=request.user, defaults={'role': 'admin'})
                request.session['tenant_id'] = tenant.id
                messages.info(request, f'🔑 تم الدخول بصلاحية الإدارة الكاملة لمتجر "{tenant.name}".')
                return redirect(f'/t/{tenant.slug}/dashboard/')

            elif action == 'delete_tenant':
                name = tenant.name
                owner = tenant.owner
                tenant.delete()
                if owner and not owner.is_superuser and not owner.owned_tenants.exists():
                    owner.delete()
                messages.success(request, f'🗑️ تم حذف شركة "{name}" وكافة بياناتها بنجاح.')

        except Tenant.DoesNotExist:
            messages.error(request, 'الشركة المحددة غير موجودة.')

        return redirect('/superadmin/')
