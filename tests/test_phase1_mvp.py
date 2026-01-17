import pytest
from django.contrib.auth import get_user_model
from django_honeywords.service import initialize_user_honeywords, verify_password

class FixedGenerator:
    def __init__(self, words):
        self._words = words
    def honeywords(self, real: str, k: int):
        return self._words

@pytest.mark.django_db
def test_honeyword_detected_deterministic(settings):
    settings.HONEYWORDS = {"HONEYCHECKER_MODE": "local"}

    User = get_user_model()
    u = User.objects.create_user(username="bob")

    real = "Secret123"
    words = [
        real,
        "Secret124",
        "Secret125",
        "Secret126",
        "Secret127",
        "Secret128",
        "Secret129",
        "Secret120",
        "Secret12a",
        "Secret12Z",
    ]

    # Force deterministic real index so the test is strict
    initialize_user_honeywords(u, real, k=10, generator=FixedGenerator(words), real_index=0)

    idx_real = verify_password(u, real)
    assert idx_real == 0

    idx_honey = verify_password(u, "Secret124")
    assert idx_honey == 1

    # And local honeychecker record says only index 0 is real
    assert u.honeychecker_record.real_index == 0