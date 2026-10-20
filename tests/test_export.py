"""Testes dos exports de scan."""
import json

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.assets.models import Asset, Endpoint, Parameter
from apps.programs.models import Program
from apps.scans.exporters import to_csv, to_json, to_markdown
from apps.scans.models import Scan, ScanAsset, ScanEndpoint, ScanParameter

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


@pytest.fixture
def populated(program, scan):
    a = Asset.objects.create(program=program, hostname="a.x.com",
                             ip="1.2.3.4", is_alive=True,
                             verification="verified",
                             verification_note="confirmado")
    ScanAsset.objects.create(scan=scan, asset=a)

    e = Endpoint.objects.create(asset=a, url="https://a.x.com/api/v1",
                                method="GET", status_code=200,
                                source="wordlist", kind="rest")
    ScanEndpoint.objects.create(scan=scan, endpoint=e)

    p = Parameter.objects.create(endpoint=e, name="id", location="query")
    ScanParameter.objects.create(scan=scan, parameter=p)

    return scan


def test_json_export(populated):
    body = to_json(populated)
    data = json.loads(body)
    assert data["scan"]["target"] == "a.x.com"
    assert data["summary"]["assets"] == 1
    assert data["summary"]["apis"] == 1
    assert data["summary"]["params"] == 1
    assert data["assets"][0]["verification"] == "verified"


def test_csv_export(populated):
    body = to_csv(populated)
    lines = [l for l in body.splitlines() if l.strip()]
    assert len(lines) >= 3   # header + asset + endpoint (+ param)
    assert "a.x.com" in body
    assert "verified" in body


def test_markdown_export(populated):
    body = to_markdown(populated)
    assert "# Scan #" in body
    assert "a.x.com" in body
    assert "API endpoints" in body
    assert "confirmado" in body
    assert "Argus — Autonomous Security Research Platform" in body


def test_export_endpoints_respect_owner(client, user, populated):
    client.force_login(user)
    for name in ("export_md", "export_csv", "export_json"):
        r = client.get(reverse(f"scans:{name}", args=[populated.pk]))
        assert r.status_code == 200
        assert "attachment" in r["Content-Disposition"]


def test_export_denied_for_other_user(client, populated):
    other = User.objects.create_user("bob", password="x")
    client.force_login(other)
    r = client.get(reverse("scans:export_json", args=[populated.pk]))
    assert r.status_code == 404
