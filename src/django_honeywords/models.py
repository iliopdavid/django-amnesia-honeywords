from django.conf import settings
from django.db import models
from django.utils import timezone

class HoneywordEvent(models.Model):
    OUTCOME_REAL = "real"
    OUTCOME_HONEY = "honey"
    OUTCOME_INVALID = "invalid"

    OUTCOME_CHOICES = [
        # NOTE: In Amnesia, a successful login means a *marked credential* matched.
        # This can be either the real password or a marked honeyword.
        (OUTCOME_REAL, "Marked credential"),
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

class AmnesiaSet(models.Model):
    """Amnesia scheme state (no stored real index)."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="amnesia_set",
    )
    k = models.PositiveSmallIntegerField(default=20)
    p_mark = models.FloatField(default=0.1)
    p_remark = models.FloatField(default=0.01)
    created_at = models.DateTimeField(default=timezone.now)
    algorithm_version = models.CharField(max_length=32, default="amnesia_v1")


class AmnesiaCredential(models.Model):
    aset = models.ForeignKey(
        AmnesiaSet,
        on_delete=models.CASCADE,
        related_name="credentials",
    )
    index = models.PositiveSmallIntegerField()
    password_hash = models.CharField(max_length=256)
    marked = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["aset", "index"],
                name="uniq_amnesia_cred_aset_index",
            ),
        ]