from typing import TypedDict

import requests
import json
from django.conf import settings
from django.core.cache import cache

ROOT_URI = settings.TABBY_ROOT
TABBY_AUTHENTICATION_TOKEN = settings.TABBY_AUTHENTICATION_TOKEN
TEAM_CACHE_TIMEOUT_SECONDS = getattr(settings, "TABBY_TEAM_CACHE_TIMEOUT_SECONDS", 3600)
ROUND_DRAW_CACHE_TIMEOUT_SECONDS = getattr(settings, "TABBY_ROUND_DRAW_CACHE_TIMEOUT_SECONDS", 3600)
VENUE_CACHE_TIMEOUT_SECONDS = getattr(settings, "TABBY_VENUE_CACHE_TIMEOUT_SECONDS", 3600*24*2)
ROUND_CACHE_TIMEOUT_SECONDS = getattr(settings, "TABBY_ROUND_CACHE_TIMEOUT_SECONDS", 3600)


class RoundLinks(TypedDict):
    pairing: str
    availabilities: str

class Round:
    def __init__(self, id, url, starts_at, motions_released, _links, seq, completed, name, abbreviation, stage, draw_type, draw_status, silent, motions_status, weight, break_category=None, motions=None, feedback_weight=None):
        self.id = id
        self.url = url
        self.break_category = break_category
        self.motions = motions
        self.starts_at = starts_at
        self.motions_released = motions_released
        self._links = _links
        self.seq = seq
        self.completed = completed
        self.name = name
        self.abbreviation = abbreviation
        self.stage = stage
        self.draw_type = draw_type
        self.draw_status = draw_status
        self.feedback_weight = feedback_weight
        self.silent = silent
        self.motions_status = motions_status
        self.weight = weight


class Draw:
    def __init__(self, id, url, venue, teams, adjudicators, barcode, _links, sides_confirmed, bracket=None, room_rank=None, flags=None, importance=None, result_status=None):
        self.id = id
        self.url = url
        self.venue = venue
        self.teams = teams
        self.adjudicators = adjudicators
        self.barcode = barcode
        self._links = _links
        self.bracket = bracket
        self.room_rank = room_rank
        self.flags = flags
        self.importance = importance
        self.result_status = result_status
        self.sides_confirmed = sides_confirmed


class Team:
    def __init__(self, id, url, institution, break_categories, institution_conflicts, venue_constraints, answers, reference, short_reference, code_name, short_name, long_name, use_institution_prefix, seed, emoji, registration_status, speakers, detail=None):
        self.id = id
        self.url = url
        self.institution = institution
        self.break_categories = break_categories
        self.institution_conflicts = institution_conflicts
        self.venue_constraints = venue_constraints
        self.answers = answers
        self.reference = reference
        self.short_reference = short_reference
        self.code_name = code_name
        self.short_name = short_name
        self.long_name = long_name
        self.use_institution_prefix = use_institution_prefix
        self.seed = seed
        self.emoji = emoji
        self.registration_status = registration_status
        self.speakers = speakers


class Venue:
    def __init__(self, id, url, display_name, barcode, name, priority, *args, **kwargs):
        self.id = id
        self.url = url
        self.display_name = display_name
        self.barcode = barcode
        self.name = name
        self.priority = priority


def get_all_rounds():
    """

    Response format:
    [

        {
            "id": 0,
            "url": "http://example.com",
            "break_category": "http://example.com",
            "motions": [
                {
                    "id": 0,
                    "url": "http://example.com",
                    "text": "string",
                    "reference": "string",
                    "info_slide": "string",
                    "info_slide_plain": "string",
                    "seq": 0
                }
            ],
            "starts_at": "2019-08-24T14:15:22Z",
            "motions_released": true,
            "_links": {},
            "seq": 2147483647,
            "completed": true,
            "name": "string",
            "abbreviation": "string",
            "stage": "P",
            "draw_type": "R",
            "draw_status": "N",
            "feedback_weight": 0.1,
            "silent": true,
            "motions_status": "N",
            "weight": -2147483648
        }

    ]
    """
    response = requests.get(f"{ROOT_URI}/rounds")
    print(response.text)
    rounds_data = json.loads(response.text)
    return [Round(**round_data) for round_data in rounds_data]


def get_round_by_id(round_id):
    cache_key = f"tabby:round:{round_id}"
    cached_round_data = cache.get(cache_key)
    if cached_round_data is not None:
        return Round(**cached_round_data)


    response = requests.get(f"{ROOT_URI}/rounds/{round_id}")
    round_data = json.loads(response.text)
    cache.set(cache_key, round_data, timeout=ROUND_CACHE_TIMEOUT_SECONDS)
    return Round(**round_data)


def get_round_draw(round_id):
    """
    {
        "id": 0,
        "url": "http://example.com",
        "venue": "http://example.com",
        "teams": [
            {
                "team": "http://example.com",
                "side": 0,
                "flags": [
                    "max_swapped"
                ]
            }
        ],
        "adjudicators": {
            "chair": "http://example.com",
            "panellists": [
            "http://example.com"
            ],
            "trainees": [
            "http://example.com"
            ]
        },
        "barcode": "string",
        "_links": {
            "ballots": "http://example.com",
            "checkin": "http://example.com"
        },
        "bracket": 0.1,
        "room_rank": -2147483648,
        "flags": [
            "max_swapped"
        ],
        "importance": -2,
        "result_status": "N",
        "sides_confirmed": true
    }
    """
    cache_key = f"tabby:round_draw:{round_id}"
    cached_draw_data = cache.get(cache_key)
    if cached_draw_data is not None:
        return [Draw(**pairing_data) for pairing_data in cached_draw_data]

    response = requests.get(f"{ROOT_URI}/rounds/{round_id}/pairings")
    draw_data = json.loads(response.text)
    if not isinstance(draw_data, list):
        raise ValueError("Draw not yet released")


    draw = [Draw(**pairing_data) for pairing_data in draw_data]
    cache.set(cache_key, draw_data, timeout=ROUND_DRAW_CACHE_TIMEOUT_SECONDS)
    return draw


def get_team_by_id(team_id):
    """
    {"id":7,"url":"https://tabbycat-website-6btp.onrender.com/api/v1/tournaments/mac26/teams/7","institution":"https://tabbycat-website-6btp.onrender.com/api/v1/institutions/2","break_categories":["https://tabbycat-website-6btp.onrender.com/api/v1/tournaments/mac26/break-categories/1"],"institution_conflicts":["https://tabbycat-website-6btp.onrender.com/api/v1/institutions/2"],"venue_constraints":[],"answers":[],"reference":"3","short_reference":"3","code_name":"Biting Lip","short_name":"RED 3","long_name":"Macleans Red 3","use_institution_prefix":true,"seed":null,"emoji":"🫦","registration_status":"C","speakers":[{"id":19,"url":"https://tabbycat-website-6btp.onrender.com/api/v1/tournaments/mac26/speakers/19","name":"Speaker 1","categories":[],"_links":{"checkin":"https://tabbycat-website-6btp.onrender.com/api/v1/tournaments/mac26/speakers/19/checkin"},"barcode":"929735","answers":[],"last_name":null,"email":null,"phone":"","anonymous":false,"code_name":"01481770","url_key":"o6xx78ps","gender":"","pronoun":""},{"id":20,"url":"https://tabbycat-website-6btp.onrender.com/api/v1/tournaments/mac26/speakers/20","name":"Speaker 2","categories":[],"_links":{"checkin":"https://tabbycat-website-6btp.onrender.com/api/v1/tournaments/mac26/speakers/20/checkin"},"barcode":"541685","answers":[],"last_name":null,"email":null,"phone":"","anonymous":false,"code_name":"88999449","url_key":"vh2lcq6j","gender":"","pronoun":""},{"id":21,"url":"https://tabbycat-website-6btp.onrender.com/api/v1/tournaments/mac26/speakers/21","name":"Speaker 3","categories":[],"_links":{"checkin":"https://tabbycat-website-6btp.onrender.com/api/v1/tournaments/mac26/speakers/21/checkin"},"barcode":"675405","answers":[],"last_name":null,"email":null,"phone":"","anonymous":false,"code_name":"09877898","url_key":"ecppqbpc","gender":"","pronoun":""}]}
    
    """
    cache_key = f"tabby:team:{team_id}"
    cached_team_data = cache.get(cache_key)
    if cached_team_data is not None:
        return Team(**cached_team_data)

    response = requests.get(
        f"{ROOT_URI}/teams/{team_id}",
        headers={
            "Accept": "application/json",
            "Authorization": f"Token {TABBY_AUTHENTICATION_TOKEN}",
        },
    )
    response.raise_for_status()
    team_data = response.json()
    cache.set(cache_key, team_data, timeout=TEAM_CACHE_TIMEOUT_SECONDS)
    return Team(**team_data)


def get_venue(venue_uri):
    cache_key = f"tabby:venue:{venue_uri}"
    cached_venue_data = cache.get(cache_key)
    if cached_venue_data is not None:
        return Venue(**cached_venue_data)

    response = requests.get(
        venue_uri,
        headers={
            "Accept": "application/json",
            "Authorization": f"Token {TABBY_AUTHENTICATION_TOKEN}",
        },
    )
    response.raise_for_status()
    venue_data = response.json()
    cache.set(cache_key, venue_data, timeout=VENUE_CACHE_TIMEOUT_SECONDS)
    return Venue(**venue_data)