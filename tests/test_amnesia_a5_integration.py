"""
Integration tests covering gaps:
  - breach → policy (reset / lock)
  - honeyword_detected signal fires
  - locked-out user rejected
  - amnesia_initialize_from_settings()
  - re-initialization (password change)
  - event logging assertions
  - generator safeguard
  - password change warning signal
"""
import logging

import pytest
from django.contrib.auth import authenticate, get_user_model
from django.core.management import call_command
from django.utils import timezone

from django_honeywords.amnesia_service import (
    amnesia_check,
    amnesia_initialize,
    amnesia_initialize_from_settings,
)
from django_honeywords.generator import SimpleMutationGenerator
from django_honeywords.models import AmnesiaSet, HoneywordEvent, HoneywordUserState
from django_honeywords.policy import apply_lock, apply_reset, get_state, is_locked


# ── helpers ──────────────────────────────────────────────────────────


class FixedGenerator:
    def __init__(self, words):
        self._words = words

    def honeywords(self, real: str, k: int):
        return list(self._words)


class FixedRNG:
    def __init__(self, values):
        self.values = list(values)
        self.i = 0

    def random(self) -> float:
        v = self.values[self.i % len(self.values)]
        self.i += 1
        return v

    def randbelow(self, n: int) -> int:
        return 0


def _make_user(username, password="Secret123", k=5):
    """Create user and initialize amnesia with deterministic settings."""
    User = get_user_model()
    u = User.objects.create_user(username=username)
    words = [password, "h1", "h2", "h3", "h4"]
    amnesia_initialize(
        u,
        password,
        k=k,
        p_mark=0.0,
        p_remark=0.0,
        generator=FixedGenerator(words),
        real_index=0,
        rng=FixedRNG([0.9]),
    )
    return u


# ── breach → policy tests ───────────────────────────────────────────


@pytest.mark.django_db
def test_breach_triggers_reset_policy(settings):
    settings.AUTHENTICATION_BACKENDS = ["django_honeywords.backend.HoneywordsBackend"]
    settings.HONEYWORDS = {"ON_HONEYWORD": "reset"}

    u = _make_user("reset_user")

    # Login with honeyword → breach → reset policy applied
    result = authenticate(username="reset_user", password="h1")
    assert result is None

    state = get_state(u)
    assert state.must_reset is True


@pytest.mark.django_db
def test_breach_triggers_lock_policy(settings):
    settings.AUTHENTICATION_BACKENDS = ["django_honeywords.backend.HoneywordsBackend"]
    settings.HONEYWORDS = {"ON_HONEYWORD": "lock", "LOCK_BASE_SECONDS": 60, "LOCK_MAX_SECONDS": 3600}

    u = _make_user("lock_user")

    result = authenticate(username="lock_user", password="h1")
    assert result is None

    state = get_state(u)
    assert state.locked_until is not None
    assert state.locked_until > timezone.now()
    assert state.lock_count == 1


@pytest.mark.django_db
def test_breach_with_log_policy_does_not_lock_or_reset(settings):
    settings.AUTHENTICATION_BACKENDS = ["django_honeywords.backend.HoneywordsBackend"]
    settings.HONEYWORDS = {"ON_HONEYWORD": "log"}

    u = _make_user("log_user")

    result = authenticate(username="log_user", password="h1")
    assert result is None

    state = get_state(u)
    assert state.must_reset is False
    assert state.locked_until is None


# ── signal tests ─────────────────────────────────────────────────────


@pytest.mark.django_db
def test_honeyword_detected_signal_fires(settings):
    settings.AUTHENTICATION_BACKENDS = ["django_honeywords.backend.HoneywordsBackend"]
    settings.HONEYWORDS = {"ON_HONEYWORD": "log"}

    from django_honeywords.signals import honeyword_detected

    received = []

    def handler(sender, user, username, request, event, **kwargs):
        received.append({
            "user": user,
            "username": username,
            "event": event,
        })

    honeyword_detected.connect(handler)
    try:
        u = _make_user("sig_user")
        authenticate(username="sig_user", password="h1")

        assert len(received) == 1
        assert received[0]["username"] == "sig_user"
        assert received[0]["event"].outcome == "honey"
    finally:
        honeyword_detected.disconnect(handler)


@pytest.mark.django_db
def test_signal_not_fired_on_success(settings):
    settings.AUTHENTICATION_BACKENDS = ["django_honeywords.backend.HoneywordsBackend"]

    from django_honeywords.signals import honeyword_detected

    received = []
    honeyword_detected.connect(lambda **kw: received.append(1))
    try:
        _make_user("sig_ok_user")
        authenticate(username="sig_ok_user", password="Secret123")
        assert len(received) == 0
    finally:
        honeyword_detected.disconnect()


# ── locked-out user tests ───────────────────────────────────────────


@pytest.mark.django_db
def test_locked_user_rejected_even_with_real_password(settings):
    settings.AUTHENTICATION_BACKENDS = ["django_honeywords.backend.HoneywordsBackend"]

    u = _make_user("locked_real")
    apply_lock(u, base_seconds=3600, max_seconds=3600)

    # Real password should still be rejected while locked
    result = authenticate(username="locked_real", password="Secret123")
    assert result is None


@pytest.mark.django_db
def test_must_reset_user_rejected(settings):
    settings.AUTHENTICATION_BACKENDS = ["django_honeywords.backend.HoneywordsBackend"]

    u = _make_user("reset_real")
    apply_reset(u)

    result = authenticate(username="reset_real", password="Secret123")
    assert result is None


# ── amnesia_initialize_from_settings tests ───────────────────────────


@pytest.mark.django_db
def test_amnesia_initialize_from_settings(settings):
    settings.HONEYWORDS = {"AMNESIA_K": 5, "AMNESIA_P_MARK": 0.0, "AMNESIA_P_REMARK": 0.0}

    User = get_user_model()
    u = User.objects.create_user(username="settings_user")

    amnesia_initialize_from_settings(u, "MyPass1")

    aset = AmnesiaSet.objects.get(user=u)
    assert aset.k == 5
    assert aset.p_mark == 0.0
    assert aset.p_remark == 0.0
    assert aset.credentials.count() == 5

    # Real password works
    assert amnesia_check(u, "MyPass1") == "success"


# ── re-initialization tests ─────────────────────────────────────────


@pytest.mark.django_db
def test_reinitialize_replaces_old_credentials():
    User = get_user_model()
    u = User.objects.create_user(username="reinit_user")

    words_v1 = ["OldPass1", "old_h1", "old_h2", "old_h3", "old_h4"]
    amnesia_initialize(
        u, "OldPass1", k=5, p_mark=0.0, p_remark=0.0,
        generator=FixedGenerator(words_v1), real_index=0, rng=FixedRNG([0.9]),
    )
    assert amnesia_check(u, "OldPass1") == "success"

    # Re-initialize with new password
    words_v2 = ["NewPass2", "new_h1", "new_h2", "new_h3", "new_h4"]
    amnesia_initialize(
        u, "NewPass2", k=5, p_mark=0.0, p_remark=0.0,
        generator=FixedGenerator(words_v2), real_index=0, rng=FixedRNG([0.9]),
    )

    # Old password no longer works
    assert amnesia_check(u, "OldPass1") == "invalid"
    # New one does
    assert amnesia_check(u, "NewPass2") == "success"
    # Still exactly k credentials
    assert u.amnesia_set.credentials.count() == 5


# ── event logging tests ─────────────────────────────────────────────


@pytest.mark.django_db
def test_breach_creates_honey_event(settings):
    settings.AUTHENTICATION_BACKENDS = ["django_honeywords.backend.HoneywordsBackend"]
    settings.HONEYWORDS = {"ON_HONEYWORD": "log"}

    u = _make_user("ev_honey")

    HoneywordEvent.objects.all().delete()
    authenticate(username="ev_honey", password="h1")

    events = list(HoneywordEvent.objects.filter(user=u))
    assert len(events) == 1
    assert events[0].outcome == "honey"
    assert events[0].username == "ev_honey"


@pytest.mark.django_db
def test_invalid_creates_invalid_event(settings):
    settings.AUTHENTICATION_BACKENDS = ["django_honeywords.backend.HoneywordsBackend"]

    u = _make_user("ev_inv")

    HoneywordEvent.objects.all().delete()
    authenticate(username="ev_inv", password="totally-wrong")

    events = list(HoneywordEvent.objects.filter(user=u))
    assert len(events) == 1
    assert events[0].outcome == "invalid"


@pytest.mark.django_db
def test_success_logs_event_when_enabled(settings):
    settings.AUTHENTICATION_BACKENDS = ["django_honeywords.backend.HoneywordsBackend"]
    settings.HONEYWORDS = {"LOG_REAL_SUCCESS": True}

    u = _make_user("ev_real")

    HoneywordEvent.objects.all().delete()
    result = authenticate(username="ev_real", password="Secret123")
    assert result is not None

    events = list(HoneywordEvent.objects.filter(user=u))
    assert len(events) == 1
    assert events[0].outcome == "real"


@pytest.mark.django_db
def test_success_does_not_log_when_disabled(settings):
    settings.AUTHENTICATION_BACKENDS = ["django_honeywords.backend.HoneywordsBackend"]
    settings.HONEYWORDS = {"LOG_REAL_SUCCESS": False}

    _make_user("ev_quiet")

    HoneywordEvent.objects.all().delete()
    authenticate(username="ev_quiet", password="Secret123")

    assert HoneywordEvent.objects.count() == 0


@pytest.mark.django_db
def test_nonexistent_user_logs_invalid_event(settings):
    settings.AUTHENTICATION_BACKENDS = ["django_honeywords.backend.HoneywordsBackend"]

    HoneywordEvent.objects.all().delete()
    authenticate(username="ghost", password="anything")

    events = list(HoneywordEvent.objects.filter(username="ghost"))
    assert len(events) == 1
    assert events[0].outcome == "invalid"
    assert events[0].user is None


# ── generator safeguard test ─────────────────────────────────────────


def test_generator_safeguard_on_short_password():
    gen = SimpleMutationGenerator()
    # Force _random_mutate to always return the same thing → can't produce k distinct
    gen._random_mutate = lambda s: "same"
    with pytest.raises(RuntimeError, match="Could not generate"):
        gen.honeywords("a", k=5)


# ── password change warning test ─────────────────────────────────────


@pytest.mark.django_db
def test_password_change_warning(settings, caplog):
    settings.AUTHENTICATION_BACKENDS = ["django_honeywords.backend.HoneywordsBackend"]

    u = _make_user("warn_user")

    with caplog.at_level(logging.WARNING, logger="django_honeywords.signals"):
        u.set_password("NewPassword999")
        u.save()

    assert any("AmnesiaSet was not re-initialized" in msg for msg in caplog.messages)


# ── exponential backoff lock test ────────────────────────────────────


@pytest.mark.django_db
def test_lock_exponential_backoff():
    User = get_user_model()
    u = User.objects.create_user(username="backoff_user")

    apply_lock(u, base_seconds=60, max_seconds=3600)
    state1 = get_state(u)
    assert state1.lock_count == 1

    apply_lock(u, base_seconds=60, max_seconds=3600)
    state2 = get_state(u)
    assert state2.lock_count == 2
    # Second lock should be longer than first
    assert state2.locked_until > state1.locked_until
