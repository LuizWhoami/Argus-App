"""Testes da Fase 2A — models de assets e scans."""
import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from apps.assets.models import Asset, Endpoint
from apps.programs.models import Program
from apps.scans.models import Scan

User = get_user_model()


@pytest.fixture
def owner(db):
    return User.objects.create_user("owner", password="x")


@pytest.fixture
def program(owner):
    return Program.objects.create(owner=owner, name="P", slug="p")


# ---------------------------------------------------------------- assets

def test_asset_unique_per_program(program):
    Asset.objects.create(program=program, hostname="a.test.com")
    with pytest.raises(IntegrityError):
        Asset.objects.create(program=program, hostname="a.test.com")


def test_asset_cascade_on_program_delete(program):
    Asset.objects.create(program=program, hostname="a.test.com")
    program.delete()
    assert Asset.objects.count() == 0


def test_endpoint_unique_constraint(program):
    a = Asset.objects.create(program=program, hostname="a.test.com")
    Endpoint.objects.create(asset=a, url="https://a.test.com/x", method="GET")
    with pytest.raises(IntegrityError):
        Endpoint.objects.create(asset=a, url="https://a.test.com/x",
                                method="GET")


# ---------------------------------------------------------------- scans

def test_scan_starts_queued(program, owner):
    s = Scan.objects.create(program=program, target="a.test.com",
                            requested_by=owner)
    assert s.status == Scan.STATUS_QUEUED
    assert s.started_at is None
    assert not s.is_terminal()


def test_scan_state_machine_happy_path(program, owner):
    s = Scan.objects.create(program=program, target="a.test.com")
    s.mark_running()
    assert s.status == Scan.STATUS_RUNNING
    assert s.started_at is not None
    s.mark_completed()
    assert s.status == Scan.STATUS_COMPLETED
    assert s.finished_at is not None
    assert s.is_terminal()


def test_scan_cannot_go_running_twice(program):
    s = Scan.objects.create(program=program, target="a.test.com")
    s.mark_running()
    with pytest.raises(ValueError):
        s.mark_running()


def test_scan_cannot_fail_after_terminal(program):
    s = Scan.objects.create(program=program, target="a.test.com")
    s.mark_running()
    s.mark_completed()
    with pytest.raises(ValueError):
        s.mark_failed("late error")


def test_scan_cancel_from_running(program):
    s = Scan.objects.create(program=program, target="a.test.com")
    s.mark_running()
    s.mark_cancelled()
    assert s.status == Scan.STATUS_CANCELLED
    assert s.is_terminal()


def test_scan_cascade_on_program_delete(program):
    Scan.objects.create(program=program, target="a.test.com")
    program.delete()
    assert Scan.objects.count() == 0
