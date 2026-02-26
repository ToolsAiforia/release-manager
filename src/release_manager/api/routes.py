from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse

from release_manager.models import (
    AppConfig,
    Release,
    ReleaseReport,
    RemoteRepo,
    RepoReport,
    RepoSelection,
    TagInfo,
)
from release_manager.services import exporter, git_ops, linear, remote, scanner
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
    config: AppConfig = request.app.state.app_config
    return _templates(request).TemplateResponse(
        "index.html",
        {
            "request": request,
            "default_root_dir": settings.default_root_dir,
            "active_page": "repos",
            "app_config": config,
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


# ── Settings & Remote Repos API ────────────────────────────


@router.get("/api/settings")
async def api_get_settings(request: Request):
    """Return current credentials (tokens masked)."""
    config: AppConfig = request.app.state.app_config
    return {
        "git_username": config.git_username,
        "has_token": bool(config.git_token),
        "has_linear_key": bool(config.linear_api_key),
    }


@router.post("/api/settings")
async def api_save_settings(request: Request):
    """Update credentials."""
    body = await request.json()
    config: AppConfig = request.app.state.app_config
    config.git_username = body.get("git_username", config.git_username)
    token = body.get("git_token", "")
    if token:
        config.git_token = token
    linear_key = body.get("linear_api_key", "")
    if linear_key:
        config.linear_api_key = linear_key
    remote.save_config(settings.repos_dir, config)
    request.app.state.app_config = config
    return {"ok": True}


@router.post("/api/remote-repos")
async def api_add_remote_repo(request: Request):
    """Add a remote repo URL, clone it."""
    body = await request.json()
    url = body.get("url", "").strip()
    if not url:
        return Response("URL is required", status_code=400)

    config: AppConfig = request.app.state.app_config

    # Check for duplicate
    for r in config.remote_repos:
        if r.url == url:
            return Response("Repo already added", status_code=409)

    name = remote.repo_name_from_url(url)

    try:
        remote.clone_repo(
            url, settings.repos_dir,
            config.git_username, config.git_token,
        )
    except Exception as e:
        return Response(f"Clone failed: {e}", status_code=500)

    repo = RemoteRepo(
        id=uuid4().hex[:12],
        url=url,
        name=name,
        added_at=datetime.now(),
        last_synced=datetime.now(),
    )
    config.remote_repos.append(repo)
    remote.save_config(settings.repos_dir, config)

    return {"id": repo.id, "name": repo.name}


@router.delete("/api/remote-repos/{repo_id}")
async def api_remove_remote_repo(repo_id: str, request: Request):
    """Remove a remote repo and its cloned directory."""
    config: AppConfig = request.app.state.app_config
    for i, r in enumerate(config.remote_repos):
        if r.id == repo_id:
            remote.remove_repo(
                r.name, settings.repos_dir,
                is_local_import=bool(r.local_path),
            )
            config.remote_repos.pop(i)
            remote.save_config(settings.repos_dir, config)
            return {"ok": True}
    return Response("Not found", status_code=404)


@router.post("/api/remote-repos/{repo_id}/sync")
async def api_sync_remote_repo(repo_id: str, request: Request):
    """Fetch + pull a specific remote repo."""
    config: AppConfig = request.app.state.app_config
    for r in config.remote_repos:
        if r.id == repo_id:
            try:
                msg = remote.sync_repo(
                    r.name, settings.repos_dir,
                    config.git_username, config.git_token,
                    r.url, r.local_path,
                )
                r.last_synced = datetime.now()
                remote.save_config(settings.repos_dir, config)
                return {"message": msg}
            except Exception as e:
                return Response(f"Sync failed: {e}", status_code=500)
    return Response("Not found", status_code=404)


@router.post("/api/import-local")
async def api_import_local(request: Request):
    """Scan a local directory and import repos into remote list."""
    body = await request.json()
    root_dir = body.get("root_dir", "").strip()
    if not root_dir:
        return Response("Directory path is required", status_code=400)

    config: AppConfig = request.app.state.app_config
    repos = scanner.scan_repos(root_dir)

    existing_paths = {r.local_path for r in config.remote_repos if r.local_path}
    existing_urls = {r.url for r in config.remote_repos}

    added = 0
    skipped = 0
    for repo in repos:
        if repo.path in existing_paths:
            skipped += 1
            continue

        origin_url = remote.get_origin_url(repo.path) or ""
        if origin_url and origin_url in existing_urls:
            skipped += 1
            continue

        entry = RemoteRepo(
            id=uuid4().hex[:12],
            url=origin_url,
            name=repo.name,
            added_at=datetime.now(),
            local_path=repo.path,
        )
        config.remote_repos.append(entry)
        added += 1

    if added > 0:
        remote.save_config(settings.repos_dir, config)

    return {"added": added, "skipped": skipped, "total": len(repos)}


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


@router.get("/api/export/contributors")
async def api_export_contributors(request: Request):
    """Export contributors by component as CSV (draft)."""
    report: ReleaseReport | None = request.app.state.last_report
    if not report:
        return Response("No report available", status_code=404)
    content = exporter.contributors_to_csv(report)
    return Response(
        content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=contributors.csv"},
    )


@router.get("/api/export/commits")
async def api_export_commits(request: Request):
    """Export all commits as CSV (draft)."""
    report: ReleaseReport | None = request.app.state.last_report
    if not report:
        return Response("No report available", status_code=404)
    content = exporter.commits_to_csv(report)
    return Response(
        content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=commits.csv"},
    )


@router.get("/api/releases/{release_id}/export/contributors")
async def api_export_release_contributors(release_id: str, request: Request):
    """Export contributors by component as CSV (saved release)."""
    release = _find_release(request, release_id)
    if not release:
        return Response("Release not found", status_code=404)
    content = exporter.contributors_to_csv(release.report)
    return Response(
        content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=contributors.csv"},
    )


@router.get("/api/releases/{release_id}/export/commits")
async def api_export_release_commits(release_id: str, request: Request):
    """Export all commits as CSV (saved release)."""
    release = _find_release(request, release_id)
    if not release:
        return Response("Release not found", status_code=404)
    content = exporter.commits_to_csv(release.report)
    return Response(
        content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=commits.csv"},
    )


# ── Linear API ─────────────────────────────────────────────


@router.get("/api/linear/issue/{identifier}")
async def api_linear_issue(identifier: str, request: Request):
    """Fetch a single Linear issue by identifier (e.g. ABC-123)."""
    config: AppConfig = request.app.state.app_config
    if not config.linear_api_key:
        return Response("Linear API key not configured", status_code=400)
    issue = linear.fetch_issue(identifier.upper(), config.linear_api_key)
    if not issue:
        return Response("Issue not found", status_code=404)
    return issue


@router.post("/api/linear/issues")
async def api_linear_issues(request: Request):
    """Batch-fetch Linear issues. Body: {"keys": ["ABC-123", ...]}."""
    config: AppConfig = request.app.state.app_config
    if not config.linear_api_key:
        return Response("Linear API key not configured", status_code=400)
    body = await request.json()
    keys = [k.upper() for k in body.get("keys", [])]
    if not keys:
        return {}
    return linear.fetch_issues(keys, config.linear_api_key)


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


@router.post("/partials/remote-repo-list", response_class=HTMLResponse)
async def partial_remote_repo_list(request: Request):
    """Return the remote repos table with tags loaded."""
    config: AppConfig = request.app.state.app_config
    repo_tags: dict[str, list[TagInfo]] = {}
    for r in config.remote_repos:
        repo_path = remote.get_repo_path(r.name, settings.repos_dir, r.local_path)
        try:
            repo_tags[r.name] = git_ops.get_tags(repo_path)
        except Exception:
            repo_tags[r.name] = []
    return _templates(request).TemplateResponse(
        "partials/remote_repo_list.html",
        {
            "request": request,
            "app_config": config,
            "repo_tags": repo_tags,
        },
    )


@router.post("/partials/remote-collect-and-redirect")
async def partial_remote_collect_and_redirect(request: Request):
    """Collect commits from selected remote repos, redirect to draft."""
    form = await request.form()
    selected_repos = form.getlist("selected_repos")

    if not selected_repos:
        return HTMLResponse(
            '<div class="px-4 py-3 rounded-lg bg-red-50 dark:bg-red-500/10 border border-red-200 '
            'dark:border-red-500/20 text-sm text-red-700 dark:text-red-300">'
            "Select at least one repo.</div>",
            headers={"HX-Reswap": "innerHTML", "HX-Retarget": "#remote-repo-list"},
        )

    config: AppConfig = request.app.state.app_config
    selections: list[RepoSelection] = []
    for name in selected_repos:
        from_tag = str(form.get(f"from_tag__{name}", ""))
        to_tag = str(form.get(f"to_tag__{name}", ""))
        if from_tag and to_tag:
            selections.append(
                RepoSelection(repo_name=name, from_tag=from_tag, to_tag=to_tag)
            )

    if not selections:
        return HTMLResponse(
            '<div class="px-4 py-3 rounded-lg bg-red-50 dark:bg-red-500/10 border border-red-200 '
            'dark:border-red-500/20 text-sm text-red-700 dark:text-red-300">'
            "Select at least one repo with both from/to tags.</div>",
            headers={"HX-Reswap": "innerHTML", "HX-Retarget": "#remote-repo-list"},
        )

    # Build report using clone paths instead of root_dir/name
    # Build a lookup for local_path by repo name
    repo_lookup = {r.name: r for r in config.remote_repos}
    repo_reports: list[RepoReport] = []
    all_keys: set[str] = set()
    for sel in selections:
        entry = repo_lookup.get(sel.repo_name)
        lp = entry.local_path if entry else None
        repo_path = remote.get_repo_path(sel.repo_name, settings.repos_dir, lp)
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

    report = ReleaseReport(
        generated_at=datetime.now(),
        root_dir=settings.repos_dir,
        repos=repo_reports,
        all_linear_keys=sorted(all_keys),
    )
    request.app.state.last_report = report
    return HTMLResponse("", headers={"HX-Redirect": "/draft"})


@router.post("/partials/remote-sync-all", response_class=HTMLResponse)
async def partial_remote_sync_all(request: Request):
    """Sync all remote repos, then return refreshed repo list."""
    config: AppConfig = request.app.state.app_config
    for r in config.remote_repos:
        try:
            remote.sync_repo(
                r.name, settings.repos_dir,
                config.git_username, config.git_token,
                r.url, r.local_path,
            )
            r.last_synced = datetime.now()
        except Exception:
            pass
    remote.save_config(settings.repos_dir, config)

    repo_tags: dict[str, list[TagInfo]] = {}
    for r in config.remote_repos:
        repo_path = remote.get_repo_path(r.name, settings.repos_dir, r.local_path)
        try:
            repo_tags[r.name] = git_ops.get_tags(repo_path)
        except Exception:
            repo_tags[r.name] = []

    return _templates(request).TemplateResponse(
        "partials/remote_repo_list.html",
        {
            "request": request,
            "app_config": config,
            "repo_tags": repo_tags,
        },
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
        {"request": request, "report": report, "export_base": "/api/export"},
    )
