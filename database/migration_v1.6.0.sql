-- ============================================================================
-- SINAGERSAT - Migración v1.6.0 (idempotente)
-- 1. edan_localidades.tipo_localidad: pasa de campo VARCHAR a catálogo
--    (tabla edan.tipo_localidad) con FK. Los datos existentes se migran por
--    nombre y la columna varchar se elimina.
-- 2. Nueva tabla edan.edan_localidades_estado (catálogo de estados de
--    localidad, mismo patrón que edan.estado_edan) con FK en edan_localidades.
-- Aplica sobre migration_v1.5.1.
-- ============================================================================

BEGIN;

-- 1. Catálogo: tipo de localidad (21 términos según definición del usuario)
CREATE TABLE IF NOT EXISTS edan.tipo_localidad (
    id_tipo_localidad  integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre             varchar(50)  NOT NULL UNIQUE,
    descripcion        text,
    orden              integer      NOT NULL DEFAULT 0
);

INSERT INTO edan.tipo_localidad (nombre, descripcion, orden) VALUES
    ('Localidad',        'Lugar poblado o asentamiento',                                                                1),
    ('Comunidad',        'Asentamiento y/o unidad social rural',                                                        2),
    ('Comunidad indígena','Comunidad perteneciente a un pueblo indígena',                                               3),
    ('Comunidad campesina','Comunidad organizada de población campesina',                                               4),
    ('Ayllu',            'Organización territorial/social indígena originaria',                                         5),
    ('Marka',            'Agrupación territorial de ayllus',                                                            6),
    ('TIOC',             'Territorio Indígena Originario Campesino',                                                   7),
    ('TCO',              'Tierra Comunitaria de Origen',                                                               8),
    ('OTB',              'Organización Territorial de Base',                                                           9),
    ('Distrito municipal','Subdivisión territorial de un municipio',                                                   10),
    ('Distrito indígena originario campesino','Distrito conformado considerando una organización indígena originaria campesina',11),
    ('Barrio',           'Sector poblado urbano',                                                                       12),
    ('Zona',             'Sector de un área urbana o poblada',                                                         13),
    ('Centro poblado',   'Concentración de población',                                                                  14),
    ('Pueblo indígena',  'Población organizada alrededor de una identidad indígena',                                    15),
    ('Capitanía',        'Organización territorial/social de pueblos indígenas',                                        16),
    ('Cabildo',          'Forma de organización/autoridad comunitaria',                                                 17),
    ('Sindicato agrario','Organización social campesina',                                                               18),
    ('Subcentral',       'Agrupación de comunidades/sindicatos',                                                       19),
    ('Central agraria',  'Organización que agrupa comunidades o sindicatos',                                            20),
    ('Territorio indígena','Territorio reconocido a un pueblo/nación indígena',                                         21)
ON CONFLICT (nombre) DO UPDATE SET descripcion = EXCLUDED.descripcion, orden = EXCLUDED.orden;

-- 2. Catálogo: estado de localidad (mismo patrón que edan.estado_edan)
CREATE TABLE IF NOT EXISTS edan.edan_localidades_estado (
    id_edan_localidad_estado integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre             varchar(50)  NOT NULL UNIQUE,
    descripcion        text,
    orden              integer      NOT NULL DEFAULT 0
);

INSERT INTO edan.edan_localidades_estado (nombre, descripcion, orden) VALUES
    ('borrador',  'Borrador inicial',                            1),
    ('enviado',   'Formulario enviado al servidor',              2),
    ('aprobado',  'Formulario aprobado',                         3),
    ('rechazado', 'Formulario rechazado',                        4),
    ('cerrado',   'Formulario cerrado',                          5)
ON CONFLICT (nombre) DO UPDATE SET descripcion = EXCLUDED.descripcion, orden = EXCLUDED.orden;

-- 3. edan_localidades: nueva columna FK de tipo de localidad
ALTER TABLE edan.edan_localidades ADD COLUMN IF NOT EXISTS id_tipo_localidad integer;

-- 3.1 Backfill desde el varchar (por nombre) y eliminación del campo
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'edan' AND table_name = 'edan_localidades'
          AND column_name = 'tipo_localidad'
    ) THEN
        UPDATE edan.edan_localidades l
        SET id_tipo_localidad = t.id_tipo_localidad
        FROM edan.tipo_localidad t
        WHERE t.nombre = l.tipo_localidad AND l.id_tipo_localidad IS NULL;

        ALTER TABLE edan.edan_localidades DROP COLUMN tipo_localidad;
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'edan_localidades_id_tipo_localidad_fkey') THEN
        ALTER TABLE edan.edan_localidades
            ADD CONSTRAINT edan_localidades_id_tipo_localidad_fkey
            FOREIGN KEY (id_tipo_localidad) REFERENCES edan.tipo_localidad(id_tipo_localidad)
            ON DELETE SET NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_edan_localidades_tipo ON edan.edan_localidades(id_tipo_localidad);

-- 4. edan_localidades: nueva columna FK de estado de localidad
ALTER TABLE edan.edan_localidades ADD COLUMN IF NOT EXISTS id_edan_localidad_estado integer;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'edan_localidades_id_edan_localidad_estado_fkey') THEN
        ALTER TABLE edan.edan_localidades
            ADD CONSTRAINT edan_localidades_id_edan_localidad_estado_fkey
            FOREIGN KEY (id_edan_localidad_estado) REFERENCES edan.edan_localidades_estado(id_edan_localidad_estado)
            ON DELETE SET NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_edan_localidades_estado ON edan.edan_localidades(id_edan_localidad_estado);

COMMIT;

SELECT 'IDEMPOTENT OK v1.6.0' AS resultado;
