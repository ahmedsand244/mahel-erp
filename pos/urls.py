from django.urls import path
from .views import (
    POSView, 
    POSCheckoutAjaxView, 
    AddCustomerAjaxView,
    SalesInvoicesListView,
    OrderInvoiceDetailJsonView,
    PublicInvoiceDetailView,
    ExportInvoicesExcelView,
    SyncLocalToCloudView
)

app_name = 'pos'

urlpatterns = [
    path('', POSView.as_view(), name='pos_view'),
    path('checkout/', POSCheckoutAjaxView.as_view(), name='checkout_ajax'),
    path('add-customer-ajax/', AddCustomerAjaxView.as_view(), name='add_customer_ajax'),
    path('invoices/', SalesInvoicesListView.as_view(), name='invoices_list'),
    path('invoices/<int:pk>/json/', OrderInvoiceDetailJsonView.as_view(), name='invoice_detail_json'),
    path('invoices/<int:pk>/public/', PublicInvoiceDetailView.as_view(), name='public_invoice_detail'),
    path('invoices/export-excel/', ExportInvoicesExcelView.as_view(), name='export_invoices_excel'),
    path('sync-local-to-cloud/', SyncLocalToCloudView.as_view(), name='sync_local_to_cloud'),
]

