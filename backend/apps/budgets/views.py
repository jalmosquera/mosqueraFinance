from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import ListCreateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.services import record_entity_mutation
from apps.families.models import Family, FamilyMembership

from .models import (
    BudgetLine,
    FreeMoneyAllowance,
    MonthlyBudgetForecast,
    SavingsDistributionRule,
)
from .serializers import (
    BudgetLineSerializer,
    FreeMoneyAllowanceSerializer,
    MonthlyBudgetForecastSerializer,
    ProjectedSavingsSerializer,
    SavingsDistributionRuleSerializer,
)
from .services import calculate_projected_savings


class FamilyScopedBudgetView:
    permission_classes = (IsAuthenticated,)

    def get_family(self):
        return get_object_or_404(Family.objects.visible_to(self.request.user), pk=self.kwargs["family_pk"])

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["family"] = self.get_family()
        return context

    def require_admin(self):
        if not FamilyMembership.objects.active_admin_for(self.request.user, self.get_family()).exists():
            raise PermissionDenied("Only family administrators can configure budgets.")


class BudgetForecastListCreateView(FamilyScopedBudgetView, ListCreateAPIView):
    serializer_class = MonthlyBudgetForecastSerializer

    def get_queryset(self):
        return MonthlyBudgetForecast.objects.filter(family=self.get_family()).prefetch_related("lines")

    @transaction.atomic
    def perform_create(self, serializer):
        self.require_admin()
        forecast = serializer.save()
        record_entity_mutation(
            actor=self.request.user,
            action="budget_forecast.created",
            family=forecast.family,
            entity_type="budget_forecast",
            entity_id=forecast.pk,
            metadata={"month": forecast.month.isoformat(), "version": forecast.version},
        )


class BudgetLineListCreateView(FamilyScopedBudgetView, ListCreateAPIView):
    serializer_class = BudgetLineSerializer

    def get_forecast(self):
        return get_object_or_404(
            MonthlyBudgetForecast.objects.filter(family=self.get_family()),
            pk=self.kwargs["forecast_pk"],
        )

    def get_queryset(self):
        return BudgetLine.objects.filter(forecast=self.get_forecast())

    @transaction.atomic
    def perform_create(self, serializer):
        self.require_admin()
        line = serializer.save(forecast=self.get_forecast())
        record_entity_mutation(
            actor=self.request.user,
            action="budget_line.created",
            family=line.forecast.family,
            entity_type="budget_line",
            entity_id=line.pk,
            metadata={"forecast_id": line.forecast_id, "kind": line.kind},
        )


class FreeMoneyAllowanceListCreateView(FamilyScopedBudgetView, ListCreateAPIView):
    serializer_class = FreeMoneyAllowanceSerializer

    def get_queryset(self):
        queryset = FreeMoneyAllowance.objects.filter(family=self.get_family())
        if not FamilyMembership.objects.active_admin_for(self.request.user, self.get_family()).exists():
            queryset = queryset.filter(owner=self.request.user)
        return queryset

    @transaction.atomic
    def perform_create(self, serializer):
        family = self.get_family()
        is_admin = FamilyMembership.objects.active_admin_for(self.request.user, family).exists()
        if not is_admin and serializer.validated_data["owner_id"] != self.request.user.pk:
            raise PermissionDenied("You can only configure your own allowance.")
        allowance = serializer.save(family=family)
        record_entity_mutation(
            actor=self.request.user,
            action="free_money_allowance.created",
            family=family,
            entity_type="free_money_allowance",
            entity_id=allowance.pk,
            metadata={"owner_id": allowance.owner_id, "effective_date": allowance.effective_date.isoformat()},
        )


class SavingsDistributionRuleListCreateView(FamilyScopedBudgetView, ListCreateAPIView):
    serializer_class = SavingsDistributionRuleSerializer

    def get_queryset(self):
        self.require_admin()
        return SavingsDistributionRule.objects.filter(family=self.get_family())

    @transaction.atomic
    def perform_create(self, serializer):
        self.require_admin()
        rule = serializer.save(family=self.get_family())
        record_entity_mutation(
            actor=self.request.user,
            action="savings_distribution_rule.created",
            family=rule.family,
            entity_type="savings_distribution_rule",
            entity_id=rule.pk,
            metadata={"effective_date": rule.effective_date.isoformat()},
        )


class ProjectedSavingsView(FamilyScopedBudgetView, APIView):
    def post(self, request, family_pk):
        self.require_admin()
        serializer = ProjectedSavingsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(calculate_projected_savings(family=self.get_family(), **serializer.validated_data))
