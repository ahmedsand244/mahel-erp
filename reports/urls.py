from django.urls import path
from .views import ReportsProfitLossView, SaveAuditView

app_name = 'reports'

urlpatterns = [
    path('', ReportsProfitLossView.as_view(), name='reports_view'),
    path('save-audit/', SaveAuditView.as_view(), name='save_audit'),
]
