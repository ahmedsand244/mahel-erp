from django.db import models
from tenants.models import Tenant
from tenants.managers import TenantManager

class StoreAudit(models.Model):
    """
    سجل وجلسات جرد المحل والمركز المالي للفترات والأيام المحددة
    """
    title = models.CharField(max_length=200, verbose_name="عنوان/بيان الجرد")
    audit_date = models.DateField(auto_now_add=True, verbose_name="تاريخ إجراء الجرد")
    start_date = models.DateField(verbose_name="بداية فترة الجرد", null=True, blank=True)
    end_date = models.DateField(verbose_name="نهاية فترة الجرد", null=True, blank=True)
    
    gross_sales = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="إجمالي المبيعات")
    cogs = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="تكلفة المبيعات")
    maintenance_labor = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="أجور الصيانة")
    maintenance_parts_sell = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="مبيعات قطع الغيار")
    maintenance_parts_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="تكلفة قطع الغيار")
    total_expenses = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="المصروفات")
    net_profit = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="صافي الربح")
    
    inventory_cost_value = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="قيمة المخزون بسعر الشراء")
    inventory_retail_value = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="قيمة المخزون بسعر البيع")
    
    customer_debts = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="ديون العملاء وقت الجرد")
    supplier_debts = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="ديون الموردين وقت الجرد")
    
    notes = models.TextField(blank=True, null=True, verbose_name="ملاحظات وتفاصيل الجرد")
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True, related_name='store_audits', verbose_name="الشركة")
    created_at = models.DateTimeField(auto_now_add=True)

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
        return f"{self.title} - {self.audit_date}"

