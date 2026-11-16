from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.services import record_entity_mutation
from apps.families.models import Family
from apps.obligations.services import (
    preserve_historical_occurrences_before_forecast_edit,
)

from .dashboard import build_expense_dashboard
from .models import ExpenseForecast, ExpenseMovement
from .serializers import (
    CorrectExpenseMovementSerializer,
    ExpenseDashboardMonthSerializer,
    ExpenseForecastSerializer,
    ExpenseMovementSerializer,
)
from .services import correct_expense_movement, create_expense_movement


class FamilyScopedExpenseViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    entity_type = None

    def get_family(self):
        return get_object_or_404(
            Family.objects.visible_to(self.request.user), pk=self.kwargs["family_pk"]
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["family"] = self.get_family()
        return context

    def get_queryset(self):
        return self.model.objects.visible_to(self.request.user).filter(family=self.get_family())

    @transaction.atomic
    def perform_create(self, serializer):
        record = serializer.save()
        record_entity_mutation(
            actor=self.request.user,
            action=f"{self.entity_type}.created",
            family=record.family,
            entity_type=self.entity_type,
            entity_id=record.pk,
            metadata={"owner_id": record.owner_id},
        )

    @transaction.atomic
    def perform_update(self, serializer):
        if isinstance(serializer.instance, ExpenseForecast):
            preserve_historical_occurrences_before_forecast_edit(
                forecast=serializer.instance
            )
        record = serializer.save()
        record_entity_mutation(
            actor=self.request.user,
            action=f"{self.entity_type}.updated",
            family=record.family,
            entity_type=self.entity_type,
            entity_id=record.pk,
            metadata={"owner_id": record.owner_id},
        )

    @transaction.atomic
    def perform_destroy(self, instance):
        record_entity_mutation(
            actor=self.request.user,
            action=f"{self.entity_type}.deleted",
            family=instance.family,
            entity_type=self.entity_type,
            entity_id=instance.pk,
            metadata={"owner_id": instance.owner_id},
        )
        instance.delete()


class ExpenseForecastViewSet(FamilyScopedExpenseViewSet):
    model = ExpenseForecast
    serializer_class = ExpenseForecastSerializer
    entity_type = "expense_forecast"


class ExpenseMovementViewSet(FamilyScopedExpenseViewSet):
    model = ExpenseMovement
    serializer_class = ExpenseMovementSerializer
    entity_type = "expense_movement"
    http_method_names = ("get", "post", "head", "options")

    def perform_create(self, serializer):
        allocations = serializer.validated_data.pop("allocations", [])
        serializer.instance = create_expense_movement(
            actor=self.request.user,
            family=self.get_family(),
            movement_data=serializer.validated_data,
            allocations=allocations,
        )

    @action(detail=True, methods=["post"])
    def correct(self, request, *args, **kwargs):
        movement = self.get_object()
        serializer = CorrectExpenseMovementSerializer(
            data=request.data, context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)
        try:
            replacement_data = serializer.validated_data.copy()
            reason = replacement_data.pop("reason")
            allocations = replacement_data.pop("allocations", [])
            reversal, replacement = correct_expense_movement(
                actor=request.user,
                movement=movement,
                reason=reason,
                movement_data=replacement_data,
                allocations=allocations,
            )
        except DjangoValidationError as error:
            raise ValidationError(error.messages) from error
        return Response(
            {
                "reversal": self.get_serializer(reversal).data,
                "replacement": self.get_serializer(replacement).data,
            },
            status=status.HTTP_201_CREATED,
        )


class ExpenseDashboardView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, family_pk):
        family = get_object_or_404(Family.objects.visible_to(request.user), pk=family_pk)
        serializer = ExpenseDashboardMonthSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return Response(
            build_expense_dashboard(
                family=family,
                user=request.user,
                month=serializer.validated_data["month"],
            )
        )
