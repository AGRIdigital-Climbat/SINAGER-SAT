-- ============================================================================
-- SINAGERSAT - Migración v2.46.0 (idempotente)
-- RIDA: codigo propio de rida.evento_rida
--
-- El evento RIDA nace de un EDAN aprobado (1:1). Su codigo es el del EDAN con
-- sufijo "-R": ej. 070101/2026/002 -> 070101/2026/002-R.
-- Se genera en habilitar_evento(); este script crea la columna y hace el
-- backfill de los eventos existentes.
--
-- Regla de negocio (confirmada): un EDAN SIN codigo_edan no puede habilitar
-- RIDA (habilitar responde 400), por lo que todo evento nuevo lleva codigo.
-- Los eventos heredados de EDAN migrados sin codigo quedarian en NULL y solo
-- serian consultables por id.
-- ============================================================================

BEGIN;

ALTER TABLE rida.evento_rida ADD COLUMN IF NOT EXISTS codigo VARCHAR(35);

-- Backfill: codigo_edan + '-R' para los eventos que ya existen.
UPDATE rida.evento_rida ev
SET codigo = e.codigo_edan || '-R'
FROM edan.edan e
WHERE e.id_edan = ev.id_edan
  AND ev.codigo IS NULL
  AND e.codigo_edan IS NOT NULL;

-- Unicidad (los eventos sin codigo quedarian todos en NULL, permitido por
-- UNIQUE de PostgreSQL; habilitar nunca los genera).
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'evento_rida_codigo_key'
          AND conrelid = 'rida.evento_rida'::regclass
    ) THEN
        ALTER TABLE rida.evento_rida
            ADD CONSTRAINT evento_rida_codigo_key UNIQUE (codigo);
    END IF;

    -- NOT NULL solo si el backfill no dejo ningun NULL (datos legados).
    IF NOT EXISTS (SELECT 1 FROM rida.evento_rida WHERE codigo IS NULL) THEN
        ALTER TABLE rida.evento_rida ALTER COLUMN codigo SET NOT NULL;
    END IF;
END $$;

SELECT 'IDEMPOTENT OK v2.46.0 evento_rida.codigo' AS resultado,
       (SELECT string_agg(id_evento_rida || '=' || codigo, ', ' ORDER BY id_evento_rida)
        FROM rida.evento_rida) AS codigos;

COMMIT;
