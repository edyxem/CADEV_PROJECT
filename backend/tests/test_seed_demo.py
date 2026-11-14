"""Le jeu de démonstration est idempotent et permet de rejouer le scénario jury (§17)."""

import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.community.models import Answer, Post
from apps.moderation.models import Report
from apps.projects.models import JoinRequest, Project, ProjectTask
from common import demo_data

pytestmark = pytest.mark.django_db

API = "/api/v1"


def signed_in(username: str) -> APIClient:
    client = APIClient()
    response = client.post(
        f"{API}/auth/login/", {"identifier": username, "password": demo_data.DEMO_PASSWORD}
    )
    assert response.status_code == 200, response.json()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.json()['access']}")
    return client


@pytest.fixture
def seeded(capsys):
    call_command("seed_demo")
    return capsys.readouterr().out


def counts():
    return (
        User.objects.count(),
        Post.all_objects.count(),
        Answer.all_objects.count(),
        Project.objects.count(),
        JoinRequest.objects.count(),
        ProjectTask.objects.count(),
        Report.objects.count(),
    )


def test_seed_is_idempotent_and_fictional(seeded):
    before = counts()

    call_command("seed_demo")

    assert counts() == before
    assert before[0] == len(demo_data.MEMBERS)
    assert "Démo prête" in seeded
    assert not User.objects.exclude(email__endswith=demo_data.DEMO_EMAIL_DOMAIN).exists()
    assert all(
        demo_data.FICTIONAL_NOTICE in user.profile.bio
        for user in User.objects.select_related("profile")
    )
    assert Report.objects.filter(status="PENDING").count() == len(demo_data.REPORTS)


def test_seed_covers_p2_modules(seeded):
    from apps.communities.models import Community
    from apps.events.models import Event
    from apps.mentorship.models import MentorProfile
    from apps.messaging.models import Conversation
    from apps.opportunities.models import Opportunity

    call_command("seed_demo")

    assert Opportunity.objects.filter(status="PUBLISHED").count() == 2
    assert Opportunity.objects.filter(status="PENDING_REVIEW").count() == 1
    assert MentorProfile.objects.count() == len(demo_data.MENTORS)
    assert Community.objects.count() == len(demo_data.COMMUNITIES)
    assert Event.objects.count() == len(demo_data.EVENTS)
    assert Conversation.objects.count() == len(demo_data.CONVERSATIONS)


def test_jury_scenario_section_17(seeded):
    awa = signed_in("awa_diop")

    # Profil et compétences déclarées.
    profile = awa.get(f"{API}/profiles/me/").json()
    assert {skill["technology"]["slug"] for skill in profile["skills"]} >= {"django", "python"}
    assert all(skill["is_verified"] is False for skill in profile["skills"])

    # Une question technique et ses réponses, dont une acceptée.
    question = awa.get(f"{API}/questions/", {"q": "N+1"}).json()["results"][0]
    answers = awa.get(f"{API}/questions/{question['id']}/answers/").json()["results"]
    assert answers[0]["is_accepted"] is True

    # Recherche d'un développeur par technologie.
    found = awa.get(f"{API}/search/users/", {"technology": "react"}).json()["results"]
    assert "kofi_mensah" in {item["username"] for item in found}

    # Un projet qui cherche un collaborateur ; une demande ; acceptation par le propriétaire.
    yao = signed_in("yao_kouassi")
    project = yao.get(f"{API}/projects/", {"recruiting": "true", "q": "CampusSecure"}).json()[
        "results"
    ][0]
    request = yao.post(
        f"{API}/projects/{project['slug']}/join-requests/",
        {"message": "Je souhaite contribuer aux scripts d'audit et à la documentation."},
    ).json()
    owner = signed_in("moussa_traore")
    assert owner.post(f"{API}/join-requests/{request['id']}/accept/").json()["status"] == "ACCEPTED"

    # Espace projet : membres et attribution d'une tâche.
    members = owner.get(f"{API}/projects/{project['slug']}/members/").json()["results"]
    assert "yao_kouassi" in {member["user"]["username"] for member in members}
    task = owner.post(
        f"{API}/projects/{project['slug']}/tasks/",
        {"title": "Tester le kit sur un réseau de démonstration", "assignee": "yao_kouassi"},
        format="json",
    )
    assert task.status_code == 201

    # La modération dispose de signalements de test.
    moderator = signed_in("demo_moderateur")
    assert moderator.get(f"{API}/moderation/reports/").json()["count"] == len(demo_data.REPORTS)
