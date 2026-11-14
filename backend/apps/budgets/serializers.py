from rest_framework import serializers

from .models import (
    BudgetLine,
    FreeMoneyAllowance,
    MonthlyBudgetForecast,
    SavingsDistributionRule,
)


class BudgetLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = BudgetLine
        fields = ("id", "name", "amount", "kind", "replaces")
        read_only_fields = ("id",)


class MonthlyBudgetForecastSerializer(serializers.ModelSerializer):
    lines = BudgetLineSerializer(many=True, required=False)

    class Meta:
        model = MonthlyBudgetForecast
        fields = ("id", "family_id", "month", "version", "lines", "created_at")
        read_only_fields = ("id", "family_id", "created_at")

    def create(self, validated_data):
        lines = validated_data.pop("lines", [])
        forecast = MonthlyBudgetForecast.objects.create(family=self.context["family"], **validated_data)
        line_replacements = []
        for line_data in lines:
            replaces = line_data.pop("replaces", None)
            line = BudgetLine.objects.create(forecast=forecast, **line_data)
            if replaces is not None:
                line_replacements.append((line, replaces))
        for line, replaces in line_replacements:
            line.replaces_id = replaces.pk if isinstance(replaces, BudgetLine) else replaces
            line.save(update_fields=("replaces",))
        return forecast

    def validate_lines(self, lines):
        if sum(line["kind"] == BudgetLine.Kind.RECONCILIATION for line in lines) > 1:
            raise serializers.ValidationError("A budget forecast can contain only one reconciliation line.")
        return lines


class FreeMoneyAllowanceSerializer(serializers.ModelSerializer):
    owner_id = serializers.IntegerField(min_value=1)

    class Meta:
        model = FreeMoneyAllowance
        fields = ("id", "family_id", "owner_id", "amount", "effective_date", "created_at")
        read_only_fields = ("id", "family_id", "created_at")


class SavingsDistributionRuleSerializer(serializers.ModelSerializer):
    first_owner_id = serializers.IntegerField(min_value=1)
    second_owner_id = serializers.IntegerField(min_value=1)

    class Meta:
        model = SavingsDistributionRule
        fields = ("id", "family_id", "effective_date", "first_owner_id", "second_owner_id", "created_at")
        read_only_fields = ("id", "family_id", "created_at")


class ProjectedSavingsSerializer(serializers.Serializer):
    month = serializers.DateField()
    projected_income = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=0)

    def validate_month(self, value):
        if value.day != 1:
            raise serializers.ValidationError("Month must be the first day of a month.")
        return value
