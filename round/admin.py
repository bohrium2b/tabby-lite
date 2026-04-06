from django.contrib import admin
from round.models import BallotPairing

# Register your models here.
class BallotPairingAdmin(admin.ModelAdmin):
    pass

admin.site.register(BallotPairing, BallotPairingAdmin)