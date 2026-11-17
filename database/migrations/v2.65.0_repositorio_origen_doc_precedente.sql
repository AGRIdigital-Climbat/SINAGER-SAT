-- ============================================================================
-- SINAGERSAT - Migración v2.65.0 (idempotente)
-- Repositorio de documentos: origen explícito EDAN|RIDA|DOC_PRECEDENTE y
-- soporte para documentos de respaldo municipal (DOC_PRECEDENTE).
--
--   Contexto:
--   - v2.48.0 derivaba el origen de id_evento_rida (NULL=edan, NOT NULL=rida).
--     Eso impide distinguir un documento de respaldo general (sin EDAN y sin
--     evento RIDA) de uno de EDAN.
--   - Se agrega columna explicita 'origen' con valores EDAN, RIDA,
--     DOC_PRECEDENTE. Se hace backfill desde el estado actual y se mantiene
--     id_edan/id_evento_rida como columnas de vínculo (compatibles).
--   - DOC_PRECEDENTE: subida municipal (municipio sube respaldos generales);
--     la vista/consulta es nacional y se filtra por geografía
--     (departamento/provincia/municipio). No lleva id_edan ni id_evento_rida.
--
--   Contratos EDAN/RIDA existentes NO cambian.
--
--   IDEMPOTENCIA: ADD COLUMN IF NOT EXISTS, DO $$ condicionales, constraints
--   con nombres fijos y IF NOT EXISTS donde aplica. Reaplicable.
-- ============================================================================

BEGIN;

-- 1. Columna origen explícita
ALTER TABLE repositorio.documentos
    ADD COLUMN IF NOT EXISTS origen varchar(20);

-- 2. Backfill (solo donde falte) desde el estado actual
UPDATE repositorio.documentos
SET origen = CASE
    WHEN id_evento_rida IS NOT NULL THEN 'RIDA'
    ELSE 'EDAN'
END
WHERE origen IS NULL;

-- 3. Default y NOT NULL
ALTER TABLE repositorio.documentos
    ALTER COLUMN origen SET DEFAULT 'EDAN';

ALTER TABLE repositorio.documentos
    ALTER COLUMN origen SET NOT NULL;

-- 4. Constraint de dominio (EDAN|RIDA|DOC_PRECEDENTE)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'chk_documentos_origen'
          AND conrelid = 'repositorio.documentos'::regclass
    ) THEN
        ALTER TABLE repositorio.documentos
            ADD CONSTRAINT chk_documentos_origen
            CHECK (origen IN ('EDAN', 'RIDA', 'DOC_PRECEDENTE'));
    END IF;
END $$;

-- 5. Consistencia origen <-> vínculos
--    EDAN:           id_evento_rida NULL (id_edan puede ser NULL por legado)
--    RIDA:           id_evento_rida NOT NULL
--    DOC_PRECEDENTE: sin id_edan ni id_evento_rida (respaldo municipal)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'chk_documentos_origen_vinculos'
          AND conrelid = 'repositorio.documentos'::regclass
    ) THEN
        ALTER TABLE repositorio.documentos
            ADD CONSTRAINT chk_documentos_origen_vinculos
            CHECK (
                (origen = 'RIDA' AND id_evento_rida IS NOT NULL)
                OR (origen = 'EDAN' AND id_evento_rida IS NULL)
                OR (origen = 'DOC_PRECEDENTE' AND id_evento_rida IS NULL AND id_edan IS NULL)
            );
    END IF;
END $$;

-- 6. Índices para filtros (listado general / geografía)
CREATE INDEX IF NOT EXISTS idx_documentos_origen
    ON repositorio.documentos (origen);

CREATE INDEX IF NOT EXISTS idx_documentos_id_municipio
    ON repositorio.documentos (id_municipio);

CREATE INDEX IF NOT EXISTS idx_documentos_fecha_documento
    ON repositorio.documentos (fecha_documento DESC);

-- 7. Comentarios
COMMENT ON COLUMN repositorio.documentos.origen IS
    'Origen del documento (asignado por la API según la ruta de subida): EDAN, RIDA o DOC_PRECEDENTE (respaldo municipal, sin id_edan/id_evento_rida).';

COMMENT ON COLUMN repositorio.documentos.id_edan IS
    'EDAN al que pertenece el documento. NULL en DOC_PRECEDENTE y en casos legacy EDAN; en RIDA se hereda de rida.evento_rida.id_edan.';

COMMENT ON COLUMN repositorio.documentos.id_evento_rida IS
    'Evento RIDA al que pertenece el documento. NOT NULL solo cuando origen=RIDA.';

COMMENT ON TABLE repositorio.documentos IS
    'Repositorio de documentos PDF. Origen explícito: EDAN, RIDA (vinculado a evento/EDAN) o DOC_PRECEDENTE (respaldo municipal, vinculado a geografía y usuario que sube). Consulta de vista nacional con filtros geográficos.';

COMMIT;
SELECT 'IDEMPOTENT OK v2.65.0 repositorio origen DOC_PRECEDENTE';
