"""Runtime settings, read from environment variables or backend/.env."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env", env_prefix="PARALLAX_", extra="ignore"
    )

    # PARALLAX_DATABASE_URL wins; on nexus the bound store injects DATABASE_URL (postgresql://...).
    database_url: str = Field(default="postgresql+psycopg://parallax@localhost:5433/parallax",
                              validation_alias=AliasChoices("PARALLAX_DATABASE_URL", "DATABASE_URL"))
    # Inbound bearer token. nexus injects PARALLAX_API_API_TOKEN for the app slug "parallax-api".
    # When set, every /api route except /api/health requires `Authorization: Bearer <token>`.
    api_token: str | None = Field(default=None, validation_alias=AliasChoices("PARALLAX_API_TOKEN", "PARALLAX_API_API_TOKEN"))
    # Optional second credential for the CLI (push-research, smoke). Minted by nexus (generate) as
    # PARALLAX_CLI_TOKEN; the operator copies it from the nexus UI into backend/.env as PARALLAX_REMOTE_TOKEN.
    cli_token: str | None = None

    # "mock" runs the whole pipeline offline with deterministic fake outputs.
    llm_mode: Literal["openai", "mock"] = "mock"
    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")

    # Model roles. Confirm names with `python -m parallax.cli models` once the key is set.
    model_fast: str = "gpt-5-mini"  # personas, departments, extraction, research
    model_strong: str = "gpt-5"  # verifier, synthesis, drafting
    # One judge: validation showed a 3-judge panel always voted alike; the value is in the stated drivers.
    judge_models: list[str] = ["gpt-5"]
    embedding_model: str = "text-embedding-3-small"

    # Market-twin engine: TinyTroupe simulates personas in a TinyWorld; "direct" uses plain
    # structured LLM calls with the same persona prompt (fallback if TinyTroupe misbehaves).
    persona_engine: Literal["tinytroupe", "direct"] = "tinytroupe"

    # Research contract locations (the research branch layout).
    research_root: Path = REPO_ROOT / "research"

    target_model: str = "bmw:G60"
    markets: list[str] = ["US", "EU", "CN"]

    max_parallel_cases: int = 5
    max_llm_calls_per_run: int = 600
    max_research_requests_per_case: int = 2
    grounding_quotes_per_persona: int = 25

    # Only sources that are accepted AND have export_permissions.external_llm == true may reach
    # an external LLM. Setting this to true is for synthetic/demo data only and is audited.
    allow_unreviewed_evidence_for_llm: bool = False

    var_dir: Path = BACKEND_ROOT / "var"

    # Client side (CLI talking to a deployed backend): keep the token in backend/.env, never in chat or git.
    remote_url: str = "https://parallax.dehlwes.net"
    remote_token: str | None = None

    @field_validator("database_url")
    @classmethod
    def _psycopg_driver(cls, value: str) -> str:
        for prefix in ("postgresql://", "postgres://"):
            if value.startswith(prefix):
                return "postgresql+psycopg://" + value[len(prefix):]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
