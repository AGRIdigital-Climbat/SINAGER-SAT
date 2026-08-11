-- ============================================================================
-- SINAGERSAT - Migración v1.9.0 (idempotente)
-- Modelo de sincronización AppSheet (offline-first) aplicado a edan.edan y
-- edan.edan_localidades.
--
-- Campos de sync definitivos (los únicos necesarios):
--   - id_local (UUID del dispositivo, UNIQUE): identidad estable del documento
--     entre dispositivos. El servidor lo mapea a la PK (id_edan / id_edan_localidad).
--   - fecha_creacion (solo edan.edan): auditoría, NOW() del servidor.
--   - fecha_modificacion: autoridad de tiempo (NOW() al escribir). Soporta el
--     pull incremental y la resolución last-write-wins.
--   - pendiente_actualizacion: "cambios locales sin subir" (flag dirty).
--   - pendiente_eliminacion: tombstone de borrado.
--
-- Se ELIMINAN (redundantes / no necesarios):
--   edan.edan:            sincronizado, es_borrador (derivable de id_estado=1),
--                         intentos_sync, ultimo_error, id_server (id_edan es el
--                         id del servidor).
--   edan.edan_localidades: sincronizado, id_server.
--
-- Dueño del pull del EDAN = id_usuario_ugr (rol 6). Dueño del pull de la
-- localidad = id_usuario.
-- Aplica sobre migration_v1.8.0.
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. edan.edan: restaurar id_local (identidad del documento)
-- ============================================================================

-- 1.1 Columna id_local (si no existiera)
ALTER TABLE edan.edan ADD COLUMN IF NOT EXISTS id_local varchar(64);

-- 1.2 Backfill UUID para filas existentes (antes del índice único)
UPDATE edan.edan SET id_local = gen_random_uuid()::text WHERE id_local IS NULL;

-- 1.3 Índice único parcial
DROP INDEX IF EXISTS edan_id_local_key;
CREATE UNIQUE INDEX edan_id_local_key ON edan.edan(id_local) WHERE id_local IS NOT NULL;

-- ============================================================================
-- 2. edan.edan: eliminar columnas de sync sobrantes
-- ============================================================================
ALTER TABLE edan.edan DROP COLUMN IF EXISTS sincronizado;      -- elimina idx_edan_sincronizado
ALTER TABLE edan.edan DROP COLUMN IF EXISTS es_borrador;       -- derivable de id_estado = 1
ALTER TABLE edan.edan DROP COLUMN IF EXISTS intentos_sync;
ALTER TABLE edan.edan DROP COLUMN IF EXISTS ultimo_error;
ALTER TABLE edan.edan DROP COLUMN IF EXISTS id_server;

-- ============================================================================
-- 3. edan.edan: índice de pull incremental por dueño (UGR)
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_edan_sync_pull ON edan.edan(id_usuario_ugr, fecha_modificacion);

-- ============================================================================
-- 4. edan.edan_localidades: mismas reglas de sincronización
-- ============================================================================

-- 4.1 Eliminar columnas sobrantes
ALTER TABLE edan.edan_localidades DROP COLUMN IF EXISTS sincronizado;
ALTER TABLE edan.edan_localidades DROP COLUMN IF EXISTS id_server;

-- 4.2 Índice de pull incremental por dueño
CREATE INDEX IF NOT EXISTS idx_edan_localidades_sync_pull
    ON edan.edan_localidades(id_usuario, fecha_modificacion);

COMMIT;

SELECT 'IDEMPOTENT OK v1.9.0' AS resultado;
