import secrets
from django.contrib.auth.hashers import make_password
from django.db import transaction

from .generator import SimpleMutationGenerator
from .models import HoneywordSet, HoneywordHash, HoneycheckerRecord, find_matching_index

def initialize_user_honeywords(user, real_password: str, k: int = 20, generator=None) -> None:
    generator = generator or SimpleMutationGenerator()
    words = generator.honeywords(real_password, k)

    # Randomly place the real password among the k candidates
    real_index = secrets.randbelow(k)
    words[0], words[real_index] = words[real_index], words[0]

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

        HoneycheckerRecord.objects.update_or_create(user=user, defaults={"real_index": real_index})

def verify_password(user, password: str) -> str:
    """
    Returns: "real", "honey", "invalid"
    """
    if not hasattr(user, "honeyword_set"):
        return "invalid"
    hset = user.honeyword_set
    idx = find_matching_index(hset, password)
    if idx is None:
        return "invalid"
    real_idx = user.honeychecker_record.real_index
    return "real" if idx == real_idx else "honey"