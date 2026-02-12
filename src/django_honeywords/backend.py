from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend
from django.utils import timezone

from django_honeywords.amnesia_service import amnesia_check
from django_honeywords.conf import get_setting
from django_honeywords.events import log_event
from django_honeywords.models import HoneywordEvent
from django_honeywords.policy import apply_lock, apply_reset, get_state
from django_honeywords.signals import honeyword_detected


class HoneywordsBackend(BaseBackend):
    """Auth backend (Amnesia-only).

    Returns user on success, otherwise None.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if password is None:
            return None

        User = get_user_model()
        username_field = getattr(User, "USERNAME_FIELD", "username")
        if username is None:
            username = kwargs.get(username_field)

        if username is None:
            return None
        try:
            # Respect custom user models and normalization rules.
            user = User._default_manager.get_by_natural_key(username)
        except User.DoesNotExist:
            log_event(user=None, username=username, outcome=HoneywordEvent.OUTCOME_INVALID, request=request)
            return None

        # Policy gate: lock + must_reset block auth
        state = get_state(user)
        locked = state.locked_until is not None and state.locked_until > timezone.now()
        if locked or state.must_reset:
            log_event(user=user, username=username, outcome=HoneywordEvent.OUTCOME_INVALID, request=request)
            return None

        verdict = amnesia_check(user, password)

        if verdict == "success":
            if get_setting("LOG_REAL_SUCCESS"):
                # In Amnesia, success means a *marked* credential matched (real or honeyword).
                log_event(user=user, username=username, outcome=HoneywordEvent.OUTCOME_REAL, request=request)
            return user

        if verdict == "breach":
            event = log_event(user=user, username=username, outcome=HoneywordEvent.OUTCOME_HONEY, request=request)
            honeyword_detected.send(
                sender=self.__class__,
                user=user,
                username=username,
                request=request,
                event=event,
            )

            action = get_setting("ON_HONEYWORD")
            if action == "reset":
                apply_reset(user)
            elif action == "lock":
                apply_lock(
                    user,
                    base_seconds=get_setting("LOCK_BASE_SECONDS"),
                    max_seconds=get_setting("LOCK_MAX_SECONDS"),
                )
            return None

        # "invalid"
        log_event(user=user, username=username, outcome=HoneywordEvent.OUTCOME_INVALID, request=request)
        return None

    def get_user(self, user_id):
        User = get_user_model()
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None