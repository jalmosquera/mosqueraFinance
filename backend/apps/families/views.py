from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User

from .initial_forecast_serializers import InitialForecastConfigurationSerializer
from .initial_forecast_services import configure_initial_forecasts
from .models import Family, FamilyMembership
from .serializers import (
    FamilyMembershipSerializer,
    FamilySerializer,
    MembershipCreateSerializer,
    MembershipUpdateSerializer,
)
from .services import create_membership, delete_membership, update_membership


class FamilyListView(ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = FamilySerializer

    def get_queryset(self):
        return Family.objects.visible_to(self.request.user)


class FamilyDetailView(RetrieveAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = FamilySerializer

    def get_queryset(self):
        return Family.objects.visible_to(self.request.user)


class FamilyMembershipBaseView(APIView):
    permission_classes = (IsAuthenticated,)

    def get_family(self):
        return get_object_or_404(
            Family.objects.visible_to(self.request.user),
            pk=self.kwargs["family_pk"],
        )

    def get_membership(self, family):
        return get_object_or_404(
            FamilyMembership.objects.in_families_visible_to(self.request.user).filter(
                family=family
            ),
            pk=self.kwargs["membership_pk"],
        )


class FamilyMembershipListView(FamilyMembershipBaseView):
    def get(self, request, family_pk):
        family = self.get_family()
        memberships = FamilyMembership.objects.in_families_visible_to(
            request.user
        ).filter(family=family)
        return Response(FamilyMembershipSerializer(memberships, many=True).data)

    def post(self, request, family_pk):
        family = self.get_family()
        serializer = MembershipCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = get_object_or_404(
            User.objects.all(), pk=serializer.validated_data["user_id"]
        )
        membership = create_membership(
            actor=request.user,
            family=family,
            user=user,
            role=serializer.validated_data["role"],
            is_active=serializer.validated_data["is_active"],
        )
        return Response(
            FamilyMembershipSerializer(membership).data, status=status.HTTP_201_CREATED
        )


class FamilyMembershipDetailView(FamilyMembershipBaseView):
    def get(self, request, family_pk, membership_pk):
        membership = self.get_membership(self.get_family())
        return Response(FamilyMembershipSerializer(membership).data)

    def patch(self, request, family_pk, membership_pk):
        membership = self.get_membership(self.get_family())
        serializer = MembershipUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        membership = update_membership(
            actor=request.user,
            membership=membership,
            role=serializer.validated_data.get("role", membership.role),
            is_active=serializer.validated_data.get("is_active", membership.is_active),
        )
        return Response(FamilyMembershipSerializer(membership).data)

    def delete(self, request, family_pk, membership_pk):
        membership = self.get_membership(self.get_family())
        delete_membership(actor=request.user, membership=membership)
        return Response(status=status.HTTP_204_NO_CONTENT)


class InitialForecastConfigurationView(APIView):
    permission_classes = (IsAuthenticated,)

    def put(self, request, family_pk):
        family = get_object_or_404(Family.objects.visible_to(request.user), pk=family_pk)
        if not FamilyMembership.objects.active_admin_for(request.user, family).exists():
            raise PermissionDenied("Only family administrators can configure initial forecasts.")
        serializer = InitialForecastConfigurationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = configure_initial_forecasts(
                actor=request.user,
                family=family,
                data=serializer.validated_data,
            )
        except DjangoValidationError as error:
            raise ValidationError(error.message_dict) from error
        return Response(result, status=status.HTTP_200_OK)
