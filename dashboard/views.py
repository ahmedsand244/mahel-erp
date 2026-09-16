import json
from decimal import Decimal
from django.views.generic import TemplateView, View
from django.http import JsonResponse
from django.db.models import Sum, F, Q, Count, ExpressionWrapper, DecimalField

from pos.models import Order
from maintenance.models import MaintenanceTicket
from inventory.models import Product, StockAlert
from expenses.models import Expense
from ledger.models import Customer, Supplier, Transaction
from dashboard.models import AuditLog
from core_project.services import get_profit_and_loss

class DashboardView(TemplateView):
    template_name = "dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 1. Fetch Profit & Loss KPIs
        pnl = get_profit_and_loss()
        context.update(pnl)

        total_income = pnl['gross_sales'] + pnl['parts_sell'] + pnl['labor_fees']
        cogs_total = pnl['cogs'] + pnl['parts_cost']
        store_expenses = pnl['total_expenses']
        total_costs_all = cogs_total + store_expenses
        collected_from_customers = pnl['collected_from_customers']

        context['total_income'] = total_income
        context['total_costs_all'] = total_costs_all
        context['cogs_total'] = cogs_total
        context['store_expenses'] = store_expenses
        context['collected_from_customers'] = collected_from_customers

        # Actual cash received in store drawer (cash sales + visa sales + labor + debt collections + cash deposits)
        order_methods = Order.objects.aggregate(
            cash_visa=Sum('total_amount', filter=Q(payment_method__in=['cash', 'visa'])),
            deferred=Sum('total_amount', filter=Q(payment_method='deferred'))
        )
        cash_sales = order_methods['cash_visa'] or Decimal('0.00')
        deferred_sales = order_methods['deferred'] or Decimal('0.00')
        cash_deposits = pnl.get('cash_deposits', Decimal('0.00'))
        cash_withdrawals = pnl.get('cash_withdrawals', Decimal('0.00'))
        cash_sales_fawry = cash_sales + pnl['labor_fees']
        total_cash_inflow = cash_sales_fawry + collected_from_customers + cash_deposits
        
        context['cash_sales_fawry'] = cash_sales_fawry
        context['deferred_sales'] = deferred_sales
        context['total_cash_inflow'] = total_cash_inflow
        context['cash_deposits'] = cash_deposits
        context['cash_withdrawals'] = cash_withdrawals

        # Net Cash Position = All Cash In - All Cash Out
        # Cash In: cash/visa sales + labor fees collected + customer debt collections + cash injections (top-ups)
        # Cash Out: operating expenses paid + payments sent to suppliers + cash withdrawals
        total_cash_in = total_cash_inflow
        total_cash_out = pnl['total_expenses'] + pnl['paid_to_suppliers'] + cash_withdrawals
        context['total_cash_in'] = total_cash_in
        context['total_cash_out'] = total_cash_out
        context['net_cash_position'] = total_cash_in - total_cash_out

        # Total Supplier Liabilities (what the store owes to all suppliers combined)
        context['total_supplier_liabilities'] = Supplier.objects.aggregate(Sum('balance'))['balance__sum'] or Decimal('0.00')

        # 2. Inventory Valuation (Instant SQL Aggregation - Ultra Fast)
        from django.db.models import ExpressionWrapper
        inv_agg = Product.objects.aggregate(
            val=Sum(ExpressionWrapper(F('purchase_price') * F('stock_quantity'), output_field=DecimalField(max_digits=16, decimal_places=2))),
            count=Count('id')
        )
        context['inventory_cost_val'] = inv_agg['val'] or Decimal('0.00')
        context['products_count'] = inv_agg['count'] or 0

        # 3. Dynamic deduplicated low stock products
        low_stock_products = Product.objects.filter(
            stock_quantity__lte=F('min_stock_threshold')
        ).only('id', 'name', 'stock_quantity', 'min_stock_threshold').order_by('stock_quantity', 'name')[:5]
        
        context['low_stock_products'] = low_stock_products
        context['low_stock_count'] = low_stock_products.count()

        # 4. Maintenance & Ledger Counts
        context['active_tickets_count'] = MaintenanceTicket.objects.exclude(status='delivered').count()
        context['total_customer_debts'] = Customer.objects.filter(balance__gt=0).aggregate(Sum('balance'))['balance__sum'] or Decimal('0.00')
        context['total_supplier_debts'] = Supplier.objects.filter(balance__gt=0).aggregate(Sum('balance'))['balance__sum'] or Decimal('0.00')
        
        # 5. Recent Activity Logs
        context['recent_orders'] = Order.objects.select_related('customer').order_by('-created_at')[:6]
        context['recent_tickets'] = MaintenanceTicket.objects.select_related('customer').order_by('-created_at')[:6]
        context['recent_collections'] = Transaction.objects.filter(transaction_type__in=['pay_received', 'cash_deposit']).select_related('customer', 'supplier').order_by('-created_at')[:6]
        
        # 6. Interactive Chart Analytics (Single Grouped Query for Entire 7 Days)
        from django.utils import timezone
        import datetime

        today = timezone.now().date()
        chart_dates = []
        chart_sales = []
        chart_profits = []

        seven_days_ago = today - datetime.timedelta(days=6)
        daily_stats = {
            row['created_at__date']: row
            for row in Order.objects.filter(created_at__date__gte=seven_days_ago)
                                    .values('created_at__date')
                                    .annotate(sales=Sum('total_amount'), cogs=Sum('cost_of_goods_sold'))
        }

        for i in range(6, -1, -1):
            day_date = today - datetime.timedelta(days=i)
            chart_dates.append(day_date.strftime('%m/%d'))
            day_data = daily_stats.get(day_date, {})
            sales = day_data.get('sales') or Decimal('0.00')
            cogs = day_data.get('cogs') or Decimal('0.00')
            profit = sales - cogs

            chart_sales.append(float(sales))
            chart_profits.append(float(profit))

        # Top 5 Selling Products (Filtered by tenant orders)
        from pos.models import OrderItem
        tenant_orders = Order.objects.all()
        top_items = (
            OrderItem.objects
            .filter(order__in=tenant_orders)
            .values('product__name')
            .annotate(total_qty=Sum('quantity'), total_rev=Sum(F('unit_price') * F('quantity')))
            .order_by('-total_qty')[:5]
        )

        top_names = [item['product__name'] or 'صنف عام' for item in top_items]
        top_quantities = [item['total_qty'] for item in top_items]

        # Payment Methods Distribution
        all_orders = Order.objects.all()
        cash_val = float(all_orders.filter(payment_method='cash').aggregate(Sum('total_amount'))['total_amount__sum'] or 0)
        visa_val = float(all_orders.filter(payment_method='visa').aggregate(Sum('total_amount'))['total_amount__sum'] or 0)
        deferred_val = float(all_orders.filter(payment_method='deferred').aggregate(Sum('total_amount'))['total_amount__sum'] or 0)

        context['chart_dates_json'] = json.dumps(chart_dates)
        context['chart_sales_json'] = json.dumps(chart_sales)
        context['chart_profits_json'] = json.dumps(chart_profits)
        context['top_names_json'] = json.dumps(top_names)
        context['top_quantities_json'] = json.dumps(top_quantities)
        context['payment_dist_json'] = json.dumps([cash_val, visa_val, deferred_val])

        # 7. Recent System Audit & Activity Logs
        from dashboard.models import AuditLog
        context['recent_audit_logs'] = AuditLog.objects.select_related('user').order_by('-created_at')[:8]

        return context


class GlobalSearchView(View):
    """البحث المباشر الشامل في كافة أرجاء النظام (منتجات، عملاء، موردين، فواتير، صيانة، طلبات بضاعة)"""
    def get(self, request, *args, **kwargs):
        query = request.GET.get('q', '').strip()
        if not query or len(query) < 1:
            return JsonResponse({'results': []})

        tenant = getattr(request, 'tenant', None)
        if not tenant:
            tenant_id = request.session.get('tenant_id')
            if tenant_id:
                from tenants.models import Tenant
                try:
                    tenant = Tenant.objects.get(id=tenant_id)
                except Tenant.DoesNotExist:
                    tenant = None
            if not tenant and request.user.is_authenticated:
                tenant = getattr(request.user, 'tenant', None)

        from tenants.middleware import set_current_tenant, clear_current_tenant, get_current_tenant
        prev_tenant = get_current_tenant()
        if tenant:
            set_current_tenant(tenant)

        try:
            prefix = f"/t/{tenant.slug}" if tenant else ""
            results = []

            # 1. المنتجات والمخزون
            products = Product.objects.filter(
                Q(name__icontains=query) | Q(sku__icontains=query) | Q(barcode__icontains=query) | Q(category__icontains=query)
            )[:5]
            if products.exists():
                items = []
                for p in products:
                    items.append({
                        'title': p.name,
                        'subtitle': f"SKU: {p.sku} | السعر: {p.selling_price:,.2f} ج.م | الرصيد: {p.stock_quantity}",
                        'url': f'{prefix}/inventory/',
                        'badge': f"{p.stock_quantity} قطعة",
                        'badge_type': 'primary' if p.stock_quantity > 0 else 'error'
                    })
                results.append({
                    'category': 'المنتجات والمخزون',
                    'icon': 'inventory_2',
                    'items': items
                })

            # 2. حسابات العملاء والشكك
            customers = Customer.objects.filter(
                Q(name__icontains=query) | Q(phone__icontains=query) | Q(workplace__icontains=query) | Q(address__icontains=query)
            )[:5]
            if customers.exists():
                items = []
                for c in customers:
                    items.append({
                        'title': c.name,
                        'subtitle': f"هاتف: {c.phone or '—'} | مكان العمل: {c.workplace or '—'}",
                        'url': f'{prefix}/ledger/customer/{c.id}/',
                        'badge': f"دين: {c.balance:,.2f} ج.م" if c.balance > 0 else "خالص",
                        'badge_type': 'error' if c.balance > 0 else 'primary'
                    })
                results.append({
                    'category': 'حسابات العملاء (الشكك)',
                    'icon': 'person',
                    'items': items
                })

            # 3. حسابات الموردين والشركات
            suppliers = Supplier.objects.filter(
                Q(name__icontains=query) | Q(phone__icontains=query) | Q(company__icontains=query)
            )[:5]
            if suppliers.exists():
                items = []
                for s in suppliers:
                    items.append({
                        'title': s.name,
                        'subtitle': f"الشركة: {s.company or '—'} | هاتف: {s.phone or '—'}",
                        'url': f'{prefix}/ledger/supplier/{s.id}/',
                        'badge': f"مستحق: {s.balance:,.2f} ج.م" if s.balance > 0 else "خالص",
                        'badge_type': 'error' if s.balance > 0 else 'primary'
                    })
                results.append({
                    'category': 'حسابات الموردين والتوريدات',
                    'icon': 'local_shipping',
                    'items': items
                })

            # 4. تذاكر الورشة والصيانة
            tickets = MaintenanceTicket.objects.select_related('customer').filter(
                Q(ticket_number__icontains=query) | Q(device_name__icontains=query) | Q(customer__name__icontains=query)
            )[:5]
            if tickets.exists():
                items = []
                for t in tickets:
                    cust_title = t.customer.name if t.customer else 'عميل نقدي'
                    items.append({
                        'title': f"تذكرة #{t.ticket_number} - {t.device_name}",
                        'subtitle': f"العميل: {cust_title} | الحالة: {t.get_status_display()}",
                        'url': f'{prefix}/maintenance/',
                        'badge': t.get_status_display(),
                        'badge_type': 'primary' if t.status == 'delivered' else 'tertiary'
                    })
                results.append({
                    'category': 'تذاكر الورشة والصيانة',
                    'icon': 'build',
                    'items': items
                })

            # 5. فواتير المبيعات (POS)
            orders = Order.objects.select_related('customer').filter(
                Q(order_number__icontains=query) | Q(customer__name__icontains=query)
            )[:5]
            if orders.exists():
                items = []
                for o in orders:
                    cust_name = o.customer.name if o.customer else "عميل نقدي"
                    items.append({
                        'title': f"فاتورة مبيعات #{o.order_number}",
                        'subtitle': f"العميل: {cust_name} | {o.created_at.strftime('%Y-%m-%d %H:%M')}",
                        'url': f'{prefix}/pos/invoices/?q={o.order_number}',
                        'badge': f"{o.total_amount:,.2f} ج.م",
                        'badge_type': 'primary'
                    })
                results.append({
                    'category': 'فواتير المبيعات (POS)',
                    'icon': 'receipt_long',
                    'items': items
                })

            # 6. طلبات البضاعة والنواقص للموردين
            from inventory.models import PurchaseOrder
            purchase_orders = PurchaseOrder.objects.select_related('supplier').filter(
                Q(order_number__icontains=query) | Q(supplier__name__icontains=query) | Q(notes__icontains=query)
            )[:5]
            if purchase_orders.exists():
                items = []
                for po in purchase_orders:
                    supp_name = po.supplier.name if po.supplier else "عدة شركات"
                    items.append({
                        'title': f"طلب بضاعة #{po.order_number} ({supp_name})",
                        'subtitle': f"الحالة: {po.get_status_display()} | {po.created_at.strftime('%Y-%m-%d')}",
                        'url': f'{prefix}/inventory/orders/{po.id}/',
                        'badge': po.get_status_display(),
                        'badge_type': 'primary' if po.status == 'received' else 'tertiary'
                    })
                results.append({
                    'category': 'طلبات البضاعة والنواقص',
                    'icon': 'local_shipping',
                    'items': items
                })

            return JsonResponse({'results': results})
        finally:
            set_current_tenant(prev_tenant)


import os
import zipfile
from io import BytesIO
from datetime import datetime
from django.shortcuts import render, redirect
from django.http import HttpResponse, Http404, JsonResponse
from django.contrib import messages
from django.conf import settings
from django.core.management import call_command

class BackupDashboardView(TemplateView):
    """لوحة التحكم وإدارة النسخ الاحتياطية للبيانات والأمان"""
    template_name = "backup.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        db_path = settings.DATABASES['default']['NAME']
        db_size_mb = 0
        if isinstance(db_path, (str, os.PathLike)) and os.path.exists(db_path):
            db_size_mb = round(os.path.getsize(db_path) / (1024 * 1024), 2)

        media_size_mb = 0
        if os.path.exists(settings.MEDIA_ROOT):
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(settings.MEDIA_ROOT):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    if os.path.exists(fp):
                        total_size += os.path.getsize(fp)
            media_size_mb = round(total_size / (1024 * 1024), 2)

        context['db_size_mb'] = db_size_mb
        context['media_size_mb'] = media_size_mb
        context['now_str'] = datetime.now().strftime('%Y-%m-%d %H:%M')
        return context


class DownloadDatabaseBackupView(View):
    """تحميل نسخة احتياطية فورية من قاعدة البيانات"""
    def get(self, request, *args, **kwargs):
        now_str = datetime.now().strftime('%Y_%m_%d_%H%M%S')
        db_engine = settings.DATABASES['default']['ENGINE']
        
        if 'sqlite' in db_engine:
            db_path = settings.DATABASES['default']['NAME']
            if os.path.exists(db_path):
                with open(db_path, 'rb') as f:
                    response = HttpResponse(f.read(), content_type='application/x-sqlite3')
                    response['Content-Disposition'] = f'attachment; filename="elnamaa_db_backup_{now_str}.sqlite3"'
                    return response
        
        out = BytesIO()
        call_command('dumpdata', indent=2, stdout=out)
        out.seek(0)
        response = HttpResponse(out.read(), content_type='application/json')
        response['Content-Disposition'] = f'attachment; filename="elnamaa_data_backup_{now_str}.json"'
        return response


class DownloadMediaBackupView(View):
    """تحميل نسخة مضغوطة zip من الصور والمستندات المرفوعة"""
    def get(self, request, *args, **kwargs):
        media_dir = settings.MEDIA_ROOT
        now_str = datetime.now().strftime('%Y_%m_%d_%H%M%S')
        
        mem_file = BytesIO()
        with zipfile.ZipFile(mem_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            if os.path.exists(media_dir):
                for root, dirs, files in os.walk(media_dir):
                    for file in files:
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, media_dir)
                        zf.write(full_path, rel_path)
        
        mem_file.seek(0)
        response = HttpResponse(mem_file.read(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="elnamaa_media_backup_{now_str}.zip"'
        return response


class RestoreDatabaseBackupView(View):
    """استرجاع نسخة احتياطية من ملف مرفوع"""
    def post(self, request, *args, **kwargs):
        uploaded_file = request.FILES.get('backup_file')
        if not uploaded_file:
            messages.error(request, "يرجى اختيار ملف النسخة الاحتياطية أولاً.")
            return redirect('dashboard:backup_manage')
            
        file_name = uploaded_file.name.lower()
        try:
            if file_name.endswith('.sqlite3') or file_name.endswith('.db'):
                db_path = settings.DATABASES['default']['NAME']
                with open(db_path, 'wb+') as destination:
                    for chunk in uploaded_file.chunks():
                        destination.write(chunk)
                messages.success(request, "✅ تم استرجاع قاعدة البيانات كاملة بنجاح من ملف SQLite!")
            elif file_name.endswith('.json'):
                temp_path = os.path.join(settings.BASE_DIR, 'temp_restore.json')
                with open(temp_path, 'wb+') as destination:
                    for chunk in uploaded_file.chunks():
                        destination.write(chunk)
                call_command('loaddata', temp_path)
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                messages.success(request, "✅ تم استرجاع كافة البيانات بنجاح من ملف JSON!")
            else:
                messages.error(request, "صيغة الملف غير مدعومة. يرجى رفع ملف (.sqlite3) أو (.json).")
        except Exception as e:
            messages.error(request, f"فشلت عملية الاسترجاع: {str(e)}")
            
        return redirect('dashboard:backup_manage')


from core_project.gdrive_service import perform_gdrive_upload

class UploadToGoogleDriveBackupView(View):
    """رفع نسخة احتياطية من قاعدة البيانات مباشرة إلى Google Drive"""
    def post(self, request, *args, **kwargs):
        from dashboard.audit import log_activity
        success, message = perform_gdrive_upload()
        if success:
            messages.success(request, message)
            log_activity(request, module='backup', action_type='export', description="رفع نسخة احتياطية بنجاح إلى Google Drive", severity='info')
        else:
            messages.error(request, message)
            log_activity(request, module='backup', action_type='export', description=f"فشل رفع النسخة الاحتياطية إلى Google Drive: {message}", severity='warning')
        return redirect('dashboard:backup_manage')


from django.views.generic import ListView

class AuditLogListView(ListView):
    """
    صفحة الأرشيف الكامل لسجل النشاطات والحركات الرقابي (System Audit Log & Activity Tracker).
    تتيح استعراض وبحث وفلترة كافة الإجراءات مع تفاصيل دقيقة عن الجهاز، المتصفح، الـ IP، ونوع الحركة.
    """
    model = AuditLog
    template_name = "audit_log.html"
    context_object_name = "logs"
    paginate_by = 35

    def get_queryset(self):
        from dashboard.models import AuditLog
        qs = AuditLog.objects.select_related('user').all()

        # 1. Text Search (بحث في تفاصيل الحدث، اسم المستخدم، البريد، أو الـ IP أو الجهاز)
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(description__icontains=q) |
                Q(user_display__icontains=q) |
                Q(user_email__icontains=q) |
                Q(ip_address__icontains=q) |
                Q(device_info__icontains=q)
            )

        # 2. Module Filter (القسم)
        module = self.request.GET.get('module', '').strip()
        if module and module != 'all':
            qs = qs.filter(module=module)

        # 3. Action Type Filter (نوع الإجراء)
        action_type = self.request.GET.get('action_type', '').strip()
        if action_type and action_type != 'all':
            qs = qs.filter(action_type=action_type)

        # 4. Severity Filter (مستوى الأهمية / الحركات الحساسة)
        severity = self.request.GET.get('severity', '').strip()
        if severity == 'danger':
            qs = qs.filter(severity='danger')
        elif severity == 'warning':
            qs = qs.filter(severity='warning')
        elif severity == 'sensitive':
            qs = qs.filter(severity__in=['warning', 'danger'])
        elif severity == 'info':
            qs = qs.filter(severity='info')

        # 5. User Filter (المستخدم)
        user_val = self.request.GET.get('user', '').strip()
        if user_val and user_val != 'all':
            if user_val.isdigit():
                qs = qs.filter(user_id=int(user_val))
            else:
                qs = qs.filter(user_display=user_val)

        # 6. Date Filter (الفترة الزمنية)
        period = self.request.GET.get('period', '').strip()
        start_date = self.request.GET.get('start_date', '').strip()
        end_date = self.request.GET.get('end_date', '').strip()

        from django.utils import timezone
        import datetime
        today = timezone.now().date()

        if period == 'today':
            qs = qs.filter(created_at__date=today)
        elif period == 'yesterday':
            yesterday = today - datetime.timedelta(days=1)
            qs = qs.filter(created_at__date=yesterday)
        elif period == 'this_week':
            week_start = today - datetime.timedelta(days=today.weekday())
            qs = qs.filter(created_at__date__gte=week_start)
        elif period == 'this_month':
            month_start = today.replace(day=1)
            qs = qs.filter(created_at__date__gte=month_start)
        else:
            if start_date:
                qs = qs.filter(created_at__date__gte=start_date)
            if end_date:
                qs = qs.filter(created_at__date__lte=end_date)

        return qs.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from dashboard.models import AuditLog
        all_logs = AuditLog.objects.all()

        from django.utils import timezone
        today = timezone.now().date()

        # Summary KPIs
        context['total_logs_count'] = all_logs.count()
        context['today_logs_count'] = all_logs.filter(created_at__date=today).count()
        context['danger_logs_count'] = all_logs.filter(severity='danger').count()
        context['sensitive_logs_count'] = all_logs.filter(severity__in=['warning', 'danger']).count()
        context['active_users_count'] = all_logs.values('user_display').distinct().count()

        # Filter choices
        context['module_choices'] = AuditLog.MODULE_CHOICES
        context['action_choices'] = AuditLog.ACTION_CHOICES
        context['severity_choices'] = AuditLog.SEVERITY_CHOICES
        
        # Unique list of user names for filter
        user_names = all_logs.exclude(user_display='').values_list('user_display', flat=True).distinct()
        context['users_list'] = sorted(list(set(user_names)))

        # Preserved query parameters
        context['current_q'] = self.request.GET.get('q', '')
        context['current_module'] = self.request.GET.get('module', 'all')
        context['current_action_type'] = self.request.GET.get('action_type', 'all')
        context['current_severity'] = self.request.GET.get('severity', 'all')
        context['current_user'] = self.request.GET.get('user', 'all')
        context['current_period'] = self.request.GET.get('period', '')
        context['current_start_date'] = self.request.GET.get('start_date', '')
        context['current_end_date'] = self.request.GET.get('end_date', '')

        return context




