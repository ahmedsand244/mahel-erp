from django.contrib import admin
from .models import Product, StockAlert

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'barcode', 'purchase_price', 'selling_price', 'stock_quantity', 'min_stock_threshold')
    search_fields = ('name', 'sku', 'barcode')
    list_filter = ('min_stock_threshold',)

@admin.register(StockAlert)
class StockAlertAdmin(admin.ModelAdmin):
    list_display = ('product', 'message', 'is_resolved', 'created_at')
    list_filter = ('is_resolved', 'created_at')
    search_fields = ('product__name',)
