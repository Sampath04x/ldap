from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://fwident:fwident_dev@localhost:5432/fwident"
    sync_database_url: str = "postgresql+psycopg://fwident:fwident_dev@localhost:5432/fwident"
    provider: str = "mock"
    api_key: str = ""  # empty = no auth required
    cors_origins: str = "http://localhost:3000"
    
    # Diagnostic thresholds (configurable)
    ip_mapping_stale_hours: int = 8
    group_mapping_stale_hours: int = 24
    auth_failure_window_hours: int = 24
    auth_failure_threshold: int = 3

    model_config = {"env_file": ".env", "extra": "ignore"}
    
    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

@lru_cache
def get_settings() -> Settings:
    return Settings()
