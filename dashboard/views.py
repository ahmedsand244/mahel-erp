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
        cash_sales = Order.objects.filter(payment_method__in=['cash', 'visa']).aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')
        cash_deposits = pnl.get('cash_deposits', Decimal('0.00'))
        cash_withdrawals = pnl.get('cash_withdrawals', Decimal('0.00'))
        total_cash_inflow = cash_sales + pnl['labor_fees'] + collected_from_customers + cash_deposits
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
        ).order_by('stock_quantity', 'name')[:5]
        
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
        
        # 6. Interactive Chart Analytics (Last 7 Days Trend & Product Breakdown)
        from django.utils import timezone
        import datetime

        today = timezone.now().date()
        chart_dates = []
        chart_sales = []
        chart_profits = []

        for i in range(6, -1, -1):
            day_date = today - datetime.timedelta(days=i)
            day_str = day_date.strftime('%Y-%m-%d')
            chart_dates.append(day_date.strftime('%m/%d'))

            day_orders = Order.objects.filter(created_at__date=day_date)
            sales = day_orders.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')
            cogs = day_orders.aggregate(Sum('cost_of_goods_sold'))['cost_of_goods_sold__sum'] or Decimal('0.00')
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

        return context


class GlobalSearchView(View):
    """البحث المباشر الشامل في كافة أرجاء النظام"""
    def get(self, request, *args, **kwargs):
        query = request.GET.get('q', '').strip()
        if not query or len(query) < 1:
            return JsonResponse({'results': []})

        results = []

        # 1. المنتجات والمخزون
        products = Product.objects.filter(
            Q(name__icontains=query) | Q(sku__icontains=query)
        )[:5]
        if products.exists():
            items = []
            for p in products:
                items.append({
                    'title': p.name,
                    'subtitle': f"كود: {p.sku} | السعر: {p.selling_price} ج.م | المتاح: {p.stock_quantity}",
                    'url': '/inventory/',
                    'badge': f"{p.stock_quantity} قطعة",
                    'badge_type': 'primary' if p.stock_quantity > 0 else 'error'
                })
            results.append({
                'category': 'المنتجات والمخزون',
                'icon': 'inventory_2',
                'items': items
            })

        # 2. حسابات العملاء
        customers = Customer.objects.filter(
            Q(name__icontains=query) | Q(phone__icontains=query) | Q(workplace__icontains=query)
        )[:5]
        if customers.exists():
            items = []
            for c in customers:
                items.append({
                    'title': c.name,
                    'subtitle': f"هاتف: {c.phone or '—'} | مكان العمل: {c.workplace or '—'}",
                    'url': f'/ledger/customer/{c.id}/',
                    'badge': f"دين: {c.balance} ج.م" if c.balance > 0 else "مسدد بالكامل",
                    'badge_type': 'error' if c.balance > 0 else 'primary'
                })
            results.append({
                'category': 'حسابات العملاء (الشكك)',
                'icon': 'person',
                'items': items
            })

        # 3. حسابات الموردين
        suppliers = Supplier.objects.filter(
            Q(name__icontains=query) | Q(phone__icontains=query) | Q(company__icontains=query)
        )[:5]
        if suppliers.exists():
            items = []
            for s in suppliers:
                items.append({
                    'title': s.name,
                    'subtitle': f"الشركة: {s.company or '—'} | هاتف: {s.phone or '—'}",
                    'url': f'/ledger/supplier/{s.id}/',
                    'badge': f"مستحق: {s.balance} ج.م" if s.balance > 0 else "مسدد",
                    'badge_type': 'error' if s.balance > 0 else 'primary'
                })
            results.append({
                'category': 'حسابات الموردين والتوريدات',
                'icon': 'local_shipping',
                'items': items
            })

        # 4. تذاكر الصيانة
        tickets = MaintenanceTicket.objects.select_related('customer').filter(
            Q(ticket_number__icontains=query) | Q(device_name__icontains=query) | Q(customer__name__icontains=query)
        )[:5]
        if tickets.exists():
            items = []
            for t in tickets:
                items.append({
                    'title': f"تذكرة #{t.ticket_number} - {t.device_name}",
                    'subtitle': f"العميل: {t.customer.name}",
                    'url': '/maintenance/',
                    'badge': t.get_status_display(),
                    'badge_type': 'primary' if t.status == 'delivered' else 'tertiary'
                })
            results.append({
                'category': 'تذاكر الورشة والصيانة',
                'icon': 'build',
                'items': items
            })

        # 5. فواتير المبيعات POS
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
                    'url': '/pos/',
                    'badge': f"{o.total_amount} ج.م",
                    'badge_type': 'primary'
                })
            results.append({
                'category': 'فواتير المبيعات (POS)',
                'icon': 'receipt_long',
                'items': items
            })

        return JsonResponse({'results': results})


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
        success, message = perform_gdrive_upload()
        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)
        return redirect('dashboard:backup_manage')



