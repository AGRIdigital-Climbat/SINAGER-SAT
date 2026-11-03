-- ============================================================================
-- SINAGERSAT API v2.30.0
-- Migración: Reestructurar SINB (eliminar observación biocultural, 
--            recomendaciones simplificadas, geografía en pronósticos)
-- ============================================================================
-- Autor: migración automática
-- Fecha: 2026-10-04
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. ELIMINAR OBSERVACIÓN BIO CULTURAL
-- ============================================================================

-- 1A. Drop vistas (orden: dependientes primero)
DROP VIEW IF EXISTS sinb.v_tendencia_fenologia;
DROP VIEW IF EXISTS sinb.v_primera_observacion;
DROP VIEW IF EXISTS sinb.v_registro_territorial;

-- 1B. Eliminar FK en evidencia primero (para poder drop observacion_registro)
ALTER TABLE sinb.evidencia DROP CONSTRAINT IF EXISTS evidencia_id_observacion_registro_fkey;

-- 1C. Drop tablas hijas de observacion (orden: hijas primero)
DROP TABLE IF EXISTS sinb.observacion_pronostico;
DROP TABLE IF EXISTS sinb.observacion_recomendacion;
DROP TABLE IF EXISTS sinb.observacion_registro;
DROP TABLE IF EXISTS sinb.observacion;

-- 1D. Eliminar columna en evidencia y añadir geografía propia + campos para fotos
ALTER TABLE sinb.evidencia DROP COLUMN IF EXISTS id_observacion_registro;
ALTER TABLE sinb.evidencia ADD COLUMN IF NOT EXISTS coordenadas jsonb,
                            ADD COLUMN IF NOT EXISTS fecha_foto date;
CREATE INDEX IF NOT EXISTS idx_evidencia_coordenadas ON sinb.evidencia USING GIN(coordenadas);
ALTER TABLE sinb.evidencia ADD COLUMN IF NOT EXISTS codigo_comunidad text REFERENCES shared.comunidades(codigo_ine);
ALTER TABLE sinb.evidencia ADD COLUMN IF NOT EXISTS id_municipio   integer REFERENCES shared.municipio(id);
CREATE INDEX IF NOT EXISTS idx_evidencia_geo ON sinb.evidencia(codigo_comunidad, id_municipio);

-- ============================================================================
-- 2. RESTRUCTURAR RECOMENDACIONES
-- ============================================================================

-- 2A. Crear catálogo categoria_recomendacion (patrón de categoria_pronostico_temporal)
CREATE TABLE IF NOT EXISTS sinb.categoria_recomendacion (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre          varchar(100) NOT NULL,
    descripcion     text,
    estado          sinb.estado_registro NOT NULL DEFAULT 'ACTIVO',
    creado_en       timestamptz NOT NULL DEFAULT now(),
    actualizado_en  timestamptz NOT NULL DEFAULT now(),
    creado_por      integer REFERENCES usuarios.usuario(id_usuario),
    version_registro integer NOT NULL DEFAULT 1
);

-- Sembrar categorías generales
INSERT INTO sinb.categoria_recomendacion (id, nombre, descripcion, estado) VALUES
    (gen_random_uuid(), 'Ambiente', 'Recomendaciones relacionadas con el ambiente natural', 'ACTIVO'),
    (gen_random_uuid(), 'Salud', 'Recomendaciones relacionadas con salud comunitaria', 'ACTIVO'),
    (gen_random_uuid(), 'Agua', 'Recomendaciones sobre gestión del agua', 'ACTIVO'),
    (gen_random_uuid(), 'Fauna', 'Recomendaciones sobre fauna y biodiversidad animal', 'ACTIVO'),
    (gen_random_uuid(), 'Flora', 'Recomendaciones sobre flora y vegetación', 'ACTIVO'),
    (gen_random_uuid(), 'Siembra', 'Recomendaciones sobre épocas y lugares de siembra', 'ACTIVO'),
    (gen_random_uuid(), 'Infraestructura', 'Recomendaciones sobre infraestructura comunitaria', 'ACTIVO'),
    (gen_random_uuid(), 'Otro', 'Otras recomendaciones no clasificadas', 'ACTIVO')
ON CONFLICT DO NOTHING;

-- 2B. Añadir columnas nuevas primero
ALTER TABLE sinb.recomendacion_local
    ADD COLUMN IF NOT EXISTS id_indicador_natural uuid REFERENCES sinb.indicador_natural(id),
    ADD COLUMN IF NOT EXISTS titulo varchar(200),
    ADD COLUMN IF NOT EXISTS participantes jsonb NOT NULL DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS comentarios   jsonb NOT NULL DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS es_ingesta    boolean NOT NULL DEFAULT false;

-- 2C. Eliminar FKs antiguas ANTES de migrar datos
ALTER TABLE sinb.recomendacion_local DROP CONSTRAINT IF EXISTS recomendacion_local_id_categoria_fkey;
ALTER TABLE sinb.recomendacion_local DROP CONSTRAINT IF EXISTS recomendacion_local_id_dimension_fkey;

-- 2D. Migrar datos: titulo = texto, categoría → Siembra
DO $$
DECLARE
    cat_siembra uuid;
BEGIN
    SELECT id INTO cat_siembra FROM sinb.categoria_recomendacion WHERE nombre = 'Siembra' LIMIT 1;
    
    UPDATE sinb.recomendacion_local
    SET titulo = COALESCE(texto, 'Recomendación migrada'),
        id_categoria = cat_siembra
    WHERE titulo IS NULL;
END $$;

-- 2E. Nueva FK a categoria_recomendacion
ALTER TABLE sinb.recomendacion_local
    ADD CONSTRAINT recomendacion_local_id_categoria_fkey 
    FOREIGN KEY (id_categoria) REFERENCES sinb.categoria_recomendacion(id) ON DELETE RESTRICT;

-- 2F. Renombrar id_usuario_elabora → id_usuario_subio y actualizar FK
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_schema='sinb' AND table_name='recomendacion_local' 
               AND column_name='id_usuario_elabora') THEN
        ALTER TABLE sinb.recomendacion_local RENAME COLUMN id_usuario_elabora TO id_usuario_subio;
        -- Recrear FK con nuevo nombre
        ALTER TABLE sinb.recomendacion_local
            ADD CONSTRAINT recomendacion_local_id_usuario_subio_fkey
            FOREIGN KEY (id_usuario_subio) REFERENCES usuarios.usuario(id_usuario) ON DELETE SET NULL;
    END IF;
END $$;

-- 2F. Drop tablas auxiliares de recomendacion
DROP TABLE IF EXISTS sinb.variante_local;
DROP TABLE IF EXISTS sinb.categoria_comportamiento;
DROP TABLE IF EXISTS sinb.dimension_recomendacion;

-- ============================================================================
-- 3. GEOGRAFÍA EN PRONÓSTICOS + BACKFILL
-- ============================================================================

-- 3A. Añadir id_municipio a pronostico_largo y pronostico_corto
ALTER TABLE sinb.pronostico_largo ADD COLUMN IF NOT EXISTS id_municipio integer REFERENCES shared.municipio(id);
ALTER TABLE sinb.pronostico_corto ADD COLUMN IF NOT EXISTS id_municipio integer REFERENCES shared.municipio(id);
CREATE INDEX IF NOT EXISTS idx_pronostico_largo_municipio ON sinb.pronostico_largo(id_municipio);
CREATE INDEX IF NOT EXISTS idx_pronostico_corto_municipio ON sinb.pronostico_corto(id_municipio);

-- 3B. Añadir es_ingesta a ambas tablas
ALTER TABLE sinb.pronostico_largo ADD COLUMN IF NOT EXISTS es_ingesta boolean NOT NULL DEFAULT false;
ALTER TABLE sinb.pronostico_corto ADD COLUMN IF NOT EXISTS es_ingesta boolean NOT NULL DEFAULT false;

-- 3C. Backfill id_usuario_subio = 2 (admin) para registros NULL
-- Pronóstico largo
UPDATE sinb.pronostico_largo
SET id_usuario_subio = 2, es_ingesta = true
WHERE id_usuario_subio IS NULL;

-- Pronóstico corto
UPDATE sinb.pronostico_corto
SET id_usuario_subio = 2, es_ingesta = true
WHERE id_usuario_subio IS NULL;

-- Recomendaciones
UPDATE sinb.recomendacion_local
SET id_usuario_subio = 2, es_ingesta = true
WHERE id_usuario_subio IS NULL;

-- ============================================================================
-- 4. ÍNDICES ADICIONALES PARA RANKING
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_pronostico_largo_usuario ON sinb.pronostico_largo(id_usuario_subio);
CREATE INDEX IF NOT EXISTS idx_pronostico_corto_usuario ON sinb.pronostico_corto(id_usuario_subio);
CREATE INDEX IF NOT EXISTS idx_recomendacion_usuario ON sinb.recomendacion_local(id_usuario_subio);
CREATE INDEX IF NOT EXISTS idx_evidencia_usuario ON sinb.evidencia(id_usuario_subio);

COMMIT;

-- ============================================================================
-- FIN MIGRACIÓN v2.30.0
-- ============================================================================
