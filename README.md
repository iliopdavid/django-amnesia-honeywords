# django-honeywords

A Django authentication backend implementing **honeywords** for breach detection. When attackers crack password hashes and attempt login with a stolen credential, the system can detect whether the submitted password is the real one or a decoy (honeyword), enabling real-time intrusion detection.

## Overview

Honeywords are decoy passwords stored alongside the real password hash. For each user, instead of storing a single password hash, the system stores `k` hashes (e.g., 20): one real password and `k-1` honeywords. Only a separate service (the **Honeychecker**) knows which index corresponds to the real password.

If an attacker steals password hashes and cracks them, they cannot distinguish the real password from honeywords. When they attempt to log in with a honeyword, the system detects the breach attempt.

## Features

- 🔐 **Drop-in Django Authentication Backend** - Seamlessly integrates with Django's auth system
- 🍯 **Honeyword Generation** - Simple mutation-based generator (extensible for custom generators)
- 🔍 **Dual Honeychecker Modes** - Local (MVP/testing) or Remote (production-ready separation)
- 📊 **Event Logging** - Tracks all authentication attempts with IP and User-Agent
- 📡 **Django Signals** - Hook into honeyword detection events
- 🛡️ **Configurable Policies** - Choose between logging, password reset, or account lockout on detection
- 🐳 **Docker-ready Honeychecker** - Isolated FastAPI microservice with PostgreSQL backend

## Architecture

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│   Django App    │      │   Honeychecker  │      │   PostgreSQL    │
│                 │      │    (FastAPI)    │      │                 │
│ ┌─────────────┐ │      │                 │      │ ┌─────────────┐ │
│ │ Honeywords  │ │ HTTP │ ┌─────────────┐ │      │ │ real_index  │ │
│ │  Backend    │◄──────►│ │  /set       │ │◄────►│ │   table     │ │
│ └─────────────┘ │      │ │  /verify    │ │      │ └─────────────┘ │
│                 │      │ └─────────────┘ │      │                 │
│ ┌─────────────┐ │      └─────────────────┘      └─────────────────┘
│ │ k password  │ │
│ │   hashes    │ │
│ └─────────────┘ │
└─────────────────┘
```

The key security principle: the Django application stores all `k` password hashes but does **not** know which one is real. The Honeychecker service (ideally on separate infrastructure) holds only the mapping of `user_id → real_index`.

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

# Honeywords configuration
HONEYWORDS = {
    "HONEYCHECKER_MODE": "local",  # "local" for testing, "remote" for production
    "HONEYCHECKER_URL": "http://localhost:8001",  # Only used in remote mode
    "HONEYCHECKER_FAIL_CLOSED": True,  # Deny auth if honeychecker is unreachable
    "ON_HONEYWORD": "log",  # "log" | "reset" | "lock"
    "LOG_REAL_SUCCESS": False,  # Log successful real password logins
    "LOCK_BASE_SECONDS": 60,  # Base lockout duration
    "LOCK_MAX_SECONDS": 3600,  # Maximum lockout duration
}
```

### 2. Run Migrations

From your Django project directory (where `manage.py` is located):

```bash
python manage.py migrate django_honeywords
```

### 3. Initialize Honeywords for Users

For new users or to migrate existing users, run from your Django project:

```bash
python manage.py honeywords_init_user <username> --password <password> --k 20
```

Or programmatically:

```python
from django_honeywords.service import initialize_user_honeywords

initialize_user_honeywords(user, "real_password", k=20)
```

### 4. (Production) Start the Remote Honeychecker

```bash
cd honeychecker
docker-compose up -d
```

This starts:
- **honeychecker**: FastAPI service on port 8001
- **honeychecker-db**: PostgreSQL database on port 5433

## Configuration Options

| Setting | Default | Description |
|---------|---------|-------------|
| `HONEYCHECKER_MODE` | `"remote"` | `"local"` stores real index in Django DB; `"remote"` uses separate honeychecker service |
| `HONEYCHECKER_URL` | `"http://localhost:8001"` | URL of the remote honeychecker service |
| `HONEYCHECKER_FAIL_CLOSED` | `True` | If honeychecker is unreachable, deny authentication |
| `ON_HONEYWORD` | `"log"` | Action on honeyword detection: `"log"`, `"reset"`, or `"lock"` |
| `LOG_REAL_SUCCESS` | `False` | Whether to log successful authentications with real passwords |
| `LOCK_BASE_SECONDS` | `60` | Base duration for account lockout |
| `LOCK_MAX_SECONDS` | `3600` | Maximum lockout duration (exponential backoff capped here) |

## Components

### Django Models

- **`HoneywordSet`** - Links a user to their set of `k` honeyword hashes
- **`HoneywordHash`** - Individual password hashes with their index
- **`HoneycheckerRecord`** - (Local mode only) Stores the real password index
- **`HoneywordEvent`** - Audit log of authentication attempts
- **`HoneywordUserState`** - Tracks lockout and reset states per user

### Services

#### `service.py`
- `initialize_user_honeywords(user, password, k=20)` - Generate and store honeywords for a user
- `verify_password(user, password)` - Check if password matches any of the k hashes (returns index or None)

#### `generator.py`
- `SimpleMutationGenerator` - Basic character mutation generator for honeywords
  - Creates variants by randomly mutating single characters
  - **Note**: Not indistinguishability-strong; suitable for MVP/testing

#### `backend.py`
- `HoneywordsBackend` - Django authentication backend
  - Authenticates users against honeyword sets
  - Consults honeychecker (local/remote) to verify real vs honey
  - Enforces policy (log/reset/lock) on honeyword detection

#### `policy.py`
- `is_locked(user)` - Check if user is currently locked out
- `apply_reset(user)` - Mark user as requiring password reset
- `apply_lock(user)` - Apply exponential backoff lockout

#### `events.py`
- `log_event(user, username, outcome, request)` - Record authentication attempt with metadata

### Signals

Connect to the `honeyword_detected` signal to implement custom alerting:

```python
from django_honeywords.signals import honeyword_detected

def on_honeyword(sender, user, username, request, event, **kwargs):
    # Send alert to security team
    send_security_alert(
        message=f"Honeyword detected for user {username}",
        ip=event.ip_address,
        user_agent=event.user_agent,
    )

honeyword_detected.connect(on_honeyword)
```

### Remote Honeychecker Service

A standalone FastAPI microservice that stores only user_id → real_index mappings:

**Endpoints:**
- `POST /set` - Store or update real index for a user
  ```json
  {"user_id": "123", "real_index": 7}
  ```
- `POST /verify` - Check if a candidate index is the real one
  ```json
  {"user_id": "123", "candidate_index": 7}
  ```
  Response: `{"is_real": true}`

## Management Commands

These commands are available in your Django project after installing `django-honeywords`.

### `honeywords_init_user`

Initialize honeywords for an existing user:

```bash
# Run from your Django project directory
python manage.py honeywords_init_user alice --password "SecurePass123" --k 20
```

Arguments:
- `username` - Username of the user
- `--password` - The user's real password (required)
- `--k` - Number of honeywords including real password (default: 20)

## Development

### Running Tests

The package includes an `example_project/` directory with Django settings for testing.

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run specific test phases
pytest tests/test_phase1_mvp.py      # Core honeyword functionality
pytest tests/test_phase2_backend.py  # Authentication backend
pytest tests/test_phase3_events.py   # Event logging and signals
pytest tests/test_phase3_policy.py   # Reset and lock policies
pytest tests/test_phase4_remote.py   # Remote honeychecker integration
```

### Local Development with Docker

Start the honeychecker service for integration testing:

```bash
docker-compose up -d
```

Services:
- Honeychecker API: http://localhost:8001
- PostgreSQL: localhost:5433

### Project Structure

```
django-honeywords/
├── src/django_honeywords/
│   ├── apps.py              # Django app config
│   ├── backend.py           # Authentication backend
│   ├── conf.py              # Settings with defaults
│   ├── events.py            # Event logging
│   ├── generator.py         # Honeyword generation
│   ├── honeychecker_client.py  # Remote honeychecker client
│   ├── models.py            # Database models
│   ├── policy.py            # Reset/lock policies
│   ├── service.py           # Core honeyword service
│   ├── signals.py           # Django signals
│   └── management/commands/ # Management commands
├── honeychecker/            # Standalone honeychecker service
│   ├── Dockerfile
│   ├── requirements.txt
│   └── honeychecker/
│       ├── app.py           # FastAPI application
│       ├── db.py            # SQLAlchemy setup
│       └── models.py        # Honeychecker models
├── tests/                   # Test suite
├── example_project/         # Example Django project
└── docker-compose.yml       # Docker setup for honeychecker
```

## Security Considerations

1. **Separate Infrastructure**: In production, run the honeychecker on separate infrastructure from your Django application. If an attacker compromises your web server, they shouldn't be able to access the honeychecker's database.

2. **Fail Closed**: By default (`HONEYCHECKER_FAIL_CLOSED=True`), authentication fails if the honeychecker is unreachable. This prevents attackers from bypassing detection by DoS'ing the honeychecker.

3. **Honeyword Quality**: The included `SimpleMutationGenerator` creates basic variants. For stronger security, implement a custom generator that produces indistinguishable honeywords (e.g., using similar character patterns, common password structures).

4. **Audit Logging**: All authentication attempts are logged to `HoneywordEvent`. Regularly review these logs and set up alerts for honeyword detections.

5. **Network Security**: Secure the honeychecker API endpoint. Use TLS, API keys, or network-level restrictions to prevent unauthorized access.

## Roadmap

- [ ] Password reset flow integration
- [ ] Admin interface for honeyword management
- [ ] Advanced honeyword generators (model-based, AI-assisted)
- [ ] Metrics and monitoring integration
- [ ] Multi-factor authentication support
- [ ] Rate limiting on honeychecker endpoints

## References

- Juels, A., & Rivest, R. L. (2013). *Honeywords: Making password-cracking detectable*. ACM CCS 2013.

## License

MIT License
