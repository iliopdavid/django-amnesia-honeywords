# Integration guide

This guide focuses on correct application integration.

## Initialization points (required)

Honeywords must be initialized from the **plaintext password**. Typical integration points:

- **Signup**: after creating the user, call `amnesia_initialize_from_settings(user, raw_password)`.
- **Password change**: after a successful password change, re-initialize honeywords using the new plaintext.
- **Admin/migration script**: use the `amnesia_init_user` command for one-off migrations.

## Password storage behavior

`django-amnesia-honeywords` sets the Django password to *unusable* for initialized users to reduce bypass risk if `ModelBackend` is enabled.

Operational consequence:

- Default Django password reset flows typically exclude users with unusable passwords.
- If you want `ON_HONEYWORD="reset"`, wire a reset UX that is compatible with unusable-password users (application-specific).

## Signals

Use `honeyword_detected` to trigger custom alerting or automation.

## Testing

The repository includes `example_project/settings_test.py` for fast tests.

Run tests with:

```bash
pytest -q
```
