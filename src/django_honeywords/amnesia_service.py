from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import Protocol

from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from .conf import get_setting

from .models import AmnesiaSet, AmnesiaCredential


class RNG(Protocol):
    def random(self) -> float: ...
    def randbelow(self, n: int) -> int: ...


@dataclass
class DefaultRNG:
    def random(self) -> float:
        # secrets doesn't have random() float, so use SystemRandom
        import random
        return random.SystemRandom().random()

    def randbelow(self, n: int) -> int:
        return secrets.randbelow(n)


def _bernoulli(rng: RNG, p: float) -> bool:
    return rng.random() < p


def amnesia_initialize(
    user,
    real_password: str,
    *,
    k: int = 20,
    p_mark: float = 0.1,
    p_remark: float = 0.01,
    generator=None,
    real_index: int | None = None,   # TESTING ONLY (not stored)
    rng: RNG | None = None,
) -> None:
    """
    Creates an Amnesia set for user:
      - generates k candidate passwords (one is the real password)
      - hashes all candidates
      - sets initial marks: real marked True, others marked Bernoulli(p_mark)

    NOTE: real_index is only to make tests deterministic; Amnesia does NOT store it.
    """
    if k < 2:
        raise ValueError("k must be >= 2")
    if not (0.0 <= p_mark <= 1.0):
        raise ValueError("p_mark must be in [0, 1]")
    if not (0.0 <= p_remark <= 1.0):
        raise ValueError("p_remark must be in [0, 1]")
    if real_index is not None and not (0 <= real_index < k):
        raise ValueError("real_index must be in [0, k)")

    rng = rng or DefaultRNG()

    if generator is None:
        # reuse your simple generator to generate honeywords
        from .generator import SimpleMutationGenerator
        generator = SimpleMutationGenerator()

    words = generator.honeywords(real_password, k)

    # Ensure real_password appears exactly once
    if words.count(real_password) != 1:
        raise ValueError("generator must include the real password exactly once")

    # Place the real password at chosen real_index (or randomly) WITHOUT storing index
    if real_index is None:
        real_index = secrets.randbelow(k)

    # Move real_password to real_index
    current = words.index(real_password)
    words[current], words[real_index] = words[real_index], words[current]

    with transaction.atomic():
        aset, _ = AmnesiaSet.objects.update_or_create(
            user=user,
            defaults={
                "k": k,
                "p_mark": p_mark,
                "p_remark": p_remark,
                "algorithm_version": "amnesia_v1",
            },
        )

        AmnesiaCredential.objects.filter(aset=aset).delete()

        creds = []
        for i in range(k):
            is_real = (i == real_index)
            marked = True if is_real else _bernoulli(rng, p_mark)
            creds.append(
                AmnesiaCredential(
                    aset=aset,
                    index=i,
                    password_hash=make_password(words[i]),
                    marked=marked,
                )
            )
        AmnesiaCredential.objects.bulk_create(creds)

        # Block default Django password auth
        user.set_unusable_password()
        user.save(update_fields=["password"])


def _find_candidate(aset: AmnesiaSet, password: str) -> AmnesiaCredential | None:
    # small k -> linear scan is fine
    for cred in aset.credentials.all().order_by("index"):
        if check_password(password, cred.password_hash):
            return cred
    return None


def amnesia_check(user, password: str, *, rng: RNG | None = None) -> str:
    """
    Returns:
      - "invalid": password not in candidate set
      - "breach": password matches an unmarked candidate (reject login + detect)
      - "success": password matches a marked candidate (accept) and maybe remark
    """
    if not hasattr(user, "amnesia_set"):
        return "invalid"

    rng = rng or DefaultRNG()
    aset: AmnesiaSet = user.amnesia_set

    cred = _find_candidate(aset, password)
    if cred is None:
        return "invalid"

    if not cred.marked:
        # breach detected
        return "breach"

    # success path; maybe remark
    if _bernoulli(rng, aset.p_remark):
        # Remark rule:
        # - keep the used credential marked=True
        # - for each other credential: re-sample marked ~ Bernoulli(p_mark)
        #
        # Important: remarking must NOT monotonically accumulate marks over time,
        # otherwise detection probability collapses as all entries become marked.
        with transaction.atomic():
            cred = AmnesiaCredential.objects.select_for_update().get(pk=cred.pk)
            if not cred.marked:
                # race: another thread unmarked it between our check and lock
                return "breach"

            others = list(
                AmnesiaCredential.objects.select_for_update()
                .filter(aset=aset)
                .exclude(pk=cred.pk)
            )
            for o in others:
                o.marked = _bernoulli(rng, aset.p_mark)

            if others:
                AmnesiaCredential.objects.bulk_update(others, ["marked"])

    return "success"

def amnesia_initialize_from_settings(
    user,
    real_password: str,
    *,
    generator=None,
    rng=None,
    real_index=None,  # test-only
) -> None:
    return amnesia_initialize(
        user,
        real_password,
        k=int(get_setting("AMNESIA_K")),
        p_mark=float(get_setting("AMNESIA_P_MARK")),
        p_remark=float(get_setting("AMNESIA_P_REMARK")),
        generator=generator,
        rng=rng,
        real_index=real_index,
    )