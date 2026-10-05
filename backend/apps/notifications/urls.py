from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import AnnouncementView, DeviceRegisterView, DeviceUnregisterView, NotificationViewSet

router = DefaultRouter()
router.register("notifications", NotificationViewSet, basename="notification")

urlpatterns = [
    path("announcements/", AnnouncementView.as_view(), name="announcements"),
    path("devices/", DeviceRegisterView.as_view(), name="device-register"),
    path("devices/unregister/", DeviceUnregisterView.as_view(), name="device-unregister"),
    *router.urls,
]
