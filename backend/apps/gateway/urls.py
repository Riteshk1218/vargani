from django.urls import path

from .views import GatewayConfigView, PortalPayVerifyView, PortalPayView, razorpay_webhook

urlpatterns = [
    path("gateway/config/", GatewayConfigView.as_view(), name="gateway-config"),
    path("portal/pay/", PortalPayView.as_view(), name="portal-pay"),
    path("portal/pay/verify/", PortalPayVerifyView.as_view(), name="portal-pay-verify"),
    path("webhooks/razorpay/<uuid:org_id>/", razorpay_webhook, name="webhook-razorpay"),
]
