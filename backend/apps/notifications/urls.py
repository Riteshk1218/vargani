from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import AnnouncementView, NotificationViewSet

router = DefaultRouter()
router.register("notifications", NotificationViewSet, basename="notification")

urlpatterns = [path("announcements/", AnnouncementView.as_view(), name="announcements"), *router.urls]
