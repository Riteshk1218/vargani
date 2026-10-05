from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import PublicReceiptPdfView, PublicReceiptView, ReceiptViewSet, ReceiptVoidRequestViewSet

router = DefaultRouter()
router.register("receipts", ReceiptViewSet, basename="receipt")
router.register("receipt-void-requests", ReceiptVoidRequestViewSet, basename="receipt-void-request")

urlpatterns = [
    path("public/receipts/<str:token>/", PublicReceiptView.as_view(), name="public-receipt"),
    path("public/receipts/<str:token>/pdf/", PublicReceiptPdfView.as_view(), name="public-receipt-pdf"),
    *router.urls,
]
