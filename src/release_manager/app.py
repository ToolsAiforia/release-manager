from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from release_manager.api.routes import router

PACKAGE_DIR = Path(__file__).parent


def create_app() -> FastAPI:
    app = FastAPI(title="Release Manager")

    app.mount(
        "/static",
        StaticFiles(directory=PACKAGE_DIR / "static"),
        name="static",
    )

    templates = Jinja2Templates(directory=PACKAGE_DIR / "templates")
    app.state.templates = templates
    app.state.last_report = None

    app.include_router(router)

    return app
