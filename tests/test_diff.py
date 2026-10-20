"""Testes do diff entre scans."""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.assets.models import Asset, Endpoint
from apps.programs.models import Program
from apps.scans.diff import compute_diff, previous_scan
from apps.scans.models import Scan, ScanAsset, ScanEndpoint

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user("alice", password="x")


@pytest.fixture
def program(user):
    return Program.objects.create(owner=user, name="P", slug="p")


def _complete(scan):
    scan.mark_running()
    scan.mark_completed()
    return scan


def test_previous_scan_none_when_first(program):
    s = _complete(Scan.objects.create(program=program, target="a.x.com"))
    assert previous_scan(s) is None


def test_previous_scan_finds_older(program):
    s1 = _complete(Scan.objects.create(program=program, target="a.x.com"))
    s2 = _complete(Scan.objects.create(program=program, target="a.x.com"))
    assert previous_scan(s2) == s1


def test_diff_detects_new_asset(program):
    s1 = _complete(Scan.objects.create(program=program, target="a.x.com"))
    s2 = _complete(Scan.objects.create(program=program, target="a.x.com"))

    a1 = Asset.objects.create(program=program, hostname="a.x.com")
    ScanAsset.objects.create(scan=s1, asset=a1)

    a2 = Asset.objects.create(program=program, hostname="b.x.com")
    ScanAsset.objects.create(scan=s2, asset=a1)
    ScanAsset.objects.create(scan=s2, asset=a2)

    d = compute_diff(s2)
    added_hosts = {a.hostname for a in d["assets"]["added"]}
    removed_hosts = {a.hostname for a in d["assets"]["removed"]}
    unchanged = {a.hostname for a in d["assets"]["unchanged"]}

    assert added_hosts == {"b.x.com"}
    assert removed_hosts == set()
    assert unchanged == {"a.x.com"}


def test_diff_detects_removed_asset(program):
    s1 = _complete(Scan.objects.create(program=program, target="a.x.com"))
    s2 = _complete(Scan.objects.create(program=program, target="a.x.com"))

    a1 = Asset.objects.create(program=program, hostname="a.x.com")
    a2 = Asset.objects.create(program=program, hostname="b.x.com")
    ScanAsset.objects.create(scan=s1, asset=a1)
    ScanAsset.objects.create(scan=s1, asset=a2)
    ScanAsset.objects.create(scan=s2, asset=a1)

    d = compute_diff(s2)
    removed = {a.hostname for a in d["assets"]["removed"]}
    assert removed == {"b.x.com"}


def test_diff_first_scan_all_new(program):
    s = _complete(Scan.objects.create(program=program, target="a.x.com"))
    a = Asset.objects.create(program=program, hostname="a.x.com")
    ScanAsset.objects.create(scan=s, asset=a)

    d = compute_diff(s)
    assert d["has_previous"] is False
    assert len(d["assets"]["added"]) == 1
    assert d["assets"]["removed"] == []


def test_diff_view_requires_login(client, user, program):
    s = _complete(Scan.objects.create(program=program, target="a.x.com"))
    r = client.get(reverse("scans:diff", args=[s.pk]))
    assert r.status_code == 302

    client.force_login(user)
    r = client.get(reverse("scans:diff", args=[s.pk]))
    assert r.status_code == 200


def test_diff_isolated_by_owner(client, user, program):
    other = User.objects.create_user("bob", password="x")
    other_prog = Program.objects.create(owner=other, name="Q", slug="q")
    s = _complete(Scan.objects.create(program=other_prog, target="b.x.com"))

    client.force_login(user)
    r = client.get(reverse("scans:diff", args=[s.pk]))
    assert r.status_code == 404
