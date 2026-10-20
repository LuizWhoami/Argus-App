"""Preenche snapshots de links antigos."""
from django.core.management.base import BaseCommand

from apps.scans.models import Scan


class Command(BaseCommand):
    help = "Preenche snapshots de links antigos."

    def add_arguments(self, parser):
        parser.add_argument("--scan-id", type=int, default=None)

    def handle(self, *args, **opts):
        qs = Scan.objects.order_by("id")
        if opts["scan_id"]:
            qs = qs.filter(pk=opts["scan_id"])

        total = 0
        for scan in qs:
            for link in scan.scan_assets.select_related("asset"):
                link.snap_ip = link.asset.ip
                link.snap_is_alive = link.asset.is_alive
                link.save(update_fields=["snap_ip", "snap_is_alive"])
                total += 1
            for link in scan.scan_endpoints.select_related("endpoint"):
                e = link.endpoint
                link.snap_status_code = e.status_code
                link.snap_content_type = e.content_type
                link.snap_kind = e.kind
                link.save(update_fields=[
                    "snap_status_code", "snap_content_type", "snap_kind"])
                total += 1
            for link in scan.scan_parameters.select_related("parameter"):
                link.snap_location = link.parameter.location
                link.save(update_fields=["snap_location"])
                total += 1

        self.stdout.write(self.style.SUCCESS(
            f"{total} links com snapshot preenchido"))
