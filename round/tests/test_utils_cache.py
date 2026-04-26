from django.test import TestCase, override_settings
from django.core.cache import cache

import time

from round import utils as utils_mod
from round import cache_helpers


class UtilsAndCacheTests(TestCase):
    def test_generate_passphrase_and_wordlist(self):
        # Basic generation should return a non-empty string
        p = utils_mod.generate_passphrase()
        self.assertIsInstance(p, str)
        self.assertGreater(len(p), 0)

        # A format with a space and capitalized words should contain a space
        p2 = utils_mod.generate_passphrase("W W")
        self.assertIn(" ", p2)
        # First word should be capitalized for format "W"
        first = p2.split()[0]
        self.assertTrue(first[0].isupper())

        # WORDLIST should be loaded from the file and contain known words
        self.assertIn("abacus", utils_mod.WORDLIST)

    def test_swr_get_miss_calls_fetch_and_caches(self):
        key = "test:swr:miss"
        try:
            cache.delete(key)
        except Exception:
            pass

        def fetch():
            return {"value": 1}

        val = cache_helpers.swr_get(key, fetch_func=fetch, cache_timeout=1)
        self.assertEqual(val, {"value": 1})

        # Ensure the wrapped value was stored in cache
        stored = cache.get(key)
        self.assertIsInstance(stored, dict)
        self.assertIn("v", stored)
        self.assertEqual(stored["v"], {"value": 1})

    def test_swr_get_hit_returns_value(self):
        key = "test:swr:wrapped"
        now = int(time.time())
        wrapper = {"v": 123, "ts": now, "fetch_callable": None, "stale_after": 1000}
        cache.set(key, wrapper, timeout=None)
        val = cache_helpers.swr_get(key, fetch_func=None)
        self.assertEqual(val, 123)
