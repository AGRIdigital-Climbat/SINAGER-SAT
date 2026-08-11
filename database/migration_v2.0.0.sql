-- ============================================================================
-- SINAGERSAT - Migración v2.0.0 (idempotente)
-- edan.edan_localidades: renombra la columna "nombre" a "localidad".
-- Semántica: una localidad tiene un nombre propio (la comunidad afectada);
-- el UGR decide qué localidades (fila por comunidad) se agrupan bajo un EDAN.
-- Aplica sobre migration_v1.9.0.
-- ============================================================================

BEGIN;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'edan'
          AND table_name   = 'edan_localidades'
          AND column_name  = 'nombre'
    ) THEN
        ALTER TABLE edan.edan_localidades RENAME COLUMN nombre TO localidad;
    END IF;
END $$;

COMMIT;

SELECT 'IDEMPOTENT OK v2.0.0' AS resultado;
