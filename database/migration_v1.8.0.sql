-- ============================================================================
-- SINAGERSAT - Migración v1.8.0 (idempotente)
-- edan.edan: identidad por USUARIOS en lugar de campos libres.
-- 1. Se agregan id_usuario_alcalde (rol 8) e id_usuario_ugr (rol 6),
--    ambos FK -> usuarios.usuario(id_usuario) con ON DELETE SET NULL.
-- 2. Backfill previo: id_usuario_ugr desde id_usuario (rol 6);
--    id_usuario_alcalde por coincidencia de nombre con usuario rol 8.
-- 3. Se eliminan las columnas libres:
--    nombre_alcalde, fono_alcalde, responsable_nombre, responsable_cargo,
--    responsable_fono, responsable_correo, id_reporte_rea, fotografia,
--    estado, id_local e id_usuario.
-- Aplica sobre migration_v1.7.0. Sin trigger: la validación de rol 6/8
-- queda a cargo de la API.
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. Nuevas columnas
-- ============================================================================
ALTER TABLE edan.edan ADD COLUMN IF NOT EXISTS id_usuario_alcalde integer;
ALTER TABLE edan.edan ADD COLUMN IF NOT EXISTS id_usuario_ugr integer;

-- ============================================================================
-- 2. Backfill (antes de eliminar las columnas libres)
-- ============================================================================

-- 2.1 id_usuario_ugr hereda de id_usuario cuando este es rol 6 (UGR Municipio)
UPDATE edan.edan e
SET id_usuario_ugr = e.id_usuario
FROM usuarios.usuario u
WHERE u.id_usuario = e.id_usuario
  AND u.id_rol = 6;

-- 2.2 id_usuario_alcalde por coincidencia de nombre con usuario rol 8 (Alcalde)
UPDATE edan.edan e
SET id_usuario_alcalde = u.id_usuario
FROM usuarios.usuario u
WHERE u.nombre = e.nombre_alcalde
  AND u.id_rol = 8;

-- ============================================================================
-- 3. FKs -> usuarios.usuario (ON DELETE SET NULL)
-- ============================================================================
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'edan_id_usuario_alcalde_fkey') THEN
        ALTER TABLE edan.edan
            ADD CONSTRAINT edan_id_usuario_alcalde_fkey
            FOREIGN KEY (id_usuario_alcalde) REFERENCES usuarios.usuario(id_usuario) ON DELETE SET NULL;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'edan_id_usuario_ugr_fkey') THEN
        ALTER TABLE edan.edan
            ADD CONSTRAINT edan_id_usuario_ugr_fkey
            FOREIGN KEY (id_usuario_ugr) REFERENCES usuarios.usuario(id_usuario) ON DELETE SET NULL;
    END IF;
END $$;

-- ============================================================================
-- 4. Índices
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_edan_usuario_alcalde ON edan.edan(id_usuario_alcalde);
CREATE INDEX IF NOT EXISTS idx_edan_usuario_ugr ON edan.edan(id_usuario_ugr);

-- ============================================================================
-- 5. Eliminación de columnas libres
--    (las FKs e índices asociados se eliminan automáticamente)
-- ============================================================================
ALTER TABLE edan.edan DROP COLUMN IF EXISTS nombre_alcalde;
ALTER TABLE edan.edan DROP COLUMN IF EXISTS fono_alcalde;
ALTER TABLE edan.edan DROP COLUMN IF EXISTS responsable_nombre;
ALTER TABLE edan.edan DROP COLUMN IF EXISTS responsable_cargo;
ALTER TABLE edan.edan DROP COLUMN IF EXISTS responsable_fono;
ALTER TABLE edan.edan DROP COLUMN IF EXISTS responsable_correo;
ALTER TABLE edan.edan DROP COLUMN IF EXISTS id_reporte_rea; -- elimina edan_id_reporte_rea_fkey + idx_edan_id_reporte_rea
ALTER TABLE edan.edan DROP COLUMN IF EXISTS fotografia;
ALTER TABLE edan.edan DROP COLUMN IF EXISTS estado;          -- elimina idx_edan_estado
ALTER TABLE edan.edan DROP COLUMN IF EXISTS id_local;        -- elimina edan_id_local_key
ALTER TABLE edan.edan DROP COLUMN IF EXISTS id_usuario;      -- elimina edan_id_usuario_fkey + idx_edan_usuario + idx_edan_sync_pull

COMMIT;

SELECT 'IDEMPOTENT OK v1.8.0' AS resultado;
