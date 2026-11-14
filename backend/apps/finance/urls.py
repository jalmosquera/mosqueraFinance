from django.urls import path

from .views import (
    CategoryDetailView,
    CategoryListCreateView,
    LogicalAccountDetailView,
    LogicalAccountListCreateView,
)

urlpatterns = [
    path(
        "families/<int:family_pk>/logical-accounts/",
        LogicalAccountListCreateView.as_view(),
        name="logical-account-list",
    ),
    path(
        "families/<int:family_pk>/logical-accounts/<int:pk>/",
        LogicalAccountDetailView.as_view(),
        name="logical-account-detail",
    ),
    path(
        "families/<int:family_pk>/categories/",
        CategoryListCreateView.as_view(),
        name="category-list",
    ),
    path(
        "families/<int:family_pk>/categories/<int:pk>/",
        CategoryDetailView.as_view(),
        name="category-detail",
    ),
]
