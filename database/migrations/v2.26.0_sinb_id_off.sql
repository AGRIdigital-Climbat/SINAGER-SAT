-- SINAGERSAT/BaseData - Migración v2.26.0
-- Agregar columnas id_off para sincronización offline en esquema sinb
-- Autor: opencode | Fecha: 2026-10-03

-- ============================================================================
-- TABLAS TRANSACCIONALES SINB CON ID_OFFLINE
-- ============================================================================

-- 1. observacion
ALTER TABLE sinb.observacion 
    ADD COLUMN IF NOT EXISTS id_off VARCHAR(36);

CREATE INDEX IF NOT EXISTS idx_observacion_id_off 
    ON sinb.observacion (id_off) 
    WHERE id_off IS NOT NULL;

COMMENT ON COLUMN sinb.observacion.id_off IS 
    'Identificador único generado por el dispositivo para sincronización offline';

-- 2. observacion_registro
ALTER TABLE sinb.observacion_registro 
    ADD COLUMN IF NOT EXISTS id_off VARCHAR(36);

CREATE INDEX IF NOT EXISTS idx_observacion_registro_id_off 
    ON sinb.observacion_registro (id_off) 
    WHERE id_off IS NOT NULL;

COMMENT ON COLUMN sinb.observacion_registro.id_off IS 
    'Identificador único generado por el dispositivo para sincronización offline';

-- 3. pronostico_estacional
ALTER TABLE sinb.pronostico_estacional 
    ADD COLUMN IF NOT EXISTS id_off VARCHAR(36);

CREATE INDEX IF NOT EXISTS idx_pronostico_estacional_id_off 
    ON sinb.pronostico_estacional (id_off) 
    WHERE id_off IS NOT NULL;

COMMENT ON COLUMN sinb.pronostico_estacional.id_off IS 
    'Identificador único generado por el dispositivo para sincronización offline';

-- 4. pronostico_temporal
ALTER TABLE sinb.pronostico_temporal 
    ADD COLUMN IF NOT EXISTS id_off VARCHAR(36);

CREATE INDEX IF NOT EXISTS idx_pronostico_temporal_id_off 
    ON sinb.pronostico_temporal (id_off) 
    WHERE id_off IS NOT NULL;

COMMENT ON COLUMN sinb.pronostico_temporal.id_off IS 
    'Identificador único generado por el dispositivo para sincronización offline';

-- 5. aviso
ALTER TABLE sinb.aviso 
    ADD COLUMN IF NOT EXISTS id_off VARCHAR(36);

CREATE INDEX IF NOT EXISTS idx_aviso_id_off 
    ON sinb.aviso (id_off) 
    WHERE id_off IS NOT NULL;

COMMENT ON COLUMN sinb.aviso.id_off IS 
    'Identificador único generado por el dispositivo para sincronización offline';

-- 6. recomendacion_local
ALTER TABLE sinb.recomendacion_local 
    ADD COLUMN IF NOT EXISTS id_off VARCHAR(36);

CREATE INDEX IF NOT EXISTS idx_recomendacion_local_id_off 
    ON sinb.recomendacion_local (id_off) 
    WHERE id_off IS NOT NULL;

COMMENT ON COLUMN sinb.recomendacion_local.id_off IS 
    'Identificador único generado por el dispositivo para sincronización offline';

-- ============================================================================
-- REGLA DE NEGOCIO: id_off es único por dispositivo (no global)
-- El dispositivo debe garantizar unicidad local antes de enviar
-- ============================================================================

-- 7. observacion_registro (tabla dependiente, también requiere id_off)
ALTER TABLE sinb.observacion_registro 
    ADD COLUMN IF NOT EXISTS id_off VARCHAR(36);

CREATE INDEX IF NOT EXISTS idx_observacion_registro_id_off 
    ON sinb.observacion_registro (id_off) 
    WHERE id_off IS NOT NULL;

COMMENT ON COLUMN sinb.observacion_registro.id_off IS 
    'Identificador único generado por el dispositivo para sincronización offline';

-- ============================================================================
-- GENERAR ID_OFF PARA DATOS MIGRADOS (valores UUID únicos)
-- ============================================================================

-- Para datos ya migrados, generar id_off únicos basados en el id existente
-- Esto asegura que cada registro tenga un id_off para futura sincronización

-- observacion: generar UUID basado en id existente
UPDATE sinb.observacion 
SET id_off = 'mig-' || SUBSTRING(id::text FROM 1 FOR 36)
WHERE id_off IS NULL;

-- observacion_registro: generar UUID basado en id existente
UPDATE sinb.observacion_registro 
SET id_off = 'mig-' || SUBSTRING(id::text FROM 1 FOR 36)
WHERE id_off IS NULL;

-- pronostico_estacional: generar UUID basado en id existente
UPDATE sinb.pronostico_estacional 
SET id_off = 'mig-' || SUBSTRING(id::text FROM 1 FOR 36)
WHERE id_off IS NULL;

-- pronostico_temporal: generar UUID basado en id existente
UPDATE sinb.pronostico_temporal 
SET id_off = 'mig-' || SUBSTRING(id::text FROM 1 FOR 36)
WHERE id_off IS NULL;

-- recomendacion_local: generar UUID basado en id existente
UPDATE sinb.recomendacion_local 
SET id_off = 'mig-' || SUBSTRING(id::text FROM 1 FOR 36)
WHERE id_off IS NULL;

-- aviso: no hay datos migrados aún, pero la columna existe
