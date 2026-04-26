from django.contrib import admin

from round.models import BallotPairing, PendingSubmission
from django.conf import settings


class BallotPairingAdmin(admin.ModelAdmin):
    pass


@admin.action(description="Re-run selected submissions")
def rerun_submissions(modeladmin, request, queryset):
    from round.tasks import sync_submission_to_api

    for submission in queryset:
        submission.status = PendingSubmission.STATUS_PENDING
        submission.retry_count = 0
        submission.save()
        try:
            if getattr(settings, "LIGHT_MEMORY_MODE", False):
                from round.tasks import sync_submission_to_api_now
                try:
                    sync_submission_to_api_now(submission.id)
                except Exception:
                    pass
            else:
                sync_submission_to_api.delay(submission.id)
        except Exception:
            # Admin action should not fail hard; leave record for manual retry
            pass


class PendingSubmissionAdmin(admin.ModelAdmin):
    list_display = ("id", "endpoint", "status", "retry_count", "created_at")
    list_filter = ("status",)
    actions = [rerun_submissions]
    readonly_fields = ("created_at", "updated_at")


admin.site.register(BallotPairing, BallotPairingAdmin)
admin.site.register(PendingSubmission, PendingSubmissionAdmin)