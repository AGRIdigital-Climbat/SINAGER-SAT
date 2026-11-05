-- ============================================================================
-- SINAGERSAT - Migración v1.5.0 (idempotente)
-- Restaura la funcionalidad geoespacial perdida:
--   1. Crea la extensión PostGIS (paquete postgresql-16-postgis-3 instalado).
--   2. Agrega la columna geom (MultiPolygon, SRID 4326) a shared.municipio.
--   3. Crea el índice GiST para búsquedas espaciales.
-- La carga de datos de geom se hace por separado con database/restaurar_geom.sh
-- (extrae el bloque COPY de backup_v1.2.8.sql para NO tocar otras tablas).
-- Aplica sobre migration_v1.4.3.
-- ============================================================================

BEGIN;

-- ── 0. Schema public (PostGIS se instala ahí) ──
CREATE SCHEMA IF NOT EXISTS public;
ALTER SCHEMA public OWNER TO pg_database_owner;

-- ── 1. Extensión PostGIS ──
CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA public;

-- ── 2. Columna geom en shared.municipio ──
ALTER TABLE shared.municipio ADD COLUMN IF NOT EXISTS geom geometry(MultiPolygon, 4326);

-- ── 3. Índice espacial ──
CREATE INDEX IF NOT EXISTS idx_municipio_geom ON shared.municipio USING gist (geom);

COMMIT;

SELECT 'IDEMPOTENT OK v1.5.0' AS resultado;
