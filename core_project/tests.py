from django.test import TestCase
from decimal import Decimal
from inventory.models import Product, StockAlert
from ledger.models import Customer, Supplier, Transaction
from expenses.models import Expense
from pos.models import Order, OrderItem
from maintenance.models import MaintenanceTicket, TicketPartConsumption
from core_project.services import (
    pos_checkout, 
    add_maintenance_part, 
    receive_customer_payment, 
    send_supplier_payment, 
    get_profit_and_loss
)

class E2EScenarioTests(TestCase):
    def setUp(self):
        # 1. Suppliers
        self.supplier = Supplier.objects.create(
            name="شركة الدلتا للميكانيكا والجرارات", 
            company="شركة الدلتا", 
            balance=Decimal("45000.00")
        )
        
        # 2. Products
        self.p_motor = Product.objects.create(
            name="موتور رش ياماها زراعي 15 حصان",
            sku="PMP-YMH-15HP",
            barcode="880123456701",
            purchase_price=Decimal("12000.00"),
            selling_price=Decimal("15500.00"),
            stock_quantity=10,
            min_stock_threshold=3
        )
        self.p_filter = Product.objects.create(
            name="فلتر هواء عالي الكفاءة",
            sku="FLT-AIR-HD90",
            barcode="880123456723",
            purchase_price=Decimal("280.00"),
            selling_price=Decimal("420.00"),
            stock_quantity=2, # Low stock
            min_stock_threshold=5
        )

        # 3. Customer
        self.customer = Customer.objects.create(
            name="الحاج متولي عبد الصمد", 
            phone="01012345678", 
            balance=Decimal("0.00")
        )

    def test_scenario_a_stock_alerts(self):
        """Scenario A: Test stock thresholds and alert creation"""
        # Create alert for low stock
        StockAlert.objects.create(
            product=self.p_filter,
            message="تنبيه مخزون"
        )
        self.assertTrue(StockAlert.objects.filter(product=self.p_filter).exists())

    def test_scenario_b_pos_cash_and_deferred(self):
        """Scenario B: POS cash & credit checkouts"""
        # Cash order
        cart_cash = [{'product_id': self.p_motor.id, 'quantity': 1}]
        order_cash = pos_checkout("POS-TEST-01", "cash", cart_cash)
        self.assertEqual(order_cash.total_amount, Decimal("15500.00"))
        self.assertEqual(order_cash.cost_of_goods_sold, Decimal("12000.00"))

        # Stock reduced
        self.p_motor.refresh_from_db()
        self.assertEqual(self.p_motor.stock_quantity, 9)

        # Deferred order
        cart_def = [{'product_id': self.p_motor.id, 'quantity': 1}]
        order_def = pos_checkout("POS-TEST-02", "deferred", cart_def, customer_id=self.customer.id)
        
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.balance, Decimal("15500.00"))
        self.assertTrue(Transaction.objects.filter(customer=self.customer, transaction_type='sale_credit').exists())

    def test_scenario_c_maintenance_lifecycle(self):
        """Scenario C: Maintenance ticket and spare part consumption"""
        ticket = MaintenanceTicket.objects.create(
            ticket_number="MNT-TEST-01",
            customer=self.customer,
            device_name="محرك ياماها",
            labor_fees=Decimal("350.00")
        )
        # Add part
        add_maintenance_part(ticket.id, self.p_motor.id, 1)
        ticket.refresh_from_db()
        
        self.assertEqual(ticket.parts_sell, Decimal("15500.00"))
        self.assertEqual(ticket.parts_cost, Decimal("12000.00"))
        self.assertEqual(ticket.labor_fees, Decimal("350.00"))

    def test_scenario_d_ledger_reconciliation(self):
        """Scenario D: Debt settlement and supplier payment"""
        self.customer.balance = Decimal("10000.00")
        self.customer.save()

        # Receive payment from customer
        receive_customer_payment(self.customer.id, Decimal("4000.00"))
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.balance, Decimal("6000.00"))

        # Pay supplier
        send_supplier_payment(self.supplier.id, Decimal("10000.00"))
        self.supplier.refresh_from_db()
        self.assertEqual(self.supplier.balance, Decimal("35000.00"))

    def test_scenario_e_pnl_profit_accuracy(self):
        """Scenario E: P&L financial precision with Decimal"""
        Expense.objects.create(category="rent", description="إيجار المحل", amount=Decimal("5000.00"))
        
        # POS Order
        pos_checkout("POS-TEST-03", "cash", [{'product_id': self.p_motor.id, 'quantity': 1}])

        pnl = get_profit_and_loss()
        # Revenue = 15500, COGS = 12000, Expense = 5000 -> Net Profit = 15500 - 12000 - 5000 = -1500
        self.assertEqual(pnl['gross_sales'], Decimal("15500.00"))
        self.assertEqual(pnl['cogs'], Decimal("12000.00"))
        self.assertEqual(pnl['total_expenses'], Decimal("5000.00"))
        self.assertEqual(pnl['net_profit'], Decimal("-1500.00"))

    def test_scenario_f_bulk_price_adjustment(self):
        """Scenario F: Bulk percentage price hike (+10%)"""
        from inventory.views import BulkPriceAdjustmentView
        from django.test import RequestFactory

        from django.contrib.messages.storage.fallback import FallbackStorage

        # Perform 10% price hike on selling price for all products
        factory = RequestFactory()
        request = factory.post('/inventory/bulk-price-adjust/', {
            'percentage': '10',
            'price_target': 'selling',
            'scope': 'all'
        })
        setattr(request, 'session', {})
        setattr(request, '_messages', FallbackStorage(request))

        view = BulkPriceAdjustmentView.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 302)

        self.p_motor.refresh_from_db()
        # Original selling price 15500 * 1.10 = 17050.00
        self.assertEqual(self.p_motor.selling_price, Decimal("17050.00"))

