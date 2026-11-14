from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.families.models import Family

from .models import PaymentObligation
from .serializers import (
    MonthSerializer,
    PaymentObligationSerializer,
    SettleObligationSerializer,
    VoidObligationSerializer,
)
from .services import materialize_family_occurrences, settle_obligation, void_obligation


class PaymentObligationViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = (IsAuthenticated,)
    serializer_class = PaymentObligationSerializer

    def get_family(self):
        return get_object_or_404(
            Family.objects.visible_to(self.request.user), pk=self.kwargs["family_pk"]
        )

    def get_queryset(self):
        return PaymentObligation.objects.visible_to(self.request.user).filter(family=self.get_family())

    def _month(self, request):
        serializer = MonthSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data["month"]

    def list(self, request, *args, **kwargs):
        month = self._month(request)
        queryset = self.filter_queryset(self.get_queryset()).filter(
            source_period=month
        )
        return Response(self.get_serializer(queryset, many=True).data)

    @action(detail=False, methods=["post"])
    def generate(self, request, *args, **kwargs):
        serializer = MonthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        month = serializer.validated_data["month"]
        materialize_family_occurrences(
            family=self.get_family(), user=request.user, start=month, end=month
        )
        queryset = self.get_queryset().filter(source_period=month)
        return Response(self.get_serializer(queryset, many=True).data)

    @action(detail=True, methods=["post"])
    def settle(self, request, *args, **kwargs):
        obligation = self.get_object()
        serializer = SettleObligationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            obligation = settle_obligation(
                actor=request.user,
                obligation=obligation,
                allocations=serializer.validated_data.get("allocations"),
            )
        except DjangoValidationError as error:
            raise ValidationError(error.message_dict if hasattr(error, "message_dict") else error.messages) from error
        return Response(self.get_serializer(obligation).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def void(self, request, *args, **kwargs):
        obligation = self.get_object()
        serializer = VoidObligationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            obligation = void_obligation(
                actor=request.user, obligation=obligation, reason=serializer.validated_data["reason"]
            )
        except DjangoValidationError as error:
            raise ValidationError(error.messages) from error
        return Response(self.get_serializer(obligation).data, status=status.HTTP_200_OK)
