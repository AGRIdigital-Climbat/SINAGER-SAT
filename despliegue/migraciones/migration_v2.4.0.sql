-- ============================================================================
-- SINAGERSAT - Migración v2.4.0 (idempotente)
-- edan.edan_localidades_salud_necesidades: elimina la columna `botiquines`
-- (no corresponde a una sección del formulario EDAN).
-- Aplica sobre migration_v2.3.0.
-- NOTA: la API (api/edan/service.py) todavía referencia `botiquines`;
-- se adaptará en una etapa posterior.
-- ============================================================================

BEGIN;

ALTER TABLE edan.edan_localidades_salud_necesidades DROP COLUMN IF EXISTS botiquines;

COMMIT;

SELECT 'IDEMPOTENT OK v2.4.0' AS resultado;
