import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.accounts.tests.factories import UserFactory
from apps.catalog.tests.factories import CategoryFactory, TechnologyFactory
from apps.notifications.models import Notification
from apps.projects.models import Project, ProjectMember
from apps.projects.tests.factories import RoleNeedFactory, add_member, make_project

pytestmark = pytest.mark.django_db

URL = "/api/v1/projects/"
Role = ProjectMember.Role


def detail(project, suffix=""):
    return f"{URL}{project.slug}/{suffix}"


class TestCreateProject:
    def test_member_creates_project_and_becomes_owner(self, client_for, user):
        TechnologyFactory(name="Django", slug="django")
        CategoryFactory(name="Projets et hackathons", slug="projets-et-hackathons")

        response = client_for(user).post(
            URL,
            {
                "name": "Annuaire des fablabs africains",
                "short_description": "Recenser les fablabs du continent",
                "description": "<p>Projet <script>x()</script>ouvert</p>",
                "problem": "Les fablabs sont difficiles à trouver.",
                "category": "projets-et-hackathons",
                "technologies": ["django"],
                "repository_url": "https://github.com/afridev/fablabs",
            },
            format="json",
        )

        assert response.status_code == 201, response.json()
        body = response.json()
        assert body["slug"] == "annuaire-des-fablabs-africains"
        assert body["status"] == "RECRUITING"
        assert body["my_role"] == "OWNER"
        assert body["member_count"] == 1
        assert body["permissions"]["edit_settings"] is True
        assert "script" not in body["description"]
        assert ProjectMember.objects.get(project__slug=body["slug"]).role == Role.OWNER

    def test_slug_is_unique(self, user):
        first = make_project(user, name="Mon projet")
        second = make_project(user, name="Mon projet")

        assert (first.slug, second.slug) == ("mon-projet", "mon-projet-2")

    def test_anonymous_cannot_create(self, api_client):
        assert api_client.post(URL, {"name": "Projet", "short_description": "x"}).status_code == 401

    @pytest.mark.parametrize(
        "payload",
        [
            {"name": "ab", "short_description": "x"},
            {"name": "Projet valide", "short_description": "x", "repository_url": "javascript:x"},
            {"name": "Projet valide", "short_description": "x", "demo_url": "ftp://x.org"},
        ],
    )
    def test_invalid_payloads(self, client_for, user, payload):
        assert client_for(user).post(URL, payload, format="json").status_code == 400


class TestProjectAccess:
    def test_visitor_sees_public_project_but_not_tasks(self, api_client, user):
        project = make_project(user)

        body = api_client.get(detail(project)).json()

        assert body["name"] == project.name
        assert body["my_role"] is None
        assert body["permissions"]["view_tasks"] is False
        assert api_client.get(f"{URL}{project.id}/").status_code == 200
        assert api_client.get(detail(project, "members/")).json()["count"] == 1

    def test_private_project_is_invisible_to_non_members(
        self, client_for, api_client, user, other_user, moderator
    ):
        project = make_project(user, visibility=Project.Visibility.PRIVATE)

        assert api_client.get(detail(project)).status_code == 404
        assert client_for(other_user).get(detail(project)).status_code == 404
        assert client_for(other_user).get(detail(project, "members/")).status_code == 404
        assert client_for(user).get(detail(project)).status_code == 200
        assert client_for(moderator).get(detail(project)).status_code == 200
        assert api_client.get(URL).json()["count"] == 0

    @pytest.mark.parametrize("role", [Role.MANAGER, Role.CONTRIBUTOR, Role.OBSERVER])
    def test_only_owner_edits_settings(self, client_for, user, other_user, role):
        project = make_project(user)
        add_member(project, other_user, role=role)

        response = client_for(other_user).patch(detail(project), {"name": "Nom détourné"})

        assert response.status_code == 403

    def test_global_roles_give_no_project_rights(self, client_for, user, admin_user, moderator):
        project = make_project(user)

        for intruder in (admin_user, moderator):
            assert (
                client_for(intruder).patch(detail(project), {"name": "Nom détourné"}).status_code
                == 403
            )

    def test_owner_updates_and_status_change_notifies_members(self, client_for, user, other_user):
        project = make_project(user)
        add_member(project, other_user)

        response = client_for(user).patch(
            detail(project), {"status": "IN_PROGRESS", "name": "Nouveau nom"}
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Nouveau nom"
        assert response.json()["slug"] == project.slug
        assert Notification.objects.get(recipient=other_user).type == "PROJECT_UPDATED"

    def test_status_transitions_are_enforced(self, client_for, user):
        project = make_project(user)
        client = client_for(user)

        assert client.patch(detail(project), {"status": "COMPLETED"}).status_code == 409
        assert client.patch(detail(project), {"status": "IN_PROGRESS"}).status_code == 200
        completed = client.patch(detail(project), {"status": "COMPLETED"})
        assert completed.json()["completed_at"] is not None
        assert client.patch(detail(project), {"status": "ARCHIVED"}).status_code == 200
        assert client.patch(detail(project), {"name": "Modif après archivage"}).status_code == 409
        assert client.patch(detail(project), {"status": "PAUSED"}).status_code == 200

    def test_put_and_delete_are_not_exposed(self, client_for, user):
        project = make_project(user)

        assert client_for(user).delete(detail(project)).status_code == 404
        assert client_for(user).put(detail(project), {}).status_code == 404


class TestProjectList:
    def test_filters_and_mine(self, client_for, api_client, user, other_user):
        django = TechnologyFactory(name="Django", slug="django")
        open_project = make_project(user, name="Projet Django ouvert", technologies=[django])
        RoleNeedFactory(project=open_project, role_name="Designer UI")
        closed = make_project(other_user, name="Projet fermé", accepts_join_requests=False)
        make_project(other_user, name="Projet archivé", status=Project.Status.ARCHIVED)

        def slugs(**params):
            return sorted(item["slug"] for item in api_client.get(URL, params).json()["results"])

        assert slugs() == sorted([open_project.slug, closed.slug])
        assert slugs(technology="django") == [open_project.slug]
        assert slugs(recruiting="true") == [open_project.slug]
        assert slugs(recruiting="false") == [closed.slug]
        assert slugs(role="designer") == [open_project.slug]
        assert slugs(q="ferme") == [closed.slug]
        mine = client_for(other_user).get(f"{URL}mine/").json()
        assert mine["count"] == 2

    def test_list_query_count_is_bounded(self, api_client, django_assert_max_num_queries):
        for _ in range(4):
            make_project().technologies.add(TechnologyFactory())

        with django_assert_max_num_queries(7):
            api_client.get(URL)


class TestRoleNeeds:
    def test_owner_manages_roles_and_visitors_read_them(
        self, client_for, api_client, user, other_user
    ):
        TechnologyFactory(name="Figma", slug="figma")
        project = make_project(user)
        client = client_for(user)

        created = client.post(
            detail(project, "roles/"),
            {"role_name": "Designer UI/UX", "required_technologies": ["figma"], "slots": 2},
            format="json",
        )
        role_id = created.json()["id"]

        assert created.status_code == 201
        assert api_client.get(detail(project, "roles/")).json()[0]["slots"] == 2
        assert (
            client_for(other_user).post(detail(project, "roles/"), {"role_name": "x"}).status_code
            == 403
        )
        assert (
            client.patch(detail(project, f"roles/{role_id}/"), {"is_open": False}).json()["is_open"]
            is False
        )
        assert client.delete(detail(project, f"roles/{role_id}/")).status_code == 204

    def test_invalid_slots(self, client_for, user):
        project = make_project(user)

        response = client_for(user).post(
            detail(project, "roles/"), {"role_name": "Data", "slots": 0}
        )

        assert response.status_code == 400


class TestLogo:
    def png(self):
        buffer = io.BytesIO()
        Image.new("RGB", (800, 800), "blue").save(buffer, "PNG")
        return SimpleUploadedFile("logo.png", buffer.getvalue(), content_type="image/png")

    def test_owner_uploads_and_removes_logo(self, client_for, user, other_user):
        project = make_project(user)
        url = detail(project, "logo/")

        assert (
            client_for(other_user).put(url, {"logo": self.png()}, format="multipart").status_code
            == 403
        )
        response = client_for(user).put(url, {"logo": self.png()}, format="multipart")
        assert response.status_code == 200
        assert response.json()["logo"].endswith(".webp")
        assert client_for(user).put(url, {}, format="multipart").status_code == 400
        assert client_for(user).delete(url).status_code == 204


class TestOwnershipAndLeaving:
    def test_transfer_ownership(self, client_for, user, other_user):
        project = make_project(user)
        add_member(project, other_user)

        response = client_for(user).post(
            detail(project, "transfer-ownership/"), {"username": "kofi"}
        )

        assert response.status_code == 200
        project.refresh_from_db()
        assert project.owner == other_user
        assert ProjectMember.objects.get(project=project, user=user).role == Role.MANAGER

    def test_transfer_requires_owner_and_valid_target(self, client_for, user, other_user):
        project = make_project(user)
        observer = add_member(project, role=Role.OBSERVER).user
        outsider = UserFactory()
        add_member(project, other_user)

        assert (
            client_for(other_user)
            .post(detail(project, "transfer-ownership/"), {"username": "kofi"})
            .status_code
            == 403
        )
        for target in (observer, outsider):
            response = client_for(user).post(
                detail(project, "transfer-ownership/"), {"username": target.username}
            )
            assert response.status_code == 409

    def test_member_leaves_but_owner_cannot(self, client_for, user, other_user):
        project = make_project(user)
        add_member(project, other_user)

        assert client_for(user).post(detail(project, "leave/")).status_code == 409
        assert client_for(other_user).post(detail(project, "leave/")).status_code == 204
        assert client_for(other_user).post(detail(project, "leave/")).status_code == 409
        assert ProjectMember.objects.get(project=project, user=other_user).status == "LEFT"


def test_project_hidden_by_moderation_leaves_public_spaces(api_client, client_for, user, moderator):
    project = make_project(user)
    Project.objects.filter(pk=project.pk).update(hidden_by_moderation=True)

    assert api_client.get(URL).json()["count"] == 0
    assert api_client.get(detail(project)).status_code == 404
    assert client_for(user).get(detail(project)).status_code == 200
    assert client_for(moderator).get(detail(project)).status_code == 200
