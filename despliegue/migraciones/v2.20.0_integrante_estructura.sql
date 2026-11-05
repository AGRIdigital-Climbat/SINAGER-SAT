-- ============================================================================
-- SINAGERSAT - Migración v2.20.0 (idempotente)
-- Reestructura `rida.integrante` (SOLO esta tabla).
--
-- La tabla queda únicamente con:
--   id_integrante       (PK)
--   id_familia          (FK -> rida.familia, NOT NULL)
--   nombre              (antes "nombres")
--   apellido            (antes "apellidos")
--   sexo                (CHAR(1) CHECK 'M'/'F')
--   fecha_nacimiento    (DATE)
--   numero_ci
--   id_parentesco       (FK -> rida.cat_parentesco)
--   es_jefe             (BOOLEAN)
--   gestante_semanas    (CHECK 0..45)
--   lactante_meses      (CHECK 0..36)
--   id_discapacidad     (FK -> rida.cat_tipo_discapacidad)
--   id_enfermedad       (FK -> rida.cat_enfermedad_cronica)
--   telefono
--   id_integrante_off   (identificador offline generado por el dispositivo)
--   fecha_creacion / fecha_modificacion
--
-- Se eliminan: medicacion_continua, actividad_economica, observaciones.
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. Renombrar (DROP + ADD, por idempotencia; tabla vacía)
-- ----------------------------------------------------------------------------
ALTER TABLE rida.integrante
    DROP COLUMN IF EXISTS nombres,
    DROP COLUMN IF EXISTS apellidos,
    DROP COLUMN IF EXISTS medicacion_continua,
    DROP COLUMN IF EXISTS actividad_economica,
    DROP COLUMN IF EXISTS observaciones;

-- ----------------------------------------------------------------------------
-- 2. Nuevas columnas
-- ----------------------------------------------------------------------------
ALTER TABLE rida.integrante
    ADD COLUMN IF NOT EXISTS nombre           VARCHAR(100) NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS apellido         VARCHAR(100) NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS id_integrante_off VARCHAR(36),
    ADD COLUMN IF NOT EXISTS fecha_creacion     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ADD COLUMN IF NOT EXISTS fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

SELECT 'IDEMPOTENT OK v2.20.0 integrante';

COMMIT;