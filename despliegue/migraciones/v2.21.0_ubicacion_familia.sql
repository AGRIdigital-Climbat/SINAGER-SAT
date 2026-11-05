-- ============================================================================
-- SINAGERSAT - Migración v2.21.0 (idempotente)
-- NUEVA tabla `rida.ubicacion_familia` + catálogo mínimo `rida.cat_tipo_albergue`.
--
--   rida.cat_tipo_albergue (id_cat_tipo_albergue PK, nombre) — vacío, lo pobla el usuario.
--   rida.ubicacion_familia:
--     id_ubicacion_familia  (PK)
--     id_ubicacion_off      (identificador offline generado por el dispositivo)
--     coordenada_lat/lon    (convención EDAN NUMERIC(10,8)/(11,8))
--     id_familia            (FK -> rida.familia)
--     id_cat_tipo_albergue  (FK -> rida.cat_tipo_albergue)
--     fecha_creacion / fecha_modificacion
--
-- Además se enlaza el FK familia.id_ubicacion_familia -> rida.ubicacion_familia
-- (referencia circular familia <-> ubicacion_familia, bloque condicional).
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. Catálogo mínimo de tipo de albergue
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rida.cat_tipo_albergue (
    id_cat_tipo_albergue SERIAL PRIMARY KEY,
    nombre               VARCHAR(80) NOT NULL
);

-- ----------------------------------------------------------------------------
-- 2. Tabla nueva ubicacion_familia
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rida.ubicacion_familia (
    id_ubicacion_familia  SERIAL PRIMARY KEY,
    id_ubicacion_off      VARCHAR(36),
    coordenada_lat        NUMERIC(10,8),
    coordenada_lon        NUMERIC(11,8),
    id_familia            INTEGER NOT NULL REFERENCES rida.familia(id_familia),
    id_cat_tipo_albergue  INTEGER REFERENCES rida.cat_tipo_albergue(id_cat_tipo_albergue),
    fecha_creacion        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_modificacion    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ubicacion_familia_id_familia
    ON rida.ubicacion_familia (id_familia);

-- ----------------------------------------------------------------------------
-- 3. FK circular familia.id_ubicacion_familia -> ubicacion_familia
-- ----------------------------------------------------------------------------
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'familia_id_ubicacion_familia_fkey'
          AND conrelid = 'rida.familia'::regclass
    ) THEN
        ALTER TABLE rida.familia
            ADD CONSTRAINT familia_id_ubicacion_familia_fkey
                FOREIGN KEY (id_ubicacion_familia)
                REFERENCES rida.ubicacion_familia(id_ubicacion_familia);
    END IF;
END $$;

SELECT 'IDEMPOTENT OK v2.21.0 ubicacion_familia';

COMMIT;