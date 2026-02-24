from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse

from release_manager.models import (
    Release,
    ReleaseReport,
    RepoReport,
    RepoSelection,
    TagInfo,
)
from release_manager.services import exporter, git_ops, scanner
from release_manager.settings import settings

router = APIRouter()


def _templates(request: Request):
    return request.app.state.templates


def _build_report(root_dir: str, selections: list[RepoSelection]) -> ReleaseReport:
    """Build a ReleaseReport from a list of repo selections."""
    repo_reports: list[RepoReport] = []
    all_keys: set[str] = set()

    for sel in selections:
        repo_path = f"{root_dir.rstrip('/')}/{sel.repo_name}"
        commits = git_ops.get_commits_between_tags(
            repo_path, sel.from_tag, sel.to_tag
        )
        repo_keys: list[str] = []
        seen: set[str] = set()
        for c in commits:
            for k in c.linear_keys:
                if k not in seen:
                    seen.add(k)
                    repo_keys.append(k)
        all_keys.update(repo_keys)

        repo_reports.append(
            RepoReport(
                repo_name=sel.repo_name,
                from_tag=sel.from_tag,
                to_tag=sel.to_tag,
                commits=commits,
                linear_keys=repo_keys,
            )
        )

    return ReleaseReport(
        generated_at=datetime.now(),
        root_dir=root_dir,
        repos=repo_reports,
        all_linear_keys=sorted(all_keys),
    )


def _find_release(request: Request, release_id: str) -> Release | None:
    """Find a release by id in app.state.releases."""
    for rel in request.app.state.releases:
        if rel.id == release_id:
            return rel
    return None


# ── Pages ──────────────────────────────────────────────────────


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return _templates(request).TemplateResponse(
        "index.html",
        {
            "request": request,
            "default_root_dir": settings.default_root_dir,
            "active_page": "repos",
        },
    )


@router.get("/draft", response_class=HTMLResponse)
async def draft_page(request: Request):
    report: ReleaseReport | None = request.app.state.last_report
    return _templates(request).TemplateResponse(
        "draft.html",
        {
            "request": request,
            "report": report,
            "active_page": "draft",
        },
    )


@router.get("/releases", response_class=HTMLResponse)
async def releases_page(request: Request):
    releases: list[Release] = request.app.state.releases
    return _templates(request).TemplateResponse(
        "releases.html",
        {
            "request": request,
            "releases": list(reversed(releases)),
            "active_page": "releases",
        },
    )


@router.get("/releases/{release_id}", response_class=HTMLResponse)
async def release_detail_page(release_id: str, request: Request):
    release = _find_release(request, release_id)
    return _templates(request).TemplateResponse(
        "release_detail.html",
        {
            "request": request,
            "release": release,
            "active_page": "releases",
        },
    )


# ── API ────────────────────────────────────────────────────────


@router.post("/api/scan")
async def api_scan(request: Request):
    form = await request.form()
    root_dir = str(form.get("root_dir", settings.default_root_dir))
    repos = scanner.scan_repos(root_dir)
    return {"repos": [r.model_dump() for r in repos]}


@router.get("/api/repos/{name}/tags")
async def api_tags(name: str, request: Request):
    form_root = request.query_params.get("root_dir", settings.default_root_dir)
    repo_path = f"{form_root.rstrip('/')}/{name}"
    tags = git_ops.get_tags(repo_path)
    return {"tags": [t.model_dump(mode="json") for t in tags]}


@router.post("/api/repos/{name}/fetch")
async def api_fetch(name: str, request: Request):
    form = await request.form()
    root_dir = str(form.get("root_dir", settings.default_root_dir))
    repo_path = f"{root_dir.rstrip('/')}/{name}"
    message = git_ops.fetch_and_pull(repo_path)
    return {"message": message}


@router.post("/api/collect")
async def api_collect(request: Request):
    body = await request.json()
    root_dir = body.get("root_dir", settings.default_root_dir)
    selections = [RepoSelection(**s) for s in body.get("selections", [])]
    report = _build_report(root_dir, selections)
    request.app.state.last_report = report
    return report.model_dump(mode="json")


@router.post("/api/refresh")
async def api_refresh(request: Request):
    """Re-collect using the same selections from the last report."""
    last: ReleaseReport | None = request.app.state.last_report
    if not last:
        return {"error": "No previous report to refresh"}

    selections = [
        RepoSelection(
            repo_name=r.repo_name, from_tag=r.from_tag, to_tag=r.to_tag
        )
        for r in last.repos
    ]
    report = _build_report(last.root_dir, selections)
    request.app.state.last_report = report
    return report.model_dump(mode="json")


# ── Releases API ───────────────────────────────────────────────


@router.post("/api/releases")
async def api_create_release(request: Request):
    """Create a named release from the current draft (last_report)."""
    body = await request.json()
    name = body.get("name", "").strip()
    if not name:
        return {"error": "Release name is required"}

    report: ReleaseReport | None = request.app.state.last_report
    if not report:
        return {"error": "No draft to create release from"}

    release = Release(
        id=uuid4().hex[:12],
        name=name,
        created_at=datetime.now(),
        report=report,
    )
    request.app.state.releases.append(release)
    return {"id": release.id, "name": release.name}


@router.delete("/api/releases/{release_id}")
async def api_delete_release(release_id: str, request: Request):
    """Delete a release by id."""
    releases: list[Release] = request.app.state.releases
    for i, rel in enumerate(releases):
        if rel.id == release_id:
            releases.pop(i)
            return {"ok": True}
    return Response("Not found", status_code=404)


# ── Export ─────────────────────────────────────────────────────


def _export_report(report: ReleaseReport, fmt: str) -> Response:
    """Export a report in the given format."""
    if fmt == "csv":
        content = exporter.to_csv(report)
        return Response(
            content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=release_notes.csv"},
        )
    elif fmt == "markdown":
        content = exporter.to_markdown(report)
        return Response(
            content,
            media_type="text/markdown",
            headers={"Content-Disposition": "attachment; filename=release_notes.md"},
        )
    elif fmt == "json":
        content = exporter.to_json(report)
        return Response(
            content,
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=release_notes.json"},
        )
    else:
        return Response(f"Unknown format: {fmt}", status_code=400)


@router.get("/api/export/{fmt}")
async def api_export(fmt: str, request: Request):
    """Export the current draft."""
    report: ReleaseReport | None = request.app.state.last_report
    if not report:
        return Response("No report available", status_code=404)
    return _export_report(report, fmt)


@router.get("/api/releases/{release_id}/export/{fmt}")
async def api_export_release(release_id: str, fmt: str, request: Request):
    """Export a specific saved release."""
    release = _find_release(request, release_id)
    if not release:
        return Response("Release not found", status_code=404)
    return _export_report(release.report, fmt)


# ── HTMX Partials ─────────────────────────────────────────────


@router.post("/partials/repo-list", response_class=HTMLResponse)
async def partial_repo_list(request: Request):
    form = await request.form()
    root_dir = str(form.get("root_dir", settings.default_root_dir))
    repos = scanner.scan_repos(root_dir)

    # Auto-load tags for all repos
    repo_tags: dict[str, list[TagInfo]] = {}
    for repo in repos:
        try:
            repo_tags[repo.name] = git_ops.get_tags(repo.path)
        except Exception:
            repo_tags[repo.name] = []

    return _templates(request).TemplateResponse(
        "partials/repo_list.html",
        {"request": request, "repos": repos, "root_dir": root_dir, "repo_tags": repo_tags},
    )


@router.post("/partials/collect-and-redirect")
async def partial_collect_and_redirect(request: Request):
    """Collect commits from selected repos, store report, redirect to draft page."""
    form = await request.form()
    root_dir = str(form.get("root_dir", settings.default_root_dir))
    selected_repos = form.getlist("selected_repos")

    if not selected_repos:
        return HTMLResponse(
            '<div class="px-4 py-3 rounded-lg bg-red-50 dark:bg-red-500/10 border border-red-200 '
            'dark:border-red-500/20 text-sm text-red-700 dark:text-red-300">'
            "Select at least one repo.</div>",
            headers={"HX-Reswap": "innerHTML", "HX-Retarget": "#repo-list"},
        )

    selections: list[RepoSelection] = []
    for name in selected_repos:
        from_tag = str(form.get(f"from_tag__{name}", ""))
        to_tag = str(form.get(f"to_tag__{name}", ""))
        if from_tag and to_tag:
            selections.append(RepoSelection(repo_name=name, from_tag=from_tag, to_tag=to_tag))

    if not selections:
        return HTMLResponse(
            '<div class="px-4 py-3 rounded-lg bg-red-50 dark:bg-red-500/10 border border-red-200 '
            'dark:border-red-500/20 text-sm text-red-700 dark:text-red-300">'
            "Select at least one repo with both from/to tags.</div>",
            headers={"HX-Reswap": "innerHTML", "HX-Retarget": "#repo-list"},
        )

    report = _build_report(root_dir, selections)
    request.app.state.last_report = report

    # Tell HTMX to redirect to the draft page
    return HTMLResponse("", headers={"HX-Redirect": "/draft"})


@router.post("/partials/fetch-and-reload", response_class=HTMLResponse)
async def partial_fetch_and_reload(request: Request):
    """Fetch all repos, then re-scan + reload tags. Return refreshed repo list."""
    form = await request.form()
    root_dir = str(form.get("root_dir", settings.default_root_dir))

    # Fetch all repos first
    repos = scanner.scan_repos(root_dir)
    for repo in repos:
        try:
            git_ops.fetch_and_pull(repo.path)
        except Exception:
            pass

    # Re-scan and load tags
    repos = scanner.scan_repos(root_dir)
    repo_tags: dict[str, list[TagInfo]] = {}
    for repo in repos:
        try:
            repo_tags[repo.name] = git_ops.get_tags(repo.path)
        except Exception:
            repo_tags[repo.name] = []

    return _templates(request).TemplateResponse(
        "partials/repo_list.html",
        {"request": request, "repos": repos, "root_dir": root_dir, "repo_tags": repo_tags},
    )


@router.post("/partials/refresh-report", response_class=HTMLResponse)
async def partial_refresh_report(request: Request):
    """Re-collect using last report's selections, return updated report content."""
    last: ReleaseReport | None = request.app.state.last_report
    if not last:
        return HTMLResponse(
            '<p class="text-sm text-gray-500 dark:text-gray-400 text-center py-8">'
            "No previous report to refresh.</p>"
        )

    selections = [
        RepoSelection(repo_name=r.repo_name, from_tag=r.from_tag, to_tag=r.to_tag)
        for r in last.repos
    ]
    report = _build_report(last.root_dir, selections)
    request.app.state.last_report = report
    return _templates(request).TemplateResponse(
        "partials/report_content.html",
        {"request": request, "report": report},
    )
