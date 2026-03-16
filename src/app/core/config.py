import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_name: str
    database_url: str


def _load_env(dotenv_path: Path) -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(dotenv_path)
        return
    except ModuleNotFoundError:
        pass

    if not dotenv_path.exists():
        return

    for line in dotenv_path.read_text().splitlines():
        entry = line.strip()
        if not entry or entry.startswith("#") or "=" not in entry:
            continue
        key, value = entry.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'").strip('"'))


@lru_cache
def get_settings() -> Settings:
    project_root = Path(__file__).resolve().parents[3]
    _load_env(project_root / ".env")

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required. Set it in .env or environment variables.")

    app_name = os.getenv("APP_NAME", "FastAPI PostgreSQL App")
    return Settings(app_name=app_name, database_url=database_url)
