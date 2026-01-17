from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend

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

        # Support username or email-style login later if needed.
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return None

        outcome = verify_password(user, password)
        if outcome == "real":
            return user

        # honey or invalid => reject
        return None

    def get_user(self, user_id):
        User = get_user_model()
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
