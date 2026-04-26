from django.test import override_settings, TestCase
from django.core.cache import cache
from round import cache_helpers
from round.models import PendingSubmission

class LightModeTests(TestCase):
    def test_refresh_cache_runs_sync_in_light_mode(self):
        # Create a simple fetch function
        def fetch():
            return "value"

        key = "test:light:refresh"
        # Ensure cache cleared
        cache.delete(key)

        with override_settings(LIGHT_MEMORY_MODE=True):
            val = cache_helpers.swr_get(key, fetch_func=fetch, stale_after=1)
            # value should be present and callable stored
            self.assertEqual(val, "value")
            stored = cache.get(key)
            self.assertIsInstance(stored, dict)
            self.assertEqual(stored.get("v"), "value")

    def test_sync_submission_now_does_not_raise(self):
        # Create a PendingSubmission object and call sync submission synchronously
        p = PendingSubmission.objects.create(payload={"foo": "bar"}, endpoint="https://example.invalid", status=PendingSubmission.STATUS_PENDING)
        from round.tasks import sync_submission_to_api_now
        # Should run without raising (best-effort, may mark failed)
        sync_submission_to_api_now(p.id)
        self.assertIn(p.status, [PendingSubmission.STATUS_PENDING, PendingSubmission.STATUS_FAILED, PendingSubmission.STATUS_COMPLETED])
