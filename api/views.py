from django.shortcuts import render
from django.http import HttpResponse
from round.utils import get_all_rounds, get_round_by_id, get_round_draw, get_team_by_id, get_venue
from django.core.cache import cache
import json

# Create your views here.
def rounds(request):
    rounds_data = get_all_rounds(raw=True)
    return HttpResponse(json.dumps(rounds_data), content_type='application/json')


def round_detail(request, round_id):
    round_data = get_round_by_id(round_id, raw=True)
    return HttpResponse(json.dumps(round_data), content_type='application/json')


def round_draw(request, round_id):
    draw_data = get_round_draw(round_id, raw=True)
    for pairing in draw_data:
        pairing["venue"] = get_venue(pairing["venue"], raw=True)
        for team in pairing["teams"]:
            team["team"] = get_team_by_id(team["team"], raw=True)
        # Replace venue URLs with venue data
        pairing["venue"] = get_venue(pairing["venue"], raw=True)
        # Replace team URLs with team data
    return HttpResponse(json.dumps(draw_data), content_type='application/json')


def team_detail(request, team_id):
    team_data = get_team_by_id(team_id, raw=True)
    return HttpResponse(json.dumps(team_data), content_type='application/json')

