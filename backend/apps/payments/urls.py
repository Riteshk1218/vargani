from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import PaymentViewSet

router = DefaultRouter()
router.register("payments", PaymentViewSet, basename="payment")

urlpatterns = [
    # The karyakarta flow: same service and rules as POST /payments/.
    path("collections/", PaymentViewSet.as_view({"post": "create"}), name="collections"),
    *router.urls,
]
