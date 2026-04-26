from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model

from round import views as views_mod


class ViewsTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        User = get_user_model()
        self.user = User.objects.create_user(username="tester", password="pass")

    @patch('round.views.get_all_rounds')
    @patch('round.views.get_all_teams')
    @patch('round.views.get_tournament')
    @patch('round.views.get_tournament_conf')
    @patch('round.views.get_institution')
    def test_rounds_list_post(self, mock_get_institution, mock_conf, mock_tournament, mock_teams, mock_rounds):
        mock_rounds.return_value = [SimpleNamespace(seq=1, name='R1')]
        mock_teams.return_value = [SimpleNamespace(institution='inst-url')]
        mock_tournament.return_value = SimpleNamespace(name='T')
        mock_conf.return_value = {}
        mock_get_institution.return_value = SimpleNamespace(name='Inst', url='inst-url')

        request = self.factory.post('/rounds')
        request.user = self.user
        response = views_mod.rounds_list(request)
        self.assertEqual(response.status_code, 200)

    @patch('round.views.get_round_draw')
    @patch('round.views.get_team_by_id')
    @patch('round.views.get_venue')
    def test_draw_csv(self, mock_get_venue, mock_get_team, mock_get_round_draw):
        # Prepare pairing object expected by the view
        pairing = SimpleNamespace()
        pairing.id = 1
        pairing.venue = None
        pairing.teams = [
            {"team": "https://host/api/teams/1/", "side": "aff"},
            {"team": "https://host/api/teams/2/", "side": "neg"},
        ]
        mock_get_round_draw.return_value = [pairing]

        mock_get_team.side_effect = [
            SimpleNamespace(speakers=[{"email": "a@example.com"}], emoji="😀", short_name="TeamA"),
            SimpleNamespace(speakers=[{"email": "b@example.com"}], emoji="😃", short_name="TeamB"),
        ]
        request = self.factory.get('/rounds/1/draw.csv')
        request.user = self.user
        response = views_mod.draw_csv(request, 1)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        content = response.content.decode('utf-8')
        self.assertIn('a@example.com', content)
        self.assertIn('😀 TeamA', content)

    @patch('round.views.BallotPairing')
    @patch('round.views.get_round_draw')
    @patch('round.views.get_adjudicator')
    @patch('round.views.get_team_by_id')
    @patch('round.views.get_venue')
    def test_adj_draw_csv(self, mock_get_venue, mock_get_team, mock_get_adj, mock_get_round_draw, mock_ballotpairing):
        pairing = SimpleNamespace()
        pairing.id = 2
        pairing.venue = None
        pairing.teams = [
            {"team": "https://host/api/teams/1/", "side": "aff"},
            {"team": "https://host/api/teams/2/", "side": "neg"},
        ]
        pairing.adjudicators = {"chair": "https://host/api/adjs/1/", "panellists": [], "trainees": []}
        mock_get_round_draw.return_value = [pairing]

        # BallotPairing.objects.get should return an object with passphrase
        mock_ballotpairing.objects.get.return_value = SimpleNamespace(passphrase='SECRET')

        mock_get_adj.return_value = SimpleNamespace(email='adj@example.com', name='Adj')
        mock_get_team.side_effect = [
            SimpleNamespace(emoji='😀', short_name='TeamA'),
            SimpleNamespace(emoji='😃', short_name='TeamB'),
        ]

        request = self.factory.get('/rounds/2/adj_draw.csv')
        request.user = self_user = self.user
        response = views_mod.adj_draw_csv(request, 2)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        content = response.content.decode('utf-8')
        self.assertIn('adj@example.com', content)
        self.assertIn('SECRET', content)

    @patch('round.views.get_institution')
    @patch('round.views.PendingSubmission')
    @patch('round.views.sync_submission_to_api')
    @patch('round.views.cache')
    def test_registration_post(self, mock_cache, mock_sync, mock_pending, mock_get_institution):
        # Fake institution returned by API
        mock_get_institution.return_value = SimpleNamespace(name='Uni', code='U', url='inst-url')

        # Fake PendingSubmission class with objects.create
        class FakePending:
            STATUS_PENDING = 'pending'

            def __init__(self, payload, endpoint, status):
                self.payload = payload
                self.endpoint = endpoint
                self.status = status
                self.id = 1

            def save(self):
                return

            class objects:
                @staticmethod
                def create(payload, endpoint, status):
                    return FakePending(payload, endpoint, status)

        mock_pending.return_value = FakePending
        mock_pending.objects = FakePending.objects

        # Ensure sync_submission_to_api.delay exists
        mock_sync.delay = lambda _id: None

        body = {
            'teamName': 'TeamX',
            'institution': 'inst-url',
            'speaker1Name': 'A', 'speaker1Email': 'a@example.com',
            'speaker2Name': 'B', 'speaker2Email': 'b@example.com',
            'speaker3Name': '', 'speaker3Email': '',
            'speaker4Name': '', 'speaker4Email': '',
        }

        import json
        request = self.factory.post('/registration', data=json.dumps(body), content_type='application/json')
        request.user = self.user
        response = views_mod.registration(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(data.get('status'), 'success')

    @patch('round.views.BallotPairing')
    @patch('round.views.get_adjudicator')
    @patch('round.views.get_round_by_id')
    @patch('round.views.get_round_draw')
    @patch('round.views.get_team_by_id')
    @patch('round.views.PendingSubmission')
    @patch('round.views.sync_submission_to_api')
    def test_ballot_post(self, mock_sync, mock_pending, mock_get_team, mock_get_round_draw, mock_get_round_by_id, mock_get_adjudicator, mock_ballotpairing):
        # Prepare fake ballot_pairing
        class FakeBP:
            def __init__(self):
                self.round_seq = 1
                self.pairing_seq = 10
                self.passphrase = 'p'
                self.pk = 5
                self.completed = False

            def save(self):
                return

        fake_bp = FakeBP()
        mock_ballotpairing.objects.get.return_value = fake_bp

        # Round and pairing
        mock_get_round_by_id.return_value = SimpleNamespace(seq=1)
        pairing = SimpleNamespace(id=10, teams=[{"team": "https://host/api/teams/1/", "side": "aff"}, {"team": "https://host/api/teams/2/", "side": "neg"}], adjudicators={"chair": "https://host/api/adjs/1/", "panellists": [], "trainees": []})
        mock_get_round_draw.return_value = [pairing]

        # Mock adjudicator resolution to avoid network calls
        mock_get_adjudicator.return_value = SimpleNamespace(email='adj@example.com', name='Adj')

        # get_team_by_id should return team objects with .url attribute
        mock_get_team.side_effect = [SimpleNamespace(url='t1'), SimpleNamespace(url='t2')]

        # Fake PendingSubmission similar to registration test
        class FakePending2:
            STATUS_PENDING = 'pending'

            def __init__(self, payload, endpoint, status):
                self.payload = payload
                self.endpoint = endpoint
                self.status = status
                self.id = 2

            def save(self):
                return

            class objects:
                @staticmethod
                def create(payload, endpoint, status):
                    return FakePending2(payload, endpoint, status)

        mock_pending.return_value = FakePending2
        mock_pending.objects = FakePending2.objects

        # Prepare POST body
        body = {
            'team1': {'speakers': [{'id': 's1', 'points': 10}], 'win': True, 'points': 100},
            'team2': {'speakers': [{'id': 's2', 'points': 9}], 'win': False, 'points': 90},
        }
        import json
        request = self.factory.post('/ballot/p', data=json.dumps(body), content_type='application/json')
        request.user = self.user
        response = views_mod.ballot(request, 'p')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode('utf-8'))
        self.assertTrue(data.get('success'))
