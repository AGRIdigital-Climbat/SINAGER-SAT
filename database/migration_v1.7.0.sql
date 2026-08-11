-- ============================================================================
-- SINAGERSAT - Migración v1.7.0 (idempotente)
-- 1. edan.edan: se eliminan las columnas desnormalizadas *_nombre
--    (departamento_nombre, provincia_nombre, municipio_nombre, tipo_evento_nombre).
--    Los nombres se siguen resolviendo por JOIN en la API.
-- 2. edan.edan_localidades pasa a ser la UNIDAD DE REPORTE:
--    - id_edan pasa a NULLABLE y su FK cambia de CASCADE a ON DELETE SET NULL
--      (borrar un EDAN consolidado NO destruye los reportes aprobados).
--    - Nuevas columnas: id_tipo_evento, id_departamento, id_provincia,
--      id_municipio (FKs), fecha_llenado, fecha_evento, hora_evento y los
--      tres totales (población, familias afectadas, familias damnificadas).
--    - Backfill: las localidades existentes heredan los valores de su EDAN.
-- Aplica sobre migration_v1.6.0.
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. edan.edan: eliminar columnas desnormalizadas *_nombre
-- ============================================================================
ALTER TABLE edan.edan DROP COLUMN IF EXISTS departamento_nombre;
ALTER TABLE edan.edan DROP COLUMN IF EXISTS provincia_nombre;
ALTER TABLE edan.edan DROP COLUMN IF EXISTS municipio_nombre;
ALTER TABLE edan.edan DROP COLUMN IF EXISTS tipo_evento_nombre;

-- ============================================================================
-- 2. edan.edan_localidades: unidad de reporte
-- ============================================================================

-- 2.1 id_edan NULLABLE y FK con ON DELETE SET NULL
ALTER TABLE edan.edan_localidades ALTER COLUMN id_edan DROP NOT NULL;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'edan_localidades_id_edan_fkey'
    ) THEN
        ALTER TABLE edan.edan_localidades DROP CONSTRAINT edan_localidades_id_edan_fkey;
        ALTER TABLE edan.edan_localidades
            ADD CONSTRAINT edan_localidades_id_edan_fkey
            FOREIGN KEY (id_edan) REFERENCES edan.edan(id_edan) ON DELETE SET NULL;
    END IF;
END $$;

-- 2.2 Nuevas columnas
ALTER TABLE edan.edan_localidades ADD COLUMN IF NOT EXISTS id_tipo_evento integer;
ALTER TABLE edan.edan_localidades ADD COLUMN IF NOT EXISTS id_departamento integer;
ALTER TABLE edan.edan_localidades ADD COLUMN IF NOT EXISTS id_provincia integer;
ALTER TABLE edan.edan_localidades ADD COLUMN IF NOT EXISTS id_municipio integer;
ALTER TABLE edan.edan_localidades ADD COLUMN IF NOT EXISTS fecha_llenado date;
ALTER TABLE edan.edan_localidades ADD COLUMN IF NOT EXISTS fecha_evento date;
ALTER TABLE edan.edan_localidades ADD COLUMN IF NOT EXISTS hora_evento time without time zone;
ALTER TABLE edan.edan_localidades ADD COLUMN IF NOT EXISTS total_poblacion_afectada integer NOT NULL DEFAULT 0;
ALTER TABLE edan.edan_localidades ADD COLUMN IF NOT EXISTS total_familias_afectadas integer NOT NULL DEFAULT 0;
ALTER TABLE edan.edan_localidades ADD COLUMN IF NOT EXISTS total_familias_damnificadas integer NOT NULL DEFAULT 0;

-- 2.3 FKs
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'edan_localidades_id_tipo_evento_fkey') THEN
        ALTER TABLE edan.edan_localidades
            ADD CONSTRAINT edan_localidades_id_tipo_evento_fkey
            FOREIGN KEY (id_tipo_evento) REFERENCES edan.tipo_evento(id_tipo_evento) ON DELETE SET NULL;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'edan_localidades_id_departamento_fkey') THEN
        ALTER TABLE edan.edan_localidades
            ADD CONSTRAINT edan_localidades_id_departamento_fkey
            FOREIGN KEY (id_departamento) REFERENCES shared.departamento(id) ON DELETE SET NULL;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'edan_localidades_id_provincia_fkey') THEN
        ALTER TABLE edan.edan_localidades
            ADD CONSTRAINT edan_localidades_id_provincia_fkey
            FOREIGN KEY (id_provincia) REFERENCES shared.provincia(id) ON DELETE SET NULL;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'edan_localidades_id_municipio_fkey') THEN
        ALTER TABLE edan.edan_localidades
            ADD CONSTRAINT edan_localidades_id_municipio_fkey
            FOREIGN KEY (id_municipio) REFERENCES shared.municipio(id) ON DELETE SET NULL;
    END IF;
END $$;

-- 2.4 Backfill: las localidades existentes heredan de su EDAN
UPDATE edan.edan_localidades l
SET id_tipo_evento           = e.id_tipo_evento,
    id_departamento          = e.id_departamento,
    id_provincia             = e.id_provincia,
    id_municipio             = e.id_municipio,
    fecha_llenado            = e.fecha_llenado,
    fecha_evento             = e.fecha_evento,
    hora_evento              = e.hora_evento,
    total_poblacion_afectada    = COALESCE(e.total_poblacion_afectada, 0),
    total_familias_afectadas    = COALESCE(e.total_familias_afectadas, 0),
    total_familias_damnificadas = COALESCE(e.total_familias_damnificadas, 0)
FROM edan.edan e
WHERE l.id_edan = e.id_edan
  AND (l.id_tipo_evento IS NULL OR l.id_municipio IS NULL
       OR l.id_departamento IS NULL OR l.id_provincia IS NULL);

-- 2.5 Columnas de sincronización de localidad (la localidad es la unidad de
--     reporte y se sincroniza de forma autónoma antes de consolidarse)
ALTER TABLE edan.edan_localidades ADD COLUMN IF NOT EXISTS id_local varchar(64);
ALTER TABLE edan.edan_localidades ADD COLUMN IF NOT EXISTS id_server integer;
ALTER TABLE edan.edan_localidades ADD COLUMN IF NOT EXISTS id_usuario integer;
ALTER TABLE edan.edan_localidades ADD COLUMN IF NOT EXISTS fecha_modificacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE edan.edan_localidades ADD COLUMN IF NOT EXISTS sincronizado boolean NOT NULL DEFAULT false;
ALTER TABLE edan.edan_localidades ADD COLUMN IF NOT EXISTS pendiente_actualizacion boolean NOT NULL DEFAULT false;
ALTER TABLE edan.edan_localidades ADD COLUMN IF NOT EXISTS pendiente_eliminacion boolean NOT NULL DEFAULT false;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'edan_localidades_id_usuario_fkey') THEN
        ALTER TABLE edan.edan_localidades
            ADD CONSTRAINT edan_localidades_id_usuario_fkey
            FOREIGN KEY (id_usuario) REFERENCES usuarios.usuario(id_usuario) ON DELETE SET NULL;
    END IF;
END $$;

DROP INDEX IF EXISTS edan_localidades_id_local_key;
CREATE UNIQUE INDEX IF NOT EXISTS edan_localidades_id_local_key
    ON edan.edan_localidades(id_local) WHERE id_local IS NOT NULL;

-- 2.6 Índices
CREATE INDEX IF NOT EXISTS idx_edan_localidades_evento ON edan.edan_localidades(id_tipo_evento);
CREATE INDEX IF NOT EXISTS idx_edan_localidades_dep ON edan.edan_localidades(id_departamento);
CREATE INDEX IF NOT EXISTS idx_edan_localidades_prov ON edan.edan_localidades(id_provincia);
CREATE INDEX IF NOT EXISTS idx_edan_localidades_mun ON edan.edan_localidades(id_municipio);
CREATE INDEX IF NOT EXISTS idx_edan_localidades_consolidar
    ON edan.edan_localidades(id_municipio, id_tipo_evento, id_edan_localidad_estado);

COMMIT;

SELECT 'IDEMPOTENT OK v1.7.0' AS resultado;
