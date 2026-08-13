from django.contrib import admin
from .models import MaintenanceTicket, TicketPartConsumption

class TicketPartConsumptionInline(admin.TabularInline):
    model = TicketPartConsumption
    extra = 0

@admin.register(MaintenanceTicket)
class MaintenanceTicketAdmin(admin.ModelAdmin):
    list_display = ('ticket_number', 'customer', 'device_name', 'status', 'labor_fees', 'parts_cost', 'parts_sell', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('ticket_number', 'customer__name', 'device_name')
    inlines = [TicketPartConsumptionInline]
