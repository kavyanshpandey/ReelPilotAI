import time
from collections import defaultdict
from datetime import UTC, datetime
from threading import Lock
from typing import Annotated

import redis
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from reelpilot.config import Settings, get_settings
from reelpilot.models import UsageCounter, User
from reelpilot.security import get_current_user

_memory_hits: dict[tuple[str, str], list[float]] = defaultdict(list)
_memory_lock = Lock()

RATE_WINDOWS = {
    "general": (60, 60),
    "imports": (60, 10),
    "analysis": (60, 20),
    "generation": (60, 15),
    "auth": (60, 10),
}


def _bucket_for_path(path: str) -> str:
    if "/imports/" in path:
        return "imports"
    if "/analysis-runs" in path:
        return "analysis"
    if "/content-packs" in path:
        return "generation"
    return "general"


def _check_memory(key: tuple[str, str], window: int, limit: int) -> tuple[bool, int]:
    now = time.monotonic()
    with _memory_lock:
        hits = [hit for hit in _memory_hits[key] if now - hit < window]
        allowed = len(hits) < limit
        if allowed:
            hits.append(now)
        _memory_hits[key] = hits
        retry_after = max(1, int(window - (now - hits[0]))) if hits else window
    return allowed, retry_after


def _check_redis(key: tuple[str, str], settings: Settings, window: int, limit: int) -> tuple[bool, int]:
    try:
        client = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=0.15)
        redis_key = f"reelpilot:rate:{key[0]}:{key[1]}"
        count = int(client.incr(redis_key))
        if count == 1:
            client.expire(redis_key, window)
        ttl = max(1, int(client.ttl(redis_key)))
        return count <= limit, ttl
    except redis.RedisError:
        return _check_memory(key, window, limit)


def _raise_rate_limit(retry_after: int, detail: str) -> None:
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=detail,
        headers={"Retry-After": str(retry_after)},
    )


def enforce_api_limit(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    bucket = _bucket_for_path(request.url.path)
    window, limit = RATE_WINDOWS[bucket]
    allowed, retry_after = _check_redis((user.id, bucket), settings, window, limit)
    if not allowed:
        _raise_rate_limit(retry_after, f"Too many {bucket} requests. Try again shortly.")


def enforce_auth_limit(
    request: Request, settings: Annotated[Settings, Depends(get_settings)]
) -> None:
    client_id = request.client.host if request.client else "unknown"
    allowed, retry_after = _check_redis((client_id, "auth"), settings, *RATE_WINDOWS["auth"])
    if not allowed:
        _raise_rate_limit(retry_after, "Too many authentication attempts. Try again shortly.")


class QuotaExceededError(ValueError):
    def __init__(self, metric: str, limit: int):
        super().__init__(f"Monthly {metric} limit of {limit:,} reached")
        self.metric = metric
        self.limit = limit


def consume_quota(database: Session, workspace_id: str, metric: str, amount: int, limit: int) -> None:
    month = datetime.now(UTC).strftime("%Y-%m")
    counter = database.scalar(
        select(UsageCounter).where(
            UsageCounter.workspace_id == workspace_id, UsageCounter.month == month
        )
    )
    if counter is None:
        counter = UsageCounter(workspace_id=workspace_id, month=month)
        database.add(counter)
        database.flush()
    current = getattr(counter, metric)
    if current + amount > limit:
        raise QuotaExceededError(metric, limit)
    setattr(counter, metric, current + amount)
