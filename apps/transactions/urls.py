"""
URL routes for transactions app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TransactionViewSet, TransactionCategoryView

router = DefaultRouter()
router.register(r'transactions', TransactionViewSet, basename='transaction')

urlpatterns = [
    path('transactions/categories/', TransactionCategoryView.as_view(), name='transaction_categories'),
    path('', include(router.urls)),
]
