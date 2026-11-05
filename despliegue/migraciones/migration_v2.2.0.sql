-- ============================================================================
-- SINAGERSAT - Migración v2.2.0 (idempotente)
-- Consolidación del modelo de la localidad: las secciones 3.2 (Impacto en la
-- Población) y 10.1 (Necesidades de Protección) quedan en UNA tabla 1:N cada
-- una, eliminando el patrón redundante "cabecera 1:1 + detalle 1:N":
--
--   1. edan.edan_localidades_impacto_poblacion  (1:1 → 1:N)
--      Absorbe las filas de edan_grupo_etario_detalle; renombra grupo_etario
--      → rango; elimina la fila 'TOTAL' (derivable como suma del detalle).
--      Se elimina edan_grupo_etario_detalle.
--
--   2. edan.edan_localidades_proteccion  (1:1 → 1:N)
--      Absorbe las filas de edan_localidades_proteccion_grupos (grupo,
--      mujeres, hombres, apoyo_psicologico, reposicion_documentos,
--      observaciones) + columna nueva `necesidad`.
--      Se elimina edan_localidades_proteccion_grupos.
--
-- Aplica sobre migration_v2.1.0.
-- NOTA: la API (api/edan/service.py) debe adaptarse en una etapa posterior;
-- todavía referencia las tablas de detalle que aquí se eliminan.
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. edan_localidades_impacto_poblacion (1:1 → 1:N)
-- ============================================================================

-- Secuencia para la nueva PK serial
CREATE SEQUENCE IF NOT EXISTS edan.edan_localidades_impacto_poblacion_id_impacto_poblacion_seq;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'edan' AND table_name = 'edan_grupo_etario_detalle'
    ) THEN
        -- 1a. Nueva columna PK + renombrar grupo_etario → rango
        ALTER TABLE edan.edan_localidades_impacto_poblacion
            ADD COLUMN IF NOT EXISTS id_impacto_poblacion integer;
        ALTER TABLE edan.edan_localidades_impacto_poblacion
            ALTER COLUMN id_impacto_poblacion
            SET DEFAULT nextval('edan.edan_localidades_impacto_poblacion_id_impacto_poblacion_seq');
        ALTER TABLE edan.edan_localidades_impacto_poblacion
            RENAME COLUMN grupo_etario TO rango;

        -- 1b. Quitar la PK antigua (id_edan_localidad, 1:1) ANTES del backfill
        ALTER TABLE edan.edan_localidades_impacto_poblacion
            DROP CONSTRAINT IF EXISTS edan_localidades_impacto_poblacion_pkey;

        -- 1c. Backfill desde edan_grupo_etario_detalle (los datos reales)
        INSERT INTO edan.edan_localidades_impacto_poblacion
            (id_edan_localidad, rango, fallecidos, heridos, desaparecidos, observaciones)
        SELECT id_edan_localidad, rango, fallecidos, heridos, desaparecidos, observaciones
        FROM edan.edan_grupo_etario_detalle;

        -- 1d. Eliminar filas 1:1 preexistentes (resumen 'TOTAL'/marcador vacío,
        --     id_impacto_poblacion NULL) — la suma es derivable del detalle
        DELETE FROM edan.edan_localidades_impacto_poblacion
        WHERE id_impacto_poblacion IS NULL;

        -- 1e. Nueva PK serial
        ALTER TABLE edan.edan_localidades_impacto_poblacion
            ALTER COLUMN id_impacto_poblacion SET NOT NULL;
        ALTER TABLE edan.edan_localidades_impacto_poblacion
            ADD CONSTRAINT edan_localidades_impacto_poblacion_pkey
            PRIMARY KEY (id_impacto_poblacion);

        -- 1f. Índice por localidad
        CREATE INDEX IF NOT EXISTS idx_edan_impacto_poblacion_localidad
            ON edan.edan_localidades_impacto_poblacion (id_edan_localidad);

        -- 1g. Eliminar la tabla de detalle absorbida
        DROP TABLE edan.edan_grupo_etario_detalle;
    END IF;
END $$;

-- ============================================================================
-- 2. edan_localidades_proteccion (1:1 → 1:N)
-- ============================================================================

-- Secuencia para la nueva PK serial
CREATE SEQUENCE IF NOT EXISTS edan.edan_localidades_proteccion_id_grupo_vulnerable_seq;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'edan' AND table_name = 'edan_localidades_proteccion_grupos'
    ) THEN
        -- 2a. Nueva columna PK + columnas de detalle de grupos vulnerables
        ALTER TABLE edan.edan_localidades_proteccion
            ADD COLUMN IF NOT EXISTS id_grupo_vulnerable integer,
            ADD COLUMN IF NOT EXISTS grupo                 character varying(50) NOT NULL DEFAULT '',
            ADD COLUMN IF NOT EXISTS mujeres               integer NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS hombres               integer NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS apoyo_psicologico     boolean,
            ADD COLUMN IF NOT EXISTS reposicion_documentos boolean,
            ADD COLUMN IF NOT EXISTS necesidad             text,
            ADD COLUMN IF NOT EXISTS observaciones         text NOT NULL DEFAULT '';

        ALTER TABLE edan.edan_localidades_proteccion
            ALTER COLUMN id_grupo_vulnerable
            SET DEFAULT nextval('edan.edan_localidades_proteccion_id_grupo_vulnerable_seq');

        -- 2b. Quitar la PK antigua (id_edan_localidad, 1:1) ANTES del backfill
        ALTER TABLE edan.edan_localidades_proteccion
            DROP CONSTRAINT IF EXISTS edan_localidades_proteccion_pkey;

        -- 2c. Backfill desde edan_localidades_proteccion_grupos
        INSERT INTO edan.edan_localidades_proteccion
            (id_edan_localidad, grupo, mujeres, hombres,
             apoyo_psicologico, reposicion_documentos, observaciones)
        SELECT id_edan_localidad, grupo, mujeres, hombres,
               apoyo_psicologico, reposicion_documentos, observaciones
        FROM edan.edan_localidades_proteccion_grupos;

        -- 2d. Eliminar filas marcador 1:1 preexistentes (grupo vacío)
        DELETE FROM edan.edan_localidades_proteccion WHERE grupo = '';

        -- 2e. Nueva PK serial
        ALTER TABLE edan.edan_localidades_proteccion
            ALTER COLUMN id_grupo_vulnerable SET NOT NULL;
        ALTER TABLE edan.edan_localidades_proteccion
            ADD CONSTRAINT edan_localidades_proteccion_pkey
            PRIMARY KEY (id_grupo_vulnerable);

        -- 2f. Restricciones preservadas del detalle original
        ALTER TABLE edan.edan_localidades_proteccion
            ADD CONSTRAINT edan_localidades_proteccion_grupo_check
            CHECK (grupo IN ('ninos', 'adolescentes', 'mujeres_lactantes',
                             'mujeres_embarazadas', 'adultos_mayores',
                             'personas_discapacidad', 'personas_enfermedad'));

        ALTER TABLE edan.edan_localidades_proteccion
            ADD CONSTRAINT edan_localidades_proteccion_id_edan_localidad_grupo_key
            UNIQUE (id_edan_localidad, grupo);

        CREATE INDEX IF NOT EXISTS idx_edan_proteccion_local
            ON edan.edan_localidades_proteccion (id_edan_localidad);

        -- 2f. Eliminar la tabla de detalle absorbida
        DROP TABLE edan.edan_localidades_proteccion_grupos;
    END IF;
END $$;

COMMIT;

SELECT 'IDEMPOTENT OK v2.2.0' AS resultado;
