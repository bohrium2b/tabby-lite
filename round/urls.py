from django.urls import path
from django.views.generic import TemplateView
from round.views import *

app_name = 'round'
urlpatterns = [
    path('', rounds_list, name='rounds_list'),
    path('<int:round_seq>/', rounds_detail, name='rounds_detail'),
    path('<int:round_seq>/draw/', draw_csv, name='draw_csv'),
    path('registration/', registration, name='registration'),
    path('ballot/', empty_ballot, name='empty_ballot'),
    path('ballot/<str:passphrase>/', ballot, name='ballot'),
]