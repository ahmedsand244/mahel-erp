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
    يتم تخزينه مؤقتاً في الرام (RAM Cache) لمدة 30 ثانية لتفادي استعلامات قاعدة البيانات المتكررة.
    """
    if not request.user.is_authenticated:
        return {'smart_alerts': [], 'smart_alerts_count': 0}

    if hasattr(request, '_cached_smart_alerts'):
        return request._cached_smart_alerts

    tenant = getattr(request, 'tenant', None)
    tenant_id = tenant.id if tenant else 'none'
    cache_key = f"smart_alerts_{tenant_id}_{request.user.id}"
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        request._cached_smart_alerts = cached_data
        return cached_data

    alerts = []
    today = timezone.now().date()

    # 0. تنبيه انتهاء الاشتراك والتجديد (مثبّت في أعلى التنبيهات)
    tenant = getattr(request, 'tenant', None)
    if tenant:
        end_date = tenant.trial_ends_at or (tenant.created_at + timezone.timedelta(days=14))
        days_left = max(0, (end_date.date() - today).days)
        days_str = "اليوم" if days_left == 0 else f"{days_left} يوم"
        alerts.append({
            'title': f"حالة الاشتراك: متبقي {days_str} على انتهاء التجديد",
            'subtitle': f"تاريخ الانتهاء: {end_date.strftime('%Y-%m-%d')} | الباقة الحالية: {tenant.get_plan_display()}",
            'url': f"https://api.whatsapp.com/send?phone=201011079572&text=مرحباً، أود تجديد اشتراك شركة: {tenant.name}",
            'type': 'warning' if days_left > 3 else 'error',
            'icon': 'hourglass_top',
            'badge': 'تجديد الاشتراك'
        })

    # 1. تنبيهات استحقاق ديون العملاء (استعلام فائق السرعة)
    overdue_customers = Customer.objects.filter(
        balance__gt=0,
        due_date__lte=today
    ).only('id', 'name', 'balance', 'due_date').order_by('due_date')[:5]

    for c in overdue_customers:
        days = (today - c.due_date).days if c.due_date else 0
        days_str = "اليوم" if days == 0 else f"منذ {days} يوم"
        alerts.append({
            'title': f"استحقاق دين عميل: {c.name}",
            'subtitle': f"المبلغ المستحق: {c.balance} ج.م | موعد الاستحقاق: {c.due_date} ({days_str})",
            'url': f"/ledger/customer/{c.id}/",
            'type': 'error',
            'icon': 'account_balance_wallet',
            'badge': 'استحقاق دين عميل'
        })

    # 2. تنبيهات استحقاق ديون الموردين
    overdue_suppliers = Supplier.objects.filter(
        balance__gt=0,
        due_date__lte=today
    ).only('id', 'name', 'balance', 'due_date').order_by('due_date')[:5]

    for s in overdue_suppliers:
        days = (today - s.due_date).days if s.due_date else 0
        days_str = "اليوم" if days == 0 else f"منذ {days} يوم"
        alerts.append({
            'title': f"مستحقات مورد: {s.name}",
            'subtitle': f"المبلغ المطلوب سداده: {s.balance} ج.م | الموعد: {s.due_date} ({days_str})",
            'url': f"/ledger/supplier/{s.id}/",
            'type': 'warning',
            'icon': 'local_shipping',
            'badge': 'مستحقات مورد'
        })

    # 3. تنبيهات نقص المخزون والحد الأدنى
    low_stock = Product.objects.filter(
        stock_quantity__lte=F('min_stock_threshold')
    ).only('id', 'name', 'stock_quantity', 'min_stock_threshold').order_by('stock_quantity')[:5]

    for p in low_stock:
        alerts.append({
            'title': f"نقص مخزون: {p.name}",
            'subtitle': f"المتاح حالياً: {p.stock_quantity} قطعة | الحد الأدنى: {p.min_stock_threshold}",
            'url': '/inventory/',
            'type': 'warning' if p.stock_quantity > 0 else 'error',
            'icon': 'inventory_2',
            'badge': 'نقص مخزون'
        })

    # 4. تنبيهات تذاكر الصيانة والورشة المعلقة
    active_tickets = MaintenanceTicket.objects.exclude(status='delivered').select_related('customer').only('id', 'ticket_number', 'device_name', 'status', 'customer__name', 'created_at').order_by('-created_at')[:5]

    for t in active_tickets:
        cust_name = t.customer.name if t.customer else "عميل"
        alerts.append({
            'title': f"تذكرة صيانة #{t.ticket_number} — {t.device_name}",
            'subtitle': f"العميل: {cust_name} | الحالة: {t.get_status_display()}",
            'url': '/maintenance/',
            'type': 'warning',
            'icon': 'build',
            'badge': 'ورشة نشطة'
        })

    result = {
        'smart_alerts': alerts,
        'smart_alerts_count': len(alerts)
    }
    cache.set(cache_key, result, timeout=30)
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
