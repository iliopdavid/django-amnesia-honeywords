# django-honeywords

A Django authentication backend implementing the **Amnesia honeywords** scheme for breach detection — without requiring a separate honeychecker service. When attackers crack password hashes and attempt login with a stolen credential, the system detects whether the submitted password is real or a decoy (honeyword), enabling real-time intrusion detection.

## Overview

For each user, instead of storing a single password hash, the system stores `k` hashed candidates (1 real + `k-1` honeywords). Each candidate carries a `marked` boolean flag. The real password is always marked; other candidates are marked with probability `p_mark`.

On login:
1. Find which candidate matches the submitted password
2. If **no match** → reject (invalid password)
3. If **match but unmarked** → breach detected (attacker using a stolen credential)
4. If **match and marked** → success; with probability `p_remark`, re-mark other candidates

The key advantage: **no separate Honeychecker service is needed**. The system never stores which index is the real password — security comes from the probabilistic marking scheme.

## Features

- 🔐 **Drop-in Django Authentication Backend** — seamlessly integrates with Django's auth system
- 🍯 **Honeyword Generation** — simple mutation-based generator (extensible for custom generators)
- 📊 **Event Logging** — tracks all authentication attempts with IP and User-Agent
- 📡 **Django Signals** — hook into honeyword detection events
- 🛡️ **Configurable Policies** — choose between logging, password reset, or account lockout on detection
- 🧠 **No Honeychecker Required** — Amnesia scheme eliminates the need for a separate service

## Architecture

```
┌─────────────────────────────────┐
│          Django App             │
│                                 │
│  ┌───────────────────────────┐  │
│  │  HoneywordsBackend        │  │
│  │  (authentication)         │  │
│  └───────────┬───────────────┘  │
│              │                  │
│  ┌───────────▼───────────────┐  │
│  │  amnesia_check()          │  │
│  │  - find matching cred     │  │
│  │  - check marked flag      │  │
│  │  - probabilistic remark   │  │
│  └───────────┬───────────────┘  │
│              │                  │
│  ┌───────────▼───────────────┐  │
│  │  AmnesiaSet               │  │
│  │  └─ k AmnesiaCredentials  │  │
│  │     (hash + marked flag)  │  │
│  └───────────────────────────┘  │
└─────────────────────────────────┘
```

## Installation

```bash
pip install django-honeywords
```

Or install from source:

```bash
git clone https://github.com/your-username/django-honeywords.git
cd django-honeywords
pip install -e .
```

## Quick Start

### 1. Add to Django Settings

```python
INSTALLED_APPS = [
    # ...
    "django_honeywords.apps.DjangoHoneywordsConfig",
]

AUTHENTICATION_BACKENDS = [
    "django_honeywords.backend.HoneywordsBackend",
]

# Honeywords configuration (all optional — sensible defaults provided)
HONEYWORDS = {
    "AMNESIA_K": 20,            # Number of candidates per user
    "AMNESIA_P_MARK": 0.1,      # Probability of marking a honeyword
    "AMNESIA_P_REMARK": 0.01,   # Probability of re-marking on success
    "ON_HONEYWORD": "log",      # "log" | "reset" | "lock"
    "LOG_REAL_SUCCESS": False,   # Log successful real password logins
    "LOCK_BASE_SECONDS": 60,    # Base lockout duration
    "LOCK_MAX_SECONDS": 3600,   # Maximum lockout duration
}
```

### 2. Run Migrations

```bash
python manage.py migrate django_honeywords
```

### 3. Initialize Honeywords for Users

For new users or to migrate existing users:

```bash
python manage.py amnesia_init_user <username> --password <password>
```

Or programmatically:

```python
from django_honeywords.amnesia_service import amnesia_initialize_from_settings

amnesia_initialize_from_settings(user, "real_password")
```

## Configuration Options

| Setting | Default | Description |
|---------|---------|-------------|
| `AMNESIA_K` | `20` | Number of candidate passwords per user (1 real + k-1 honeywords) |
| `AMNESIA_P_MARK` | `0.1` | Probability of marking each honeyword during initialization |
| `AMNESIA_P_REMARK` | `0.01` | Probability of re-marking other candidates on successful login |
| `ON_HONEYWORD` | `"log"` | Action on honeyword detection: `"log"`, `"reset"`, or `"lock"` |
| `LOG_REAL_SUCCESS` | `False` | Whether to log successful authentications with real passwords |
| `LOCK_BASE_SECONDS` | `60` | Base duration for account lockout |
| `LOCK_MAX_SECONDS` | `3600` | Maximum lockout duration (exponential backoff capped here) |

## Components

### Django Models

- **`AmnesiaSet`** — links a user to their set of `k` candidates with marking parameters
- **`AmnesiaCredential`** — individual password hash with `marked` flag and index
- **`HoneywordEvent`** — audit log of authentication attempts (outcome: real/honey/invalid)
- **`HoneywordUserState`** — tracks lockout and password-reset state per user

### Services

#### `amnesia_service.py`
- `amnesia_initialize(user, password, k, p_mark, p_remark)` — generate and store candidates for a user
- `amnesia_initialize_from_settings(user, password)` — same, using values from `HONEYWORDS` settings
- `amnesia_check(user, password)` — returns `"success"`, `"breach"`, or `"invalid"`

#### `generator.py`
- `SimpleMutationGenerator` — basic character mutation generator for honeywords
  - Creates variants by randomly mutating single characters
  - Extensible: implement your own generator with a `honeywords(real, k)` method

#### `backend.py`
- `HoneywordsBackend` — Django authentication backend
  - Authenticates users via `amnesia_check()`
  - Enforces policy (log/reset/lock) on honeyword detection
  - Fires `honeyword_detected` signal on breach

#### `policy.py`
- `is_locked(user)` — check if user is currently locked out
- `apply_reset(user)` — mark user as requiring password reset
- `apply_lock(user)` — apply exponential backoff lockout

#### `events.py`
- `log_event(user, username, outcome, request)` — record authentication attempt with metadata

### Signals

Connect to the `honeyword_detected` signal to implement custom alerting:

```python
from django_honeywords.signals import honeyword_detected

def on_honeyword(sender, user, username, request, event, **kwargs):
    send_security_alert(
        message=f"Honeyword detected for user {username}",
        ip=event.ip_address,
        user_agent=event.user_agent,
    )

honeyword_detected.connect(on_honeyword)
```

## Management Commands

### `amnesia_init_user`

Initialize honeywords for an existing user:

```bash
python manage.py amnesia_init_user alice --password "SecurePass123"
```

Arguments:
- `username` — username of the user
- `--password` — the user's real password (required)

Parameters `k`, `p_mark`, and `p_remark` are read from the `HONEYWORDS` settings.

## Development

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run specific test groups
pytest tests/test_amnesia_a1_models.py    # Model creation
pytest tests/test_amnesia_a2_core.py      # Core amnesia logic
pytest tests/test_amnesia_a3_backend.py   # Authentication backend
pytest tests/test_amnesia_a4_command.py   # Management command
```

### Project Structure

```
django-honeywords/
├── src/django_honeywords/
│   ├── apps.py              # Django app config
│   ├── amnesia_service.py   # Core amnesia service
│   ├── backend.py           # Authentication backend
│   ├── conf.py              # Settings with defaults
│   ├── events.py            # Event logging
│   ├── generator.py         # Honeyword generation
│   ├── models.py            # Database models
│   ├── policy.py            # Reset/lock policies
│   ├── signals.py           # Django signals
│   └── management/commands/ # Management commands
├── tests/                   # Test suite
└── example_project/         # Example Django project for testing
```

## Security Considerations

1. **Honeyword Quality**: The included `SimpleMutationGenerator` creates basic variants. For stronger security, implement a custom generator that produces indistinguishable honeywords.

2. **Audit Logging**: All authentication attempts are logged to `HoneywordEvent`. Regularly review these logs and set up alerts for honeyword detections.

3. **Parameter Tuning**: The `p_mark` and `p_remark` parameters control the trade-off between false positive rate and detection sensitivity. See the Amnesia paper for guidance on choosing values.

4. **Password Reset Flow**: When `ON_HONEYWORD = "reset"`, users flagged with `must_reset` should be redirected to a password change page. Integrate this with your application's auth flow.

## References

- Juels, A., & Rivest, R. L. (2013). *Honeywords: Making password-cracking detectable*. ACM CCS 2013.
- Chakraborty, N., & Mondal, S. (2021). *On the Amnesia and Sliding-Window Variants of Honeywords*.

## License

MIT License
