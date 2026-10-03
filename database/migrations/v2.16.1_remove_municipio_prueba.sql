-- ============================================================================
-- SINAGERSAT - Migración v2.16.1 (idempotente)
-- Elimina el municipio de prueba "_Prueba Mun" (codigo_ine '999998') de
-- shared.municipio. Es un dato de prueba SIN registros asociados (manzanos,
-- comunidades, EDAN, REA, repositorio ni usuarios), por lo que conviene
-- quitarlo de la tabla en lugar de excluirlo en cada consulta/API.
-- No rompe relaciones (no existen filas que referencien su id).
-- ============================================================================

BEGIN;

DELETE FROM shared.municipio
 WHERE codigo_ine = '999998'
   AND NOT EXISTS (SELECT 1 FROM shared.manzanos ma WHERE ma.id_municipio = shared.municipio.id)
   AND NOT EXISTS (SELECT 1 FROM shared.comunidades co WHERE co.id_municipio = shared.municipio.id);

COMMIT;

SELECT 'IDEMPOTENT OK v2.16.1 remove_municipio_prueba' AS resultado;