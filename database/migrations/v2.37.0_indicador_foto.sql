-- ============================================================================
-- v2.37.0 Fotos de indicador natural (tabla nueva) y eliminación de evidencia
-- ============================================================================
-- La galería de "evidencias" estaba vacía (0 filas) y sin altas desde el
-- código: solo existían 4 endpoints de lectura. Se sustituye por una tabla
-- dedicada `sinb.indicador_foto` vinculada 1:N a `sinb.indicador_natural`,
-- con CRUD bajo /sinb/indicador-natural/{id}/fotos.
-- ============================================================================

BEGIN;

-- 1. Tabla nueva: fotos de indicador natural
CREATE TABLE sinb.indicador_foto (
    id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    id_indicador_natural uuid NOT NULL REFERENCES sinb.indicador_natural(id) ON DELETE CASCADE,
    path_foto            text NOT NULL,
    descripcion          text NOT NULL,
    id_usuario_subio     int  NOT NULL REFERENCES usuarios.usuario(id_usuario),
    creado_en            timestamptz NOT NULL DEFAULT now(),
    actualizado_en       timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX ind_foto_indicador ON sinb.indicador_foto (id_indicador_natural);
CREATE INDEX ind_foto_usuario   ON sinb.indicador_foto (id_usuario_subio);

COMMENT ON TABLE sinb.indicador_foto IS 'Fotos de indicadores naturales; 1:N con sinb.indicador_natural; DELETE borra fila y archivo';
COMMENT ON COLUMN sinb.indicador_foto.path_foto IS 'Ruta relativa bajo uploads/ (ver api/upload.py)';

-- 2. Eliminar tabla obsoleta de galería (0 filas, sin FKs entrantes)
DROP TABLE IF EXISTS sinb.evidencia;

COMMIT;

-- Verificación
-- SELECT COUNT(*) FROM sinb.evidencia;            -- debe fallar (tabla inexistente)
-- \d sinb.indicador_foto                          -- debe existir
