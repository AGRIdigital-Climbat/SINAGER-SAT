-- ============================================================================
-- MIGRACIÓN v1.4.0 — EDAN jerárquico por localidades
-- ============================================================================
-- Rediseña el esquema EDAN (edan.edan plano) al modelo por localidades de la
-- app AppREA (PostgresEDAN.md / lib/models/edan.dart).
--
-- * Cabecera edan.edan: sync flags, id_provincia, id_usuario, id_tipo_evento,
--   id_estado/estado, renombres (fono_alcalde, responsable_*, fecha_*).
-- * Nueva edan.estado_edan (catálogo de estados) + seed.
-- * Nueva edan.edan_localidades + 16 sub-tablas colgando de id_edan_localidad.
-- * DROP de las tablas planas vacías + edan_comunidad + junction edan_tipo_evento.
--
-- Idempotente: se puede ejecutar varias veces con seguridad.
-- ============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- 1. Catálogo de estados EDAN
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS edan.estado_edan (
    id_estado   SERIAL PRIMARY KEY,
    nombre      VARCHAR(50) NOT NULL UNIQUE,
    descripcion TEXT,
    orden       INT NOT NULL DEFAULT 0
);

INSERT INTO edan.estado_edan (nombre, descripcion, orden) VALUES
    ('borrador',   'Formulario en borrador, no enviado',      1),
    ('enviado',    'Formulario enviado al servidor',          2),
    ('aprobado',   'Formulario aprobado',                     3),
    ('rechazado',  'Formulario rechazado',                    4),
    ('cerrado',    'Formulario cerrado',                      5)
ON CONFLICT (nombre) DO NOTHING;

-- ---------------------------------------------------------------------------
-- 2. Cabecera edan.edan — renombres de columnas
-- ---------------------------------------------------------------------------
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_schema='edan' AND table_name='edan' AND column_name='telefono_alcalde') THEN
        ALTER TABLE edan.edan RENAME COLUMN telefono_alcalde TO fono_alcalde;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_schema='edan' AND table_name='edan' AND column_name='nombre_responsable') THEN
        ALTER TABLE edan.edan RENAME COLUMN nombre_responsable TO responsable_nombre;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_schema='edan' AND table_name='edan' AND column_name='cargo_responsable') THEN
        ALTER TABLE edan.edan RENAME COLUMN cargo_responsable TO responsable_cargo;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_schema='edan' AND table_name='edan' AND column_name='telefono_responsable') THEN
        ALTER TABLE edan.edan RENAME COLUMN telefono_responsable TO responsable_fono;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_schema='edan' AND table_name='edan' AND column_name='email_responsable') THEN
        ALTER TABLE edan.edan RENAME COLUMN email_responsable TO responsable_correo;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_schema='edan' AND table_name='edan' AND column_name='fecha_registro') THEN
        ALTER TABLE edan.edan RENAME COLUMN fecha_registro TO fecha_creacion;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_schema='edan' AND table_name='edan' AND column_name='fecha_actualizacion') THEN
        ALTER TABLE edan.edan RENAME COLUMN fecha_actualizacion TO fecha_modificacion;
    END IF;
END $$;

-- ---------------------------------------------------------------------------
-- 3. Cabecera edan.edan — nuevas columnas (sync + geografía + estado)
-- ---------------------------------------------------------------------------
ALTER TABLE edan.edan
    ADD COLUMN IF NOT EXISTS id_server            INT,
    ADD COLUMN IF NOT EXISTS id_provincia         INT,
    ADD COLUMN IF NOT EXISTS id_usuario           INT,
    ADD COLUMN IF NOT EXISTS id_tipo_evento       INT,
    ADD COLUMN IF NOT EXISTS id_estado            INT NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS estado               VARCHAR(50) NOT NULL DEFAULT 'borrador',
    ADD COLUMN IF NOT EXISTS sincronizado         BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS pendiente_eliminacion   BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS pendiente_actualizacion BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS es_borrador          BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS intentos_sync        INT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS ultimo_error         TEXT,
    ADD COLUMN IF NOT EXISTS departamento_nombre  VARCHAR(200),
    ADD COLUMN IF NOT EXISTS provincia_nombre     VARCHAR(200),
    ADD COLUMN IF NOT EXISTS municipio_nombre     VARCHAR(200),
    ADD COLUMN IF NOT EXISTS tipo_evento_nombre   VARCHAR(100);

-- Columnas planas obsoletas
ALTER TABLE edan.edan
    DROP COLUMN IF EXISTS usuario_registro,
    DROP COLUMN IF EXISTS localidades_afectadas;

-- FKs de la cabecera
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='edan_id_provincia_fkey') THEN
        ALTER TABLE edan.edan ADD CONSTRAINT edan_id_provincia_fkey
            FOREIGN KEY (id_provincia) REFERENCES shared.provincia(id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='edan_id_usuario_fkey') THEN
        ALTER TABLE edan.edan ADD CONSTRAINT edan_id_usuario_fkey
            FOREIGN KEY (id_usuario) REFERENCES usuarios.usuario(id_usuario);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='edan_id_tipo_evento_fkey') THEN
        ALTER TABLE edan.edan ADD CONSTRAINT edan_id_tipo_evento_fkey
            FOREIGN KEY (id_tipo_evento) REFERENCES edan.tipo_evento(id_tipo_evento);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='edan_id_estado_fkey') THEN
        ALTER TABLE edan.edan ADD CONSTRAINT edan_id_estado_fkey
            FOREIGN KEY (id_estado) REFERENCES edan.estado_edan(id_estado);
    END IF;
END $$;

-- Backfill cabecera existente (solo 1 EDAN de prueba)
UPDATE edan.edan e
SET id_provincia       = COALESCE(e.id_provincia, m.id_provincia),
    provincia_nombre   = COALESCE(e.provincia_nombre, p.nombre),
    departamento_nombre = COALESCE(e.departamento_nombre, d.nombre),
    municipio_nombre   = COALESCE(e.municipio_nombre, m.nombre),
    id_estado          = COALESCE(e.id_estado, 1),
    estado             = COALESCE(NULLIF(e.estado, ''), 'borrador'),
    es_borrador        = TRUE
FROM shared.municipio m
LEFT JOIN shared.provincia p ON p.id = m.id_provincia
LEFT JOIN shared.departamento d ON d.id = m.id_departamento
WHERE m.id = e.id_municipio;

-- ---------------------------------------------------------------------------
-- 4. edan_localidades (nodo intermedio)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS edan.edan_localidades (
    id_edan_localidad SERIAL PRIMARY KEY,
    id_edan           BIGINT NOT NULL REFERENCES edan.edan(id_edan) ON DELETE CASCADE,
    tipo_localidad    VARCHAR(50)  NOT NULL DEFAULT '',
    nombre            VARCHAR(200) NOT NULL DEFAULT '',
    imp_poblacion     BOOLEAN NOT NULL DEFAULT FALSE,
    imp_salud         BOOLEAN NOT NULL DEFAULT FALSE,
    imp_infraestructura BOOLEAN NOT NULL DEFAULT FALSE,
    imp_servicios     BOOLEAN NOT NULL DEFAULT FALSE,
    imp_educacion     BOOLEAN NOT NULL DEFAULT FALSE,
    imp_vivienda      BOOLEAN NOT NULL DEFAULT FALSE,
    imp_agropecuario  BOOLEAN NOT NULL DEFAULT FALSE,
    imp_proteccion    BOOLEAN NOT NULL DEFAULT FALSE,
    imp_necesidades   BOOLEAN NOT NULL DEFAULT FALSE
);

-- ---------------------------------------------------------------------------
-- 5. Sub-tablas por localidad
-- ---------------------------------------------------------------------------

-- 5.1 Impacto en población (1:1)
CREATE TABLE IF NOT EXISTS edan.edan_localidades_impacto_poblacion (
    id_edan_localidad BIGINT PRIMARY KEY REFERENCES edan.edan_localidades(id_edan_localidad) ON DELETE CASCADE,
    grupo_etario      VARCHAR(100) NOT NULL DEFAULT '',
    fallecidos        INT NOT NULL DEFAULT 0,
    heridos           INT NOT NULL DEFAULT 0,
    desaparecidos     INT NOT NULL DEFAULT 0,
    observaciones     TEXT NOT NULL DEFAULT ''
);

-- 5.1a Detalle de grupos etarios (1:N)
CREATE TABLE IF NOT EXISTS edan.edan_grupo_etario_detalle (
    id_grupo_etario_detalle SERIAL PRIMARY KEY,
    id_edan_localidad BIGINT NOT NULL REFERENCES edan.edan_localidades(id_edan_localidad) ON DELETE CASCADE,
    rango             VARCHAR(100) NOT NULL DEFAULT '',
    fallecidos        INT NOT NULL DEFAULT 0,
    heridos           INT NOT NULL DEFAULT 0,
    desaparecidos     INT NOT NULL DEFAULT 0,
    observaciones     TEXT NOT NULL DEFAULT ''
);

-- 5.2 Primera respuesta (1:1)
CREATE TABLE IF NOT EXISTS edan.edan_localidades_primera_respuesta (
    id_edan_localidad BIGINT PRIMARY KEY REFERENCES edan.edan_localidades(id_edan_localidad) ON DELETE CASCADE,
    busqueda          BOOLEAN NOT NULL DEFAULT FALSE,
    salvamento        BOOLEAN NOT NULL DEFAULT FALSE,
    evacuacion        BOOLEAN NOT NULL DEFAULT FALSE,
    observaciones     TEXT NOT NULL DEFAULT ''
);

-- 5.3 Establecimientos de salud (1:N)
CREATE TABLE IF NOT EXISTS edan.edan_localidades_salud_establecimientos (
    id_establecimiento_salud SERIAL PRIMARY KEY,
    id_edan_localidad BIGINT NOT NULL REFERENCES edan.edan_localidades(id_edan_localidad) ON DELETE CASCADE,
    nombre_establecimiento VARCHAR(200) NOT NULL DEFAULT '',
    comunidad         VARCHAR(200) NOT NULL DEFAULT '',
    nivel_atencion    VARCHAR(50)  NOT NULL DEFAULT '',
    dano_parcial      BOOLEAN NOT NULL DEFAULT FALSE,
    dano_total        BOOLEAN NOT NULL DEFAULT FALSE,
    medicos_afectados INT NOT NULL DEFAULT 0,
    enfermeras_afectadas INT NOT NULL DEFAULT 0,
    otros_afectados   INT NOT NULL DEFAULT 0
);

-- 5.4 Necesidades de salud (1:1)
CREATE TABLE IF NOT EXISTS edan.edan_localidades_salud_necesidades (
    id_edan_localidad BIGINT PRIMARY KEY REFERENCES edan.edan_localidades(id_edan_localidad) ON DELETE CASCADE,
    botiquines        BOOLEAN NOT NULL DEFAULT FALSE,
    numero_personas   INT NOT NULL DEFAULT 0,
    otras_necesidades TEXT NOT NULL DEFAULT '',
    observaciones     TEXT NOT NULL DEFAULT ''
);

-- 5.5 Daños viales (1:N)
CREATE TABLE IF NOT EXISTS edan.edan_localidades_danos_viales (
    id_dano_vial      SERIAL PRIMARY KEY,
    id_edan_localidad BIGINT NOT NULL REFERENCES edan.edan_localidades(id_edan_localidad) ON DELETE CASCADE,
    via_puente        VARCHAR(200) NOT NULL DEFAULT '',
    tramo             VARCHAR(200) NOT NULL DEFAULT '',
    dano_parcial      BOOLEAN NOT NULL DEFAULT FALSE,
    dano_total        BOOLEAN NOT NULL DEFAULT FALSE,
    km_danio          NUMERIC(10,2) NOT NULL DEFAULT 0,
    necesidades_inmediatas TEXT NOT NULL DEFAULT '',
    observaciones     TEXT NOT NULL DEFAULT ''
);

-- 5.6 Daños infraestructura pública (1:N)
CREATE TABLE IF NOT EXISTS edan.edan_localidades_danos_infra_publica (
    id_dano_infra     SERIAL PRIMARY KEY,
    id_edan_localidad BIGINT NOT NULL REFERENCES edan.edan_localidades(id_edan_localidad) ON DELETE CASCADE,
    comunidad         VARCHAR(200) NOT NULL DEFAULT '',
    tipo_estructura   VARCHAR(200) NOT NULL DEFAULT '',
    dano_parcial      BOOLEAN NOT NULL DEFAULT FALSE,
    dano_total        BOOLEAN NOT NULL DEFAULT FALSE,
    observaciones     TEXT NOT NULL DEFAULT ''
);

-- 5.7 Servicios básicos (1:N, 5 tipos fijos)
CREATE TABLE IF NOT EXISTS edan.edan_localidades_servicios_basicos (
    id_servicio_basico SERIAL PRIMARY KEY,
    id_edan_localidad BIGINT NOT NULL REFERENCES edan.edan_localidades(id_edan_localidad) ON DELETE CASCADE,
    tipo              VARCHAR(50) NOT NULL
        CHECK (tipo IN ('energia_electrica','agua_potable','alcantarillado','gas_domiciliario','telecomunicaciones')),
    afectado          BOOLEAN NOT NULL DEFAULT FALSE,
    dano_parcial      BOOLEAN NOT NULL DEFAULT FALSE,
    dano_total        BOOLEAN NOT NULL DEFAULT FALSE,
    necesidades_inmediatas TEXT NOT NULL DEFAULT '',
    observaciones     TEXT NOT NULL DEFAULT '',
    UNIQUE (id_edan_localidad, tipo)
);

-- 5.8 Unidades educativas (1:N)
CREATE TABLE IF NOT EXISTS edan.edan_localidades_unidades_educativas (
    id_unidad_educativa SERIAL PRIMARY KEY,
    id_edan_localidad BIGINT NOT NULL REFERENCES edan.edan_localidades(id_edan_localidad) ON DELETE CASCADE,
    nombre_establecimiento VARCHAR(200) NOT NULL DEFAULT '',
    comunidad         VARCHAR(200) NOT NULL DEFAULT '',
    dano_parcial      BOOLEAN NOT NULL DEFAULT FALSE,
    dano_total        BOOLEAN NOT NULL DEFAULT FALSE,
    suspension_clases BOOLEAN,
    perdida_material  BOOLEAN,
    funciona_albergue BOOLEAN,
    estudiantes       INT NOT NULL DEFAULT 0,
    profesores        INT NOT NULL DEFAULT 0,
    administrativos   INT NOT NULL DEFAULT 0,
    observaciones     TEXT NOT NULL DEFAULT ''
);

-- 5.9 Daños vivienda (1:N, dano_* son números)
CREATE TABLE IF NOT EXISTS edan.edan_localidades_danos_vivienda (
    id_dano_vivienda  SERIAL PRIMARY KEY,
    id_edan_localidad BIGINT NOT NULL REFERENCES edan.edan_localidades(id_edan_localidad) ON DELETE CASCADE,
    comunidad         VARCHAR(200) NOT NULL DEFAULT '',
    dano_parcial      INT NOT NULL DEFAULT 0,
    dano_total        INT NOT NULL DEFAULT 0,
    necesidades_inmediatas TEXT NOT NULL DEFAULT '',
    observaciones     TEXT NOT NULL DEFAULT ''
);

-- 5.10 Daños agricultura (1:N, texto libre + FK opcional a shared.cultivo)
CREATE TABLE IF NOT EXISTS edan.edan_localidades_danos_agricultura (
    id_dano_agricultura SERIAL PRIMARY KEY,
    id_edan_localidad BIGINT NOT NULL REFERENCES edan.edan_localidades(id_edan_localidad) ON DELETE CASCADE,
    tipo_cultivo      VARCHAR(200) NOT NULL DEFAULT '',
    id_cultivo        INT REFERENCES shared.cultivo(id),
    hectareas_afectadas INT NOT NULL DEFAULT 0,
    hectareas_perdidas   INT NOT NULL DEFAULT 0,
    necesidades_inmediatas TEXT NOT NULL DEFAULT '',
    observaciones     TEXT NOT NULL DEFAULT ''
);

-- 5.11 Daños pecuario (1:N, texto libre + FK opcional a shared.pecuario)
CREATE TABLE IF NOT EXISTS edan.edan_localidades_danos_pecuario (
    id_dano_pecuario  SERIAL PRIMARY KEY,
    id_edan_localidad BIGINT NOT NULL REFERENCES edan.edan_localidades(id_edan_localidad) ON DELETE CASCADE,
    especie           VARCHAR(100) NOT NULL DEFAULT '',
    id_especie        INT REFERENCES shared.pecuario(id),
    raza              VARCHAR(100) NOT NULL DEFAULT '',
    animales_afectados INT NOT NULL DEFAULT 0,
    animales_muertos  INT NOT NULL DEFAULT 0,
    necesidades_inmediatas TEXT NOT NULL DEFAULT ''
);

-- 5.12 Infraestructura productiva (1:N, dano_* son números)
CREATE TABLE IF NOT EXISTS edan.edan_localidades_infra_productiva (
    id_infra_productiva SERIAL PRIMARY KEY,
    id_edan_localidad BIGINT NOT NULL REFERENCES edan.edan_localidades(id_edan_localidad) ON DELETE CASCADE,
    tipo              VARCHAR(200) NOT NULL DEFAULT '',
    dano_parcial      INT NOT NULL DEFAULT 0,
    dano_total        INT NOT NULL DEFAULT 0
);

-- 5.13 Protección (1:1)
CREATE TABLE IF NOT EXISTS edan.edan_localidades_proteccion (
    id_edan_localidad BIGINT PRIMARY KEY REFERENCES edan.edan_localidades(id_edan_localidad) ON DELETE CASCADE
);

-- 5.13a Grupos vulnerables (1:N, 7 grupos fijos)
CREATE TABLE IF NOT EXISTS edan.edan_localidades_proteccion_grupos (
    id_grupo_vulnerable SERIAL PRIMARY KEY,
    id_edan_localidad BIGINT NOT NULL REFERENCES edan.edan_localidades(id_edan_localidad) ON DELETE CASCADE,
    grupo             VARCHAR(50) NOT NULL
        CHECK (grupo IN ('ninos','adolescentes','mujeres_lactantes','mujeres_embarazadas',
                         'adultos_mayores','personas_discapacidad','personas_enfermedad')),
    mujeres           INT NOT NULL DEFAULT 0,
    hombres           INT NOT NULL DEFAULT 0,
    apoyo_psicologico BOOLEAN,
    reposicion_documentos BOOLEAN,
    observaciones     TEXT NOT NULL DEFAULT '',
    UNIQUE (id_edan_localidad, grupo)
);

-- 5.14 Necesidades humanitarias (1:1)
CREATE TABLE IF NOT EXISTS edan.edan_localidades_necesidades_humanitarias (
    id_edan_localidad BIGINT PRIMARY KEY REFERENCES edan.edan_localidades(id_edan_localidad) ON DELETE CASCADE,
    alimentos         BOOLEAN NOT NULL DEFAULT FALSE,
    refugio_vivienda  BOOLEAN NOT NULL DEFAULT FALSE,
    ropa_cama         BOOLEAN NOT NULL DEFAULT FALSE,
    articulos_higiene BOOLEAN NOT NULL DEFAULT FALSE,
    articulos_cocina  BOOLEAN NOT NULL DEFAULT FALSE,
    prendas_vestir    BOOLEAN NOT NULL DEFAULT FALSE,
    herramientas      BOOLEAN NOT NULL DEFAULT FALSE,
    almacenamiento_agua BOOLEAN NOT NULL DEFAULT FALSE,
    banos             BOOLEAN NOT NULL DEFAULT FALSE,
    obs_alimentos     TEXT NOT NULL DEFAULT '',
    obs_refugio_vivienda TEXT NOT NULL DEFAULT '',
    obs_ropa_cama     TEXT NOT NULL DEFAULT '',
    obs_articulos_higiene TEXT NOT NULL DEFAULT '',
    obs_articulos_cocina TEXT NOT NULL DEFAULT '',
    obs_prendas_vestir TEXT NOT NULL DEFAULT '',
    obs_herramientas  TEXT NOT NULL DEFAULT '',
    obs_almacenamiento_agua TEXT NOT NULL DEFAULT '',
    obs_banos         TEXT NOT NULL DEFAULT ''
);

-- ---------------------------------------------------------------------------
-- 6. Índices recomendados
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_edan_usuario      ON edan.edan(id_usuario);
CREATE INDEX IF NOT EXISTS idx_edan_estado       ON edan.edan(estado);
CREATE INDEX IF NOT EXISTS idx_edan_sincronizado ON edan.edan(sincronizado) WHERE sincronizado = FALSE;
CREATE INDEX IF NOT EXISTS idx_edan_fecha_creacion ON edan.edan(fecha_creacion DESC);
CREATE INDEX IF NOT EXISTS idx_edan_provincia    ON edan.edan(id_provincia);
CREATE INDEX IF NOT EXISTS idx_edan_municipio2   ON edan.edan(id_municipio);
CREATE INDEX IF NOT EXISTS idx_edan_tipo_evento2 ON edan.edan(id_tipo_evento);
CREATE INDEX IF NOT EXISTS idx_edan_localidades_edan ON edan.edan_localidades(id_edan);
CREATE INDEX IF NOT EXISTS idx_edan_localidades_imp   ON edan.edan_localidades(imp_poblacion, imp_salud, imp_infraestructura);
CREATE INDEX IF NOT EXISTS idx_edan_grupo_detalle_localidad ON edan.edan_grupo_etario_detalle(id_edan_localidad);
CREATE INDEX IF NOT EXISTS idx_edan_agricultura_localidad ON edan.edan_localidades_danos_agricultura(id_edan_localidad);
CREATE INDEX IF NOT EXISTS idx_edan_agricultura_cultivo   ON edan.edan_localidades_danos_agricultura(id_cultivo);
CREATE INDEX IF NOT EXISTS idx_edan_pecuario_localidad    ON edan.edan_localidades_danos_pecuario(id_edan_localidad);
CREATE INDEX IF NOT EXISTS idx_edan_pecuario_especie      ON edan.edan_localidades_danos_pecuario(id_especie);
CREATE INDEX IF NOT EXISTS idx_edan_salud_localidad       ON edan.edan_localidades_salud_establecimientos(id_edan_localidad);
CREATE INDEX IF NOT EXISTS idx_edan_vial_localidad        ON edan.edan_localidades_danos_viales(id_edan_localidad);
CREATE INDEX IF NOT EXISTS idx_edan_infra_publica_local   ON edan.edan_localidades_danos_infra_publica(id_edan_localidad);
CREATE INDEX IF NOT EXISTS idx_edan_servicio_localidad    ON edan.edan_localidades_servicios_basicos(id_edan_localidad);
CREATE INDEX IF NOT EXISTS idx_edan_educacion_localidad   ON edan.edan_localidades_unidades_educativas(id_edan_localidad);
CREATE INDEX IF NOT EXISTS idx_edan_vivienda_localidad    ON edan.edan_localidades_danos_vivienda(id_edan_localidad);
CREATE INDEX IF NOT EXISTS idx_edan_infra_prod_localidad  ON edan.edan_localidades_infra_productiva(id_edan_localidad);
CREATE INDEX IF NOT EXISTS idx_edan_proteccion_grupo_local ON edan.edan_localidades_proteccion_grupos(id_edan_localidad);

-- ---------------------------------------------------------------------------
-- 7. DROP de tablas planas vacías + edan_comunidad + junction edan_tipo_evento
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS edan.edan_agricultura;
DROP TABLE IF EXISTS edan.edan_ayuda_humanitaria;
DROP TABLE IF EXISTS edan.edan_comunidad;
DROP TABLE IF EXISTS edan.edan_educacion_afectacion;
DROP TABLE IF EXISTS edan.edan_educacion_dano;
DROP TABLE IF EXISTS edan.edan_infraestructura_productiva;
DROP TABLE IF EXISTS edan.edan_infraestructura_publica;
DROP TABLE IF EXISTS edan.edan_infraestructura_vial;
DROP TABLE IF EXISTS edan.edan_pecuaria;
DROP TABLE IF EXISTS edan.edan_poblacion_grupo;
DROP TABLE IF EXISTS edan.edan_primera_respuesta;
DROP TABLE IF EXISTS edan.edan_proteccion;
DROP TABLE IF EXISTS edan.edan_salud_establecimiento;
DROP TABLE IF EXISTS edan.edan_salud_necesidades;
DROP TABLE IF EXISTS edan.edan_servicio_basico;
DROP TABLE IF EXISTS edan.edan_tipo_evento;
DROP TABLE IF EXISTS edan.edan_vivienda;

-- ---------------------------------------------------------------------------
-- 8. Backfill: 1 localidad por EDAN existente
-- ---------------------------------------------------------------------------
INSERT INTO edan.edan_localidades (id_edan, tipo_localidad, nombre)
SELECT e.id_edan, 'Comunidad', 'Sin especificar'
FROM edan.edan e
WHERE NOT EXISTS (
    SELECT 1 FROM edan.edan_localidades l WHERE l.id_edan = e.id_edan
);

COMMIT;
