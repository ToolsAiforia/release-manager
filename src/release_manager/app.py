import re
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from release_manager.api.routes import router
from release_manager.services import remote
from release_manager.settings import settings

PACKAGE_DIR = Path(__file__).parent

BOT_PATTERNS = [
    re.compile(p, re.I)
    for p in [
        r"\[bot\]",
        r"^dependabot",
        r"^renovate",
        r"^github-actions",
        r"^bender-",
        r"^aiphoria-ai$",
    ]
]


def _is_bot(name: str) -> bool:
    return any(p.search(name) for p in BOT_PATTERNS)


def _filter_humans(authors) -> list[str]:
    return [a for a in authors if not _is_bot(a)]


def create_app() -> FastAPI:
    app = FastAPI(title="Release Manager")

    app.mount(
        "/static",
        StaticFiles(directory=PACKAGE_DIR / "static"),
        name="static",
    )

    templates = Jinja2Templates(directory=PACKAGE_DIR / "templates")
    templates.env.filters["filter_humans"] = _filter_humans
    templates.env.tests["bot"] = _is_bot
    app.state.templates = templates
    app.state.last_report = None
    app.state.releases = remote.load_releases(settings.repos_dir)
    app.state.deploy_snapshots = remote.load_snapshots(settings.repos_dir)
    config = remote.load_config(settings.repos_dir)
    # Override credentials from env vars if set
    if settings.git_token:
        config.git_token = settings.git_token
    if settings.git_username:
        config.git_username = settings.git_username
    if settings.linear_api_key:
        config.linear_api_key = settings.linear_api_key
    app.state.app_config = config

    app.include_router(router)

    return app
