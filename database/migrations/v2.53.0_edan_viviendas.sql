-- ============================================================================
-- SINAGERSAT - Migración v2.53.0 (idempotente)
-- EDAN: detalle por vivienda en daños de vivienda (Fase 1: solo BD)
--
--   Problema: hoy `edan_localidades_danos_vivienda` guarda solo el AGREGADO
--   (dano_total = N, dano_parcial = M) con UNA sola foto por fila. Se necesita
--   una fila + foto POR vivienda, sin perder la vista agregada (la API vieja y
--   los reportes leen dano_total/dano_parcial de esa tabla).
--
--   Solución (tabla hija + conteos DERIVADOS):
--     * Nueva tabla `edan.edan_localidades_viviendas` (1:N desde la fila de
--       daños): una fila por vivienda con tipo_dano (TOTAL|PARCIAL), sus
--       coordenadas, su propio uuid y su `fotografia` (path, mismo patrón que
--       las secciones actuales).
--     * Fotos por vivienda: el PATH vive en la columna `fotografia` de la fila
--       (como en las secciones); la identidad/ciclo de vida se registra en la
--       tabla `edan.fotografias` existente con el nuevo valor tipo_entidad
--       'vivienda' + uuid_registro = uuid de la vivienda.
--     * Trigger AFTER INSERT/UPDATE/DELETE fn_recompute_danos_vivienda():
--       recalcula dano_total/dano_parcial en la fila padre como COUNT(*) de
--       viviendas por tipo. SOLO actúa sobre filas que (tengan o acaben de
--       tener) viviendas: las 65 filas legacy SIN detalle conservan sus
--       conteos actuales intactos (sin backfill, decisión de diseño).
--     * `necesidades_inmediatas` y `observaciones` se QUEDAN en la sección
--       (nivel comunidad), no en la fila de vivienda.
--
--   Regla de coexistencia (documentada): si la app vieja escribe conteos a
--   mano y la app nueva escribe viviendas, los conteos DERIVADOS ganan
--   siempre que exista al menos una vivienda en la fila.
--
--   NO se toca: código de la API vieja, filas existentes, columnas de la
--   sección, índices idx_seccion_*. Las migraciones v2.49–v2.52 siguen
--   intactas. Tombstones de secciones pasan a v2.54.0 (la 53 queda para esto).
--
--   IDEMPOTENCIA: CREATE TABLE IF NOT EXISTS + CREATE OR REPLACE FUNCTION +
--   DROP TRIGGER IF EXISTS + DROP/ADD CONSTRAINT en DO ... IF NOT EXISTS +
--   CREATE INDEX IF NOT EXISTS. Se puede aplicar N veces.
--
--   Respaldo previo: backups/pre_v2.49.0_edan_uuid_*.sql (+ backup completo
--   database/backup_2026_10_10_042635.sql)
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. Tabla de detalle por vivienda
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS edan.edan_localidades_viviendas (
    id_vivienda          bigserial PRIMARY KEY,
    id_dano_vivienda     bigint NOT NULL
                         REFERENCES edan.edan_localidades_danos_vivienda (id_dano_vivienda)
                         ON DELETE CASCADE,
    uuid_registro        uuid NOT NULL DEFAULT gen_random_uuid(),
    uuid_dano_vivienda   uuid NOT NULL,
    tipo_dano            varchar(10) NOT NULL
                         CHECK (tipo_dano IN ('TOTAL', 'PARCIAL')),
    coordenada_lat       numeric,
    coordenada_lon       numeric,
    fotografia           varchar(500),
    version              integer NOT NULL DEFAULT 1,
    fecha_modificacion   timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_viviendas_uuid UNIQUE (uuid_registro)
);

-- En BDs donde v2.53.0 ya se aplicó sin la columna (aplicación anterior)
ALTER TABLE edan.edan_localidades_viviendas
    ADD COLUMN IF NOT EXISTS fotografia varchar(500);

COMMENT ON TABLE edan.edan_localidades_viviendas IS
    'Detalle por vivienda de la sección daños de vivienda: una fila + fotos por casa (tipo_dano TOTAL|PARCIAL). Los conteos dano_total/dano_parcial de la fila padre se derivan de aquí por trigger (fn_recompute_danos_vivienda); las filas legacy sin detalle conservan sus conteos originales.';
COMMENT ON COLUMN edan.edan_localidades_viviendas.id_dano_vivienda IS
    'Fila de sección dueña (edan_localidades_danos_vivienda). FK numérica ON DELETE CASCADE.';
COMMENT ON COLUMN edan.edan_localidades_viviendas.uuid_registro IS
    'Identidad permanente de la vivienda (cliente la genera; DEFAULT del servidor si no llega). Única e inmutable; las fotos se vinculan por tipo_entidad=''vivienda'' + este uuid en edan.fotografias.';
COMMENT ON COLUMN edan.edan_localidades_viviendas.uuid_dano_vivienda IS
    'Espejo del vínculo con la fila padre: FK -> edan_localidades_danos_vivienda(uuid_registro) ON DELETE CASCADE; lo mantiene trg_espejo_uuid_dano_vivienda (v2.52.0).';
COMMENT ON COLUMN edan.edan_localidades_viviendas.tipo_dano IS
    'TOTAL o PARCIAL. El trigger de recálculo cuenta por este valor para mantener dano_total/dano_parcial en el padre.';
COMMENT ON COLUMN edan.edan_localidades_viviendas.coordenada_lat IS
    'Latitud de la vivienda (opcional; la sección tiene las coordenadas de la comunidad, éstas son por casa).';
COMMENT ON COLUMN edan.edan_localidades_viviendas.coordenada_lon IS
    'Longitud de la vivienda (opcional).';
COMMENT ON COLUMN edan.edan_localidades_viviendas.fotografia IS
    'Path del archivo de foto de la vivienda (mismo patrón que la columna fotografia de las secciones). La identidad/ciclo de vida de la foto se registra además en edan.fotografias con tipo_entidad=''vivienda'' + uuid_registro.';

CREATE INDEX IF NOT EXISTS idx_viviendas_dano
    ON edan.edan_localidades_viviendas (id_dano_vivienda);
CREATE INDEX IF NOT EXISTS idx_viviendas_uuid_dano
    ON edan.edan_localidades_viviendas (uuid_dano_vivienda);
CREATE INDEX IF NOT EXISTS idx_viviendas_sync_pull
    ON edan.edan_localidades_viviendas (fecha_modificacion);

-- ----------------------------------------------------------------------------
-- 2. Identidad: respeta el uuid del cliente; se asigna solo si no llega
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION edan.fn_uuid_vivienda() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        IF NEW.uuid_registro IS NULL THEN
            NEW.uuid_registro := OLD.uuid_registro;   -- inmutable al editar
        END IF;
    ELSE
        IF NEW.uuid_registro IS NULL THEN
            NEW.uuid_registro := gen_random_uuid();   -- el cliente idealmente lo genera
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION edan.fn_uuid_vivienda() IS
    'BEFORE INSERT/UPDATE en edan_localidades_viviendas: uuid_registro lo aporta el cliente (API nueva) o se genera; inmutable en UPDATE.';

DROP TRIGGER IF EXISTS trg_uuid_vivienda ON edan.edan_localidades_viviendas;
CREATE TRIGGER trg_uuid_vivienda
    BEFORE INSERT OR UPDATE ON edan.edan_localidades_viviendas
    FOR EACH ROW EXECUTE FUNCTION edan.fn_uuid_vivienda();

-- ----------------------------------------------------------------------------
-- 3. Espejo del uuid de la fila padre (patrón v2.52.0)
--    Si el padre no existe se lanza error claro (la fila no es insertable).
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION edan.fn_espejo_uuid_dano_vivienda() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    v uuid;
BEGIN
    SELECT d.uuid_registro INTO v
    FROM edan.edan_localidades_danos_vivienda d
    WHERE d.id_dano_vivienda = NEW.id_dano_vivienda;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'No existe la fila de daños de vivienda id_dano_vivienda=% (no se puede asignar uuid_dano_vivienda)',
            NEW.id_dano_vivienda;
    END IF;

    NEW.uuid_dano_vivienda := v;
    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION edan.fn_espejo_uuid_dano_vivienda() IS
    'BEFORE INSERT/UPDATE en edan_localidades_viviendas: uuid_dano_vivienda es espejo de id_dano_vivienda (fuente de verdad numérica) y apunta a danos_vivienda.uuid_registro.';

DROP TRIGGER IF EXISTS trg_espejo_uuid_dano_vivienda ON edan.edan_localidades_viviendas;
CREATE TRIGGER trg_espejo_uuid_dano_vivienda
    BEFORE INSERT OR UPDATE ON edan.edan_localidades_viviendas
    FOR EACH ROW EXECUTE FUNCTION edan.fn_espejo_uuid_dano_vivienda();

-- ----------------------------------------------------------------------------
-- 4. Versionado optimista (reutiliza fn_bump_version de v2.51.0)
-- ----------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_bump_version ON edan.edan_localidades_viviendas;
CREATE TRIGGER trg_bump_version
    BEFORE UPDATE ON edan.edan_localidades_viviendas
    FOR EACH ROW EXECUTE FUNCTION edan.fn_bump_version();

-- ----------------------------------------------------------------------------
-- 5. Recálculo de conteos en la fila padre (la vista agregada de siempre)
--    Regla: si la fila tiene (o acaba de perder) viviendas, los conteos se
--    derivan de COUNT(*). Filas legacy sin viviendas NUNCA se tocan.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION edan.fn_recompute_danos_vivienda() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    v_id bigint;
BEGIN
    IF TG_OP = 'UPDATE' AND NEW.id_dano_vivienda IS DISTINCT FROM OLD.id_dano_vivienda THEN
        -- la vivienda se movió de fila: recalcular también la fila anterior
        UPDATE edan.edan_localidades_danos_vivienda d
        SET dano_total  = (SELECT count(*) FROM edan.edan_localidades_viviendas v
                            WHERE v.id_dano_vivienda = OLD.id_dano_vivienda
                              AND v.tipo_dano = 'TOTAL'),
            dano_parcial = (SELECT count(*) FROM edan.edan_localidades_viviendas v
                            WHERE v.id_dano_vivienda = OLD.id_dano_vivienda
                              AND v.tipo_dano = 'PARCIAL')
        WHERE d.id_dano_vivienda = OLD.id_dano_vivienda;
    END IF;

    IF TG_OP = 'DELETE' THEN
        v_id := OLD.id_dano_vivienda;
    ELSE
        v_id := NEW.id_dano_vivienda;
    END IF;

    UPDATE edan.edan_localidades_danos_vivienda d
    SET dano_total  = (SELECT count(*) FROM edan.edan_localidades_viviendas v
                        WHERE v.id_dano_vivienda = v_id
                          AND v.tipo_dano = 'TOTAL'),
        dano_parcial = (SELECT count(*) FROM edan.edan_localidades_viviendas v
                        WHERE v.id_dano_vivienda = v_id
                          AND v.tipo_dano = 'PARCIAL')
    WHERE d.id_dano_vivienda = v_id;

    RETURN NULL;
END;
$$;

COMMENT ON FUNCTION edan.fn_recompute_danos_vivienda() IS
    'AFTER INSERT/UPDATE/DELETE en edan_localidades_viviendas: dano_total/dano_parcial del padre = COUNT(*) por tipo_dano. Solo actúa sobre filas con viviendas; las legacy sin detalle quedan intactas.';

DROP TRIGGER IF EXISTS trg_recompute_danos ON edan.edan_localidades_viviendas;
CREATE TRIGGER trg_recompute_danos
    AFTER INSERT OR UPDATE OR DELETE ON edan.edan_localidades_viviendas
    FOR EACH ROW EXECUTE FUNCTION edan.fn_recompute_danos_vivienda();

-- ----------------------------------------------------------------------------
-- 6. fotografias: 15º valor de tipo_entidad ('vivienda')
-- ----------------------------------------------------------------------------
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'fotografias_tipo_entidad_check'
          AND conrelid = 'edan.fotografias'::regclass
    ) THEN
        ALTER TABLE edan.fotografias DROP CONSTRAINT fotografias_tipo_entidad_check;
    END IF;

    ALTER TABLE edan.fotografias
        ADD CONSTRAINT fotografias_tipo_entidad_check
        CHECK (tipo_entidad IN (
            'danos_agricultura',
            'danos_infra_publica',
            'danos_pecuario',
            'danos_viales',
            'danos_vivienda',
            'impacto_poblacion',
            'infra_productiva',
            'necesidades_humanitarias',
            'primera_respuesta',
            'proteccion',
            'salud_establecimientos',
            'salud_necesidades',
            'servicios_basicos',
            'unidades_educativas',
            'vivienda'
        ));
END $$;

COMMENT ON COLUMN edan.fotografias.tipo_entidad IS
    'Nombre corto de la tabla dueña (polimórfico): 14 secciones + ''vivienda'' (edan_localidades_viviendas, v2.53.0). uuid_registro apunta al uuid de esa fila.';

-- ----------------------------------------------------------------------------
-- 7. registro_borrado: la nueva tabla queda lista para tombstones (v2.54.0)
-- ----------------------------------------------------------------------------
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'registro_borrado_tabla_check'
          AND conrelid = 'edan.registro_borrado'::regclass
    ) THEN
        ALTER TABLE edan.registro_borrado DROP CONSTRAINT registro_borrado_tabla_check;
    END IF;

    ALTER TABLE edan.registro_borrado
        ADD CONSTRAINT registro_borrado_tabla_check
        CHECK (tabla IN (
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
            'edan_localidades_viviendas',
            'fotografias'
        ));
END $$;

COMMIT;
SELECT 'IDEMPOTENT OK v2.53.0 edan_localidades_viviendas';
