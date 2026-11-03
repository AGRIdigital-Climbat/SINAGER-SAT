-- ============================================================================
-- SINAGERSAT API v2.31.2
-- Eliminar tablas obsoletas después de unificación
-- ============================================================================

BEGIN;

-- Tablas SINB sin datos y sin referencias
DROP TABLE IF EXISTS sinb.pronostico_digital CASCADE;
DROP TABLE IF EXISTS sinb.avisos_observador CASCADE;
DROP TABLE IF EXISTS sinb.norma_climatica CASCADE;
DROP TABLE IF EXISTS sinb.ventana_observacion CASCADE;
DROP TABLE IF EXISTS sinb.serie_climatica CASCADE;
DROP TABLE IF EXISTS sinb.serie_indicador CASCADE;
DROP TABLE IF EXISTS sinb.desviacion_indicador CASCADE;
DROP TABLE IF EXISTS sinb.calificacion_indicador CASCADE;
DROP TABLE IF EXISTS sinb.sinonimo_indicador CASCADE;
DROP TABLE IF EXISTS sinb.zona_comunidad CASCADE;
DROP TABLE IF EXISTS sinb.zona_manzano CASCADE;

-- FK duplicada en pronostico_corto (limpieza)
ALTER TABLE sinb.pronostico_corto DROP CONSTRAINT IF EXISTS pronostico_temporal_id_categoria_fkey;

COMMIT;
