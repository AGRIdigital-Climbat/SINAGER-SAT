-- ============================================================================
-- SINAGERSAT - Migración v2.18.0 (idempotente)
-- Reestructura `rida.formulario_rida` (SOLO esta tabla).
--
-- La tabla queda únicamente con:
--   id_formulario      (PK)
--   id_edan_localidad  (FK -> edan.edan_localidades, UNIQUE 1:1)
--   id_edan            (FK -> edan.edan; "aprobado" controlado por frontend)
--   id_estado          (FK -> rida.cat_estado_formulario)
--   id_usuario         (FK -> usuarios.usuario)
--   fecha_creacion / fecha_modificacion
--
-- Se eliminan: nombre_localidad, id_municipio, id_departamento,
-- tipo_asentamiento, n_carpa, lat, lon, geom, estado,
-- junto con sus índices/CHECK/FK dependientes.
--
-- Nuevo catálogo requerido: rida.cat_estado_formulario
-- (semilla PENDIENTE / EN_PROCESO / CERRADO).
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. Catálogo de estados del formulario (referenciado por id_estado)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rida.cat_estado_formulario (
    id_estado_formulario SERIAL PRIMARY KEY,
    codigo               VARCHAR(30) UNIQUE NOT NULL,
    nombre               VARCHAR(80) NOT NULL,
    descripcion          TEXT,
    orden                INTEGER,
    activo               BOOLEAN DEFAULT TRUE
);

INSERT INTO rida.cat_estado_formulario (codigo, nombre, descripcion, orden, activo)
VALUES
    ('PENDIENTE',  'Pendiente',  'Formulario creado, pendiente de proceso', 1, TRUE),
    ('EN_PROCESO', 'En proceso', 'Formulario en proceso de gestión',        2, TRUE),
    ('CERRADO',    'Cerrado',    'Formulario cerrado',                      3, TRUE)
ON CONFLICT (codigo) DO NOTHING;

-- ----------------------------------------------------------------------------
-- 2. rida.formulario_rida: nueva columna id_estado
-- ----------------------------------------------------------------------------
ALTER TABLE rida.formulario_rida
    ADD COLUMN IF NOT EXISTS id_estado INTEGER
        REFERENCES rida.cat_estado_formulario(id_estado_formulario);

DO $$
DECLARE v_id_pendiente INTEGER;
BEGIN
    SELECT id_estado_formulario INTO v_id_pendiente
    FROM rida.cat_estado_formulario WHERE codigo = 'PENDIENTE';
    IF v_id_pendiente IS NOT NULL THEN
        EXECUTE 'ALTER TABLE rida.formulario_rida ALTER COLUMN id_estado SET DEFAULT ' || v_id_pendiente;
    END IF;
END $$;

ALTER TABLE rida.formulario_rida ALTER COLUMN id_estado SET NOT NULL;

-- ----------------------------------------------------------------------------
-- 3. Eliminar columnas que ya no aplican
-- ----------------------------------------------------------------------------
ALTER TABLE rida.formulario_rida
    DROP COLUMN IF EXISTS nombre_localidad,
    DROP COLUMN IF EXISTS id_municipio,
    DROP COLUMN IF EXISTS id_departamento,
    DROP COLUMN IF EXISTS tipo_asentamiento,
    DROP COLUMN IF EXISTS n_carpa,
    DROP COLUMN IF EXISTS lat,
    DROP COLUMN IF EXISTS lon,
    DROP COLUMN IF EXISTS geom,
    DROP COLUMN IF EXISTS estado;

-- Limpieza explícita de índices dependientes (seguridad idempotente)
DROP INDEX IF EXISTS rida.idx_formulario_id_municipio;
DROP INDEX IF EXISTS rida.idx_formulario_rida_geom;

-- Restricciones dependientes (DROP COLUMN ya las elimina; IF EXISTS por robustez)
ALTER TABLE rida.formulario_rida
    DROP CONSTRAINT IF EXISTS formulario_rida_tipo_asentamiento_check,
    DROP CONSTRAINT IF EXISTS formulario_rida_id_municipio_fkey,
    DROP CONSTRAINT IF EXISTS formulario_rida_id_departamento_fkey;

SELECT 'IDEMPOTENT OK v2.18.0 formulario_rida';

COMMIT;