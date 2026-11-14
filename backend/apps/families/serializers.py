from rest_framework import serializers

from .models import Family, FamilyMembership, UserNotificationPreference


class FamilySerializer(serializers.ModelSerializer):
    class Meta:
        model = Family
        fields = ("id", "name", "created_at")
        read_only_fields = fields


class FamilyBootstrapSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=12, trim_whitespace=False)
    family_name = serializers.CharField(max_length=120, trim_whitespace=True)

    def validate_family_name(self, value):
        if not value:
            raise serializers.ValidationError("Family name cannot be blank.")
        return value


class FamilyMembershipSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = FamilyMembership
        fields = (
            "id",
            "family_id",
            "user_id",
            "role",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "family_id", "user_id", "created_at", "updated_at")


class MembershipCreateSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(min_value=1)
    role = serializers.ChoiceField(
        choices=FamilyMembership.Role.choices, default=FamilyMembership.Role.MEMBER
    )
    is_active = serializers.BooleanField(default=True)


class MembershipUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(
        choices=FamilyMembership.Role.choices, required=False
    )
    is_active = serializers.BooleanField(required=False)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("Provide role or is_active.")
        return attrs


class UserNotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserNotificationPreference
        fields = ("is_enabled", "reminder_time", "permission", "updated_at")
        read_only_fields = ("updated_at",)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("Provide at least one notification preference.")
        return attrs
