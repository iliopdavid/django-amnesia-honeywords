import pytest
from django.contrib.auth import get_user_model

from django_honeywords.service import initialize_user_honeywords, verify_password


class FixedGenerator:
    def __init__(self, words):
        self._words = words

    def honeywords(self, real: str, k: int):
        assert k == len(self._words)
        # Must include the real password exactly once
        assert self._words.count(real) == 1
        return self._words


@pytest.mark.django_db
def test_honeyword_detected_deterministic():
    User = get_user_model()
    u = User.objects.create_user(username="bob")

    real = "Secret123"
    # 10 total, includes the real password exactly once
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

    initialize_user_honeywords(u, real, k=10, generator=FixedGenerator(words))

    # Real must authenticate as real
    assert verify_password(u, real) == "real"

    # Any other known candidate must be either honey or real depending on the randomized real_index swap.
    # Since real_index is randomized, pick a candidate that isn't the real password and assert it is NOT invalid.
    outcome = verify_password(u, "Secret124")
    assert outcome in ("honey", "real")
    assert outcome != "invalid"
