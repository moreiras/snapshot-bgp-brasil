"""Entrypoint for the snapshot pipeline CLI."""
from __future__ import annotations

import argparse
from datetime import date

from app.bootstrap import initialize_database
from app.collectors.bgp import collect_bgp
from app.processors.bgp import process_bgp


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Snapshot BGP Brasil pipeline")
    parser.add_argument("--snapshot-date", type=lambda d: date.fromisoformat(d), default=date.today(), help="Logical date for the snapshot")
    parser.add_argument("--bgp-sources", default="ixp_df,global", help="Comma-separated list of BGP sources to collect")
    parser.add_argument("--load-registrobr", action="store_true", help="Placeholder flag for Registro.br loader")
    parser.add_argument("--init-db", action="store_true", help="Apply schema before running the pipeline")
    parser.add_argument("--force-download", action="store_true", help="Overwrite already collected raw data for the given date")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.init_db:
        initialize_database()

    sources = [source.strip() for source in args.bgp_sources.split(",") if source.strip()]
    raw_files = collect_bgp(args.snapshot_date, sources, force=args.force_download)
    process_bgp(raw_files, args.snapshot_date)

    if args.load_registrobr:
        print("Registro.br loader not implemented in v1, flag retained for CLI compatibility.")


if __name__ == "__main__":
    main()
