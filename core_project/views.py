from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages

def user_login(request):
    if request.user.is_authenticated:
        return redirect('/')
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            next_url = request.GET.get('next') or '/'
            messages.success(request, f"مرحباً بك مجدداً 👋")
            return redirect(next_url)
        else:
            messages.error(request, "اسم المستخدم أو كلمة السر غير صحيحة! يرجى المحاولة مرة أخرى.")
            
    return render(request, 'login.html')

def user_logout(request):
    logout(request)
    messages.info(request, "تم تسجيل الخروج بنجاح.")
    return redirect('login')


def dashboard_redirect_view(request):
    """
    إعادة توجيه ذكية لرابط /dashboard/ المستخدم كـ start_url في تطبيق الهاتف / PWA.
    يحول المستخدم مباشرة إلى لوحة تحكم شركته /t/{slug}/dashboard/ أو لصفحة تسجيل الدخول.
    """
    if not request.user.is_authenticated:
        return redirect('/login/?next=/dashboard/')

    from tenants.models import TenantUser, Tenant
    membership = TenantUser.objects.filter(user=request.user).order_by('-joined_at').first()
    if membership and membership.tenant:
        request.session['tenant_id'] = membership.tenant.id
        return redirect(f'/t/{membership.tenant.slug}/dashboard/')

    tenant = Tenant.objects.filter(owner=request.user).first()
    if tenant:
        request.session['tenant_id'] = tenant.id
        return redirect(f'/t/{tenant.slug}/dashboard/')

    if request.user.is_superuser:
        return redirect('/superadmin/')

    return redirect('/')

