-- ============================================================================
-- SINAGERSAT API v2.31.2
-- Revertir columnas _off en catálogos (agregadas sin planificar)
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

DROP INDEX IF EXISTS sinb.idx_grupo_off;
DROP INDEX IF EXISTS sinb.idx_indicador_off;
DROP INDEX IF EXISTS sinb.idx_caracteristica_off;
DROP INDEX IF EXISTS sinb.idx_comportamiento_off;
DROP INDEX IF EXISTS sinb.idx_significado_off;
DROP INDEX IF EXISTS sinb.idx_zona_off;
DROP INDEX IF EXISTS sinb.idx_categoria_off;
DROP INDEX IF EXISTS sinb.idx_escenario_off;

COMMIT;
