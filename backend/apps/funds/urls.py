from rest_framework.routers import DefaultRouter

from .views import FundViewSet

router = DefaultRouter()
router.register("funds", FundViewSet, basename="fund")
urlpatterns = router.urls
