from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.finance.models import Category, LogicalAccount

from .models import IncomeForecast, IncomeMovement


class IncomeRecordSerializer(serializers.ModelSerializer):
    owner_id = serializers.PrimaryKeyRelatedField(
        source="owner", queryset=get_user_model().objects.all(), required=False, allow_null=True
    )
    account_id = serializers.PrimaryKeyRelatedField(source="account", queryset=LogicalAccount.objects.all())
    category_id = serializers.PrimaryKeyRelatedField(source="category", queryset=Category.objects.all())

    class Meta:
        fields = (
            "id", "family_id", "owner_id", "account_id", "category_id", "amount",
            "occurred_on", "description", "status", "created_at", "updated_at",
        )
        read_only_fields = ("id", "family_id", "status", "created_at", "updated_at")

    def get_fields(self):
        fields = super().get_fields()
        request = self.context["request"]
        family = self.context["family"]
        fields["owner_id"].queryset = request.user.__class__.objects.filter(
            family_memberships__family=family, family_memberships__is_active=True
        )
        fields["account_id"].queryset = LogicalAccount.objects.visible_to(request.user).filter(family=family)
        fields["category_id"].queryset = Category.objects.visible_to(request.user).filter(family=family)
        return fields

    def validate_owner_id(self, owner):
        if owner is not None and owner != self.context["request"].user:
            raise serializers.ValidationError("Private records can only be owned by you.")
        if self.instance and owner != self.instance.owner:
            raise serializers.ValidationError("Owner cannot be changed after creation.")
        return owner

    def validate(self, attrs):
        values = {
            field: attrs.get(field, getattr(self.instance, field, None))
            for field in ("owner", "account", "category", "amount", "occurred_on", "description")
        }
        if self.Meta.model is IncomeForecast:
            values.update(
                {
                    field: attrs.get(field, getattr(self.instance, field, None))
                    for field in ("recurrence", "effective_date")
                }
            )
        model = self.Meta.model(family=self.context["family"], **values)
        try:
            model.full_clean()
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.message_dict) from error
        return attrs

    def create(self, validated_data):
        return self.Meta.model.objects.create(family=self.context["family"], **validated_data)


class IncomeForecastSerializer(IncomeRecordSerializer):
    class Meta(IncomeRecordSerializer.Meta):
        model = IncomeForecast
        fields = IncomeRecordSerializer.Meta.fields + ("recurrence", "effective_date")


class IncomeMovementSerializer(IncomeRecordSerializer):
    class Meta(IncomeRecordSerializer.Meta):
        model = IncomeMovement
        fields = IncomeRecordSerializer.Meta.fields + ("void_reason", "voided_at")
        read_only_fields = IncomeRecordSerializer.Meta.read_only_fields + ("void_reason", "voided_at")


class VoidMovementSerializer(serializers.Serializer):
    reason = serializers.CharField(trim_whitespace=True, min_length=1, max_length=1000)
