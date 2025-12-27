"""
URL routes for reports app.
"""
from django.urls import path
from .views import DashboardSummaryView, IncomeExpenseReportView

urlpatterns = [
    path('reports/summary/', DashboardSummaryView.as_view(), name='dashboard_summary'),
    path('reports/income-expense/', IncomeExpenseReportView.as_view(), name='income_expense_report'),
]
