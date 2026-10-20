"""Cria ScanAsset/ScanEndpoint/ScanParameter para scans antigos.

Modos:
  padrao        usa a janela temporal do scan
  --force       liga TODOS os achados do programa ao scan indicado
  --scan-id N   limita a um scan especifico
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.assets.models import Asset, Endpoint, Parameter
from apps.scans.models import Scan, ScanAsset, ScanEndpoint, ScanParameter


class Command(BaseCommand):
    help = "Liga achados a scans."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--force", action="store_true",
                            help="ignora janela temporal; liga tudo do programa")
        parser.add_argument("--scan-id", type=int, default=None)

    def handle(self, *args, **opts):
        dry = opts["dry_run"]
        force = opts["force"]
        scan_id = opts["scan_id"]

        qs = Scan.objects.order_by("id")
        if scan_id:
            qs = qs.filter(pk=scan_id)

        for scan in qs:
            if not force and (
                scan.scan_assets.exists()
                or scan.scan_endpoints.exists()
                or scan.scan_parameters.exists()
            ):
                continue

            if force:
                assets = Asset.objects.filter(program=scan.program)
                endpoints = Endpoint.objects.filter(asset__program=scan.program)
                params = Parameter.objects.filter(
                    endpoint__asset__program=scan.program)
            else:
                t0 = scan.started_at or scan.created_at
                t1 = scan.finished_at or timezone.now()
                assets = Asset.objects.filter(
                    program=scan.program,
                    first_seen__gte=t0, first_seen__lte=t1)
                endpoints = Endpoint.objects.filter(
                    asset__program=scan.program,
                    discovered_at__gte=t0, discovered_at__lte=t1)
                params = Parameter.objects.filter(
                    endpoint__asset__program=scan.program,
                    endpoint__discovered_at__gte=t0,
                    endpoint__discovered_at__lte=t1)

            n_a, n_e, n_p = assets.count(), endpoints.count(), params.count()

            if dry:
                self.stdout.write(
                    f"scan#{scan.pk} {scan.target}: "
                    f"assets={n_a} endpoints={n_e} params={n_p}")
                continue

            for a in assets:
                ScanAsset.objects.get_or_create(scan=scan, asset=a)
            for e in endpoints:
                ScanEndpoint.objects.get_or_create(scan=scan, endpoint=e)
            for p in params:
                ScanParameter.objects.get_or_create(scan=scan, parameter=p)
            self.stdout.write(
                f"scan#{scan.pk} ligado: a={n_a} e={n_e} p={n_p}")
