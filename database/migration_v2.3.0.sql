-- ============================================================================
-- SINAGERSAT - Migración v2.3.0 (idempotente)
-- edan.edan_localidades_proteccion: ajuste posterior a v2.2.0.
--   - Elimina la columna `necesidad` (no corresponde a una columna del
--     formulario 10.1).
--   - Agrega la columna `total` (N° total de personas del grupo vulnerable).
--     El frontend la calcula sumando hombres + mujeres y la envía.
-- Aplica sobre migration_v2.2.0.
-- ============================================================================

BEGIN;

-- 1. Eliminar la columna `necesidad`
ALTER TABLE edan.edan_localidades_proteccion DROP COLUMN IF EXISTS necesidad;

-- 2. Nueva columna `total`
ALTER TABLE edan.edan_localidades_proteccion
    ADD COLUMN IF NOT EXISTS total integer NOT NULL DEFAULT 0;

-- 3. Backfill: total = hombres + mujeres para los registros existentes
UPDATE edan.edan_localidades_proteccion
SET total = hombres + mujeres;

COMMIT;

SELECT 'IDEMPOTENT OK v2.3.0' AS resultado;
