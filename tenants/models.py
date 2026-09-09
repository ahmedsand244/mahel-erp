from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Tenant(models.Model):
    """
    يمثل شركة/مؤسسة واحدة في النظام SaaS.
    كل البيانات (مخزن، عملاء، فواتير...) مرتبطة بـ Tenant.
    """
    PLAN_CHOICES = [
        ('trial', 'تجربة مجانية'),
        ('basic', 'الباقة الأساسية'),
        ('pro',   'الباقة الاحترافية'),
    ]

    name          = models.CharField(max_length=200, verbose_name="اسم الشركة / المؤسسة")
    slug          = models.SlugField(max_length=100, unique=True, verbose_name="معرف النظام (URL)")
    owner         = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_tenants', verbose_name="المالك")
    plan          = models.CharField(max_length=20, choices=PLAN_CHOICES, default='trial', verbose_name="الباقة")
    trial_ends_at = models.DateTimeField(null=True, blank=True, verbose_name="نهاية فترة التجربة")
    is_active     = models.BooleanField(default=True, verbose_name="مفعّل")
    phone         = models.CharField(max_length=50, blank=True, null=True, verbose_name="هاتف التواصل")
    address       = models.CharField(max_length=255, blank=True, null=True, verbose_name="العنوان")
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "شركة / مؤسسة"
        verbose_name_plural = "الشركات والمؤسسات"

    def __str__(self):
        return f"{self.name} ({self.slug})"

    @property
    def is_trial_expired(self):
        if self.plan == 'trial' and self.trial_ends_at:
            return timezone.now() > self.trial_ends_at
        return False

    @property
    def is_subscription_expired(self):
        if not self.is_active:
            return True
        if self.trial_ends_at:
            return timezone.now() > self.trial_ends_at
        return False

    @property
    def base_url(self):
        return f"/t/{self.slug}"


class TenantUser(models.Model):
    """ربط المستخدمين بالشركات — مستخدم واحد ممكن يكون في أكتر من شركة."""
    ROLE_CHOICES = [
        ('admin',    'مسؤول النظام'),
        ('manager',  'مدير'),
        ('cashier',  'كاشير / موظف مبيعات'),
        ('viewer',   'مشاهد فقط'),
    ]
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='members')
    user   = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tenant_memberships')
    role   = models.CharField(max_length=20, choices=ROLE_CHOICES, default='cashier')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('tenant', 'user')

    def __str__(self):
        return f"{self.user.username} @ {self.tenant.slug} ({self.role})"


class UserSocialAuth(models.Model):
    """
    ربط المستخدم بحساب Google OAuth 2.0.
    يدعم:
    1. ربط الحسابات الحالية من الإعدادات.
    2. الربط التلقائي عبر البريد الإلكتروني عند تسجيل الدخول.
    3. منع ربط نفس حساب Google بأكثر من مستخدم محلي.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='social_auths', verbose_name="المستخدم")
    google_id = models.CharField(max_length=255, unique=True, null=True, blank=True, verbose_name="Google Sub/ID")
    google_email = models.EmailField(null=True, blank=True, verbose_name="البريد الإلكتروني لحساب Google")
    linked_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الربط")

    class Meta:
        verbose_name = "ربط حساب اجتماعي"
        verbose_name_plural = "ربط الحسابات الاجتماعية"

    def __str__(self):
        return f"{self.user.username} 🔗 Google ({self.google_email or self.google_id})"

