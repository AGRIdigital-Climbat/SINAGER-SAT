-- ============================================================================
-- SINAGERSAT - Migración v2.52.0 (idempotente)
-- EDAN: llaves foráneas por UUID (espejo) + id_seccion sintético (Fase 1/2)
--
--   Contexto: las APIs nuevas (Fase 2, ver PLAN_APIS_V2_EDAN.md) trabajan SOLO
--   con uuid: el POST/PUT manda uuid y el GET consulta por uuid o id. Para que
--   ese vínculo padre→hijo viaje y se valide en la BD (y no solo en la capa de
--   servicio), las tablas hijas ahora cargan también el uuid del padre:
--
--     edan.edan_localidades.uuid_edan           -> FK -> edan.edan(uuid_edan)
--                                                  ON DELETE SET NULL (espejo de id_edan)
--     14 secciones.uuid_edan_localidad          -> FK -> edan.edan_localidades(uuid_edan_localidad)
--                                                  ON DELETE CASCADE (espejo de id_edan_localidad)
--
--   Regla de espejo: la FUENTE DE VERDAD sigue siendo el id numérico (la API
--   vieja no se toca). Un trigger BEFORE INSERT/UPDATE deriva el uuid del padre
--   desde el id; si el padre no existe aún (borrado en curso) el espejo queda
--   NULL y el FK numérico es quien da el error definitivo.
--
--   Además se REFUERZA edan.fn_derivar_uuid_registro: si `id_seccion` es un
--   UUID puro (formato sintético que usará el flujo nuevo: id_seccion :=
--   uuid_registro::text) se usa directo como uuid_registro. Así, si la app
--   vieja borra y reinserta una fila (patrón DELETE+INSERT del sync), la
--   identidad se rederiva IDÉNTICA. Verificado en los datos actuales: 0 filas
--   existentes tienen id_seccion en formato UUID puro -> nada cambia de valor.
--
--   No se tocan: columnas id_local/id_seccion, índices idx_seccion_*, la API
--   de código ni las reglas LWW/version ya instaladas (v2.49–v2.51).
--
--   IDEMPOTENCIA: ADD COLUMN IF NOT EXISTS + CREATE OR REPLACE FUNCTION +
--   DROP/CREATE TRIGGER IF EXISTS + DO ... IF NOT EXISTS en constraints +
--   CREATE INDEX IF NOT EXISTS. Se puede aplicar N veces.
--
--   Respaldo previo: backups/pre_v2.49.0_edan_uuid_*.sql (y backup completo
--   database/backup_2026_10_10_042635.sql)
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. Columna espejo en la cabecera de localidades
-- ----------------------------------------------------------------------------
ALTER TABLE edan.edan_localidades ADD COLUMN IF NOT EXISTS uuid_edan uuid;

-- ----------------------------------------------------------------------------
-- 2. Espejo localidades -> edan
--    Si el padre no existe (borrado en curso u origen desconocido) el espejo
--    queda NULL: el FK numérico `id_edan` sigue siendo quien valida de verdad.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION edan.fn_espejo_uuid_edan() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    v uuid;
BEGIN
    IF NEW.id_edan IS NULL THEN
        NEW.uuid_edan := NULL;
    ELSE
        SELECT e.uuid_edan INTO v FROM edan.edan e WHERE e.id_edan = NEW.id_edan;
        NEW.uuid_edan := v;   -- NULL si el padre no existe (no estorbar al FK numérico)
    END IF;
    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION edan.fn_espejo_uuid_edan() IS
    'BEFORE INSERT/UPDATE en edan_localidades: uuid_edan es espejo de id_edan (fuente de verdad numérica). Mantiene coherente el vínculo para las APIs nuevas (solo uuid).';

DROP TRIGGER IF EXISTS trg_espejo_uuid_edan ON edan.edan_localidades;
CREATE TRIGGER trg_espejo_uuid_edan
    BEFORE INSERT OR UPDATE ON edan.edan_localidades
    FOR EACH ROW EXECUTE FUNCTION edan.fn_espejo_uuid_edan();

-- Backfill de las localidades consolidadas (las 7 con id_edan NOT NULL)
UPDATE edan.edan_localidades l
SET uuid_edan = e.uuid_edan
FROM edan.edan e
WHERE e.id_edan = l.id_edan
  AND l.uuid_edan IS DISTINCT FROM e.uuid_edan;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'edan_localidades_uuid_edan_fk'
          AND conrelid = 'edan.edan_localidades'::regclass
    ) THEN
        ALTER TABLE edan.edan_localidades
            ADD CONSTRAINT edan_localidades_uuid_edan_fk
            FOREIGN KEY (uuid_edan) REFERENCES edan.edan (uuid_edan)
            ON DELETE SET NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_edan_localidades_uuid_edan
    ON edan.edan_localidades (uuid_edan);

COMMENT ON COLUMN edan.edan_localidades.uuid_edan IS
    'Espejo del vínculo con la cabecera EDAN (id_edan es la fuente de verdad). FK -> edan.edan(uuid_edan) ON DELETE SET NULL; lo mantiene trg_espejo_uuid_edan; las APIs nuevas enlazan por aquí.';

-- ----------------------------------------------------------------------------
-- 3. Espejo secciones -> localidad (14 tablas)
--    Si la localidad no existe se lanza un error claro (la fila no es
--    insertable sin padre: el FK numérico también lo impediría).
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION edan.fn_espejo_uuid_localidad() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    v uuid;
BEGIN
    SELECT l.uuid_edan_localidad INTO v
    FROM edan.edan_localidades l
    WHERE l.id_edan_localidad = NEW.id_edan_localidad;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'No existe la localidad id_edan_localidad=% (no se puede asignar uuid_edan_localidad)',
            NEW.id_edan_localidad;
    END IF;

    NEW.uuid_edan_localidad := v;
    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION edan.fn_espejo_uuid_localidad() IS
    'BEFORE INSERT/UPDATE en las 14 secciones: uuid_edan_localidad es espejo de id_edan_localidad (fuente de verdad numérica) y apunta a edan_localidades.uuid_edan_localidad.';

DO $$
DECLARE
    t record;
    v_fk text;
    v_idx text;
BEGIN
    FOR t IN
        SELECT * FROM (VALUES
            ('edan_localidades_danos_agricultura',      'danos_agricultura'),
            ('edan_localidades_danos_infra_publica',    'danos_infra_publica'),
            ('edan_localidades_danos_pecuario',         'danos_pecuario'),
            ('edan_localidades_danos_viales',           'danos_viales'),
            ('edan_localidades_danos_vivienda',         'danos_vivienda'),
            ('edan_localidades_impacto_poblacion',      'impacto_poblacion'),
            ('edan_localidades_infra_productiva',       'infra_productiva'),
            ('edan_localidades_necesidades_humanitarias', 'necesidades_humanitarias'),
            ('edan_localidades_primera_respuesta',      'primera_respuesta'),
            ('edan_localidades_proteccion',             'proteccion'),
            ('edan_localidades_salud_establecimientos', 'salud_establecimientos'),
            ('edan_localidades_salud_necesidades',      'salud_necesidades'),
            ('edan_localidades_servicios_basicos',      'servicios_basicos'),
            ('edan_localidades_unidades_educativas',    'unidades_educativas')
        ) AS v(tabla, corto)
    LOOP
        EXECUTE format(
            'ALTER TABLE edan.%I ADD COLUMN IF NOT EXISTS uuid_edan_localidad uuid',
            t.tabla);

        EXECUTE format(
            'DROP TRIGGER IF EXISTS trg_espejo_uuid_localidad ON edan.%I', t.tabla);
        EXECUTE format(
            'CREATE TRIGGER trg_espejo_uuid_localidad BEFORE INSERT OR UPDATE ON edan.%I'
            || ' FOR EACH ROW EXECUTE FUNCTION edan.fn_espejo_uuid_localidad()',
            t.tabla);

        EXECUTE format(
            'UPDATE edan.%I t SET uuid_edan_localidad = l.uuid_edan_localidad'
            || ' FROM edan.edan_localidades l'
            || ' WHERE l.id_edan_localidad = t.id_edan_localidad'
            || '   AND t.uuid_edan_localidad IS DISTINCT FROM l.uuid_edan_localidad',
            t.tabla);

        EXECUTE format(
            'ALTER TABLE edan.%I ALTER COLUMN uuid_edan_localidad SET NOT NULL',
            t.tabla);

        v_fk := format('fk_%s_uuid_edan_localidad', t.corto);
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint
            WHERE conname = v_fk
              AND conrelid = format('edan.%I', t.tabla)::regclass
        ) THEN
            EXECUTE format(
                'ALTER TABLE edan.%I ADD CONSTRAINT %I'
                || ' FOREIGN KEY (uuid_edan_localidad)'
                || ' REFERENCES edan.edan_localidades (uuid_edan_localidad)'
                || ' ON DELETE CASCADE',
                t.tabla, v_fk);
        END IF;

        v_idx := format('idx_%s_uuid_edan_localidad', t.corto);
        EXECUTE format(
            'CREATE INDEX IF NOT EXISTS %I ON edan.%I (uuid_edan_localidad)',
            v_idx, t.tabla);

        EXECUTE format(
            'COMMENT ON COLUMN edan.%I.uuid_edan_localidad IS %L',
            t.tabla,
            'Espejo del vínculo con la localidad (id_edan_localidad es la fuente de verdad). FK -> edan_localidades(uuid_edan_localidad) ON DELETE CASCADE; lo mantiene trg_espejo_uuid_localidad; las APIs nuevas enlazan por aquí.');
    END LOOP;
END $$;

-- ----------------------------------------------------------------------------
-- 4. fn_derivar_uuid_registro: soporte de id_seccion sintético (UUID puro)
--    Orden de derivación (los valores existentes conservan su uuid actual):
--      a) id_seccion con formato UUID puro  -> id_seccion::uuid  (flujo nuevo)
--      b) 1:1                              -> md5(tabla|id_edan_localidad)
--      c) 1:N con id_seccion                -> md5(tabla|id_seccion)   (legacy)
--      d) 1:N sin id_seccion                -> gen_random_uuid()
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION edan.fn_derivar_uuid_registro(
    p_tabla        text,
    p_id_seccion   text,
    p_id_localidad bigint,
    p_es_11        boolean
) RETURNS uuid LANGUAGE plpgsql AS $$
BEGIN
    -- a) id_seccion sintético del flujo nuevo: la identidad sobrevive al
    --    DELETE+INSERT de la app vieja porque se rederiva exactamente igual.
    IF p_id_seccion IS NOT NULL
       AND p_id_seccion ~ '^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$' THEN
        RETURN p_id_seccion::uuid;
    END IF;
    -- b) 1:1: clave estable = localidad (comportamiento original)
    IF p_es_11 THEN
        RETURN md5(p_tabla || '|' || p_id_localidad::text)::uuid;
    END IF;
    -- c) 1:N legacy
    IF p_id_seccion IS NOT NULL THEN
        RETURN md5(p_tabla || '|' || p_id_seccion)::uuid;
    END IF;
    -- d) 1:N sin clave
    RETURN gen_random_uuid();
END;
$$;

COMMENT ON FUNCTION edan.fn_derivar_uuid_registro(text, text, bigint, boolean) IS
    'Deriva uuid_registro de forma determinística: id_seccion sintético (UUID puro) directo; si no, md5(tabla|clave) legacy. 0 filas existentes usan formato UUID puro en id_seccion.';

COMMIT;
SELECT 'IDEMPOTENT OK v2.52.0 edan fk uuid + id_seccion sintetico';
