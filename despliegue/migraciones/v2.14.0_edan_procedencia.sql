-- ============================================================================
-- SINAGERSAT - Migración v2.14.0 (idempotente)
-- Procedencia de EDAN consolidados (importación de histórico legacy):
--   Agrega a edan.edan (cabecera):
--     - procedencia   : origen del registro ('sistema' | 'excel_legacy' | 'api_import')
--     - origen_id     : id de la fila en la fuente legacy (dedup / re-importación)
--     - id_importacion: FK a edan.edan_importacion_log (lote que lo insertó)
--   Amplía edan.edan_localidades.localidad a TEXT (LUGAR del legacy llega a 1.096 chars).
-- ============================================================================

BEGIN;

ALTER TABLE edan.edan
    ADD COLUMN IF NOT EXISTS procedencia VARCHAR(20) NOT NULL DEFAULT 'sistema',
    ADD COLUMN IF NOT EXISTS origen_id VARCHAR(100),
    ADD COLUMN IF NOT EXISTS id_importacion BIGINT;

COMMENT ON COLUMN edan.edan.procedencia IS 'Origen del registro: sistema (actual), excel_legacy (importado desde BD legacy), api_import (cargado por API).';
COMMENT ON COLUMN edan.edan.origen_id IS 'Identificador del registro en la fuente legacy (ej: ID de la fila del Excel) para deduplicación de reimportaciones.';
COMMENT ON COLUMN edan.edan.id_importacion IS 'ID del lote (edan.edan_importacion_log) que insertó el registro.';

ALTER TABLE edan.edan
    ADD CONSTRAINT edan_procedencia_check
        CHECK (procedencia IN ('sistema', 'excel_legacy', 'api_import'));

CREATE INDEX IF NOT EXISTS idx_edan_procedencia
    ON edan.edan (procedencia);

CREATE INDEX IF NOT EXISTS idx_edan_origen_id
    ON edan.edan (origen_id);

CREATE UNIQUE INDEX IF NOT EXISTS edan_origen_id_key
    ON edan.edan (origen_id) WHERE origen_id IS NOT NULL;

ALTER TABLE edan.edan
    ADD CONSTRAINT edan_id_importacion_fk
        FOREIGN KEY (id_importacion)
        REFERENCES edan.edan_importacion_log (id_importacion)
        ON DELETE SET NULL;

ALTER TABLE edan.edan_localidades
    ALTER COLUMN localidad TYPE TEXT;

COMMIT;

SELECT 'IDEMPOTENT OK v2.14.0' AS resultado;