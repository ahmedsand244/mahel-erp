from django.urls import path
from .views import MaintenanceKanbanView, UpdateTicketStatusView, AddPartsToTicketView

app_name = 'maintenance'

urlpatterns = [
    path('', MaintenanceKanbanView.as_view(), name='kanban'),
    path('update-status/<int:pk>/', UpdateTicketStatusView.as_view(), name='update_status'),
    path('add-parts/<int:pk>/', AddPartsToTicketView.as_view(), name='add_parts'),
]
