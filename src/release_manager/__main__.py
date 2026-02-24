import uvicorn

from release_manager.settings import settings

uvicorn.run(
    "release_manager.app:create_app",
    factory=True,
    host=settings.host,
    port=settings.port,
    reload=True,
)
