from django.urls import path
from rest_framework.routers import DefaultRouter

from .overview import SavingsOverviewView
from .views import (
    MatiasFundMovementViewSet,
    MatiasFundView,
    SavingsGoalViewSet,
    SavingsMovementViewSet,
)

router = DefaultRouter()
router.register(r"families/(?P<family_pk>[^/.]+)/savings-goals", SavingsGoalViewSet, basename="savings-goal")
router.register(r"families/(?P<family_pk>[^/.]+)/savings-movements", SavingsMovementViewSet, basename="savings-movement")
router.register(r"families/(?P<family_pk>[^/.]+)/matias-fund-movements", MatiasFundMovementViewSet, basename="matias-fund-movement")

urlpatterns = [
    path("families/<int:family_pk>/savings/overview/", SavingsOverviewView.as_view(), name="savings-overview"),
    path("families/<int:family_pk>/matias-fund/", MatiasFundView.as_view(), name="matias-fund"),
] + router.urls
