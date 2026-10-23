"""Django settings for the Beng statement-intelligence application.

Local development and tests use the isolated PostgreSQL service in
``compose.yaml`` (loopback port 55432). Nothing here reads private data.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


# Local development key; deployments must supply DJANGO_SECRET_KEY.
SECRET_KEY = _env("DJANGO_SECRET_KEY", "insecure-local-development-key")
DEBUG = _env_bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = [h for h in _env("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "ledger",
    "jobs",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "intellistore.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "intellistore.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": _env("POSTGRES_DB", "intellistore"),
        "USER": _env("POSTGRES_USER", "intellistore"),
        "PASSWORD": _env("POSTGRES_PASSWORD", "intellistore-local-only"),
        "HOST": _env("POSTGRES_HOST", "127.0.0.1"),
        "PORT": _env("POSTGRES_PORT", "55432"),
        "CONN_MAX_AGE": 0,
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-gb"
TIME_ZONE = "Europe/London"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Worker lease/retry timings. Provisional until calibrated on the laptop (P-06).
WORKER_LEASE_SECONDS = int(_env("WORKER_LEASE_SECONDS", "120"))
WORKER_MAX_ATTEMPTS = int(_env("WORKER_MAX_ATTEMPTS", "3"))
WORKER_RETRY_DELAYS = tuple(
    int(value) for value in _env("WORKER_RETRY_DELAYS", "30,120").split(",")
)

# Private local laptop controller. The URL is unset until deployment supplies a
# container-reachable private address; no wake happens without one.
LAPTOP_CONTROLLER = None
LAPTOP_CONTROLLER_URL = _env("LAPTOP_CONTROLLER_URL", "").strip()
LAPTOP_CONTROLLER_TIMEOUT_SECONDS = float(
    _env("LAPTOP_CONTROLLER_TIMEOUT_SECONDS", "5")
)

# Provisional keep-awake timing; P-06 calibration on the target laptop remains open.
# Renew only near expiry and add a short extension, so a crash cannot leave an
# eight-hour inhibition from a single long renewal.
WORKER_KEEP_AWAKE_SECONDS = max(1, int(_env("WORKER_KEEP_AWAKE_SECONDS", "1200")))
WORKER_KEEP_AWAKE_RENEW_BEFORE_SECONDS = max(
    1, int(_env("WORKER_KEEP_AWAKE_RENEW_BEFORE_SECONDS", "300"))
)
WORKER_KEEP_AWAKE_EXTENSION_SECONDS = max(
    1, int(_env("WORKER_KEEP_AWAKE_EXTENSION_SECONDS", "600"))
)

# Local authoritative data (accepted originals and later recovery material).
DATA_DIR = Path(_env("INTELLISTORE_DATA_DIR", str(BASE_DIR / "var")))

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Invalid user-supplied PDFs are expected; pypdf's warnings would log contents-adjacent detail.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "loggers": {"pypdf": {"level": "ERROR"}},
}

# Private single-user access: one login, no self-service registration.
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/login/"
