"""Cache helper utilities implementing a stale-while-revalidate pattern.

The `swr_get` function wraps Django's cache to return cached values
immediately while triggering background refreshes when values are stale.
This module also provides a small Redis-backed locking helper used to
ensure only one background refresher runs for a particular key.
"""

import logging
from django.core.cache import cache
from django.conf import settings
import time
import importlib

logger = logging.getLogger(__name__)

try:
    from django_redis import get_redis_connection
except Exception:
    get_redis_connection = None


def _acquire_lock(key, ttl=300):
    """Attempt to acquire a Redis lock for `key`.

    Returns a lock object when acquired, or `None` if Redis is not
    configured or the lock could not be obtained.
    """
    if not get_redis_connection or not getattr(settings, "DJANGO_USE_REDIS", False):
        return None
    conn = get_redis_connection("default")
    lock = conn.lock(f"lock:{key}", timeout=ttl)
    got = lock.acquire(blocking=False)
    return lock if got else None


def _release_lock(lock):
    """Release a previously-acquired Redis lock, ignoring errors.

    The function is defensive and will silently ignore release errors
    because it is used in best-effort background refresh paths.
    """
    try:
        if lock:
            lock.release()
    except Exception:
        pass


def swr_get(key, fetch_func=None, lock_ttl=300, cache_timeout=None, stale_after=300):
    """Stale-While-Revalidate helper.

    - If key exists in cache: return it immediately and trigger background refresh.
    - If key missing: call `fetch_func()` synchronously, cache result, and return.

    `fetch_func` should be a callable that returns the value to cache.
    """
    try:
        stored = cache.get(key)
    except Exception as exc:
        logger.debug("Cache get error for %s: %s", key, exc)
        stored = None

    # Normalize legacy values (not wrapped) to wrapped form
    now = int(time.time())
    if stored is not None:
        if isinstance(stored, dict) and "v" in stored and "ts" in stored:
            age = now - int(stored.get("ts", 0))
            item_stale_after = stored.get("stale_after", stale_after)
            # If stale threshold passed, attempt background refresh
            if item_stale_after is not None and age >= item_stale_after:
                lock = None
                try:
                    lock = _acquire_lock(key, ttl=lock_ttl)
                    if lock:
                        from round.tasks import refresh_cache
                        try:
                            if getattr(settings, "LIGHT_MEMORY_MODE", False):
                                from round.tasks import refresh_cache_now
                                try:
                                    refresh_cache_now(key)
                                except Exception:
                                    logger.debug("Failed to run refresh_cache synchronously for %s", key)
                            else:
                                refresh_cache.delay(key)
                        except Exception:
                            logger.debug("Failed to enqueue refresh_cache for %s", key)
                finally:
                    _release_lock(lock)
            return stored["v"]
        else:
            # Legacy non-wrapped value: return directly and attempt to wrap if fetch_func provided
            try:
                lock = _acquire_lock(key, ttl=lock_ttl)
                if lock and fetch_func:
                    from round.tasks import refresh_cache
                    try:
                        # store fetch callable path for future background refreshes
                        path = None
                        try:
                            path = f"{fetch_func.__module__}.{fetch_func.__name__}"
                        except Exception:
                            path = None
                        if getattr(settings, "LIGHT_MEMORY_MODE", False):
                            from round.tasks import refresh_cache_now
                            try:
                                refresh_cache_now(key, path)
                            except Exception:
                                logger.debug("Failed to run refresh_cache synchronously for legacy key %s", key)
                        else:
                            refresh_cache.delay(key, path)
                    except Exception:
                        logger.debug("Failed to enqueue refresh_cache for legacy key %s", key)
            finally:
                _release_lock(lock)
            return stored
    logger.debug("Cache miss for key %s", key)
    if fetch_func is None:
        return None

    value = fetch_func()
    # Try to store the callable path for future background refreshes
    fetch_path = None
    try:
        fetch_path = f"{fetch_func.__module__}.{fetch_func.__name__}"
    except Exception:
        fetch_path = None

    wrapper = {"v": value, "ts": now, "fetch_callable": fetch_path, "stale_after": stale_after}
    try:
        # Persist until overwritten by default (no expiry) unless explicit cache_timeout provided
        cache.set(key, wrapper, timeout=cache_timeout)
    except Exception as exc:
        logger.debug("Cache set error for %s: %s", key, exc)
    return value
