from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.families.urls")),
    path("api/v1/", include("apps.finance.urls")),
    path("api/v1/", include("apps.budgets.urls")),
    path("api/v1/", include("apps.incomes.urls")),
    path("api/v1/", include("apps.expenses.urls")),
    path("api/v1/", include("apps.savings.urls")),
    path("api/v1/", include("apps.projections.urls")),
]
