from django.conf import settings

DEFAULTS = {
    "LOG_REAL_SUCCESS": False,
    "ON_HONEYWORD": "log",  # log | reset | lock
    "LOCK_BASE_SECONDS": 60,
    "LOCK_MAX_SECONDS": 3600,

    # Phase 4
    "HONEYCHECKER_MODE": "remote",  # remote | local
    "HONEYCHECKER_URL": "http://localhost:8001",
    "HONEYCHECKER_FAIL_CLOSED": True,
}


def get_setting(name: str):
    return getattr(settings, "HONEYWORDS", {}).get(name, DEFAULTS[name])
