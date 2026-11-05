-- ============================================================================
-- SINAGERSAT - Migración v2.41.0 (idempotente)
-- RIDA: la solicitud cuelga del EVENTO, no del formulario
--
--   rida.solicitud pasa de `id_formulario` (una localidad) a `id_evento_rida`
--   (el PADRE del RIDA). Tiene sentido: un evento = un EDAN = un municipio, y
--   la solicitud pide suministros para todo el evento; la geografía se deriva
--   igual (evento -> edan -> municipio/departamento).
--
--   Datos legacy: las solicitudes huérfanas (formulario sin evento, pruebas
--   "Obrajes/Achumani") se depuran junto a toda su descendencia, en orden de
--   FKs (todo NO ACTION salvo aprobaciones_solicitud, que es CASCADE).
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. Columna nueva (preparada para el backfill)
-- ----------------------------------------------------------------------------
ALTER TABLE rida.solicitud ADD COLUMN IF NOT EXISTS id_evento_rida INTEGER;

DO $$
BEGIN
    -- Todo el bloque solo corre mientras exista la columna vieja: el re-run
    -- de la migración (ya con id_formulario caída) lo salta limpiamente.
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_schema = 'rida' AND table_name = 'solicitud'
                 AND column_name = 'id_formulario') THEN

        -- ------------------------------------------------------------------
        -- 2. Backfill: evento del formulario ancla actual
        -- ------------------------------------------------------------------
        UPDATE rida.solicitud s
        SET id_evento_rida = f.id_evento_rida
        FROM rida.formulario_rida f
        WHERE f.id_formulario = s.id_formulario
          AND s.id_evento_rida IS NULL
          AND f.id_evento_rida IS NOT NULL;

        -- ------------------------------------------------------------------
        -- 3. Depuración legacy: solicitudes sin evento y su descendencia
        -- ------------------------------------------------------------------
        CREATE TEMP TABLE _orph_s ON COMMIT DROP AS
        SELECT id_solicitud FROM rida.solicitud WHERE id_evento_rida IS NULL;

        DELETE FROM rida.entrega_beneficiario eb
        WHERE eb.id_entrega IN (SELECT e.id_entrega FROM rida.entrega e
                                JOIN _orph_s o ON o.id_solicitud = e.id_solicitud);

        DELETE FROM rida.entrega_detalle ed
        WHERE ed.id_entrega IN (SELECT e.id_entrega FROM rida.entrega e
                                JOIN _orph_s o ON o.id_solicitud = e.id_solicitud);

        DELETE FROM rida.contratacion c
        WHERE c.id_solicitud IN (SELECT id_solicitud FROM _orph_s)
           OR c.id_proforma IN (SELECT p.id_proforma FROM rida.proforma p
                                JOIN _orph_s o ON o.id_solicitud = p.id_solicitud);

        DELETE FROM rida.entrega e
        WHERE e.id_solicitud IN (SELECT id_solicitud FROM _orph_s);

        DELETE FROM rida.proforma p
        WHERE p.id_solicitud IN (SELECT id_solicitud FROM _orph_s);

        DELETE FROM rida.requerimiento_umee r
        WHERE r.id_solicitud IN (SELECT id_solicitud FROM _orph_s);

        DELETE FROM rida.comando_incidente ci
        WHERE ci.id_solicitud IN (SELECT id_solicitud FROM _orph_s);

        DELETE FROM rida.bitacora b
        WHERE b.id_solicitud IN (SELECT id_solicitud FROM _orph_s);

        DELETE FROM rida.proyecto pr
        WHERE pr.id_solicitud IN (SELECT id_solicitud FROM _orph_s);

        -- documentos subidos por esas solicitudes: muere también el registro
        -- en el repositorio (los archivos físicos quedan; son datos de prueba)
        CREATE TEMP TABLE _orph_docs ON COMMIT DROP AS
        SELECT sd.id_documento FROM rida.solicitud_documento sd
        JOIN _orph_s o ON o.id_solicitud = sd.id_solicitud
        WHERE sd.id_documento IS NOT NULL;

        DELETE FROM rida.solicitud_documento sd
        WHERE sd.id_solicitud IN (SELECT id_solicitud FROM _orph_s);

        DELETE FROM repositorio.documentos d
        WHERE d.id_documento IN (SELECT id_documento FROM _orph_docs);

        DELETE FROM rida.solicitud s
        WHERE s.id_solicitud IN (SELECT id_solicitud FROM _orph_s);

        -- ------------------------------------------------------------------
        -- 4. Cambio de ancla: cae id_formulario
        -- ------------------------------------------------------------------
        DROP INDEX IF EXISTS rida.idx_solicitud_id_formulario;
        ALTER TABLE rida.solicitud DROP CONSTRAINT IF EXISTS solicitud_id_formulario_fkey;
        ALTER TABLE rida.solicitud DROP COLUMN IF EXISTS id_formulario;
    END IF;
END $$;

-- ----------------------------------------------------------------------------
-- 5. id_evento_rida: FK + NOT NULL + índice (idempotente)
-- ----------------------------------------------------------------------------
ALTER TABLE rida.solicitud DROP CONSTRAINT IF EXISTS solicitud_id_evento_rida_fkey;
ALTER TABLE rida.solicitud
    ADD CONSTRAINT solicitud_id_evento_rida_fkey
    FOREIGN KEY (id_evento_rida) REFERENCES rida.evento_rida(id_evento_rida);

ALTER TABLE rida.solicitud ALTER COLUMN id_evento_rida SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_solicitud_id_evento_rida
    ON rida.solicitud (id_evento_rida);

SELECT 'IDEMPOTENT OK v2.41.0 solicitud_evento';

COMMIT;
