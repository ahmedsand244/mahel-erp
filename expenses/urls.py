from django.urls import path
from .views import ExpenseListView, ExpenseCreateView, ExpenseDeleteView

app_name = 'expenses'

urlpatterns = [
    path('', ExpenseListView.as_view(), name='expense_list'),
    path('add/', ExpenseCreateView.as_view(), name='expense_add'),
    path('delete/<int:pk>/', ExpenseDeleteView.as_view(), name='expense_delete'),
]
