from django.shortcuts import render, HttpResponse
from regex import match
from round.emojis import EMOJI_LIST
from round.utils import get_all_institutions, get_all_rounds, get_institution, get_round_by_id, get_round_draw, get_team_by_id, get_venue, create_team, create_speaker, get_all_teams
import json
import random

# Create your views here.
def rounds_list(request):
    rounds = get_all_rounds()  # Replace with actual function to fetch rounds
    teams = get_all_teams()
    for team in teams:
        # Replace institution URL with institution name
        institution_name = get_institution(team.institution).name
        team.institution = institution_name
    return render(request, 'rounds/list.html', {'rounds': rounds, 'teams': teams})


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


def draw_csv(request, round_id):
    try:
        draw = get_round_draw(round_id)
    except ValueError as e:
        # Handle the error, e.g., by displaying an error message
        return render(request, 'rounds/detail.html', {'error': str(e)})

    # Generate CSV content from the draw data
    csv_content = "email, team1, sideteam1, team2, sideteam2, venue\n"
    for pairing in draw:
        team1 = get_team_by_id(match(r'.+\/teams\/(\d+)\/{0,1}', pairing.teams[0]["team"]).group(1)).short_name
        emailteam1 = get_team_by_id(match(r'.+\/teams\/(\d+)\/{0,1}', pairing.teams[0]["team"]).group(1)).speakers[0]["email"]
        sideteam1 = pairing.teams[0]["side"]
        team2 = get_team_by_id(match(r'.+\/teams\/(\d+)\/{0,1}', pairing.teams[1]["team"]).group(1)).short_name
        emailteam2 = get_team_by_id(match(r'.+\/teams\/(\d+)\/{0,1}', pairing.teams[1]["team"]).group(1)).speakers[0]["email"]
        sideteam2 = pairing.teams[1]["side"]
        venue = get_venue(pairing.venue).name
        csv_content += f"{emailteam1}, {team1}, {sideteam1}, {team2}, {sideteam2}, {venue}\n"
        csv_content += f"{emailteam2}, {team2}, {sideteam2}, {team1}, {sideteam1}, {venue}\n"

    response = HttpResponse(csv_content, content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="round_{round_id}_draw.csv"'
    return response


def registration(request):
    if request.method == 'POST':
        # Handle form submission here
        body = json.loads(request.body.decode('utf-8'))
        institution = get_institution(body.get('institution'))
        print(body.get('teamName'))
        print(body.get('institution'))
        print(body.get('speaker1Name'))
        print(body.get('speaker1Email'))
        print(body.get('speaker2Name'))
        print(body.get('speaker2Email'))
        print(body.get('speaker3Name'))
        print(body.get('speaker3Email'))
        # Create three speakers
        speaker1 = {
            'name': body.get('speaker1Name'),
            'email': body.get('speaker1Email'),
            'institution': body.get('institution')
        }
        speaker2 = {
            'name': body.get('speaker2Name'),
            'email': body.get('speaker2Email'),
            'institution': body.get('institution')
        }
        speaker3 = {
            'name': body.get('speaker3Name'),
            'email': body.get('speaker3Email'),
            'institution': body.get('institution')
        }
        print(speaker1, speaker2, speaker3)
        team = create_team(short_name=f"{institution.code} {body.get('teamName')}", long_name=f"{institution.name} {body.get('teamName')}", reference=body.get('teamName'), emoji=random.choice(EMOJI_LIST), institution=institution.url)
        team_id = team.id
        create_speaker(speaker1['name'], team_id=team_id, email=speaker1['email'], institution=speaker1['institution'])
        create_speaker(speaker2['name'], team_id=team_id, email=speaker2['email'], institution=speaker2['institution'])
        create_speaker(speaker3['name'], team_id=team_id, email=speaker3['email'], institution=speaker3['institution'])

        return HttpResponse(json.dumps({'status': 'success', 'message': 'Registration successful!'}), content_type='application/json')
    
    institutions = get_all_institutions()
    return render(request, 'rounds/registration.html', {'institutions': institutions})