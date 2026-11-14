from django.urls import path

from .views import (
    BudgetForecastListCreateView,
    BudgetLineListCreateView,
    FreeMoneyAllowanceListCreateView,
    ProjectedSavingsView,
    SavingsDistributionRuleListCreateView,
)

urlpatterns = [
    path("families/<int:family_pk>/budget-forecasts/", BudgetForecastListCreateView.as_view(), name="budget-forecast-list"),
    path("families/<int:family_pk>/budget-forecasts/<int:forecast_pk>/lines/", BudgetLineListCreateView.as_view(), name="budget-line-list"),
    path("families/<int:family_pk>/free-money-allowances/", FreeMoneyAllowanceListCreateView.as_view(), name="free-money-allowance-list"),
    path("families/<int:family_pk>/savings-distribution-rules/", SavingsDistributionRuleListCreateView.as_view(), name="savings-distribution-rule-list"),
    path("families/<int:family_pk>/budgets/projected-savings/", ProjectedSavingsView.as_view(), name="projected-savings"),
]
