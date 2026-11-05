-- ============================================================================
-- SINAGERSAT - Migración v2.17.2 (idempotente)
-- Aprobaciones EDAN: se elimina la columna 'ordinal'.
--
--   El orden de la cadena ugr -> alcalde -> dgr -> videcid lo define el código
--   (constante NIVELES_APROBACION en api/edan/service.py). 'ordinal' nunca se
--   expone por la API, por lo que no afecta al frontend ni a la lógica.
--
--   Solo se elimina la columna; los datos (nivel/estado/observación/por/fecha)
--   se conservan.
-- ============================================================================

BEGIN;

ALTER TABLE edan.aprobaciones_edan DROP COLUMN IF EXISTS ordinal;

COMMIT;

SELECT 'IDEMPOTENT OK v2.17.2 drop ordinal aprobaciones' AS resultado;