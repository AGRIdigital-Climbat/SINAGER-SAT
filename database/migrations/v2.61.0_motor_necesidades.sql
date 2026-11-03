-- =============================================================================
-- v2.61.0 — Motor de calculo de NECESIDADES (RIDA)
--
-- Agrega la base de datos del motor que calcula necesidades por familia a
-- partir de la poblacion objetivo y reglas, en lugar de depender solo de las
-- necesidades manuales del censo:
--
--   1. rida.regla_necesidad ....... regla de NECESIDAD (una regla = un
--                                   articulo de una categoria, con criterio
--                                   POR_FAMILIA | POR_INTEGRANTE |
--                                   POR_CONDICION_ESPECIAL, cantidad base,
--                                   dias de duracion y condiciones JSONB).
--   2. rida.necesidad (ALTER) ..... columna fuente ('manual' | 'motor') y
--                                   id_regla_necesidad (trazabilidad).
--
-- Semantica acordada:
--   * El motor manda: al persistir reemplaza las necesidades manuales de las
--     categorias que cubre para cada familia (aunque cambien articulo o
--     cantidad). Las categorias sin regla se conservan.
--   * Cantidad por familia = ceil(cantidad_base * dias * poblacion_familia);
--     no se usan cantidad_min/cantidad_max.
--   * Solo corren reglas activas.
--
-- Idempotente: puede aplicarse 2 veces sin efecto adverso.
-- =============================================================================

BEGIN;

-- 1. Reglas de necesidad -------------------------------------------------------
CREATE TABLE IF NOT EXISTS rida.regla_necesidad (
    id_regla_necesidad    serial PRIMARY KEY,
    nombre                varchar(100) NOT NULL,
    criterio_aplicacion   varchar(30)  NOT NULL
                          CHECK (criterio_aplicacion IN
                                 ('POR_FAMILIA', 'POR_INTEGRANTE', 'POR_CONDICION_ESPECIAL')),
    id_categoria_ayuda    integer NOT NULL
                          REFERENCES rida.cat_categoria_ayuda(id_categoria_ayuda)
                          ON DELETE RESTRICT,
    id_articulo           integer NOT NULL
                          REFERENCES rida.cat_articulo(id_articulo)
                          ON DELETE RESTRICT,
    cantidad_base         numeric(8, 3) NOT NULL DEFAULT 0
                          CHECK (cantidad_base >= 0),
    dias_duracion         integer CHECK (dias_duracion > 0),
    condiciones           jsonb NOT NULL DEFAULT '{}'::jsonb
                          CHECK (jsonb_typeof(condiciones) = 'object'),
    prioridad             integer NOT NULL DEFAULT 100,
    orden                 integer NOT NULL DEFAULT 0,
    activo                boolean NOT NULL DEFAULT TRUE,
    fecha_creacion        timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_modificacion    timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_regla_necesidad_activo
    ON rida.regla_necesidad(activo);
CREATE INDEX IF NOT EXISTS idx_regla_necesidad_categoria
    ON rida.regla_necesidad(id_categoria_ayuda);

COMMENT ON TABLE rida.regla_necesidad IS
    'Reglas del motor de necesidades: una fila = un articulo de una categoria '
    'con su cantidad base por familia/integrante/condicion. Solo las activas '
    'se ejecutan.';
COMMENT ON COLUMN rida.regla_necesidad.condiciones IS
    'Filtros opcionales para integrantes: {"gestante": bool, "discapacidad": '
    'bool, "edad_min_dias": int, "edad_max_dias": int, "sexo": "M"|"F"}. '
    'POR_FAMILIA exige {}. POR_CONDICION_ESPECIAL exige al menos un filtro.';

-- 2. Columnas de trazabilidad en necesidad ------------------------------------
ALTER TABLE rida.necesidad
    ADD COLUMN IF NOT EXISTS fuente varchar(20) NOT NULL DEFAULT 'manual';
ALTER TABLE rida.necesidad
    ADD COLUMN IF NOT EXISTS id_regla_necesidad integer;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'necesidad_fuente_check'
          AND conrelid = 'rida.necesidad'::regclass
    ) THEN
        ALTER TABLE rida.necesidad
            ADD CONSTRAINT necesidad_fuente_check
            CHECK (fuente IN ('manual', 'motor'));
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'necesidad_id_regla_necesidad_fkey'
          AND conrelid = 'rida.necesidad'::regclass
    ) THEN
        ALTER TABLE rida.necesidad
            ADD CONSTRAINT necesidad_id_regla_necesidad_fkey
            FOREIGN KEY (id_regla_necesidad)
            REFERENCES rida.regla_necesidad(id_regla_necesidad)
            ON DELETE SET NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_necesidad_fuente
    ON rida.necesidad(fuente);
CREATE INDEX IF NOT EXISTS idx_necesidad_id_regla_necesidad
    ON rida.necesidad(id_regla_necesidad);

-- Una sola fila de motor por familia + articulo (las manuales se reemplazan
-- por categoria antes de insertar, asi que no quedan duplicados).
CREATE UNIQUE INDEX IF NOT EXISTS uq_necesidad_motor_familia_articulo
    ON rida.necesidad(id_familia, id_articulo)
    WHERE fuente = 'motor' AND id_articulo IS NOT NULL;

COMMENT ON COLUMN rida.necesidad.fuente IS
    'manual = capturada/editada por el usuario; motor = generada por '
    'POST /ayuda-humanitaria/expedientes/{id}/motor-necesidades.';
COMMENT ON COLUMN rida.necesidad.id_regla_necesidad IS
    'Regla de necesidad que genero la fila (NULL si es manual).';

COMMIT;
