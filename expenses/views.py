from django.shortcuts import redirect, get_object_or_404
from django.views.generic import ListView, CreateView, View
from django.urls import reverse_lazy
from django.contrib import messages
from decimal import Decimal
from .models import Expense

class ExpenseListView(ListView):
    model = Expense
    template_name = "expenses.html"
    context_object_name = "expenses"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category_choices'] = Expense.CATEGORY_CHOICES
        return context


class ExpenseCreateView(CreateView):
    model = Expense
    fields = ['category', 'description', 'amount']
    template_name = "expenses.html"
    success_url = reverse_lazy('expenses:expense_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        from dashboard.audit import log_activity
        log_activity(
            self.request,
            module='expenses',
            action_type='create',
            description=f"تسجيل مصروف جديد: '{form.instance.description}' بقيمة {form.instance.amount:,.2f} ج.م ({form.instance.get_category_display()})",
            severity='info'
        )
        messages.success(self.request, f"تم تسجيل المصروف '{form.instance.description}' بمبلغ {form.instance.amount} ج.م بنجاح!")
        return response

    def form_invalid(self, form):
        error_msg = "; ".join([f"{', '.join(errs)}" for field, errs in form.errors.items()])
        messages.error(self.request, f"خطأ أثناء تسجيل المصروف: {error_msg}")
        return redirect('expenses:expense_list')


class ExpenseDeleteView(View):
    def post(self, request, pk, *args, **kwargs):
        expense = get_object_or_404(Expense, pk=pk)
        desc = expense.description
        amount = expense.amount
        cat = expense.get_category_display()
        expense.delete()
        from dashboard.audit import log_activity
        log_activity(
            request,
            module='expenses',
            action_type='delete',
            description=f"حذف بند المصروف '{desc}' بقيمة {amount:,.2f} ج.م ({cat})",
            severity='danger'
        )
        messages.success(request, f"تم حذف بند المصروف '{desc}' بنجاح.")
        return redirect('expenses:expense_list')

