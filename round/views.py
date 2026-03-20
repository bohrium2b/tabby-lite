from django.shortcuts import render
from regex import match
from round.utils import get_all_rounds, get_round_by_id, get_round_draw, get_team_by_id, get_venue

# Create your views here.
def rounds_list(request):
    rounds = get_all_rounds()  # Replace with actual function to fetch rounds
    return render(request, 'rounds/list.html', {'rounds': rounds})


def rounds_detail(request, round_id):
    # Replace with actual function to fetch a single round
    round = get_round_by_id(round_id)
    
    try:
        draw = get_round_draw(round_id)
    except ValueError as e:
        # Handle the error, e.g., by displaying an error message
        return render(request, 'rounds/detail.html', {'round': round, 'error': str(e)})


    for pairing in draw:
        # Get location
        location = get_venue(pairing.venue)
        pairing.location = location
        for team in pairing.teams:
            print(team["team"])
            team_name = get_team_by_id(match(r'.+\/teams\/(\d+)\/{0,1}', team["team"]).group(1)).short_name
            team["team"] = team_name
    return render(request, 'rounds/detail.html', {'round': round, 'draw': draw})