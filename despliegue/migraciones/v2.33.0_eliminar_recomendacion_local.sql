-- ============================================================================
-- v2.33.0 Eliminar recomendacion_local y categoria_recomendacion
-- ============================================================================
-- Las recomendaciones ahora solo entran por POST /pronostico-largo.
-- Estas tablas y sus endpoints se eliminan por estar obsoletos.
-- ============================================================================

BEGIN;

-- 1. Eliminar FK saliente de recomendacion_local
ALTER TABLE sinb.recomendacion_local 
    DROP CONSTRAINT IF EXISTS recomendacion_local_id_categoria_fkey;

-- 2. Eliminar tabla principal (104 filas)
DROP TABLE IF EXISTS sinb.recomendacion_local;

-- 3. Eliminar catálogo categoria_recomendacion (8 filas, solo usado por recomendacion_local)
DROP TABLE IF EXISTS sinb.categoria_recomendacion;

COMMIT;

-- Verificación
-- SELECT COUNT(*) FROM sinb.recomendacion_local;  -- debe fallar
-- SELECT COUNT(*) FROM sinb.categoria_recomendacion;  -- debe fallar
