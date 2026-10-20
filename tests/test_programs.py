"""Testes da Fase 1 — isolamento entre usuarios + validacao de escopo."""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.programs.models import Program, ScopeEntry

User = get_user_model()


@pytest.fixture
def user_a(db):
    return User.objects.create_user("alice", password="x")


@pytest.fixture
def user_b(db):
    return User.objects.create_user("bob", password="x")


def test_create_program_assigns_owner(client, user_a):
    client.force_login(user_a)
    r = client.post(reverse("programs:create"), {"name": "Prog A", "max_rps": 3})
    assert r.status_code == 302
    p = Program.objects.get(name="Prog A")
    assert p.owner == user_a


def test_user_cannot_see_other_users_program(client, user_a, user_b):
    p = Program.objects.create(owner=user_a, name="Privado", slug="privado")
    client.force_login(user_b)
    r = client.get(reverse("programs:detail", args=[p.slug]))
    assert r.status_code == 404


def test_scope_preview_respects_exclusion(client, user_a):
    p = Program.objects.create(owner=user_a, name="P", slug="p")
    ScopeEntry.objects.create(program=p, kind="allow", pattern="*.x.com")
    ScopeEntry.objects.create(program=p, kind="exclude", pattern="admin.x.com")

    client.force_login(user_a)
    r1 = client.get(reverse("programs:detail", args=["p"]), {"check": "a.x.com"})
    assert b"ALLOW" in r1.content

    r2 = client.get(reverse("programs:detail", args=["p"]), {"check": "admin.x.com"})
    assert b"DENY" in r2.content


def test_scope_entry_duplicate_is_ignored(client, user_a):
    p = Program.objects.create(owner=user_a, name="P", slug="p")
    client.force_login(user_a)
    url = reverse("programs:scope_add", args=["p"])
    client.post(url, {"kind": "allow", "pattern": "*.x.com"})
    client.post(url, {"kind": "allow", "pattern": "*.x.com"})
    assert ScopeEntry.objects.filter(program=p).count() == 1


def test_scope_entry_invalid_kind_rejected(client, user_a):
    p = Program.objects.create(owner=user_a, name="P", slug="p")
    client.force_login(user_a)
    url = reverse("programs:scope_add", args=["p"])
    r = client.post(url, {"kind": "whatever", "pattern": "x.com"})
    assert r.status_code == 400


def test_me_endpoint_returns_user_info(client, user_a):
    client.force_login(user_a)
    r = client.get(reverse("accounts:me"))
    assert r.status_code == 200
    assert r.json()["username"] == "alice"
