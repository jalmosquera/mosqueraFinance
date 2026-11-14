from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.families.models import Family

from .serializers import ProjectionScenarioSerializer
from .services import project_scenario


class ProjectionScenarioView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, family_pk):
        family = get_object_or_404(Family.objects.visible_to(request.user), pk=family_pk)
        serializer = ProjectionScenarioSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            project_scenario(user=request.user, family=family, **serializer.validated_data)
        )
