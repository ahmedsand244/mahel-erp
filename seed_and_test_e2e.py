import os
import sys
import django
from decimal import Decimal

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core_project.settings')
django.setup()

from inventory.models import Product, StockAlert
from ledger.models import Customer, Supplier, Transaction
from expenses.models import Expense
from pos.models import Order, OrderItem
from maintenance.models import MaintenanceTicket, TicketPartConsumption
from core_project.services import pos_checkout, add_maintenance_part, receive_customer_payment, send_supplier_payment, get_profit_and_loss

def run_e2e_scenarios():
    print("=" * 70)
    print("🚀 RUNNING E2E DATA SEEDING & FINANCIAL SCENARIOS (EGP / جنيه مصري)")
    print("=" * 70)

    # Clean existing database records for clean test run
    StockAlert.objects.all().delete()
    OrderItem.objects.all().delete()
    Order.objects.all().delete()
    TicketPartConsumption.objects.all().delete()
    MaintenanceTicket.objects.all().delete()
    Transaction.objects.all().delete()
    Customer.objects.all().delete()
    Supplier.objects.all().delete()
    Expense.objects.all().delete()
    Product.objects.all().delete()

    print("\n--- 🏭 SCENARIO A: STOCK IN & SUPPLIER PURCHASING ---")
    # 1. Create 5 Egyptian Suppliers
    suppliers = [
        Supplier.objects.create(name="شركة الدلتا للميكانيكا والجرارات", company="شركة الدلتا لإستيراد وتوزيع محركات الرش", balance=Decimal("45000.00")),
        Supplier.objects.create(name="مصنع الأمل لمواتير الرش الزراعي", company="شركة الأمل للميكانيكا الحديثة", balance=Decimal("28500.00")),
        Supplier.objects.create(name="الشركة المصرية لمضخات المياه", company="إيجبشن بومبست المصرية", balance=Decimal("15000.00")),
        Supplier.objects.create(name="شركة السويس لقطع غيار الديزل", company="سويس تيك للمحركات", balance=Decimal("32000.00")),
        Supplier.objects.create(name="شركة النيل للزيوت والشحومات", company="مصر للزيوت الهيدروليكية", balance=Decimal("8500.00")),
    ]
    print(f"✅ Created {len(suppliers)} Suppliers with realistic Egyptian profiles.")

    # 2. Inject 30+ Diverse Agricultural Inventory Items in EGP
    products_data = [
        # Motors
        ("موتور رش ياماها زراعي 15 حصان", "PMP-YMH-15HP", "880123456701", Decimal("12000.00"), Decimal("15500.00"), 15, 3),
        ("محرك ديزل كوبوتا 24 حصان", "ENG-KBT-24HP", "880123456702", Decimal("35000.00"), Decimal("42000.00"), 8, 2),
        ("محرك هوندا بنزين 6.5 حصان", "ENG-HND-65HP", "880123456703", Decimal("6500.00"), Decimal("8200.00"), 12, 3),
        ("موتور طلمبة رش 4 زمان", "PMP-4STRK-01", "880123456704", Decimal("4800.00"), Decimal("6100.00"), 10, 2),
        ("محرك روبن 5 حصان زراعي", "ENG-RBN-5HP", "880123456705", Decimal("7200.00"), Decimal("9000.00"), 6, 2),

        # Pistons & Rings
        ("مكبس محرك ديزل 120mm", "PST-DSL-120M", "880123456706", Decimal("1800.00"), Decimal("2450.00"), 20, 4),
        ("طقم شنابر مكبس موتور ياماها", "RNG-YMH-SET", "880123456707", Decimal("350.00"), Decimal("520.00"), 45, 5),
        ("بستم صيانة روبن 65mm", "PST-RBN-65M", "880123456708", Decimal("680.00"), Decimal("950.00"), 18, 3),
        ("طقم بستم وكاميرا كوبوتا", "PST-KBT-KIT", "880123456709", Decimal("3200.00"), Decimal("4300.00"), 7, 2),

        # Carburetors & Fuel System
        ("كربوراتير موتور روبن أصلي", "CRB-RBN-ORG", "880123456710", Decimal("850.00"), Decimal("1200.00"), 15, 3),
        ("كربوراتير موتور رش ياماها", "CRB-YMH-15H", "880123456711", Decimal("920.00"), Decimal("1350.00"), 12, 3),
        ("طلمبة جلب جاز ديزل", "FLP-DSL-001", "880123456712", Decimal("1400.00"), Decimal("1950.00"), 9, 2),
        ("رشاش ديزل كوبوتا كامل", "INJ-KBT-DSL", "880123456713", Decimal("1100.00"), Decimal("1600.00"), 14, 3),

        # Spraying Hoses & Guns
        ("خرطوم رش زراعي مقوى 100 متر", "HOS-SPR-100M", "880123456714", Decimal("1650.00"), Decimal("2200.00"), 30, 5),
        ("مسدس رش زراعي ضغط عالي", "GUN-SPR-HPR", "880123456715", Decimal("420.00"), Decimal("650.00"), 50, 8),
        ("طقم نزلات ورشاشات نحاس", "NZL-BRS-SET", "880123456716", Decimal("180.00"), Decimal("280.00"), 60, 10),
        ("خرطوم شفط ضغط 2 بوصة", "HOS-SUC-2IN", "880123456717", Decimal("850.00"), Decimal("1250.00"), 22, 4),

        # Oils, Seals & Gaskets
        ("زيت محركات ديزل 15W40 سعة 5 لتر", "OIL-DSL-5L", "880123456718", Decimal("380.00"), Decimal("520.00"), 80, 10),
        ("شحم هيدروليك عالي الجودة 1كجم", "GRS-HYD-1KG", "880123456719", Decimal("140.00"), Decimal("210.00"), 100, 15),
        ("طقم جوانات محرك ياماها", "GSK-YMH-SET", "880123456720", Decimal("220.00"), Decimal("340.00"), 35, 5),
        ("أولسيه كرانك أمامي كوبوتا", "OIL-SL-KBT", "880123456721", Decimal("75.00"), Decimal("120.00"), 40, 5),
        ("أولسيه عمود طلمبة الرش", "OIL-SL-PMP", "880123456722", Decimal("60.00"), Decimal("95.00"), 50, 8),

        # Filters & Low Stock Alert Test Items
        ("فلتر هواء عالي الكفاءة", "FLT-AIR-HD90", "880123456723", Decimal("280.00"), Decimal("420.00"), 25, 5),
        ("فلتر زيت هيدروليك", "FLT-HYD-01", "880123456724", Decimal("95.00"), Decimal("150.00"), 2, 5), # Low Stock Alert!
        ("فلتر جاز ديزل", "FLT-FUEL-D02", "880123456725", Decimal("110.00"), Decimal("175.00"), 1, 4), # Low Stock Alert!
        ("شمعة إشعال (بوجيه) روبن", "SPK-PLG-RBN", "880123456726", Decimal("45.00"), Decimal("75.00"), 2, 6), # Low Stock Alert!

        # Pumps & Valves
        ("مضخة مياه طرد مركزي 50HP", "PMP-CEN-50HP", "880123456727", Decimal("22000.00"), Decimal("28500.00"), 5, 2),
        ("طلمبة رش 3 سلندر نحاس", "PMP-BRS-3CYL", "880123456728", Decimal("4500.00"), Decimal("6200.00"), 11, 3),
        ("محبس طرد 2 بوصة نحاس", "VLV-BRS-2IN", "880123456729", Decimal("320.00"), Decimal("480.00"), 30, 5),
        ("رمان بلي محرك 6205", "BRG-6205-HD", "880123456730", Decimal("120.00"), Decimal("190.00"), 45, 6),
        ("سير طلمبة رش V-Belt", "BLT-VB-B54", "880123456731", Decimal("85.00"), Decimal("140.00"), 50, 8),
    ]

    products_dict = {}
    for name, sku, barcode, p_price, s_price, stock, thresh in products_data:
        prod = Product.objects.create(
            name=name,
            sku=sku,
            barcode=barcode,
            purchase_price=p_price,
            selling_price=s_price,
            stock_quantity=stock,
            min_stock_threshold=thresh
        )
        products_dict[sku] = prod
        # Trigger stock alert if below threshold
        if stock <= thresh:
            StockAlert.objects.create(
                product=prod,
                message=f"تنبيه: انخفض مخزون '{prod.name}' إلى {stock} قطع (الحد الأدنى {thresh})."
            )

    print(f"✅ Injected {len(products_data)} Agricultural products into inventory with prices in EGP.")
    alerts_count = StockAlert.objects.filter(is_resolved=False).count()
    print(f"🔔 Active Stock Alerts triggered: {alerts_count} alerts.")

    # 3. Create 5 Egyptian Farmers / Agribusiness Clients
    c1 = Customer.objects.create(name="الحاج متولي عبد الصمد (مزارع النخيل المتحد)", phone="01012345678", balance=Decimal("0.00"))
    c2 = Customer.objects.create(name="المهندس سعيد الشرقاوي (مزارع الوادي الأخضر)", phone="01198765432", balance=Decimal("0.00"))
    c3 = Customer.objects.create(name="الحاج عبد الستار الفقي (مؤسسة زراعية الصحراء)", phone="01245551112", balance=Decimal("0.00"))
    c4 = Customer.objects.create(name="الشيخ محمد الراجحي (مزرعة التين والزيتون)", phone="01522233344", balance=Decimal("0.00"))
    c5 = Customer.objects.create(name="المعلم بسيوني الحفناوي (ورشة الحفناوي للميكانيكا)", phone="01066677788", balance=Decimal("0.00"))
    print(f"✅ Created 5 Egyptian Customer profiles.")


    print("\n--- 💳 SCENARIO B: POS CHECKOUT DYNAMICS (CASH, VISA, DEFERRED/آجل) ---")
    # Checkout 1: Cash Payment
    cart_cash = [
        {'product_id': products_dict['HOS-SPR-100M'].id, 'quantity': 2}, # 2 * 2200 = 4400
        {'product_id': products_dict['GUN-SPR-HPR'].id, 'quantity': 3},  # 3 * 650 = 1950
        {'product_id': products_dict['OIL-DSL-5L'].id, 'quantity': 4},   # 4 * 520 = 2080
    ]
    order_cash = pos_checkout(
        order_number="POS-EGP-1001",
        payment_method="cash",
        cart_items=cart_cash
    )
    print(f"✅ Cash Checkout Success: Order #{order_cash.order_number} Total: {order_cash.total_amount} EGP (COGS: {order_cash.cost_of_goods_sold} EGP)")

    # Checkout 2: Visa Payment
    cart_visa = [
        {'product_id': products_dict['ENG-HND-65HP'].id, 'quantity': 1}, # 8200
        {'product_id': products_dict['NZL-BRS-SET'].id, 'quantity': 5},   # 5 * 280 = 1400
    ]
    order_visa = pos_checkout(
        order_number="POS-EGP-1002",
        payment_method="visa",
        cart_items=cart_visa
    )
    print(f"✅ Visa Checkout Success: Order #{order_visa.order_number} Total: {order_visa.total_amount} EGP")

    # Checkout 3: Deferred / Credit (الشكك) for Farmer Haj Metwally
    cart_deferred = [
        {'product_id': products_dict['PMP-YMH-15HP'].id, 'quantity': 1}, # 15500
        {'product_id': products_dict['PST-DSL-120M'].id, 'quantity': 2}, # 2 * 2450 = 4900
    ]
    order_def = pos_checkout(
        order_number="POS-EGP-1003",
        payment_method="deferred",
        cart_items=cart_deferred,
        customer_id=c1.id
    )
    c1.refresh_from_db()
    print(f"✅ Deferred Credit Checkout Success: Order #{order_def.order_number} Total: {order_def.total_amount} EGP")
    print(f"📌 Customer '{c1.name}' Ledger Balance updated automatically to: {c1.balance} EGP")


    print("\n--- 🛠️ SCENARIO C: WORKSHOP & MAINTENANCE LIFECYCLE ---")
    # Ticket 1: Yamaha Motor Repair
    t1 = MaintenanceTicket.objects.create(
        ticket_number="MNT-2026-01",
        customer=c2,
        device_name="موتور رش ياماها 15 حصان (صيانة شاملة ورأس الضاغط)",
        status="in_progress",
        labor_fees=Decimal("450.00") # 100% Margin Labor
    )
    # Consuming parts inside maintenance
    add_maintenance_part(t1.id, products_dict['FLT-AIR-HD90'].id, 1) # Charged 420, Cost 280
    add_maintenance_part(t1.id, products_dict['OIL-SL-KBT'].id, 2)    # Charged 2*120=240, Cost 2*75=150
    t1.refresh_from_db()

    # Complete and deliver ticket
    t1.status = 'delivered'
    t1.save()
    print(f"✅ Maintenance Ticket #{t1.ticket_number} delivered:")
    print(f"   - Labor Fees (100% Net Profit): {t1.labor_fees} EGP")
    print(f"   - Parts Billed: {t1.parts_sell} EGP (Cost: {t1.parts_cost} EGP)")

    # Ticket 2: Robin Engine Overhaul
    t2 = MaintenanceTicket.objects.create(
        ticket_number="MNT-2026-02",
        customer=c3,
        device_name="محرك روبن 5 حصان زراعي",
        status="delivered",
        labor_fees=Decimal("650.00")
    )
    add_maintenance_part(t2.id, products_dict['CRB-RBN-ORG'].id, 1) # Charged 1200, Cost 850
    add_maintenance_part(t2.id, products_dict['SPK-PLG-RBN'].id, 2)  # Charged 2*75=150, Cost 2*45=90
    t2.refresh_from_db()
    print(f"✅ Maintenance Ticket #{t2.ticket_number} delivered. Total Labor: {t2.labor_fees} EGP, Parts Sell: {t2.parts_sell} EGP")


    print("\n--- 📖 SCENARIO D: LEDGER RECONCILIATION & PARTIAL DEBT PAYMENT ---")
    # Customer c1 owes 20,400.00 EGP (15,500 + 4,900)
    print(f"Initial Debt for '{c1.name}': {c1.balance} EGP")
    # Partial payment of 8,400 EGP
    receive_customer_payment(c1.id, Decimal("8400.00"))
    c1.refresh_from_db()
    print(f"✅ Partial Payment Received: 8,400.00 EGP. Remaining Debt Balance: {c1.balance} EGP")
    
    # Supplier Payment Settlement
    s1 = suppliers[0]
    print(f"Initial Debt to Supplier '{s1.name}': {s1.balance} EGP")
    send_supplier_payment(s1.id, Decimal("15000.00"))
    s1.refresh_from_db()
    print(f"✅ Settlement Payment Sent: 15,000.00 EGP. Remaining Supplier Debt: {s1.balance} EGP")


    print("\n--- 📊 SCENARIO E: OPERATING EXPENSES & P&L PROFIT ACCURACY ---")
    Expense.objects.create(category="rent", description="إيجار المعرض والورشة الرئيسي لشهر أغسطس", amount=Decimal("15000.00"))
    Expense.objects.create(category="salary", description="رواتب فني الصيانة ومحاسب المبيعات", amount=Decimal("22000.00"))
    Expense.objects.create(category="utility", description="فاتورة كهرباء ومياه الورشة ورسم الخدمات", amount=Decimal("2850.00"))
    Expense.objects.create(category="marketing", description="حملة إعلانات فيسبوك للمزارعين والمستلزمات", amount=Decimal("1800.00"))
    print("✅ Registered 4 Monthly Operating Expenses in EGP.")

    # Audit P&L Financial Calculations
    pnl = get_profit_and_loss()
    print("\n" + "=" * 70)
    print("📈 EXECUTIVE P&L FINANCIAL AUDIT REPORT (EGP)")
    print("=" * 70)
    print(f"1. Gross POS Sales Revenues : {pnl['gross_sales']:>12.2f} EGP")
    print(f"2. POS Cost of Goods (COGS) : -{pnl['cogs']:>11.2f} EGP")
    print(f"3. Maintenance Labor Fees   : +{pnl['labor_fees']:>11.2f} EGP (100% Margin)")
    print(f"4. Maintenance Parts Sales  : +{pnl['parts_sell']:>11.2f} EGP")
    print(f"5. Maintenance Parts Cost   : -{pnl['parts_cost']:>11.2f} EGP")
    print(f"6. Total Operating Expenses : -{pnl['total_expenses']:>11.2f} EGP")
    print("-" * 70)
    print(f"Total Revenues (Revenues + Labor) : {pnl['total_revenues'] + pnl['labor_fees']:>12.2f} EGP")
    print(f"Total Costs & Expenses             : {pnl['total_costs'] + pnl['total_expenses']:>12.2f} EGP")
    print("-" * 70)
    print(f"💰 NET PROFIT (صافي الأرباح الفعلية): {pnl['net_profit']:>12.2f} EGP")
    print("=" * 70)

    # Verification checks
    expected_gross_sales = order_cash.total_amount + order_visa.total_amount + order_def.total_amount
    expected_cogs = order_cash.cost_of_goods_sold + order_visa.cost_of_goods_sold + order_def.cost_of_goods_sold
    expected_labor = t1.labor_fees + t2.labor_fees
    expected_parts_sell = t1.parts_sell + t2.parts_sell
    expected_parts_cost = t1.parts_cost + t2.parts_cost
    expected_expenses = Decimal("15000.00") + Decimal("22000.00") + Decimal("2850.00") + Decimal("1800.00")
    
    expected_net_profit = (expected_gross_sales + expected_parts_sell + expected_labor) - (expected_cogs + expected_parts_cost + expected_expenses)

    assert pnl['gross_sales'] == expected_gross_sales, "Gross sales mismatch!"
    assert pnl['cogs'] == expected_cogs, "COGS mismatch!"
    assert pnl['labor_fees'] == expected_labor, "Labor fees mismatch!"
    assert pnl['total_expenses'] == expected_expenses, "Expenses mismatch!"
    assert pnl['net_profit'] == expected_net_profit, "Net profit calculation mismatch!"
    
    print("\n✨ ALL 5 FINANCIAL & OPERATIONAL E2E SCENARIOS PASSED WITH 100% DECIMAL PRECISION! ✨\n")

if __name__ == '__main__':
    run_e2e_scenarios()
