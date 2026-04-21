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
