from rest_framework import serializers

from .models import Category, LogicalAccount


class FamilyScopedCreateSerializer(serializers.ModelSerializer):
    owner_id = serializers.IntegerField(required=False, allow_null=True, min_value=1)

    def validate_owner_id(self, owner_id):
        if owner_id is not None and owner_id != self.context["request"].user.pk:
            raise serializers.ValidationError("Private records can only be owned by you.")
        return owner_id

    def create(self, validated_data):
        return self.Meta.model.objects.create(
            family=self.context["family"],
            owner_id=validated_data.pop("owner_id", None),
            **validated_data,
        )


class LogicalAccountSerializer(FamilyScopedCreateSerializer):
    class Meta:
        model = LogicalAccount
        fields = ("id", "family_id", "owner_id", "name", "created_at")
        read_only_fields = ("id", "family_id", "created_at")


class CategorySerializer(FamilyScopedCreateSerializer):
    class Meta:
        model = Category
        fields = ("id", "family_id", "owner_id", "name", "kind", "created_at")
        read_only_fields = ("id", "family_id", "created_at")
