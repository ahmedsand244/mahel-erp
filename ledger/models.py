from django.db import models
from django.utils import timezone
from tenants.models import Tenant
from tenants.managers import TenantManager

class Customer(models.Model):
    name = models.CharField(max_length=200, db_index=True, verbose_name="اسم العميل")
    phone = models.CharField(max_length=50, blank=True, null=True, db_index=True, verbose_name="رقم الهاتف")
    workplace = models.CharField(max_length=200, blank=True, null=True, verbose_name="مكان العمل / المزرعة / الورشة")
    address = models.CharField(max_length=200, blank=True, null=True, verbose_name="العنوان / المنطقة")
    avatar = models.ImageField(upload_to='customers/', blank=True, null=True, verbose_name="صورة العميل")
    notes = models.TextField(blank=True, null=True, verbose_name="ملاحظات وتفاصيل إضافية")
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, db_index=True, verbose_name="رصيد الحساب (الشكك)")
    due_date = models.DateField(blank=True, null=True, db_index=True, verbose_name="موعد استحقاق السداد")
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True, db_index=True, related_name='customers', verbose_name="الشركة")
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    objects = TenantManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.tenant_id:
            from tenants.middleware import get_current_tenant
            t = get_current_tenant()
            if t:
                self.tenant = t
        super().save(*args, **kwargs)

    def _get_due_date_object(self):
        if not self.due_date:
            return None
        if isinstance(self.due_date, str):
            try:
                from datetime import datetime
                return datetime.strptime(self.due_date, '%Y-%m-%d').date()
            except ValueError:
                return None
        return self.due_date

    @property
    def is_due_today(self):
        d = self._get_due_date_object()
        if d and self.balance > 0:
            return d == timezone.now().date()
        return False

    @property
    def is_overdue(self):
        d = self._get_due_date_object()
        if d and self.balance > 0:
            return d < timezone.now().date()
        return False

    @property
    def days_overdue(self):
        d = self._get_due_date_object()
        if d and self.balance > 0:
            delta = (timezone.now().date() - d).days
            return delta if delta > 0 else 0
        return 0

    @property
    def days_until_due(self):
        d = self._get_due_date_object()
        if d and self.balance > 0:
            delta = (d - timezone.now().date()).days
            return delta if delta >= 0 else 0
        return 0

    def __str__(self):
        return f"{self.name} ({self.balance} ج.م)"


class Supplier(models.Model):
    name = models.CharField(max_length=200, db_index=True, verbose_name="اسم المورد")
    company = models.CharField(max_length=200, blank=True, null=True, verbose_name="الشركة")
    phone = models.CharField(max_length=50, blank=True, null=True, db_index=True, verbose_name="رقم الهاتف")
    address = models.CharField(max_length=200, blank=True, null=True, verbose_name="العنوان / المقر")
    avatar = models.ImageField(upload_to='suppliers/', blank=True, null=True, verbose_name="صورة المورد")
    notes = models.TextField(blank=True, null=True, verbose_name="ملاحظات وتفاصيل إضافية")
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, db_index=True, verbose_name="رصيد المورد")
    due_date = models.DateField(blank=True, null=True, db_index=True, verbose_name="موعد استحقاق السداد")
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True, db_index=True, related_name='suppliers', verbose_name="الشركة")
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    objects = TenantManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.tenant_id:
            from tenants.middleware import get_current_tenant
            t = get_current_tenant()
            if t:
                self.tenant = t
        super().save(*args, **kwargs)

    def _get_due_date_object(self):
        if not self.due_date:
            return None
        if isinstance(self.due_date, str):
            try:
                from datetime import datetime
                return datetime.strptime(self.due_date, '%Y-%m-%d').date()
            except ValueError:
                return None
        return self.due_date

    @property
    def is_due_today(self):
        d = self._get_due_date_object()
        if d and self.balance > 0:
            return d == timezone.now().date()
        return False

    @property
    def is_overdue(self):
        d = self._get_due_date_object()
        if d and self.balance > 0:
            return d < timezone.now().date()
        return False

    @property
    def days_overdue(self):
        d = self._get_due_date_object()
        if d and self.balance > 0:
            delta = (timezone.now().date() - d).days
            return delta if delta > 0 else 0
        return 0

    @property
    def days_until_due(self):
        d = self._get_due_date_object()
        if d and self.balance > 0:
            delta = (d - timezone.now().date()).days
            return delta if delta >= 0 else 0
        return 0

    def __str__(self):
        return f"{self.name} - {self.company} ({self.balance} ج.م)"


class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('sale_credit', 'فاتورة مبيعات شكك (آجل)'),
        ('purchase_credit', 'فاتورة مشتريات آجل'),
        ('pay_received', 'دفعة مستلمة من العميل'),
        ('pay_sent', 'دفعة مسددة للمورد'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, blank=True, null=True, related_name='ledger_transactions', verbose_name="العميل")
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, blank=True, null=True, related_name='ledger_transactions', verbose_name="المورد")
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="المبلغ")
    transaction_type = models.CharField(max_length=30, choices=TRANSACTION_TYPES, verbose_name="نوع المعاملة")
    notes = models.CharField(max_length=500, blank=True, default='', verbose_name="البيان / الملاحظات")
    due_date = models.DateField(blank=True, null=True, db_index=True, verbose_name="موعد استحقاق السداد")
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True, db_index=True, related_name='transactions', verbose_name="الشركة")
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
        party = self.customer.name if self.customer else (self.supplier.name if self.supplier else "N/A")
        return f"{self.get_transaction_type_display()} - {party} - {self.amount}"
