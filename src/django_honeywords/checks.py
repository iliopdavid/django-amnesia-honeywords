from __future__ import annotations

from django.conf import settings
from django.core.checks import Warning, register
from django.urls import NoReverseMatch, reverse


@register()
def honeywords_deployment_checks(app_configs, **kwargs):
    errors = []

    honeywords_cfg = getattr(settings, "HONEYWORDS", {}) or {}
    on_honeyword = honeywords_cfg.get("ON_HONEYWORD", "log")

    backends = getattr(settings, "AUTHENTICATION_BACKENDS", []) or []
    if "django.contrib.auth.backends.ModelBackend" in backends and any(
        b.endswith("HoneywordsBackend") for b in backends
    ):
        errors.append(
            Warning(
                "ModelBackend is enabled alongside HoneywordsBackend.",
                hint=(
                    "In production, this can allow users without an AmnesiaSet to authenticate "
                    "via the default Django password backend. Prefer using only HoneywordsBackend, "
                    "or ensure all users are initialized and have unusable Django passwords."
                ),
                id="django_honeywords.W001",
            )
        )

    hashers = getattr(settings, "PASSWORD_HASHERS", []) or []
    if any("MD5PasswordHasher" in h for h in hashers):
        errors.append(
            Warning(
                "MD5PasswordHasher is configured.",
                hint="Use Django's default secure hashers (PBKDF2/Argon2/BCrypt) in production.",
                id="django_honeywords.W002",
            )
        )

    hosts = getattr(settings, "ALLOWED_HOSTS", []) or []
    if "*" in hosts:
        errors.append(
            Warning(
                "ALLOWED_HOSTS contains '*' (wildcard).",
                hint="Set explicit hostnames in production.",
                id="django_honeywords.W003",
            )
        )

    if getattr(settings, "DEBUG", False):
        errors.append(
            Warning(
                "DEBUG is True.",
                hint="Set DEBUG=False in production.",
                id="django_honeywords.W004",
            )
        )

    if on_honeyword == "reset":
        try:
            reverse("password_reset")
        except NoReverseMatch:
            errors.append(
                Warning(
                    "ON_HONEYWORD is set to 'reset' but no password reset URLs were found.",
                    hint=(
                        "Configure a reset flow in your project (e.g., include Django's auth password reset URLs) "
                        "or switch ON_HONEYWORD to 'log' or 'lock'."
                    ),
                    id="django_honeywords.W005",
                )
            )

    return errors
