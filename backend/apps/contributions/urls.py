from django.urls import path
from rest_framework.routers import DefaultRouter

from .collector_views import CollectorAssignmentViewSet, CollectorPerformanceView, MyCollectorDashboardView
from .views import ContributionTypeViewSet, ContributionViewSet, DueViewSet

router = DefaultRouter()
router.register("contribution-types", ContributionTypeViewSet, basename="contribution-type")
router.register("contributions", ContributionViewSet, basename="contribution")
router.register("dues", DueViewSet, basename="due")
router.register("collector-assignments", CollectorAssignmentViewSet, basename="collector-assignment")

urlpatterns = [
    path("collectors/", CollectorPerformanceView.as_view(), name="collectors"),
    path("collectors/me/dashboard/", MyCollectorDashboardView.as_view(), name="collector-dashboard"),
    *router.urls,
]
