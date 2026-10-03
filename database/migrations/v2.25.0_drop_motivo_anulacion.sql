-- ============================================================================
-- SINAGERSAT - Migración v2.25.0 (idempotente)
-- RIDA: eliminar columna motivo_anulacion de rida.evento_rida
--
-- El parámetro "motivo de la anulación" se retira de la tabla y de la API
-- (POST /evento/{id}/anular ya no requiere ?motivo=...).
-- Conserva: anulado, id_usuario_anulo, fecha_anulacion.
--
-- Verificación previa: 0 filas con motivo_anulacion IS NOT NULL (sin pérdida).
-- ============================================================================

BEGIN;

ALTER TABLE rida.evento_rida DROP COLUMN IF EXISTS motivo_anulacion;

COMMIT;

SELECT 'IDEMPOTENT OK v2.25.0 drop_motivo_anulacion' AS resultado;
