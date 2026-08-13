from django.db import models
from tenants.models import Tenant
from tenants.managers import TenantManager

class Expense(models.Model):
    CATEGORY_CHOICES = [
        ('rent', 'إيجار المحل'),
        ('utility', 'فواتير (كهرباء / مياه / إنترنت)'),
        ('salary', 'رواتب وأجور الموظفين'),
        ('marketing', 'تسويق وإعلانات'),
        ('other', 'مصروفات تشغيلية أخرى'),
    ]

    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default='other', db_index=True, verbose_name="نوع المصروف")
    description = models.CharField(max_length=255, verbose_name="بيان المصروف")
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="المبلغ")
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True, related_name='expenses', verbose_name="الشركة")
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
        return f"{self.get_category_display()} - {self.amount}"
