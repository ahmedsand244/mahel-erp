from django.db import models
from tenants.models import Tenant
from tenants.managers import TenantManager

class Product(models.Model):
    CATEGORY_CHOICES = [
        ('fertilizers', 'أسمدة ومخصبات زراعية'),
        ('pesticides', 'مبيدات حشرية وفطرية'),
        ('spare_parts', 'قطع غيار مواقير ورش'),
        ('equipment', 'معدات وآلات زراعية'),
        ('oils', 'زيوت وشحومات'),
        ('general', 'عام / متنوع'),
    ]

    name = models.CharField(max_length=200, db_index=True, verbose_name="اسم المنتج")
    sku = models.CharField(max_length=100, verbose_name="رمز SKU")
    barcode = models.CharField(max_length=100, blank=True, null=True, verbose_name="الباركود")
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='general', verbose_name="التصنيف / الفئة")
    image = models.ImageField(upload_to='products/', blank=True, null=True, verbose_name="صورة المنتج")
    purchase_price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="سعر الشراء")
    selling_price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="سعر البيع")
    stock_quantity = models.IntegerField(default=0, verbose_name="الكمية المتوفرة")
    min_stock_threshold = models.IntegerField(default=5, verbose_name="الحد الأدنى للتنبيه")
    default_supplier = models.ForeignKey('ledger.Supplier', on_delete=models.SET_NULL, blank=True, null=True, related_name='products', verbose_name="المورد / الشركة الافتراضية")
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True, db_index=True, related_name='products', verbose_name="الشركة")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    objects = TenantManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['sku']),
            models.Index(fields=['barcode']),
            models.Index(fields=['category']),
        ]

    def save(self, *args, **kwargs):
        if not self.tenant_id:
            from tenants.middleware import get_current_tenant
            t = get_current_tenant()
            if t:
                self.tenant = t
        if self.barcode == "":
            self.barcode = None
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.sku})"


class StockAlert(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='alerts', verbose_name="المنتج")
    message = models.TextField(verbose_name="رسالة التنبيه")
    is_resolved = models.BooleanField(default=False, db_index=True, verbose_name="تم حلها")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        status = "محلول" if self.is_resolved else "نشط"
        return f"تنبيه: {self.product.name} - [{status}]"


class PurchaseOrder(models.Model):
    STATUS_CHOICES = [
        ('draft', 'مسودة (قيد التحضير)'),
        ('sent', 'تم الإرسال للشركة'),
        ('received', 'تم استلام البضاعة بالمخزن'),
        ('cancelled', 'ملغي'),
    ]

    order_number = models.CharField(max_length=50, verbose_name="رقم طلب البضاعة")
    supplier = models.ForeignKey('ledger.Supplier', on_delete=models.SET_NULL, blank=True, null=True, related_name='purchase_orders', verbose_name="الشركة / المورد الرئيسي")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name="حالة الطلب")
    notes = models.TextField(blank=True, default='', verbose_name="ملاحظات وتوجيهات للشركة")
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True, related_name='purchase_orders', verbose_name="الشركة")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخر تحديث")
    received_at = models.DateTimeField(blank=True, null=True, verbose_name="تاريخ استلام الشحنة")

    objects = TenantManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ['-created_at']
        verbose_name = "طلب بضاعة"
        verbose_name_plural = "طلبات البضاعة والنواقص"

    def save(self, *args, **kwargs):
        if not self.tenant_id:
            from tenants.middleware import get_current_tenant
            t = get_current_tenant()
            if t:
                self.tenant = t
        super().save(*args, **kwargs)

    def __str__(self):
        supplier_name = self.supplier.name if self.supplier else "عدة شركات/موردين"
        return f"طلب {self.order_number} - {supplier_name} ({self.get_status_display()})"

    @property
    def total_estimated_cost(self):
        return sum(item.total_cost for item in self.items.all())

    @property
    def total_items_count(self):
        return sum(item.quantity_requested for item in self.items.all())


class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items', verbose_name="طلب البضاعة")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, blank=True, null=True, related_name='purchase_order_items', verbose_name="المنتج بالمخزن")
    custom_item_name = models.CharField(max_length=200, blank=True, default='', verbose_name="اسم صنف خارجي / تخصيص")
    supplier = models.ForeignKey('ledger.Supplier', on_delete=models.SET_NULL, blank=True, null=True, related_name='order_items', verbose_name="الشركة / المورد")
    quantity_requested = models.IntegerField(default=1, verbose_name="الكمية المطلوبة")
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="تكلفة القطعة التقديرية")
    is_received = models.BooleanField(default=False, verbose_name="تم الاستلام")

    class Meta:
        ordering = ['id']

    @property
    def display_name(self):
        if self.product:
            return self.product.name
        if self.custom_item_name and self.custom_item_name.strip():
            return self.custom_item_name.strip()
        return "صنف طلبية مخصص"

    @property
    def display_supplier_name(self):
        if self.supplier:
            return self.supplier.name
        if self.product and self.product.default_supplier:
            return self.product.default_supplier.name
        if self.purchase_order and self.purchase_order.supplier:
            return self.purchase_order.supplier.name
        return "غير محدد"

    @property
    def total_cost(self):
        return self.quantity_requested * self.unit_cost

    def __str__(self):
        return f"{self.display_name} x {self.quantity_requested}"

