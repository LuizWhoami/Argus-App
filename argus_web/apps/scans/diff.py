"""Diff entre dois scans do mesmo alvo/programa."""
from typing import Optional

from apps.assets.models import Asset, Endpoint, Parameter

from .models import Scan


ASSET_FIELDS = [
    ("snap_ip", "ip", "IP"),
    ("snap_is_alive", "is_alive", "Alive"),
]
ENDPOINT_FIELDS = [
    ("snap_status_code", "status_code", "Status"),
    ("snap_content_type", "content_type", "Content-Type"),
    ("snap_kind", "kind", "Tipo"),
]
PARAM_FIELDS = [
    ("snap_location", "location", "Local"),
]


def previous_scan(scan: Scan) -> Optional[Scan]:
    return (Scan.objects
            .filter(program=scan.program, target=scan.target, pk__lt=scan.pk)
            .exclude(status=Scan.STATUS_QUEUED)
            .order_by("-pk")
            .first())


def _fmt(v):
    if v is None or v == "":
        return "—"
    if isinstance(v, bool):
        return "sim" if v else "não"
    return str(v)


def _compare(prev_link, cur_obj, field_map):
    out = []
    for prev_attr, cur_attr, label in field_map:
        old = getattr(prev_link, prev_attr, None)
        new = getattr(cur_obj, cur_attr, None)
        if old != new:
            out.append({"label": label, "old": _fmt(old), "new": _fmt(new)})
    return out


def _obj_of(link):
    return (getattr(link, "asset", None)
            or getattr(link, "endpoint", None)
            or getattr(link, "parameter", None))


def _diff_group(cur_map, prev_map, field_map):
    cur_pks, prev_pks = set(cur_map), set(prev_map)

    added = [_obj_of(cur_map[pk]) for pk in cur_pks - prev_pks]
    removed = [_obj_of(prev_map[pk]) for pk in prev_pks - cur_pks]

    changed, unchanged = [], []
    for pk in cur_pks & prev_pks:
        cur_obj = _obj_of(cur_map[pk])
        changes = _compare(prev_map[pk], cur_obj, field_map)
        if changes:
            changed.append({"obj": cur_obj, "changes": changes})
        else:
            unchanged.append(cur_obj)

    return {"added": added, "removed": removed,
            "changed": changed, "unchanged": unchanged}


def compute_diff(scan: Scan) -> dict:
    prev = previous_scan(scan)

    if not prev:
        cur_a = [l.asset for l in scan.scan_assets.select_related("asset")]
        cur_e = [l.endpoint for l in scan.scan_endpoints.select_related("endpoint")]
        cur_p = [l.parameter for l in scan.scan_parameters.select_related("parameter")]
        return {
            "has_previous": False, "previous": None,
            "assets": {"added": cur_a, "removed": [], "changed": [], "unchanged": []},
            "endpoints": {"added": cur_e, "removed": [], "changed": [], "unchanged": []},
            "params": {"added": cur_p, "removed": [], "changed": [], "unchanged": []},
        }

    cur_assets = {l.asset_id: l for l in scan.scan_assets.select_related("asset")}
    prev_assets = {l.asset_id: l for l in prev.scan_assets.select_related("asset")}
    cur_eps = {l.endpoint_id: l for l in scan.scan_endpoints.select_related("endpoint")}
    prev_eps = {l.endpoint_id: l for l in prev.scan_endpoints.select_related("endpoint")}
    cur_params = {l.parameter_id: l for l in scan.scan_parameters.select_related("parameter")}
    prev_params = {l.parameter_id: l for l in prev.scan_parameters.select_related("parameter")}

    return {
        "has_previous": True,
        "previous": prev,
        "assets": _diff_group(cur_assets, prev_assets, ASSET_FIELDS),
        "endpoints": _diff_group(cur_eps, prev_eps, ENDPOINT_FIELDS),
        "params": _diff_group(cur_params, prev_params, PARAM_FIELDS),
    }


def diff_counts(scan: Scan) -> dict:
    d = compute_diff(scan)
    if not d["has_previous"]:
        return {"new": 0, "removed": 0, "changed": 0, "has_previous": False}
    return {
        "new": sum(len(d[k]["added"]) for k in ("assets", "endpoints", "params")),
        "removed": sum(len(d[k]["removed"]) for k in ("assets", "endpoints", "params")),
        "changed": sum(len(d[k]["changed"]) for k in ("assets", "endpoints", "params")),
        "has_previous": True,
    }
