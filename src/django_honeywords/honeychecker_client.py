from __future__ import annotations
import requests

from .conf import get_setting


class HoneycheckerError(RuntimeError):
    pass


def _base_url() -> str:
    return str(get_setting("HONEYCHECKER_URL")).rstrip("/")


def set_real_index(user_id: str, real_index: int) -> None:
    try:
        r = requests.post(
            f"{_base_url()}/set",
            json={"user_id": str(user_id), "real_index": int(real_index)},
            timeout=2,
        )
        r.raise_for_status()
    except Exception as e:
        raise HoneycheckerError(str(e)) from e


def verify_index(user_id: str, candidate_index: int) -> bool:
    try:
        r = requests.post(
            f"{_base_url()}/verify",
            json={"user_id": str(user_id), "candidate_index": int(candidate_index)},
            timeout=2,
        )
        r.raise_for_status()
        data = r.json()
        return bool(data["is_real"])
    except Exception as e:
        raise HoneycheckerError(str(e)) from e
