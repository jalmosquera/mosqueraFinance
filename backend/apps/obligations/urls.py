from rest_framework.routers import DefaultRouter

from .views import PaymentObligationViewSet

router = DefaultRouter()
router.register(
    r"families/(?P<family_pk>[^/.]+)/payment-obligations",
    PaymentObligationViewSet,
    basename="payment-obligation",
)

urlpatterns = router.urls
