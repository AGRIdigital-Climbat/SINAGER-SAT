-- ============================================================================
-- SINAGERSAT API v2.31.1 (REVERTIR)
-- Eliminar campos offline agregados por error
-- ============================================================================

BEGIN;

ALTER TABLE sinb.grupo DROP COLUMN IF EXISTS id_grupo_off;
ALTER TABLE sinb.indicador_natural DROP COLUMN IF EXISTS id_indicador_off;
ALTER TABLE sinb.caracteristica DROP COLUMN IF EXISTS id_caracteristica_off;
ALTER TABLE sinb.comportamiento DROP COLUMN IF EXISTS id_comportamiento_off;
ALTER TABLE sinb.significado DROP COLUMN IF EXISTS id_significado_off;
ALTER TABLE sinb.zona_geografica DROP COLUMN IF EXISTS id_zona_off;
ALTER TABLE sinb.categoria_pronostico DROP COLUMN IF EXISTS id_categoria_off;
ALTER TABLE sinb.escenario DROP COLUMN IF EXISTS id_escenario_off;

COMMIT;
