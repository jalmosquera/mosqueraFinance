from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ExpenseDashboardView, ExpenseForecastViewSet, ExpenseMovementViewSet

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

urlpatterns = [
    path(
        "families/<int:family_pk>/expenses/dashboard/",
        ExpenseDashboardView.as_view(),
        name="expense-dashboard",
    ),
] + router.urls
