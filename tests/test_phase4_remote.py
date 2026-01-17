import pytest
from unittest.mock import patch
from django.contrib.auth import authenticate, get_user_model

from django_honeywords.service import initialize_user_honeywords


class FixedGenerator:
    def __init__(self, words):
        self._words = words
    def honeywords(self, real: str, k: int):
        return self._words


@pytest.mark.django_db
def test_remote_honeychecker_real_allows_login(settings):
    settings.AUTHENTICATION_BACKENDS = ["django_honeywords.backend.HoneywordsBackend"]
    settings.HONEYWORDS = {"HONEYCHECKER_MODE": "remote"}

    User = get_user_model()
    u = User.objects.create_user(username="alice")

    real = "RealPass"
    words = [real] + [f"h{i}" for i in range(9)]

    with patch("django_honeywords.service.set_real_index") as set_idx, \
         patch("django_honeywords.backend.verify_index", return_value=True):
        initialize_user_honeywords(u, real, k=10, generator=FixedGenerator(words), real_index=0)
        set_idx.assert_called_once()

        assert authenticate(username="alice", password=real) is not None


@pytest.mark.django_db
def test_remote_honeychecker_honey_rejects_login(settings):
    settings.AUTHENTICATION_BACKENDS = ["django_honeywords.backend.HoneywordsBackend"]
    settings.HONEYWORDS = {"HONEYCHECKER_MODE": "remote"}

    User = get_user_model()
    u = User.objects.create_user(username="bob")

    real = "RealPass"
    honey = "HoneyPass"
    words = [real, honey] + [f"x{i}" for i in range(8)]

    with patch("django_honeywords.service.set_real_index"), \
         patch("django_honeywords.backend.verify_index", return_value=False):
        initialize_user_honeywords(u, real, k=10, generator=FixedGenerator(words), real_index=0)
        assert authenticate(username="bob", password=honey) is None