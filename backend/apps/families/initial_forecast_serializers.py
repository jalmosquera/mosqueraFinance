from decimal import Decimal

from rest_framework import serializers

from apps.incomes.models import Recurrence


class AccountInputSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False, min_value=1)
    key = serializers.SlugField(required=False, max_length=64)
    owner_id = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    name = serializers.CharField(max_length=120)


class CategoryInputSerializer(AccountInputSerializer):
    kind = serializers.ChoiceField(choices=("INCOME", "EXPENSE"))


class ForecastAllocationInputSerializer(serializers.Serializer):
    member_id = serializers.IntegerField(min_value=1)
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"))


class ForecastInputSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False, min_value=1)
    owner_id = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    account_id = serializers.IntegerField(required=False, min_value=1)
    account_key = serializers.SlugField(required=False, max_length=64)
    category_id = serializers.IntegerField(required=False, min_value=1)
    category_key = serializers.SlugField(required=False, max_length=64)
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"))
    occurred_on = serializers.DateField()
    effective_date = serializers.DateField()
    recurrence = serializers.ChoiceField(choices=Recurrence.choices, default=Recurrence.NONE)
    description = serializers.CharField(required=False, allow_blank=True, max_length=255)

    def validate(self, attrs):
        for name in ("account", "category"):
            if bool(attrs.get(f"{name}_id")) == bool(attrs.get(f"{name}_key")):
                raise serializers.ValidationError(
                    {name: "Provide exactly one of the id or a key from this request."}
                )
        return attrs


class ExpenseForecastInputSerializer(ForecastInputSerializer):
    is_cigarettes = serializers.BooleanField(default=False)
    allocations = ForecastAllocationInputSerializer(many=True, required=False)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        allocations = attrs.get("allocations", [])
        if attrs["is_cigarettes"]:
            if attrs.get("owner_id") is not None:
                raise serializers.ValidationError({"owner_id": "The cigarettes forecast must be shared."})
            if attrs["recurrence"] != Recurrence.MONTHLY:
                raise serializers.ValidationError({"recurrence": "The cigarettes forecast must recur monthly."})
            if not allocations:
                raise serializers.ValidationError({"allocations": "Cigarettes requires shared allocations."})
            if sum((item["amount"] for item in allocations), Decimal("0.00")) != attrs["amount"]:
                raise serializers.ValidationError({"allocations": "Allocation amounts must equal the forecast amount exactly."})
        elif allocations:
            raise serializers.ValidationError({"allocations": "Only cigarettes can have planned allocations."})
        return attrs


class BudgetLineInputSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False, min_value=1)
    name = serializers.CharField(max_length=120)
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.00"))


class BudgetInputSerializer(serializers.Serializer):
    month = serializers.DateField()
    lines = BudgetLineInputSerializer(many=True)

    def validate_month(self, value):
        if value.day != 1:
            raise serializers.ValidationError("Budget month must be the first day of a month.")
        return value

    def validate_lines(self, value):
        normalized_names = [line["name"].strip().casefold() for line in value]
        if len(normalized_names) != len(set(normalized_names)):
            raise serializers.ValidationError("Budget lines must not duplicate a total by name.")
        return value


class FreeMoneyInputSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False, min_value=1)
    owner_id = serializers.IntegerField(min_value=1)
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.00"))
    effective_date = serializers.DateField()


class DistributionInputSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False, min_value=1)
    effective_date = serializers.DateField()
    first_owner_id = serializers.IntegerField(min_value=1)
    second_owner_id = serializers.IntegerField(min_value=1)


class MatiasFundInputSerializer(serializers.Serializer):
    target_amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"))
    projected_balance = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.00"), default=Decimal("0.00"))


class InitialForecastConfigurationSerializer(serializers.Serializer):
    accounts = AccountInputSerializer(many=True, required=False, default=list)
    categories = CategoryInputSerializer(many=True, required=False, default=list)
    income_forecasts = ForecastInputSerializer(many=True, required=False, default=list)
    expense_forecasts = ExpenseForecastInputSerializer(many=True, required=False, default=list)
    budget = BudgetInputSerializer(required=False)
    free_money_allowances = FreeMoneyInputSerializer(many=True, required=False, default=list)
    savings_distribution = DistributionInputSerializer(required=False)
    matias_fund = MatiasFundInputSerializer(required=False)

    def validate(self, attrs):
        for field in ("accounts", "categories"):
            keys = [item.get("key") for item in attrs[field] if item.get("key")]
            if len(keys) != len(set(keys)):
                raise serializers.ValidationError({field: "Keys must be unique within the request."})
        cigarette_count = sum(item["is_cigarettes"] for item in attrs["expense_forecasts"])
        if cigarette_count > 1:
            raise serializers.ValidationError({"expense_forecasts": "Only one shared cigarettes forecast is allowed."})
        return attrs
