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
from ledger.models import Customer
from pos.models import Order, OrderItem


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

                    prod = Product.objects.filter(id=prod_id).first()
                    if not prod:
                        continue

                    cost_price = float(prod.purchase_cost or 0.0)
                    item_total = unit_price * qty
                    item_cost = cost_price * qty

                    total_amount += item_total
                    total_cost += item_cost

                    # Deduct inventory stock
                    prod.stock_quantity = max(0, (prod.stock_quantity or 0) - qty)
                    prod.save()

                    order_items_to_create.append({
                        'product': prod,
                        'quantity': qty,
                        'unit_price': unit_price,
                        'cost': cost_price
                    })

                if not order_items_to_create:
                    continue

                order_number = f"MOB-{int(timezone.now().timestamp())}-{Order.objects.count() + 1}"
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
