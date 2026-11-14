"""Scénario de bout en bout du §12.3, rejoué uniquement via l'API HTTP."""

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.accounts.tests.factories import DEFAULT_PASSWORD, UserFactory
from apps.catalog.tests.factories import CategoryFactory, CountryFactory, TechnologyFactory

pytestmark = pytest.mark.django_db

API = "/api/v1"


def signed_in(identifier: str, password: str = DEFAULT_PASSWORD) -> APIClient:
    client = APIClient()
    response = client.post(f"{API}/auth/login/", {"identifier": identifier, "password": password})
    assert response.status_code == 200, response.json()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.json()['access']}")
    return client


def ok(response, status=200):
    assert response.status_code == status, (response.status_code, response.json())
    return response.json()


def test_section_12_3_end_to_end_scenario():
    CategoryFactory(name="Backend et API", slug="backend-et-api")
    TechnologyFactory(name="Django", slug="django")
    CountryFactory(code="BJ", name="Bénin")
    UserFactory(username="sena_dev")
    UserFactory(username="mod_e2e", role=User.Role.MODERATOR)

    # 1. Un visiteur crée un compte et complète son profil.
    visitor = APIClient()
    registered = ok(
        visitor.post(
            f"{API}/auth/register/",
            {
                "username": "koffi_e2e",
                "email": "koffi.e2e@example.org",
                "password": "Lagune-Cotonou-2026",
            },
        ),
        201,
    )
    koffi = APIClient()
    koffi.credentials(HTTP_AUTHORIZATION=f"Bearer {registered['access']}")
    ok(
        koffi.patch(
            f"{API}/profiles/me/", {"country": "BJ", "headline": "Dev Django"}, format="json"
        )
    )
    ok(
        koffi.put(
            f"{API}/profiles/me/skills/",
            [{"technology": "django", "level": "INTERMEDIATE"}],
            format="json",
        )
    )
    assert ok(visitor.get(f"{API}/profiles/koffi_e2e/"))["country"]["code"] == "BJ"

    # 2. Il publie une question.
    question = ok(
        koffi.post(
            f"{API}/posts/",
            {
                "type": "QUESTION",
                "title": "Comment paginer une API Django REST ?",
                "content": "<p>Ma liste renvoie trop d'éléments.</p>",
                "category": "backend-et-api",
                "technologies": ["django"],
            },
            format="json",
        ),
        201,
    )

    # 3. Un autre membre répond.
    sena = signed_in("sena_dev")
    answer = ok(
        sena.post(
            f"{API}/questions/{question['id']}/answers/",
            {"content": "<p>Utilisez <code>PageNumberPagination</code>.</p>"},
        ),
        201,
    )

    # 4. Le premier membre consulte la réponse (et l'accepte).
    answers = ok(koffi.get(f"{API}/questions/{question['id']}/answers/"))
    assert answers["results"][0]["id"] == answer["id"]
    ok(koffi.post(f"{API}/answers/{answer['id']}/accept/"))
    assert ok(koffi.get(f"{API}/notifications/"))["count"] >= 1

    # 5. Un membre crée un projet ouvert à la collaboration.
    project = ok(
        sena.post(
            f"{API}/projects/",
            {"name": "Bibliothèque numérique scolaire", "short_description": "Livres en ligne"},
            format="json",
        ),
        201,
    )
    assert project["is_accepting_members"] is True

    # 6. Un autre membre demande à rejoindre le projet.
    join_request = ok(
        koffi.post(
            f"{API}/projects/{project['slug']}/join-requests/",
            {"message": "Je peux développer l'API Django de la bibliothèque."},
        ),
        201,
    )

    # 7. Le propriétaire accepte la demande.
    ok(sena.post(f"{API}/join-requests/{join_request['id']}/accept/"))
    members = ok(sena.get(f"{API}/projects/{project['slug']}/members/"))
    assert {item["user"]["username"] for item in members["results"]} == {"sena_dev", "koffi_e2e"}

    # 8. Le nouveau membre consulte le projet et met à jour une tâche.
    task = ok(
        sena.post(
            f"{API}/projects/{project['slug']}/tasks/",
            {"title": "Créer le modèle Livre", "assignee": "koffi_e2e"},
            format="json",
        ),
        201,
    )
    detail = ok(koffi.get(f"{API}/projects/{project['slug']}/"))
    assert detail["my_role"] == "CONTRIBUTOR"
    assert (
        ok(koffi.patch(f"{API}/tasks/{task['id']}/", {"status": "IN_PROGRESS"}))["status"]
        == "IN_PROGRESS"
    )

    # 9. Un membre signale un contenu.
    report = ok(
        koffi.post(
            f"{API}/reports/",
            {"target_type": "ANSWER", "target_id": answer["id"], "reason": "SPAM"},
            format="json",
        ),
        201,
    )

    # 10. Le modérateur traite le signalement.
    moderator = signed_in("mod_e2e")
    queue = ok(moderator.get(f"{API}/moderation/reports/"))
    assert [item["id"] for item in queue["results"]] == [report["id"]]
    handled = ok(
        moderator.post(
            f"{API}/moderation/reports/{report['id']}/action/",
            {"action": "NO_ACTION", "reason": "La réponse est pertinente."},
            format="json",
        )
    )
    assert handled["status"] == "REJECTED"
    assert handled["actions"][0]["moderator"] == "mod_e2e"
