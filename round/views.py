import io

from django.shortcuts import render, HttpResponse
from django.core.cache import cache
from django.views.decorators.cache import cache_page
from regex import match
from round.emojis import EMOJI_LIST
from round.models import BallotPairing
from round.utils import Ballot, Result, ResultTeam, Sheet, Speech, Team, create_ballot, get_adjudicator, get_all_institutions, get_all_rounds, get_institution, get_round_by_id, get_round_draw, get_team_by_id, get_tournament, get_tournament_conf, get_venue, create_team, create_speaker, get_all_teams, generate_passphrase
from django.contrib.auth.decorators import login_required
from requests.exceptions import HTTPError
import json
import csv
import random

# Create your views here.
def rounds_list(request):
    if request.method == "POST":
        rounds = get_all_rounds()  # Replace with actual function to fetch rounds
        teams = get_all_teams()
        tournament = get_tournament()
        tournament_conf = get_tournament_conf()
        for team in teams:
            # Replace institution URL with institution name
            institution_name = get_institution(team.institution).name
            team.institution = institution_name
        return render(request, 'rounds/list.html', {'rounds': rounds, 'teams': teams, 'tournament': tournament, 'tournament_conf': tournament_conf})
    return render(request, 'rounds/index.html')


def rounds_detail(request, round_seq):
    # Replace with actual function to fetch a single round
    round = get_round_by_id(round_seq)
    # If post request, refresh cache
    if request.method == "POST":
        cache.delete(f'tabby:round_draw:{round_seq}')
    
    try:
        draw = get_round_draw(round_seq)
    except ValueError as e:
        # Handle the error, e.g., by displaying an error message
        return render(request, 'rounds/detail.html', {'round': round, 'error': str(e)})

    for pairing in draw:
        # Get location
        if pairing.venue:
            location = get_venue(pairing.venue)
            pairing.location = location
        for team in pairing.teams:
            team_name = get_team_by_id(match(r'.+\/teams\/(\d+)\/{0,1}', team["team"]).group(1))
            team["team"] = team_name
        if pairing.adjudicators["chair"]:
            pairing.adjudicators = {"chair": get_adjudicator(pairing.adjudicators["chair"]), "panellists": [get_adjudicator(panellist) for panellist in pairing.adjudicators["panellists"]], "trainees": [get_adjudicator(trainee) for trainee in pairing.adjudicators["trainees"]]}
            # Generate a ballot pairing
            # If one doesn't already exist
            if not BallotPairing.objects.filter(round_seq=round_seq, pairing_seq=pairing.id).exists():
                ballot_pairing = BallotPairing.objects.create(
                    round_seq=round_seq,
                    pairing_seq=pairing.id,
                    passphrase=generate_passphrase()
                )
            else:
                ballot_pairing = BallotPairing.objects.get(round_seq=round_seq, pairing_seq=pairing.id)
                print(ballot_pairing.passphrase)
            pairing.ballot_pairing = ballot_pairing
    return render(request, 'rounds/detail.html', {'round': round, 'draw': draw})


@login_required
def draw_csv(request, round_seq):
    try:
        draw = get_round_draw(round_seq)
    except ValueError as e:
        # Handle the error, e.g., by displaying an error message
        return render(request, 'rounds/detail.html', {'error': str(e)})

    # Generate CSV content from the draw data
    csv_content = "email, team1, sideteam1, team2, sideteam2, venue\n"
    for pairing in draw:
        team1 = get_team_by_id(match(r'.+\/teams\/(\d+)\/{0,1}', pairing.teams[0]["team"]).group(1))
        emailteam1 = team1.speakers[0]["email"]
        sideteam1 = pairing.teams[0]["side"]
        # If it is a BYE debate, replace team2 with BYE
        if pairing.teams[0]['side'] == 'bye':
            team2 = Team(emoji="", id=0, url="", institution="", use_institution_prefix=False, break_categories=[], institution_conflicts=[], venue_constraints=[], answers=[], reference="BYE", short_reference="BYE", code_name="BYE", short_name="BYE", long_name="BYE", seed=0, registration_status="confirmed", speakers=[], detail=None)
            emailteam2 = ""
            sideteam2 = ""
        else: 
            team2 = get_team_by_id(match(r'.+\/teams\/(\d+)\/{0,1}', pairing.teams[1]["team"]).group(1))
            emailteam2 = team2.speakers[0]["email"]
            sideteam2 = pairing.teams[1]["side"]
        if pairing.venue:
            venue = get_venue(pairing.venue).name
        else:
            venue = "BYE"
        csv_content += f"{emailteam1}, {team1.emoji} {team1.short_name}, {sideteam1}, {team2.emoji} {team2.short_name}, {sideteam2}, {venue}\n"
        
        if pairing.teams[0]['side'] == 'bye':
            pass 
        else:
            csv_content += f"{emailteam2}, {team2.emoji} {team2.short_name}, {sideteam2}, {team1.emoji} {team1.short_name}, {sideteam1}, {venue}\n"

    response = HttpResponse(csv_content, content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="round_{round_seq}_draw.csv"'
    return response


@login_required
def adj_draw_csv(request, round_seq):
    try:
        draw = get_round_draw(round_seq)
    except ValueError as e:
        # Handle the error, e.g., by displaying an error message
        return render(request, 'rounds/detail.html', {'error': str(e)})
    pairings = []
    # For each pairing in the draw, create a dict of {"email": "...", "name": "...", "team1": "EMOJI TEAM SHORT_NAME", "sideteam1": "...", "team2": "EMOJI TEAM SHORT_NAME", "sideteam2": "...", "venue": "...", "passphrase": "CONFIDENTIAL PASSPHRASE"}
    for pairing in draw:
        # Get ballot_pairing
        ballot_pairing = BallotPairing.objects.get(round_seq=round_seq, pairing_seq=pairing.id)
        # Get adj
        adjudicators = pairing.adjudicators or {}
        chair = adjudicators.get("chair")
        adjudicator = get_adjudicator(chair) if chair else None
        # Get team1
        team1 = get_team_by_id(match(r'.+\/teams\/(\d+)\/{0,1}', pairing.teams[0]["team"] if pairing.teams[0]["team"] else "").group(1))
        # If team1 side is BYE:
        if pairing.teams[0]['side'] == 'bye':
            # Get team2
            team2 = Team(emoji="", id=0, url="", institution="", use_institution_prefix=False, break_categories=[], institution_conflicts=[], venue_constraints=[], answers=[], reference="BYE", short_reference="BYE", code_name="BYE", short_name="BYE", long_name="BYE", seed=0, registration_status="confirmed", speakers=[], detail=None)
            sideteam2 = "BYE"
        else:
            team2 = get_team_by_id(match(r'.+\/teams\/(\d+)\/{0,1}', pairing.teams[1]["team"] if pairing.teams[1]["team"] else "").group(1))
            sideteam2 = pairing.teams[1]['side']
        # Get venue
        if pairing.venue:
            venue = get_venue(pairing.venue).name
        else:
            venue = "BYE"

        # Create a dict for the pairing
        pairing_dict = {
            "email": adjudicator.email if adjudicator else "",
            "name": adjudicator.name if adjudicator else "",
            "team1": f"{team1.emoji} {team1.short_name}" if team1 else "",
            "sideteam1": pairing.teams[0]['side'] if pairing.teams[0]['side'] else "",
            "team2": f"{team2.emoji} {team2.short_name}" if team2 else "",
            "sideteam2": f"{sideteam2}",
            "venue": venue,
            "passphrase": ballot_pairing.passphrase if sideteam2 is not "BYE" else ""
        }
        pairings.append(pairing_dict)
    # Now use csv to put pairings to csv
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=pairing_dict.keys())
    writer.writeheader()
    writer.writerows(pairings)
    # Get output as str then return it as csv mime type
    csv_content = output.getvalue()

    response = HttpResponse(csv_content, content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="round_{round_seq}_adj_draw.csv"'
    return response


def registration(request):
    """
    Display a registration page.
    """
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
        print(body.get('speaker4Name'))
        print(body.get('speaker4Email'))
        # Create four speakers
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
        speaker4 = {
            'name': body.get('speaker4Name'),
            'email': body.get('speaker4Email'),
            'institution': body.get('institution')
        }

        print(speaker1, speaker2, speaker3, speaker4)
        print(f"Institution: {institution.name}")
        try:
            team = create_team(short_name=f"{institution.code} {body.get('teamName')}", long_name=f"{institution.name} {body.get('teamName')}", reference=body.get('teamName'), emoji=random.choice(EMOJI_LIST)[0], institution=institution.url)
        except HTTPError as e:
            # If the error is related to emoji not being unique or stuff like that, retry with a different emoji
            if "emoji" in str(e).lower():
                team = create_team(short_name=f"{institution.code} {body.get('teamName')}", long_name=f"{institution.name} {body.get('teamName')}", reference=body.get('teamName'), emoji=random.choice(EMOJI_LIST)[0], institution=institution.url)

            print(f"Error creating team: {e}")
            return HttpResponse(json.dumps({'status': 'error', 'message': 'Failed to create team'}), content_type='application/json')
        team_id = team.id
        create_speaker(speaker1['name'], team_id=team_id, email=speaker1['email'], institution=speaker1['institution'])
        create_speaker(speaker2['name'], team_id=team_id, email=speaker2['email'], institution=speaker2['institution'])
        create_speaker(speaker3['name'], team_id=team_id, email=speaker3['email'], institution=speaker3['institution'])
        if speaker4['name'] and speaker4['email']:
            create_speaker(speaker4['name'], team_id=team_id, email=speaker4['email'], institution=speaker4['institution'])
        # Invalidate all_teams cache
        cache.delete('tabby:teams')
        return HttpResponse(json.dumps({'status': 'success', 'message': f'Registration successful! Welcome {team.emoji} {team.short_name}!'}), content_type='application/json')
    
    institutions = get_all_institutions()
    team_name = generate_passphrase("W W") # Get a random word
    return render(request, 'rounds/registration.html', {'institutions': institutions, "team_name": team_name, "can_edit_team_name": False})


def ballot(request, passphrase):
    try:
        ballot_pairing = BallotPairing.objects.get(passphrase=passphrase)
        # Now get round and pairing 
        round = get_round_by_id(ballot_pairing.round_seq)
        pairings = get_round_draw(round.seq)
        pairing = None
        for xpairing in pairings:
            if ballot_pairing.pairing_seq == xpairing.id:
                pairing = xpairing
        for team in pairing.teams:
            team["team"] = get_team_by_id(match(r'.+\/teams\/(\d+)\/{0,1}', team["team"]).group(1))
        print(pairing.teams)
        pairing.adjudicators = {"chair": get_adjudicator(pairing.adjudicators["chair"]), "panellists": [get_adjudicator(panellist) for panellist in pairing.adjudicators["panellists"]], "trainees": [get_adjudicator(trainee) for trainee in pairing.adjudicators["trainees"]]}
    except BallotPairing.DoesNotExist:
        return render(request, 'rounds/ballot.html', {'error': 'Invalid passphrase'})

    # On submit to POST
    if request.method == "POST":
        # Pull parameters from body - {"team1": {"team": <team_id>, "speakers": [{"id": <speaker_id>, "points": <points>, "role": "first" | "second" | "third" | "reply"}, ...], "win": <bool>}, "team2": {...}}
        body = json.loads(request.body.decode('utf-8'))
        ballot_team1 = body.get("team1")
        ballot_team2 = body.get("team2")
        # Now create SpeechResults
        speech_results1 = []
        for speaker_data in ballot_team1.get("speakers"):
            speech_result = Speech(
                ghost=False,
                score=speaker_data.get("points"),
                speaker=speaker_data.get("id"), # In the form of a URL
            )
            speech_results1.append(speech_result)

        speech_results2 = []
        for speaker_data in ballot_team2.get("speakers"):
            speech_result = Speech(
                ghost=False,
                score=speaker_data.get("points"),
                speaker=speaker_data.get("id"), # In the form of a URL
            )
            speech_results2.append(speech_result)
        # Now create ResultTeam
        result_team1 = ResultTeam(
            side=pairing.teams[0]["side"],
            points=1 if ballot_team1.get("win") else 0,
            win=ballot_team1.get("win"),
            score=ballot_team1.get("points"),
            team=pairing.teams[0]["team"].url,
            speeches=speech_results1
        )
        print(result_team1)
        result_team2 = ResultTeam(
            side=pairing.teams[1]["side"],
            points=1 if ballot_team2.get("win") else 0,
            win=ballot_team2.get("win"),
            score=ballot_team2.get("points"),
            team=pairing.teams[1]["team"].url,
            speeches=speech_results2
        )
        print(result_team2)
        # Now create Sheet
        sheet = Sheet(
            teams=[result_team1, result_team2],
            adjudicator=None
        )
        print(sheet)
        # Create Result
        result = Result(
            sheets=[sheet],
        )
        print(result)
        # Submit Ballot
        try:
            completed_ballot = create_ballot(round_seq=round.seq, pairing_id=pairing.id, result=result, single_adj=False, submitter=pairing.adjudicators["chair"], confirmed=True)
            ballot_pairing.completed = True
            ballot_pairing.save()
            return HttpResponse(json.dumps({"success": True}))
        except HTTPError as e:
            print(e)
            return HttpResponse(json.dumps({"error": "Failed to submit ballot"}), status=500)
        
    if ballot_pairing.completed:
        return render(request, 'rounds/empty_ballot.html', {'error': 'This ballot has already been submitted.'})
    return render(request, 'rounds/ballot.html', {'ballot_pairing': ballot_pairing, 'round': round, 'pairing': pairing})


@cache_page(3600)
def empty_ballot(request):
    return render(request, 'rounds/empty_ballot.html')