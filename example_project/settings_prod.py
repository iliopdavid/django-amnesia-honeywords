"""Production settings template for django-amnesia-honeywords.

Copy/adapt this into your project. Keep secrets out of source control.
"""

from __future__ import annotations

import os


def _env_bool(name: str, default: bool = False) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "on"}


SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    raise RuntimeError("DJANGO_SECRET_KEY must be set in production")

DEBUG = _env_bool("DJANGO_DEBUG", False)

allowed_hosts = os.environ.get("DJANGO_ALLOWED_HOSTS", "")
ALLOWED_HOSTS = [h.strip() for h in allowed_hosts.split(",") if h.strip()]
if not ALLOWED_HOSTS:
    # Fail closed: require explicit hosts.
    raise RuntimeError("DJANGO_ALLOWED_HOSTS must be set (comma-separated)")

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.admin",
    "django_honeywords.apps.DjangoHoneywordsConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

# IMPORTANT: Do not include ModelBackend in production unless you fully understand
# the bypass risk for users who were not initialized with an AmnesiaSet.
AUTHENTICATION_BACKENDS = [
    "django_honeywords.backend.HoneywordsBackend",
]

# Use Django's default secure hashers (PBKDF2 by default).
# If you enable Argon2 or BCrypt, add the corresponding package dependencies.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True

ROOT_URLCONF = "example_project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {
    "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": "db.sqlite3"}
}

# Honeywords policy (recommended production defaults)
HONEYWORDS = {
    # Choose a response on honeyword detection.
    # Prefer "lock" (containment) or "log" (alert-only) unless you have a full reset UX.
    "ON_HONEYWORD": os.environ.get("HONEYWORDS_ON_HONEYWORD", "lock"),
    "LOCK_BASE_SECONDS": int(os.environ.get("HONEYWORDS_LOCK_BASE_SECONDS", "60")),
    "LOCK_MAX_SECONDS": int(os.environ.get("HONEYWORDS_LOCK_MAX_SECONDS", "3600")),

    # Amnesia parameters
    "AMNESIA_K": int(os.environ.get("HONEYWORDS_AMNESIA_K", "20")),
    "AMNESIA_P_MARK": float(os.environ.get("HONEYWORDS_AMNESIA_P_MARK", "0.1")),
    "AMNESIA_P_REMARK": float(os.environ.get("HONEYWORDS_AMNESIA_P_REMARK", "0.01")),
}

USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
