-- ============================================================================
-- SINAGERSAT - Migración v2.49.0 (idempotente)
-- EDAN: identidad permanente por UUID (Fase 1: solo BD, sin tocar APIs)
--
--   Contexto: un mismo formulario debe tener la MISMA identidad en la app
--   Flutter, en la web y en el servidor, sin importar dónde se cree o cuántas
--   veces se sincronice. Hoy la identidad "de cliente" es `id_local` (varchar,
--   97/124 UUIDs válidos, 27 con formato raro) y las filas de sección usan
--   `id_seccion`; los IDs numéricos serial son internos del servidor.
--
--   Esta migración AÑADE (nada se renombra ni se elimina):
--     edan.edan_localidades.uuid_edan_localidad  -> identidad de la cabecera
--     edan.edan.uuid_edan                        -> identidad del EDAN consolidado
--     uuid_registro en las 14 tablas de sección  -> identidad de cada fila
--
--   Reglas de asignación (transición):
--   * Cabeceras: si `id_local` es un UUID válido, uuid := id_local::uuid (la
--     identidad que generó el móvil se conserva tal cual); si no, gen_random_uuid().
--     El trigger también cubre el patrón de la API vieja que inserta la fila y
--     manda `id_local` en un segundo UPDATE.
--   * Filas de sección: si el cliente envía `uuid_registro` (flujo nuevo) se
--     respeta; si viene NULL (API vieja) se deriva DETERMINÍSTICAMENTE de
--     md5(tabla|clave): id_edan_localidad en las 1:1 (PK de la tabla) y
--     id_seccion en las 1:N (id_seccion es único por tabla). Así el patrón
--     DELETE+INSERT del sync viejo NO genera un uuid nuevo por sincronización
--     (regla: "no crear un UUID nuevo cada vez que un registro se sincroniza").
--   * uuid_registro es INMUTABLE una vez asignado (BEFORE UPDATE lo restaura).
--
--   No se tocan: columnas id_local/id_seccion, índices únicos globales
--   idx_seccion_* (carga de los 15 `ON CONFLICT (id_seccion)` de la API actual),
--   columnas fotografia, flags pendiente_* ni el LWW por fecha_modificacion.
--
--   IDEMPOTENCIA: ADD COLUMN IF NOT EXISTS + DROP TRIGGER IF EXISTS +
--   CREATE OR REPLACE FUNCTION + backfill WHERE ... IS NULL + CREATE UNIQUE
--   INDEX IF NOT EXISTS. Se puede aplicar N veces.
--
--   Respaldo previo: backups/pre_v2.49.0_edan_uuid_*.sql (+ backup completo
--   database/backup_2026_10_10_*.sql)
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. Columnas de identidad (aditivas, SIN DEFAULT: las asignan los triggers)
-- ----------------------------------------------------------------------------
ALTER TABLE edan.edan_localidades ADD COLUMN IF NOT EXISTS uuid_edan_localidad uuid;
ALTER TABLE edan.edan             ADD COLUMN IF NOT EXISTS uuid_edan          uuid;

ALTER TABLE edan.edan_localidades_danos_agricultura     ADD COLUMN IF NOT EXISTS uuid_registro uuid;
ALTER TABLE edan.edan_localidades_danos_infra_publica   ADD COLUMN IF NOT EXISTS uuid_registro uuid;
ALTER TABLE edan.edan_localidades_danos_pecuario        ADD COLUMN IF NOT EXISTS uuid_registro uuid;
ALTER TABLE edan.edan_localidades_danos_viales          ADD COLUMN IF NOT EXISTS uuid_registro uuid;
ALTER TABLE edan.edan_localidades_danos_vivienda        ADD COLUMN IF NOT EXISTS uuid_registro uuid;
ALTER TABLE edan.edan_localidades_impacto_poblacion     ADD COLUMN IF NOT EXISTS uuid_registro uuid;
ALTER TABLE edan.edan_localidades_infra_productiva      ADD COLUMN IF NOT EXISTS uuid_registro uuid;
ALTER TABLE edan.edan_localidades_necesidades_humanitarias ADD COLUMN IF NOT EXISTS uuid_registro uuid;
ALTER TABLE edan.edan_localidades_primera_respuesta     ADD COLUMN IF NOT EXISTS uuid_registro uuid;
ALTER TABLE edan.edan_localidades_proteccion            ADD COLUMN IF NOT EXISTS uuid_registro uuid;
ALTER TABLE edan.edan_localidades_salud_establecimientos ADD COLUMN IF NOT EXISTS uuid_registro uuid;
ALTER TABLE edan.edan_localidades_salud_necesidades     ADD COLUMN IF NOT EXISTS uuid_registro uuid;
ALTER TABLE edan.edan_localidades_servicios_basicos    ADD COLUMN IF NOT EXISTS uuid_registro uuid;
ALTER TABLE edan.edan_localidades_unidades_educativas  ADD COLUMN IF NOT EXISTS uuid_registro uuid;

-- ----------------------------------------------------------------------------
-- 2. Funciones de derivación y triggers de identidad
-- ----------------------------------------------------------------------------
-- Derivación determinística de uuid_registro (usada por el trigger y por el
-- backfill, para que ambos produzcan exactamente el mismo valor).
CREATE OR REPLACE FUNCTION edan.fn_derivar_uuid_registro(
    p_tabla        text,
    p_id_seccion   text,
    p_id_localidad bigint,
    p_es_11        boolean
) RETURNS uuid LANGUAGE plpgsql AS $$
BEGIN
    IF p_es_11 THEN
        -- 1:1: la clave estable es la localidad (PK de la tabla)
        RETURN md5(p_tabla || '|' || p_id_localidad::text)::uuid;
    END IF;
    -- 1:N: id_seccion es único global por tabla -> uuid determinístico único
    IF p_id_seccion IS NOT NULL THEN
        RETURN md5(p_tabla || '|' || p_id_seccion)::uuid;
    END IF;
    -- 1:N sin id_seccion (no debería ocurrir): identidad nueva
    RETURN gen_random_uuid();
END;
$$;

COMMENT ON FUNCTION edan.fn_derivar_uuid_registro(text, text, bigint, boolean) IS
    'Deriva el uuid_registro de una fila de sección EDAN de forma determinística (tabla+clave). No criptográfico: solo garantiza determinismo y unicidad por (tabla, clave).';

-- Cabecera: uuid desde id_local cuando es UUID válido.
CREATE OR REPLACE FUNCTION edan.fn_uuid_edan_localidad() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        IF NEW.uuid_edan_localidad IS NULL THEN
            NEW.uuid_edan_localidad := CASE
                WHEN NEW.id_local ~ '^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
                    THEN NEW.id_local::uuid
                ELSE gen_random_uuid()
            END;
        END IF;
    ELSE
        -- La API vieja inserta y luego asigna id_local en un UPDATE: al cambiar
        -- id_local a un UUID válido, la identidad del móvil pasa a ser la del servidor.
        IF NEW.id_local IS DISTINCT FROM OLD.id_local
           AND NEW.id_local ~ '^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$' THEN
            NEW.uuid_edan_localidad := NEW.id_local::uuid;
        ELSIF NEW.uuid_edan_localidad IS NULL THEN
            NEW.uuid_edan_localidad := CASE
                WHEN NEW.id_local ~ '^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
                    THEN NEW.id_local::uuid
                ELSE gen_random_uuid()
            END;
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

-- EDAN consolidado: misma regla (id_local suele ser NULL -> gen_random).
CREATE OR REPLACE FUNCTION edan.fn_uuid_edan() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        IF NEW.uuid_edan IS NULL THEN
            NEW.uuid_edan := CASE
                WHEN NEW.id_local ~ '^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
                    THEN NEW.id_local::uuid
                ELSE gen_random_uuid()
            END;
        END IF;
    ELSE
        IF NEW.id_local IS DISTINCT FROM OLD.id_local
           AND NEW.id_local ~ '^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$' THEN
            NEW.uuid_edan := NEW.id_local::uuid;
        ELSIF NEW.uuid_edan IS NULL THEN
            NEW.uuid_edan := gen_random_uuid();
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

-- Filas de sección: respeta uuid del cliente; si es NULL deriva determinístico;
-- una vez asignado es inmutable.
CREATE OR REPLACE FUNCTION edan.fn_uuid_registro() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        IF OLD.uuid_registro IS NOT NULL
           AND NEW.uuid_registro IS DISTINCT FROM OLD.uuid_registro THEN
            NEW.uuid_registro := OLD.uuid_registro;
        END IF;
        RETURN NEW;
    END IF;
    -- INSERT
    IF NEW.uuid_registro IS NULL THEN
        NEW.uuid_registro := edan.fn_derivar_uuid_registro(
            TG_TABLE_NAME, NEW.id_seccion, NEW.id_edan_localidad,
            (TG_ARGV[0] = '11'));
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_uuid_edan_localidad ON edan.edan_localidades;
CREATE TRIGGER trg_uuid_edan_localidad
    BEFORE INSERT OR UPDATE ON edan.edan_localidades
    FOR EACH ROW EXECUTE FUNCTION edan.fn_uuid_edan_localidad();

DROP TRIGGER IF EXISTS trg_uuid_edan ON edan.edan;
CREATE TRIGGER trg_uuid_edan
    BEFORE INSERT OR UPDATE ON edan.edan
    FOR EACH ROW EXECUTE FUNCTION edan.fn_uuid_edan();

-- ----------------------------------------------------------------------------
-- 3. Secciones (14): triggers + backfill + SET NOT NULL + comentarios
--    (es_11 = tabla 1:1 con PK id_edan_localidad)
-- ----------------------------------------------------------------------------
DO $$
DECLARE
    t record;
BEGIN
    FOR t IN
        SELECT * FROM (VALUES
            ('edan_localidades_danos_agricultura',      false),
            ('edan_localidades_danos_infra_publica',    false),
            ('edan_localidades_danos_pecuario',         false),
            ('edan_localidades_danos_viales',           false),
            ('edan_localidades_danos_vivienda',         false),
            ('edan_localidades_impacto_poblacion',      false),
            ('edan_localidades_infra_productiva',       false),
            ('edan_localidades_proteccion',             false),
            ('edan_localidades_salud_establecimientos', false),
            ('edan_localidades_servicios_basicos',      false),
            ('edan_localidades_unidades_educativas',    false),
            ('edan_localidades_necesidades_humanitarias', true),
            ('edan_localidades_primera_respuesta',      true),
            ('edan_localidades_salud_necesidades',      true)
        ) AS v(tabla, es_11)
    LOOP
        EXECUTE format(
            'DROP TRIGGER IF EXISTS trg_uuid_registro ON edan.%I', t.tabla);
        EXECUTE format(
            'CREATE TRIGGER trg_uuid_registro BEFORE INSERT OR UPDATE ON edan.%I'
            || ' FOR EACH ROW EXECUTE FUNCTION edan.fn_uuid_registro(%L)',
            t.tabla, CASE WHEN t.es_11 THEN '11' ELSE '1n' END);
        EXECUTE format(
            'UPDATE edan.%I SET uuid_registro ='
            || ' edan.fn_derivar_uuid_registro(%L, id_seccion, id_edan_localidad, %L)'
            || ' WHERE uuid_registro IS NULL',
            t.tabla, t.tabla, t.es_11);
        EXECUTE format(
            'ALTER TABLE edan.%I ALTER COLUMN uuid_registro SET NOT NULL', t.tabla);
        EXECUTE format(
            'COMMENT ON COLUMN edan.%I.uuid_registro IS %L',
            t.tabla,
            'Identidad permanente de la fila de sección (generada por el cliente en el flujo nuevo; determinística desde id_seccion/id_edan_localidad en la transición). Inmutable: no cambia entre sincronizaciones.');
    END LOOP;
END $$;

-- ----------------------------------------------------------------------------
-- 4. Backfill de cabeceras (id_local válido -> uuid = id_local)
-- ----------------------------------------------------------------------------
UPDATE edan.edan_localidades
SET uuid_edan_localidad = CASE
    WHEN id_local ~ '^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
        THEN id_local::uuid
    ELSE gen_random_uuid()
END
WHERE uuid_edan_localidad IS NULL;

UPDATE edan.edan
SET uuid_edan = CASE
    WHEN id_local ~ '^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
        THEN id_local::uuid
    ELSE gen_random_uuid()
END
WHERE uuid_edan IS NULL;

ALTER TABLE edan.edan_localidades ALTER COLUMN uuid_edan_localidad SET NOT NULL;
ALTER TABLE edan.edan             ALTER COLUMN uuid_edan          SET NOT NULL;

-- ----------------------------------------------------------------------------
-- 5. Índices únicos (clave de upsert idempotente de las APIs futuras)
-- ----------------------------------------------------------------------------
CREATE UNIQUE INDEX IF NOT EXISTS uq_edan_localidades_uuid
    ON edan.edan_localidades (uuid_edan_localidad);
CREATE UNIQUE INDEX IF NOT EXISTS uq_edan_uuid
    ON edan.edan (uuid_edan);

CREATE UNIQUE INDEX IF NOT EXISTS uq_danos_agricultura_uuid
    ON edan.edan_localidades_danos_agricultura (uuid_registro);
CREATE UNIQUE INDEX IF NOT EXISTS uq_danos_infra_publica_uuid
    ON edan.edan_localidades_danos_infra_publica (uuid_registro);
CREATE UNIQUE INDEX IF NOT EXISTS uq_danos_pecuario_uuid
    ON edan.edan_localidades_danos_pecuario (uuid_registro);
CREATE UNIQUE INDEX IF NOT EXISTS uq_danos_viales_uuid
    ON edan.edan_localidades_danos_viales (uuid_registro);
CREATE UNIQUE INDEX IF NOT EXISTS uq_danos_vivienda_uuid
    ON edan.edan_localidades_danos_vivienda (uuid_registro);
CREATE UNIQUE INDEX IF NOT EXISTS uq_impacto_poblacion_uuid
    ON edan.edan_localidades_impacto_poblacion (uuid_registro);
CREATE UNIQUE INDEX IF NOT EXISTS uq_infra_productiva_uuid
    ON edan.edan_localidades_infra_productiva (uuid_registro);
CREATE UNIQUE INDEX IF NOT EXISTS uq_necesidades_humanitarias_uuid
    ON edan.edan_localidades_necesidades_humanitarias (uuid_registro);
CREATE UNIQUE INDEX IF NOT EXISTS uq_primera_respuesta_uuid
    ON edan.edan_localidades_primera_respuesta (uuid_registro);
CREATE UNIQUE INDEX IF NOT EXISTS uq_proteccion_uuid
    ON edan.edan_localidades_proteccion (uuid_registro);
CREATE UNIQUE INDEX IF NOT EXISTS uq_salud_establecimientos_uuid
    ON edan.edan_localidades_salud_establecimientos (uuid_registro);
CREATE UNIQUE INDEX IF NOT EXISTS uq_salud_necesidades_uuid
    ON edan.edan_localidades_salud_necesidades (uuid_registro);
CREATE UNIQUE INDEX IF NOT EXISTS uq_servicios_basicos_uuid
    ON edan.edan_localidades_servicios_basicos (uuid_registro);
CREATE UNIQUE INDEX IF NOT EXISTS uq_unidades_educativas_uuid
    ON edan.edan_localidades_unidades_educativas (uuid_registro);

-- ----------------------------------------------------------------------------
-- 6. Comentarios de cabecera
-- ----------------------------------------------------------------------------
COMMENT ON COLUMN edan.edan_localidades.uuid_edan_localidad IS
    'Identidad permanente del formulario (app/web/servidor). En transición igual a id_local cuando id_local es UUID válido; id_local se conserva como clave legacy de las APIs actuales.';
COMMENT ON COLUMN edan.edan.uuid_edan IS
    'Identidad permanente del EDAN consolidado. id_local se conserva como columna legacy (hoy NULL en las 5 filas existentes).';

COMMIT;
SELECT 'IDEMPOTENT OK v2.49.0 edan identidad uuid';
