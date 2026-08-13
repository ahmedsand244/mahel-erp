from django.utils import timezone
from django.db.models import F, Q
from decimal import Decimal

from ledger.models import Customer, Supplier, Transaction
from inventory.models import Product
from maintenance.models import MaintenanceTicket

def smart_notifications(request):
    """
    سياق محرك التنبيهات والإشعارات الذكية المتاحة لكافة صفحات النظام.
    يغطي:
    1. استحقاق مواعيد سداد ديون العملاء والموردين
    2. النقص الحاد في المخزون (الحد الأدنى)
    3. تذاكر الورشة والصيانة المتأخرة أو المستحقة التسليم
    """
    if not request.user.is_authenticated:
        return {'smart_alerts': [], 'smart_alerts_count': 0}

    alerts = []
    today = timezone.now().date()

    # 1. تنبيهات استحقاق ديون العملاء
    overdue_customers = Customer.objects.filter(
        balance__gt=0,
        due_date__lte=today
    ).order_by('due_date')[:5]

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
    ).order_by('due_date')[:5]

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
    ).order_by('stock_quantity')[:5]

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
    active_tickets = MaintenanceTicket.objects.exclude(status='delivered').order_by('-created_at')[:5]

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

    return {
        'smart_alerts': alerts,
        'smart_alerts_count': len(alerts)
    }
