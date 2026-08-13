from django.urls import path
from .views import (
    LedgerListView, CollectPaymentView, PaySupplierView,
    AddCustomerSupplierView, AddCustomerDebtView, AddSupplierDebtView,
    CustomerDetailView, SupplierDetailView, UpdateCustomerProfileView, UpdateSupplierProfileView,
    PublicCustomerLedgerView, ExportCustomersExcelView, ExportSuppliersExcelView
)

app_name = 'ledger'

urlpatterns = [
    path('', LedgerListView.as_view(), name='ledger_list'),
    path('collect-payment/', CollectPaymentView.as_view(), name='collect_payment'),
    path('pay-supplier/', PaySupplierView.as_view(), name='pay_supplier'),
    path('add-party/', AddCustomerSupplierView.as_view(), name='add_party'),
    path('add-customer-debt/<int:pk>/', AddCustomerDebtView.as_view(), name='add_customer_debt'),
    path('add-supplier-debt/<int:pk>/', AddSupplierDebtView.as_view(), name='add_supplier_debt'),
    path('customer/<int:pk>/', CustomerDetailView.as_view(), name='customer_detail'),
    path('supplier/<int:pk>/', SupplierDetailView.as_view(), name='supplier_detail'),
    path('customer/<int:pk>/public/', PublicCustomerLedgerView.as_view(), name='public_customer_ledger'),
    path('customer/<int:pk>/update-profile/', UpdateCustomerProfileView.as_view(), name='update_customer_profile'),
    path('supplier/<int:pk>/update-profile/', UpdateSupplierProfileView.as_view(), name='update_supplier_profile'),
    # Excel Exports
    path('export-customers/', ExportCustomersExcelView.as_view(), name='export_customers_excel'),
    path('export-suppliers/', ExportSuppliersExcelView.as_view(), name='export_suppliers_excel'),
]

