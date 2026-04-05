from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    pubmed_base_url: str = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    log_level: str = "INFO"
    openai_api_key: str | None = None
    uvicorn_workers: int = 1  # read by entrypoint.sh; each worker opens its own DB pool

    model_config = {"env_file": ".env", "frozen": True, "extra": "ignore"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
