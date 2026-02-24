from datetime import datetime

from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse

from release_manager.models import ReleaseReport, RepoReport, RepoSelection
from release_manager.services import exporter, git_ops, scanner
from release_manager.settings import settings

router = APIRouter()


def _templates(request: Request):
    return request.app.state.templates


# ── Pages ──────────────────────────────────────────────────────


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return _templates(request).TemplateResponse(
        "index.html",
        {"request": request, "default_root_dir": settings.default_root_dir},
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
    selections: list[RepoSelection] = [
        RepoSelection(**s) for s in body.get("selections", [])
    ]

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

    report = ReleaseReport(
        generated_at=datetime.now(),
        root_dir=root_dir,
        repos=repo_reports,
        all_linear_keys=sorted(all_keys),
    )
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
    # Reuse collect logic
    request._body = None  # type: ignore[attr-defined]

    import json

    body = {
        "root_dir": last.root_dir,
        "selections": [s.model_dump() for s in selections],
    }
    # Build a fake scope — easier to just call the logic directly
    root_dir = last.root_dir
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

    report = ReleaseReport(
        generated_at=datetime.now(),
        root_dir=root_dir,
        repos=repo_reports,
        all_linear_keys=sorted(all_keys),
    )
    request.app.state.last_report = report
    return report.model_dump(mode="json")


@router.get("/api/export/{fmt}")
async def api_export(fmt: str, request: Request):
    report: ReleaseReport | None = request.app.state.last_report
    if not report:
        return Response("No report available", status_code=404)

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


# ── HTMX Partials ─────────────────────────────────────────────


@router.post("/partials/repo-list", response_class=HTMLResponse)
async def partial_repo_list(request: Request):
    form = await request.form()
    root_dir = str(form.get("root_dir", settings.default_root_dir))
    repos = scanner.scan_repos(root_dir)
    return _templates(request).TemplateResponse(
        "partials/repo_list.html",
        {"request": request, "repos": repos, "root_dir": root_dir},
    )


@router.post("/partials/report-table", response_class=HTMLResponse)
async def partial_report_table(request: Request):
    report: ReleaseReport | None = request.app.state.last_report
    return _templates(request).TemplateResponse(
        "partials/report_table.html",
        {"request": request, "report": report},
    )
