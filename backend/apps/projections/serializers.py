from decimal import Decimal

from rest_framework import serializers


class ForecastChangeSerializer(serializers.Serializer):
    forecast_id = serializers.IntegerField(min_value=1)
    amount = serializers.DecimalField(
        max_digits=14, decimal_places=2, min_value=Decimal("0.01")
    )


class SavingsChangeSerializer(serializers.Serializer):
    goal_id = serializers.IntegerField(min_value=1)
    projected_monthly_contribution = serializers.DecimalField(
        max_digits=14, decimal_places=2, min_value=Decimal("0.00"), required=False
    )
    projected_balance = serializers.DecimalField(
        max_digits=14, decimal_places=2, min_value=Decimal("0.00"), required=False
    )

    def validate(self, attrs):
        if len(attrs) == 1:
            raise serializers.ValidationError(
                "Specify a projected monthly contribution or projected balance."
            )
        return attrs


class ProjectionScenarioSerializer(serializers.Serializer):
    start_month = serializers.DateField()
    income_changes = ForecastChangeSerializer(many=True, required=False, default=list)
    expense_changes = ForecastChangeSerializer(many=True, required=False, default=list)
    savings_changes = SavingsChangeSerializer(many=True, required=False, default=list)

    def validate_start_month(self, value):
        if value.day != 1:
            raise serializers.ValidationError("Start month must be the first day of a month.")
        return value

    def validate(self, attrs):
        for field, id_field in (
            ("income_changes", "forecast_id"),
            ("expense_changes", "forecast_id"),
            ("savings_changes", "goal_id"),
        ):
            identifiers = [change[id_field] for change in attrs[field]]
            if len(identifiers) != len(set(identifiers)):
                raise serializers.ValidationError(
                    {field: "Each record can only be changed once per scenario."}
                )
        return attrs


class ApprovedForecastQuerySerializer(serializers.Serializer):
    start_month = serializers.DateField()

    def validate_start_month(self, value):
        if value.day != 1:
            raise serializers.ValidationError("Start month must be the first day of a month.")
        return value
