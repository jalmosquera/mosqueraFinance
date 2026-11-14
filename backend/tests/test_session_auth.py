from datetime import timedelta

import pytest
from django.test import Client, RequestFactory, override_settings
from django.utils import timezone
from rest_framework import status

from apps.accounts.models import LoginThrottle
from apps.accounts.views import _attempt_fingerprint, _is_rate_limited

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def clear_login_throttles():
    LoginThrottle.objects.all().delete()
    yield
    LoginThrottle.objects.all().delete()


def csrf_client():
    client = Client(enforce_csrf_checks=True)
    response = client.get("/api/v1/auth/csrf/")
    assert response.status_code == status.HTTP_200_OK
    return client


def test_csrf_bootstrap_sets_cookie():
    client = Client(enforce_csrf_checks=True)

    response = client.get("/api/v1/auth/csrf/")

    assert response.status_code == status.HTTP_200_OK
    assert "csrftoken" in response.cookies


def test_login_requires_csrf_token(user_factory):
    user_factory("jalberth")
    client = Client(enforce_csrf_checks=True)

    response = client.post(
        "/api/v1/auth/login/",
        data={"username": "jalberth", "password": "test-password"},
        content_type="application/json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_login_me_and_logout_use_session_cookie(user_factory):
    user = user_factory("jalberth")
    client = csrf_client()
    csrf_token = client.cookies["csrftoken"].value

    login_response = client.post(
        "/api/v1/auth/login/",
        data={"username": "jalberth", "password": "test-password"},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    me_response = client.get("/api/v1/auth/me/")
    logout_response = client.post(
        "/api/v1/auth/logout/", HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value
    )
    logged_out_response = client.get("/api/v1/auth/me/")

    assert login_response.status_code == status.HTTP_200_OK
    assert login_response.json()["user"]["id"] == user.pk
    assert "sessionid" in login_response.cookies
    assert me_response.status_code == status.HTTP_200_OK
    assert me_response.json()["user"]["username"] == "jalberth"
    assert logout_response.status_code == status.HTTP_204_NO_CONTENT
    assert logged_out_response.status_code == status.HTTP_401_UNAUTHORIZED


def test_logout_requires_csrf_token(user_factory):
    user = user_factory("jalberth")
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)

    response = client.post("/api/v1/auth/logout/")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@override_settings(LOGIN_ATTEMPT_LIMIT=2, LOGIN_ATTEMPT_WINDOW_SECONDS=60)
def test_login_attempts_are_rate_limited(user_factory):
    user_factory("jalberth")
    client = csrf_client()
    csrf_token = client.cookies["csrftoken"].value

    for _ in range(2):
        response = client.post(
            "/api/v1/auth/login/",
            data={"username": "jalberth", "password": "wrong-password"},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    response = client.post(
        "/api/v1/auth/login/",
        data={"username": "jalberth", "password": "wrong-password"},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS


@override_settings(LOGIN_ATTEMPT_LIMIT=2, LOGIN_ATTEMPT_WINDOW_SECONDS=60)
def test_successful_login_clears_shared_throttle_window(user_factory):
    user_factory("jalberth")
    client = csrf_client()
    csrf_token = client.cookies["csrftoken"].value

    failed_response = client.post(
        "/api/v1/auth/login/",
        data={"username": "jalberth", "password": "wrong-password"},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    successful_response = client.post(
        "/api/v1/auth/login/",
        data={"username": "jalberth", "password": "test-password"},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert failed_response.status_code == status.HTTP_400_BAD_REQUEST
    assert successful_response.status_code == status.HTTP_200_OK
    assert not LoginThrottle.objects.exists()


@override_settings(LOGIN_ATTEMPT_LIMIT=1, LOGIN_ATTEMPT_WINDOW_SECONDS=60)
def test_expired_shared_throttle_window_restarts():
    request = RequestFactory().post("/")
    fingerprint = _attempt_fingerprint(request, "jalberth")
    LoginThrottle.objects.create(
        fingerprint=fingerprint,
        attempts=1,
        window_started_at=timezone.now() - timedelta(seconds=61),
    )

    is_limited = _is_rate_limited(request, "jalberth")

    assert is_limited is False
    assert LoginThrottle.objects.get(fingerprint=fingerprint).attempts == 1
