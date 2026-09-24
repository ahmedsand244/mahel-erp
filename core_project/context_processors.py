from django.utils import timezone
from django.db.models import F, Q
from decimal import Decimal
from django.core.cache import cache

from ledger.models import Customer, Supplier, Transaction
from inventory.models import Product
from maintenance.models import MaintenanceTicket

def smart_notifications(request):
    """
    سياق محرك التنبيهات والإشعارات الذكية المتاحة لكافة صفحات النظام.
    يتم تحديث التنبيهات بدقة فائقة ويشمل:
    1. تنبيهات نقص ونفاد المخزون (تساوي أو أقل من الحد الأدنى)
    2. استحقاق مواعيد سداد ديون العملاء والموردين
    3. تذاكر الصيانة والورشة المعلقة
    4. تذكير تجديد الاشتراك والنسخ الاحتياطي
    """
    if not request.user.is_authenticated:
        return {'smart_alerts': [], 'smart_alerts_count': 0}

    if hasattr(request, '_cached_smart_alerts'):
        return request._cached_smart_alerts

    tenant = getattr(request, 'tenant', None)
    if not tenant and request.user.is_authenticated:
        from tenants.models import TenantUser, Tenant
        membership = TenantUser.objects.filter(user=request.user).select_related('tenant').first()
        if membership:
            tenant = membership.tenant
        else:
            tenant = Tenant.objects.filter(owner=request.user).first()

    tenant_id = tenant.id if tenant else 'none'
    cache_key = f"smart_alerts_{tenant_id}_{request.user.id}"
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        request._cached_smart_alerts = cached_data
        return cached_data

    alerts = []
    today = timezone.now().date()

    # 0. تنبيه انتهاء الاشتراك والتجديد (مثبّت في أعلى التنبيهات إذا تبقّى 7 أيام أو أقل)
    if tenant:
        end_date = tenant.trial_ends_at or (tenant.created_at + timezone.timedelta(days=14))
        days_left = max(0, (end_date.date() - today).days)
        if days_left <= 7:
            days_str = "اليوم" if days_left == 0 else f"{days_left} يوم"
            alerts.append({
                'title': f"حالة الاشتراك: متبقي {days_str} على انتهاء التجديد",
                'subtitle': f"تاريخ الانتهاء: {end_date.strftime('%Y-%m-%d')} | الباقة الحالية: {tenant.get_plan_display()}",
                'url': f"https://api.whatsapp.com/send?phone=201011079572&text=مرحباً، أود تجديد اشتراك شركة: {tenant.name}",
                'type': 'warning' if days_left > 3 else 'error',
                'icon': 'hourglass_top',
                'badge': 'تجديد الاشتراك'
            })

    # 1. تنبيهات نقص المخزون والحد الأدنى
    low_stock_filter = Q(stock_quantity__lte=F('min_stock_threshold'))
    if tenant:
        low_stock_qs = Product.all_objects.filter(Q(tenant=tenant) | Q(tenant__isnull=True), low_stock_filter)
    else:
        low_stock_qs = Product.objects.filter(low_stock_filter)

    low_stock_count = low_stock_qs.count()
    low_stock = low_stock_qs.only('id', 'name', 'stock_quantity', 'min_stock_threshold').order_by('stock_quantity')[:100]
    inv_url = f"/t/{tenant.slug}/inventory/" if tenant else "/inventory/"

    for p in low_stock:
        is_zero = (p.stock_quantity <= 0)
        alerts.append({
            'title': f"نفاد المخزون: {p.name}" if is_zero else f"نقص مخزون: {p.name}",
            'subtitle': f"الكمية المتاحة: {p.stock_quantity} قطعة | الحد الأدنى للتنبيه: {p.min_stock_threshold} قطعة",
            'url': inv_url,
            'type': 'error' if is_zero else 'warning',
            'icon': 'inventory_2',
            'badge': 'نفاد تام' if is_zero else 'وصل للحد الأدنى',
            'category': 'inventory'
        })

    # 2. تنبيهات استحقاق ديون العملاء
    cust_filter = Q(balance__gt=0) & (Q(due_date__lte=today) | Q(due_date__isnull=True))
    if tenant:
        cust_qs = Customer.all_objects.filter(Q(tenant=tenant) | Q(tenant__isnull=True), cust_filter)
    else:
        cust_qs = Customer.objects.filter(cust_filter)

    cust_count = cust_qs.count()
    overdue_customers = cust_qs.only('id', 'name', 'balance', 'due_date').order_by('due_date')[:50]

    for c in overdue_customers:
        days = (today - c.due_date).days if c.due_date else None
        days_str = f"منذ {days} يوم" if (days is not None and days > 0) else ("اليوم" if days == 0 else "مستحق السداد")
        cust_url = f"/t/{tenant.slug}/ledger/customer/{c.id}/" if tenant else f"/ledger/customer/{c.id}/"
        alerts.append({
            'title': f"استحقاق دين عميل: {c.name}",
            'subtitle': f"المبلغ المستحق: {c.balance} ج.م | موعد الاستحقاق: {c.due_date or 'غير محدد'} ({days_str})",
            'url': cust_url,
            'type': 'error',
            'icon': 'account_balance_wallet',
            'badge': 'استحقاق دين عميل',
            'category': 'ledger'
        })

    # 3. تنبيهات مستحقات الموردين
    supp_filter = Q(balance__gt=0) & (Q(due_date__lte=today) | Q(due_date__isnull=True))
    if tenant:
        supp_qs = Supplier.all_objects.filter(Q(tenant=tenant) | Q(tenant__isnull=True), supp_filter)
    else:
        supp_qs = Supplier.objects.filter(supp_filter)

    supp_count = supp_qs.count()
    overdue_suppliers = supp_qs.only('id', 'name', 'balance', 'due_date').order_by('due_date')[:50]

    for s in overdue_suppliers:
        days = (today - s.due_date).days if s.due_date else None
        days_str = f"منذ {days} يوم" if (days is not None and days > 0) else ("اليوم" if days == 0 else "مستحق السداد")
        supp_url = f"/t/{tenant.slug}/ledger/supplier/{s.id}/" if tenant else f"/ledger/supplier/{s.id}/"
        alerts.append({
            'title': f"مستحقات مورد: {s.name}",
            'subtitle': f"المبلغ المطلوب سداده: {s.balance} ج.م | الموعد: {s.due_date or 'غير محدد'} ({days_str})",
            'url': supp_url,
            'type': 'warning',
            'icon': 'local_shipping',
            'badge': 'مستحقات مورد',
            'category': 'ledger'
        })

    # 4. تنبيهات تذاكر الصيانة والورشة المعلقة
    maint_filter = ~Q(status='delivered')
    if tenant:
        maint_qs = MaintenanceTicket.all_objects.filter(Q(tenant=tenant) | Q(tenant__isnull=True), maint_filter)
    else:
        maint_qs = MaintenanceTicket.objects.filter(maint_filter)

    maint_count = maint_qs.count()
    active_tickets = maint_qs.select_related('customer').only('id', 'ticket_number', 'device_name', 'status', 'customer__name', 'created_at').order_by('-created_at')[:50]

    maint_url = f"/t/{tenant.slug}/maintenance/" if tenant else "/maintenance/"
    for t in active_tickets:
        cust_name = t.customer.name if t.customer else "عميل"
        alerts.append({
            'title': f"تذكرة صيانة #{t.ticket_number} — {t.device_name}",
            'subtitle': f"العميل: {cust_name} | الحالة: {t.get_status_display()}",
            'url': maint_url,
            'type': 'warning',
            'icon': 'build',
            'badge': 'ورشة نشطة',
            'category': 'maintenance'
        })

    # 5. تنبيه النسخ الاحتياطي الأسبوعي للبيانات
    has_backup_alert = False
    if request.user.is_staff or request.user.is_superuser or (tenant and getattr(tenant, 'owner_id', None) == request.user.id):
        has_backup_alert = True
        backup_url = f"/t/{tenant.slug}/dashboard/backup/" if tenant else "/dashboard/backup/"
        alerts.append({
            'title': "🛡️ تذكير النسخ الاحتياطي الأسبوعي للبيانات",
            'subtitle': "اضغط هنا لتحميل نسخة احتياطية آمنة (Backup) من قاعدة البيانات لضمان سلامة العمليات.",
            'url': backup_url,
            'type': 'warning',
            'icon': 'cloud_download',
            'badge': 'أمان البيانات',
            'category': 'system'
        })

    total_true_count = len(alerts)

    result = {
        'smart_alerts': alerts,
        'smart_alerts_count': total_true_count,
        'alerts_counts': {
            'inventory': low_stock_count,
            'ledger': cust_count + supp_count,
            'maintenance': maint_count
        }
    }
    cache.set(cache_key, result, timeout=120)
    request._cached_smart_alerts = result
    return result


def tenant_subscription_info(request):
    """
    يوفر معلومات اشتراك الشركة والوقت المتبقي لجميع صفحات النظام
    مخزن في الذاكرة (RAM Cache) لمدة دقيقتين لسرعة التصفح الفائقة.
    """
    if hasattr(request, '_cached_tenant_subscription_info'):
        return request._cached_tenant_subscription_info

    tenant = getattr(request, 'tenant', None)
    tenant_id = tenant.id if tenant else 'none'
    cache_key = f"tenant_sub_info_{tenant_id}"
    cached_res = cache.get(cache_key)
    if cached_res is not None:
        request._cached_tenant_subscription_info = cached_res
        return cached_res

    if not tenant and request.user.is_authenticated:
        from tenants.models import TenantUser, Tenant
        membership = TenantUser.objects.filter(user=request.user).select_related('tenant').first()
        if membership:
            tenant = membership.tenant
        else:
            tenant = Tenant.objects.filter(owner=request.user).first()

    if not tenant:
        res = {'subscription_info': None}
        cache.set(cache_key, res, timeout=120)
        request._cached_tenant_subscription_info = res
        return res

    now = timezone.now()
    end_date = tenant.trial_ends_at or (tenant.created_at + timezone.timedelta(days=14))
    days_left = max(0, (end_date - now).days)
    hours_left = max(0, int((end_date - now).total_seconds() // 3600))

    res = {
        'subscription_info': {
            'tenant_name': tenant.name,
            'plan_display': tenant.get_plan_display(),
            'days_left': days_left,
            'hours_left': hours_left,
            'is_expired': days_left == 0 and hours_left == 0,
            'end_date': end_date.strftime('%Y-%m-%d'),
            'badge_color': 'emerald' if days_left > 5 else ('amber' if days_left > 2 else 'rose'),
        }
    }
    cache.set(cache_key, res, timeout=120)
    request._cached_tenant_subscription_info = res
    return res
