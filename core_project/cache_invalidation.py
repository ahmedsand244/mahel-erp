"""
Automatic Cache Invalidation Engine for MAHEL ERP.
Listens to post_save and post_delete signals across models to clear relevant cache keys instantly.
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache

from inventory.models import Product, Category
from ledger.models import Customer, Supplier, Transaction
from maintenance.models import MaintenanceTicket
from pos.models import Order
from tenants.models import Tenant

@receiver([post_save, post_delete], sender=Product)
def invalidate_product_caches(sender, instance, **kwargs):
    cache.clear()

@receiver([post_save, post_delete], sender=Customer)
@receiver([post_save, post_delete], sender=Supplier)
@receiver([post_save, post_delete], sender=Transaction)
def invalidate_ledger_caches(sender, instance, **kwargs):
    cache.clear()

@receiver([post_save, post_delete], sender=MaintenanceTicket)
def invalidate_maintenance_caches(sender, instance, **kwargs):
    cache.clear()

@receiver([post_save, post_delete], sender=Order)
def invalidate_pos_caches(sender, instance, **kwargs):
    cache.clear()

@receiver([post_save, post_delete], sender=Tenant)
def invalidate_tenant_caches(sender, instance, **kwargs):
    if instance.slug:
        cache.delete(f"tenant_slug_{instance.slug}")
    cache.delete(f"tenant_id_{instance.id}")
    cache.delete(f"tenant_sub_info_{instance.id}")
