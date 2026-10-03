-- ============================================================================
-- v2.28.0: NDVI Satelital - Series históricas de vegetación
-- ============================================================================
-- Autor: SINAGERSAT
-- Fecha: 2026-10-03
-- Descripción: Tablas para almacenamiento de NDVI calculado desde Sentinel-2
--              (EarthSearch STAC API - sin API key requerida)
-- ============================================================================

-- ============================================================================
-- TABLAS PRINCIPALES
-- ============================================================================

-- Escenas satelitales (registro de cada imagen descargada)
CREATE TABLE IF NOT EXISTS sinb.escena_satelital (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    producto varchar(50) NOT NULL DEFAULT 'sentinel-2-l2a',
    escena_id varchar(100) NOT NULL,
    fecha_adquisicion date NOT NULL,
    fecha_proceso timestamptz NOT NULL DEFAULT now(),
    cobertura_nubes numeric(5,2) CHECK (cobertura_nubes BETWEEN 0 AND 100),
    huella geometry(MULTIPOLYGON, 4326),
    path_archivo text,
    metadata jsonb,
    creado_en timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uk_escena_satelital UNIQUE (escena_id)
);

-- Índices para consultas espaciales y temporales
CREATE INDEX IF NOT EXISTS idx_escena_fecha ON sinb.escena_satelital(fecha_adquisicion);
CREATE INDEX IF NOT EXISTS idx_escena_huella ON sinb.escena_satelital USING GIST(huella);
CREATE INDEX IF NOT EXISTS idx_escena_nubes ON sinb.escena_satelital(cobertura_nubes);

-- Comentario de tabla
COMMENT ON TABLE sinb.escena_satelital IS 
    'Escenas Sentinel-2 procesadas (EarthSearch STAC). 
     Una fila por escena única (identificada por escena_id).
     NDVI se calcula desde bandas B08 (nir) y B04 (red).';

COMMENT ON COLUMN sinb.escena_satelital.escena_id IS 
    'Identificador único de EarthSearch (ej: S2B_19KFA_20260726_0_L2A)';

COMMENT ON COLUMN sinb.escena_satelital.metadata IS 
    'Metadatos completos de la escena (JSON de EarthSearch)';

-- ============================================================================
-- AGREGADOS POR COMUNIDAD (NDVI calculado)
-- ============================================================================

CREATE TABLE IF NOT EXISTS sinb.agregado_satelital (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    id_escena_satelital uuid NOT NULL REFERENCES sinb.escena_satelital(id) ON DELETE CASCADE,
    codigo_comunidad text NOT NULL REFERENCES shared.comunidades(codigo_ine) ON DELETE CASCADE,
    ndvi_promedio numeric(5,4),
    ndvi_min numeric(5,4),
    ndvi_max numeric(5,4),
    ndvi_desviacion numeric(5,4),
    pixeles_totales integer,
    pixeles_validos integer,
    fecha_proceso timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uk_agregado UNIQUE (id_escena_satelital, codigo_comunidad)
);

-- Índices para consultas
CREATE INDEX IF NOT EXISTS idx_agregado_escena ON sinb.agregado_satelital(id_escena_satelital);
CREATE INDEX IF NOT EXISTS idx_agregado_comunidad ON sinb.agregado_satelital(codigo_comunidad);
CREATE INDEX IF NOT EXISTS idx_agregado_ndvi ON sinb.agregado_satelital(ndvi_promedio);

-- Índices compuestos para consultas temporales
CREATE INDEX IF NOT EXISTS idx_agregado_fecha_comunidad 
    ON sinb.agregado_satelital(codigo_comunidad, fecha_proceso);

CREATE INDEX IF NOT EXISTS idx_escena_fecha_nubes 
    ON sinb.escena_satelital(fecha_adquisicion, cobertura_nubes)
    WHERE cobertura_nubes < 20;

-- Comentario de tabla
COMMENT ON TABLE sinb.agregado_satelital IS 
    'NDVI agregado por comunidad para cada escena satelital.
     Una fila por (escena × comunidad).
     Campos ndvi_* son estadísticos espaciales dentro del bbox de la comunidad.';

COMMENT ON COLUMN sinb.agregado_satelital.ndvi_promedio IS 
    'Promedio espacial de NDVI dentro del bbox de la comunidad (-1 a 1)';

COMMENT ON COLUMN sinb.agregado_satelital.pixeles_validos IS 
    'Cantidad de píxeles SIN nubes usados para el cálculo';

-- ============================================================================
-- SERIES TEMPORALES (para consultas rápidas de tendencias)
-- ============================================================================

CREATE TABLE IF NOT EXISTS sinb.serie_ndvi_comunidad (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    codigo_comunidad text NOT NULL REFERENCES shared.comunidades(codigo_ine) ON DELETE CASCADE,
    fecha date NOT NULL,
    ndvi_promedio numeric(5,4),
    ndvi_anomalia numeric(5,4),
    ndvi_percentil integer CHECK (ndvi_percentil BETWEEN 0 AND 100),
    estado_vegetacion varchar(20),
    n_escenas integer DEFAULT 1,
    creado_en timestamptz NOT NULL DEFAULT now(),
    actualizado_en timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uk_serie_ndvi UNIQUE (codigo_comunidad, fecha)
);

-- Índices para series temporales
CREATE INDEX IF NOT EXISTS idx_serie_comunidad_fecha ON sinb.serie_ndvi_comunidad(codigo_comunidad, fecha);
CREATE INDEX IF NOT EXISTS idx_serie_fecha ON sinb.serie_ndvi_comunidad(fecha);
CREATE INDEX IF NOT EXISTS idx_serie_anomalia ON sinb.serie_ndvi_comunidad(ndvi_anomalia);

-- Comentario de tabla
COMMENT ON TABLE sinb.serie_ndvi_comunidad IS 
    'Serie temporal diaria de NDVI por comunidad (materializada para consultas rápidas).
     Se actualiza cuando ingresa nueva escena.
     ndvi_anomalia = desviación del promedio histórico para esa fecha.';

COMMENT ON COLUMN sinb.serie_ndvi_comunidad.ndvi_anomalia IS 
    'Diferencia vs. promedio histórico (mismo día del año, últimos 5 años)';

COMMENT ON COLUMN sinb.serie_ndvi_comunidad.estado_vegetacion IS 
    'Clasificación: seco, bajo, normal, alto, muy_alto';

-- ============================================================================
-- VISTAS ÚTILES
-- ============================================================================

-- Vista: Último NDVI por comunidad
CREATE OR REPLACE VIEW sinb.vw_ultimo_ndvi_comunidad AS
SELECT 
    c.codigo_ine,
    c.nombre,
    s.fecha,
    s.ndvi_promedio,
    s.ndvi_anomalia,
    s.estado_vegetacion,
    CASE 
        WHEN s.ndvi_anomalia < -0.15 THEN 'alerta_roja'
        WHEN s.ndvi_anomalia < -0.05 THEN 'alerta_amarilla'
        WHEN s.ndvi_anomalia > 0.10 THEN 'muy_bien'
        ELSE 'normal'
    END as estado_alerta
FROM shared.comunidades c
LEFT JOIN LATERAL (
    SELECT fecha, ndvi_promedio, ndvi_anomalia, estado_vegetacion
    FROM sinb.serie_ndvi_comunidad
    WHERE codigo_comunidad = c.codigo_ine
    ORDER BY fecha DESC
    LIMIT 1
) s ON true;

COMMENT ON VIEW sinb.vw_ultimo_ndvi_comunidad IS 
    'Último valor de NDVI disponible para cada comunidad con estado de alerta';

-- Vista: Evolución mensual (últimos 12 meses)
CREATE OR REPLACE VIEW sinb.vw_evolucion_mensual_ndvi AS
SELECT 
    c.codigo_ine,
    c.nombre,
    date_trunc('month', s.fecha) as mes,
    avg(s.ndvi_promedio) as ndvi_promedio_mes,
    avg(s.ndvi_anomalia) as anomalia_promedio_mes,
    count(*) as n_dias_con_datos
FROM shared.comunidades c
JOIN sinb.serie_ndvi_comunidad s ON c.codigo_ine = s.codigo_comunidad
WHERE s.fecha >= (CURRENT_DATE - INTERVAL '12 months')
GROUP BY c.codigo_ine, c.nombre, date_trunc('month', s.fecha)
ORDER BY mes DESC;

COMMENT ON VIEW sinb.vw_evolucion_mensual_ndvi IS 
    'Agregación mensual de NDVI para los últimos 12 meses';

-- Vista: Alertas activas (comunidades con NDVI bajo)
CREATE OR REPLACE VIEW sinb.vw_alertas_ndvi AS
SELECT 
    c.codigo_ine,
    c.nombre,
    s.fecha,
    s.ndvi_promedio,
    s.ndvi_anomalia,
    s.estado_vegetacion,
    CASE 
        WHEN s.ndvi_promedio < 0.2 THEN 'sequia_extrema'
        WHEN s.ndvi_promedio < 0.3 THEN 'sequia_moderada'
        WHEN s.ndvi_anomalia < -0.15 THEN 'anomalia_negativa_fuerte'
        WHEN s.ndvi_anomalia < -0.05 THEN 'anomalia_negativa_leve'
        ELSE 'normal'
    END as tipo_alerta,
    CASE 
        WHEN s.ndvi_promedio < 0.2 THEN 1
        WHEN s.ndvi_promedio < 0.3 THEN 2
        WHEN s.ndvi_anomalia < -0.15 THEN 3
        WHEN s.ndvi_anomalia < -0.05 THEN 4
        ELSE 5
    END as nivel_prioridad
FROM shared.comunidades c
JOIN sinb.serie_ndvi_comunidad s ON c.codigo_ine = s.codigo_comunidad
WHERE s.fecha >= (CURRENT_DATE - INTERVAL '7 days')
  AND (s.ndvi_promedio < 0.3 OR s.ndvi_anomalia < -0.05)
ORDER BY nivel_prioridad, s.ndvi_anomalia;

COMMENT ON VIEW sinb.vw_alertas_ndvi IS 
    'Comunidades con NDVI bajo o anomalía negativa (últimos 7 días).
     nivel_prioridad: 1=más urgente, 5=normal';

-- ============================================================================
-- FUNCIONES DE CÁLCULO DE NDVI
-- ============================================================================

-- Función: Clasificar estado de vegetación según NDVI
CREATE OR REPLACE FUNCTION sinb.clasificar_estado_vegetacion(p_ndvi numeric)
RETURNS varchar(20) AS $$
BEGIN
    IF p_ndvi IS NULL THEN
        RETURN 'sin_datos';
    ELSIF p_ndvi < 0.1 THEN
        RETURN 'suelo_desnudo';
    ELSIF p_ndvi < 0.2 THEN
        RETURN 'seco';
    ELSIF p_ndvi < 0.3 THEN
        RETURN 'bajo';
    ELSIF p_ndvi < 0.5 THEN
        RETURN 'normal';
    ELSIF p_ndvi < 0.7 THEN
        RETURN 'alto';
    ELSE
        RETURN 'muy_alto';
    END IF;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION sinb.clasificar_estado_vegetacion IS 
    'Clasifica NDVI en categorías de vegetación';

-- Función: Calcular anomalía NDVI (desviación del histórico)
CREATE OR REPLACE FUNCTION sinb.calcular_anomalia_ndvi(
    p_codigo_comunidad text,
    p_fecha date,
    p_ndvi numeric
)
RETURNS numeric AS $$
DECLARE
    v_promedio_historico numeric;
BEGIN
    -- Calcular promedio histórico para la misma fecha (±15 días, últimos 5 años)
    SELECT avg(ndvi_promedio) INTO v_promedio_historico
    FROM sinb.serie_ndvi_comunidad
    WHERE codigo_comunidad = p_codigo_comunidad
      AND fecha != p_fecha
      AND extract(month from fecha) = extract(month from p_fecha)
      AND extract(day from fecha) BETWEEN extract(day from p_fecha) - 15 AND extract(day from p_fecha) + 15
      AND fecha >= (p_fecha - INTERVAL '5 years');
    
    IF v_promedio_historico IS NULL THEN
        RETURN 0;  -- Sin histórico, anomalia = 0
    END IF;
    
    RETURN round(p_ndvi - v_promedio_historico, 4);
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION sinb.calcular_anomalia_ndvi IS 
    'Calcula desviación del NDVI actual vs. promedio histórico (misma época del año)';

-- Función: Insertar/actualizar serie temporal (UPSERT)
CREATE OR REPLACE FUNCTION sinb.actualizar_serie_ndvi_comunidad(
    p_codigo_comunidad text,
    p_fecha date,
    p_ndvi numeric
)
RETURNS void AS $$
DECLARE
    v_anomalia numeric;
    v_estado varchar(20);
BEGIN
    v_estado := sinb.clasificar_estado_vegetacion(p_ndvi);
    v_anomalia := sinb.calcular_anomalia_ndvi(p_codigo_comunidad, p_fecha, p_ndvi);
    
    INSERT INTO sinb.serie_ndvi_comunidad (
        codigo_comunidad, fecha, ndvi_promedio, ndvi_anomalia, 
        estado_vegetacion, actualizado_en
    ) VALUES (
        p_codigo_comunidad, p_fecha, p_ndvi, v_anomalia, v_estado, now()
    )
    ON CONFLICT (codigo_comunidad, fecha) DO UPDATE SET
        ndvi_promedio = p_ndvi,
        ndvi_anomalia = EXCLUDED.ndvi_anomalia,
        estado_vegetacion = EXCLUDED.estado_vegetacion,
        actualizado_en = now();
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION sinb.actualizar_serie_ndvi_comunidad IS 
    'Inserta o actualiza registro de serie temporal (idempotente)';

-- ============================================================================
-- FUNCIONES DE AGREGACIÓN ESPACIAL
-- ============================================================================

-- Función: Obtener bbox de comunidad (para recorte de imágenes)
CREATE OR REPLACE FUNCTION sinb.obtener_bbox_comunidad(p_codigo_comunidad text)
RETURNS geometry(POLYGON, 4326) AS $$
DECLARE
    v_bbox geometry;
BEGIN
    -- Usar geometría de shared.comunidades si existe
    SELECT ST_Envelope(geometria) INTO v_bbox
    FROM shared.comunidades
    WHERE codigo_ine = p_codigo_comunidad;
    
    IF v_bbox IS NULL THEN
        -- Fallback: bbox genérico (debe ser sobrescrito por datos reales)
        v_bbox := ST_GeomFromText(
            'POLYGON((-70 -20, -57 -20, -57 -10, -70 -10, -70 -20))', 4326
        );
    END IF;
    
    RETURN v_bbox;
END;
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION sinb.obtener_bbox_comunidad IS 
    'Obtiene bounding box de una comunidad para recorte de imágenes satelitales';

-- ============================================================================
-- LOG DE PROCESAMIENTO (auditoría)
-- ============================================================================

CREATE TABLE IF NOT EXISTS sinb.ndvi_procesamiento_log (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    fecha_proceso date NOT NULL DEFAULT CURRENT_DATE,
    hora_inicio timestamptz NOT NULL DEFAULT now(),
    hora_fin timestamptz,
    escenas_consultadas integer DEFAULT 0,
    escenas_descargadas integer DEFAULT 0,
    comunidades_procesadas integer DEFAULT 0,
    pixeles_procesados bigint DEFAULT 0,
    estado varchar(20) DEFAULT 'en_progreso',
    error_mensaje text,
    metadata jsonb,
    creado_en timestamptz NOT NULL DEFAULT now()
);

-- Índice para consultas por fecha
CREATE INDEX IF NOT EXISTS idx_ndvi_log_fecha ON sinb.ndvi_procesamiento_log(fecha_proceso);

COMMENT ON TABLE sinb.ndvi_procesamiento_log IS 
    'Registro de ejecución de tarea CRON de ingesta NDVI.
     Auditoría de procesamiento diario.';

-- ============================================================================
-- GRANTS (opcionales, para roles de aplicación)
-- ============================================================================

-- Grant de lectura para rol sinagersat_reader (si existe)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'sinagersat_reader') THEN
        GRANT SELECT ON ALL TABLES IN SCHEMA sinb TO sinagersat_reader;
    END IF;
END $$;

-- ============================================================================
-- DATOS INICIALES (opcional)
-- ============================================================================

-- Insertar registro inicial de log (marcador de inicio)
INSERT INTO sinb.ndvi_procesamiento_log (fecha_proceso, estado)
VALUES (CURRENT_DATE, 'inicializado')
ON CONFLICT DO NOTHING;

-- ============================================================================
-- FIN DE MIGRACIÓN
-- ============================================================================
