from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.audit.services import record_entity_mutation
from apps.families.models import Family

from .models import ExpenseForecast, ExpenseMovement
from .serializers import (
    ExpenseForecastSerializer,
    ExpenseMovementSerializer,
    VoidMovementSerializer,
)
from .services import create_expense_movement, void_expense_movement


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
    def void(self, request, *args, **kwargs):
        movement = self.get_object()
        serializer = VoidMovementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            movement = void_expense_movement(
                actor=request.user, movement=movement, reason=serializer.validated_data["reason"]
            )
        except DjangoValidationError as error:
            raise ValidationError(error.messages) from error
        return Response(self.get_serializer(movement).data, status=status.HTTP_200_OK)
