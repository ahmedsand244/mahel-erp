from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, View
from django.http import JsonResponse
from django.contrib import messages
from decimal import Decimal
from .models import MaintenanceTicket, TicketPartConsumption
from ledger.models import Customer
from inventory.models import Product
from core_project.services import add_maintenance_part

class MaintenanceKanbanView(ListView):
    model = MaintenanceTicket
    template_name = "maintenance.html"
    context_object_name = "tickets"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tickets = MaintenanceTicket.objects.select_related('customer').prefetch_related('parts_consumed__product')
        context['pending_tickets'] = tickets.filter(status='pending')
        context['in_progress_tickets'] = tickets.filter(status='in_progress')
        context['completed_tickets'] = tickets.filter(status='completed')
        context['delivered_tickets'] = tickets.filter(status='delivered')
        context['customers'] = Customer.objects.all()
        context['products'] = Product.objects.filter(stock_quantity__gt=0)
        return context

    def post(self, request, *args, **kwargs):
        customer_id = request.POST.get('customer_id')
        device_name = request.POST.get('device_name')
        labor_fees = request.POST.get('labor_fees') or '0.00'

        if not customer_id or not device_name:
            messages.error(request, "يرجى تحديد العميل وإدخال اسم المعدة بشكل صحيح.")
            return redirect('maintenance:kanban')

        try:
            customer = get_object_or_404(Customer, id=customer_id)
            import random
            import time
            ticket_number = f"MNT-{int(time.time())}-{random.randint(10, 99)}"

            t = MaintenanceTicket.objects.create(
                ticket_number=ticket_number,
                customer=customer,
                device_name=device_name,
                labor_fees=Decimal(str(labor_fees))
            )
            messages.success(request, f"تم فتح تذكرة الصيانة #{t.ticket_number} للمعدة '{device_name}' بنجاح!")
        except Exception as e:
            messages.error(request, f"خطأ أثناء فتح تذكرة الصيانة: {str(e)}")

        return redirect('maintenance:kanban')


class UpdateTicketStatusView(View):
    def post(self, request, pk, *args, **kwargs):
        ticket = get_object_or_404(MaintenanceTicket, pk=pk)
        new_status = request.POST.get('status')
        if new_status in dict(MaintenanceTicket.STATUS_CHOICES):
            ticket.status = new_status
            ticket.save()
            messages.success(request, f"تم تحديث حالة التذكرة #{ticket.ticket_number} إلى '{ticket.get_status_display()}'")
            return JsonResponse({'success': True})
        return JsonResponse({'success': False, 'error': 'حالة غير صحيحة'}, status=400)


class AddPartsToTicketView(View):
    def post(self, request, pk, *args, **kwargs):
        ticket = get_object_or_404(MaintenanceTicket, pk=pk)
        product_id = request.POST.get('product_id')
        qty = int(request.POST.get('quantity', 1))

        try:
            part = add_maintenance_part(ticket.id, product_id, qty)
            messages.success(request, f"تم تركيب قطعة الغيار '{part.product.name}' (الكمية: {qty}) للتذكرة #{ticket.ticket_number} بنجاح!")
        except ValueError as e:
            messages.error(request, f"فشلت عملية إضافة قطعة الغيار: {str(e)}")
        except Exception as e:
            messages.error(request, f"حدث خطأ أثناء تركيب القطعة: {str(e)}")

        return redirect('maintenance:kanban')
