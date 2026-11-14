import hashlib
import json

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.core.cache import cache
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST


def _attempt_key(request: HttpRequest, username: str) -> str:
    fingerprint = f"{request.META.get('REMOTE_ADDR', '')}:{username.lower()}"
    return f"login-attempts:{hashlib.sha256(fingerprint.encode()).hexdigest()}"


def _is_rate_limited(request: HttpRequest, username: str) -> bool:
    key = _attempt_key(request, username)
    limit = settings.LOGIN_ATTEMPT_LIMIT
    if cache.add(key, 1, timeout=settings.LOGIN_ATTEMPT_WINDOW_SECONDS):
        return False
    return cache.incr(key) > limit


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

    cache.delete(_attempt_key(request, username))
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
