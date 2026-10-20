"""Testes da visualizacao por etapa."""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.assets.models import Asset, Endpoint, Parameter
from apps.programs.models import Program
from apps.scans.models import Scan, ScanAsset, ScanEndpoint

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user("alice", password="x")


@pytest.fixture
def program(user):
    return Program.objects.create(owner=user, name="P", slug="p")


@pytest.fixture
def scan(program):
    return Scan.objects.create(program=program, target="a.x.com")


def test_stage_subdomains_lists_assets(client, user, program, scan):
    a = Asset.objects.create(program=program, hostname="a.x.com")
    ScanAsset.objects.create(scan=scan, asset=a)
    client.force_login(user)
    r = client.get(reverse("scans:stage", args=[scan.pk, "subdomains"]))
    assert r.status_code == 200
    assert b"a.x.com" in r.content


def test_stage_crawl_lists_katana_endpoints(client, user, program, scan):
    a = Asset.objects.create(program=program, hostname="a.x.com")
    e = Endpoint.objects.create(asset=a, url="https://a.x.com/x",
                                method="GET", source="katana")
    ScanEndpoint.objects.create(scan=scan, endpoint=e)
    client.force_login(user)
    r = client.get(reverse("scans:stage", args=[scan.pk, "crawl"]))
    assert r.status_code == 200
    assert b"a.x.com/x" in r.content


def test_stage_api_only_shows_endpoints_with_kind(client, user, program, scan):
    a = Asset.objects.create(program=program, hostname="a.x.com")
    plain = Endpoint.objects.create(asset=a, url="https://a.x.com/plain",
                                    method="GET", source="katana")
    api = Endpoint.objects.create(asset=a, url="https://a.x.com/api",
                                  method="GET", source="wordlist",
                                  kind="rest")
    ScanEndpoint.objects.create(scan=scan, endpoint=plain)
    ScanEndpoint.objects.create(scan=scan, endpoint=api)
    client.force_login(user)
    r = client.get(reverse("scans:stage", args=[scan.pk, "api"]))
    assert b"/api" in r.content
    assert b"/plain" not in r.content


def test_stage_unknown_returns_404(client, user, scan):
    client.force_login(user)
    r = client.get(reverse("scans:stage", args=[scan.pk, "zznope"]))
    assert r.status_code == 404


def test_stage_isolated_by_owner(client, user, program, scan):
    other = User.objects.create_user("bob", password="x")
    client.force_login(other)
    r = client.get(reverse("scans:stage", args=[scan.pk, "subdomains"]))
    assert r.status_code == 404
