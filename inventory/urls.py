from django.urls import path
from .views import (
    InventoryListView, ProductCreateView, ProductUpdateView,
    ProductDeleteView, QuickRestockView, BulkPriceAdjustmentView, SingleProductPriceAdjustmentView,
    PurchaseOrderListView, PurchaseOrderBuilderView, PurchaseOrderDetailView, PurchaseOrderReceiveView, PurchaseOrderDeleteView,
    ExportProductsExcelView, DownloadSampleProductsExcelView, ImportProductsExcelView, BarcodeGeneratorView,
    CategoryCreateView, CategoryDeleteView
)

app_name = 'inventory'

urlpatterns = [
    path('', InventoryListView.as_view(), name='inventory_list'),
    path('add/', ProductCreateView.as_view(), name='product_add'),
    path('update/<int:pk>/', ProductUpdateView.as_view(), name='product_update'),
    path('delete/<int:pk>/', ProductDeleteView.as_view(), name='product_delete'),
    path('restock/<int:pk>/', QuickRestockView.as_view(), name='quick_restock'),
    path('bulk-price-adjust/', BulkPriceAdjustmentView.as_view(), name='bulk_price_adjust'),
    path('single-price-adjust/<int:pk>/', SingleProductPriceAdjustmentView.as_view(), name='single_price_adjust'),
    # Barcode Label Generator
    path('barcode-generator/', BarcodeGeneratorView.as_view(), name='barcode_generator'),
    # Excel Import / Export
    path('export-excel/', ExportProductsExcelView.as_view(), name='export_excel'),
    path('sample-excel/', DownloadSampleProductsExcelView.as_view(), name='sample_excel'),
    path('import-excel/', ImportProductsExcelView.as_view(), name='import_excel'),
    # Purchase Orders & Requisitions
    path('orders/', PurchaseOrderListView.as_view(), name='purchase_order_list'),
    path('orders/new/', PurchaseOrderBuilderView.as_view(), name='purchase_order_create'),
    path('orders/edit/<int:pk>/', PurchaseOrderBuilderView.as_view(), name='purchase_order_edit'),
    path('orders/<int:pk>/', PurchaseOrderDetailView.as_view(), name='purchase_order_detail'),
    path('orders/<int:pk>/receive/', PurchaseOrderReceiveView.as_view(), name='purchase_order_receive'),
    path('orders/<int:pk>/delete/', PurchaseOrderDeleteView.as_view(), name='purchase_order_delete'),
    # Categories Management
    path('categories/add/', CategoryCreateView.as_view(), name='category_add'),
    path('categories/delete/<int:pk>/', CategoryDeleteView.as_view(), name='category_delete'),
]

