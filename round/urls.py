from django.urls import path
from django.views.generic import TemplateView
from round.views import *

urlpatterns = [
    path('', rounds_list, name='rounds_list'),
    path('<int:round_id>/', rounds_detail, name='rounds_detail'),
    path('<int:round_id>/draw/', draw_csv, name='draw_csv'),
    path('registration/', registration, name='registration'),
]