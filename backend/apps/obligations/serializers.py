from datetime import date
from decimal import Decimal

from rest_framework import serializers

from .models import PaymentObligation


class PaymentObligationSerializer(serializers.ModelSerializer):
    income_forecast_id = serializers.IntegerField(read_only=True)
    expense_forecast_id = serializers.IntegerField(read_only=True)
    income_movement_id = serializers.IntegerField(read_only=True)
    expense_movement_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = PaymentObligation
        fields = (
            "id", "family_id", "income_forecast_id", "expense_forecast_id", "source_period",
            "owner_id", "account_id", "category_id", "amount", "due_on", "description",
            "allocations", "status", "income_movement_id", "expense_movement_id", "void_reason",
            "created_at", "updated_at",
        )


class MonthSerializer(serializers.Serializer):
    month = serializers.DateField(required=False, default=date.today)

    def validate_month(self, value):
        if value.day != 1:
            raise serializers.ValidationError("Month must be the first day of a month.")
        return value


class AllocationInputSerializer(serializers.Serializer):
    member_id = serializers.IntegerField(min_value=1)
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"))


class SettleObligationSerializer(serializers.Serializer):
    allocations = AllocationInputSerializer(many=True, required=False)


class VoidObligationSerializer(serializers.Serializer):
    reason = serializers.CharField(trim_whitespace=True, min_length=1, max_length=1000)
