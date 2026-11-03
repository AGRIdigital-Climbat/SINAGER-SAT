-- ============================================================================
-- SINAGERSAT - Migración v2.51.0 (idempotente)
-- EDAN: versionado optimista + tombstones de borrado (Fase 1: solo BD)
--
--   Contexto: hoy el conflicto de sincronización se resuelve solo por LWW
--   (fecha_modificacion) y los borrados NO se propagan: cada dispositivo asume
--   que lo que no ve "ya no existe" en su lado. El flujo correcto (Fase 2)
--   necesita (a) detectar ediciones simultáneas (409 con ambas versiones) y
--   (b) propagar eliminaciones como eventos (registro_borrado / tombstones).
--
--   Esta migración AÑADE (nada se renombra ni se elimina):
--     * version integer NOT NULL DEFAULT 1 en edan, edan_localidades y las 14
--       secciones, con trigger BEFORE UPDATE fn_bump_version() que la incrementa
--       en cada UPDATE (el cliente envía la version que leyó; si no coincide con
--       la del servidor -> conflicto). INSERT respeta DEFAULT 1.
--     * edan.registro_borrado: log de borrados (tabla + uuid del registro +
--       clave legacy + cuándo + quién), con UNIQUE (tabla, id_registro).
--     * Trigger AFTER DELETE fn_registrar_borrado() SOLO en edan.edan y
--       edan.edan_localidades (borrados físicos reales de la API actual).
--       Las 14 secciones NO llevan trigger todavía: el sync viejo hace
--       DELETE+INSERT en cada actualización (service.update_localidad) y
--       generaría falsos tombstones; se añaden en la Fase 2 (v2.52.0) cuando
--       desaparezca ese patrón.
--
--   Nota: no se implementa aquí la resolución de conflictos (eso es servicio/
--   API en la Fase 2); solo el estado de BD que la hace posible.
--
--   IDEMPOTENCIA: ADD COLUMN IF NOT EXISTS + DROP TRIGGER IF EXISTS +
--   CREATE OR REPLACE FUNCTION + CREATE TABLE IF NOT EXISTS +
--   CREATE INDEX IF NOT EXISTS. Se puede aplicar N veces.
--
--   Respaldo previo: backups/pre_v2.49.0_edan_uuid_*.sql
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. Columna version (aditiva; DEFAULT rellena las filas existentes con 1)
-- ----------------------------------------------------------------------------
ALTER TABLE edan.edan_localidades ADD COLUMN IF NOT EXISTS version integer NOT NULL DEFAULT 1;
ALTER TABLE edan.edan             ADD COLUMN IF NOT EXISTS version integer NOT NULL DEFAULT 1;

ALTER TABLE edan.edan_localidades_danos_agricultura     ADD COLUMN IF NOT EXISTS version integer NOT NULL DEFAULT 1;
ALTER TABLE edan.edan_localidades_danos_infra_publica   ADD COLUMN IF NOT EXISTS version integer NOT NULL DEFAULT 1;
ALTER TABLE edan.edan_localidades_danos_pecuario        ADD COLUMN IF NOT EXISTS version integer NOT NULL DEFAULT 1;
ALTER TABLE edan.edan_localidades_danos_viales          ADD COLUMN IF NOT EXISTS version integer NOT NULL DEFAULT 1;
ALTER TABLE edan.edan_localidades_danos_vivienda        ADD COLUMN IF NOT EXISTS version integer NOT NULL DEFAULT 1;
ALTER TABLE edan.edan_localidades_impacto_poblacion     ADD COLUMN IF NOT EXISTS version integer NOT NULL DEFAULT 1;
ALTER TABLE edan.edan_localidades_infra_productiva      ADD COLUMN IF NOT EXISTS version integer NOT NULL DEFAULT 1;
ALTER TABLE edan.edan_localidades_necesidades_humanitarias ADD COLUMN IF NOT EXISTS version integer NOT NULL DEFAULT 1;
ALTER TABLE edan.edan_localidades_primera_respuesta     ADD COLUMN IF NOT EXISTS version integer NOT NULL DEFAULT 1;
ALTER TABLE edan.edan_localidades_proteccion            ADD COLUMN IF NOT EXISTS version integer NOT NULL DEFAULT 1;
ALTER TABLE edan.edan_localidades_salud_establecimientos ADD COLUMN IF NOT EXISTS version integer NOT NULL DEFAULT 1;
ALTER TABLE edan.edan_localidades_salud_necesidades     ADD COLUMN IF NOT EXISTS version integer NOT NULL DEFAULT 1;
ALTER TABLE edan.edan_localidades_servicios_basicos    ADD COLUMN IF NOT EXISTS version integer NOT NULL DEFAULT 1;
ALTER TABLE edan.edan_localidades_unidades_educativas  ADD COLUMN IF NOT EXISTS version integer NOT NULL DEFAULT 1;

-- ----------------------------------------------------------------------------
-- 2. Trigger de versionado optimista
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION edan.fn_bump_version() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    NEW.version := OLD.version + 1;
    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION edan.fn_bump_version() IS
    'BEFORE UPDATE: incrementa version en cada escritura (LWW y versionado optimista conviven: fecha_modificacion ordena, version detecta edición simultánea).';

DO $$
DECLARE
    t text;
BEGIN
    FOREACH t IN ARRAY ARRAY[
        'edan', 'edan_localidades',
        'edan_localidades_danos_agricultura',
        'edan_localidades_danos_infra_publica',
        'edan_localidades_danos_pecuario',
        'edan_localidades_danos_viales',
        'edan_localidades_danos_vivienda',
        'edan_localidades_impacto_poblacion',
        'edan_localidades_infra_productiva',
        'edan_localidades_necesidades_humanitarias',
        'edan_localidades_primera_respuesta',
        'edan_localidades_proteccion',
        'edan_localidades_salud_establecimientos',
        'edan_localidades_salud_necesidades',
        'edan_localidades_servicios_basicos',
        'edan_localidades_unidades_educativas'
    ]
    LOOP
        EXECUTE format(
            'DROP TRIGGER IF EXISTS trg_bump_version ON edan.%I', t);
        EXECUTE format(
            'CREATE TRIGGER trg_bump_version BEFORE UPDATE ON edan.%I'
            || ' FOR EACH ROW EXECUTE FUNCTION edan.fn_bump_version()', t);
        EXECUTE format(
            'COMMENT ON COLUMN edan.%I.version IS %L', t,
            'Versión optimista: se incrementa en cada UPDATE (fn_bump_version). El cliente envía la versión leída; si no coincide con la del servidor hay edición simultánea.');
    END LOOP;
END $$;

-- ----------------------------------------------------------------------------
-- 3. Tombstones: edan.registro_borrado
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS edan.registro_borrado (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tabla        varchar(60) NOT NULL CHECK (tabla IN (
                     'edan',
                     'edan_localidades',
                     'edan_localidades_danos_agricultura',
                     'edan_localidades_danos_infra_publica',
                     'edan_localidades_danos_pecuario',
                     'edan_localidades_danos_viales',
                     'edan_localidades_danos_vivienda',
                     'edan_localidades_impacto_poblacion',
                     'edan_localidades_infra_productiva',
                     'edan_localidades_necesidades_humanitarias',
                     'edan_localidades_primera_respuesta',
                     'edan_localidades_proteccion',
                     'edan_localidades_salud_establecimientos',
                     'edan_localidades_salud_necesidades',
                     'edan_localidades_servicios_basicos',
                     'edan_localidades_unidades_educativas',
                     'fotografias'
                 )),
    id_registro  uuid NOT NULL,
    clave_legacy text,
    borrado_en   timestamptz NOT NULL DEFAULT now(),
    id_usuario   integer,
    CONSTRAINT uq_registro_borrado UNIQUE (tabla, id_registro)
);

COMMENT ON TABLE edan.registro_borrado IS
    'Tombstones: borrados físicos de registros EDAN para propagarlos por pull a los demás dispositivos (nunca borrar algo sin dejar evento). Secciones se añaden en v2.52.0 (hoy el sync viejo hace DELETE+INSERT y generaría falsos tombstones).';
COMMENT ON COLUMN edan.registro_borrado.id_registro IS
    'uuid del registro borrado (uuid_edan, uuid_edan_localidad, uuid_fotografia o uuid_registro según tabla).';
COMMENT ON COLUMN edan.registro_borrado.clave_legacy IS
    'Clave numérica/string anterior (id_local o id_edan_localidad) para diagnóstico y migración de clientes.';
COMMENT ON COLUMN edan.registro_borrado.id_usuario IS
    'Usuario responsable del borrado. Lo informa la API con set_config(''app.id_usuario'', ...) antes del DELETE (GUC); NULL cuando no hay contexto.';

CREATE INDEX IF NOT EXISTS idx_registro_borrado_borrado_en
    ON edan.registro_borrado (borrado_en);

-- Trigger AFTER DELETE: solo cabeceras (edan y edan_localidades).
CREATE OR REPLACE FUNCTION edan.fn_registrar_borrado() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    v_uuid    uuid;
    v_legacy  text;
BEGIN
    IF TG_ARGV[0] = 'edan' THEN
        v_uuid   := OLD.uuid_edan;
        v_legacy := OLD.id_local;
    ELSE
        v_uuid   := OLD.uuid_edan_localidad;
        v_legacy := OLD.id_local;
    END IF;

    IF v_uuid IS NOT NULL THEN
        INSERT INTO edan.registro_borrado AS rb
            (tabla, id_registro, clave_legacy, id_usuario)
        VALUES
            (TG_ARGV[0], v_uuid, v_legacy,
             NULLIF(current_setting('app.id_usuario', true), '')::integer)
        ON CONFLICT (tabla, id_registro)
        DO UPDATE SET borrado_en   = now(),
                      clave_legacy = EXCLUDED.clave_legacy;
    END IF;
    RETURN OLD;
END;
$$;

COMMENT ON FUNCTION edan.fn_registrar_borrado() IS
    'AFTER DELETE en edan.edan / edan.edan_localidades: registra el tombstone (idempotente por ON CONFLICT). Las secciones se migran en v2.52.0.';

DROP TRIGGER IF EXISTS trg_registro_borrado ON edan.edan;
CREATE TRIGGER trg_registro_borrado
    AFTER DELETE ON edan.edan
    FOR EACH ROW EXECUTE FUNCTION edan.fn_registrar_borrado('edan');

DROP TRIGGER IF EXISTS trg_registro_borrado ON edan.edan_localidades;
CREATE TRIGGER trg_registro_borrado
    AFTER DELETE ON edan.edan_localidades
    FOR EACH ROW EXECUTE FUNCTION edan.fn_registrar_borrado('edan_localidades');

COMMIT;
SELECT 'IDEMPOTENT OK v2.51.0 edan version + registro_borrado';
