from rest_framework.routers import DefaultRouter

from .views import ExpenseCategoryViewSet, ExpenseViewSet, OtherIncomeViewSet

router = DefaultRouter()
router.register("expense-categories", ExpenseCategoryViewSet, basename="expense-category")
router.register("expenses", ExpenseViewSet, basename="expense")
router.register("other-income", OtherIncomeViewSet, basename="other-income")

urlpatterns = router.urls
