-- ============================================================================
-- SINAGERSAT - Migración v2.19.0 (idempotente)
-- Reestructura `rida.familia` (SOLO esta tabla).
--
-- La tabla queda únicamente con:
--   id_familia          (PK)
--   id_familia_off      (identificador offline generado por el dispositivo)
--   id_formulario       (FK -> rida.formulario_rida, NOT NULL)
--   id_edan_localidad   (FK -> edan.edan_localidades)
--   id_ubicacion_familia (INTEGER sin FK: la tabla se crea más adelante)
--   fecha_creacion / fecha_modificacion
--   id_necesidad        (FK -> rida.necesidad, al final por referencia circular)
--   observacion
--
-- Se eliminan: codigo_ficha, id_condicion, ubicacion_original, ubicacion_actual,
-- id_jefe (arrastra el FK circular a rida.integrante), n_integrantes, estado,
-- observaciones, junto con sus índices/CHECK/FK dependientes.
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. Eliminar columnas que ya no aplican
-- ----------------------------------------------------------------------------
ALTER TABLE rida.familia
    DROP COLUMN IF EXISTS codigo_ficha,
    DROP COLUMN IF EXISTS id_condicion,
    DROP COLUMN IF EXISTS ubicacion_original,
    DROP COLUMN IF EXISTS ubicacion_actual,
    DROP COLUMN IF EXISTS id_jefe,
    DROP COLUMN IF EXISTS n_integrantes,
    DROP COLUMN IF EXISTS estado,
    DROP COLUMN IF EXISTS observaciones;

-- Limpieza explícita de restricciones dependientes (seguridad idempotente)
ALTER TABLE rida.familia
    DROP CONSTRAINT IF EXISTS familia_codigo_ficha_key,
    DROP CONSTRAINT IF EXISTS familia_id_condicion_fkey,
    DROP CONSTRAINT IF EXISTS familia_ubicacion_actual_check,
    DROP CONSTRAINT IF EXISTS fk_familia_jefe_integrante;

-- ----------------------------------------------------------------------------
-- 2. Nuevas columnas
-- ----------------------------------------------------------------------------
ALTER TABLE rida.familia
    ADD COLUMN IF NOT EXISTS id_familia_off    VARCHAR(36),
    ADD COLUMN IF NOT EXISTS id_edan_localidad INTEGER REFERENCES edan.edan_localidades(id_edan_localidad),
    ADD COLUMN IF NOT EXISTS id_ubicacion_familia INTEGER,
    ADD COLUMN IF NOT EXISTS fecha_creacion     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ADD COLUMN IF NOT EXISTS fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ADD COLUMN IF NOT EXISTS id_necesidad       INTEGER,
    ADD COLUMN IF NOT EXISTS observacion        TEXT;

-- ----------------------------------------------------------------------------
-- 3. FK circular familia -> necesidad (al final, por la referencia mutua)
-- ----------------------------------------------------------------------------
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'familia_id_necesidad_fkey'
          AND conrelid = 'rida.familia'::regclass
    ) THEN
        ALTER TABLE rida.familia
            ADD CONSTRAINT familia_id_necesidad_fkey
                FOREIGN KEY (id_necesidad) REFERENCES rida.necesidad(id_necesidad);
    END IF;
END $$;

ALTER TABLE rida.familia
    ALTER COLUMN id_formulario SET NOT NULL;

SELECT 'IDEMPOTENT OK v2.19.0 familia';

COMMIT;