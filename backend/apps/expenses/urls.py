from rest_framework.routers import DefaultRouter

from .views import ExpenseForecastViewSet, ExpenseMovementViewSet

router = DefaultRouter()
router.register(
    r"families/(?P<family_pk>[^/.]+)/expense-forecasts",
    ExpenseForecastViewSet,
    basename="expense-forecast",
)
router.register(
    r"families/(?P<family_pk>[^/.]+)/expense-movements",
    ExpenseMovementViewSet,
    basename="expense-movement",
)

urlpatterns = router.urls
