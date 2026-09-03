import json
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login
from django.db import transaction
from django.utils import timezone

from tenants.models import Tenant, TenantUser
from tenants.middleware import set_current_tenant
from inventory.models import Product
from ledger.models import Customer, Supplier
from pos.models import Order, OrderItem
from expenses.models import Expense
from decimal import Decimal


@method_decorator(csrf_exempt, name='dispatch')
class ApiLoginView(View):
    """
    POST /api/v1/login/
    Body: {"username": "...", "password": "...", "tenant_slug": "..."}
    """
    def post(self, request):
        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            return JsonResponse({'success': False, 'error': 'بيانات JSON غير صالحة'}, status=400)

        username = data.get('username')
        password = data.get('password')
        tenant_slug = data.get('tenant_slug')

        if not username or not password:
            return JsonResponse({'success': False, 'error': 'يرجى إدخال اسم المستخدم وكلمة المرور'}, status=400)

        user = authenticate(request, username=username, password=password)
        if not user:
            return JsonResponse({'success': False, 'error': 'اسم المستخدم أو كلمة المرور غير صحيحة'}, status=401)

        # Resolve tenant
        tenant = None
        if tenant_slug:
            tenant = Tenant.objects.filter(slug=tenant_slug, is_active=True).first()
        
        if not tenant:
            membership = TenantUser.objects.filter(user=user).select_related('tenant').first()
            if membership and membership.tenant.is_active:
                tenant = membership.tenant
            else:
                tenant = Tenant.objects.filter(is_active=True).first()

        if not tenant:
            return JsonResponse({'success': False, 'error': 'لم يتم العثور على شركة صالحة لهذا الحساب'}, status=403)

        if tenant.is_subscription_expired:
            return JsonResponse({'success': False, 'error': 'اشتراك الشركة منتهي، يرجى التجديد أولاً'}, status=403)

        return JsonResponse({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
            },
            'tenant': {
                'id': tenant.id,
                'name': tenant.name,
                'slug': tenant.slug,
                'plan': tenant.plan,
            }
        })


@method_decorator(csrf_exempt, name='dispatch')
class ApiProductsView(View):
    """
    GET /api/v1/products/?tenant_slug=mahel
    Returns cached products for mobile app POS catalog
    """
    def get(self, request):
        tenant_slug = request.GET.get('tenant_slug') or (request.tenant.slug if hasattr(request, 'tenant') and request.tenant else None)
        tenant = None
        if tenant_slug:
            tenant = Tenant.objects.filter(slug=tenant_slug, is_active=True).first()

        if tenant:
            set_current_tenant(tenant)
            products_qs = Product.objects.filter(tenant=tenant)
        else:
            products_qs = Product.objects.all()

        data = []
        for p in products_qs:
            data.append({
                'id': p.id,
                'name': p.name,
                'sku': p.sku or '',
                'barcode': p.barcode or '',
                'sale_price': float(p.sale_price or 0.0),
                'cost_price': float(p.purchase_cost or 0.0),
                'stock_quantity': p.stock_quantity or 0,
                'unit': p.unit or 'حبة',
                'category_name': p.category.name if p.category else 'عام',
            })

        return JsonResponse({'success': True, 'count': len(data), 'products': data})


@method_decorator(csrf_exempt, name='dispatch')
class ApiCustomersView(View):
    """
    GET /api/v1/customers/?tenant_slug=mahel
    """
    def get(self, request):
        tenant_slug = request.GET.get('tenant_slug') or (request.tenant.slug if hasattr(request, 'tenant') and request.tenant else None)
        tenant = None
        if tenant_slug:
            tenant = Tenant.objects.filter(slug=tenant_slug, is_active=True).first()

        if tenant:
            set_current_tenant(tenant)
            customers_qs = Customer.objects.filter(tenant=tenant)
        else:
            customers_qs = Customer.objects.all()

        data = []
        for c in customers_qs:
            data.append({
                'id': c.id,
                'name': c.name,
                'phone': c.phone or '',
                'balance': float(c.balance or 0.0),
            })

        return JsonResponse({'success': True, 'count': len(data), 'customers': data})


@method_decorator(csrf_exempt, name='dispatch')
class ApiInvoiceSyncView(View):
    """
    POST /api/v1/invoices/sync/
    Syncs offline invoices created on mobile to server database
    """
    def post(self, request):
        try:
            payload = json.loads(request.body.decode('utf-8'))
        except Exception:
            return JsonResponse({'success': False, 'error': 'بيانات JSON غير صالحة'}, status=400)

        tenant_slug = payload.get('tenant_slug')
        invoices = payload.get('invoices', [])

        tenant = None
        if tenant_slug:
            tenant = Tenant.objects.filter(slug=tenant_slug, is_active=True).first()

        if tenant:
            set_current_tenant(tenant)

        synced_ids = []
        errors = []

        with transaction.atomic():
            for inv in invoices:
                client_id = inv.get('client_id')
                payment_method = inv.get('payment_method', 'cash')
                customer_id = inv.get('customer_id')
                items = inv.get('items', [])

                if not items:
                    continue

                customer = None
                if customer_id:
                    customer = Customer.objects.filter(id=customer_id).first()

                # Calculate total amount & COGS
                total_amount = 0
                total_cost = 0
                order_items_to_create = []

                for item in items:
                    prod_id = item.get('product_id')
                    qty = int(item.get('quantity', 1))
                    unit_price = float(item.get('unit_price', 0.0))

                    prod = None
                    if prod_id:
                        prod = Product.objects.filter(id=prod_id).first()
                    if not prod and item.get('product_sku'):
                        prod = Product.objects.filter(sku=item.get('product_sku')).first()
                    if not prod and item.get('product_name'):
                        prod = Product.objects.filter(name=item.get('product_name')).first()

                    if not prod:
                        continue

                    cost_price = float(getattr(prod, 'purchase_price', 0.0) or 0.0)
                    item_total = unit_price * qty
                    item_cost = cost_price * qty

                    total_amount += item_total
                    total_cost += item_cost

                    # Deduct inventory stock safely
                    prod.stock_quantity = max(0, (prod.stock_quantity or 0) - qty)
                    prod.save(update_fields=['stock_quantity'])

                    order_items_to_create.append({
                        'product': prod,
                        'quantity': qty,
                        'unit_price': unit_price,
                        'cost': cost_price
                    })

                if not order_items_to_create:
                    continue

                order_number = inv.get('order_number') or f"MOB-{int(timezone.now().timestamp())}-{Order.objects.count() + 1}"

                # Prevent duplicate order on re-sync
                existing_order = Order.objects.filter(order_number=order_number).first()
                if existing_order:
                    synced_ids.append(existing_order.id)
                    continue

                order = Order.objects.create(
                    order_number=order_number,
                    customer=customer,
                    payment_method=payment_method,
                    total_amount=total_amount,
                    cost_of_goods_sold=total_cost,
                    tenant=tenant
                )

                for oi in order_items_to_create:
                    OrderItem.objects.create(
                        order=order,
                        product=oi['product'],
                        quantity=oi['quantity'],
                        unit_price=oi['unit_price'],
                        cost=oi['cost']
                    )

                # Update customer balance if deferred
                if payment_method == 'deferred' and customer:
                    customer.balance = (customer.balance or 0) + total_amount
                    customer.save()

                synced_ids.append({
                    'client_id': client_id,
                    'server_order_number': order.order_number,
                    'server_order_id': order.id,
                })

        return JsonResponse({
            'success': True,
            'synced_count': len(synced_ids),
            'synced': synced_ids,
            'errors': errors
        })


@method_decorator(csrf_exempt, name='dispatch')
class ApiDashboardSummaryView(View):
    """
    GET /api/v1/dashboard/?tenant_slug=mahel
    """
    def get(self, request):
        tenant_slug = request.GET.get('tenant_slug')
        tenant = None
        if tenant_slug:
            tenant = Tenant.objects.filter(slug=tenant_slug, is_active=True).first()

        if tenant:
            set_current_tenant(tenant)
            orders_qs = Order.objects.filter(tenant=tenant)
            products_qs = Product.objects.filter(tenant=tenant)
        else:
            orders_qs = Order.objects.all()
            products_qs = Product.objects.all()

        today = timezone.now().date()
        today_orders = orders_qs.filter(created_at__date=today)
        
        today_sales = sum(float(o.total_amount or 0) for o in today_orders)
        today_count = today_orders.count()
        low_stock_count = products_qs.filter(stock_quantity__lte=5).count()

        return JsonResponse({
            'success': True,
            'today_sales': today_sales,
            'today_orders_count': today_count,
            'low_stock_count': low_stock_count,
            'total_products': products_qs.count()
        })


import urllib.request
import urllib.error

@method_decorator(csrf_exempt, name='dispatch')
class ApiFullSyncView(View):
    """
    POST /api/v1/sync/full/
    Comprehensive Two-Way Sync Endpoint for Products, Customers, Suppliers, Invoices & Expenses
    """
    def post(self, request):
        try:
            payload = json.loads(request.body.decode('utf-8'))
        except Exception:
            return JsonResponse({'success': False, 'error': 'بيانات JSON غير صالحة'}, status=400)

        tenant_slug = payload.get('tenant_slug')
        tenant = None
        if tenant_slug:
            tenant = Tenant.objects.filter(slug=tenant_slug, is_active=True).first()
        if tenant:
            set_current_tenant(tenant)

        customers_data = payload.get('customers', [])
        suppliers_data = payload.get('suppliers', [])
        products_data = payload.get('products', [])
        invoices_data = payload.get('invoices', [])
        expenses_data = payload.get('expenses', [])

        synced_customers = 0
        synced_suppliers = 0
        synced_products = 0
        synced_invoices = 0
        synced_expenses = 0

        with transaction.atomic():
            # 1. Sync Customers
            for c in customers_data:
                phone = (c.get('phone') or '').strip() or None
                name = (c.get('name') or '').strip()
                if not name:
                    continue
                cust = None
                if phone:
                    cust = Customer.objects.filter(phone=phone).first()
                if not cust:
                    cust = Customer.objects.filter(name=name).first()
                
                if cust:
                    if c.get('workplace'): cust.workplace = c.get('workplace')
                    if c.get('address'): cust.address = c.get('address')
                    if 'balance' in c:
                        try: cust.balance = max(cust.balance or 0, Decimal(str(c['balance'])))
                        except: pass
                    cust.save()
                else:
                    try: init_bal = Decimal(str(c.get('balance', 0)))
                    except: init_bal = Decimal('0.00')
                    Customer.objects.create(
                        name=name,
                        phone=phone,
                        workplace=c.get('workplace') or '',
                        address=c.get('address') or '',
                        notes=c.get('notes') or '',
                        balance=init_bal,
                        tenant=tenant
                    )
                synced_customers += 1

            # 2. Sync Suppliers
            for s in suppliers_data:
                name = (s.get('name') or '').strip()
                phone = (s.get('phone') or '').strip() or None
                if not name:
                    continue
                sup = None
                if phone:
                    sup = Supplier.objects.filter(phone=phone).first()
                if not sup:
                    sup = Supplier.objects.filter(name=name).first()
                if not sup:
                    try: init_bal = Decimal(str(s.get('balance', 0)))
                    except: init_bal = Decimal('0.00')
                    Supplier.objects.create(
                        name=name,
                        company=s.get('company') or s.get('company_name') or '',
                        phone=phone,
                        address=s.get('address') or '',
                        notes=s.get('notes') or '',
                        balance=init_bal,
                        tenant=tenant
                    )
                synced_suppliers += 1

            # 3. Sync Products
            for p in products_data:
                sku = (p.get('sku') or '').strip()
                name = (p.get('name') or '').strip()
                if not name and not sku:
                    continue
                prod = None
                if sku:
                    prod = Product.objects.filter(sku=sku).first()
                if not prod and name:
                    prod = Product.objects.filter(name=name).first()

                cat = p.get('category') or 'عام / متنوع'
                p_price = Decimal(str(p.get('purchase_price', 0.0)))
                s_price = Decimal(str(p.get('selling_price', 0.0)))
                stock = int(p.get('stock_quantity', 0))

                if prod:
                    prod.selling_price = s_price
                    prod.purchase_price = p_price
                    prod.category = cat
                    if 'stock_quantity' in p:
                        prod.stock_quantity = stock
                    prod.save()
                else:
                    Product.objects.create(
                        name=name,
                        sku=sku or f"SKU-{Product.objects.count() + 1}",
                        barcode=p.get('barcode') or None,
                        category=cat,
                        purchase_price=p_price,
                        selling_price=s_price,
                        stock_quantity=stock,
                        min_stock_threshold=int(p.get('min_stock_threshold', 5)),
                        tenant=tenant
                    )
                synced_products += 1

            # 4. Sync Invoices
            for inv in invoices_data:
                order_num = inv.get('order_number')
                if not order_num:
                    continue
                if Order.objects.filter(order_number=order_num).exists():
                    continue

                items = inv.get('items', [])
                if not items:
                    continue

                customer = None
                cust_phone = inv.get('customer_phone')
                cust_name = inv.get('customer_name')
                if cust_phone:
                    customer = Customer.objects.filter(phone=cust_phone).first()
                if not customer and cust_name:
                    customer = Customer.objects.filter(name=cust_name).first()
                if not customer and inv.get('customer_id'):
                    customer = Customer.objects.filter(id=inv.get('customer_id')).first()

                total_amount = Decimal('0.00')
                total_cost = Decimal('0.00')
                items_to_create = []

                for item in items:
                    prod_id = item.get('product_id')
                    prod_sku = item.get('product_sku')
                    prod_name = item.get('product_name')
                    qty = int(item.get('quantity', 1))
                    unit_price = Decimal(str(item.get('unit_price', 0.0)))

                    prod = None
                    if prod_id:
                        prod = Product.objects.filter(id=prod_id).first()
                    if not prod and prod_sku:
                        prod = Product.objects.filter(sku=prod_sku).first()
                    if not prod and prod_name:
                        prod = Product.objects.filter(name=prod_name).first()

                    if not prod:
                        continue

                    cost_price = Decimal(str(getattr(prod, 'purchase_price', 0.0) or 0.0))
                    total_amount += unit_price * qty
                    total_cost += cost_price * qty

                    prod.stock_quantity = max(0, (prod.stock_quantity or 0) - qty)
                    prod.save(update_fields=['stock_quantity'])

                    items_to_create.append({
                        'product': prod,
                        'quantity': qty,
                        'unit_price': unit_price,
                        'cost': cost_price
                    })

                if not items_to_create:
                    continue

                order = Order.objects.create(
                    order_number=order_num,
                    customer=customer,
                    payment_method=inv.get('payment_method', 'cash'),
                    total_amount=total_amount,
                    cost_of_goods_sold=total_cost,
                    tenant=tenant
                )

                for it in items_to_create:
                    OrderItem.objects.create(
                        order=order,
                        product=it['product'],
                        quantity=it['quantity'],
                        unit_price=it['unit_price'],
                        cost=it['cost']
                    )

                if inv.get('payment_method') == 'deferred' and customer:
                    customer.balance = (customer.balance or 0) + total_amount
                    customer.save(update_fields=['balance'])

                synced_invoices += 1

            # 5. Sync Expenses
            for exp in expenses_data:
                desc = (exp.get('description') or '').strip()
                amt = Decimal(str(exp.get('amount', 0)))
                cat = exp.get('category') or 'other'
                if not desc or amt <= 0:
                    continue
                if not Expense.objects.filter(description=desc, amount=amt).exists():
                    Expense.objects.create(
                        category=cat,
                        description=desc,
                        amount=amt,
                        tenant=tenant
                    )
                    synced_expenses += 1

        return JsonResponse({
            'success': True,
            'message': 'تمت المزامنة الشاملة لكافة البيانات بنجاح!',
            'stats': {
                'products': synced_products,
                'customers': synced_customers,
                'suppliers': synced_suppliers,
                'invoices': synced_invoices,
                'expenses': synced_expenses
            }
        })


@method_decorator(csrf_exempt, name='dispatch')
class DesktopSyncAllToCloudView(View):
    """
    POST /api/v1/desktop/sync-all/
    Triggered from Desktop to send ALL local products, customers, suppliers, invoices, and expenses to cloud
    """
    def post(self, request):
        try:
            cloud_url = "https://webservises.pythonanywhere.com/api/v1/sync/full/"

            # 1. Package Products
            products_list = []
            for p in Product.objects.all():
                products_list.append({
                    'name': p.name,
                    'sku': p.sku,
                    'barcode': p.barcode or '',
                    'category': p.category or 'عام / متنوع',
                    'purchase_price': float(p.purchase_price or 0),
                    'selling_price': float(p.selling_price or 0),
                    'stock_quantity': p.stock_quantity,
                    'min_stock_threshold': p.min_stock_threshold
                })

            # 2. Package Customers
            customers_list = []
            for c in Customer.objects.all():
                customers_list.append({
                    'name': c.name,
                    'phone': c.phone or '',
                    'workplace': c.workplace or '',
                    'address': c.address or '',
                    'balance': float(c.balance or 0),
                    'notes': c.notes or ''
                })

            # 3. Package Suppliers
            suppliers_list = []
            for s in Supplier.objects.all():
                suppliers_list.append({
                    'name': s.name,
                    'company': getattr(s, 'company', '') or '',
                    'phone': s.phone or '',
                    'address': s.address or '',
                    'balance': float(s.balance or 0),
                    'notes': s.notes or ''
                })

            # 4. Package Invoices
            invoices_list = []
            for o in Order.objects.all().prefetch_related('items__product', 'customer'):
                items_data = []
                for it in o.items.all():
                    items_data.append({
                        'product_id': it.product_id,
                        'product_name': it.product.name if it.product else '',
                        'product_sku': it.product.sku if it.product else '',
                        'quantity': it.quantity,
                        'unit_price': float(it.unit_price)
                    })
                if items_data:
                    invoices_list.append({
                        'order_number': o.order_number,
                        'payment_method': o.payment_method,
                        'customer_id': o.customer_id,
                        'customer_phone': o.customer.phone if o.customer else '',
                        'customer_name': o.customer.name if o.customer else '',
                        'items': items_data
                    })

            # 5. Package Expenses
            expenses_list = []
            for e in Expense.objects.all():
                expenses_list.append({
                    'category': e.category,
                    'description': e.description,
                    'amount': float(e.amount)
                })

            payload = {
                'tenant_slug': 'mahel',
                'products': products_list,
                'customers': customers_list,
                'suppliers': suppliers_list,
                'invoices': invoices_list,
                'expenses': expenses_list
            }

            req_body = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                cloud_url,
                data=req_body,
                headers={'Content-Type': 'application/json', 'User-Agent': 'AlNamaa-Desktop-Universal-Sync/1.0'}
            )

            with urllib.request.urlopen(req, timeout=30) as response:
                raw_data = response.read().decode('utf-8')
                try:
                    res_data = json.loads(raw_data)
                    return JsonResponse(res_data)
                except Exception:
                    return JsonResponse({
                        'success': False,
                        'error': 'استجاب السيرفر السحابي بصفحة غير مهيأة. يرجى سحب التحديث (git pull) وعمل Reload في بايثون إني وير.'
                    }, status=400)

        except urllib.error.URLError as e:
            return JsonResponse({'success': False, 'error': f'تعذر الاتصال بالسيرفر السحابي (يرجى التأكد من تشغيل الإنترنت): {str(e.reason)}'}, status=503)
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'خطأ أثناء المزامنة الشاملة: {str(e)}'}, status=500)
