-- ============================================================================
-- SINAGERSAT - Migración v2.23.0 (idempotente)
-- RIDA: Reestructuración de tablas necesidad, cat_articulo, cat_categoria_ayuda
--
-- CAMBIOS:
-- 1. Renombrar columnas para consistencia (id_categoria → id_categoria_ayuda,
--    unidad_medida → unidad_de_medida)
-- 2. Añadir columnas faltantes a necesidad (id_necesidad_off, fecha_creacion,
--    fecha_modificacion)
-- 3. Convertir necesidad.estado de VARCHAR a BOOLEAN
-- 4. Crear triggers para autogenerar códigos (ART-000001, CAT-000001)
--
-- IMPORTANTE:
-- - NO se eliminan tablas ni datos existentes
-- - Se mantiene integridad referencial
-- - Datos existentes en cat_categoria_ayuda se preservan
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. Renombrar PK y secuencia de cat_categoria_ayuda
-- ----------------------------------------------------------------------------

-- Renombrar columna de PK
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'rida' 
          AND table_name = 'cat_categoria_ayuda' 
          AND column_name = 'id_categoria'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'rida' 
          AND table_name = 'cat_categoria_ayuda' 
          AND column_name = 'id_categoria_ayuda'
    ) THEN
        ALTER TABLE rida.cat_categoria_ayuda 
            RENAME COLUMN id_categoria TO id_categoria_ayuda;
    END IF;
END $$;

-- Renombrar secuencia asociada
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_class WHERE relname = 'cat_categoria_ayuda_id_categoria_seq' AND relnamespace = 'rida'::regnamespace) THEN
        ALTER SEQUENCE rida.cat_categoria_ayuda_id_categoria_seq 
            RENAME TO cat_categoria_ayuda_id_categoria_ayuda_seq;
    END IF;
END $$;

-- Actualizar el DEFAULT de la PK para usar la secuencia renombrada
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'rida' 
          AND table_name = 'cat_categoria_ayuda' 
          AND column_name = 'id_categoria_ayuda'
          AND column_default NOT LIKE '%id_categoria_ayuda_seq%'
    ) THEN
        ALTER TABLE rida.cat_categoria_ayuda 
            ALTER COLUMN id_categoria_ayuda SET DEFAULT nextval('rida.cat_categoria_ayuda_id_categoria_ayuda_seq'::regclass);
    END IF;
END $$;

-- Renombrar constraint de PK si existe con nombre antiguo
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'cat_categoria_ayuda_pkey' AND connamespace = 'rida'::regnamespace) THEN
        -- El nombre ya es correcto, no hacer nada
        NULL;
    END IF;
END $$;

-- ----------------------------------------------------------------------------
-- 2. Renombrar columnas en cat_articulo
-- ----------------------------------------------------------------------------

-- Renombrar id_categoria → id_categoria_ayuda en cat_articulo
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'rida' 
          AND table_name = 'cat_articulo' 
          AND column_name = 'id_categoria'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'rida' 
          AND table_name = 'cat_articulo' 
          AND column_name = 'id_categoria_ayuda'
    ) THEN
        ALTER TABLE rida.cat_articulo 
            RENAME COLUMN id_categoria TO id_categoria_ayuda;
    END IF;
END $$;

-- Renombrar unidad_medida → unidad_de_medida en cat_articulo
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'rida' 
          AND table_name = 'cat_articulo' 
          AND column_name = 'unidad_medida'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'rida' 
          AND table_name = 'cat_articulo' 
          AND column_name = 'unidad_de_medida'
    ) THEN
        ALTER TABLE rida.cat_articulo 
            RENAME COLUMN unidad_medida TO unidad_de_medida;
    END IF;
END $$;

-- Actualizar nombre del constraint FK en cat_articulo
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'cat_articulo_id_categoria_fkey' AND connamespace = 'rida'::regnamespace) THEN
        ALTER TABLE rida.cat_articulo 
            RENAME CONSTRAINT cat_articulo_id_categoria_fkey TO cat_articulo_id_categoria_ayuda_fkey;
    END IF;
END $$;

-- ----------------------------------------------------------------------------
-- 3. Renombrar columnas en necesidad
-- ----------------------------------------------------------------------------

-- Renombrar id_categoria → id_categoria_ayuda en necesidad
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'rida' 
          AND table_name = 'necesidad' 
          AND column_name = 'id_categoria'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'rida' 
          AND table_name = 'necesidad' 
          AND column_name = 'id_categoria_ayuda'
    ) THEN
        ALTER TABLE rida.necesidad 
            RENAME COLUMN id_categoria TO id_categoria_ayuda;
    END IF;
END $$;

-- Renombrar unidad_medida → unidad_de_medida en necesidad
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'rida' 
          AND table_name = 'necesidad' 
          AND column_name = 'unidad_medida'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'rida' 
          AND table_name = 'necesidad' 
          AND column_name = 'unidad_de_medida'
    ) THEN
        ALTER TABLE rida.necesidad 
            RENAME COLUMN unidad_medida TO unidad_de_medida;
    END IF;
END $$;

-- Actualizar nombre del constraint FK en necesidad
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'necesidad_id_categoria_fkey' AND connamespace = 'rida'::regnamespace) THEN
        ALTER TABLE rida.necesidad 
            RENAME CONSTRAINT necesidad_id_categoria_fkey TO necesidad_id_categoria_ayuda_fkey;
    END IF;
END $$;

-- ----------------------------------------------------------------------------
-- 4. Añadir columnas faltantes a necesidad
-- ----------------------------------------------------------------------------

-- Añadir id_necesidad_off si no existe
ALTER TABLE rida.necesidad 
    ADD COLUMN IF NOT EXISTS id_necesidad_off VARCHAR(50);

-- Añadir fecha_creacion si no existe
ALTER TABLE rida.necesidad 
    ADD COLUMN IF NOT EXISTS fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Añadir fecha_modificacion si no existe
ALTER TABLE rida.necesidad 
    ADD COLUMN IF NOT EXISTS fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- ----------------------------------------------------------------------------
-- 5. Convertir necesidad.estado de VARCHAR a BOOLEAN
-- ----------------------------------------------------------------------------

-- Paso 1: Añadir columna temporal booleana
ALTER TABLE rida.necesidad 
    ADD COLUMN IF NOT EXISTS estado_bool BOOLEAN DEFAULT FALSE;

-- Paso 2: Migrar datos (PENDIENTE→false, COMPLETADA/TRUE→true, otros→false)
UPDATE rida.necesidad 
SET estado_bool = CASE 
    WHEN estado ILIKE 'COMPLETADA' OR estado ILIKE 'TRUE' OR estado ILIKE 'SI' OR estado = '1' THEN TRUE
    ELSE FALSE 
END
WHERE estado_bool IS NULL AND estado IS NOT NULL;

-- Paso 3: Eliminar columna antigua VARCHAR
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'rida' 
          AND table_name = 'necesidad' 
          AND column_name = 'estado'
          AND data_type = 'character varying'
    ) THEN
        ALTER TABLE rida.necesidad DROP COLUMN estado;
    END IF;
END $$;

-- Paso 4: Renombrar columna booleana a 'estado'
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'rida' 
          AND table_name = 'necesidad' 
          AND column_name = 'estado_bool'
    ) THEN
        ALTER TABLE rida.necesidad RENAME COLUMN estado_bool TO estado;
    END IF;
END $$;

-- Paso 5: Asegurar DEFAULT FALSE
ALTER TABLE rida.necesidad 
    ALTER COLUMN estado SET DEFAULT FALSE;

-- ----------------------------------------------------------------------------
-- 6. Crear trigger para autogenerar código en cat_articulo (ART-000001)
-- ----------------------------------------------------------------------------

-- Función para generar código de artículo
CREATE OR REPLACE FUNCTION rida.fn_generar_codigo_articulo()
RETURNS TRIGGER AS $$
BEGIN
    -- Solo generar si el código es NULL o vacío
    IF NEW.codigo IS NULL OR NEW.codigo = '' THEN
        SELECT 'ART-' || LPAD(nextval('rida.cat_articulo_codigo_seq'::regclass)::TEXT, 6, '0')
        INTO NEW.codigo;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Secuencia para códigos de artículo
CREATE SEQUENCE IF NOT EXISTS rida.cat_articulo_codigo_seq START WITH 1;

-- Trigger para cat_articulo
DROP TRIGGER IF EXISTS trg_generar_codigo_articulo ON rida.cat_articulo;
CREATE TRIGGER trg_generar_codigo_articulo
    BEFORE INSERT ON rida.cat_articulo
    FOR EACH ROW
    EXECUTE FUNCTION rida.fn_generar_codigo_articulo();

-- ----------------------------------------------------------------------------
-- 7. Crear trigger para autogenerar código en cat_categoria_ayuda (CAT-000001)
-- ----------------------------------------------------------------------------

-- Función para generar código de categoría
CREATE OR REPLACE FUNCTION rida.fn_generar_codigo_categoria()
RETURNS TRIGGER AS $$
BEGIN
    -- Solo generar si el código es NULL o vacío
    IF NEW.codigo IS NULL OR NEW.codigo = '' THEN
        SELECT 'CAT-' || LPAD(nextval('rida.cat_categoria_ayuda_codigo_seq'::regclass)::TEXT, 6, '0')
        INTO NEW.codigo;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Secuencia para códigos de categoría (iniciar después de los 5 existentes)
CREATE SEQUENCE IF NOT EXISTS rida.cat_categoria_ayuda_codigo_seq START WITH 6;

-- Trigger para cat_categoria_ayuda
DROP TRIGGER IF EXISTS trg_generar_codigo_categoria ON rida.cat_categoria_ayuda;
CREATE TRIGGER trg_generar_codigo_categoria
    BEFORE INSERT ON rida.cat_categoria_ayuda
    FOR EACH ROW
    EXECUTE FUNCTION rida.fn_generar_codigo_categoria();

-- ----------------------------------------------------------------------------
-- 8. Añadir índices para columnas de sincronización
-- ----------------------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_necesidad_id_necesidad_off 
    ON rida.necesidad (id_necesidad_off) WHERE id_necesidad_off IS NOT NULL;

-- ----------------------------------------------------------------------------
-- 9. Actualizar comentarios de columnas
-- ----------------------------------------------------------------------------

COMMENT ON COLUMN rida.necesidad.id_necesidad_off IS 'Identificador único para sincronización offline (generado por el cliente)';
COMMENT ON COLUMN rida.necesidad.fecha_creacion IS 'Fecha y hora de creación del registro (auto-generada)';
COMMENT ON COLUMN rida.necesidad.fecha_modificacion IS 'Fecha y hora de última modificación (auto-actualizada)';
COMMENT ON COLUMN rida.necesidad.estado IS 'Estado de la necesidad: FALSE=pendiente, TRUE=completada';
COMMENT ON COLUMN rida.cat_articulo.codigo IS 'Código único autogenerado (formato: ART-000001)';
COMMENT ON COLUMN rida.cat_categoria_ayuda.codigo IS 'Código único autogenerado (formato: CAT-000001)';

COMMIT;

SELECT 'IDEMPOTENT OK v2.23.0 rida_necesidad_articulo_estructura' AS resultado;
