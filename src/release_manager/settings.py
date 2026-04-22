from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    host: str = "127.0.0.1"
    port: int = 8000
    default_root_dir: str = str(Path.home() / "Work")
    repos_dir: str = "~/.release-manager/repos"
    git_username: str = ""
    git_token: str = ""
    linear_api_key: str = ""

    model_config = {"env_prefix": "RM_", "env_file": ".env"}


settings = Settings()
