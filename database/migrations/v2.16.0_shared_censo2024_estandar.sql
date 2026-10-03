-- ============================================================================
-- SINAGERSAT - Migración v2.16.0 (idempotente)
-- Estandariza shared.manzanos / shared.comunidades con la lógica usada en
-- shared.departamento / shared.provincia / shared.municipio:
--   * Renombra `codigo` (clave censal INE) -> `codigo_ine` (sigue siendo PK).
--   * Elimina columnas redundantes derivadas del CSV:
--     area (=> tipo_unidad), ficha, idep, iprov, imun, codigo_departamento,
--     codigo_provincia, codigo_municipio, nombre_dep, nombre_prov, nombre_mun.
--   * Agrega `id_departamento` / `id_provincia` (enteros, espejo de
--     shared.municipio, sin FK) derivados de shared.municipio via id_municipio.
-- La columna `id_municipio` (FK -> shared.municipio) y `geom` se conservan.
-- NO altera el resto del esquema ni las APIs (no rompe relaciones existentes).
-- ============================================================================

BEGIN;

-- ── shared.manzanos ─────────────────────────────────────────────────────────

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_schema='shared' AND table_name='manzanos'
                 AND column_name='codigo')
       AND NOT EXISTS (SELECT 1 FROM information_schema.columns
                       WHERE table_schema='shared' AND table_name='manzanos'
                         AND column_name='codigo_ine') THEN
        ALTER TABLE shared.manzanos RENAME COLUMN codigo TO codigo_ine;
    END IF;
END $$;

ALTER TABLE shared.manzanos
    DROP COLUMN IF EXISTS area,
    DROP COLUMN IF EXISTS ficha,
    DROP COLUMN IF EXISTS idep,
    DROP COLUMN IF EXISTS iprov,
    DROP COLUMN IF EXISTS imun,
    DROP COLUMN IF EXISTS codigo_departamento,
    DROP COLUMN IF EXISTS codigo_provincia,
    DROP COLUMN IF EXISTS codigo_municipio,
    DROP COLUMN IF EXISTS nombre_dep,
    DROP COLUMN IF EXISTS nombre_prov,
    DROP COLUMN IF EXISTS nombre_mun;

ALTER TABLE shared.manzanos
    ADD COLUMN IF NOT EXISTS id_departamento integer,
    ADD COLUMN IF NOT EXISTS id_provincia integer;

UPDATE shared.manzanos m
SET id_departamento = mu.id_departamento,
    id_provincia    = mu.id_provincia
FROM shared.municipio mu
WHERE mu.id = m.id_municipio
  AND (m.id_departamento IS NULL OR m.id_provincia IS NULL);

ALTER TABLE shared.manzanos
    ALTER COLUMN id_departamento SET NOT NULL,
    ALTER COLUMN id_provincia    SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_manzanos_id_departamento ON shared.manzanos (id_departamento);
CREATE INDEX IF NOT EXISTS idx_manzanos_id_provincia    ON shared.manzanos (id_provincia);

-- ── shared.comunidades ──────────────────────────────────────────────────────

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_schema='shared' AND table_name='comunidades'
                 AND column_name='codigo')
       AND NOT EXISTS (SELECT 1 FROM information_schema.columns
                       WHERE table_schema='shared' AND table_name='comunidades'
                         AND column_name='codigo_ine') THEN
        ALTER TABLE shared.comunidades RENAME COLUMN codigo TO codigo_ine;
    END IF;
END $$;

ALTER TABLE shared.comunidades
    DROP COLUMN IF EXISTS area,
    DROP COLUMN IF EXISTS ficha,
    DROP COLUMN IF EXISTS idep,
    DROP COLUMN IF EXISTS iprov,
    DROP COLUMN IF EXISTS imun,
    DROP COLUMN IF EXISTS codigo_departamento,
    DROP COLUMN IF EXISTS codigo_provincia,
    DROP COLUMN IF EXISTS codigo_municipio,
    DROP COLUMN IF EXISTS nombre_dep,
    DROP COLUMN IF EXISTS nombre_prov,
    DROP COLUMN IF EXISTS nombre_mun;

ALTER TABLE shared.comunidades
    ADD COLUMN IF NOT EXISTS id_departamento integer,
    ADD COLUMN IF NOT EXISTS id_provincia integer;

UPDATE shared.comunidades c
SET id_departamento = mu.id_departamento,
    id_provincia    = mu.id_provincia
FROM shared.municipio mu
WHERE mu.id = c.id_municipio
  AND (c.id_departamento IS NULL OR c.id_provincia IS NULL);

ALTER TABLE shared.comunidades
    ALTER COLUMN id_departamento SET NOT NULL,
    ALTER COLUMN id_provincia    SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_comunidades_id_departamento ON shared.comunidades (id_departamento);
CREATE INDEX IF NOT EXISTS idx_comunidades_id_provincia    ON shared.comunidades (id_provincia);

COMMIT;

SELECT 'IDEMPOTENT OK v2.16.0 shared_censo2024_estandar' AS resultado;