-- ============================================================================
-- SINAGERSAT - Migración v2.16.4 (idempotente)
-- Agrega 4 campos booleanos a edan.edan para registro de aprobaciones:
--   aprob_ugr, aprob_alcalde, aprob_dgr, aprob_videcid.
-- Son NOT NULL DEFAULT false, por lo que las filas existentes quedan en false
-- y las APIs que no envíen estos campos no se ven afectadas.
-- ============================================================================

BEGIN;

ALTER TABLE edan.edan ADD COLUMN IF NOT EXISTS aprob_ugr boolean NOT NULL DEFAULT false;
ALTER TABLE edan.edan ADD COLUMN IF NOT EXISTS aprob_alcalde boolean NOT NULL DEFAULT false;
ALTER TABLE edan.edan ADD COLUMN IF NOT EXISTS aprob_dgr boolean NOT NULL DEFAULT false;
ALTER TABLE edan.edan ADD COLUMN IF NOT EXISTS aprob_videcid boolean NOT NULL DEFAULT false;

COMMIT;

SELECT 'IDEMPOTENT OK v2.16.4 add_4boolean_fields' AS resultado;