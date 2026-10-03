-- SINAGERSAT/BaseData - Migración v2.27.0
-- Tablas especializadas para pronósticos digitales de Open-Meteo
-- Autor: opencode | Fecha: 2026-10-03

-- ============================================================================
-- TABLA 1: PRONÓSTICO DIARIO MUNICIPAL (AUTOMÁTICO - 2x/día)
-- ============================================================================

CREATE TABLE IF NOT EXISTS sinb.pronostico_diario_municipal (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    id_municipio integer NOT NULL REFERENCES shared.municipio(id) ON DELETE CASCADE,
    fecha date NOT NULL,
    temp_max numeric(5,1),              -- Temperatura máxima (°C)
    temp_min numeric(5,1),              -- Temperatura mínima (°C)
    precipitacion_suma numeric(6,1),    -- Suma de precipitación (mm)
    precipitacion_prob_max integer,     -- Probabilidad máxima de precipitación (%)
    fuente varchar(100) DEFAULT 'open-meteo',
    creado_en timestamptz NOT NULL DEFAULT now(),
    actualizado_en timestamptz NOT NULL DEFAULT now(),
    
    CONSTRAINT uk_pronostico_diario UNIQUE (id_municipio, fecha),
    CONSTRAINT chk_fecha_valida CHECK (fecha >= CURRENT_DATE - INTERVAL '1 day')
);

CREATE INDEX IF NOT EXISTS idx_pronostico_diario_municipio_fecha 
    ON sinb.pronostico_diario_municipal (id_municipio, fecha DESC);

CREATE INDEX IF NOT EXISTS idx_pronostico_diario_fecha 
    ON sinb.pronostico_diario_municipal (fecha DESC);

COMMENT ON TABLE sinb.pronostico_diario_municipal IS 
    'Pronóstico diario automático para 343 municipios (2x/día, 7 días de horizonte)';

COMMENT ON COLUMN sinb.pronostico_diario_municipal.temp_max IS 
    'Temperatura máxima diaria en °C';

COMMENT ON COLUMN sinb.pronostico_diario_municipal.temp_min IS 
    'Temperatura mínima diaria en °C';

COMMENT ON COLUMN sinb.pronostico_diario_municipal.precipitacion_suma IS 
    'Suma total de precipitación del día en mm';

COMMENT ON COLUMN sinb.pronostico_diario_municipal.precipitacion_prob_max IS 
    'Probabilidad máxima de precipitación en %';


-- ============================================================================
-- TABLA 2: PRONÓSTICO HOURLY POR PUNTO (ON-DEMAND - CACHÉ 24H)
-- ============================================================================

CREATE TABLE IF NOT EXISTS sinb.pronostico_hourly_punto (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    latitud numeric(9,6) NOT NULL,                  -- Latitud del punto
    longitud numeric(9,6) NOT NULL,                 -- Longitud del punto
    fecha_hora timestamptz NOT NULL,                -- Fecha y hora del pronóstico
    id_variable_climatica uuid REFERENCES sinb.variable_climatica(id) ON DELETE CASCADE,
    valor numeric,                                  -- Valor de la variable
    unidad varchar(50),                             -- Unidad de medida
    id_municipio integer REFERENCES shared.municipio(id) ON DELETE SET NULL,
    creado_en timestamptz NOT NULL DEFAULT now(),
    expira_en timestamptz NOT NULL DEFAULT (now() + INTERVAL '24 hours'),
    
    CONSTRAINT uk_pronostico_hourly UNIQUE (latitud, longitud, fecha_hora, id_variable_climatica),
    CONSTRAINT chk_horizonte_hourly CHECK (fecha_hora <= now() + INTERVAL '7 days')
);

CREATE INDEX IF NOT EXISTS idx_pronostico_hourly_coord_fecha 
    ON sinb.pronostico_hourly_punto (latitud, longitud, fecha_hora DESC);

CREATE INDEX IF NOT EXISTS idx_pronostico_hourly_expira 
    ON sinb.pronostico_hourly_punto (expira_en) 
    WHERE expira_en < now();

CREATE INDEX IF NOT EXISTS idx_pronostico_hourly_municipio 
    ON sinb.pronostico_hourly_punto (id_municipio, fecha_hora DESC);

COMMENT ON TABLE sinb.pronostico_hourly_punto IS 
    'Pronóstico por hora para puntos específicos (on-demand, caché 24 horas)';

COMMENT ON COLUMN sinb.pronostico_hourly_punto.latitud IS 
    'Latitud del punto consultado (coordenadas WGS84)';

COMMENT ON COLUMN sinb.pronostico_hourly_punto.longitud IS 
    'Longitud del punto consultado (coordenadas WGS84)';

COMMENT ON COLUMN sinb.pronostico_hourly_punto.expira_en IS 
    'Fecha de expiración del registro (24 horas desde creación)';


-- ============================================================================
-- TABLA 3: PRONÓSTICO MINUTELY_15 (NOWCAST - CACHÉ 1H)
-- ============================================================================

CREATE TABLE IF NOT EXISTS sinb.pronostico_minutely_cache (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    latitud numeric(9,6) NOT NULL,                  -- Latitud del punto
    longitud numeric(9,6) NOT NULL,                 -- Longitud del punto
    fecha_hora timestamptz NOT NULL,                -- Fecha y hora del pronóstico
    precipitacion numeric(5,2),                     -- Precipitación (mm)
    temperatura numeric(5,1),                       -- Temperatura (°C)
    id_municipio integer REFERENCES shared.municipio(id) ON DELETE SET NULL,
    creado_en timestamptz NOT NULL DEFAULT now(),
    expira_en timestamptz NOT NULL DEFAULT (now() + INTERVAL '1 hour'),
    
    CONSTRAINT uk_pronostico_minutely UNIQUE (latitud, longitud, fecha_hora),
    CONSTRAINT chk_horizonte_minutely CHECK (fecha_hora <= now() + INTERVAL '48 hours')
);

CREATE INDEX IF NOT EXISTS idx_pronostico_minutely_coord_fecha 
    ON sinb.pronostico_minutely_cache (latitud, longitud, fecha_hora DESC);

CREATE INDEX IF NOT EXISTS idx_pronostico_minutely_expira 
    ON sinb.pronostico_minutely_cache (expira_en) 
    WHERE expira_en < now();

COMMENT ON TABLE sinb.pronostico_minutely_cache IS 
    'Nowcast cada 15 minutos para alertas inmediatas (caché 1 hora)';

COMMENT ON COLUMN sinb.pronostico_minutely_cache.precipitacion IS 
    'Precipitación en mm para los próximos 15 minutos';

COMMENT ON COLUMN sinb.pronostico_minutely_cache.expira_en IS 
    'Fecha de expiración del registro (1 hora desde creación)';


-- ============================================================================
-- FUNCIONES DE LIMPIEZA AUTOMÁTICA (CACHÉ EXPIRADO)
-- ============================================================================

-- Función para limpiar caché hourly expirado
-- ELIMINADA: No borrar caché (se guarda para auditoría)
-- CREATE OR REPLACE FUNCTION sinb.limpieza_cache_hourly()
RETURNS integer AS $$
DECLARE
    filas_eliminadas integer;
BEGIN
    DELETE FROM sinb.pronostico_hourly_punto
    WHERE expira_en < now();
    
    GET DIAGNOSTICS filas_eliminadas = ROW_COUNT;
    RETURN filas_eliminadas;
END;
$$ LANGUAGE plpgsql;

-- Función para limpiar caché minutely expirado
-- ELIMINADA: No borrar caché (se guarda para auditoría)
-- CREATE OR REPLACE FUNCTION sinb.limpieza_cache_minutely()
RETURNS integer AS $$
DECLARE
    filas_eliminadas integer;
BEGIN
    DELETE FROM sinb.pronostico_minutely_cache
    WHERE expira_en < now();
    
    GET DIAGNOSTICS filas_eliminadas = ROW_COUNT;
    RETURN filas_eliminadas;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- GRANTS (opcionales, para roles de aplicación)
-- ============================================================================

-- GRANT USAGE ON SCHEMA sinb TO sinagersat;
-- GRANT SELECT ON ALL TABLES IN SCHEMA sinb TO sinagersat;
-- GRANT INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA sinb TO sinagersat;

-- ============================================================================
-- VERIFICACIÓN
-- ============================================================================

SELECT 
    'pronostico_diario_municipal' as tabla, 
    COUNT(*) as filas 
FROM sinb.pronostico_diario_municipal
UNION ALL
SELECT 'pronostico_hourly_punto', COUNT(*) FROM sinb.pronostico_hourly_punto
UNION ALL
SELECT 'pronostico_minutely_cache', COUNT(*) FROM sinb.pronostico_minutely_cache;

-- ============================================================================
-- CORRECCIÓN DE ÍNDICES (usando expresión compatible)
-- ============================================================================

-- Índice para hourly expirado (sin función en WHERE)
-- ELIMINADO: No borrar caché
-- CREATE INDEX IF NOT EXISTS idx_pronostico_hourly_expira_raw
    ON sinb.pronostico_hourly_punto (expira_en);

-- Índice para minutely expirado (sin función en WHERE)
-- ELIMINADO: No borrar caché
-- CREATE INDEX IF NOT EXISTS idx_pronostico_minutely_expira_raw
    ON sinb.pronostico_minutely_cache (expira_en);

-- Verificación final
SELECT 
    'pronostico_diario_municipal' as tabla, 
    COUNT(*) as filas 
FROM sinb.pronostico_diario_municipal
UNION ALL
SELECT 'pronostico_hourly_punto', COUNT(*) FROM sinb.pronostico_hourly_punto
UNION ALL
SELECT 'pronostico_minutely_cache', COUNT(*) FROM sinb.pronostico_minutely_cache;

SELECT 'Migración v2.27.0 completada exitosamente' as estado;

-- ============================================================================
-- NOTA: Funciones de limpieza ELIMINADAS
-- Los registros de caché se mantienen indefinidamente para auditoría
-- ============================================================================
-- DROP FUNCTION IF EXISTS sinb.limpieza_cache_hourly();
-- DROP FUNCTION IF EXISTS sinb.limpieza_cache_minutely();

