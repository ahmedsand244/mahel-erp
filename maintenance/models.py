from django.db import models
from ledger.models import Customer
from inventory.models import Product
from tenants.models import Tenant
from tenants.managers import TenantManager

class MaintenanceTicket(models.Model):
    STATUS_CHOICES = [
        ('pending', 'استلام / قيد الانتظار'),
        ('in_progress', 'صيانة نشطة'),
        ('completed', 'جاهز للاستلام'),
        ('delivered', 'تم التسليم والتحصيل'),
    ]

    ticket_number = models.CharField(max_length=100, verbose_name="رقم تذكرة الصيانة")
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='tickets', verbose_name="العميل")
    device_name = models.CharField(max_length=200, verbose_name="المعدة / الموتور")
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending', db_index=True, verbose_name="حالة الصيانة")
    labor_fees = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="رسوم المصنعية")
    parts_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="تكلفة قطع الغيار")
    parts_sell = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="مبيعات قطع الغيار")
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True, related_name='tickets', verbose_name="الشركة")
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
        return f"تذكرة صيانة #{self.ticket_number} - {self.device_name}"


class TicketPartConsumption(models.Model):
    ticket = models.ForeignKey(MaintenanceTicket, on_delete=models.CASCADE, related_name='parts_consumed', verbose_name="تذكرة الصيانة")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='ticket_parts', verbose_name="المنتج (قطعة الغيار)")
    quantity = models.IntegerField(default=1, verbose_name="الكمية")
    price_charged = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="السعر المطلوب")
    cost = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="التكلفة الفعلية")

    def __str__(self):
        return f"تركيب {self.product.name} x {self.quantity} للتذكرة {self.ticket.ticket_number}"
