from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.catalog.tests.factories import TechnologyFactory
from apps.moderation.models import AuditLog
from apps.moderation.services import create_report, take_action
from apps.notifications.models import Notification
from apps.opportunities.models import Opportunity, Organization

pytestmark = pytest.mark.django_db

URL = "/api/v1/opportunities/"


def payload(**extra):
    data = {
        "type": "INTERNSHIP",
        "title": "Stage développeur backend Django",
        "description": "<p>Stage de six mois <script>x</script></p>",
        "organization_name": "Startup fictive",
        "source_url": "https://example.org/offres/stage-backend",
        "application_url": "https://example.org/candidater",
        "work_mode": "REMOTE",
    }
    data.update(extra)
    return data


@pytest.fixture
def verified_org(user):
    organization = Organization.objects.create(
        name="Fondation Tech",
        slug="fondation-tech",
        website="https://fondation.example.org",
        is_verified=True,
    )
    organization.members.add(user)
    return organization


def make_published(publisher, **extra) -> Opportunity:
    data = {
        "type": "JOB",
        "title": "Développeur·se React",
        "description": "<p>Poste</p>",
        "organization_name": "Entreprise",
        "source_url": "https://example.org/job",
        "status": Opportunity.Status.PUBLISHED,
        "published_at": timezone.now(),
    }
    data.update(extra)
    return Opportunity.objects.create(publisher=publisher, **data)


class TestPublication:
    def test_unverified_publisher_goes_to_review(self, client_for, api_client, user):
        response = client_for(user).post(URL, payload(), format="json")

        assert response.status_code == 201, response.json()
        body = response.json()
        assert body["status"] == "PENDING_REVIEW"
        assert "script" not in body["description"]
        assert api_client.get(URL).json()["count"] == 0
        assert client_for(user).get(f"{URL}mine/").json()["count"] == 1

    def test_verified_partner_publishes_directly(self, client_for, api_client, user, verified_org):
        response = client_for(user).post(URL, payload(organization="fondation-tech"), format="json")

        assert response.json()["status"] == "PUBLISHED"
        assert response.json()["is_verified_partner"] is True
        assert api_client.get(URL).json()["count"] == 1

    def test_cannot_publish_for_someone_elses_organization(
        self, client_for, other_user, verified_org
    ):
        response = client_for(other_user).post(
            URL, payload(organization="fondation-tech"), format="json"
        )

        assert response.status_code == 403

    @pytest.mark.parametrize(
        "changes",
        [
            {"source_url": ""},
            {"source_url": "javascript:alert(1)"},
            {"application_url": "ftp://x.org"},
            {"organization_name": ""},
            {"deadline": "2020-01-01"},
        ],
    )
    def test_invalid_payloads(self, client_for, user, changes):
        assert client_for(user).post(URL, payload(**changes), format="json").status_code == 400

    def test_draft_then_submit(self, client_for, user):
        client = client_for(user)
        draft = client.post(URL, payload(submit=False), format="json").json()

        assert draft["status"] == "DRAFT"
        submitted = client.post(f"{URL}{draft['id']}/submit/")
        assert submitted.json()["status"] == "PENDING_REVIEW"
        assert client_for(UserFactory()).post(f"{URL}{draft['id']}/submit/").status_code == 404

    def test_editing_published_offer_sends_it_back_to_review(self, client_for, user):
        opportunity = make_published(user)

        response = client_for(user).patch(f"{URL}{opportunity.id}/", {"title": "Titre modifié"})

        assert response.json()["status"] == "PENDING_REVIEW"
        assert (
            client_for(UserFactory()).patch(f"{URL}{opportunity.id}/", {"title": "x"}).status_code
            == 404
        )


class TestReview:
    def test_moderator_approves_and_publisher_is_notified(self, client_for, user, moderator):
        draft = client_for(user).post(URL, payload(), format="json").json()

        queue = client_for(moderator).get(f"{URL}review-queue/").json()
        response = client_for(moderator).post(
            f"{URL}{draft['id']}/review/", {"approve": True, "note": "Source vérifiée."}
        )

        assert queue["count"] == 1
        assert response.json()["status"] == "PUBLISHED"
        assert AuditLog.objects.filter(action="opportunity.approve").exists()
        assert Notification.objects.filter(recipient=user, type="OPPORTUNITY_UPDATE").exists()

    def test_rejection_note_is_visible_to_publisher_only(
        self, client_for, user, moderator, other_user
    ):
        draft = client_for(user).post(URL, payload(), format="json").json()
        client_for(moderator).post(
            f"{URL}{draft['id']}/review/", {"approve": False, "note": "Source invérifiable."}
        )

        mine = client_for(user).get(f"{URL}{draft['id']}/").json()

        assert mine["status"] == "REJECTED" and mine["review_note"] == "Source invérifiable."
        assert client_for(other_user).get(f"{URL}{draft['id']}/").status_code == 404

    def test_members_cannot_review_and_moderators_not_their_own(self, client_for, user, moderator):
        draft = client_for(user).post(URL, payload(), format="json").json()
        own = client_for(moderator).post(URL, payload(), format="json").json()

        assert (
            client_for(user).post(f"{URL}{draft['id']}/review/", {"approve": True}).status_code
            == 403
        )
        assert (
            client_for(moderator).post(f"{URL}{own['id']}/review/", {"approve": True}).status_code
            == 403
        )

    def test_published_offer_cannot_be_reviewed_again(self, client_for, moderator, user):
        opportunity = make_published(user)

        response = client_for(moderator).post(f"{URL}{opportunity.id}/review/", {"approve": True})

        assert response.json()["code"] == "invalid_transition"


class TestListing:
    def test_expired_offers_are_flagged_and_hidden_by_default(self, api_client, user):
        make_published(
            user, title="Offre active", deadline=timezone.localdate() + timedelta(days=5)
        )
        make_published(
            user, title="Offre expirée", deadline=timezone.localdate() - timedelta(days=1)
        )

        default = api_client.get(URL).json()["results"]
        everything = api_client.get(URL, {"include_expired": "true"}).json()["results"]

        assert [item["title"] for item in default] == ["Offre active"]
        assert {item["is_expired"] for item in everything} == {True, False}

    def test_filters(self, api_client, user):
        django = TechnologyFactory(name="Django", slug="django")
        match = make_published(user, type="INTERNSHIP", title="Stage Django", work_mode="REMOTE")
        match.technologies.add(django)
        make_published(user, type="JOB", work_mode="ONSITE")

        def titles(**params):
            return [item["title"] for item in api_client.get(URL, params).json()["results"]]

        assert titles(type="INTERNSHIP") == ["Stage Django"]
        assert titles(technology="django") == ["Stage Django"]
        assert titles(work_mode="REMOTE") == ["Stage Django"]
        assert titles(q="stage") == ["Stage Django"]

    def test_no_payment_or_login_required_to_read(self, api_client, user):
        opportunity = make_published(user)

        body = api_client.get(f"{URL}{opportunity.id}/").json()

        assert body["application_url"] == "" and body["source_url"].startswith("https://")


class TestInterests:
    def test_member_applies_and_publisher_sees_it(self, client_for, user, other_user):
        opportunity = make_published(user)
        url = f"{URL}{opportunity.id}/interests/"

        response = client_for(other_user).post(
            url, {"kind": "APPLICATION", "message": "Mon profil correspond."}
        )

        assert response.status_code == 201
        assert (
            client_for(other_user)
            .post(url, {"kind": "APPLICATION", "message": "Encore"})
            .json()["code"]
            == "duplicate_interest"
        )
        assert (
            client_for(other_user)
            .post(url, {"kind": "INFORMATION", "message": "Une question ?"})
            .status_code
            == 201
        )
        assert client_for(user).get(url).json()["count"] == 2
        assert client_for(other_user).get(url).status_code == 404
        assert (
            client_for(user).post(url, {"kind": "INFORMATION", "message": "x"}).json()["code"]
            == "own_opportunity"
        )

    def test_expired_offer_refuses_interest(self, client_for, user, other_user):
        opportunity = make_published(user, deadline=timezone.localdate() - timedelta(days=1))

        response = client_for(other_user).post(
            f"{URL}{opportunity.id}/interests/", {"kind": "APPLICATION", "message": "x"}
        )

        assert response.json()["code"] == "opportunity_expired"


class TestModerationAndOrganizations:
    def test_suspicious_offer_is_reported_and_hidden(
        self, client_for, api_client, user, other_user, moderator
    ):
        opportunity = make_published(user)
        report = create_report(
            reporter=other_user, target_type="OPPORTUNITY", target_id=opportunity.pk, reason="SCAM"
        )

        take_action(moderator=moderator, report=report, action="HIDE", reason="Offre trompeuse.")

        assert api_client.get(f"{URL}{opportunity.id}/").status_code == 404
        assert (
            client_for(user).patch(f"{URL}{opportunity.id}/", {"title": "x"}).json()["code"]
            == "content_removed"
        )
        take_action(
            moderator=moderator,
            action="RESTORE",
            reason="Vérifiée.",
            target_type="OPPORTUNITY",
            target_id=opportunity.pk,
        )
        assert api_client.get(f"{URL}{opportunity.id}/").status_code == 200

    def test_organization_creation_and_admin_verification(self, client_for, user, admin_user):
        created = client_for(user).post(
            "/api/v1/organizations/",
            {"name": "Association Code Afrique", "website": "https://code.example.org"},
        )
        slug = created.json()["slug"]

        assert created.json()["is_verified"] is False
        assert client_for(user).post(f"/api/v1/organizations/{slug}/verify/").status_code == 403
        verified = client_for(admin_user).post(f"/api/v1/organizations/{slug}/verify/")
        assert verified.json()["is_verified"] is True
        assert AuditLog.objects.filter(action="organization.verify").exists()
        assert (
            client_for(admin_user)
            .post(f"/api/v1/organizations/{slug}/verify/", {"verified": False})
            .json()["is_verified"]
            is False
        )

    def test_invalid_website(self, client_for, user):
        response = client_for(user).post(
            "/api/v1/organizations/", {"name": "Org", "website": "javascript:x"}
        )

        assert response.status_code == 400
