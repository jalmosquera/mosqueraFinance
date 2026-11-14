from django.urls import path

from .views import ProjectionScenarioView

urlpatterns = [
    path(
        "families/<int:family_pk>/projections/scenario/",
        ProjectionScenarioView.as_view(),
        name="projection-scenario",
    ),
]
