from pydantic import RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    redis_url: RedisDsn = RedisDsn(url="redis://localhost:6379/0")
    # How long a task's owner and billing marker are kept. Matches Celery's
    # default result_expires, so they last as long as the result.
    task_ttl_s: int = 86_400
    stream_timeout_s: float = 300

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
