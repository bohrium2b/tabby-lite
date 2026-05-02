from types import SimpleNamespace

from django.test import TestCase, override_settings

from round import tasks, utils


class AssignTeamsToPotentialPersonsTests(TestCase):
    @override_settings(TABBY_ROOT="http://example")
    def test_groups_three_individuals_into_one_team(self):
        from round.models import PotentialTeamPerson, PendingSubmission

        # Create three individual potential persons
        p1 = PotentialTeamPerson.objects.create(name="Alice", email="a@example.org")
        p2 = PotentialTeamPerson.objects.create(name="Bob", email="b@example.org")
        p3 = PotentialTeamPerson.objects.create(name="Carol", email="c@example.org")

        # Patch utilities for deterministic output
        orig_get_all = utils.get_all_institutions
        orig_pass = utils.generate_passphrase
        try:
            utils.get_all_institutions = lambda: [SimpleNamespace(name="Open Institution", pk=1)]
            utils.generate_passphrase = lambda pattern: "TEAM-NAME"

            # Run the task synchronously
            tasks.assign_teams_to_potential_persons.run()

        finally:
            utils.get_all_institutions = orig_get_all
            utils.generate_passphrase = orig_pass

        # Check that a single PendingSubmission was created for the team
        subs = PendingSubmission.objects.filter(endpoint__contains="/teams")
        self.assertEqual(subs.count(), 1)
        payload = subs.first().payload
        # Followup speakers should include our three people
        followup = payload.get("_followup")
        self.assertIsNotNone(followup)
        speakers = followup.get("create_speakers")
        emails = {s["email"] for s in speakers}
        self.assertSetEqual(emails, {"a@example.org", "b@example.org", "c@example.org"})

        # Ensure persons are marked assigned_successfully
        p1.refresh_from_db()
        p2.refresh_from_db()
        p3.refresh_from_db()
        self.assertTrue(p1.assigned_successfully)
        self.assertTrue(p2.assigned_successfully)
        self.assertTrue(p3.assigned_successfully)

    @override_settings(TABBY_ROOT="http://example")
    def test_keeps_companions_together(self):
        from round.models import PotentialTeamPerson, PendingSubmission

        # Create a companion pair and a third person
        a = PotentialTeamPerson.objects.create(name="Ann", email="ann@example.org")
        b = PotentialTeamPerson.objects.create(name="Ben", email="ben@example.org")
        c = PotentialTeamPerson.objects.create(name="Cory", email="cory@example.org")
        # Link companions
        a.companion = b
        b.companion = a
        a.save()
        b.save()

        # Patch utils similarly
        orig_get_all = utils.get_all_institutions
        orig_pass = utils.generate_passphrase
        try:
            utils.get_all_institutions = lambda: [SimpleNamespace(name="Open Institution", pk=1)]
            utils.generate_passphrase = lambda pattern: "TEAM-PAIR"
            tasks.assign_teams_to_potential_persons.run()
        finally:
            utils.get_all_institutions = orig_get_all
            utils.generate_passphrase = orig_pass

        # There should be at least one pending submission that includes all three speakers
        subs = PendingSubmission.objects.filter(endpoint__contains="/teams")
        self.assertGreaterEqual(subs.count(), 1)
        found = False
        for s in subs:
            fu = s.payload.get("_followup") or {}
            sp = fu.get("create_speakers") or []
            emails = {x.get("email") for x in sp}
            if {"ann@example.org", "ben@example.org", "cory@example.org"}.issubset(emails):
                found = True
                break
        self.assertTrue(found, "Expected to find a submission containing the companion pair and third person")

        # Ensure all three are marked assigned
        a.refresh_from_db()
        b.refresh_from_db()
        c.refresh_from_db()
        self.assertTrue(a.assigned_successfully)
        self.assertTrue(b.assigned_successfully)
        self.assertTrue(c.assigned_successfully)
