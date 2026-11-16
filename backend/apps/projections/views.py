from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.families.models import Family, FamilyMembership

from .serializers import ApprovedForecastQuerySerializer, ProjectionScenarioSerializer
from .services import approved_forecast, project_scenario


class ProjectionScenarioView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, family_pk):
        family = get_object_or_404(Family.objects.visible_to(request.user), pk=family_pk)
        serializer = ProjectionScenarioSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            project_scenario(user=request.user, family=family, **serializer.validated_data)
        )


class ApprovedForecastView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, family_pk):
        family = get_object_or_404(Family.objects.visible_to(request.user), pk=family_pk)
        membership = get_object_or_404(
            FamilyMembership.objects.active(), family=family, user=request.user
        )
        serializer = ApprovedForecastQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return Response(
            approved_forecast(
                user=request.user,
                family=family,
                membership=membership,
                has_household_aggregate_authority=FamilyMembership.objects.household_aggregate_authority_for(
                    request.user, family
                ).exists(),
                **serializer.validated_data,
            ),
            headers={"Cache-Control": "private, no-store"},
        )
