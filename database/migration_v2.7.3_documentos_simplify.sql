-- ============================================================================
-- SINAGERSAT - Migración v2.7.3 (idempotente)
-- Simplificación de repositorio.documentos:
--   Eliminar campos innecesarios:
--     - mime_type       (siempre será application/pdf)
--     - version         (sin versionado)
--     - id_documento_padre (sin versionado)
--     - metadata        (ya hay columnas dedicadas)
--     - ip_origen       (audit no esencial)
--   Eliminar vista:
--     - vw_documentos_activos (sin versionado no aplica)
--   Eliminar índice relacionado con versionado.
-- ============================================================================

BEGIN;

DROP VIEW IF EXISTS repositorio.vw_documentos_activos;
DROP INDEX IF EXISTS repositorio.idx_documentos_version;
DROP INDEX IF EXISTS repositorio.idx_documentos_consulta;

ALTER TABLE repositorio.documentos
    DROP COLUMN IF EXISTS mime_type,
    DROP COLUMN IF EXISTS version,
    DROP COLUMN IF EXISTS id_documento_padre,
    DROP COLUMN IF EXISTS metadata,
    DROP COLUMN IF EXISTS ip_origen;

ALTER TABLE repositorio.documentos
    DROP CONSTRAINT IF EXISTS chk_version_positiva;

COMMENT ON TABLE  repositorio.documentos IS 'Repositorio centralizado de documentos PDF vinculados a EDAN. Tabla mínima (~13 columnas).';

COMMIT;

SELECT 'IDEMPOTENT OK v2.7.3' AS resultado;
