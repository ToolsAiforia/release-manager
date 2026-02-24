from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    host: str = "127.0.0.1"
    port: int = 8000
    default_root_dir: str = "/Users/malinovskaia/Work/"

    model_config = {"env_prefix": "RM_"}


settings = Settings()
