# snapshot-bgp-brasil

First functional prototype of the BGP snapshot pipeline described in `instrucoes.txt`. The stack is dockerized and ships with a simple Python CLI that collects demonstrative BGP data, expands prefixes, and populates the provided schema.

## Components
- **PostgreSQL + PostGIS** – persistence layer using the schema in `modelo.sql`.
- **pgAdmin** – optional administrative UI.
- **Python 3.12 container** – runs the CLI and pipeline.

## Setup
1. Copy `.env.example` to `.env` and adjust credentials/ports if needed.
2. Build and start the stack:
   ```bash
   docker-compose up -d --build
   ```
3. Initialize the database schema and run the pipeline for today:
   ```bash
   docker-compose run --rm app python main.py --init-db
   docker-compose run --rm app python main.py --snapshot-date 2025-09-01 --bgp-sources ixp_df,global
   ```

Raw data is persisted under `data/raw/<date>/` and processed inserts are written into the database tables defined in `modelo.sql`. The `--load-registrobr` flag is present for future expansion; it is a no-op in this prototype.
