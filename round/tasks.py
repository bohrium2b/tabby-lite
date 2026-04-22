import logging
import requests
from celery import shared_task
from django.conf import settings
from django.core.mail import mail_admins
import random
import importlib
import time
from django.core.cache import cache

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=5)
def sync_submission_to_api(self, submission_id):
    from round.models import PendingSubmission
    try:
        submission = PendingSubmission.objects.get(pk=submission_id)
    except PendingSubmission.DoesNotExist:
        logger.debug("Submission %s no longer exists", submission_id)
        return

    if submission.status == PendingSubmission.STATUS_COMPLETED:
        return

    try:
        # Log submission
        logger.info("Syncing submission %s to API", submission_id)
        resp = requests.post(submission.endpoint, json=submission.payload, timeout=10, headers={"Authorization": f"Token {settings.TABBY_AUTHENTICATION_TOKEN}"})
        status = resp.status_code
        logger.info("Response from API for submission %s: %d", submission_id, status)
        if status in (200, 201):
            # On success, mark completed and handle any follow-up actions encoded in payload
            submission.status = PendingSubmission.STATUS_COMPLETED
            submission.retry_count = self.request.retries if hasattr(self.request, "retries") else 0
            submission.save()

            # Handle follow-up actions (e.g., create speakers after team creation)
            try:
                followup = submission.payload.get("_followup") if isinstance(submission.payload, dict) else None
                if followup:
                    # Example followup: {"create_speakers": [ {"name":..., "email":...}, ... ] }
                    created = resp.json()
                    team_url = created.get("url")
                    if followup.get("create_speakers") and team_url:
                        for speaker in followup.get("create_speakers"):
                            speaker_payload = speaker.copy()
                            speaker_payload["team"] = team_url
                            try:
                                # Attempt to create speaker synchronously here; if it fails, enqueue as PendingSubmission
                                r = requests.post(f"{settings.TABBY_HOST}/api/v1/tournaments/{settings.TABBY_TOURNAMENT}/speakers", json=speaker_payload, headers={"Authorization": f"Token {settings.TABBY_AUTHENTICATION_TOKEN}"}, timeout=10)
                                if r.status_code not in (200, 201):
                                    PendingSubmission.objects.create(payload=speaker_payload, endpoint=f"{settings.TABBY_HOST}/api/v1/tournaments/{settings.TABBY_TOURNAMENT}/speakers", status=PendingSubmission.STATUS_PENDING)
                            except Exception:
                                PendingSubmission.objects.create(payload=speaker_payload, endpoint=f"{settings.TABBY_HOST}/api/v1/speakers", status=PendingSubmission.STATUS_PENDING)
                    if followup.get("debate_status"):
                        # Example followup: {"debate_status": "confirmed"}
                        # Amend debate pairing as in utils to be confirmed
                        # Get meta
                        meta = submission.payload.get("_meta") if isinstance(submission.payload, dict) else None
                        round_seq = meta["round_seq"]
                        pairing_id = meta["pairing_id"]
                        try:
                            r = requests.patch(f"{settings.TABBY_HOST}/api/v1/tournaments/{settings.TABBY_TOURNAMENT}/rounds/{round_seq}/pairings/{pairing_id}", json={"result_status": followup["debate_status"]}, headers={"Authorization": f"Token {settings.TABBY_AUTHENTICATION_TOKEN}"}, timeout=10)
                        except Exception:
                            logger.debug("Failed to update debate status for pairing %s in round %s", pairing_id, round_seq)
            except Exception:
                logger.debug("No followup actions or followup failed for submission %s", submission.id)
            return
        if 400 <= status < 500:
            submission.status = PendingSubmission.STATUS_FAILED
            submission.error_log = resp.text
            submission.save()
            logger.exception("Submission %s failed", submission.id)
            mail_admins(
                "PendingSubmission failed",
                f"Submission {submission.id} failed with {status}: {resp.text}",
            )
            # If this submission had local meta to revert optimistic state, do so
            try:
                meta = submission.payload.get("_meta") if isinstance(submission.payload, dict) else None
                if meta and meta.get("local_ballot_pairing_pk"):
                    from round.models import BallotPairing
                    try:
                        bp = BallotPairing.objects.get(pk=meta.get("local_ballot_pairing_pk"))
                        bp.completed = False
                        bp.save()
                    except Exception:
                        pass
            except Exception:
                pass
            return
        # For 5xx and other unexpected status codes, treat as transient
        raise requests.exceptions.RequestException(f"HTTP {status}")

    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
        # Exponential backoff sequence (seconds): 1m, 5m, 10m, 20m, 40m
        retries = getattr(self.request, "retries", 0)
        backoffs = [60, 300, 600, 1200, 2400]
        countdown = backoffs[min(retries, len(backoffs) - 1)]
        submission.retry_count = retries + 1
        submission.save()
        logger.warning("Transient error sending submission %s (retry %s): %s", submission.id, retries, exc)
        raise self.retry(exc=exc, countdown=countdown)
    except Exception as exc:  # pragma: no cover - best-effort logging path
        submission.status = PendingSubmission.STATUS_FAILED
        submission.error_log = str(exc)
        submission.save()
        logger.exception("Unexpected error sending submission %s: %s", submission.id, exc)
        mail_admins("PendingSubmission unexpected failure", f"Submission {submission.id} error: {exc}")


@shared_task
def heartbeat():
    """Ping the Tabby API host to keep it from hibernating."""
    try:
        url = getattr(settings, "TABBY_HOST", None)
        if not url:
            return
        # Lightweight ping
        requests.get(url, timeout=5)
    except Exception as exc:  # pragma: no cover - retry is handled by beat schedule
        logger.debug("Heartbeat ping failed: %s", exc)


@shared_task
def refresh_cache(key, fetch_callable_path=None):
    """Background refresh for a cache key.

    It will resolve a fetch callable either from the provided
    `fetch_callable_path` or from metadata stored with the cache value
    (set by `swr_get`). The callable is called synchronously and the
    result is written back into the cache with an updated timestamp.
    """
    try:
        # Try to load existing metadata from cache to learn stale_after/fetch path
        stored = None
        try:
            stored = cache.get(key)
        except Exception as exc:
            logger.debug("refresh_cache: cache.get(%s) failed: %s", key, exc)

        # Determine callable path
        path = fetch_callable_path
        stale_after = None
        if not path and isinstance(stored, dict):
            path = stored.get("fetch_callable")
            stale_after = stored.get("stale_after")

        if not path:
            logger.debug("refresh_cache: no fetch callable available for %s", key)
            return

        try:
            module_name, func_name = path.rsplit(".", 1)
            module = importlib.import_module(module_name)
            func = getattr(module, func_name)
        except Exception as exc:
            logger.debug("refresh_cache: failed to resolve %s: %s", path, exc)
            return

        try:
            val = func()
        except Exception as exc:
            logger.debug("refresh_cache: fetch function %s raised: %s", path, exc)
            return

        now = int(time.time())
        wrapper = {"v": val, "ts": now, "fetch_callable": path, "stale_after": stale_after}
        try:
            # Persist without expiry by default (timeout=None)
            cache.set(key, wrapper, timeout=None)
        except Exception as exc:
            logger.debug("refresh_cache: cache.set(%s) failed: %s", key, exc)
    except Exception as exc:  # pragma: no cover - best effort
        logger.debug("refresh_cache top-level error for %s: %s", key, exc)



@shared_task
def retry_pending_submissions(batch_size=100):
    """Find pending submissions and enqueue attempts.

    This periodically scans `PendingSubmission` objects with
    `STATUS_PENDING` and enqueues `sync_submission_to_api` for each.
    """
    try:
        from round.models import PendingSubmission
        pending_qs = PendingSubmission.objects.filter(status=PendingSubmission.STATUS_PENDING).order_by("id")[:batch_size]
        for sub in pending_qs:
            try:
                # Enqueue an attempt to send this submission
                sync_submission_to_api.delay(sub.id)
            except Exception:
                logger.debug("Failed to enqueue sync for PendingSubmission %s", sub.id)
    except Exception as exc:  # pragma: no cover
        logger.debug("retry_pending_submissions top-level error: %s", exc)



@shared_task
def periodic_refresh():
    """Randomly call various fetch utilities to keep the cache warm and appear organic."""
    try:
        # Import here to avoid early import-time side effects
        from round import utils
        candidates = [
            ("tournament", utils.get_tournament),
            ("all_rounds", utils.get_all_rounds),
            ("all_teams", utils.get_all_teams),
        ]
        # Randomly choose 1-3 tasks to run
        count = random.randint(1, min(3, len(candidates)))
        picks = random.sample(candidates, count)
        for name, func in picks:
            try:
                # Some functions accept args; use safe calls
                if name == "all_rounds":
                    func()
                elif name == "all_teams":
                    func()
                else:
                    func()
            except Exception:
                logger.debug("Periodic refresh: %s failed", name)
    except Exception as exc:  # pragma: no cover
        logger.debug("Periodic refresh top-level error: %s", exc)
