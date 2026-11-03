-- ============================================================================
-- v2.38.0 Pronóstico largo: recomendaciones en texto libre + confianza por escenario
-- ============================================================================
-- 1) recomendaciones: deja de ser un catálogo FK (sinb.recomendacion +
--    comportamiento_recomendacion + puente) y pasa a texto libre que escribe
--    el productor. Cada recomendación conserva SU id y SU id offline + nombre.
-- 2) escenarios: la probabilidad 0-100 se sustituye por confianza
--    ALTA | MEDIA | BAJA (mismo enum que el pronóstico de corto plazo).
-- 3) se elimina sinb.pronostico_largo_item.confianza (numeric 0..1), siempre
--    NULL en las 222 filas existentes y en conflicto con la nueva confianza.
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 0. Enum de confianza (ya existe en prod; declarado aquí para repliegue limpio)
-- ----------------------------------------------------------------------------
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_type t
        JOIN pg_namespace n ON n.oid = t.typnamespace
        WHERE n.nspname = 'sinb' AND t.typname = 'confianza_nivel'
    ) THEN
        CREATE TYPE sinb.confianza_nivel AS ENUM ('ALTA', 'MEDIA', 'BAJA');
    END IF;
END $$;

-- ----------------------------------------------------------------------------
-- 1. Recomendaciones en texto libre
-- ----------------------------------------------------------------------------
-- 1.1 columna de texto y respaldo de los nombres del catálogo (91 filas)
ALTER TABLE sinb.pronostico_largo_recomendacion ADD COLUMN nombre text;

UPDATE sinb.pronostico_largo_recomendacion pr
   SET nombre = r.nombre
  FROM sinb.recomendacion r
 WHERE r.id = pr.id_recomendacion;

DELETE FROM sinb.pronostico_largo_recomendacion WHERE nombre IS NULL;

ALTER TABLE sinb.pronostico_largo_recomendacion ALTER COLUMN nombre SET NOT NULL;
COMMENT ON COLUMN sinb.pronostico_largo_recomendacion.nombre
    IS 'Texto libre: lo que el productor recomienda hacer';

-- 1.2 soltar la FK al catálogo y su unique (una recomendación ya no es una fila de catálogo)
ALTER TABLE sinb.pronostico_largo_recomendacion
    DROP CONSTRAINT IF EXISTS pronostico_largo_recomendacion_id_recomendacion_fkey;
ALTER TABLE sinb.pronostico_largo_recomendacion
    DROP CONSTRAINT IF EXISTS uq_pronostico_recomendacion;
ALTER TABLE sinb.pronostico_largo_recomendacion
    DROP COLUMN IF EXISTS id_recomendacion;

-- 1.3 eliminar el catálogo y el puente de comportamientos (0 filas en el puente)
DROP TABLE IF EXISTS sinb.pronostico_largo_recomendacion_comportamiento;
DROP TABLE IF EXISTS sinb.comportamiento_recomendacion;
DROP TABLE IF EXISTS sinb.recomendacion;

-- ----------------------------------------------------------------------------
-- 2. Escenarios: probabilidad -> confianza ALTA/MEDIA/BAJA
-- ----------------------------------------------------------------------------
ALTER TABLE sinb.escenario_estacional
    ADD COLUMN confianza sinb.confianza_nivel;
COMMENT ON COLUMN sinb.escenario_estacional.confianza
    IS 'Nivel de confianza del escenario (enum igual que pronóstico de corto plazo)';

-- Las 230 filas existentes tienen probabilidad=100 (dummy) => confianza queda NULL
ALTER TABLE sinb.escenario_estacional DROP COLUMN probabilidad;

-- ----------------------------------------------------------------------------
-- 3. Eliminar la confianza numérica del bloque (222 filas, 0 con valor)
-- ----------------------------------------------------------------------------
ALTER TABLE sinb.pronostico_largo_item DROP COLUMN confianza;

COMMIT;

-- Verificación
-- \d sinb.pronostico_largo_recomendacion   -- debe tener id, id_pronostico_largo, nombre, id_recomendacion_off, creado_en
-- \d sinb.escenario_estacional             -- confianza sinb.confianza_nivel, sin probabilidad
-- SELECT count(*) FROM information_schema.columns
--  WHERE table_schema='sinb' AND table_name='pronostico_largo_item' AND column_name='confianza';  -- 0
