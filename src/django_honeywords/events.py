from __future__ import annotations

from typing import Optional

from django.http import HttpRequest

from .models import HoneywordEvent


def _get_ip(request: Optional[HttpRequest]) -> str | None:
    if request is None:
        return None
    # simple MVP: trust REMOTE_ADDR
    return request.META.get("REMOTE_ADDR")


def _get_ua(request: Optional[HttpRequest]) -> str:
    if request is None:
        return ""
    return request.META.get("HTTP_USER_AGENT", "")[:2000]


def log_event(*, user, username: str, outcome: str, request: Optional[HttpRequest]) -> HoneywordEvent:
    return HoneywordEvent.objects.create(
        user=user,
        username=username or "",
        outcome=outcome,
        ip_address=_get_ip(request),
        user_agent=_get_ua(request),
    )
