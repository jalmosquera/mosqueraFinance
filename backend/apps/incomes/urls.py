from rest_framework.routers import DefaultRouter

from .views import IncomeForecastViewSet, IncomeMovementViewSet

router = DefaultRouter()
router.register(
    r"families/(?P<family_pk>[^/.]+)/income-forecasts",
    IncomeForecastViewSet,
    basename="income-forecast",
)
router.register(
    r"families/(?P<family_pk>[^/.]+)/income-movements",
    IncomeMovementViewSet,
    basename="income-movement",
)

urlpatterns = router.urls
