import pytest
from django.contrib.auth import authenticate, get_user_model

from django_honeywords.amnesia_service import amnesia_initialize


class FixedGenerator:
    def __init__(self, words):
        self._words = words
    def honeywords(self, real: str, k: int):
        return self._words


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


@pytest.mark.django_db
def test_backend_amnesia_success_authenticates(settings):
    settings.AUTHENTICATION_BACKENDS = ["django_honeywords.backend.HoneywordsBackend"]

    User = get_user_model()
    u = User.objects.create_user(username="alice")

    real = "Secret123"
    words = [real, "h1", "h2", "h3", "h4"]

    amnesia_initialize(
        u, real,
        k=5, p_mark=0.0, p_remark=0.0,
        generator=FixedGenerator(words),
        real_index=0,
        rng=FixedRNG([0.9]),
    )

    assert authenticate(username="alice", password=real) is not None


@pytest.mark.django_db
def test_backend_amnesia_breach_rejects(settings):
    settings.AUTHENTICATION_BACKENDS = ["django_honeywords.backend.HoneywordsBackend"]

    User = get_user_model()
    u = User.objects.create_user(username="bob")

    real = "Secret123"
    words = [real, "h1", "h2", "h3", "h4"]

    amnesia_initialize(
        u, real,
        k=5, p_mark=0.0, p_remark=0.0,
        generator=FixedGenerator(words),
        real_index=0,
        rng=FixedRNG([0.9]),
    )

    # "h1" exists but unmarked => breach => auth rejected
    assert authenticate(username="bob", password="h1") is None


@pytest.mark.django_db
def test_backend_amnesia_invalid_rejects(settings):
    settings.AUTHENTICATION_BACKENDS = ["django_honeywords.backend.HoneywordsBackend"]

    User = get_user_model()
    u = User.objects.create_user(username="carol")

    real = "Secret123"
    words = [real, "h1", "h2", "h3", "h4"]

    amnesia_initialize(
        u, real,
        k=5, p_mark=0.0, p_remark=0.0,
        generator=FixedGenerator(words),
        real_index=0,
        rng=FixedRNG([0.9]),
    )

    assert authenticate(username="carol", password="wrong") is None


@pytest.mark.django_db
def test_backend_inactive_user_rejected(settings):
    settings.AUTHENTICATION_BACKENDS = ["django_honeywords.backend.HoneywordsBackend"]

    User = get_user_model()
    u = User.objects.create_user(username="inactive")
    u.is_active = False
    u.save(update_fields=["is_active"])

    real = "Secret123"
    words = [real, "h1", "h2", "h3", "h4"]

    amnesia_initialize(
        u, real,
        k=5, p_mark=0.0, p_remark=0.0,
        generator=FixedGenerator(words),
        real_index=0,
        rng=FixedRNG([0.9]),
    )

    assert authenticate(username="inactive", password=real) is None
