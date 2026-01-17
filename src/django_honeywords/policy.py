from __future__ import annotations

from datetime import timedelta
from django.utils import timezone

from .models import HoneywordUserState


def get_state(user) -> HoneywordUserState:
    state, _ = HoneywordUserState.objects.get_or_create(user=user)
    return state


def is_locked(user) -> bool:
    state = get_state(user)
    return state.locked_until is not None and state.locked_until > timezone.now()


def apply_reset(user) -> None:
    state = get_state(user)
    if not state.must_reset:
        state.must_reset = True
        state.save(update_fields=["must_reset"])


def apply_lock(user, base_seconds: int = 60, max_seconds: int = 3600) -> None:
    """
    Throttled lockout to reduce DoS risk.
    lock duration = min(base * 2^lock_count, max)
    """
    state = get_state(user)
    now = timezone.now()

    # If lock expired, keep count but reset timing basis
    duration = base_seconds * (2 ** min(state.lock_count, 10))
    duration = min(duration, max_seconds)

    state.lock_count += 1
    state.last_lock_at = now
    state.locked_until = now + timedelta(seconds=duration)
    state.save(update_fields=["lock_count", "last_lock_at", "locked_until"])
