-- ============================================================================
-- SINAGERSAT - Migración v2.5.0 (idempotente)
-- edan.edan_localidades_servicios_basicos: elimina la columna `afectado`.
-- El formulario (sección servicios básicos) solo maneja: descripción (tipo),
-- daño parcial, daño total, necesidades inmediatas y observaciones.
-- El CHECK de `tipo` ya restringe a los 5 servicios esperados.
-- Aplica sobre migration_v2.4.0.
-- NOTA: la API (api/edan/service.py) todavía referencia `afectado`;
-- se adaptará en una etapa posterior.
-- ============================================================================

BEGIN;

ALTER TABLE edan.edan_localidades_servicios_basicos DROP COLUMN IF EXISTS afectado;

COMMIT;

SELECT 'IDEMPOTENT OK v2.5.0' AS resultado;
