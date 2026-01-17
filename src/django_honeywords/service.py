import secrets
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import AbstractBaseUser
from django.db import transaction

from .conf import get_setting
from .honeychecker_client import set_real_index, HoneycheckerError
from .generator import SimpleMutationGenerator
from .models import HoneywordSet, HoneywordHash, HoneycheckerRecord, find_matching_index

def initialize_user_honeywords(user, real_password: str, k: int = 20, generator=None, real_index: int | None = None) -> None:
    generator = generator or SimpleMutationGenerator()
    words = generator.honeywords(real_password, k)

    # Randomly place the real password among the k candidates
    if real_index is None:
        real_index = secrets.randbelow(k)
    words[0], words[real_index] = words[real_index], words[0]

    if real_index is not None and not (0 <= real_index < k):
        raise ValueError("real_index must be in range [0, k)")


    with transaction.atomic():
        hset, _ = HoneywordSet.objects.update_or_create(
            user=user,
            defaults={"k": k, "algorithm_version": "v1"},
        )
        HoneywordHash.objects.filter(set=hset).delete()

        hashes = [
            HoneywordHash(set=hset, index=i, password_hash=make_password(words[i]))
            for i in range(k)
        ]
        HoneywordHash.objects.bulk_create(hashes)

        mode = get_setting("HONEYCHECKER_MODE")

        if mode == "local":
            HoneycheckerRecord.objects.update_or_create(user=user, defaults={"real_index": real_index})
        else:
            # remote mode
            set_real_index(str(user.pk), real_index)

        user.set_unusable_password()
        user.save(update_fields=["password"])

def verify_password(user, password: str) -> int | None:
    """
    Returns matched index if password matches one of the k hashes, else None.
    Honeychecker (local/remote) decides whether it's real.
    """
    if not hasattr(user, "honeyword_set"):
        return None
    hset = user.honeyword_set
    return find_matching_index(hset, password)