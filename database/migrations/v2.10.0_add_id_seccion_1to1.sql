-- ============================================================================
-- Migración v2.10.0: Agregar id_seccion a tablas 1:1
-- ============================================================================
-- Objetivo: Estandarizar todas las tablas de secciones para usar id_seccion
-- como clave de deduplicación durante la sincronización offline.
--
-- Tablas afectadas:
--   1. edan_localidades_primera_respuesta (1:1)
--   2. edan_localidades_salud_necesidades (1:1)
--   3. edan_localidades_necesidades_humanitarias (1:1)
--
-- NOTA sobre índices únicos:
-- PostgreSQL ya permite múltiples NULLs en un índice UNIQUE (NULL != NULL).
-- Por eso NO se usa WHERE id_seccion IS NOT NULL.
-- Con un índice parcial (WHERE), ON CONFLICT (id_seccion) falla con:
--   "there is no unique or exclusion constraint matching the ON CONFLICT specification"
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. Agregar columna id_seccion a las 3 tablas 1:1
-- ============================================================================

-- 1.1 Primera Respuesta
ALTER TABLE edan.edan_localidades_primera_respuesta 
ADD COLUMN IF NOT EXISTS id_seccion VARCHAR(50);

-- 1.2 Salud Necesidades
ALTER TABLE edan.edan_localidades_salud_necesidades 
ADD COLUMN IF NOT EXISTS id_seccion VARCHAR(50);

-- 1.3 Necesidades Humanitarias
ALTER TABLE edan.edan_localidades_necesidades_humanitarias 
ADD COLUMN IF NOT EXISTS id_seccion VARCHAR(50);

-- ============================================================================
-- 2. Crear índices únicos SIN WHERE clause
--    PostgreSQL permite múltiples NULLs en UNIQUE indexes (NULL != NULL)
--    y ON CONFLICT (id_seccion) requiere índice sin WHERE.
-- ============================================================================

-- 2.1 Primera Respuesta
DROP INDEX IF EXISTS edan.idx_seccion_primera_respuesta;
CREATE UNIQUE INDEX idx_seccion_primera_respuesta 
ON edan.edan_localidades_primera_respuesta (id_seccion);

-- 2.2 Salud Necesidades
DROP INDEX IF EXISTS edan.idx_seccion_salud_necesidades;
CREATE UNIQUE INDEX idx_seccion_salud_necesidades 
ON edan.edan_localidades_salud_necesidades (id_seccion);

-- 2.3 Necesidades Humanitarias
DROP INDEX IF EXISTS edan.idx_seccion_necesidades_humanitarias;
CREATE UNIQUE INDEX idx_seccion_necesidades_humanitarias 
ON edan.edan_localidades_necesidades_humanitarias (id_seccion);

-- ============================================================================
-- 3. Migrar datos existentes (generar id_seccion para filas existentes)
-- ============================================================================

-- 3.1 Primera Respuesta
UPDATE edan.edan_localidades_primera_respuesta 
SET id_seccion = 'pr-' || id_edan_localidad || '-' || SUBSTRING(MD5(RANDOM()::TEXT), 1, 8)
WHERE id_seccion IS NULL;

-- 3.2 Salud Necesidades
UPDATE edan.edan_localidades_salud_necesidades 
SET id_seccion = 'sn-' || id_edan_localidad || '-' || SUBSTRING(MD5(RANDOM()::TEXT), 1, 8)
WHERE id_seccion IS NULL;

-- 3.3 Necesidades Humanitarias
UPDATE edan.edan_localidades_necesidades_humanitarias 
SET id_seccion = 'nh-' || id_edan_localidad || '-' || SUBSTRING(MD5(RANDOM()::TEXT), 1, 8)
WHERE id_seccion IS NULL;

-- ============================================================================
-- 4. Verificación
-- ============================================================================

DO $$
DECLARE
    v_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_count 
    FROM edan.edan_localidades_primera_respuesta 
    WHERE id_seccion IS NULL;
    IF v_count > 0 THEN
        RAISE EXCEPTION 'Primera Respuesta tiene % filas sin id_seccion', v_count;
    END IF;

    SELECT COUNT(*) INTO v_count 
    FROM edan.edan_localidades_salud_necesidades 
    WHERE id_seccion IS NULL;
    IF v_count > 0 THEN
        RAISE EXCEPTION 'Salud Necesidades tiene % filas sin id_seccion', v_count;
    END IF;

    SELECT COUNT(*) INTO v_count 
    FROM edan.edan_localidades_necesidades_humanitarias 
    WHERE id_seccion IS NULL;
    IF v_count > 0 THEN
        RAISE EXCEPTION 'Necesidades Humanitarias tiene % filas sin id_seccion', v_count;
    END IF;

    RAISE NOTICE 'Verificación exitosa: todas las filas tienen id_seccion';
END $$;

COMMIT;
