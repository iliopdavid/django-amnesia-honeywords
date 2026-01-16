from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.utils import timezone

class HoneywordSet(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="honeyword_set")
    k = models.PositiveSmallIntegerField(default=20)
    created_at = models.DateTimeField(default=timezone.now)
    algorithm_version = models.CharField(max_length=32, default="v1")

class HoneywordHash(models.Model):
    set = models.ForeignKey(HoneywordSet, on_delete=models.CASCADE, related_name="hashes")
    index = models.PositiveSmallIntegerField()
    password_hash = models.CharField(max_length=256)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["set", "index"], name="uniq_honeywordhash_set_index"),
        ]

class HoneycheckerRecord(models.Model):
    """
    MVP honeychecker: real index stored locally.
    Later Phase 4 replaces this with remote honeychecker service.
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="honeychecker_record")
    real_index = models.PositiveSmallIntegerField()

def find_matching_index(hset: HoneywordSet, password: str) -> int | None:
    # Small k -> simple linear scan is fine for MVP
    for hw in hset.hashes.all().order_by("index"):
        if check_password(password, hw.password_hash):
            return hw.index
    return None