-- ============================================================================
-- SINAGERSAT - Migración v2.7.1 (idempotente)
-- Crea la tabla principal `repositorio.documentos` con soporte de:
--   - Versionado (self-reference id_documento_padre)
--   - Búsqueda full-text (TSVECTOR + GIN index + trigger)
--   - Soft delete (activo)
--   - Metadata flexible (JSONB)
--   - FK cross-schema hacia edan.edan, usuarios.usuario, shared.municipio
-- ============================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS repositorio.documentos (
    id_documento         BIGSERIAL PRIMARY KEY,
    id_edan              BIGINT NOT NULL REFERENCES edan.edan(id_edan) ON DELETE CASCADE,
    id_tipo_documento    INTEGER NOT NULL REFERENCES repositorio.tipo_documento(id_tipo_documento),
    nombre_original      VARCHAR(255) NOT NULL,
    path_archivo         VARCHAR(500) NOT NULL,
    mime_type            VARCHAR(100) NOT NULL,
    tamano_bytes         INTEGER NOT NULL,
    hash_sha256          CHAR(64),
    version              INTEGER NOT NULL DEFAULT 1,
    id_documento_padre   BIGINT REFERENCES repositorio.documentos(id_documento),
    metadata             JSONB DEFAULT '{}',
    texto_busqueda       TSVECTOR,
    id_usuario_subio     INTEGER NOT NULL REFERENCES usuarios.usuario(id_usuario),
    id_municipio         INTEGER REFERENCES shared.municipio(id),
    fecha_subida         TIMESTAMP DEFAULT NOW(),
    ip_origen            VARCHAR(45),
    activo               BOOLEAN DEFAULT TRUE,
    observaciones        TEXT,
    CONSTRAINT chk_version_positiva CHECK (version > 0),
    CONSTRAINT chk_tamano_positivo  CHECK (tamano_bytes > 0)
);

CREATE INDEX IF NOT EXISTS idx_documentos_edan           ON repositorio.documentos(id_edan);
CREATE INDEX IF NOT EXISTS idx_documentos_tipo           ON repositorio.documentos(id_tipo_documento);
CREATE INDEX IF NOT EXISTS idx_documentos_municipio      ON repositorio.documentos(id_municipio);
CREATE INDEX IF NOT EXISTS idx_documentos_fecha          ON repositorio.documentos(fecha_subida DESC);
CREATE INDEX IF NOT EXISTS idx_documentos_activo         ON repositorio.documentos(activo) WHERE activo = TRUE;
CREATE INDEX IF NOT EXISTS idx_documentos_version        ON repositorio.documentos(id_documento_padre, version DESC) WHERE id_documento_padre IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_documentos_busqueda_ft    ON repositorio.documentos USING GIN(texto_busqueda);
CREATE INDEX IF NOT EXISTS idx_documentos_consulta        ON repositorio.documentos(id_edan, id_tipo_documento, version DESC, activo) WHERE activo = TRUE;

CREATE OR REPLACE FUNCTION repositorio.fn_update_texto_busqueda()
RETURNS TRIGGER AS $$
BEGIN
    NEW.texto_busqueda :=
        setweight(to_tsvector('spanish', COALESCE(NEW.nombre_original, '')), 'A') ||
        setweight(to_tsvector('spanish', COALESCE(NEW.metadata::text, '')),  'D');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_update_texto_busqueda ON repositorio.documentos;
CREATE TRIGGER trg_update_texto_busqueda
    BEFORE INSERT OR UPDATE ON repositorio.documentos
    FOR EACH ROW
    EXECUTE FUNCTION repositorio.fn_update_texto_busqueda();

CREATE OR REPLACE VIEW repositorio.vw_documentos_activos AS
SELECT DISTINCT ON (COALESCE(d.id_documento_padre, d.id_documento))
    d.*
FROM repositorio.documentos d
WHERE d.activo = TRUE
ORDER BY COALESCE(d.id_documento_padre, d.id_documento), d.version DESC;

COMMENT ON TABLE  repositorio.documentos             IS 'Repositorio centralizado de documentos PDF vinculados a EDAN. Soporta versionado y búsqueda full-text.';
COMMENT ON COLUMN repositorio.documentos.version     IS 'Número de versión (1=original, 2+=actualización). NULL en id_documento_padre = versión raíz.';
COMMENT ON COLUMN repositorio.documentos.texto_busqueda IS 'TSVECTOR (es) indexado por GIN para búsqueda full-text sobre nombre y metadata.';

COMMIT;

SELECT 'IDEMPOTENT OK v2.7.1' AS resultado;
