-- ============================================================================
-- SINAGERSAT - Migración v2.36.0 (idempotente)
-- RIDA: hacer opcionales id_articulo y cantidad en rida.necesidad
--
-- - cantidad puede quedar NULL cuando no se registra
-- - se elimina el default 0
-- ============================================================================

BEGIN;

ALTER TABLE rida.necesidad
    ALTER COLUMN cantidad DROP DEFAULT;

ALTER TABLE rida.necesidad
    ALTER COLUMN cantidad DROP NOT NULL;

ALTER TABLE rida.necesidad
    DROP CONSTRAINT IF EXISTS necesidad_cantidad_check;

ALTER TABLE rida.necesidad
    ADD CONSTRAINT necesidad_cantidad_check
    CHECK (cantidad IS NULL OR cantidad >= 0);

COMMIT;

SELECT 'IDEMPOTENT OK v2.36.0 necesidad_articulo_cantidad_opcional' AS resultado;
