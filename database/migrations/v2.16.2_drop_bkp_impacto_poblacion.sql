-- ============================================================================
-- SINAGERSAT - Migración v2.16.2 (idempotente)
-- Elimina el respaldo puntual `edan.bkp_impacto_poblacion_20260830`
-- (snapshot previo del impacto en poblacion, previo a la importacion legacy).
-- No tiene FKs de entrada ni salida y no es referenciada por ningun codigo;
-- los datos definitivos estan en edan.edan_localidades_impacto_poblacion.
-- Se conserva edan.edan_importacion_log (traza de procedencia de los EDAN).
-- ============================================================================

BEGIN;

DROP TABLE IF EXISTS edan.bkp_impacto_poblacion_20260830;

COMMIT;

SELECT 'IDEMPOTENT OK v2.16.2 drop_bkp_impacto_poblacion' AS resultado;