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


class HoneywordEvent(models.Model):
    OUTCOME_REAL = "real"
    OUTCOME_HONEY = "honey"
    OUTCOME_INVALID = "invalid"

    OUTCOME_CHOICES = [
        (OUTCOME_REAL, "Real password"),
        (OUTCOME_HONEY, "Honeyword"),
        (OUTCOME_INVALID, "Invalid"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    username = models.CharField(max_length=150, blank=True, default="")
    outcome = models.CharField(max_length=16, choices=OUTCOME_CHOICES)
    created_at = models.DateTimeField(default=timezone.now)

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")

class HoneywordUserState(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="honeywords_state")

    must_reset = models.BooleanField(default=False)

    locked_until = models.DateTimeField(null=True, blank=True)
    lock_count = models.PositiveIntegerField(default=0)
    last_lock_at = models.DateTimeField(null=True, blank=True)

def find_matching_index(hset: HoneywordSet, password: str) -> int | None:
    # Small k -> simple linear scan is fine for MVP
    for hw in hset.hashes.all().order_by("index"):
        if check_password(password, hw.password_hash):
            return hw.index
    return None