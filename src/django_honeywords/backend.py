from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend
from django_honeywords.conf import get_setting
from django_honeywords.events import log_event
from django_honeywords.models import HoneywordEvent
from django_honeywords.signals import honeyword_detected
from django_honeywords.policy import is_locked, apply_reset, apply_lock, get_state


from .service import verify_password


class HoneywordsBackend(BaseBackend):
    """
    Auth backend:
      - returns user on real password
      - returns None on honeyword or invalid
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None

        User = get_user_model()
        user = None
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            pass

        if user is None:
            # log invalid attempt with unknown user
            log_event(user=None, username=username, outcome=HoneywordEvent.OUTCOME_INVALID, request=request)
            return None
        
        # Policy gate: lock + must_reset block auth
        state = get_state(user)
        if is_locked(user):
            log_event(user=user, username=username, outcome=HoneywordEvent.OUTCOME_INVALID, request=request)
            return None
        if state.must_reset:
            log_event(user=user, username=username, outcome=HoneywordEvent.OUTCOME_INVALID, request=request)
            return None

        outcome = verify_password(user, password)

        if outcome == "real":
            if get_setting("LOG_REAL_SUCCESS"):
                log_event(user=user, username=username, outcome=HoneywordEvent.OUTCOME_REAL, request=request)
            return user

        if outcome == "honey":
            event = log_event(
                user=user,
                username=username,
                outcome=HoneywordEvent.OUTCOME_HONEY,
                request=request,
            )

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

        # invalid
        log_event(user=user, username=username, outcome=HoneywordEvent.OUTCOME_INVALID, request=request)
        return None

    def get_user(self, user_id):
        User = get_user_model()
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
