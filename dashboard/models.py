from django.db import models
from django.contrib.auth.models import User
from tenants.models import Tenant
from tenants.managers import TenantManager


class AuditLog(models.Model):
    """
    سجل نشاطات وحركات النظام الشامل والرقابي (System Audit Log & Activity Tracker).
    يوثق كل حركة تتم داخل النظام: من قام بها، من أي جهاز ومتصفح، عنوان الـ IP، ونوع الحركة بالتفصيل.
    """
    MODULE_CHOICES = [
        ('pos', 'المبيعات ونقاط البيع'),
        ('inventory', 'المخزن والمنتجات'),
        ('purchase_orders', 'طلبات البضاعة والنواقص'),
        ('maintenance', 'الورشة والصيانة'),
        ('ledger', 'العملاء والشكك والموردين'),
        ('expenses', 'المصروفات العامة'),
        ('cash', 'الخزينة وحركات النقدية'),
        ('reports', 'التقارير المالية'),
        ('backup', 'النسخ الاحتياطي والأمان'),
        ('auth', 'الحسابات وتسجيل الدخول'),
        ('settings', 'إعدادات النظام'),
        ('other', 'حركات متنوعة'),
    ]

    ACTION_CHOICES = [
        ('create', 'إضافة جديدة'),
        ('update', 'تعديل بيانات'),
        ('delete', 'حذف'),
        ('login', 'تسجيل دخول'),
        ('logout', 'تسجيل خروج'),
        ('price_change', 'تعديل أسعار'),
        ('stock_change', 'تعديل مخزون'),
        ('status_change', 'تغيير حالة'),
        ('receive_order', 'استلام شحنة بضاعة'),
        ('export', 'تصدير بيانات'),
        ('import', 'استيراد بيانات'),
        ('restore', 'استرجاع نسخة احتياطية'),
        ('cash_operation', 'حركة خزانة / نقدية'),
        ('other', 'إجراء آخر'),
    ]

    SEVERITY_CHOICES = [
        ('info', 'عادي'),
        ('warning', 'تنبيه'),
        ('danger', 'حساس / خطير'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        verbose_name="المستخدم"
    )
    user_display = models.CharField(max_length=150, verbose_name="اسم الموظف أو المستخدم")
    user_email = models.CharField(max_length=150, blank=True, default='', verbose_name="البريد الإلكتروني")

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        db_index=True,
        related_name='audit_logs',
        verbose_name="الشركة"
    )

    module = models.CharField(max_length=50, choices=MODULE_CHOICES, db_index=True, verbose_name="القسم")
    action_type = models.CharField(max_length=50, choices=ACTION_CHOICES, db_index=True, verbose_name="نوع الإجراء")
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='info', db_index=True, verbose_name="مستوى الأهمية")

    description = models.TextField(verbose_name="وصف الحدث الدقيق")

    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="عنوان الـ IP")
    device_info = models.CharField(max_length=200, blank=True, default='', verbose_name="نوع الجهاز والمتصفح")
    user_agent = models.TextField(blank=True, default='', verbose_name="بيانات المتصفح والنظام")

    extra_data = models.JSONField(blank=True, null=True, verbose_name="بيانات إضافية")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="تاريخ ووقت الحركة")

    objects = TenantManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ['-created_at']
        verbose_name = "سجل حركة ونشاط"
        verbose_name_plural = "سجل نشاطات وحركات النظام"
        indexes = [
            models.Index(fields=['module', 'created_at']),
            models.Index(fields=['action_type', 'created_at']),
            models.Index(fields=['severity', 'created_at']),
        ]

    def save(self, *args, **kwargs):
        if not self.tenant_id:
            from tenants.middleware import get_current_tenant
            t = get_current_tenant()
            if t:
                self.tenant = t
        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.get_module_display()}] {self.user_display}: {self.description[:40]}"
