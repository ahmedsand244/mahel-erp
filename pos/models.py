from django.db import models
from ledger.models import Customer
from inventory.models import Product
from tenants.models import Tenant
from tenants.managers import TenantManager

class Order(models.Model):
    PAYMENT_METHODS = [
        ('cash', 'نقدي'),
        ('visa', 'شبكة / فيزا'),
        ('deferred', 'شكك / آجل'),
    ]

    order_number = models.CharField(max_length=100, db_index=True, verbose_name="رقم الفاتورة")
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, blank=True, null=True, related_name='orders', verbose_name="العميل")
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='cash', db_index=True, verbose_name="طريقة الدفع")
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="إجمالي الفاتورة")
    cost_of_goods_sold = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="تكلفة البضاعة المباعة")
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True, db_index=True, related_name='orders', verbose_name="الشركة")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    objects = TenantManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.tenant_id:
            from tenants.middleware import get_current_tenant
            t = get_current_tenant()
            if t:
                self.tenant = t
        super().save(*args, **kwargs)

    def __str__(self):
        return f"فاتورة مبيعات #{self.order_number}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', verbose_name="الفاتورة")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='order_items', verbose_name="المنتج")
    quantity = models.IntegerField(default=1, verbose_name="الكمية")
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="سعر الوحدة")
    cost = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="تكلفة الوحدة")

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"
