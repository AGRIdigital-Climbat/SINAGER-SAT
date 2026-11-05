-- ============================================================================
-- SINAGERSAT - Migración v2.1.0 (idempotente)
-- edan.edan_localidades_danos_viales: reemplaza el texto libre "via_puente"
-- por dos columnas booleanas con CHECK (patrón dano_parcial/dano_total):
--   via     boolean NOT NULL DEFAULT false  + CONSTRAINT via
--   puente  boolean NOT NULL DEFAULT false  + CONSTRAINT puente
-- El UGR marca si el daño vial afectó una vía (camino/carretera/ruta) y/o un
-- puente, en lugar de escribir el texto en un solo campo.
-- Aplica sobre migration_v2.0.0.
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. Nuevas columnas booleanas
-- ============================================================================
ALTER TABLE edan.edan_localidades_danos_viales ADD COLUMN IF NOT EXISTS via    boolean NOT NULL DEFAULT false;
ALTER TABLE edan.edan_localidades_danos_viales ADD COLUMN IF NOT EXISTS puente boolean NOT NULL DEFAULT false;

-- ============================================================================
-- 2. Backfill desde via_puente (antes de eliminar la columna)
--    Camino/carretera/ruta/vía/tramo → via = true
--    Puente                          → puente = true
-- ============================================================================
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'edan'
          AND table_name   = 'edan_localidades_danos_viales'
          AND column_name  = 'via_puente'
    ) THEN
        UPDATE edan.edan_localidades_danos_viales
        SET via    = (LOWER(via_puente) LIKE '%camino%'   OR
                      LOWER(via_puente) LIKE '%carretera%' OR
                      LOWER(via_puente) LIKE '%ruta%'     OR
                      LOWER(via_puente) LIKE '%via%'      OR
                      LOWER(via_puente) LIKE '%vía%'      OR
                      LOWER(via_puente) LIKE '%tramo%'),
            puente = LOWER(via_puente) LIKE '%puente%'
        WHERE via_puente <> '';
    END IF;
END $$;

-- ============================================================================
-- 3. CHECKs (via y puente) idempotentes
-- ============================================================================
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'via' AND conrelid = 'edan.edan_localidades_danos_viales'::regclass
    ) THEN
        ALTER TABLE edan.edan_localidades_danos_viales
            ADD CONSTRAINT via CHECK (via IN (true, false));
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'puente' AND conrelid = 'edan.edan_localidades_danos_viales'::regclass
    ) THEN
        ALTER TABLE edan.edan_localidades_danos_viales
            ADD CONSTRAINT puente CHECK (puente IN (true, false));
    END IF;
END $$;

-- ============================================================================
-- 4. Eliminar la columna de texto via_puente
-- ============================================================================
ALTER TABLE edan.edan_localidades_danos_viales DROP COLUMN IF EXISTS via_puente;

COMMIT;

SELECT 'IDEMPOTENT OK v2.1.0' AS resultado;
