# Deployment checklist

This document covers practical steps for deploying `django-amnesia-honeywords` safely.

## 1) Settings sanity

- Use secure settings:
  - `DEBUG = False`
  - `ALLOWED_HOSTS` set to explicit hostnames
  - Secure cookie/HTTPS settings (e.g., `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_SSL_REDIRECT`)
- Use a strong password hasher (PBKDF2/Argon2/BCrypt). Do not use MD5 in production.

Run Django system checks:

```bash
python manage.py check
```

`django-amnesia-honeywords` adds warnings for common foot-guns (wildcard hosts, MD5 hasher, backend fallback, and reset policy without reset URLs).

## 2) Authentication backends

Production recommendation:

- Use only `django_honeywords.backend.HoneywordsBackend`.

If you also enable `django.contrib.auth.backends.ModelBackend`, users who were not initialized with an AmnesiaSet may still authenticate via the default Django password backend (bypass risk).

## 3) Initialize users

You must initialize honeywords while you have the plaintext password:

- At signup
- When a user changes their password
- During migration (scripted)

If you cannot obtain plaintext passwords for existing accounts, you cannot retroactively initialize them without a forced reset or a re-enrollment flow.

## 4) Choose incident response policy

Configure `HONEYWORDS["ON_HONEYWORD"]`:

- `"log"`: log and signal only (alert-only)
- `"lock"`: temporary lockout (containment)
- `"reset"`: mark user as needing reset (`must_reset=True`) and block authentication until your app rotates credentials

If you use `"reset"`, ensure your application provides a password reset/change UX.

## 5) Monitoring

- Connect to the `honeyword_detected` signal to alert (email/Slack/SIEM).
- Review `HoneywordEvent` entries (especially outcome `honey`).
