-- ============================================================================
-- SINAGERSAT - Migración v2.54.0 (idempotente)
-- EDAN: tabla de confirmaciones de pull por dispositivo (Fase 2: APIs nuevas)
--
--   Contexto: el flujo de sincronización (PLAN_APIS_V2_EDAN.md §8/§12) usa
--   pull incremental con watermark + ack. El ack registra hasta qué marca de
--   tiempo un dispositivo ya APLICÓ los cambios descargados; el servidor puede
--   así depurar `registro_borrado` antiguo y responder con seguridad.
--
--   Esta migración SOLO crea `edan.dispositivo_sync` (nada se toca de lo
--   existente). Los tombstones de secciones NO entran aquí (romperían el
--   DELETE+INSERT del sync viejo) y quedan para v2.55.0.
--
--   IDEMPOTENCIA: CREATE TABLE IF NOT EXISTS + CREATE INDEX IF NOT EXISTS.
--   Se puede aplicar N veces.
-- ============================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS edan.dispositivo_sync (
    id_dispositivo       uuid PRIMARY KEY,
    id_usuario           integer,
    watermark_aplicado   timestamptz,
    ack_en               timestamptz NOT NULL DEFAULT now(),
    fecha_registro       timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE edan.dispositivo_sync IS
    'Confirmaciones (ack) de pull por dispositivo: hasta qué watermark (fecha_modificacion) ya aplicó el dispositivo. Usado por POST /api/v2/edan/sync/ack de las APIs nuevas (Fase 2).';
COMMENT ON COLUMN edan.dispositivo_sync.id_dispositivo IS
    'Identificador del dispositivo (uuid generado por el cliente móvil/web; estable por instalación).';
COMMENT ON COLUMN edan.dispositivo_sync.watermark_aplicado IS
    'Marca de tiempo (fecha_modificacion del servidor) hasta la cual el dispositivo confirmó haber aplicado los cambios del pull.';
COMMENT ON COLUMN edan.dispositivo_sync.ack_en IS
    'Cuándo se recibió la última confirmación de ese dispositivo.';

CREATE INDEX IF NOT EXISTS idx_dispositivo_sync_ack_en
    ON edan.dispositivo_sync (ack_en);

COMMIT;
SELECT 'IDEMPOTENT OK v2.54.0 edan.dispositivo_sync';
