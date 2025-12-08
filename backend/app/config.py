from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    cloudru_api_url: str = "https://llm.api.cloud.ru"
    cloudru_api_token: str

    gitlab_url: str | None = None
    gitlab_token: str | None = None

    app_env: str = "dev"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
