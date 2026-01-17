import pytest
from django.contrib.auth import authenticate, get_user_model

from django_honeywords.service import initialize_user_honeywords


class FixedGenerator:
    def __init__(self, words):
        self._words = words

    def honeywords(self, real: str, k: int):
        assert k == len(self._words)
        assert self._words.count(real) == 1
        return self._words


@pytest.mark.django_db
def test_authenticate_real_password_returns_user(settings):
    settings.AUTHENTICATION_BACKENDS = ["django_honeywords.backend.HoneywordsBackend"]

    User = get_user_model()
    u = User.objects.create_user(username="alice")

    real = "CorrectHorseBatteryStaple"
    words = [real] + [f"h{i}" for i in range(9)]
    initialize_user_honeywords(u, real, k=10, generator=FixedGenerator(words), real_index=0)

    user = authenticate(username="alice", password=real)
    assert user is not None
    assert user.pk == u.pk


@pytest.mark.django_db
def test_authenticate_honeyword_rejected(settings):
    settings.AUTHENTICATION_BACKENDS = ["django_honeywords.backend.HoneywordsBackend"]

    User = get_user_model()
    u = User.objects.create_user(username="bob")

    real = "Secret123"
    honey = "NotTheRealOne"
    words = [real, honey] + [f"x{i}" for i in range(8)]

    # Force the real password to be at index 0, so "honey" can never authenticate.
    initialize_user_honeywords(u, real, k=10, generator=FixedGenerator(words), real_index=0)

    assert authenticate(username="bob", password=real) is not None
    assert authenticate(username="bob", password=honey) is None


@pytest.mark.django_db
def test_authenticate_wrong_password_rejected(settings):
    settings.AUTHENTICATION_BACKENDS = ["django_honeywords.backend.HoneywordsBackend"]

    User = get_user_model()
    u = User.objects.create_user(username="carol")

    real = "Password!"
    words = [real] + [f"h{i}" for i in range(9)]
    initialize_user_honeywords(u, real, k=10, generator=FixedGenerator(words), real_index=0)

    assert authenticate(username="carol", password="TotallyWrong") is None
