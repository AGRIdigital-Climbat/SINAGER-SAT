-- ============================================================================
-- v2.39.0 Quitar confianza del observador de pronóstico largo
-- ============================================================================
-- La confianza ALTA | MEDIA | BAJA pertenece al ESCENARIO del bloque
-- (sinb.escenario_estacional.confianza) o al pronóstico corto como tal
-- (sinb.pronostico_corto.confianza), nunca al observador.
--
-- En sinb.pronostico_largo_observador la columna estaba casi sin uso:
-- 225 filas, solo 1 con valor no nulo (se elimina junto con la columna).
--
-- NO se toca sinb.pronostico_corto_observador.confianza (7 filas, 7 con valor).
-- ============================================================================

BEGIN;

ALTER TABLE sinb.pronostico_largo_observador
    DROP COLUMN IF EXISTS confianza;

COMMIT;

-- Verificación
-- \d sinb.pronostico_largo_observador    -- sin confianza
-- SELECT count(*) FROM information_schema.columns
--  WHERE table_schema='sinb' AND table_name='pronostico_largo_observador'
--    AND column_name='confianza';          -- 0
-- SELECT count(*) FROM information_schema.columns
--  WHERE table_schema='sinb' AND table_name='pronostico_corto_observador'
--    AND column_name='confianza';          -- 1 (sin cambios)
