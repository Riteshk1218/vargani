from django.urls import path

from .auth_views import MemberOTPRequestView, MemberOTPVerifyView
from .views import (
    PortalMeView,
    PortalPaymentsView,
    PortalReceiptDetailView,
    PortalReceiptPdfView,
    PortalReceiptsView,
    PortalSummaryView,
)

urlpatterns = [
    path("auth/otp/request/", MemberOTPRequestView.as_view(), name="auth-otp-request"),
    path("auth/otp/verify/", MemberOTPVerifyView.as_view(), name="auth-otp-verify"),
    path("portal/me/", PortalMeView.as_view(), name="portal-me"),
    path("portal/summary/", PortalSummaryView.as_view(), name="portal-summary"),
    path("portal/payments/", PortalPaymentsView.as_view(), name="portal-payments"),
    path("portal/receipts/", PortalReceiptsView.as_view(), name="portal-receipts"),
    path("portal/receipts/<uuid:pk>/", PortalReceiptDetailView.as_view(), name="portal-receipt"),
    path("portal/receipts/<uuid:pk>/pdf/", PortalReceiptPdfView.as_view(), name="portal-receipt-pdf"),
]
