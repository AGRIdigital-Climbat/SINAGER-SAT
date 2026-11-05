-- ============================================================================
-- SINAGERSAT - Migración v2.7.2 (idempotente)
-- Cambios en repositorio.documentos:
--   1. Agregar campos dedicados para filtros:
--        id_departamento, id_provincia, fecha_documento, nombre_documento
--   2. Remover full-text search (no útil para PDFs escaneados sin OCR):
--        DROP COLUMN texto_busqueda, DROP INDEX GIN, DROP FUNCTION, DROP TRIGGER
-- ============================================================================

BEGIN;

-- 1. AGREGAR COLUMNAS DEDICADAS PARA METADATA
ALTER TABLE repositorio.documentos
    ADD COLUMN IF NOT EXISTS id_departamento   INTEGER REFERENCES shared.departamento(id),
    ADD COLUMN IF NOT EXISTS id_provincia      INTEGER REFERENCES shared.provincia(id),
    ADD COLUMN IF NOT EXISTS fecha_documento   DATE,
    ADD COLUMN IF NOT EXISTS nombre_documento  VARCHAR(255);

-- 2. ÍNDICES PARA FILTROS
CREATE INDEX IF NOT EXISTS idx_documentos_departamento ON repositorio.documentos(id_departamento);
CREATE INDEX IF NOT EXISTS idx_documentos_provincia    ON repositorio.documentos(id_provincia);
CREATE INDEX IF NOT EXISTS idx_documentos_fecha_doc    ON repositorio.documentos(fecha_documento DESC);
CREATE INDEX IF NOT EXISTS idx_documentos_nombre       ON repositorio.documentos(nombre_documento);

-- 3. REMOVER FULL-TEXT SEARCH
DROP INDEX IF EXISTS repositorio.idx_documentos_busqueda_ft;
DROP TRIGGER IF EXISTS trg_update_texto_busqueda ON repositorio.documentos;
DROP FUNCTION IF EXISTS repositorio.fn_update_texto_busqueda();
DROP VIEW IF EXISTS repositorio.vw_documentos_activos;
ALTER TABLE repositorio.documentos DROP COLUMN IF EXISTS texto_busqueda;

-- 4. RECREAR VISTA (sin tocar columnas eliminadas)
CREATE OR REPLACE VIEW repositorio.vw_documentos_activos AS
SELECT DISTINCT ON (COALESCE(d.id_documento_padre, d.id_documento))
    d.*
FROM repositorio.documentos d
WHERE d.activo = TRUE
ORDER BY COALESCE(d.id_documento_padre, d.id_documento), d.version DESC;

-- 5. ACTUALIZAR COMENTARIOS
COMMENT ON COLUMN repositorio.documentos.id_departamento  IS 'FK a shared.departamento (denormalizado para filtros sin JOIN).';
COMMENT ON COLUMN repositorio.documentos.id_provincia     IS 'FK a shared.provincia (denormalizado para filtros sin JOIN).';
COMMENT ON COLUMN repositorio.documentos.fecha_documento  IS 'Fecha del documento (no fecha_subida).';
COMMENT ON COLUMN repositorio.documentos.nombre_documento IS 'Nombre normalizado para búsquedas exactas/filtros.';

COMMIT;

SELECT 'IDEMPOTENT OK v2.7.2' AS resultado;
