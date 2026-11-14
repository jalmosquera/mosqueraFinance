import hashlib
import json
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError, transaction
from django.http import HttpRequest, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from apps.accounts.models import LoginThrottle


def _attempt_fingerprint(request: HttpRequest, username: str) -> str:
    fingerprint = f"{request.META.get('REMOTE_ADDR', '')}:{username.lower()}"
    return hashlib.sha256(fingerprint.encode()).hexdigest()


def _is_rate_limited(request: HttpRequest, username: str) -> bool:
    fingerprint = _attempt_fingerprint(request, username)
    limit = settings.LOGIN_ATTEMPT_LIMIT
    now = timezone.now()
    window_start = now - timedelta(seconds=settings.LOGIN_ATTEMPT_WINDOW_SECONDS)

    with transaction.atomic():
        try:
            throttle = LoginThrottle.objects.select_for_update().get(
                fingerprint=fingerprint
            )
        except LoginThrottle.DoesNotExist:
            try:
                # A concurrent first attempt may insert the same fingerprint.
                with transaction.atomic():
                    LoginThrottle.objects.create(
                        fingerprint=fingerprint,
                        attempts=1,
                        window_started_at=now,
                    )
            except IntegrityError:
                throttle = LoginThrottle.objects.select_for_update().get(
                    fingerprint=fingerprint
                )
            else:
                return False

        if throttle.window_started_at <= window_start:
            throttle.attempts = 1
            throttle.window_started_at = now
        else:
            throttle.attempts += 1
        throttle.save(update_fields=["attempts", "window_started_at"])
        return throttle.attempts > limit


@require_GET
@ensure_csrf_cookie
def csrf(request: HttpRequest) -> JsonResponse:
    return JsonResponse({"detail": "CSRF cookie set."})


@require_POST
@csrf_protect
def login_view(request: HttpRequest) -> JsonResponse:
    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        payload = {}
    if not isinstance(payload, dict):
        payload = {}

    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))
    if not username or not password:
        return JsonResponse({"detail": "Invalid credentials."}, status=400)

    if _is_rate_limited(request, username):
        return JsonResponse(
            {"detail": "Too many login attempts. Try again later."},
            status=429,
        )

    user = authenticate(request, username=username, password=password)
    if user is None:
        return JsonResponse({"detail": "Invalid credentials."}, status=400)

    LoginThrottle.objects.filter(
        fingerprint=_attempt_fingerprint(request, username)
    ).delete()
    login(request, user)
    return JsonResponse({"user": _user_data(user)})


@require_GET
def current_user(request: HttpRequest) -> JsonResponse:
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "Authentication required."}, status=401)
    return JsonResponse({"user": _user_data(request.user)})


@require_POST
@csrf_protect
def logout_view(request: HttpRequest) -> JsonResponse:
    logout(request)
    return JsonResponse({}, status=204)


def _user_data(user):
    return {
        "id": user.pk,
        "username": user.get_username(),
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
    }
