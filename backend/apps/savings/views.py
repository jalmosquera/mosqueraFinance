from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.audit.services import record_entity_mutation
from apps.families.models import Family, FamilyMembership

from .models import MatiasFund, MatiasFundMovement, SavingsGoal, SavingsMovement
from .serializers import (
    MatiasFundCorrectionSerializer,
    MatiasFundMovementSerializer,
    MatiasFundSerializer,
    SavingsCorrectionSerializer,
    SavingsGoalSerializer,
    SavingsMovementSerializer,
    SimulationSerializer,
    VoidSerializer,
)
from .services import (
    correct_matias_fund_movement,
    correct_savings_movement,
    create_matias_fund_movement,
    void_matias_fund_movement,
    void_savings_movement,
)


class FamilyScopedViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)

    def get_family(self):
        return get_object_or_404(Family.objects.visible_to(self.request.user), pk=self.kwargs["family_pk"])

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["family"] = self.get_family()
        return context


class SavingsGoalViewSet(FamilyScopedViewSet):
    serializer_class = SavingsGoalSerializer

    def get_queryset(self):
        return SavingsGoal.objects.visible_to(self.request.user).filter(family=self.get_family())

    @transaction.atomic
    def perform_create(self, serializer):
        goal = serializer.save(family=self.get_family())
        record_entity_mutation(
            actor=self.request.user,
            action="savings_goal.created",
            family=goal.family,
            entity_type="savings_goal",
            entity_id=goal.pk,
            metadata={"owner_id": goal.owner_id},
        )

    @transaction.atomic
    def perform_update(self, serializer):
        goal = serializer.save()
        record_entity_mutation(
            actor=self.request.user,
            action="savings_goal.updated",
            family=goal.family,
            entity_type="savings_goal",
            entity_id=goal.pk,
            metadata={"owner_id": goal.owner_id},
        )

    @action(detail=True, methods=["post"])
    def simulate(self, request, *args, **kwargs):
        goal = self.get_object()
        serializer = SimulationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        monthly = serializer.validated_data["projected_monthly_contribution"]
        months = serializer.validated_data["months"]
        projected_balance = goal.real_balance + (monthly * months)
        return Response(
            {
                "goal_id": goal.pk,
                "real_balance": goal.real_balance,
                "projected_monthly_contribution": monthly,
                "months": months,
                "simulated_balance": projected_balance,
                "remaining_to_target": max(Decimal("0.00"), goal.target_amount - projected_balance),
            }
        )


class SavingsMovementViewSet(FamilyScopedViewSet):
    serializer_class = SavingsMovementSerializer
    http_method_names = ("get", "post", "head", "options")

    def get_queryset(self):
        return SavingsMovement.objects.filter(goal__in=SavingsGoal.objects.visible_to(self.request.user).filter(family=self.get_family()))

    @transaction.atomic
    def perform_create(self, serializer):
        movement = serializer.save()
        record_entity_mutation(
            actor=self.request.user,
            action="savings_movement.created",
            family=movement.goal.family,
            entity_type="savings_movement",
            entity_id=movement.pk,
            metadata={"goal_id": movement.goal_id, "kind": movement.kind},
        )

    @action(detail=True, methods=["post"])
    def void(self, request, *args, **kwargs):
        serializer = VoidSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            movement = void_savings_movement(actor=request.user, movement=self.get_object(), reason=serializer.validated_data["reason"])
        except DjangoValidationError as error:
            raise ValidationError(error.messages) from error
        return Response(self.get_serializer(movement).data)

    @action(detail=True, methods=["post"])
    def correct(self, request, *args, **kwargs):
        serializer = SavingsCorrectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data.copy()
        reason = data.pop("reason")
        try:
            movement = correct_savings_movement(actor=request.user, movement=self.get_object(), reason=reason, replacement_data=data)
        except DjangoValidationError as error:
            raise ValidationError(error.messages) from error
        return Response(self.get_serializer(movement).data, status=status.HTTP_201_CREATED)


class MatiasFundView(RetrieveUpdateAPIView):
    serializer_class = MatiasFundSerializer
    permission_classes = (IsAuthenticated,)

    def get_family(self):
        return get_object_or_404(Family.objects.visible_to(self.request.user), pk=self.kwargs["family_pk"])

    def get_object(self):
        return get_object_or_404(MatiasFund, family=self.get_family())

    def _require_admin(self):
        if not FamilyMembership.objects.active_admin_for(self.request.user, self.get_family()).exists():
            raise PermissionDenied("Only family administrators can configure the Matias fund.")

    def update(self, request, *args, **kwargs):
        self._require_admin()
        return super().update(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self._require_admin()
        if MatiasFund.objects.filter(family=self.get_family()).exists():
            raise ValidationError("The family already has a Matias fund.")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        fund = serializer.save(family=self.get_family())
        record_entity_mutation(
            actor=request.user,
            action="matias_fund.created",
            family=fund.family,
            entity_type="matias_fund",
            entity_id=fund.pk,
            metadata={"target_amount": str(fund.target_amount)},
        )
        return Response(self.get_serializer(fund).data, status=status.HTTP_201_CREATED)


class MatiasFundMovementViewSet(FamilyScopedViewSet):
    serializer_class = MatiasFundMovementSerializer
    http_method_names = ("get", "post", "head", "options")

    def get_fund(self):
        return get_object_or_404(MatiasFund, family=self.get_family())

    def get_queryset(self):
        return MatiasFundMovement.objects.filter(fund=self.get_fund()).prefetch_related("allocations")

    @transaction.atomic
    def perform_create(self, serializer):
        allocations = serializer.validated_data.pop("allocations")
        serializer.instance = create_matias_fund_movement(
            actor=self.request.user,
            fund=self.get_fund(),
            movement_data=serializer.validated_data,
            allocations=allocations,
        )

    @action(detail=True, methods=["post"])
    def void(self, request, *args, **kwargs):
        serializer = VoidSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            movement = void_matias_fund_movement(actor=request.user, movement=self.get_object(), reason=serializer.validated_data["reason"])
        except DjangoValidationError as error:
            raise ValidationError(error.messages) from error
        return Response(self.get_serializer(movement).data)

    @action(detail=True, methods=["post"])
    def correct(self, request, *args, **kwargs):
        serializer = MatiasFundCorrectionSerializer(data=request.data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data.copy()
        reason = data.pop("reason")
        allocations = data.pop("allocations")
        try:
            movement = correct_matias_fund_movement(actor=request.user, movement=self.get_object(), reason=reason, replacement_data=data, allocations=allocations)
        except DjangoValidationError as error:
            raise ValidationError(error.messages) from error
        return Response(self.get_serializer(movement).data, status=status.HTTP_201_CREATED)
