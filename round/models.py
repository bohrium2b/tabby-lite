from django.db import models

# Create your models here.
class BallotPairing(models.Model):
    round_seq = models.IntegerField()
    pairing_seq = models.IntegerField()
    passphrase = models.CharField(max_length=255, unique=True)
    completed = models.BooleanField(default=False)


class Config(models.Model):
    display_draw = models.BooleanField(default=False)
    display_team = models.BooleanField(default=False)
    ballot_instructions = models.TextField(blank=True)
    homepage_info = models.TextField(blank=True)
    registration_open = models.BooleanField(default=True)


class PendingSubmission(models.Model):
    STATUS_PENDING = "pending"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_FAILED, "Failed"),
    ]

    payload = models.JSONField()
    endpoint = models.CharField(max_length=1024)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    error_log = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return f"PendingSubmission {self.pk} -> {self.endpoint} ({self.status})"
