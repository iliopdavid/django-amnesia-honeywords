import logging

from django.dispatch import Signal

logger = logging.getLogger(__name__)

# args: user, username, request, event
honeyword_detected = Signal()


def _on_user_password_change(sender, instance, **kwargs):
    """
    Warn if a user's password is changed via set_password() without
    re-initializing their AmnesiaSet. The old credentials would still
    be in the DB, effectively locking the user out.
    """
    if not instance.pk:
        # New user being created — nothing to check yet
        return

    try:
        from .models import AmnesiaSet
        if not AmnesiaSet.objects.filter(user=instance).exists():
            return
    except Exception:
        return

    # Check if the password field actually changed
    try:
        old = sender.objects.filter(pk=instance.pk).values_list("password", flat=True).first()
    except Exception:
        return

    if old is not None and old != instance.password:
        username_field = getattr(instance, "USERNAME_FIELD", "username")
        who = getattr(instance, username_field, None) or instance.pk
        logger.warning(
            "User %s password changed via set_password() but AmnesiaSet was "
            "not re-initialized. Call amnesia_initialize() after password "
            "changes to keep honeywords in sync.",
            who,
        )
