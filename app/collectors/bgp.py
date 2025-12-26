"""Lightweight BGP collectors used for demonstration and testing."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable

from app.config import get_settings


@dataclass
class BGPSample:
    """Small representation of a BGP announcement for demonstration."""

    prefix: str
    as_path: str
    origin_asn: int
    source_code: str
    source_type: str = "ixp"


SAMPLE_DATA = [
    BGPSample(prefix="200.160.0.0/16", as_path="65001 65002 65003", origin_asn=65003, source_code="ixp_df"),
    BGPSample(prefix="187.16.0.0/20", as_path="65010 65020", origin_asn=65020, source_code="global"),
    BGPSample(prefix="2804:10::/32", as_path="64512 64513", origin_asn=64513, source_code="ixp_sp", source_type="global"),
]


def build_raw_path(snapshot_date: date, source: str) -> Path:
    settings = get_settings()
    return settings.raw_data_dir / snapshot_date.isoformat() / f"bgp_{source}.json"


def collect_bgp(snapshot_date: date, sources: Iterable[str], force: bool = False) -> list[Path]:
    """Persist sample BGP data per source. Acts as an idempotent collector."""
    settings = get_settings()
    written: list[Path] = []
    for source in sources:
        raw_path = build_raw_path(snapshot_date, source)
        if raw_path.exists() and not force:
            written.append(raw_path)
            continue

        raw_path.parent.mkdir(parents=True, exist_ok=True)
        payload = [sample.__dict__ for sample in SAMPLE_DATA if sample.source_code == source or source == "all"]
        if not payload:
            payload = [sample.__dict__ for sample in SAMPLE_DATA]
        raw_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        written.append(raw_path)
    return written
