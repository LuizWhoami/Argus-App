"""View do diff entre scans."""
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from .diff import compute_diff
from .models import Scan


@login_required
def diff_view(request, pk):
    scan = get_object_or_404(
        Scan, pk=pk, program__owner=request.user)
    diff = compute_diff(scan)
    return render(request, "scans/diff.html", {
        "scan": scan,
        "diff": diff,
    })
