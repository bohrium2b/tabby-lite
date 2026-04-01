from django.urls import path
from . import views


urlpatterns = [
    path('rounds/', views.rounds, name='rounds'),
    path('rounds/<int:round_id>/', views.round_detail, name='round_detail'),
    path('rounds/<int:round_id>/draw/', views.round_draw, name='round_draw'),
    path('teams/<int:team_id>/', views.team_detail, name='team_detail'),
]