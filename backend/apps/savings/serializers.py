from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import (
    MatiasFund,
    MatiasFundAllocation,
    MatiasFundMovement,
    SavingsGoal,
    SavingsMovement,
)


class SavingsGoalSerializer(serializers.ModelSerializer):
    owner_id = serializers.PrimaryKeyRelatedField(source="owner", queryset=get_user_model().objects.all(), required=False, allow_null=True)
    real_balance = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = SavingsGoal
        fields = ("id", "family_id", "owner_id", "name", "target_amount", "projected_monthly_contribution", "projected_balance", "real_balance", "created_at", "updated_at")
        read_only_fields = ("id", "family_id", "real_balance", "created_at", "updated_at")

    def get_fields(self):
        fields = super().get_fields()
        family = self.context["family"]
        fields["owner_id"].queryset = get_user_model().objects.filter(family_memberships__family=family, family_memberships__is_active=True)
        return fields

    def validate_owner_id(self, owner):
        if owner is not None and owner != self.context["request"].user:
            raise serializers.ValidationError("Private goals can only be owned by you.")
        if self.instance and owner != self.instance.owner:
            raise serializers.ValidationError("Owner cannot be changed after creation.")
        return owner

    def create(self, validated_data):
        return SavingsGoal.objects.create(family=self.context["family"], **validated_data)


class SavingsMovementSerializer(serializers.ModelSerializer):
    goal_id = serializers.PrimaryKeyRelatedField(source="goal", queryset=SavingsGoal.objects.all())
    corrects_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = SavingsMovement
        fields = ("id", "goal_id", "kind", "amount", "occurred_on", "description", "status", "void_reason", "voided_at", "corrects_id", "created_at")
        read_only_fields = ("id", "status", "void_reason", "voided_at", "corrects_id", "created_at")

    def get_fields(self):
        fields = super().get_fields()
        fields["goal_id"].queryset = SavingsGoal.objects.visible_to(self.context["request"].user).filter(family=self.context["family"])
        return fields

    def validate(self, attrs):
        model = SavingsMovement(**attrs)
        try:
            model.full_clean()
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.message_dict) from error
        return attrs


class VoidSerializer(serializers.Serializer):
    reason = serializers.CharField(trim_whitespace=True, min_length=1, max_length=1000)


class SavingsCorrectionSerializer(VoidSerializer):
    kind = serializers.ChoiceField(choices=SavingsMovement.Kind.choices)
    amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    occurred_on = serializers.DateField()
    description = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def validate(self, attrs):
        if attrs["kind"] == SavingsMovement.Kind.ADJUSTMENT and attrs["amount"] == 0:
            raise serializers.ValidationError({"amount": "An adjustment amount cannot be zero."})
        if attrs["kind"] != SavingsMovement.Kind.ADJUSTMENT and attrs["amount"] <= 0:
            raise serializers.ValidationError({"amount": "Contributions and withdrawals must be positive."})
        return attrs


class MatiasFundSerializer(serializers.ModelSerializer):
    real_balance = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = MatiasFund
        fields = ("id", "family_id", "target_amount", "projected_balance", "real_balance", "created_at", "updated_at")
        read_only_fields = ("id", "family_id", "real_balance", "created_at", "updated_at")


class MatiasFundAllocationSerializer(serializers.ModelSerializer):
    contributor_id = serializers.PrimaryKeyRelatedField(source="contributor", queryset=get_user_model().objects.all())

    class Meta:
        model = MatiasFundAllocation
        fields = ("contributor_id", "amount")

    def get_fields(self):
        fields = super().get_fields()
        family = self.context["family"]
        fields["contributor_id"].queryset = get_user_model().objects.filter(family_memberships__family=family, family_memberships__is_active=True)
        return fields


class MatiasFundMovementSerializer(serializers.ModelSerializer):
    allocations = MatiasFundAllocationSerializer(many=True)
    fund_id = serializers.IntegerField(read_only=True)
    corrects_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = MatiasFundMovement
        fields = ("id", "fund_id", "kind", "amount", "occurred_on", "description", "status", "void_reason", "voided_at", "corrects_id", "allocations", "created_at")
        read_only_fields = ("id", "fund_id", "status", "void_reason", "voided_at", "corrects_id", "created_at")

    def validate(self, attrs):
        allocations = attrs.get("allocations", [])
        total = sum((allocation["amount"] for allocation in allocations), Decimal("0.00"))
        if not allocations or total != attrs["amount"]:
            raise serializers.ValidationError({"allocations": "Allocation amounts must equal the fund movement amount exactly."})
        return attrs


class MatiasFundCorrectionSerializer(VoidSerializer):
    kind = serializers.ChoiceField(choices=MatiasFundMovement.Kind.choices)
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"))
    occurred_on = serializers.DateField()
    description = serializers.CharField(max_length=255, required=False, allow_blank=True)
    allocations = MatiasFundAllocationSerializer(many=True)

    def validate(self, attrs):
        total = sum((allocation["amount"] for allocation in attrs["allocations"]), Decimal("0.00"))
        if not attrs["allocations"] or total != attrs["amount"]:
            raise serializers.ValidationError({"allocations": "Allocation amounts must equal the fund movement amount exactly."})
        return attrs


class SimulationSerializer(serializers.Serializer):
    projected_monthly_contribution = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.00"))
    months = serializers.IntegerField(min_value=0, max_value=1200)
