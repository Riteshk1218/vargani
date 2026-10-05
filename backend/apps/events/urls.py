from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("events", views.EventViewSet, basename="event")
router.register("event-participants", views.EventParticipantViewSet, basename="event-participant")

urlpatterns = [path("event-templates/", views.EventTemplateView.as_view(), name="event-templates"), *router.urls]
