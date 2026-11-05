-- ============================================================================
-- SINAGERSAT - Migración v1.5.1 (idempotente)
-- Conexión EDAN <-> REA:
--   1. edan.edan.id_reporte_rea -> FK hacia rea.reporte_evento(id_reporte)
--      "REA de origen" (el que generó el EDAN). ON DELETE SET NULL: si se
--      borra el REA, el EDAN sobrevive y el campo queda vacío (NULL).
--   2. rea.reporte_evento.id_edan -> FK hacia edan.edan(id_edan)
--      Permite que UN EDAN agrupe VARIOS REAs (cada REA pertenece a un único
--      EDAN por estructura de una sola columna).
-- Ambos campos son OPCIONALES: un EDAN puede crearse sin REA (campo vacío).
-- Aplica sobre migration_v1.5.0.
-- ============================================================================

BEGIN;

-- 1. Alinear tipo: id_reporte_rea pasa a integer (coincide con rea.reporte_evento.id_reporte)
ALTER TABLE edan.edan ALTER COLUMN id_reporte_rea TYPE integer USING id_reporte_rea::integer;

-- 2. FK del REA de origen (debe existir; si se borra, queda NULL)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'edan_id_reporte_rea_fkey') THEN
        ALTER TABLE edan.edan
            ADD CONSTRAINT edan_id_reporte_rea_fkey
            FOREIGN KEY (id_reporte_rea) REFERENCES rea.reporte_evento(id_reporte)
            ON DELETE SET NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_edan_id_reporte_rea ON edan.edan(id_reporte_rea);

-- 3. Vínculo inverso en el REA: a qué EDAN pertenece (agrupación de varios REAs)
ALTER TABLE rea.reporte_evento ADD COLUMN IF NOT EXISTS id_edan bigint;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'reporte_evento_id_edan_fkey') THEN
        ALTER TABLE rea.reporte_evento
            ADD CONSTRAINT reporte_evento_id_edan_fkey
            FOREIGN KEY (id_edan) REFERENCES edan.edan(id_edan)
            ON DELETE SET NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_reporte_id_edan ON rea.reporte_evento(id_edan);

COMMIT;

SELECT 'IDEMPOTENT OK v1.5.1' AS resultado;
