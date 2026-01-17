import pytest
from django.contrib.auth import authenticate, get_user_model

from django_honeywords.models import HoneywordEvent
from django_honeywords.service import initialize_user_honeywords
from django_honeywords.signals import honeyword_detected


class FixedGenerator:
    def __init__(self, words):
        self._words = words

    def honeywords(self, real: str, k: int):
        return self._words


@pytest.mark.django_db
def test_honeyword_logs_event_and_fires_signal(settings):
    settings.AUTHENTICATION_BACKENDS = ["django_honeywords.backend.HoneywordsBackend"]

    fired = {"count": 0}

    def receiver(sender, **kwargs):
        fired["count"] += 1

    honeyword_detected.connect(receiver)

    User = get_user_model()
    u = User.objects.create_user(username="bob")

    real = "Secret123"
    honey = "NotTheRealOne"
    words = [real, honey] + [f"x{i}" for i in range(8)]
    initialize_user_honeywords(u, real, k=10, generator=FixedGenerator(words), real_index=0)

    assert authenticate(username="bob", password=honey) is None

    assert HoneywordEvent.objects.filter(username="bob", outcome=HoneywordEvent.OUTCOME_HONEY).count() == 1
    assert fired["count"] == 1


@pytest.mark.django_db
def test_invalid_logs_event(settings):
    settings.AUTHENTICATION_BACKENDS = ["django_honeywords.backend.HoneywordsBackend"]

    User = get_user_model()
    u = User.objects.create_user(username="alice")
    real = "Passw0rd!"
    words = [real] + [f"h{i}" for i in range(9)]
    initialize_user_honeywords(u, real, k=10, generator=FixedGenerator(words), real_index=0)

    assert authenticate(username="alice", password="Wrong") is None
    assert HoneywordEvent.objects.filter(username="alice", outcome=HoneywordEvent.OUTCOME_INVALID).count() == 1
