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
        all_tickets = list(MaintenanceTicket.objects.select_related('customer').prefetch_related('parts_consumed__product').order_by('-created_at'))
        context['pending_tickets'] = [t for t in all_tickets if t.status == 'pending']
        context['in_progress_tickets'] = [t for t in all_tickets if t.status == 'in_progress']
        context['completed_tickets'] = [t for t in all_tickets if t.status == 'completed']
        context['delivered_tickets'] = [t for t in all_tickets if t.status == 'delivered']
        context['customers'] = Customer.objects.only('id', 'name', 'phone').all()
        context['products'] = Product.objects.only('id', 'name', 'selling_price', 'stock_quantity').filter(stock_quantity__gt=0)
        return context

    def post(self, request, *args, **kwargs):
        customer_id = request.POST.get('customer_id')
        new_customer_name = request.POST.get('new_customer_name', '').strip()
        new_customer_phone = request.POST.get('new_customer_phone', '').strip()
        device_name = request.POST.get('device_name', '').strip()
        labor_fees = request.POST.get('labor_fees') or '0.00'

        customer = None
        # 1. حالة العميل النقدي السريع
        if customer_id == 'quick' or request.POST.get('is_quick_customer') == 'true':
            customer, _ = Customer.objects.get_or_create(name='عميل نقدي / ورشة', defaults={'phone': ''})
        # 2. حالة إضافة عميل جديد من المودال
        elif new_customer_name:
            customer = Customer.objects.create(name=new_customer_name, phone=new_customer_phone)
        # 3. العميل المحدد من القائمة
        elif customer_id:
            customer = Customer.objects.filter(id=customer_id).first()

        if not customer:
            messages.error(request, "يرجى تحديد العميل أو اختيار 'عميل نقدي سريع' أو إدخال بيانات عميل جديد.")
            return redirect('maintenance:kanban')

        if not device_name:
            messages.error(request, "يرجى إدخال اسم المعدة أو الموتور بشكل صحيح.")
            return redirect('maintenance:kanban')

        try:
            import random
            import time
            ticket_number = f"MNT-{int(time.time())}-{random.randint(10, 99)}"

            t = MaintenanceTicket.objects.create(
                ticket_number=ticket_number,
                customer=customer,
                device_name=device_name,
                labor_fees=Decimal(str(labor_fees))
            )
            from dashboard.audit import log_activity
            log_activity(
                request,
                module='maintenance',
                action_type='create',
                description=f"فتح تذكرة صيانة جديدة #{t.ticket_number} للمعدة '{device_name}' (العميل: {customer.name} - مصنعية مبدئية: {labor_fees} ج.م)",
                severity='info'
            )
            messages.success(request, f"🎉 تم فتح تذكرة الصيانة #{t.ticket_number} للعميل '{customer.name}' للمعدة '{device_name}' بنجاح!")
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
            from dashboard.audit import log_activity
            log_activity(
                request,
                module='maintenance',
                action_type='status_change',
                description=f"تغيير حالة تذكرة الصيانة #{ticket.ticket_number} إلى '{ticket.get_status_display()}' (المعدة: {ticket.device_name})",
                severity='info'
            )
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
            from dashboard.audit import log_activity
            log_activity(
                request,
                module='maintenance',
                action_type='update',
                description=f"استهلاك وتركيب قطعة الغيار '{part.product.name}' (الكمية: {qty}) لتذكرة الصيانة #{ticket.ticket_number}",
                severity='info'
            )
            messages.success(request, f"تم تركيب قطعة الغيار '{part.product.name}' (الكمية: {qty}) للتذكرة #{ticket.ticket_number} بنجاح!")
        except ValueError as e:
            messages.error(request, f"فشلت عملية إضافة قطعة الغيار: {str(e)}")
        except Exception as e:
            messages.error(request, f"حدث خطأ أثناء تركيب القطعة: {str(e)}")

        return redirect('maintenance:kanban')

