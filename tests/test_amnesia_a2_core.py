import pytest
from django.contrib.auth import get_user_model

from django_honeywords.amnesia_service import amnesia_initialize, amnesia_check


class FixedGenerator:
    def __init__(self, words):
        self._words = words
    def honeywords(self, real: str, k: int):
        return self._words


class FixedRNG:
    """
    Provide a deterministic stream of random() values.
    """
    def __init__(self, values):
        self.values = list(values)
        self.i = 0

    def random(self) -> float:
        v = self.values[self.i % len(self.values)]
        self.i += 1
        return v

    def randbelow(self, n: int) -> int:
        # not used in our tests because we pass real_index
        return 0


@pytest.mark.django_db
def test_amnesia_success_when_marked():
    User = get_user_model()
    u = User.objects.create_user(username="a")

    real = "Secret123"
    words = [real, "h1", "h2", "h3", "h4"]

    # p_mark=0 => non-real start unmarked; real marked True
    amnesia_initialize(
        u, real, k=5, p_mark=0.0, p_remark=0.0,
        generator=FixedGenerator(words),
        real_index=0,
        rng=FixedRNG([0.9]),
    )

    assert amnesia_check(u, real, rng=FixedRNG([0.9])) == "success"


@pytest.mark.django_db
def test_amnesia_breach_when_unmarked_candidate_used():
    User = get_user_model()
    u = User.objects.create_user(username="b")

    real = "Secret123"
    words = [real, "h1", "h2", "h3", "h4"]

    # p_mark=0 => all non-real unmarked
    amnesia_initialize(
        u, real, k=5, p_mark=0.0, p_remark=0.0,
        generator=FixedGenerator(words),
        real_index=0,
        rng=FixedRNG([0.9]),
    )

    # "h1" exists but is unmarked -> breach
    assert amnesia_check(u, "h1", rng=FixedRNG([0.9])) == "breach"


@pytest.mark.django_db
def test_amnesia_invalid_when_not_in_set():
    User = get_user_model()
    u = User.objects.create_user(username="c")

    real = "Secret123"
    words = [real, "h1", "h2", "h3", "h4"]

    amnesia_initialize(
        u, real, k=5, p_mark=0.0, p_remark=0.0,
        generator=FixedGenerator(words),
        real_index=0,
        rng=FixedRNG([0.9]),
    )

    assert amnesia_check(u, "totally-wrong", rng=FixedRNG([0.9])) == "invalid"


@pytest.mark.django_db
def test_amnesia_remark_marks_others_when_p_mark_1(settings):
    """
    Deterministic remark behavior:
      - p_remark=1 => always remark
      - p_mark=1 => all others become marked
    """
    User = get_user_model()
    u = User.objects.create_user(username="d")

    real = "Secret123"
    words = [real, "h1", "h2", "h3", "h4"]

    amnesia_initialize(
        u, real, k=5, p_mark=0.0, p_remark=1.0,
        generator=FixedGenerator(words),
        real_index=0,
        rng=FixedRNG([0.9]),
    )

    # Now update p_mark to 1 so remark marks everyone
    aset = u.amnesia_set
    aset.p_mark = 1.0
    aset.save(update_fields=["p_mark"])

    # random() values don't matter because p_remark=1 and p_mark=1
    assert amnesia_check(u, real, rng=FixedRNG([0.0])) == "success"

    marked = [c.marked for c in u.amnesia_set.credentials.order_by("index")]
    assert marked == [True, True, True, True, True]
