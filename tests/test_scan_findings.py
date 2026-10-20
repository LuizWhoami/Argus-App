"""Achados vinculados ao scan."""
import pytest
from django.contrib.auth import get_user_model

from apps.assets.models import Asset, Endpoint
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


def test_link_asset_to_scan(program, scan):
    a = Asset.objects.create(program=program, hostname="a.x.com")
    ScanAsset.objects.create(scan=scan, asset=a, is_new=True)
    assert scan.scan_assets.count() == 1
    assert scan.scan_assets.first().asset == a


def test_asset_appears_in_multiple_scans(program, scan):
    a = Asset.objects.create(program=program, hostname="a.x.com")
    s2 = Scan.objects.create(program=program, target="a.x.com")

    ScanAsset.objects.create(scan=scan, asset=a, is_new=True)
    ScanAsset.objects.create(scan=s2, asset=a, is_new=False)

    assert a.scan_links.count() == 2


def test_link_endpoint_to_scan(program, scan):
    a = Asset.objects.create(program=program, hostname="a.x.com")
    e = Endpoint.objects.create(asset=a, url="https://a.x.com/api", method="GET")
    ScanEndpoint.objects.create(scan=scan, endpoint=e, is_new=True)
    assert scan.scan_endpoints.count() == 1


def test_cannot_duplicate_link(program, scan):
    from django.db import IntegrityError
    a = Asset.objects.create(program=program, hostname="a.x.com")
    ScanAsset.objects.create(scan=scan, asset=a)
    with pytest.raises(IntegrityError):
        ScanAsset.objects.create(scan=scan, asset=a)
