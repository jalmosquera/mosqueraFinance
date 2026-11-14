import pytest
from rest_framework import status

from apps.audit.models import AuditLog
from apps.families.models import UserNotificationPreference

pytestmark = pytest.mark.django_db


def test_notification_preference_defaults_are_private_to_caller(
    api_client, user_factory, family_factory, membership_factory
):
    caller = user_factory("caller")
    family = family_factory("Family")
    membership_factory(family, caller)
    api_client.force_authenticate(caller)

    response = api_client.get(f"/api/v1/families/{family.pk}/notification-preferences/")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["is_enabled"] is False
    assert response.data["reminder_time"] is None
    assert not UserNotificationPreference.objects.exists()


def test_notification_preference_update_is_scoped_to_user_and_family(
    api_client, user_factory, family_factory, membership_factory
):
    caller = user_factory("caller")
    other_user = user_factory("other")
    family = family_factory("Family")
    membership_factory(family, caller)
    membership_factory(family, other_user)
    other_preference = UserNotificationPreference.objects.create(
        family=family,
        user=other_user,
        is_enabled=True,
        reminder_time="08:30",
        permission=UserNotificationPreference.Permission.GRANTED,
    )
    api_client.force_authenticate(caller)

    response = api_client.patch(
        f"/api/v1/families/{family.pk}/notification-preferences/",
        {"is_enabled": True, "reminder_time": "09:00", "permission": "GRANTED"},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    preference = UserNotificationPreference.objects.get(family=family, user=caller)
    assert preference.is_enabled is True
    assert str(preference.reminder_time) == "09:00:00"
    other_preference.refresh_from_db()
    assert str(other_preference.reminder_time) == "08:30:00"
    audit_log = AuditLog.objects.get(action="notification_preference.updated")
    assert audit_log.actor == caller
    assert audit_log.family == family
    assert audit_log.metadata == {
        "is_enabled": True,
        "reminder_configured": True,
        "permission": "GRANTED",
    }


def test_notification_preference_rejects_unrelated_family(
    api_client, user_factory, family_factory, membership_factory
):
    caller = user_factory("caller")
    visible_family = family_factory("Visible")
    hidden_family = family_factory("Hidden")
    membership_factory(visible_family, caller)
    api_client.force_authenticate(caller)

    response = api_client.patch(
        f"/api/v1/families/{hidden_family.pk}/notification-preferences/",
        {"is_enabled": True},
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert not UserNotificationPreference.objects.exists()
