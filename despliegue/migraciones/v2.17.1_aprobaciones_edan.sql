-- ============================================================================
-- SINAGERSAT - Migración v2.17.1 (idempotente)
-- Aprobaciones EDAN: tabla por nivel en lugar de 4 booleanos.
--
--   - Crea edan.aprobaciones_edan (1 fila por nivel ugr/alcalde/dgr/videcid)
--     con estado, observación (motivo de devolución), quién y cuándo.
--   - Backfill desde los 4 booleanos aprob_* de edan.edan (true -> 'aprobado',
--     false -> 'pendiente').
--   - Elimina los 4 booleanos de edan.edan: la tabla nueva pasa a ser la
--     fuente única de verdad de las aprobaciones.
--
--   edan.estado_edan (ciclo de vida del formulario) NO se toca.
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. Tabla aprobaciones por nivel
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS edan.aprobaciones_edan (
    id_aprobacion BIGSERIAL PRIMARY KEY,
    id_edan       BIGINT      NOT NULL REFERENCES edan.edan (id_edan) ON DELETE CASCADE,
    nivel         VARCHAR(20) NOT NULL CHECK (nivel IN ('ugr', 'alcalde', 'dgr', 'videcid')),
    ordinal       SMALLINT    NOT NULL CHECK (ordinal BETWEEN 1 AND 4),
    estado        VARCHAR(20) NOT NULL DEFAULT 'pendiente'
                  CHECK (estado IN ('pendiente', 'aprobado', 'observado', 'espera_correccion')),
    observacion   TEXT,
    por           INTEGER     REFERENCES usuarios.usuario (id_usuario),
    fecha         TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (id_edan, nivel)
);

COMMENT ON TABLE edan.aprobaciones_edan IS
    'Aprobaciones del EDAN por nivel (ugr=1 -> alcalde=2 -> dgr=3 -> videcid=4). '
    'observacion = motivo de la devolución.';

-- ----------------------------------------------------------------------------
-- 2. Backfill desde los booleanos (solo si la tabla está vacía y existen)
-- ----------------------------------------------------------------------------
DO $$
DECLARE
    v_tiene_bool boolean;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'edan' AND table_name = 'edan'
          AND column_name = 'aprob_ugr'
    ) INTO v_tiene_bool;

    IF v_tiene_bool AND NOT EXISTS (SELECT 1 FROM edan.aprobaciones_edan) THEN
        INSERT INTO edan.aprobaciones_edan (id_edan, nivel, ordinal, estado)
        SELECT e.id_edan, v.nivel, v.ordinal,
               CASE WHEN (v.nivel = 'ugr'     AND e.aprob_ugr)
                     OR (v.nivel = 'alcalde' AND e.aprob_alcalde)
                     OR (v.nivel = 'dgr'      AND e.aprob_dgr)
                     OR (v.nivel = 'videcid'  AND e.aprob_videcid)
                    THEN 'aprobado'
                    ELSE 'pendiente'
               END
        FROM edan.edan e
        CROSS JOIN (VALUES ('ugr', 1), ('alcalde', 2), ('dgr', 3), ('videcid', 4)) AS v(nivel, ordinal)
        ORDER BY e.id_edan, v.ordinal;

        RAISE NOTICE 'v2.17.1: backfill de aprobaciones completado';
    END IF;
END $$;

-- ----------------------------------------------------------------------------
-- 3. Fuente única de verdad: eliminar los booleanos de edan.edan
-- ----------------------------------------------------------------------------
ALTER TABLE edan.edan DROP COLUMN IF EXISTS aprob_ugr;
ALTER TABLE edan.edan DROP COLUMN IF EXISTS aprob_alcalde;
ALTER TABLE edan.edan DROP COLUMN IF EXISTS aprob_dgr;
ALTER TABLE edan.edan DROP COLUMN IF EXISTS aprob_videcid;

COMMIT;

SELECT 'IDEMPOTENT OK v2.17.1 aprobaciones_edan' AS resultado;