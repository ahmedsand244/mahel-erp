from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from inventory.models import Product, StockAlert
from ledger.models import Customer, Supplier, Transaction
from pos.models import Order, OrderItem
from maintenance.models import MaintenanceTicket, TicketPartConsumption

@transaction.atomic
def pos_checkout(order_number, payment_method, cart_items, customer_id=None):
    """
    Safely process order checkouts:
    - Calculates totals, costs, and profits.
    - Updates stock levels, generating alerts if thresholds are breached.
    - Records debit transactions in client ledgers if the checkout is dynamic credit/deferred.
    """
    customer = None
    if customer_id:
        customer = Customer.objects.select_for_update().get(id=customer_id)

    # 1. First, create basic order
    order = Order.objects.create(
        order_number=order_number,
        customer=customer,
        payment_method=payment_method,
        total_amount=Decimal('0.00'),
        cost_of_goods_sold=Decimal('0.00')
    )

    total_amount = Decimal('0.00')
    total_cost = Decimal('0.00')

    # 2. Iterate items, verify and deduct stock
    for item in cart_items:
        product_id = item.get('product_id')
        qty = int(item.get('quantity', 1))
        
        # lock product row to prevent race conditions
        product = Product.objects.select_for_update().get(id=product_id)
        if product.stock_quantity < qty:
            raise ValueError(f"الكمية غير كافية في المخزن للمنتج: {product.name}")

        item_sell_price = product.selling_price
        item_cost = product.purchase_price
        
        # Calculate sub-totals
        item_total = item_sell_price * qty
        item_total_cost = item_cost * qty
        
        total_amount += item_total
        total_cost += item_total_cost

        # Create OrderItem
        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=qty,
            unit_price=item_sell_price,
            cost=item_cost
        )

        # Deduct inventory
        product.stock_quantity -= qty
        product.save()

        # Check stock alerts
        if product.stock_quantity <= product.min_stock_threshold:
            StockAlert.objects.create(
                product=product,
                message=f"تنبيه: لقد وصلت كمية '{product.name}' إلى الحد الأدنى ({product.stock_quantity} قطع متبقية)."
            )

    # 3. Save final prices
    order.total_amount = total_amount
    order.cost_of_goods_sold = total_cost
    order.save()

    # 4. Handle ledger updates for deferred payment
    if payment_method == 'deferred':
        if not customer:
            raise ValueError("يجب تحديد عميل للمبيعات الآجلة (الشكك)")
        
        # Increase customer debt balance
        customer.balance += total_amount
        customer.save()

        # Write transaction record
        Transaction.objects.create(
            customer=customer,
            amount=total_amount,
            transaction_type='sale_credit'
        )

    return order


@transaction.atomic
def add_maintenance_part(ticket_id, product_id, qty):
    """
    Consumes inventory parts inside maintenance ticket repairs, updating costs dynamically.
    """
    ticket = MaintenanceTicket.objects.select_for_update().get(id=ticket_id)
    product = Product.objects.select_for_update().get(id=product_id)

    if product.stock_quantity < qty:
         raise ValueError(f"المخزون غير كافٍ لتركيب: {product.name}")

    price_charged = product.selling_price
    cost = product.purchase_price

    # Deduct stock
    product.stock_quantity -= qty
    product.save()

    # Alert if needed
    if product.stock_quantity <= product.min_stock_threshold:
        StockAlert.objects.create(
            product=product,
            message=f"تنبيه صيانة: انخفض مخزون '{product.name}' إلى الحد الأدنى ({product.stock_quantity} قطع متبقية)."
        )

    # Create part consumption entry
    consumption = TicketPartConsumption.objects.create(
        ticket=ticket,
        product=product,
        quantity=qty,
        price_charged=price_charged,
        cost=cost
    )

    # Update ticket parts total
    ticket.parts_cost += (cost * qty)
    ticket.parts_sell += (price_charged * qty)
    ticket.save()

    return consumption


@transaction.atomic
def receive_customer_payment(customer_id, amount):
    """
    Receive payments from customers to settle credit ledger accounts.
    """
    customer = Customer.objects.select_for_update().get(id=customer_id)
    amount_dec = Decimal(str(amount))
    
    # Decrease customer debt
    customer.balance -= amount_dec
    customer.save()

    # Record ledger transaction
    Transaction.objects.create(
        customer=customer,
        amount=amount_dec,
        transaction_type='pay_received'
    )
    return customer


@transaction.atomic
def send_supplier_payment(supplier_id, amount):
    """
    Record debt settlement payments sent out to suppliers.
    """
    supplier = Supplier.objects.select_for_update().get(id=supplier_id)
    amount_dec = Decimal(str(amount))

    # Decrease supplier balance we owe
    supplier.balance -= amount_dec
    supplier.save()

    # Record ledger transaction
    Transaction.objects.create(
        supplier=supplier,
        amount=amount_dec,
        transaction_type='pay_sent'
    )
    return supplier


def get_profit_and_loss(start_date=None, end_date=None):
    """
    Net Profit = (Gross Sales Revenues + Maintenance Labor Fees) - (Cost of Goods Sold + Operating Expenses)
    Supports filtering by optional start_date and end_date.
    """
    from django.db.models import Sum
    from expenses.models import Expense
    import datetime

    orders_qs = Order.objects.all()
    tickets_qs = MaintenanceTicket.objects.filter(status='delivered')
    expenses_qs = Expense.objects.all()
    tx_qs = Transaction.objects.all()

    if start_date:
        if isinstance(start_date, str):
            try:
                start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
            except ValueError:
                start_date = None
        if start_date:
            orders_qs = orders_qs.filter(created_at__date__gte=start_date)
            tickets_qs = tickets_qs.filter(created_at__date__gte=start_date)
            expenses_qs = expenses_qs.filter(created_at__date__gte=start_date)
            tx_qs = tx_qs.filter(created_at__date__gte=start_date)

    if end_date:
        if isinstance(end_date, str):
            try:
                end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                end_date = None
        if end_date:
            orders_qs = orders_qs.filter(created_at__date__lte=end_date)
            tickets_qs = tickets_qs.filter(created_at__date__lte=end_date)
            expenses_qs = expenses_qs.filter(created_at__date__lte=end_date)
            tx_qs = tx_qs.filter(created_at__date__lte=end_date)

    gross_sales = orders_qs.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')
    cogs = orders_qs.aggregate(Sum('cost_of_goods_sold'))['cost_of_goods_sold__sum'] or Decimal('0.00')
    orders_count = orders_qs.count()

    labor_fees = tickets_qs.aggregate(Sum('labor_fees'))['labor_fees__sum'] or Decimal('0.00')
    maintenance_parts_sell = tickets_qs.aggregate(Sum('parts_sell'))['parts_sell__sum'] or Decimal('0.00')
    maintenance_parts_cost = tickets_qs.aggregate(Sum('parts_cost'))['parts_cost__sum'] or Decimal('0.00')
    tickets_count = tickets_qs.count()

    total_expenses = expenses_qs.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')

    # Cash collections & payments during period
    collected_from_customers = tx_qs.filter(transaction_type='pay_received').aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
    paid_to_suppliers = tx_qs.filter(transaction_type='pay_sent').aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')

    # Total Sales includes POS Sales + Maintenance Parts Sales
    total_revenues = gross_sales + maintenance_parts_sell
    total_cost_goods = cogs + maintenance_parts_cost

    net_profit = (total_revenues + labor_fees) - (total_cost_goods + total_expenses)

    return {
        'gross_sales': gross_sales,
        'cogs': cogs,
        'orders_count': orders_count,
        'labor_fees': labor_fees,
        'parts_sell': maintenance_parts_sell,
        'parts_cost': maintenance_parts_cost,
        'tickets_count': tickets_count,
        'total_expenses': total_expenses,
        'collected_from_customers': collected_from_customers,
        'paid_to_suppliers': paid_to_suppliers,
        'total_revenues': total_revenues,
        'total_costs': total_cost_goods,
        'net_profit': net_profit,
    }


@transaction.atomic
def add_customer_debt(customer_id, amount, notes=''):
    """
    Add a new deferred-credit debt charge to an existing customer account.
    Used when customer takes goods on credit (new shekk entry).
    """
    customer = Customer.objects.select_for_update().get(id=customer_id)
    amount_dec = Decimal(str(amount))
    if amount_dec <= 0:
        raise ValueError("المبلغ يجب أن يكون أكبر من صفر")

    # Increase customer debt balance
    customer.balance += amount_dec
    customer.save()

    # Write full transaction record
    Transaction.objects.create(
        customer=customer,
        amount=amount_dec,
        transaction_type='sale_credit',
        notes=notes or f'إضافة دين يدوي بمبلغ {amount_dec} ج.م'
    )
    return customer


@transaction.atomic
def add_supplier_debt(supplier_id, amount, notes=''):
    """
    Add a new credit-purchase debt to an existing supplier account.
    Used when we receive goods from supplier on deferred payment.
    """
    supplier = Supplier.objects.select_for_update().get(id=supplier_id)
    amount_dec = Decimal(str(amount))
    if amount_dec <= 0:
        raise ValueError("المبلغ يجب أن يكون أكبر من صفر")

    # Increase what we owe to supplier
    supplier.balance += amount_dec
    supplier.save()

    # Write full transaction record
    Transaction.objects.create(
        supplier=supplier,
        amount=amount_dec,
        transaction_type='purchase_credit',
        notes=notes or f'إضافة دين مورد يدوي بمبلغ {amount_dec} ج.م'
    )
    return supplier
