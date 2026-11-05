-- ============================================================================
-- SINAGERSAT - Migración v1.4.3 (idempotente)
-- Sincronización offline-first del módulo EDAN (solo EDAN):
-- 1. Columna id_local (UUID generado por la app) UNIQUE para upsert por
--    identidad del dispositivo.
-- 2. Índice compuesto (id_usuario, fecha_modificacion) para el pull por fecha.
-- Aplica sobre migration_v1.4.2.
-- ============================================================================

BEGIN;

ALTER TABLE edan.edan ADD COLUMN IF NOT EXISTS id_local VARCHAR(64);

CREATE UNIQUE INDEX IF NOT EXISTS edan_id_local_key ON edan.edan(id_local);

CREATE INDEX IF NOT EXISTS idx_edan_sync_pull ON edan.edan(id_usuario, fecha_modificacion);

COMMIT;

SELECT 'IDEMPOTENT OK v1.4.3' AS resultado;
