"""Configuration loader for the BGP snapshot pipeline."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


@dataclass
class Settings:
    """Runtime settings loaded from environment variables."""

    database_url: str = os.environ.get("DATABASE_URL", "postgresql+psycopg2://bgp_user:bgp_password@localhost:5432/bgp")
    raw_data_dir: Path = Path(os.environ.get("RAW_DATA_DIR", "data/raw"))
    processed_data_dir: Path = Path(os.environ.get("PROCESSED_DATA_DIR", "data/processed"))
    schema_file: Path = Path(os.environ.get("SCHEMA_FILE", "modelo.sql"))

    def ensure_directories(self) -> None:
        """Create necessary local directories for data persistence."""
        self.raw_data_dir.mkdir(parents=True, exist_ok=True)
        self.processed_data_dir.mkdir(parents=True, exist_ok=True)


def get_settings() -> Settings:
    """Return a singleton-style settings instance."""
    settings = Settings()
    settings.ensure_directories()
    return settings
