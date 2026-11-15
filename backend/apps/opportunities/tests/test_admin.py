import pytest
from django.test import Client

from apps.moderation.models import AuditLog
from apps.notifications.models import Notification
from apps.opportunities.models import Opportunity

from .test_opportunities import make_published

pytestmark = pytest.mark.django_db

URL = "/admin/opportunities/opportunity/"
Status = Opportunity.Status


@pytest.fixture
def admin_client(admin_user) -> Client:
    client = Client()
    client.force_login(admin_user)
    return client


def run_action(client: Client, action: str, *opportunities: Opportunity):
    return client.post(
        URL,
        {"action": action, "_selected_action": [str(item.pk) for item in opportunities]},
        follow=True,
    )


def test_admin_publishes_pending_opportunity_with_audit_and_notification(admin_client, user):
    pending = make_published(user, status=Status.PENDING_REVIEW, published_at=None)

    response = run_action(admin_client, "approve", pending)

    assert response.status_code == 200
    pending.refresh_from_db()
    assert pending.status == Status.PUBLISHED
    assert pending.published_at is not None
    assert AuditLog.objects.filter(action="opportunity.approve").exists()
    assert Notification.objects.filter(recipient=user).exists()


def test_admin_rejects_pending_opportunity(admin_client, user):
    pending = make_published(user, status=Status.PENDING_REVIEW, published_at=None)

    run_action(admin_client, "reject", pending)

    pending.refresh_from_db()
    assert pending.status == Status.REJECTED


def test_admin_reports_forbidden_transition_without_crashing(admin_client, user):
    published = make_published(user)

    response = run_action(admin_client, "approve", published)

    assert response.status_code == 200
    assert "Transition interdite" in response.content.decode()
    published.refresh_from_db()
    assert published.status == Status.PUBLISHED
