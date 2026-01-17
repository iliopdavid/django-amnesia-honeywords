import pytest
from django.contrib.auth import authenticate, get_user_model
from django.utils import timezone
from datetime import timedelta

from django_honeywords.service import initialize_user_honeywords
from django_honeywords.models import HoneywordUserState


class FixedGenerator:
    def __init__(self, words):
        self._words = words

    def honeywords(self, real: str, k: int):
        return self._words


@pytest.mark.django_db
def test_policy_reset_marks_user_and_blocks_real_login(settings):
    settings.AUTHENTICATION_BACKENDS = ["django_honeywords.backend.HoneywordsBackend"]
    settings.HONEYWORDS = {"ON_HONEYWORD": "reset"}

    User = get_user_model()
    u = User.objects.create_user(username="bob")

    real = "Secret123"
    honey = "NotTheRealOne"
    words = [real, honey] + [f"x{i}" for i in range(8)]
    initialize_user_honeywords(u, real, k=10, generator=FixedGenerator(words), real_index=0)

    assert authenticate(username="bob", password=honey) is None

    state = HoneywordUserState.objects.get(user=u)
    assert state.must_reset is True

    # Even real password is blocked until reset flow exists (Phase 5+)
    assert authenticate(username="bob", password=real) is None


@pytest.mark.django_db
def test_policy_lock_blocks_login(settings):
    settings.AUTHENTICATION_BACKENDS = ["django_honeywords.backend.HoneywordsBackend"]
    settings.HONEYWORDS = {"ON_HONEYWORD": "lock", "LOCK_BASE_SECONDS": 300, "LOCK_MAX_SECONDS": 3600}

    User = get_user_model()
    u = User.objects.create_user(username="alice")

    real = "Passw0rd!"
    honey = "HoneyPass!"
    words = [real, honey] + [f"h{i}" for i in range(8)]
    initialize_user_honeywords(u, real, k=10, generator=FixedGenerator(words), real_index=0)

    assert authenticate(username="alice", password=honey) is None

    state = HoneywordUserState.objects.get(user=u)
    assert state.locked_until is not None
    assert state.locked_until > timezone.now()

    # Locked: real password also blocked
    assert authenticate(username="alice", password=real) is None

    # Simulate lock expiry
    state.locked_until = timezone.now() - timedelta(seconds=1)
    state.save(update_fields=["locked_until"])

    # Now real password works again
    assert authenticate(username="alice", password=real) is not None
