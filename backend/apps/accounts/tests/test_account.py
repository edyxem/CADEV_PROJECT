import re

import pytest
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core import mail

from apps.accounts import tokens
from apps.accounts.models import User
from apps.accounts.tests.factories import DEFAULT_PASSWORD, UserFactory

pytestmark = pytest.mark.django_db

ME_URL = "/api/v1/auth/me/"
NEW_PASSWORD = "Savane-Lumineuse-2027"
COOKIE = settings.AUTH_COOKIE["NAME"]


def link_params(body: str) -> dict[str, str]:
    return dict(re.findall(r"[?&](\w+)=([\w\-:.]+)", body))


class TestAccount:
    def test_owner_reads_own_account(self, client_for, user):
        response = client_for(user).get(ME_URL)

        assert response.status_code == 200
        assert response.json()["email"] == user.email

    def test_owner_updates_names(self, client_for, user):
        response = client_for(user).patch(ME_URL, {"first_name": "Awa", "last_name": "Diop"})

        assert response.status_code == 200
        user.refresh_from_db()
        assert (user.first_name, user.last_name) == ("Awa", "Diop")

    def test_member_cannot_escalate_through_the_api(self, client_for, user):
        payload = {
            "role": "ADMIN",
            "is_active": False,
            "email_verified": False,
            "is_staff": True,
            "is_superuser": True,
            "email": "pirate@example.org",
            "username": "root2",
        }

        response = client_for(user).patch(ME_URL, payload)

        assert response.status_code == 200
        user.refresh_from_db()
        assert user.role == User.Role.MEMBER
        assert user.is_active
        assert user.email_verified
        assert not user.is_staff
        assert not user.is_superuser
        assert user.email == "awa@example.org"
        assert user.username == "awa"


class TestRoleFlags:
    def test_flags_follow_the_role(self):
        admin = UserFactory(role=User.Role.ADMIN)
        moderator = UserFactory(role=User.Role.MODERATOR)
        member = UserFactory(is_staff=True, is_superuser=True)

        assert (admin.is_staff, admin.is_superuser, admin.is_admin) == (True, True, True)
        assert (moderator.is_staff, moderator.is_superuser) == (True, False)
        assert moderator.is_moderator and not moderator.is_admin
        assert (member.is_staff, member.is_superuser, member.is_moderator) == (False, False, False)

    def test_superuser_command_creates_an_admin(self):
        root = User.objects.create_superuser("racine", "Racine@Example.org", DEFAULT_PASSWORD)

        assert root.role == User.Role.ADMIN
        assert root.email == "racine@example.org"
        assert str(root) == "racine"


class TestPasswordChange:
    URL = "/api/v1/auth/password/change/"

    def test_password_change_closes_sessions(self, api_client, user):
        login = api_client.post(
            "/api/v1/auth/login/", {"identifier": "awa", "password": DEFAULT_PASSWORD}
        )
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.json()['access']}")

        response = api_client.post(
            self.URL, {"current_password": DEFAULT_PASSWORD, "new_password": NEW_PASSWORD}
        )

        assert response.status_code == 204
        user.refresh_from_db()
        assert user.check_password(NEW_PASSWORD)
        api_client.cookies[COOKIE] = login.cookies[COOKIE].value
        assert api_client.post("/api/v1/auth/token/refresh/").status_code == 401

    def test_wrong_current_password(self, client_for, user):
        response = client_for(user).post(
            self.URL, {"current_password": "faux", "new_password": NEW_PASSWORD}
        )

        assert response.status_code == 400
        assert "current_password" in response.json()["errors"]

    def test_new_password_must_respect_policy(self, client_for, user):
        response = client_for(user).post(
            self.URL, {"current_password": DEFAULT_PASSWORD, "new_password": "123"}
        )

        assert response.status_code == 400
        assert "password" in response.json()["errors"]


class TestPasswordReset:
    REQUEST_URL = "/api/v1/auth/password/reset/"
    CONFIRM_URL = "/api/v1/auth/password/reset/confirm/"

    def test_full_reset_flow(self, api_client, user):
        response = api_client.post(self.REQUEST_URL, {"email": "AWA@example.org"})
        assert response.status_code == 200
        params = link_params(mail.outbox[0].body)

        confirm = api_client.post(self.CONFIRM_URL, {**params, "new_password": NEW_PASSWORD})

        assert confirm.status_code == 204
        user.refresh_from_db()
        assert user.check_password(NEW_PASSWORD)

    def test_unknown_email_gets_the_same_answer(self, api_client, user):
        known = api_client.post(self.REQUEST_URL, {"email": user.email})
        unknown = api_client.post(self.REQUEST_URL, {"email": "personne@example.org"})

        assert known.status_code == unknown.status_code == 200
        assert known.json() == unknown.json()
        assert len(mail.outbox) == 1

    def test_token_cannot_be_reused(self, api_client, user):
        payload = {
            "uid": tokens.encode_uid(user),
            "token": default_token_generator.make_token(user),
            "new_password": NEW_PASSWORD,
        }
        assert api_client.post(self.CONFIRM_URL, payload).status_code == 204

        replay = api_client.post(self.CONFIRM_URL, {**payload, "new_password": "Autre-Sesame-2028"})

        assert replay.status_code == 400
        assert "token" in replay.json()["errors"]

    @pytest.mark.parametrize("uid", ["???", "bm9wZQ", ""])
    def test_invalid_uid_or_token(self, api_client, user, uid):
        response = api_client.post(
            self.CONFIRM_URL, {"uid": uid or "x", "token": "faux", "new_password": NEW_PASSWORD}
        )

        assert response.status_code == 400

    def test_weak_password_is_refused(self, api_client, user):
        payload = {
            "uid": tokens.encode_uid(user),
            "token": default_token_generator.make_token(user),
            "new_password": "123",
        }

        assert api_client.post(self.CONFIRM_URL, payload).status_code == 400


class TestEmailVerification:
    URL = "/api/v1/auth/email/verify/"

    def test_verification_link_confirms_the_address(self, api_client):
        user = UserFactory(email_verified=False)
        payload = {
            "uid": tokens.encode_uid(user),
            "token": tokens.email_verification_token.make_token(user),
        }

        assert api_client.post(self.URL, payload).status_code == 204
        user.refresh_from_db()
        assert user.email_verified
        assert api_client.post(self.URL, payload).status_code == 400

    def test_invalid_token(self, api_client, user):
        response = api_client.post(self.URL, {"uid": tokens.encode_uid(user), "token": "faux"})

        assert response.status_code == 400

    def test_resend_only_for_unverified_accounts(self, client_for, user):
        unverified = UserFactory(email_verified=False)

        assert client_for(unverified).post(f"{self.URL}resend/").status_code == 204
        assert client_for(user).post(f"{self.URL}resend/").status_code == 204
        assert [message.to for message in mail.outbox] == [[unverified.email]]


class TestEmailChange:
    URL = "/api/v1/auth/email/change/"

    def test_address_changes_only_after_confirmation(self, client_for, api_client, user):
        response = client_for(user).post(
            self.URL, {"new_email": "Awa.Pro@Example.org", "password": DEFAULT_PASSWORD}
        )

        assert response.status_code == 204
        user.refresh_from_db()
        assert user.email == "awa@example.org"
        assert mail.outbox[0].to == ["awa.pro@example.org"]

        token = link_params(mail.outbox[0].body)["token"]
        assert api_client.post(f"{self.URL}confirm/", {"token": token}).status_code == 204
        user.refresh_from_db()
        assert user.email == "awa.pro@example.org"

    def test_requires_password_and_free_address(self, client_for, user, other_user):
        client = client_for(user)

        wrong = client.post(self.URL, {"new_email": "x@example.org", "password": "faux"})
        taken = client.post(self.URL, {"new_email": other_user.email, "password": DEFAULT_PASSWORD})

        assert wrong.status_code == 400 and "password" in wrong.json()["errors"]
        assert taken.status_code == 400 and "new_email" in taken.json()["errors"]

    def test_tampered_token_is_refused(self, api_client):
        assert api_client.post(f"{self.URL}confirm/", {"token": "abc"}).status_code == 400

    def test_address_taken_in_the_meantime(self, api_client, user):
        token = tokens.make_email_change_token(user, "prise@example.org")
        UserFactory(email="prise@example.org")

        assert api_client.post(f"{self.URL}confirm/", {"token": token}).status_code == 400


class TestDeactivation:
    URL = "/api/v1/auth/me/deactivate/"

    def test_owner_deactivates_account(self, api_client, user):
        login = api_client.post(
            "/api/v1/auth/login/", {"identifier": "awa", "password": DEFAULT_PASSWORD}
        )
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.json()['access']}")

        response = api_client.post(self.URL, {"password": DEFAULT_PASSWORD})

        assert response.status_code == 204
        user.refresh_from_db()
        assert not user.is_active
        assert api_client.get(ME_URL).status_code == 401

    def test_wrong_password_keeps_account_active(self, client_for, user):
        response = client_for(user).post(self.URL, {"password": "faux"})

        assert response.status_code == 400
        user.refresh_from_db()
        assert user.is_active
