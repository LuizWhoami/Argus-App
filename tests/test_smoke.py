"""Smoke tests da Fase 0 — nao tocam ativos publicos."""
from argus_agent.scope import Scope


def test_scope_allow_excluded_priority():
    s = Scope(allowed=["*.x.com"], excluded=["admin.x.com"])
    assert s.is_allowed("a.x.com") is True
    assert s.is_allowed("admin.x.com") is False


def test_scope_allow_wildcard():
    s = Scope(allowed=["*.x.com"], excluded=[])
    assert s.is_allowed("deep.a.x.com") is True
    assert s.is_allowed("other.com") is False


def test_scope_deny_unknown():
    s = Scope(allowed=["a.com"], excluded=[])
    assert s.is_allowed("b.com") is False


def test_celery_echo_task():
    from apps.integrations.tasks import echo_task
    result = echo_task.apply(args=["ping"])
    assert result.get() == "ping"


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
