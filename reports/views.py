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

        messages.success(request, f"✅ تم اعتماد وحفظ '{audit.title}' بنجاح في أرشيف الجردات السابقة!")
        return redirect('reports:reports_view')
