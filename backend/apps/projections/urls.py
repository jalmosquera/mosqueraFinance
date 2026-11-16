from django.urls import path

from .views import ApprovedForecastView, ProjectionScenarioView

urlpatterns = [
    path(
        "families/<int:family_pk>/projections/approved-forecast/",
        ApprovedForecastView.as_view(),
        name="approved-forecast",
    ),
    path(
        "families/<int:family_pk>/projections/scenario/",
        ProjectionScenarioView.as_view(),
        name="projection-scenario",
    ),
]
