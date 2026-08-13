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
        messages.success(self.request, f"تم تسجيل المصروف '{form.instance.description}' بمبلغ {form.instance.amount} ج.م بنجاح!")
        return super().form_valid(form)

    def form_invalid(self, form):
        error_msg = "; ".join([f"{', '.join(errs)}" for field, errs in form.errors.items()])
        messages.error(self.request, f"خطأ أثناء تسجيل المصروف: {error_msg}")
        return redirect('expenses:expense_list')


class ExpenseDeleteView(View):
    def post(self, request, pk, *args, **kwargs):
        expense = get_object_or_404(Expense, pk=pk)
        desc = expense.description
        expense.delete()
        messages.success(request, f"تم حذف بند المصروف '{desc}' بنجاح.")
        return redirect('expenses:expense_list')
