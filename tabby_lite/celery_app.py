import os
from celery import Celery
from celery.schedules import schedule
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tabby_lite.settings")

app = Celery("tabby_lite")

# Load config from Django settings with `CELERY_` namespace
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks from installed apps
app.autodiscover_tasks()
if not getattr(settings, "LIGHT_MEMORY_MODE", False):
    # Simple beat schedule: heartbeat every 12 minutes to keep remote API alive
    app.conf.beat_schedule = {
        "api-heartbeat": {
            "task": "round.tasks.heartbeat",
            "schedule": schedule(12 * 60),
            "args": (),
        }
    }

    # Add a periodic refresh task to run more organic background fetches
    app.conf.beat_schedule.update({
        "periodic-random-refresh": {
            "task": "round.tasks.periodic_refresh",
            "schedule": schedule(5 * 60),
            "args": (),
        },
        "retry-pending-submissions": {
            "task": "round.tasks.retry_pending_submissions",
            "schedule": schedule(5 * 60),
            "args": (),
        }
    })
else:
    # In light memory mode, disable periodic beat schedule to avoid background work
    app.conf.beat_schedule = {}


@app.task(bind=True)
def debug_task(self):
    print(f"Celery debug task: {self.request!r}")
