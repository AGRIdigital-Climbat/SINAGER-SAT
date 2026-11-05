-- ============================================================================
-- SINAGERSAT - Migración v2.11.0 (idempotente)
-- Validación de firma digital (proxy AGETIC):
--   Agrega a repositorio.documentos:
--     - tiene_firma_digital     : indica si el PDF tiene firma digital (validado)
--     - resultado_firma         : JSONB con metadatos completos de las firmas
--                                 (firmante, CI, ECA, cadena de confianza, fechas)
--     - fecha_validacion_firma  : timestamp de la última validación
-- ============================================================================

BEGIN;

ALTER TABLE repositorio.documentos
    ADD COLUMN IF NOT EXISTS tiene_firma_digital BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS resultado_firma JSONB,
    ADD COLUMN IF NOT EXISTS fecha_validacion_firma TIMESTAMP WITHOUT TIME ZONE;

COMMENT ON COLUMN repositorio.documentos.tiene_firma_digital IS 'Indica si el PDF fue validado y contiene firma digital (proxy AGETIC).';
COMMENT ON COLUMN repositorio.documentos.resultado_firma IS 'Metadatos completos de la validación de firmas (JSONB): firmas, certificados, ECA, cadena de confianza, fechas.';
COMMENT ON COLUMN repositorio.documentos.fecha_validacion_firma IS 'Fecha/hora de la última validación de firma digital.';

CREATE INDEX IF NOT EXISTS idx_documentos_firma_digital
    ON repositorio.documentos (tiene_firma_digital)
    WHERE tiene_firma_digital = TRUE AND activo = TRUE;

COMMIT;

SELECT 'IDEMPOTENT OK v2.11.0' AS resultado;