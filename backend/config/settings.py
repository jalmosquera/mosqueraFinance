import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "development-only-secret-key")
DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"
USE_LOCAL_SQLITE = os.environ.get("DJANGO_USE_SQLITE") == "1"
IS_LOCAL_DEVELOPMENT = DEBUG or USE_LOCAL_SQLITE or "pytest" in sys.modules
ALLOWED_HOSTS = (
    ["localhost", "127.0.0.1"]
    if IS_LOCAL_DEVELOPMENT
    else [
        host.strip()
        for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",")
        if host.strip()
    ]
)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "apps.accounts",
    "apps.families",
    "apps.audit",
    "apps.finance",
    "apps.budgets",
    "apps.incomes",
    "apps.expenses",
    "apps.obligations",
    "apps.savings",
    "apps.projections",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]
WSGI_APPLICATION = "config.wsgi.application"

# Production defaults to PostgreSQL. SQLite requires an explicit local-development
# opt-in, while pytest stays self-contained without a running PostgreSQL instance.
if "pytest" in sys.modules or USE_LOCAL_SQLITE:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "dev.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("POSTGRES_DB", "mosquera_finance"),
            "USER": os.environ.get("POSTGRES_USER", "mosquera_finance"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
            "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        }
    }

AUTH_PASSWORD_VALIDATORS = []
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication"
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
}

LOGIN_ATTEMPT_LIMIT = 5
LOGIN_ATTEMPT_WINDOW_SECONDS = 300

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = not IS_LOCAL_DEVELOPMENT
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = not IS_LOCAL_DEVELOPMENT
CSRF_COOKIE_HTTPONLY = False
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"

if not IS_LOCAL_DEVELOPMENT:
    # The TLS proxy must set this header and the internal Nginx proxy must preserve it.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    # Compose probes this endpoint directly over the internal network.
    SECURE_REDIRECT_EXEMPT = [r"^healthz$"]
    SECURE_HSTS_SECONDS = 31536000
