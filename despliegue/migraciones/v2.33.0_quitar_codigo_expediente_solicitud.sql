-- ============================================================================
-- SINAGERSAT - Migración v2.33.0 (idempotente)
-- RIDA: eliminar columna codigo_expediente de rida.solicitud
--
-- El campo codigo_expediente se retira de la tabla y de las APIs de solicitudes.
-- Migración segura: la tabla tiene 0 filas.
-- ============================================================================

BEGIN;

ALTER TABLE rida.solicitud DROP COLUMN IF EXISTS codigo_expediente;

COMMIT;

SELECT 'IDEMPOTENT OK v2.33.0 quitar_codigo_expediente_solicitud' AS resultado;
