from django.urls import path

from .views import (
    FamilyDetailView,
    FamilyListView,
    FamilyMembershipDetailView,
    FamilyMembershipListView,
)

urlpatterns = [
    path("families/", FamilyListView.as_view(), name="family-list"),
    path("families/<int:pk>/", FamilyDetailView.as_view(), name="family-detail"),
    path(
        "families/<int:family_pk>/memberships/",
        FamilyMembershipListView.as_view(),
        name="family-membership-list",
    ),
    path(
        "families/<int:family_pk>/memberships/<int:membership_pk>/",
        FamilyMembershipDetailView.as_view(),
        name="family-membership-detail",
    ),
]
