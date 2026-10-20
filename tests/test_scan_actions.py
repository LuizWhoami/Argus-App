"""Testes das acoes de curadoria e exclusao de scans."""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.programs.models import Program
from apps.scans.models import Scan, ScanReview

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user("alice", password="x")


@pytest.fixture
def program(user):
    return Program.objects.create(owner=user, name="P", slug="p")


def _terminal_scan(program):
    s = Scan.objects.create(program=program, target="a.x.com")
    s.mark_running()
    s.mark_completed()
    return s


def test_review_toggle_on_terminal_scan(client, user, program):
    s = _terminal_scan(program)
    client.force_login(user)
    url = reverse("scans:review", args=[s.pk])

    r = client.post(url)
    assert r.status_code == 302
    assert ScanReview.objects.filter(scan=s).exists()

    client.post(url)
    assert not ScanReview.objects.filter(scan=s).exists()


def test_review_blocked_on_running_scan(client, user, program):
    s = Scan.objects.create(program=program, target="a.x.com")
    s.mark_running()
    client.force_login(user)

    r = client.post(reverse("scans:review", args=[s.pk]), follow=True)
    assert r.status_code == 200
    assert not ScanReview.objects.filter(scan=s).exists()


def test_cannot_review_other_users_scan(client, user, program):
    other = User.objects.create_user("bob", password="x")
    other_prog = Program.objects.create(owner=other, name="Q", slug="q")
    s = _terminal_scan(other_prog)

    client.force_login(user)
    r = client.post(reverse("scans:review", args=[s.pk]))
    assert r.status_code == 404


def test_delete_requires_confirmation(client, user, program):
    s = _terminal_scan(program)
    client.force_login(user)
    url = reverse("scans:delete", args=[s.pk])

    # sem confirm
    r = client.post(url, follow=True)
    assert Scan.objects.filter(pk=s.pk).exists()

    # com confirm errado
    r = client.post(url, {"confirm": "delete 999"}, follow=True)
    assert Scan.objects.filter(pk=s.pk).exists()

    # com confirm certo
    r = client.post(url, {"confirm": f"delete {s.pk}"})
    assert r.status_code == 302
    assert not Scan.objects.filter(pk=s.pk).exists()


def test_cannot_delete_other_users_scan(client, user, program):
    other = User.objects.create_user("bob", password="x")
    other_prog = Program.objects.create(owner=other, name="Q", slug="q")
    s = _terminal_scan(other_prog)

    client.force_login(user)
    r = client.post(reverse("scans:delete", args=[s.pk]),
                    {"confirm": f"delete {s.pk}"})
    assert r.status_code == 404
    assert Scan.objects.filter(pk=s.pk).exists()


def test_delete_cascades_review(client, user, program):
    s = _terminal_scan(program)
    ScanReview.objects.create(scan=s, reviewed_by=user)
    client.force_login(user)
    client.post(reverse("scans:delete", args=[s.pk]),
                {"confirm": f"delete {s.pk}"})
    assert not ScanReview.objects.filter(scan_id=s.pk).exists()
