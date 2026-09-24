import json
import uuid
from django.shortcuts import redirect, get_object_or_404, render
from django.views.generic import ListView, CreateView, UpdateView, DetailView, View, TemplateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from decimal import Decimal, ROUND_HALF_UP
from django.db.models import F
from django.db import transaction
from .models import Product, StockAlert, PurchaseOrder, PurchaseOrderItem, Category
from ledger.models import Supplier, Transaction


def get_tenant_categories(tenant):
    """جلب فئات المنتجات للشركة وإعادة إنشاء فئات افتراضية أولية إذا كانت فارغة."""
    categories = Category.all_objects.filter(tenant=tenant).order_by('name')
    if not categories.exists():
        default_names = ['أسمدة ومخصبات زراعية', 'مبيدات حشرية وفطرية', 'قطع غيار مواقير ورش', 'معدات وآلات زراعية', 'زيوت وشحومات', 'عام / متنوع']
        for dname in default_names:
            Category.all_objects.create(name=dname, tenant=tenant)
        categories = Category.all_objects.filter(tenant=tenant).order_by('name')
    return categories


class InventoryListView(ListView):
    model = Product
    template_name = "inventory.html"
    context_object_name = "products"

    def get_queryset(self):
        return Product.objects.select_related('default_supplier').only(
            'id', 'name', 'sku', 'barcode', 'category', 'image',
            'purchase_price', 'selling_price', 'stock_quantity', 'min_stock_threshold',
            'default_supplier__name'
        ).order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Dynamic stock alerts limited to top critical items
        low_stock_products = list(Product.objects.filter(
            stock_quantity__lte=F('min_stock_threshold')
        ).only('id', 'name', 'stock_quantity', 'min_stock_threshold').order_by('stock_quantity', 'name')[:30])
        
        tenant = getattr(self.request, 'tenant', None)
        context['categories'] = get_tenant_categories(tenant) if tenant else Category.objects.all()
        context['low_stock_products'] = low_stock_products
        context['critical_stock_count'] = Product.objects.filter(stock_quantity__lte=F('min_stock_threshold')).count()
        context['category_choices'] = Product.CATEGORY_CHOICES
        return context


class ProductCreateView(CreateView):
    model = Product
    fields = ['name', 'sku', 'barcode', 'category', 'image', 'purchase_price', 'selling_price', 'stock_quantity', 'min_stock_threshold']
    template_name = "inventory.html"
    success_url = reverse_lazy('inventory:inventory_list')

    def form_valid(self, form):
        if form.cleaned_data.get('barcode') == '':
            form.instance.barcode = None
        response = super().form_valid(form)
        from dashboard.audit import log_activity
        log_activity(
            self.request,
            module='inventory',
            action_type='create',
            description=f"إضافة منتج جديد: '{form.instance.name}' (SKU: {form.instance.sku}) بسعر بيع {form.instance.selling_price} ج.م ومخزون {form.instance.stock_quantity} قطعة",
            severity='info'
        )
        messages.success(self.request, f"تمت إضافة المنتج '{form.instance.name}' بنجاح إلى المخزن!")
        return response

    def form_invalid(self, form):
        error_msg = "; ".join([f"{', '.join(errs)}" for field, errs in form.errors.items()])
        messages.error(self.request, f"خطأ أثناء إضافة المنتج: {error_msg}")
        return redirect('inventory:inventory_list')


class ProductUpdateView(UpdateView):
    model = Product
    fields = ['name', 'sku', 'barcode', 'category', 'image', 'purchase_price', 'selling_price', 'stock_quantity', 'min_stock_threshold']
    template_name = "inventory.html"
    success_url = reverse_lazy('inventory:inventory_list')

    def form_valid(self, form):
        if form.cleaned_data.get('barcode') == '':
            form.instance.barcode = None
        response = super().form_valid(form)
        from dashboard.audit import log_activity
        log_activity(
            self.request,
            module='inventory',
            action_type='update',
            description=f"تعديل بيانات المنتج: '{form.instance.name}' (سعر الشراء: {form.instance.purchase_price} | سعر البيع: {form.instance.selling_price} | المخزون: {form.instance.stock_quantity})",
            severity='warning'
        )
        messages.success(self.request, f"تم تحديث بيانات المنتج '{form.instance.name}' بنجاح!")
        return response

    def form_invalid(self, form):
        error_msg = "; ".join([f"{', '.join(errs)}" for field, errs in form.errors.items()])
        messages.error(self.request, f"خطأ أثناء تعديل المنتج: {error_msg}")
        return redirect('inventory:inventory_list')


class ProductDeleteView(View):
    def post(self, request, pk, *args, **kwargs):
        product = get_object_or_404(Product, pk=pk)
        name = product.name
        try:
            product.delete()
            from dashboard.audit import log_activity
            log_activity(
                request,
                module='inventory',
                action_type='delete',
                description=f"حذف المنتج: '{name}' من المخزن بالكامل",
                severity='danger'
            )
            messages.success(request, f"تم حذف المنتج '{name}' من المخزن بنجاح.")
        except Exception:
            messages.error(request, f"لا يمكن حذف المنتج '{name}' لأنه مرتبط بفواتير أو عمليات صيانة مسجلة.")
        return redirect('inventory:inventory_list')


class QuickRestockView(View):
    """
    Quickly add stock quantity to a product directly from Stock Alerts or table.
    """
    def post(self, request, pk, *args, **kwargs):
        product = get_object_or_404(Product, pk=pk)
        added_qty_str = request.POST.get('added_quantity', '0').strip()

        try:
            added_qty = int(added_qty_str)
            if added_qty <= 0:
                messages.error(request, "يرجى إدخال كمية صحيحة أكبر من صفر.")
                return redirect('inventory:inventory_list')
        except ValueError:
            messages.error(request, "كمية غير صحيحة.")
            return redirect('inventory:inventory_list')

        product.stock_quantity += added_qty
        product.save()

        # Mark alerts resolved for this product if any
        StockAlert.objects.filter(product=product, is_resolved=False).update(is_resolved=True)

        from dashboard.audit import log_activity
        log_activity(
            request,
            module='inventory',
            action_type='stock_change',
            description=f"تزويد رصيد سريع للمنتج: '{product.name}' بمقدار (+{added_qty} قطع) - الرصيد الحالي: {product.stock_quantity}",
            severity='info'
        )

        messages.success(
            request, 
            f"📦 تم تزويد مخزون '{product.name}' بـ (+{added_qty} قطع) بنجاح! الرصيد الحالي المتوفر الآن: {product.stock_quantity} قطعة."
        )
        return redirect('inventory:inventory_list')


class BulkPriceAdjustmentView(View):
    """
    POST view to adjust prices by a percentage rate (e.g. +5%, +10%, +15%, -5%).
    """
    def post(self, request, *args, **kwargs):
        percentage_str = request.POST.get('percentage', '0').strip()
        price_target = request.POST.get('price_target', 'selling')
        scope = request.POST.get('scope', 'all')
        category = request.POST.get('category', '')
        selected_ids = request.POST.getlist('selected_products')

        try:
            pct = Decimal(percentage_str)
        except Exception:
            messages.error(request, "يرجى إدخال نسبة مئوية صحيحة (مثال: 5 أو 10 أو 12.5).")
            return redirect('inventory:inventory_list')

        if pct == 0:
            messages.warning(request, "النسبة المئوية 0% — لم يتم تغيير أي أسعار.")
            return redirect('inventory:inventory_list')

        queryset = Product.objects.all()
        if scope == 'selected':
            if not selected_ids:
                messages.error(request, "لم تقم بتحديد أي منتجات لتطبيق الزيادة عليها. علم على المنتجات المطلوبة أولاً.")
                return redirect('inventory:inventory_list')
            queryset = queryset.filter(id__in=selected_ids)
        elif scope == 'category' and category:
            queryset = queryset.filter(category=category)

        multiplier = Decimal('1.00') + (pct / Decimal('100.00'))

        updated_count = 0
        for product in queryset:
            if price_target in ['selling', 'both']:
                new_sell = (product.selling_price * multiplier).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                product.selling_price = max(Decimal('0.00'), new_sell)
            if price_target in ['purchase', 'both']:
                new_buy = (product.purchase_price * multiplier).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                product.purchase_price = max(Decimal('0.00'), new_buy)
            product.save()
            updated_count += 1

        sign = "+" if pct > 0 else ""
        target_desc = "سعر البيع" if price_target == 'selling' else ("سعر الشراء" if price_target == 'purchase' else "سعر البيع والشراء")
        from dashboard.audit import log_activity
        log_activity(
            request,
            module='inventory',
            action_type='price_change',
            description=f"تعديل أسعار جماعي ({target_desc}) بنسبة ({sign}{pct}%) على {updated_count} منتج في المخزن",
            severity='danger'
        )
        messages.success(
            request,
            f"🚀 تم تحديث {target_desc} لـ {updated_count} منتج بنسبة ({sign}{pct}%) بنجاح!"
        )
        return redirect('inventory:inventory_list')


class SingleProductPriceAdjustmentView(View):
    """
    Quick percentage adjustment for a single specific product.
    """
    def post(self, request, pk, *args, **kwargs):
        product = get_object_or_404(Product, pk=pk)
        percentage_str = request.POST.get('percentage', '0').strip()
        price_target = request.POST.get('price_target', 'selling')

        try:
            pct = Decimal(percentage_str)
        except Exception:
            messages.error(request, "يرجى إدخال نسبة صحيحة.")
            return redirect('inventory:inventory_list')

        multiplier = Decimal('1.00') + (pct / Decimal('100.00'))

        if price_target in ['selling', 'both']:
            product.selling_price = max(Decimal('0.00'), (product.selling_price * multiplier).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        if price_target in ['purchase', 'both']:
            product.purchase_price = max(Decimal('0.00'), (product.purchase_price * multiplier).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        
        product.save()
        sign = "+" if pct > 0 else ""
        from dashboard.audit import log_activity
        log_activity(
            request,
            module='inventory',
            action_type='price_change',
            description=f"تعديل سعر المنتج: '{product.name}' بنسبة ({sign}{pct}%) — سعر البيع الجديد: {product.selling_price} ج.م",
            severity='warning'
        )
        messages.success(request, f"تم تعديل سعر المنتج '{product.name}' بنسبة ({sign}{pct}%) — سعر البيع الجديد: {product.selling_price} ج.م")
        return redirect('inventory:inventory_list')


class PurchaseOrderListView(ListView):
    model = PurchaseOrder
    template_name = "purchase_order_list.html"
    context_object_name = "orders"

    def get_queryset(self):
        qs = super().get_queryset().select_related('supplier').prefetch_related('items', 'items__product', 'items__supplier')
        status_filter = self.request.GET.get('status')
        supplier_filter = self.request.GET.get('supplier_id')
        if status_filter:
            qs = qs.filter(status=status_filter)
        if supplier_filter and str(supplier_filter).isdigit():
            qs = qs.filter(supplier_id=int(supplier_filter))
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['suppliers'] = Supplier.objects.all()
        context['draft_count'] = PurchaseOrder.objects.filter(status='draft').count()
        context['sent_count'] = PurchaseOrder.objects.filter(status='sent').count()
        context['received_count'] = PurchaseOrder.objects.filter(status='received').count()
        context['critical_stock_count'] = Product.objects.filter(stock_quantity__lte=F('min_stock_threshold')).count()
        context['low_stock_products'] = Product.objects.filter(
            stock_quantity__lte=F('min_stock_threshold')
        ).select_related('default_supplier').order_by('stock_quantity', 'name')
        return context


class QuickUpdateMinStockView(View):
    """تحديث الحد الأدنى للتنبيه لمنتج معين فورياً وبسرعة من شاشة النواقص"""
    def post(self, request, *args, **kwargs):
        product_id = request.POST.get('product_id')
        new_min = request.POST.get('min_stock_threshold')
        try:
            prod = get_object_or_404(Product, id=product_id)
            if new_min is not None and str(new_min).strip().isdigit():
                prod.min_stock_threshold = max(0, int(new_min))
                prod.save(update_fields=['min_stock_threshold'])
                msg = f'✅ تم تحديث الحد الأدنى لمنتج "{prod.name}" إلى {prod.min_stock_threshold} بنجاح.'
            else:
                raise ValueError("قيمة الحد الأدنى غير صحيحة")

            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'min_stock_threshold': prod.min_stock_threshold, 'message': msg})
            messages.success(request, msg)
        except Exception as e:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': str(e)}, status=400)
            messages.error(request, f'خطأ أثناء تحديث الحد الأدنى: {str(e)}')

        return redirect(request.META.get('HTTP_REFERER', 'inventory:purchase_order_list'))


class PurchaseOrderBuilderView(View):
    def get(self, request, pk=None, *args, **kwargs):
        order = None
        if pk:
            order = get_object_or_404(PurchaseOrder, pk=pk)

        all_products = Product.objects.all().select_related('default_supplier')
        low_stock_products = Product.objects.filter(
            stock_quantity__lte=F('min_stock_threshold')
        ).select_related('default_supplier').order_by('stock_quantity', 'name')
        suppliers = Supplier.objects.all()
        initial_supplier_id = request.GET.get('supplier_id', '')

        context = {
            'order': order,
            'all_products': all_products,
            'low_stock_products': low_stock_products,
            'suppliers': suppliers,
            'initial_supplier_id': initial_supplier_id,
        }
        return render(request, "purchase_order_builder.html", context)

    def post(self, request, pk=None, *args, **kwargs):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'بيانات غير صحيحة'}, status=400)

        supplier_id = data.get('supplier_id') or None
        notes = data.get('notes', '')
        status = data.get('status', 'draft')
        items_data = data.get('items', [])

        if not items_data:
            return JsonResponse({'success': False, 'error': 'يرجى إضافة صنف واحد على الأقل للطلبية'}, status=400)

        try:
            with transaction.atomic():
                if pk:
                    order = get_object_or_404(PurchaseOrder, pk=pk)
                    order.supplier_id = supplier_id
                    order.notes = notes
                    order.status = status
                    order.save()
                    order.items.all().delete()
                else:
                    today_str = timezone.now().strftime('%Y%m%d')
                    random_suffix = str(uuid.uuid4().hex[:4]).upper()
                    order_number = f"PO-{today_str}-{random_suffix}"
                    order = PurchaseOrder.objects.create(
                        order_number=order_number,
                        supplier_id=supplier_id,
                        notes=notes,
                        status=status,
                    )

                item_supplier_ids = set()
                for item in items_data:
                    product_id = item.get('product_id')
                    custom_name = str(item.get('custom_name', '') or '').strip()
                    item_supplier_id = item.get('supplier_id') or supplier_id or None
                    if item_supplier_id:
                        try:
                            item_supplier_ids.add(int(item_supplier_id))
                        except (ValueError, TypeError):
                            pass

                    quantity = int(item.get('quantity', 1))
                    unit_cost = Decimal(str(item.get('unit_cost', 0)))

                    prod_obj = Product.objects.filter(id=product_id).first() if product_id else None

                    # Fallback to product default supplier if no supplier specified
                    if not item_supplier_id and prod_obj and prod_obj.default_supplier_id:
                        item_supplier_id = prod_obj.default_supplier_id
                        item_supplier_ids.add(prod_obj.default_supplier_id)

                    PurchaseOrderItem.objects.create(
                        purchase_order=order,
                        product=prod_obj,
                        custom_item_name=custom_name or (prod_obj.name if prod_obj else "صنف مخصص"),
                        supplier_id=item_supplier_id if item_supplier_id else None,
                        quantity_requested=max(1, quantity),
                        unit_cost=max(Decimal('0.00'), unit_cost)
                    )

                # Auto-assign order.supplier if all items belong to a single supplier and order.supplier was empty
                if not order.supplier_id and len(item_supplier_ids) == 1:
                    order.supplier_id = list(item_supplier_ids)[0]
                    order.save(update_fields=['supplier_id'])

                if status == 'received' and not order.received_at:
                    for item in order.items.all():
                        if item.product and not item.is_received:
                            item.product.stock_quantity += item.quantity_requested
                            item.product.save()
                            StockAlert.objects.filter(product=item.product, is_resolved=False).update(is_resolved=True)
                            item.is_received = True
                            item.save()
                    order.received_at = timezone.now()
                    order.save()

                    # Record financial transaction (Cash Drawer deduction or Supplier Debt)
                    payment_method = data.get('payment_method', 'cash')
                    total_cost = order.total_estimated_cost
                    if total_cost > 0:
                        supplier = order.supplier
                        if not supplier and len(item_supplier_ids) == 1:
                            supplier = Supplier.objects.filter(id=list(item_supplier_ids)[0]).first()
                            if supplier:
                                order.supplier = supplier
                                order.save(update_fields=['supplier'])

                        if payment_method == 'cash':
                            Transaction.objects.create(
                                supplier=supplier,
                                amount=total_cost,
                                transaction_type='pay_sent',
                                notes=f'سداد نقدي فوري لشراء بضاعة طلبية {order.order_number}' + (f' ({supplier.name})' if supplier else '')
                            )
                        else:
                            if supplier:
                                supplier.balance += total_cost
                                supplier.save()
                                Transaction.objects.create(
                                    supplier=supplier,
                                    amount=total_cost,
                                    transaction_type='purchase_credit',
                                    notes=f'بضاعة مستلمة آجل — طلبية {order.order_number}'
                                )

            from dashboard.audit import log_activity
            supp_name = order.supplier.name if order.supplier else f"{len(item_supplier_ids)} شركات"
            log_activity(
                request,
                module='purchase_orders',
                action_type='create',
                description=f"إنشاء / حفظ طلب بضاعة للموردين #{order.order_number} ({supp_name}) - إجمالي التكلفة التقديرية: {order.total_estimated_cost:,.2f} ج.م",
                severity='info'
            )

            return JsonResponse({
                'success': True,
                'order_id': order.id,
                'order_number': order.order_number,
                'redirect_url': str(reverse_lazy('inventory:purchase_order_detail', kwargs={'pk': order.id}))
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'حدث خطأ: {str(e)}'}, status=400)


class PurchaseOrderDetailView(DetailView):
    model = PurchaseOrder
    template_name = "purchase_order_detail.html"
    context_object_name = "order"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order = self.object
        items = order.items.select_related('product', 'supplier', 'product__default_supplier').all()

        grouped_by_supplier = {}
        for item in items:
            supp_name = item.display_supplier_name
            supp_phone = ""
            if item.supplier and item.supplier.phone:
                supp_phone = item.supplier.phone
            elif item.product and item.product.default_supplier and item.product.default_supplier.phone:
                supp_phone = item.product.default_supplier.phone
            elif order.supplier and order.supplier.phone:
                supp_phone = order.supplier.phone

            if supp_name not in grouped_by_supplier:
                grouped_by_supplier[supp_name] = {
                    'supplier_name': supp_name,
                    'phone': supp_phone,
                    'items': [],
                    'total_cost': Decimal('0.00'),
                }
            grouped_by_supplier[supp_name]['items'].append(item)
            grouped_by_supplier[supp_name]['total_cost'] += item.total_cost

        context['grouped_items'] = grouped_by_supplier
        return context


class PurchaseOrderReceiveView(View):
    def post(self, request, pk, *args, **kwargs):
        from ledger.models import Transaction
        from decimal import Decimal

        order = get_object_or_404(PurchaseOrder, pk=pk)

        if order.status == 'received':
            messages.warning(request, f"الطلبية رقم {order.order_number} تم استلامها وإضافتها للمخزن سابقاً!")
            return redirect('inventory:purchase_order_detail', pk=order.id)

        payment_method = request.POST.get('payment_method', 'deferred')  # 'cash' or 'deferred'
        try:
            actual_amount = Decimal(str(request.POST.get('actual_amount', '0') or '0'))
        except Exception:
            actual_amount = Decimal('0.00')

        with transaction.atomic():
            # 1. Update stock quantities
            updated_count = 0
            for item in order.items.all():
                if item.product and not item.is_received:
                    item.product.stock_quantity += item.quantity_requested
                    item.product.save()
                    StockAlert.objects.filter(product=item.product, is_resolved=False).update(is_resolved=True)
                    item.is_received = True
                    item.save()
                    updated_count += 1

            # 2. Mark order received
            order.status = 'received'
            order.received_at = timezone.now()
            order.save()

            # 3. Record financial transaction if amount > 0
            if actual_amount > 0:
                supplier = order.supplier
                if not supplier:
                    item_suppliers = set(order.items.values_list('supplier_id', flat=True))
                    item_suppliers.discard(None)
                    if len(item_suppliers) == 1:
                        supplier = Supplier.objects.filter(id=list(item_suppliers)[0]).first()
                        if supplier:
                            order.supplier = supplier
                            order.save(update_fields=['supplier'])

                if payment_method == 'cash':
                    # Cash payment from drawer: record as pay_sent (deducts from cash drawer / increases cash_out on dashboard)
                    Transaction.objects.create(
                        supplier=supplier,
                        amount=actual_amount,
                        transaction_type='pay_sent',
                        notes=f'سداد نقدي فوري عند استلام طلبية {order.order_number}' + (f' ({supplier.name})' if supplier else '')
                    )
                    supp_text = f" للمورد '{supplier.name}'" if supplier else ""
                    messages.success(
                        request,
                        f"تم استلام شحنة الطلبية ({order.order_number}) بنجاح وتسجيل سداد نقدي {actual_amount} ج.م{supp_text} وخصمها من النقدية بالدرج!"
                    )
                else:
                    # Deferred: add to supplier balance (shows in supplier liabilities on dashboard)
                    if supplier:
                        supplier.balance += actual_amount
                        supplier.save()
                        Transaction.objects.create(
                            supplier=supplier,
                            amount=actual_amount,
                            transaction_type='purchase_credit',
                            notes=f'بضاعة مستلمة آجل — طلبية {order.order_number}'
                        )
                        messages.success(
                            request,
                            f"تم استلام شحنة الطلبية ({order.order_number}) وتسجيل {actual_amount} ج.م على حساب المورد '{supplier.name}' آجل!"
                        )
                    else:
                        messages.success(
                            request,
                            f"تم استلام شحنة الطلبية ({order.order_number}) بنجاح بمبلغ {actual_amount} ج.م!"
                        )
            else:
                messages.success(
                    request,
                    f"تم استلام شحنة الطلبية ({order.order_number}) بنجاح! تم تزويد رصيد المخزون لـ ({updated_count}) صنف."
                )

            from dashboard.audit import log_activity
            log_activity(
                request,
                module='purchase_orders',
                action_type='receive_order',
                description=f"استلام شحنة طلب البضاعة #{order.order_number} بالمخزن وتزويد رصيد ({updated_count}) صنف (القيمة: {actual_amount:,.2f} ج.م - {payment_method})",
                severity='info'
            )

        return redirect('inventory:purchase_order_detail', pk=order.id)


class PurchaseOrderDeleteView(View):
    def post(self, request, pk, *args, **kwargs):
        order = get_object_or_404(PurchaseOrder, pk=pk)
        num = order.order_number
        order.delete()
        from dashboard.audit import log_activity
        log_activity(
            request,
            module='purchase_orders',
            action_type='delete',
            description=f"حذف طلب البضاعة #{num} من قائمة الطلبات",
            severity='danger'
        )
        messages.success(request, f"تم حذف طلب البضاعة '{num}' بنجاح.")
        return redirect('inventory:purchase_order_list')


class AddSupplierAjaxView(View):
    """
    إضافة شركة / مورد جديد فورياً عبر AJAX من شاشة بناء وتعديل طلبات البضاعة
    """
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            name = data.get('name', '').strip()
            company = data.get('company', '').strip()
            phone = data.get('phone', '').strip()
            address = data.get('address', '').strip()
            notes = data.get('notes', '').strip()

            if not name:
                return JsonResponse({'success': False, 'error': 'اسم المورد أو الشركة مطلوب ولا يمكن تركه فارغاً'}, status=400)

            tenant = getattr(request, 'tenant', None)
            supplier = Supplier.objects.create(
                name=name,
                company=company or None,
                phone=phone or None,
                address=address or None,
                notes=notes or None,
                tenant=tenant
            )

            return JsonResponse({
                'success': True,
                'supplier': {
                    'id': supplier.id,
                    'name': supplier.name,
                    'company': supplier.company or '',
                    'phone': supplier.phone or '',
                }
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': f"خطأ أثناء إضافة المورد: {str(e)}"}, status=400)


class PublicPurchaseOrderDetailView(DetailView):
    """
    صفحة عرض عامة ورسمية لأمر التوريد / طلب البضاعة مجهزة للطباعة كـ PDF ومشاركتها مع الموردين
    """
    model = PurchaseOrder
    template_name = "public_purchase_order.html"
    context_object_name = "order"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order = self.object
        items = order.items.select_related('product', 'supplier', 'product__default_supplier').all()

        grouped_by_supplier = {}
        for item in items:
            supp_name = item.display_supplier_name
            supp_phone = ""
            if item.supplier and item.supplier.phone:
                supp_phone = item.supplier.phone
            elif item.product and item.product.default_supplier and item.product.default_supplier.phone:
                supp_phone = item.product.default_supplier.phone
            elif order.supplier and order.supplier.phone:
                supp_phone = order.supplier.phone

            if supp_name not in grouped_by_supplier:
                grouped_by_supplier[supp_name] = {
                    'supplier_name': supp_name,
                    'phone': supp_phone,
                    'items': [],
                    'total_cost': Decimal('0.00'),
                }
            grouped_by_supplier[supp_name]['items'].append(item)
            grouped_by_supplier[supp_name]['total_cost'] += item.total_cost

        context['grouped_items'] = grouped_by_supplier
        return context


class ExportProductsExcelView(View):
    """تصدير جميع منتجات المخزن إلى ملف Excel (.xlsx) مع دعم CSV الاحتياطي"""
    def get(self, request, *args, **kwargs):
        from django.http import HttpResponse
        products = Product.objects.all().order_by('name')

        try:
            import openpyxl
            from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "منتجات المخزن"
            ws.views.sheetView[0].rightToLeft = True

            headers = ['اسم المنتج', 'رمز SKU', 'الباركود', 'التصنيف', 'سعر الشراء (ج.م)', 'سعر البيع (ج.م)', 'الكمية بالمخزن', 'الحد الأدنى']
            ws.append(headers)

            header_font = Font(name='Cairo', size=11, bold=True, color="FFFFFF")
            header_fill = PatternFill(start_color="10B981", end_color="10B981", fill_type="solid")
            alignment_center = Alignment(horizontal="center", vertical="center")
            thin_border = Border(left=Side(style='thin', color='CBD5E1'), right=Side(style='thin', color='CBD5E1'),
                                 top=Side(style='thin', color='CBD5E1'), bottom=Side(style='thin', color='CBD5E1'))

            for col_num, header in enumerate(headers, 1):
                cell = ws.cell(row=1, column=col_num)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = alignment_center

            for row_idx, p in enumerate(products, start=2):
                ws.append([
                    p.name,
                    p.sku or '',
                    p.barcode or '',
                    p.category or 'عام',
                    float(p.purchase_price),
                    float(p.selling_price),
                    p.stock_quantity,
                    p.min_stock_threshold
                ])
                for col_idx in range(1, len(headers) + 1):
                    cell = ws.cell(row=row_idx, column=col_idx)
                    cell.border = thin_border
                    if col_idx in [5, 6, 7, 8]:
                        cell.alignment = Alignment(horizontal="right", vertical="center")

            response = HttpResponse(
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = 'attachment; filename="inventory_products.xlsx"'
            wb.save(response)
            return response
        except Exception:
            import csv
            response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
            response['Content-Disposition'] = 'attachment; filename="inventory_products.csv"'
            writer = csv.writer(response)
            writer.writerow(['اسم المنتج', 'رمز SKU', 'الباركود', 'التصنيف', 'سعر الشراء (ج.م)', 'سعر البيع (ج.م)', 'الكمية بالمخزن', 'الحد الأدنى'])
            for p in products:
                writer.writerow([
                    p.name,
                    p.sku or '',
                    p.barcode or '',
                    p.category or 'عام',
                    float(p.purchase_price),
                    float(p.selling_price),
                    p.stock_quantity,
                    p.min_stock_threshold
                ])
            return response


class DownloadSampleProductsExcelView(View):
    """تحميل نموذج استيراد المنتجات Excel التوضيحي"""
    def get(self, request, *args, **kwargs):
        import openpyxl
        from openpyxl.styles import Font, Alignment, PatternFill
        from django.http import HttpResponse

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "نموذج استيراد المنتجات"
        ws.views.sheetView[0].rightToLeft = True

        headers = ['اسم المنتج', 'رمز SKU (الرمز المرجعي)', 'الباركود', 'التصنيف', 'سعر الشراء (ج.م)', 'سعر البيع (ج.م)', 'الكمية بالمخزن', 'الحد الأدنى']
        ws.append(headers)

        header_font = Font(name='Cairo', size=11, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="3B82F6", end_color="3B82F6", fill_type="solid")
        for col_num in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_num)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")

        sample_rows = [
            ['شداد 6 مسمار', 'SKU-0001', '622100000010', 'قطع غيار', 100, 130, 4, 2],
            ['أولسيه 41.25×25', 'SKU-0006', '622100000065', 'قطع غيار', 15, 25, 25, 5],
            ['موتور مياه 1 حصان', 'SKU-0007', '622100000072', 'مواتير', 30, 100, 2, 1],
        ]
        for row in sample_rows:
            ws.append(row)

        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="Elnamaa_Products_Import_Sample.xlsx"'
        wb.save(response)
        return response


class ImportProductsExcelView(View):
    """استيراد ملف Excel وتحديث/إضافة المنتجات بذكاء مع التعرف التلقائي على الأعمدة"""
    def post(self, request, *args, **kwargs):
        import uuid
        excel_file = request.FILES.get('excel_file')
        if not excel_file:
            messages.error(request, "يرجى اختيار ملف Excel لاستيراد المنتجات.")
            return redirect('inventory:inventory_list')

        try:
            import openpyxl
            wb = openpyxl.load_workbook(excel_file, data_only=True)
            ws = wb.active

            imported_count = 0
            updated_count = 0

            with transaction.atomic():
                rows = list(ws.iter_rows(values_only=True))
                if len(rows) <= 1:
                    messages.warning(request, "الملف المرفوع فارغ أو لا يحتوي على صفوف بيانات!")
                    return redirect('inventory:inventory_list')

                # قراءة وترسيم عناوين الأعمدة ديناميكياً لتفادي أي لخبطة بالترتيب
                header_row = [str(cell).strip() if cell is not None else '' for cell in rows[0]]
                col_map = {
                    'name': None,
                    'sku': None,
                    'barcode': None,
                    'category': None,
                    'purchase_price': None,
                    'selling_price': None,
                    'stock_quantity': None,
                    'min_stock_threshold': None,
                }

                for idx, h in enumerate(header_row):
                    hl = h.lower()
                    if col_map['name'] is None and any(k in hl for k in ['اسم المنتج', 'المنتج', 'اسم', 'name']):
                        col_map['name'] = idx
                    elif col_map['sku'] is None and any(k in hl for k in ['sku', 'المرجعي', 'كود الصنف', 'رمز']):
                        col_map['sku'] = idx
                    elif col_map['barcode'] is None and any(k in hl for k in ['باركوود', 'باركود', 'بار كود', 'barcode']):
                        col_map['barcode'] = idx
                    elif col_map['category'] is None and any(k in hl for k in ['تصنيف', 'فئة', 'category']):
                        col_map['category'] = idx
                    elif col_map['purchase_price'] is None and any(k in hl for k in ['شراء', 'تكلفة', 'cost', 'purchase']):
                        col_map['purchase_price'] = idx
                    elif col_map['selling_price'] is None and any(k in hl for k in ['بيع', 'selling', 'price']):
                        col_map['selling_price'] = idx
                    elif col_map['stock_quantity'] is None and any(k in hl for k in ['كمية', 'كميه', 'المخزن', 'مخزون', 'stock', 'qty', 'quantity']):
                        col_map['stock_quantity'] = idx
                    elif col_map['min_stock_threshold'] is None and any(k in hl for k in ['أدنى', 'ادنى', 'تنبيه', 'min', 'threshold']):
                        col_map['min_stock_threshold'] = idx

                # ضبط احتياطي في حال عدم تطابق العناوين النصية
                total_cols = len(header_row)
                if col_map['name'] is None:
                    col_map['name'] = 0

                if col_map['sku'] is None and col_map['barcode'] is None:
                    if total_cols >= 8:
                        col_map['sku'] = 1
                        col_map['barcode'] = 2
                        col_map['category'] = 3
                        col_map['purchase_price'] = 4
                        col_map['selling_price'] = 5
                        col_map['stock_quantity'] = 6
                        col_map['min_stock_threshold'] = 7
                    else:
                        col_map['barcode'] = 1
                        col_map['category'] = 2
                        col_map['purchase_price'] = 3
                        col_map['selling_price'] = 4
                        col_map['stock_quantity'] = 5
                        col_map['min_stock_threshold'] = 6

                def get_clean_str(row_data, col_idx):
                    if col_idx is None or col_idx >= len(row_data):
                        return ''
                    val = row_data[col_idx]
                    if val is None:
                        return ''
                    s = str(val).strip()
                    return '' if s in ['None', 'none', '-', ''] else s

                def get_clean_decimal(row_data, col_idx, default='0.00'):
                    if col_idx is None or col_idx >= len(row_data):
                        return Decimal(default)
                    val = row_data[col_idx]
                    if val is None:
                        return Decimal(default)
                    s = str(val).strip().replace(',', '')
                    arabic_digits = '٠١٢٣٤٥٦٧٨٩'
                    for i, d in enumerate(arabic_digits):
                        s = s.replace(d, str(i))
                    try:
                        return Decimal(s)
                    except Exception:
                        return Decimal(default)

                def get_clean_int(row_data, col_idx, default=0):
                    if col_idx is None or col_idx >= len(row_data):
                        return default
                    val = row_data[col_idx]
                    if val is None:
                        return default
                    s = str(val).strip().replace(',', '')
                    arabic_digits = '٠١٢٣٤٥٦٧٨٩'
                    for i, d in enumerate(arabic_digits):
                        s = s.replace(d, str(i))
                    try:
                        return int(float(s))
                    except Exception:
                        return default

                tenant = getattr(request, 'tenant', None)

                # قراءة الصفوف وتحديث أو إنشاء المنتجات
                for row in rows[1:]:
                    if not row or not any(row):
                        continue

                    name = get_clean_str(row, col_map['name'])
                    if not name:
                        continue

                    sku = get_clean_str(row, col_map['sku'])
                    barcode = get_clean_str(row, col_map['barcode'])
                    if not barcode:
                        barcode = None

                    category = get_clean_str(row, col_map['category']) or 'قطع غيار عامة'
                    purchase_price = get_clean_decimal(row, col_map['purchase_price'], default='0.00')
                    selling_price = get_clean_decimal(row, col_map['selling_price'], default='0.00')
                    stock_qty = get_clean_int(row, col_map['stock_quantity'], default=0)
                    min_stock = get_clean_int(row, col_map['min_stock_threshold'], default=5)

                    if not sku:
                        sku = barcode or f"SKU-{uuid.uuid4().hex[:6].upper()}"

                    prod, created = Product.objects.get_or_create(
                        name=name,
                        defaults={
                            'sku': sku,
                            'barcode': barcode,
                            'category': category,
                            'purchase_price': purchase_price,
                            'selling_price': selling_price,
                            'stock_quantity': stock_qty,
                            'min_stock_threshold': min_stock,
                            'tenant': tenant,
                        }
                    )

                    if not created:
                        if sku:
                            prod.sku = sku
                        if barcode:
                            prod.barcode = barcode
                        prod.category = category
                        prod.purchase_price = purchase_price
                        prod.selling_price = selling_price
                        prod.stock_quantity = stock_qty
                        prod.min_stock_threshold = min_stock
                        prod.save()
                        updated_count += 1
                    else:
                        imported_count += 1

            messages.success(
                request,
                f"🎉 تم بنجاح استيراد ({imported_count}) منتج جديد، وتحديث بيانات ({updated_count}) منتج سابق في المخزن بدقة تامة!"
            )
        except Exception as e:
            messages.error(request, f"حدث خطأ أثناء قراءة ملف Excel: {str(e)}")

        return redirect('inventory:inventory_list')


class BarcodeGeneratorView(TemplateView):
    """مولد وطباعة ملصقات الباركود للمنتجات وأجهزة الورشة"""
    template_name = "barcode_labels.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            products = Product.objects.filter(tenant=tenant).select_related('category').only(
                'id', 'name', 'barcode', 'sku', 'selling_price', 'stock_quantity', 'category__name'
            ).order_by('name')
        else:
            products = Product.objects.all().select_related('category').only(
                'id', 'name', 'barcode', 'sku', 'selling_price', 'stock_quantity', 'category__name'
            ).order_by('name')
        
        # Format JSON products for instant Alpine JS selector
        prod_json = []
        for p in products:
            prod_json.append({
                'id': p.id,
                'name': p.name,
                'barcode': p.barcode or p.sku or f"PROD-{p.id}",
                'price': str(p.selling_price),
                'stock': p.stock_quantity,
                'category': str(p.category.name) if p.category else 'عام'
            })
            
        context['products'] = products
        context['products_json'] = prod_json
        
        selected_id = self.request.GET.get('product_id')
        selected_prod = None
        if selected_id and str(selected_id).isdigit():
            selected_prod = products.filter(id=int(selected_id)).first()
        elif products.exists():
            selected_prod = products.first()

        context['selected_product'] = selected_prod
        context['initial_id'] = selected_prod.id if selected_prod else ''
        context['initial_title'] = selected_prod.name if selected_prod else ''
        context['initial_barcode'] = (selected_prod.barcode or selected_prod.sku or f"PROD-{selected_prod.id}") if selected_prod else '62910001'
        context['initial_price'] = str(selected_prod.selling_price) if selected_prod else '0.00'
        return context


class CategoryCreateView(View):
    def post(self, request, *args, **kwargs):
        name = request.POST.get('name', '').strip()
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', '')
        if name:
            tenant = getattr(request, 'tenant', None)
            category, created = Category.objects.get_or_create(name=name, tenant=tenant)
            if created:
                msg = f'تم إضافة الفئة "{name}" بنجاح.'
                messages.success(request, msg)
                if is_ajax:
                    return JsonResponse({'success': True, 'id': category.id, 'name': category.name, 'message': msg})
            else:
                msg = f'الفئة "{name}" موجودة بالفعل.'
                messages.info(request, msg)
                if is_ajax:
                    return JsonResponse({'success': False, 'error': msg}, status=400)
        else:
            msg = 'الرجاء إدخال اسم الفئة.'
            messages.error(request, msg)
            if is_ajax:
                return JsonResponse({'success': False, 'error': msg}, status=400)
        return redirect(request.META.get('HTTP_REFERER', 'inventory:inventory_list'))


class CategoryUpdateView(View):
    def post(self, request, pk, *args, **kwargs):
        category = get_object_or_404(Category.all_objects, pk=pk)
        new_name = request.POST.get('name', '').strip()
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', '')
        if new_name:
            old_name = category.name
            category.name = new_name
            category.save()

            # Synchronize all products belonging to this tenant with the updated category
            tenant = getattr(request, 'tenant', None) or category.tenant
            updated_count = Product.all_objects.filter(tenant=tenant, category=old_name).update(category=new_name)

            # Also check if any products had legacy choice codes
            LEGACY_CHOICE_MAP = {
                'fertilizers': 'أسمدة ومخصبات زراعية',
                'pesticides': 'مبيدات حشرية وفطرية',
                'spare_parts': 'قطع غيار مواقير ورش',
                'equipment': 'معدات وآلات زراعية',
                'oils': 'زيوت وشحومات',
                'general': 'عام / متنوع',
            }
            for code, lbl in LEGACY_CHOICE_MAP.items():
                if lbl == old_name or code == old_name:
                    updated_count += Product.all_objects.filter(tenant=tenant, category=code).update(category=new_name)

            msg = f'تم تحديث اسم الفئة إلى "{new_name}" وتحديث كافة المنتجات المرتبطة بنجاح.'
            messages.success(request, msg)
            if is_ajax:
                return JsonResponse({'success': True, 'id': category.id, 'name': new_name, 'updated_products': updated_count, 'message': msg})
        else:
            msg = 'الرجاء إدخال اسم الفئة الجديد.'
            messages.error(request, msg)
            if is_ajax:
                return JsonResponse({'success': False, 'error': msg}, status=400)
        return redirect(request.META.get('HTTP_REFERER', 'inventory:inventory_list'))


class CategoryDeleteView(View):
    def post(self, request, pk, *args, **kwargs):
        category = get_object_or_404(Category.all_objects, pk=pk)
        name = category.name
        tenant = getattr(request, 'tenant', None) or category.tenant
        category.delete()
        # Set products that had this category to default 'عام / متنوع'
        Product.all_objects.filter(tenant=tenant, category=name).update(category='عام / متنوع')
        msg = f'تم حذف الفئة "{name}" بنجاح.'
        messages.success(request, msg)
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
            return JsonResponse({'success': True, 'message': msg})
        return redirect(request.META.get('HTTP_REFERER', 'inventory:inventory_list'))


class COGSRestockDataView(View):
    """
    ميزان تعويض المخزون وحماية رأس المال (Restock Balance & Capital Safety)
    وإعادة طلب البضاعة المباعة تلقائياً بناءً على تكلفة البضاعة المباعة (COGS).
    
    يحسب:
    1. المبلغ المطلوب تعويضه (Target Capital): إجمالي COGS للمبيعات خلال الفترة.
    2. المبلغ المعوض فعلياً (Covered Capital): إجمالي ما تم إدراجه في أوامر شراء لتلك المبيعات.
    3. عجز التعويض المتبقي (Remaining Deficit): Target - Covered (يصل إلى 0.00 عند اكتمال الطلب).
    4. نسبة التغطية (Coverage Percentage).
    5. السيولة النقدية المتاحة بالدرج (Drawer Available Cash) لتحديد كفاية الكاش للشراء الفوري.
    """
    def get(self, request, *args, **kwargs):
        from pos.models import OrderItem, Order
        from inventory.models import PurchaseOrderItem
        from core_project.services import get_profit_and_loss
        from django.db.models import Sum, Q
        import datetime

        period = request.GET.get('period', 'today')  # today / this_week / this_month / all / custom
        start_date_str = request.GET.get('start_date', '').strip()
        end_date_str = request.GET.get('end_date', '').strip()
        today = timezone.now().date()

        date_filter_sales = {}
        date_filter_po = {
            'purchase_order__status__in': ['draft', 'sent', 'received'],
            'product__isnull': False,
        }

        tenant = getattr(request, 'tenant', None)
        if tenant:
            date_filter_sales['order__tenant'] = tenant
            date_filter_po['purchase_order__tenant'] = tenant

        if period == 'today':
            date_filter_sales['order__created_at__date'] = today
            date_filter_po['purchase_order__created_at__date'] = today
        elif period == 'this_week':
            week_start = today - datetime.timedelta(days=today.weekday())
            date_filter_sales['order__created_at__date__gte'] = week_start
            date_filter_po['purchase_order__created_at__date__gte'] = week_start
        elif period == 'this_month':
            month_start = today.replace(day=1)
            date_filter_sales['order__created_at__date__gte'] = month_start
            date_filter_sales['order__created_at__date__lte'] = today
            date_filter_po['purchase_order__created_at__date__gte'] = month_start
            date_filter_po['purchase_order__created_at__date__lte'] = today
        elif period == 'custom':
            if start_date_str:
                try:
                    s_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
                    date_filter_sales['order__created_at__date__gte'] = s_date
                    date_filter_po['purchase_order__created_at__date__gte'] = s_date
                except (ValueError, TypeError):
                    pass
            if end_date_str:
                try:
                    e_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
                    date_filter_sales['order__created_at__date__lte'] = e_date
                    date_filter_po['purchase_order__created_at__date__lte'] = e_date
                except (ValueError, TypeError):
                    pass
        # 'all' => no date filter

        # 1. Fetch quantities already ordered in purchase orders for this period
        ordered_qs = (
            PurchaseOrderItem.objects
            .filter(**date_filter_po)
            .values('product__id')
            .annotate(total_ordered=Sum('quantity_requested'))
        )
        ordered_map = {row['product__id']: int(row['total_ordered'] or 0) for row in ordered_qs}

        # 2. Fetch sold items in this period
        qs = (
            OrderItem.objects
            .filter(**date_filter_sales)
            .select_related('product', 'product__default_supplier')
            .values(
                'product__id',
                'product__name',
                'product__sku',
                'product__purchase_price',
                'product__stock_quantity',
                'product__default_supplier__id',
                'product__default_supplier__name',
            )
            .annotate(
                total_qty_sold=Sum('quantity'),
                total_cogs=Sum('cost'),
            )
            .order_by('-total_cogs')
        )

        items = []
        target_capital = Decimal('0.00')
        covered_capital = Decimal('0.00')
        remaining_deficit = Decimal('0.00')
        all_sold_products_count = 0

        for row in qs:
            prod_id = row['product__id']
            if not prod_id:
                continue

            all_sold_products_count += 1
            total_qty_sold = int(row['total_qty_sold'] or 0)
            already_ordered = ordered_map.get(prod_id, 0)
            purchase_price = Decimal(str(row['product__purchase_price'] or '0.00'))

            item_target_cogs = purchase_price * Decimal(str(total_qty_sold))
            covered_qty = min(already_ordered, total_qty_sold)
            item_covered_cogs = purchase_price * Decimal(str(covered_qty))
            
            target_capital += item_target_cogs
            covered_capital += item_covered_cogs

            # Calculate remaining quantity that still needs to be re-ordered
            net_needed = total_qty_sold - already_ordered
            if net_needed > 0:
                item_deficit_cogs = purchase_price * Decimal(str(net_needed))
                remaining_deficit += item_deficit_cogs

                items.append({
                    'product_id': prod_id,
                    'product_name': row['product__name'],
                    'product_sku': row['product__sku'] or '',
                    'qty_sold': total_qty_sold,
                    'already_ordered': already_ordered,
                    'purchase_price': float(purchase_price),
                    'total_cogs': float(item_target_cogs),
                    'covered_cogs': float(item_covered_cogs),
                    'deficit_cogs': float(item_deficit_cogs),
                    'current_stock': row['product__stock_quantity'],
                    'supplier_id': row['product__default_supplier__id'],
                    'supplier_name': row['product__default_supplier__name'] or '',
                    'restock_qty': net_needed,  # Default to remaining net needed
                    'is_fully_covered': False,
                })

        # Calculate coverage percent
        if target_capital > Decimal('0.00'):
            coverage_percent = round(float((covered_capital / target_capital) * Decimal('100.00')), 1)
            coverage_percent = min(100.0, max(0.0, coverage_percent))
        else:
            coverage_percent = 100.0

        # Calculate real-time available drawer cash for capital safety comparison
        try:
            order_methods = Order.objects.filter(**({'tenant': tenant} if tenant else {})).aggregate(
                cash_visa=Sum('total_amount', filter=Q(payment_method__in=['cash', 'visa']))
            )
            cash_sales = order_methods['cash_visa'] or Decimal('0.00')
            pnl = get_profit_and_loss()
            total_cash_in = cash_sales + pnl.get('labor_fees', Decimal('0.00')) + pnl.get('collected_from_customers', Decimal('0.00')) + pnl.get('cash_deposits', Decimal('0.00'))
            total_cash_out = pnl.get('total_expenses', Decimal('0.00')) + pnl.get('paid_to_suppliers', Decimal('0.00')) + pnl.get('cash_withdrawals', Decimal('0.00'))
            drawer_cash = max(Decimal('0.00'), total_cash_in - total_cash_out)
        except Exception:
            drawer_cash = Decimal('0.00')

        return JsonResponse({
            'success': True,
            'period': period,
            'start_date': start_date_str,
            'end_date': end_date_str,
            'target_capital': float(target_capital),
            'covered_capital': float(covered_capital),
            'remaining_deficit': float(remaining_deficit),
            'coverage_percent': coverage_percent,
            'drawer_cash': float(drawer_cash),
            'is_fully_covered': (remaining_deficit <= Decimal('0.00') and target_capital > Decimal('0.00')),
            'is_empty_sales': (target_capital <= Decimal('0.00')),
            'items': items,
            'items_count': len(items),
            'all_sold_products_count': all_sold_products_count,
        })


class COGSRestockCreateOrderView(View):
    """
    إنشاء أمر شراء تلقائي من قائمة COGS Restock المختارة.
    """
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'بيانات غير صحيحة'}, status=400)

        items_data = data.get('items', [])
        notes = data.get('notes', 'أمر شراء تلقائي بناءً على تكلفة البضاعة المباعة (COGS)')

        if not items_data:
            return JsonResponse({'success': False, 'error': 'يرجى تحديد صنف واحد على الأقل'}, status=400)

        try:
            with transaction.atomic():
                today_str = timezone.now().strftime('%Y%m%d')
                random_suffix = str(uuid.uuid4().hex[:4]).upper()
                order_number = f"COGS-{today_str}-{random_suffix}"
                tenant = getattr(request, 'tenant', None)

                order = PurchaseOrder.objects.create(
                    order_number=order_number,
                    notes=notes,
                    status='draft',
                    tenant=tenant,
                )

                item_supplier_ids = set()
                for item in items_data:
                    product_id = item.get('product_id')
                    restock_qty = max(1, int(item.get('restock_qty', 1)))
                    unit_cost = Decimal(str(item.get('purchase_price', 0)))
                    supplier_id = item.get('supplier_id') or None

                    prod_obj = Product.objects.filter(id=product_id).first() if product_id else None

                    if supplier_id:
                        try:
                            item_supplier_ids.add(int(supplier_id))
                        except (ValueError, TypeError):
                            pass
                    elif prod_obj and prod_obj.default_supplier_id:
                        supplier_id = prod_obj.default_supplier_id
                        item_supplier_ids.add(prod_obj.default_supplier_id)

                    PurchaseOrderItem.objects.create(
                        purchase_order=order,
                        product=prod_obj,
                        custom_item_name=prod_obj.name if prod_obj else item.get('product_name', 'صنف COGS'),
                        supplier_id=supplier_id,
                        quantity_requested=restock_qty,
                        unit_cost=max(Decimal('0.00'), unit_cost),
                    )

                # Auto-assign supplier if single supplier
                if not order.supplier_id and len(item_supplier_ids) == 1:
                    order.supplier_id = list(item_supplier_ids)[0]
                    order.save(update_fields=['supplier_id'])

            from dashboard.audit import log_activity
            log_activity(
                request,
                module='purchase_orders',
                action_type='create',
                description=f"توليد أمر شراء تلقائي من تكلفة البضاعة المباعة (COGS Restock) #{order.order_number} ({len(items_data)} أصناف)",
                severity='info'
            )

            return JsonResponse({
                'success': True,
                'order_id': order.id,
                'order_number': order.order_number,
                'redirect_url': str(reverse_lazy('inventory:purchase_order_detail', kwargs={'pk': order.id}))
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'حدث خطأ: {str(e)}'}, status=400)




