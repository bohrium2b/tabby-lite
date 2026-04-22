import logging
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)

try:
    from django_redis import get_redis_connection
except Exception:
    get_redis_connection = None


def _acquire_lock(key, ttl=300):
    if not get_redis_connection or not getattr(settings, "DJANGO_USE_REDIS", False):
        return None
    conn = get_redis_connection("default")
    lock = conn.lock(f"lock:{key}", timeout=ttl)
    got = lock.acquire(blocking=False)
    return lock if got else None


def _release_lock(lock):
    try:
        if lock:
            lock.release()
    except Exception:
        pass


def swr_get(key, fetch_func=None, lock_ttl=300, cache_timeout=None):
    """Stale-While-Revalidate helper.

    - If key exists in cache: return it immediately and trigger background refresh.
    - If key missing: call `fetch_func()` synchronously, cache result, and return.

    `fetch_func` should be a callable that returns the value to cache.
    """
    try:
        val = cache.get(key)
    except Exception as exc:
        logger.debug("Cache get error for %s: %s", key, exc)
        val = None

    if val is not None:
        # enqueue background refresh if not already running
        lock = None
        try:
            lock = _acquire_lock(key, ttl=lock_ttl)
            if lock:
                # Import here to avoid circular imports when module imported early
                from round.tasks import refresh_cache

                try:
                    refresh_cache.delay(key)
                except Exception:
                    # best-effort: ignore failures to enqueue
                    logger.debug("Failed to enqueue refresh_cache for %s", key)
        finally:
            _release_lock(lock)

        return val

    # Cache miss: perform synchronous fetch if provided
    if fetch_func is None:
        return None

    value = fetch_func()
    try:
        # Persist until overwritten by default (no expiry) unless explicit cache_timeout provided
        cache.set(key, value, timeout=cache_timeout)
    except Exception as exc:
        logger.debug("Cache set error for %s: %s", key, exc)
    return value
