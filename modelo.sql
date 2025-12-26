-- =========================================================
-- EXTENSÕES
-- =========================================================

CREATE EXTENSION IF NOT EXISTS postgis;

-- =========================================================
-- SNAPSHOT
-- =========================================================

CREATE TABLE snapshot (
  snapshot_id     BIGSERIAL PRIMARY KEY,
  collected_at    TIMESTAMP NOT NULL,
  logical_date    DATE,
  description     TEXT
);

-- =========================================================
-- SOURCE (IXPs e Tabelas Globais)
-- =========================================================

CREATE TABLE source (
  snapshot_id     BIGINT NOT NULL REFERENCES snapshot(snapshot_id),
  source_id       SERIAL,
  source_code     TEXT NOT NULL,
  source_type     TEXT NOT NULL,       -- ixp | global
  country_code    CHAR(2),
  location        GEOGRAPHY(POINT, 4326),
  lg_address      TEXT,
  lg_type         TEXT,                -- telnet | ris | routeviews | alice
  PRIMARY KEY (snapshot_id, source_id)
);

CREATE INDEX source_snapshot_idx ON source (snapshot_id);
CREATE INDEX source_location_idx ON source USING GIST (location);

-- =========================================================
-- ASN (somente ASNs vistos no snapshot)
-- =========================================================

CREATE TABLE asn (
  snapshot_id     BIGINT NOT NULL REFERENCES snapshot(snapshot_id),
  asn             INTEGER NOT NULL,
  asn_name        TEXT,
  country_code    CHAR(2),
  cnpj            TEXT,
  PRIMARY KEY (snapshot_id, asn)
);

CREATE INDEX asn_snapshot_idx ON asn (snapshot_id);

-- =========================================================
-- PREFIXOS ORIGINAIS (como vistos no BGP)
-- =========================================================

CREATE TABLE prefix (
  snapshot_id     BIGINT NOT NULL REFERENCES snapshot(snapshot_id),
  prefix          CIDR NOT NULL,
  ip_version      SMALLINT NOT NULL,    -- 4 ou 6
  source_id       INTEGER NOT NULL,
  as_path         TEXT NOT NULL,
  PRIMARY KEY (snapshot_id, prefix, source_id, as_path)
);

CREATE INDEX prefix_snapshot_idx ON prefix (snapshot_id);
CREATE INDEX prefix_source_idx ON prefix (snapshot_id, source_id);
CREATE INDEX prefix_cidr_idx ON prefix USING GIST (prefix);

-- =========================================================
-- RELAÇÃO PREFIXO ORIGINAL ↔ ASN (TIPADA)
-- =========================================================

CREATE TABLE prefix_asn (
  snapshot_id     BIGINT NOT NULL REFERENCES snapshot(snapshot_id),
  prefix          CIDR NOT NULL,
  source_id       INTEGER NOT NULL,
  asn             INTEGER NOT NULL,
  relation_type   TEXT NOT NULL,   -- origin | announce
  PRIMARY KEY (snapshot_id, prefix, source_id, asn, relation_type)
);

CREATE INDEX prefix_asn_snapshot_idx ON prefix_asn (snapshot_id);
CREATE INDEX prefix_asn_asn_idx ON prefix_asn (snapshot_id, asn);

-- =========================================================
-- PREFIXOS EXPANDIDOS (UNIDADE DE ANÁLISE E GEO)
-- =========================================================

CREATE TABLE prefix_expanded (
  snapshot_id     BIGINT NOT NULL REFERENCES snapshot(snapshot_id),
  prefix_exp      CIDR NOT NULL,
  ip_version      SMALLINT NOT NULL,    -- 4 ou 6
  origin_asn      INTEGER NOT NULL,
  country_code    CHAR(2),
  location        GEOGRAPHY(POINT, 4326),
  geo_source      TEXT,                 -- maxmind | ipinfo | etc
  PRIMARY KEY (snapshot_id, prefix_exp, origin_asn)
);

CREATE INDEX prefix_exp_snapshot_idx ON prefix_expanded (snapshot_id);
CREATE INDEX prefix_exp_asn_idx ON prefix_expanded (snapshot_id, origin_asn);
CREATE INDEX prefix_exp_geo_idx ON prefix_expanded USING GIST (location);

-- =========================================================
-- RELAÇÃO PREFIXO EXPANDIDO ↔ PREFIXO ORIGINAL
-- =========================================================

CREATE TABLE prefix_expanded_map (
  snapshot_id     BIGINT NOT NULL REFERENCES snapshot(snapshot_id),
  prefix_exp      CIDR NOT NULL,
  prefix_orig     CIDR NOT NULL,
  source_id       INTEGER NOT NULL,
  PRIMARY KEY (snapshot_id, prefix_exp, prefix_orig, source_id)
);

CREATE INDEX prefix_exp_map_snapshot_idx ON prefix_expanded_map (snapshot_id);
CREATE INDEX prefix_exp_map_orig_idx ON prefix_expanded_map (snapshot_id, prefix_orig);

-- =========================================================
-- RELAÇÃO ASN ↔ SOURCE (ÚNICA, COM RELAÇÕES REPETÍVEIS)
-- =========================================================

CREATE TABLE asn_source (
  snapshot_id     BIGINT NOT NULL REFERENCES snapshot(snapshot_id),
  asn             INTEGER NOT NULL,
  source_id       INTEGER NOT NULL,
  relation_type   TEXT NOT NULL,   -- origin | peer
  PRIMARY KEY (snapshot_id, asn, source_id, relation_type)
);

CREATE INDEX asn_source_snapshot_idx ON asn_source (snapshot_id);
CREATE INDEX asn_source_asn_idx ON asn_source (snapshot_id, asn);
CREATE INDEX asn_source_source_idx ON asn_source (snapshot_id, source_id);

-- =========================================================
-- (OPCIONAL) CHECKS SIMPLES PARA EVITAR ERROS GROSSEIROS
-- =========================================================

ALTER TABLE prefix_asn
  ADD CONSTRAINT prefix_asn_relation_chk
  CHECK (relation_type IN ('origin', 'announce'));

ALTER TABLE asn_source
  ADD CONSTRAINT asn_source_relation_chk
  CHECK (relation_type IN ('origin', 'peer'));

ALTER TABLE source
  ADD CONSTRAINT source_type_chk
  CHECK (source_type IN ('ixp', 'global'));

ALTER TABLE prefix_expanded
  ADD CONSTRAINT prefix_exp_ipver_chk
  CHECK (ip_version IN (4, 6));

