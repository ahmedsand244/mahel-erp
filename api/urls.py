from django.urls import path
from api.views import (
    ApiLoginView,
    ApiProductsView,
    ApiCustomersView,
    ApiInvoiceSyncView,
    ApiDashboardSummaryView,
    ApiFullSyncView,
    DesktopSyncAllToCloudView
)

urlpatterns = [
    path('login/', ApiLoginView.as_view(), name='api_login'),
    path('products/', ApiProductsView.as_view(), name='api_products'),
    path('customers/', ApiCustomersView.as_view(), name='api_customers'),
    path('invoices/sync/', ApiInvoiceSyncView.as_view(), name='api_invoice_sync'),
    path('dashboard/', ApiDashboardSummaryView.as_view(), name='api_dashboard'),
    path('sync/full/', ApiFullSyncView.as_view(), name='api_full_sync'),
    path('desktop/sync-all/', DesktopSyncAllToCloudView.as_view(), name='desktop_sync_all'),
]
