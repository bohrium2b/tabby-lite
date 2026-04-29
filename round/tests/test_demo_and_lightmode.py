from django.test import TestCase, override_settings
from django.conf import settings
from django.db import connection
from round.models import PendingSubmission, BallotPairing
from round import tasks
import requests


class DemoAndLightModeTests(TestCase):
    def test_demo_mode_marks_submission_completed_and_no_network(self):
        with override_settings(DEMO_MODE=True):
            # Ensure any already-created DB tables are renamed for demo prefix
            try:
                from account.apps import rename_demo_tables_for_using
                rename_demo_tables_for_using()
            except Exception:
                pass
            submission = PendingSubmission.objects.create(payload={"foo": "bar"}, endpoint="http://example/api", status=PendingSubmission.STATUS_PENDING)

            # Monkeypatch requests.post to ensure it's not called
            orig_post = requests.post
            called = {"count": 0}

            def fake_post(*args, **kwargs):
                called["count"] += 1
                class R:
                    status_code = 500
                    def json(self):
                        return {}
                return R()

            requests.post = fake_post
            try:
                # Call the sync function (sync variant)
                tasks.sync_submission_to_api_now(submission.id)
                submission.refresh_from_db()
                self.assertEqual(submission.status, PendingSubmission.STATUS_COMPLETED)
                self.assertEqual(called["count"], 0, "requests.post should not be called in DEMO_MODE")
            finally:
                requests.post = orig_post

    def test_light_memory_mode_posts_and_completes(self):
        # Ensure that without demo mode, LIGHT_MEMORY_MODE uses sync_submission_to_api_now
        with override_settings(DEMO_MODE=False, LIGHT_MEMORY_MODE=True, TABBY_AUTHENTICATION_TOKEN="token"):
            submission = PendingSubmission.objects.create(payload={"foo": "bar"}, endpoint="http://example/api", status=PendingSubmission.STATUS_PENDING)

            # Monkeypatch requests.post to simulate upstream responding with 201
            orig_post = requests.post

            def fake_post(url, json=None, timeout=None, headers=None):
                class R:
                    status_code = 201
                    def json(self):
                        return {"url": "http://example/api/resource/1"}
                return R()

            requests.post = fake_post
            try:
                tasks.sync_submission_to_api_now(submission.id)
                submission.refresh_from_db()
                self.assertEqual(submission.status, PendingSubmission.STATUS_COMPLETED)
            finally:
                requests.post = orig_post

    def test_demo_db_prefix_applied_to_models_and_db_tables(self):
        # Use a clear prefix
        prefix = "tabby_lite_demo"
        with override_settings(DEMO_MODE=True, DEMO_DB_PREFIX=prefix):
            # Force re-run of app ready hook so prefix is applied in this test
            from django.apps import apps as django_apps
            try:
                acct = django_apps.get_app_config("account")
                acct.ready()
            except Exception:
                # If ready cannot run twice, attempt to call AccountConfig.ready()
                from account.apps import AccountConfig
                try:
                    AccountConfig().ready()
                except Exception:
                    pass

            # Attempt to rename existing tables to prefixed names for the test DB
            try:
                from account.apps import rename_demo_tables_for_using
                rename_demo_tables_for_using()
            except Exception:
                pass

            # Check that some known model's db_table is prefixed
            from django.contrib.auth.models import User
            self.assertTrue(User._meta.db_table.startswith(prefix))

            # Also check that the actual DB has a table with that name
            table_name = User._meta.db_table
            tables = connection.introspection.table_names()
            self.assertIn(table_name, tables)

    def test_demo_hourly_reset_resets_ballots_and_submissions(self):
        with override_settings(DEMO_MODE=True):
            # Ensure demo-prefixed physical tables exist in the test DB
            try:
                from account.apps import rename_demo_tables_for_using
                rename_demo_tables_for_using()
            except Exception:
                pass
            # Create a completed ballot pairing and a completed submission
            bp = BallotPairing.objects.create(round_seq=1, pairing_seq=1, passphrase="p", completed=True)
            sub = PendingSubmission.objects.create(payload={"x":1}, endpoint="http://example", status=PendingSubmission.STATUS_COMPLETED, retry_count=2)

            tasks.demo_hourly_reset()

            bp.refresh_from_db()
            sub.refresh_from_db()
            self.assertFalse(bp.completed)
            self.assertEqual(sub.status, PendingSubmission.STATUS_PENDING)
            self.assertEqual(sub.retry_count, 0)