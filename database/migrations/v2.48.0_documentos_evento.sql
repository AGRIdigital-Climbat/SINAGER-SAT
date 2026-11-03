-- ============================================================================
-- SINAGERSAT - Migración v2.48.0 (idempotente)
-- Repositorio de documentos: el vínculo RIDA pasa de FORMULARIO a EVENTO.
--
--   Contexto: en v2.22.0 los documentos RIDA se guardaban con
--   'documentos.id_formulario_rida' (FK a rida.formulario_rida). El modelo
--   actual hace colgar el RIDA del EVENTO (v2.24.0: rida.evento_rida;
--   v2.41.0: solicitud -> evento; v2.47.0: necesidad sin formulario), asi que
--   los documentos deben colgar tambien del evento:
--
--       id_evento_rida IS NULL      -> 'edan'  (documento de EDAN)
--       id_evento_rida IS NOT NULL  -> 'rida'  (documento de RIDA/evento)
--
--   Un documento de RIDA se guarda con 'id_evento_rida' Y con el 'id_edan'
--   que el evento ya tiene (rida.evento_rida.id_edan), para que quede
--   vinculado a las dos tablas y sea rastreable desde el EDAN.
--
--   Legado: no hay filas historicas con id_formulario_rida hoy, pero el
--   backfill cubre el caso por si re-aparece. La columna vieja luego se
--   elimina: reemplazo total, no convivencia de dos frentes.
--
--   IDEMPOTENCIA: ADD COLUMN IF NOT EXISTS + DROP COLUMN IF EXISTS + DROP
--   INDEX/CONSTRAINT IF EXISTS. Se puede aplicar N veces.
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. Columna nueva + índice
-- ----------------------------------------------------------------------------
ALTER TABLE repositorio.documentos
    ADD COLUMN IF NOT EXISTS id_evento_rida INTEGER
    REFERENCES rida.evento_rida (id_evento_rida) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_documentos_evento_rida
    ON repositorio.documentos (id_evento_rida);

-- ----------------------------------------------------------------------------
-- 2. Backfill desde formulario (solo si la columna vieja todavia existe)
-- ----------------------------------------------------------------------------
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_schema = 'repositorio' AND table_name = 'documentos'
                 AND column_name = 'id_formulario_rida') THEN
        UPDATE repositorio.documentos d
        SET id_evento_rida = f.id_evento_rida,
            id_edan        = COALESCE(d.id_edan, f.id_edan)
        FROM rida.formulario_rida f
        WHERE f.id_formulario = d.id_formulario_rida
          AND d.id_evento_rida IS NULL
          AND f.id_evento_rida IS NOT NULL;
    END IF;
END $$;

-- ----------------------------------------------------------------------------
-- 3. Fuera el vínculo viejo
-- ----------------------------------------------------------------------------
DROP INDEX IF EXISTS idx_documentos_formulario_rida;
ALTER TABLE repositorio.documentos
    DROP CONSTRAINT IF EXISTS documentos_id_formulario_rida_fkey;
ALTER TABLE repositorio.documentos
    DROP COLUMN IF EXISTS id_formulario_rida;

-- ----------------------------------------------------------------------------
-- 4. Comentarios
-- ----------------------------------------------------------------------------
COMMENT ON COLUMN repositorio.documentos.id_edan IS
    'EDAN al que pertenece el documento. NULLABLE solo en casos legacy; en RIDA lo trae heredado de rida.evento_rida.id_edan para que quede rastreable desde la pantalla del EDAN. La API lo escribe, no el cliente.';

COMMENT ON COLUMN repositorio.documentos.id_evento_rida IS
    'Evento RIDA al que pertenece el documento. NULLABLE: NULL = documento de EDAN, no NULL = documento de RIDA. Define el "origen" que expone la API. Lo escribe la API, no el cliente.';

COMMENT ON TABLE repositorio.documentos IS
    'Repositorio de documentos PDF. Un documento es de EDAN (id_evento_rida NULL) o de RIDA (id_evento_rida NOT NULL). El origen se deriva de id_evento_rida, no es una columna.';

COMMIT;
SELECT 'IDEMPOTENT OK v2.48.0 documentos -> evento';