from django.contrib import admin
from tenants.models import Tenant, TenantUser


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display  = ('name', 'slug', 'owner', 'plan', 'is_active', 'created_at')
    list_filter   = ('plan', 'is_active')
    search_fields = ('name', 'slug', 'owner__username')
    readonly_fields = ('created_at',)
    list_editable   = ('plan', 'is_active')


@admin.register(TenantUser)
class TenantUserAdmin(admin.ModelAdmin):
    list_display  = ('user', 'tenant', 'role', 'joined_at')
    list_filter   = ('role', 'tenant')
    search_fields = ('user__username', 'tenant__name')
