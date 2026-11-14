from django.core.exceptions import ValidationError
from django.db import transaction

from apps.audit.services import record_entity_mutation
from apps.budgets.models import (
    BudgetLine,
    FreeMoneyAllowance,
    MonthlyBudgetForecast,
    SavingsDistributionRule,
)
from apps.expenses.models import ExpenseForecast, ExpenseForecastAllocation
from apps.finance.models import Category, LogicalAccount, normalize_name
from apps.incomes.models import IncomeForecast
from apps.savings.models import MatiasFund


def _member_ids(family):
    return set(family.memberships.filter(is_active=True).values_list("user_id", flat=True))


def _require_member(owner_id, member_ids):
    if owner_id is not None and owner_id not in member_ids:
        raise ValidationError({"owner_id": "Owner must be an active family member."})


def _upsert_named(*, model, family, values, member_ids):
    records = {}
    for data in values:
        key = data.pop("key", None)
        record_id = data.pop("id", None)
        owner_id = data.get("owner_id")
        _require_member(owner_id, member_ids)
        if record_id:
            try:
                record = model.objects.get(pk=record_id, family=family)
            except model.DoesNotExist as error:
                raise ValidationError({"id": "Record does not belong to this family."}) from error
            for field, value in data.items():
                setattr(record, field, value)
            record.save()
        else:
            record = model.objects.create(family=family, **data)
        if key:
            records[key] = record
    return records


def _resolve_reference(*, model, family, value, key, created):
    if value:
        try:
            return model.objects.get(pk=value, family=family)
        except model.DoesNotExist as error:
            raise ValidationError({"id": "Reference does not belong to this family."}) from error
    try:
        return created[key]
    except KeyError as error:
        raise ValidationError({"key": "Reference key is not configured in this request."}) from error


def _upsert_forecasts(*, model, family, values, accounts, categories, member_ids):
    records = []
    for data in values:
        allocations = data.pop("allocations", None)
        record_id = data.pop("id", None)
        account = _resolve_reference(
            model=LogicalAccount, family=family, value=data.pop("account_id", None),
            key=data.pop("account_key", None), created=accounts,
        )
        category = _resolve_reference(
            model=Category, family=family, value=data.pop("category_id", None),
            key=data.pop("category_key", None), created=categories,
        )
        _require_member(data.get("owner_id"), member_ids)
        if record_id:
            try:
                record = model.objects.get(pk=record_id, family=family)
            except model.DoesNotExist as error:
                raise ValidationError({"id": "Forecast does not belong to this family."}) from error
            # Snapshot the existing definition before the administrative flow changes it.
            from apps.obligations.services import (
                preserve_historical_occurrences_before_forecast_edit,
            )

            preserve_historical_occurrences_before_forecast_edit(forecast=record)
            for field, value in data.items():
                setattr(record, field, value)
            record.account = account
            record.category = category
            record.save()
        else:
            record = model.objects.create(family=family, account=account, category=category, **data)
        if allocations is not None:
            allocation_member_ids = [allocation["member_id"] for allocation in allocations]
            if len(allocation_member_ids) != len(set(allocation_member_ids)):
                raise ValidationError({"allocations": "Each member can have only one allocation."})
            if any(member_id not in member_ids for member_id in allocation_member_ids):
                raise ValidationError({"allocations": "Allocation members must be active family members."})
            ExpenseForecastAllocation.objects.filter(forecast=record).delete()
            for allocation in allocations:
                ExpenseForecastAllocation.objects.create(forecast=record, member_id=allocation["member_id"], amount=allocation["amount"])
        records.append(record)
    return records


def _upsert_budget(*, family, data):
    if not data:
        return None
    forecasts = MonthlyBudgetForecast.objects.filter(family=family, month=data["month"])
    if forecasts.count() > 1:
        raise ValidationError({"budget": "A month with multiple budget versions cannot be reconfigured here."})
    forecast = forecasts.first()
    if forecast is None:
        forecast = MonthlyBudgetForecast.objects.create(family=family, month=data["month"], version=1)
    for line_data in data["lines"]:
        line_id = line_data.pop("id", None)
        if line_id:
            try:
                line = BudgetLine.objects.get(pk=line_id, forecast=forecast)
            except BudgetLine.DoesNotExist as error:
                raise ValidationError({"budget": "Budget line does not belong to this month."}) from error
            line.name = line_data["name"]
            line.amount = line_data["amount"]
            line.save()
        else:
            if BudgetLine.objects.filter(forecast=forecast, name__iexact=line_data["name"].strip()).exists():
                raise ValidationError(
                    {"budget": f"Budget line {normalize_name(line_data['name'])!r} already exists."}
                )
            BudgetLine.objects.create(forecast=forecast, **line_data)
    return forecast


@transaction.atomic
def configure_initial_forecasts(*, actor, family, data):
    member_ids = _member_ids(family)
    accounts = _upsert_named(
        model=LogicalAccount, family=family, values=data["accounts"], member_ids=member_ids
    )
    categories = _upsert_named(
        model=Category, family=family, values=data["categories"], member_ids=member_ids
    )
    incomes = _upsert_forecasts(
        model=IncomeForecast, family=family, values=data["income_forecasts"], accounts=accounts,
        categories=categories, member_ids=member_ids,
    )
    expenses = _upsert_forecasts(
        model=ExpenseForecast, family=family, values=data["expense_forecasts"], accounts=accounts,
        categories=categories, member_ids=member_ids,
    )
    budget = _upsert_budget(family=family, data=data.get("budget"))
    allowances = []
    for allowance_data in data["free_money_allowances"]:
        allowance_id = allowance_data.pop("id", None)
        _require_member(allowance_data["owner_id"], member_ids)
        if allowance_id:
            try:
                allowance = FreeMoneyAllowance.objects.get(pk=allowance_id, family=family)
            except FreeMoneyAllowance.DoesNotExist as error:
                raise ValidationError({"id": "Allowance does not belong to this family."}) from error
            for field, value in allowance_data.items():
                setattr(allowance, field, value)
            allowance.save()
        else:
            allowance = FreeMoneyAllowance.objects.create(family=family, **allowance_data)
        allowances.append(allowance)
    distribution_data = data.get("savings_distribution")
    distribution = None
    if distribution_data:
        distribution_id = distribution_data.pop("id", None)
        _require_member(distribution_data["first_owner_id"], member_ids)
        _require_member(distribution_data["second_owner_id"], member_ids)
        if distribution_id:
            try:
                distribution = SavingsDistributionRule.objects.get(pk=distribution_id, family=family)
            except SavingsDistributionRule.DoesNotExist as error:
                raise ValidationError({"id": "Distribution rule does not belong to this family."}) from error
            for field, value in distribution_data.items():
                setattr(distribution, field, value)
            distribution.save()
        else:
            distribution = SavingsDistributionRule.objects.create(family=family, **distribution_data)
    fund_data = data.get("matias_fund")
    fund = None
    if fund_data:
        fund, _ = MatiasFund.objects.update_or_create(family=family, defaults=fund_data)
    record_entity_mutation(
        actor=actor,
        action="initial_forecast_configuration.updated",
        family=family,
        entity_type="family",
        entity_id=family.pk,
        metadata={
            "accounts": len(accounts), "categories": len(categories), "income_forecasts": len(incomes),
            "expense_forecasts": len(expenses), "budget_id": budget.pk if budget else None,
            "allowances": len(allowances), "distribution_id": distribution.pk if distribution else None,
            "matias_fund_id": fund.pk if fund else None,
        },
    )
    return {
        "account_ids": [record.pk for record in accounts.values()],
        "category_ids": [record.pk for record in categories.values()],
        "income_forecast_ids": [record.pk for record in incomes],
        "expense_forecast_ids": [record.pk for record in expenses],
        "budget_id": budget.pk if budget else None,
        "free_money_allowance_ids": [record.pk for record in allowances],
        "savings_distribution_id": distribution.pk if distribution else None,
        "matias_fund_id": fund.pk if fund else None,
    }
