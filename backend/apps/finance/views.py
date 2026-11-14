from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.generics import ListCreateAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated

from apps.audit.services import record_entity_mutation
from apps.families.models import Family

from .models import Category, LogicalAccount
from .serializers import CategorySerializer, LogicalAccountSerializer


class FamilyScopedView:
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


class LogicalAccountListCreateView(FamilyScopedView, ListCreateAPIView):
    serializer_class = LogicalAccountSerializer
    entity_type = "logical_account"

    def get_queryset(self):
        return LogicalAccount.objects.visible_to(self.request.user).filter(
            family=self.get_family()
        )


class LogicalAccountDetailView(FamilyScopedView, RetrieveAPIView):
    serializer_class = LogicalAccountSerializer

    def get_queryset(self):
        return LogicalAccount.objects.visible_to(self.request.user).filter(
            family=self.get_family()
        )


class CategoryListCreateView(FamilyScopedView, ListCreateAPIView):
    serializer_class = CategorySerializer
    entity_type = "category"

    def get_queryset(self):
        return Category.objects.visible_to(self.request.user).filter(
            family=self.get_family()
        )


class CategoryDetailView(FamilyScopedView, RetrieveAPIView):
    serializer_class = CategorySerializer

    def get_queryset(self):
        return Category.objects.visible_to(self.request.user).filter(family=self.get_family())
