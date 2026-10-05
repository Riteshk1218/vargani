from rest_framework.routers import DefaultRouter

from .views import ContributionTypeViewSet, ContributionViewSet

router = DefaultRouter()
router.register("contribution-types", ContributionTypeViewSet, basename="contribution-type")
router.register("contributions", ContributionViewSet, basename="contribution")
urlpatterns = router.urls
