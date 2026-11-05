-- ============================================================================
-- v2.47.0  rida.necesidad: eliminar id_formulario
--
-- La necesidad pertenece a una FAMILIA (necesidad.id_familia -> familia).
-- El vínculo con el formulario ya existe vía familia.id_formulario; la columna
-- rida.necesidad.id_formulario duplicaba ese camino y permitía necesidades
-- "huérfanas" de familia (colgando solo del formulario), que no entran en el
-- agrupado por familia del reporte. Se elimina para forzar una sola vía:
--     necesidad -> familia -> formulario -> localidad (edan_localidades)
-- El resto de APIs deriva id_formulario desde familia en cada SELECT.
-- ============================================================================
\set ON_ERROR_STOP on
BEGIN;

ALTER TABLE rida.necesidad DROP CONSTRAINT IF EXISTS necesidad_id_formulario_fkey;
ALTER TABLE rida.necesidad DROP COLUMN IF EXISTS id_formulario;

COMMENT ON TABLE rida.necesidad IS
    'Necesidad por familia (categoría de ayuda). Vínculo con el formulario SOLO vía familia.id_formulario; id_formulario se deriva en API.';

COMMIT;
SELECT 'IDEMPOTENT OK v2.47.0 necesidad sin id_formulario';
