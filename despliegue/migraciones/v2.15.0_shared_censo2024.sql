-- ============================================================================
-- SINAGERSAT - Migración v2.15.0 (idempotente)
-- Censo 2024 en esquema `shared`: tablas `manzanos` y `comunidades`.
--   * Una fila por unidad censal mínima (manzano / comunidad) del CPV-2024.
--   * `personas` = población censada; `viviendas` = viviendas particulares.
--   * `area`/`tipo_unidad` = clasificación cartográfica; `area_oficial` = oficial INE (Urbana/Rural/Mixto).
--   * `id_municipio` FK -> shared.municipio (única relación; no altera el resto del esquema).
--   * `geom` en EPSG:4326 (MULTIPOLYGON manzanos / POINT comunidades), se llena desde el GPKG.
-- ============================================================================

BEGIN;

-- ── MANZANOS ────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS shared.manzanos (
    codigo              text PRIMARY KEY,
    nombre              text NOT NULL,
    tipo_unidad         text NOT NULL DEFAULT 'Manzano' CHECK (tipo_unidad = 'Manzano'),
    area                smallint NOT NULL DEFAULT 1,
    personas            integer NOT NULL DEFAULT 0,
    viviendas           integer NOT NULL DEFAULT 0,
    ficha               boolean NOT NULL DEFAULT false,
    idep                smallint,
    iprov               smallint,
    imun                smallint,
    codigo_departamento smallint,
    codigo_provincia    integer,
    codigo_municipio    integer NOT NULL,
    nombre_dep          text,
    nombre_prov         text,
    nombre_mun          text,
    lat                 numeric(10,7),
    lon                 numeric(10,7),
    area_oficial        text CHECK (area_oficial IN ('Urbana', 'Rural', 'Mixto')),
    id_municipio        integer NOT NULL REFERENCES shared.municipio(id),
    geom                geometry(MultiPolygon, 4326)
);

COMMENT ON TABLE shared.manzanos IS 'Manzanos censales CPV-2024 (INE). personas = población censada, viviendas = viviendas particulares.';  

CREATE INDEX IF NOT EXISTS idx_manzanos_id_municipio   ON shared.manzanos (id_municipio);
CREATE INDEX IF NOT EXISTS idx_manzanos_nombre          ON shared.manzanos (nombre);
CREATE INDEX IF NOT EXISTS idx_manzanos_area_oficial    ON shared.manzanos (area_oficial);
CREATE INDEX IF NOT EXISTS idx_manzanos_codigo_municipio ON shared.manzanos (codigo_municipio);
CREATE INDEX IF NOT EXISTS idx_manzanos_geom            ON shared.manzanos USING gist (geom);

-- ── COMUNIDADES ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS shared.comunidades (
    codigo              text PRIMARY KEY,
    nombre              text NOT NULL,
    tipo_unidad         text NOT NULL DEFAULT 'Comunidad' CHECK (tipo_unidad = 'Comunidad'),
    area                smallint NOT NULL DEFAULT 2,
    personas            integer NOT NULL DEFAULT 0,
    viviendas           integer NOT NULL DEFAULT 0,
    ficha               boolean NOT NULL DEFAULT false,
    idep                smallint,
    iprov               smallint,
    imun                smallint,
    codigo_departamento smallint,
    codigo_provincia    integer,
    codigo_municipio    integer NOT NULL,
    nombre_dep          text,
    nombre_prov         text,
    nombre_mun          text,
    lat                 numeric(10,7),
    lon                 numeric(10,7),
    area_oficial        text CHECK (area_oficial IN ('Urbana', 'Rural', 'Mixto')),
    id_municipio        integer NOT NULL REFERENCES shared.municipio(id),
    geom                geometry(Point, 4326)
);

COMMENT ON TABLE shared.comunidades IS 'Comunidades censales CPV-2024 (INE). personas = población censada, viviendas = viviendas particulares.';

CREATE INDEX IF NOT EXISTS idx_comunidades_id_municipio   ON shared.comunidades (id_municipio);
CREATE INDEX IF NOT EXISTS idx_comunidades_nombre         ON shared.comunidades (nombre);
CREATE INDEX IF NOT EXISTS idx_comunidades_area_oficial   ON shared.comunidades (area_oficial);
CREATE INDEX IF NOT EXISTS idx_comunidades_codigo_municipio ON shared.comunidades (codigo_municipio);
CREATE INDEX IF NOT EXISTS idx_comunidades_geom           ON shared.comunidades USING gist (geom);

COMMIT;

SELECT 'IDEMPOTENT OK v2.15.0 shared_censo2024' AS resultado;