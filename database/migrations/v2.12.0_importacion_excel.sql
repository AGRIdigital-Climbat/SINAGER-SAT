-- ============================================================================
-- SINAGERSAT - Migración v2.12.0 (idempotente)
-- Importación de datos legacy (Excel):
--   Agrega a edan.edan_localidades:
--     - procedencia   : origen del registro ('sistema' | 'excel_legacy' | 'api_import')
--     - origen_id     : identificador del registro en la fuente legacy (dedup)
--     - id_importacion: FK a edan.edan_importacion_log (carga que lo insertó)
--   Crea edan.edan_importacion_log: registro de cada carga importada.
-- ============================================================================

BEGIN;

ALTER TABLE edan.edan_localidades
    ADD COLUMN IF NOT EXISTS procedencia VARCHAR(20) NOT NULL DEFAULT 'sistema',
    ADD COLUMN IF NOT EXISTS origen_id VARCHAR(100),
    ADD COLUMN IF NOT EXISTS id_importacion BIGINT;

COMMENT ON COLUMN edan.edan_localidades.procedencia IS 'Origen del registro: sistema (actual), excel_legacy (importado desde BD legacy), api_import (cargado por API).';
COMMENT ON COLUMN edan.edan_localidades.origen_id IS 'Identificador del registro en la fuente legacy (ej: ID de la fila del Excel) para deduplicación de reimportaciones.';
COMMENT ON COLUMN edan.edan_localidades.id_importacion IS 'ID del lote (edan.edan_importacion_log) que insertó el registro.';

ALTER TABLE edan.edan_localidades
    ADD CONSTRAINT edan_localidades_procedencia_check
        CHECK (procedencia IN ('sistema', 'excel_legacy', 'api_import'));

CREATE INDEX IF NOT EXISTS idx_edan_localidades_procedencia
    ON edan.edan_localidades (procedencia);

CREATE INDEX IF NOT EXISTS idx_edan_localidades_origen_id
    ON edan.edan_localidades (origen_id);

CREATE TABLE IF NOT EXISTS edan.edan_importacion_log (
    id_importacion BIGSERIAL PRIMARY KEY,
    nombre_archivo VARCHAR(255) NOT NULL,
    procedencia VARCHAR(20) NOT NULL DEFAULT 'excel_legacy',
    id_usuario INTEGER REFERENCES usuarios.usuario (id_usuario) ON DELETE SET NULL,
    fecha_importacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    filas_procesadas INTEGER NOT NULL DEFAULT 0,
    filas_insertadas INTEGER NOT NULL DEFAULT 0,
    filas_actualizadas INTEGER NOT NULL DEFAULT 0,
    filas_omitidas INTEGER NOT NULL DEFAULT 0,
    errores INTEGER NOT NULL DEFAULT 0,
    detalle JSONB NOT NULL DEFAULT '[]'::jsonb
);

COMMENT ON TABLE edan.edan_importacion_log IS 'Registro de cada carga de datos importados (Excel/API). Permite trazabilidad y reimportación.';
COMMENT ON COLUMN edan.edan_importacion_log.nombre_archivo IS 'Nombre del archivo de origen (ej: BDLimpia.xlsx).';
COMMENT ON COLUMN edan.edan_importacion_log.procedencia IS 'Procedencia marcada a los registros de esta carga.';
COMMENT ON COLUMN edan.edan_importacion_log.id_usuario IS 'Usuario autenticado que ejecutó la importación.';
COMMENT ON COLUMN edan.edan_importacion_log.detalle IS 'JSONB con errores por fila (fila, descripción).';

ALTER TABLE edan.edan_localidades
    ADD CONSTRAINT edan_localidades_id_importacion_fk
        FOREIGN KEY (id_importacion)
        REFERENCES edan.edan_importacion_log (id_importacion)
        ON DELETE SET NULL;

COMMIT;

SELECT 'IDEMPOTENT OK v2.12.0' AS resultado;