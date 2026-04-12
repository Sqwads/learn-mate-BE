from threading import Lock
from uuid import uuid4
import time
from typing import Optional

# Simple in-memory TTL session cache. Not persistent; suitable for dev/testing.

_lock = Lock()
_sessions = {}  # token -> (user_id, expires_at)

DEFAULT_TTL = 3600  # 1 hour


def create_session(user_id: str, ttl: int = DEFAULT_TTL) -> str:
    """Create a session token for the given user_id and return the token."""
    token = str(uuid4())
    expires_at = time.time() + ttl
    with _lock:
        _sessions[token] = (user_id, expires_at)
    return token


def get_user_id_for_token(token: str) -> Optional[str]:
    """Return user_id if token is valid and not expired, else None."""
    now = time.time()
    with _lock:
        data = _sessions.get(token)
        if not data:
            return None
        user_id, expires_at = data
        if expires_at < now:
            # expired
            del _sessions[token]
            return None
        return user_id


def invalidate_session(token: str) -> None:
    with _lock:
        _sessions.pop(token, None)


def clear_expired() -> None:
    now = time.time()
    with _lock:
        expired = [t for t, (_, e) in _sessions.items() if e < now]
        for t in expired:
            del _sessions[t]
