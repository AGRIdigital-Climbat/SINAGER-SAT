-- ============================================================================
-- SINAGERSAT - Migración v2.17.0 (idempotente)
-- Agrega el dato oficial de HOGARES del CPV-2024 (equivalente censal del
-- concepto "familias") al módulo Censo 2024:
--   * shared.manzanos.hogares / shared.comunidades.hogares
--       Hogares = viviendas particulares ocupadas con personas presentes
--       (INE, campo viv_tipo_presentes de la ficha del geoportal).
--       NULL = unidad sin ficha (reserva estadística del INE, sin dato oficial).
--   * shared.censo2024_hogares_municipio
--       Cifra EXACTA de hogares por municipio tomada del tabulado oficial
--       "Vivienda y hogar" del INE (343 municipios, cobertura completa).
--       Es la base más oficial para ratios (personas por hogar).
-- NO altera columnas existentes ni elimina nada (los JSON de las APIs solo
-- ganan campos; la forma de la respuesta no cambia).
-- ============================================================================

BEGIN;

ALTER TABLE shared.manzanos
    ADD COLUMN IF NOT EXISTS hogares integer
        CHECK (hogares IS NULL OR hogares >= 0);

ALTER TABLE shared.comunidades
    ADD COLUMN IF NOT EXISTS hogares integer
        CHECK (hogares IS NULL OR hogares >= 0);

CREATE TABLE IF NOT EXISTS shared.censo2024_hogares_municipio (
    id_municipio integer PRIMARY KEY REFERENCES shared.municipio (id),
    hogares      integer NOT NULL CHECK (hogares >= 0),
    fuente       text    NOT NULL DEFAULT 'INE tabulado Vivienda y hogar',
    actualizado_en timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE shared.censo2024_hogares_municipio IS
    'Hogares exactos por municipio segun el tabulado oficial INE CPV-2024 (Vivienda y hogar)';
COMMENT ON COLUMN shared.manzanos.hogares IS
    'Hogares INE (viviendas particulares ocupadas con personas presentes); NULL sin ficha';
COMMENT ON COLUMN shared.comunidades.hogares IS
    'Hogares INE (viviendas particulares ocupadas con personas presentes); NULL sin ficha';

COMMIT;

SELECT 'IDEMPOTENT OK v2.17.0 shared_censo2024_hogares' AS resultado;
