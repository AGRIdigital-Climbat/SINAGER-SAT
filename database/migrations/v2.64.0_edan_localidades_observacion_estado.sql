-- ============================================================================
-- SINAGERSAT - Migración v2.64.0 (idempotente)
-- EDAN: observación del estado de localidad (motivo de rechazo)
--
--   Contexto: al cambiar el estado de una edan.edan_localidad (p. ej. a
--   "Rechazado UGR") el revisor debe poder indicar el MOTIVO. Hoy solo
--   existe el id_edan_localidad_estado; no queda registro del porqué.
--
--   Agrega a edan.edan_localidades:
--     - observacion_estado TEXT (NULL = sin observación; texto libre)
--
--   La escribe SOLO el endpoint de cambio de estado (PUT /localidades/{id}/estado);
--   el upsert del móvil (_CABECERA_COLS) NO la expone para que el autor no
--   pueda borrarla en el sync. Obligatoria cuando el destino es "Rechazado".
--
--   IDEMPOTENCIA: ADD COLUMN IF NOT EXISTS + COMMENT. Se puede aplicar N veces.
-- ============================================================================

BEGIN;

ALTER TABLE edan.edan_localidades
    ADD COLUMN IF NOT EXISTS observacion_estado TEXT;

COMMENT ON COLUMN edan.edan_localidades.observacion_estado IS
    'Motivo/observación del último cambio de estado de la localidad (p. ej. motivo del rechazo). NULL = sin observación. Se conserva si un cambio posterior no envía observación; solo la escribe PUT /localidades/{id}/estado.';

COMMIT;

SELECT 'IDEMPOTENT OK v2.64.0' AS resultado;
