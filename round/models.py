from django.db import models

# Create your models here.
class BallotPairing(models.Model):
    round_seq = models.IntegerField()
    pairing_seq = models.IntegerField()
    passphrase = models.CharField(max_length=255, unique=True)
    completed = models.BooleanField(default=False)