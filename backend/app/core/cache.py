"""
Redis caching layer for prediction results.
Falls back gracefully to a simple in-process dict if Redis is unavailable.
"""

import json
import hashlib
from typing import Any, Optional
from loguru import logger


# ── In-process fallback cache ─────────────────────────────────────────────────
_LOCAL_CACHE: dict = {}
_MAX_LOCAL  = 512          # max entries in fallback cache


class CacheBackend:
    """Unified cache interface — Redis when available, dict otherwise."""

    def __init__(self):
        self._redis = None
        self._ttl   = 3600       # 1-hour TTL
        self._try_connect()

    def _try_connect(self):
        try:
            import redis
            from app.core.config import settings
            url = getattr(settings, "REDIS_URL", "redis://localhost:6379/0")
            r   = redis.from_url(url, socket_connect_timeout=1, socket_timeout=1)
            r.ping()
            self._redis = r
            logger.info(f"Redis connected: {url}")
        except Exception as e:
            logger.warning(f"Redis unavailable ({e}) — using in-process cache")
            self._redis = None

    # ── Public API ────────────────────────────────────────────────────────────

    def get(self, key: str) -> Optional[Any]:
        try:
            if self._redis:
                raw = self._redis.get(key)
                return json.loads(raw) if raw else None
            return _LOCAL_CACHE.get(key)
        except Exception as e:
            logger.debug(f"Cache get error: {e}")
            return None

    def set(self, key: str, value: Any) -> bool:
        try:
            if self._redis:
                self._redis.setex(key, self._ttl, json.dumps(value, default=str))
                return True
            # Evict oldest if full
            if len(_LOCAL_CACHE) >= _MAX_LOCAL:
                oldest = next(iter(_LOCAL_CACHE))
                del _LOCAL_CACHE[oldest]
            _LOCAL_CACHE[key] = value
            return True
        except Exception as e:
            logger.debug(f"Cache set error: {e}")
            return False

    def delete(self, key: str) -> bool:
        try:
            if self._redis:
                return bool(self._redis.delete(key))
            return bool(_LOCAL_CACHE.pop(key, None))
        except Exception:
            return False

    def flush_pattern(self, pattern: str) -> int:
        """Delete all keys matching a prefix (e.g. 'pred:heart:*')."""
        count = 0
        try:
            if self._redis:
                keys = self._redis.keys(pattern)
                if keys:
                    count = self._redis.delete(*keys)
            else:
                prefix = pattern.replace("*", "")
                to_del  = [k for k in _LOCAL_CACHE if k.startswith(prefix)]
                for k in to_del:
                    del _LOCAL_CACHE[k]
                count = len(to_del)
        except Exception as e:
            logger.debug(f"Cache flush error: {e}")
        return count

    def stats(self) -> dict:
        try:
            if self._redis:
                info = self._redis.info("stats")
                return {
                    "backend":     "redis",
                    "hits":        info.get("keyspace_hits", 0),
                    "misses":      info.get("keyspace_misses", 0),
                    "total_keys":  self._redis.dbsize(),
                }
            return {
                "backend":    "in-process",
                "total_keys": len(_LOCAL_CACHE),
                "hits":       None,
                "misses":     None,
            }
        except Exception:
            return {"backend": "error", "total_keys": 0}

    @property
    def available(self) -> bool:
        return self._redis is not None


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_prediction_key(disease: str, model_name: str, input_data: dict) -> str:
    """Deterministic cache key for a prediction request."""
    payload = json.dumps(
        {"d": disease, "m": model_name, "i": input_data},
        sort_keys=True, default=str
    )
    h = hashlib.sha256(payload.encode()).hexdigest()[:20]
    return f"pred:{disease}:{model_name}:{h}"


# Singleton
cache = CacheBackend()
