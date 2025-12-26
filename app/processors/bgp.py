"""Processing pipeline for BGP announcements and prefix expansion."""
from __future__ import annotations

import ipaddress
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable

from sqlalchemy import text

from app.bootstrap import ensure_snapshot
from app.db import db_session


@dataclass
class ParsedBGPEntity:
    """Normalized BGP announcement structure."""

    prefix: str
    as_path: str
    origin_asn: int
    source_code: str
    source_type: str


@dataclass
class ExpandedPrefix:
    """Expanded prefix used for analysis and geolocation."""

    prefix: str
    origin_asn: int
    source_code: str


def _load_raw(path: Path) -> list[ParsedBGPEntity]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    entities: list[ParsedBGPEntity] = []
    for entry in payload:
        entities.append(
            ParsedBGPEntity(
                prefix=entry["prefix"],
                as_path=entry["as_path"],
                origin_asn=int(entry["origin_asn"]),
                source_code=entry.get("source_code", "unknown"),
                source_type=entry.get("source_type", "ixp"),
            )
        )
    return entities


def _expand_ipv4(prefix: ipaddress.IPv4Network, origin_asn: int, source_code: str) -> list[ExpandedPrefix]:
    expanded: list[ExpandedPrefix] = []
    for subnet in prefix.subnets(new_prefix=24):
        expanded.append(ExpandedPrefix(prefix=str(subnet), origin_asn=origin_asn, source_code=source_code))
    return expanded


def _expand_ipv6(prefix: ipaddress.IPv6Network, origin_asn: int, source_code: str) -> list[ExpandedPrefix]:
    """Expand IPv6 prefixes until /48 to emulate geographic disambiguation."""
    if prefix.prefixlen >= 48:
        return [ExpandedPrefix(prefix=str(prefix), origin_asn=origin_asn, source_code=source_code)]

    expanded: list[ExpandedPrefix] = []
    for candidate in prefix.subnets(new_prefix=48):
        expanded.append(ExpandedPrefix(prefix=str(candidate), origin_asn=origin_asn, source_code=source_code))
    return expanded


def _expand_prefix(record: ParsedBGPEntity) -> list[ExpandedPrefix]:
    network = ipaddress.ip_network(record.prefix, strict=False)
    if isinstance(network, ipaddress.IPv4Network):
        return _expand_ipv4(network, record.origin_asn, record.source_code)
    return _expand_ipv6(network, record.origin_asn, record.source_code)


def _get_or_create_source(conn, snapshot_id: int, code: str, source_type: str) -> int:
    existing = conn.execute(
        text(
            """
            SELECT source_id FROM source
            WHERE snapshot_id = :snapshot_id AND source_code = :source_code
            LIMIT 1
            """
        ),
        {"snapshot_id": snapshot_id, "source_code": code},
    ).scalar()
    if existing is not None:
        return int(existing)

    created = conn.execute(
        text(
            """
            INSERT INTO source (snapshot_id, source_code, source_type)
            VALUES (:snapshot_id, :source_code, :source_type)
            RETURNING source_id
            """
        ),
        {"snapshot_id": snapshot_id, "source_code": code, "source_type": source_type},
    ).scalar_one()
    return int(created)


def process_bgp(raw_files: Iterable[Path], snapshot_date: date) -> None:
    """Parse raw BGP files, insert original prefixes, and populate expansions."""
    snapshot_id = ensure_snapshot(snapshot_date.isoformat(), description="BGP ingest")

    for raw in raw_files:
        records = _load_raw(raw)
        if not records:
            continue

        with db_session() as conn:
            source_ids: dict[str, int] = {}

            for record in records:
                source_ids.setdefault(
                    record.source_code,
                    _get_or_create_source(conn, snapshot_id, record.source_code, record.source_type),
                )
                source_id = source_ids[record.source_code]

                conn.execute(
                    text(
                        """
                        INSERT INTO asn (snapshot_id, asn)
                        VALUES (:snapshot_id, :asn)
                        ON CONFLICT DO NOTHING
                        """
                    ),
                    {"snapshot_id": snapshot_id, "asn": record.origin_asn},
                )

                conn.execute(
                    text(
                        """
                        INSERT INTO prefix (snapshot_id, prefix, ip_version, source_id, as_path)
                        VALUES (:snapshot_id, :prefix, :ip_version, :source_id, :as_path)
                        ON CONFLICT DO NOTHING
                        """
                    ),
                    {
                        "snapshot_id": snapshot_id,
                        "prefix": record.prefix,
                        "ip_version": 4 if ":" not in record.prefix else 6,
                        "source_id": source_id,
                        "as_path": record.as_path,
                    },
                )

                conn.execute(
                    text(
                        """
                        INSERT INTO prefix_asn (snapshot_id, prefix, source_id, asn, relation_type)
                        VALUES (:snapshot_id, :prefix, :source_id, :asn, 'origin')
                        ON CONFLICT DO NOTHING
                        """
                    ),
                    {
                        "snapshot_id": snapshot_id,
                        "prefix": record.prefix,
                        "source_id": source_id,
                        "asn": record.origin_asn,
                    },
                )

                for expanded in _expand_prefix(record):
                    conn.execute(
                        text(
                            """
                            INSERT INTO prefix_expanded (snapshot_id, prefix_exp, ip_version, origin_asn)
                            VALUES (:snapshot_id, :prefix_exp, :ip_version, :origin_asn)
                            ON CONFLICT DO NOTHING
                            """
                        ),
                        {
                            "snapshot_id": snapshot_id,
                            "prefix_exp": expanded.prefix,
                            "ip_version": 4 if ":" not in expanded.prefix else 6,
                            "origin_asn": expanded.origin_asn,
                        },
                    )

                    conn.execute(
                        text(
                            """
                            INSERT INTO prefix_expanded_map (snapshot_id, prefix_exp, prefix_orig, source_id)
                            VALUES (:snapshot_id, :prefix_exp, :prefix_orig, :source_id)
                            ON CONFLICT DO NOTHING
                            """
                        ),
                        {
                            "snapshot_id": snapshot_id,
                            "prefix_exp": expanded.prefix,
                            "prefix_orig": record.prefix,
                            "source_id": source_id,
                        },
                    )
