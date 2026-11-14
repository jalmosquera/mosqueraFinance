import pytest
from django.core.cache import cache
from django.test import Client, override_settings
from rest_framework import status

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


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
