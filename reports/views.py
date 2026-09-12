import json
from django.views.generic import TemplateView, View
from django.shortcuts import redirect
from django.contrib import messages
from django.db.models import Sum, F
from django.utils import timezone
from decimal import Decimal
import datetime

from inventory.models import Product
from pos.models import Order
from maintenance.models import MaintenanceTicket
from expenses.models import Expense
from ledger.models import Customer, Supplier
from core_project.services import get_profit_and_loss
from .models import StoreAudit


class ReportsProfitLossView(TemplateView):
    template_name = "reports.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Period filter: all / today / yesterday / this_month / custom
        period = self.request.GET.get('period', 'all')
        start_date_str = self.request.GET.get('start_date', '').strip()
        end_date_str = self.request.GET.get('end_date', '').strip()

        start_date = None
        end_date = None
        today = timezone.now().date()

        if period == 'today':
            start_date = end_date = today
            start_date_str = end_date_str = today.strftime('%Y-%m-%d')
        elif period == 'yesterday':
            yesterday = today - datetime.timedelta(days=1)
            start_date = end_date = yesterday
            start_date_str = end_date_str = yesterday.strftime('%Y-%m-%d')
        elif period == 'this_month':
            start_date = today.replace(day=1)
            end_date = today
            start_date_str = start_date.strftime('%Y-%m-%d')
            end_date_str = end_date.strftime('%Y-%m-%d')
        elif period == 'custom':
            if start_date_str:
                try:
                    start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
                except ValueError:
                    start_date = None
            if end_date_str:
                try:
                    end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
                except ValueError:
                    end_date = None

        context['selected_period'] = period
        context['start_date_str'] = start_date_str
        context['end_date_str'] = end_date_str

        # 1. Period P&L calculation
        pnl = get_profit_and_loss(start_date=start_date, end_date=end_date)
        
        total_income = pnl['gross_sales'] + pnl['parts_sell'] + pnl['labor_fees']
        total_costs_all = pnl['cogs'] + pnl['parts_cost'] + pnl['total_expenses']

        context.update(pnl)
        context['total_income'] = total_income
        context['total_costs_all'] = total_costs_all

        # 2. Inventory Valuation (الجرد وتقييم رأس المال)
        products = Product.objects.all()
        inventory_cost_val = Decimal('0.00')
        inventory_retail_val = Decimal('0.00')

        for p in products:
            inventory_cost_val += (p.purchase_price * Decimal(p.stock_quantity))
            inventory_retail_val += (p.selling_price * Decimal(p.stock_quantity))

        context['inventory_cost_val'] = inventory_cost_val
        context['inventory_retail_val'] = inventory_retail_val
        context['inventory_potential_profit'] = inventory_retail_val - inventory_cost_val
        context['total_products_count'] = products.count()

        # 3. Ledger balances (ديون العملاء والتزامات الموردين)
        total_customer_debts = Customer.objects.filter(balance__gt=0).aggregate(Sum('balance'))['balance__sum'] or Decimal('0.00')
        total_supplier_debts = Supplier.objects.filter(balance__gt=0).aggregate(Sum('balance'))['balance__sum'] or Decimal('0.00')

        context['total_customer_debts'] = total_customer_debts
        context['total_supplier_debts'] = total_supplier_debts

        # 4. Saved Store Audits Archive
        context['saved_audits'] = StoreAudit.objects.all().order_by('-created_at')

        # 5. Interactive Dynamic Charts Data (اتجاهات المبيعات والمصروفات وهيكل التكاليف)
        if start_date and end_date:
            range_start = start_date
            range_end = end_date
            if range_start == range_end:
                range_start = range_end - datetime.timedelta(days=6)
        elif start_date:
            range_start = start_date
            range_end = today
        else:
            range_start = today - datetime.timedelta(days=13)
            range_end = today

        days_count = (range_end - range_start).days + 1
        if days_count > 60:
            step = max(1, days_count // 30)
            date_list = [range_start + datetime.timedelta(days=i) for i in range(0, days_count, step)]
            if date_list[-1] != range_end:
                date_list.append(range_end)
        else:
            date_list = [range_start + datetime.timedelta(days=i) for i in range(days_count)]

        daily_orders = {
            row['created_at__date']: row
            for row in Order.objects.filter(created_at__date__gte=range_start, created_at__date__lte=range_end)
                                    .values('created_at__date')
                                    .annotate(sales=Sum('total_amount'), cogs=Sum('cost_of_goods_sold'))
        }
        daily_expenses = {
            row['created_at__date']: row['total_exp']
            for row in Expense.objects.filter(created_at__date__gte=range_start, created_at__date__lte=range_end)
                                      .values('created_at__date')
                                      .annotate(total_exp=Sum('amount'))
        }

        trend_labels = []
        trend_sales = []
        trend_expenses = []
        trend_profits = []

        for d in date_list:
            trend_labels.append(d.strftime('%m/%d'))
            d_order = daily_orders.get(d, {})
            d_sales = float(d_order.get('sales') or Decimal('0.00'))
            d_cogs = float(d_order.get('cogs') or Decimal('0.00'))
            d_exp = float(daily_expenses.get(d) or Decimal('0.00'))
            d_total_costs = d_cogs + d_exp
            d_profit = d_sales - d_total_costs

            trend_sales.append(round(d_sales, 2))
            trend_expenses.append(round(d_total_costs, 2))
            trend_profits.append(round(d_profit, 2))

        # Expenses Structure Breakdown
        exp_qs = Expense.objects.all()
        if start_date:
            exp_qs = exp_qs.filter(created_at__date__gte=start_date)
        if end_date:
            exp_qs = exp_qs.filter(created_at__date__lte=end_date)

        category_labels_dict = dict(Expense.CATEGORY_CHOICES)
        exp_breakdown = exp_qs.values('category').annotate(cat_sum=Sum('amount'))
        
        breakdown_labels = ['تكلفة بضاعة مباعة (COGS)']
        breakdown_values = [float(pnl['cogs'] or 0)]

        if pnl['parts_cost'] > 0:
            breakdown_labels.append('تكلفة قطع صيانة')
            breakdown_values.append(float(pnl['parts_cost']))

        for item in exp_breakdown:
            c_name = category_labels_dict.get(item['category'], item['category'])
            c_val = float(item['cat_sum'] or 0)
            if c_val > 0:
                breakdown_labels.append(c_name)
                breakdown_values.append(c_val)

        # Revenue Streams Breakdown
        rev_labels = ['مبيعات المحل (POS)']
        rev_values = [float(pnl['gross_sales'] or 0)]
        if pnl['labor_fees'] > 0:
            rev_labels.append('مصنعيات الورشة')
            rev_values.append(float(pnl['labor_fees']))
        if pnl['parts_sell'] > 0:
            rev_labels.append('قطع غيار الصيانة')
            rev_values.append(float(pnl['parts_sell']))

        context['chart_trend_labels_json'] = json.dumps(trend_labels, ensure_ascii=False)
        context['chart_trend_sales_json'] = json.dumps(trend_sales)
        context['chart_trend_expenses_json'] = json.dumps(trend_expenses)
        context['chart_trend_profits_json'] = json.dumps(trend_profits)
        context['chart_breakdown_labels_json'] = json.dumps(breakdown_labels, ensure_ascii=False)
        context['chart_breakdown_values_json'] = json.dumps(breakdown_values)
        context['chart_rev_labels_json'] = json.dumps(rev_labels, ensure_ascii=False)
        context['chart_rev_values_json'] = json.dumps(rev_values)

        return context


class SaveAuditView(View):
    """اعتماد وحفظ جلسة الجرد في الأرشيف"""
    def post(self, request, *args, **kwargs):
        title = request.POST.get('title', '').strip() or f"جرد المحل بتاريخ {timezone.now().strftime('%Y-%m-%d')}"
        start_date_str = request.POST.get('start_date', '').strip()
        end_date_str = request.POST.get('end_date', '').strip()
        notes = request.POST.get('notes', '').strip()

        start_date = None
        end_date = None

        if start_date_str:
            try:
                start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass
        if end_date_str:
            try:
                end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        pnl = get_profit_and_loss(start_date=start_date, end_date=end_date)
        
        products = Product.objects.all()
        inv_cost = Decimal('0.00')
        inv_retail = Decimal('0.00')
        for p in products:
            inv_cost += (p.purchase_price * Decimal(p.stock_quantity))
            inv_retail += (p.selling_price * Decimal(p.stock_quantity))

        cust_debts = Customer.objects.filter(balance__gt=0).aggregate(Sum('balance'))['balance__sum'] or Decimal('0.00')
        sup_debts = Supplier.objects.filter(balance__gt=0).aggregate(Sum('balance'))['balance__sum'] or Decimal('0.00')

        audit = StoreAudit.objects.create(
            title=title,
            start_date=start_date,
            end_date=end_date,
            gross_sales=pnl['gross_sales'],
            cogs=pnl['cogs'],
            maintenance_labor=pnl['labor_fees'],
            maintenance_parts_sell=pnl['parts_sell'],
            maintenance_parts_cost=pnl['parts_cost'],
            total_expenses=pnl['total_expenses'],
            net_profit=pnl['net_profit'],
            inventory_cost_value=inv_cost,
            inventory_retail_value=inv_retail,
            customer_debts=cust_debts,
            supplier_debts=sup_debts,
            notes=notes
        )

        messages.success(request, f"تم اعتماد وحفظ '{audit.title}' بنجاح في أرشيف الجردات السابقة.")
        return redirect('reports:reports_view')
