-- Paso 4: Migrar datos transaccionales SINB

SET statement_timeout = 0;

DROP TABLE IF EXISTS tmp_obs_mapeo;
DROP TABLE IF EXISTS tmp_obs_reg_mapeo;
DROP TABLE IF EXISTS tmp_pronostico_estacional_mapeo;
DROP TABLE IF EXISTS tmp_pronostico_temporal_mapeo;
DROP TABLE IF EXISTS tmp_recomendacion_mapeo;
DROP TABLE IF EXISTS tmp_cat_mapeo;

-- ============================================
-- 1. OBSERVACIONES
-- ============================================
CREATE TEMP TABLE tmp_obs_mapeo AS
WITH obs_base AS (
    SELECT 
        o.id_observacion as id_legacy,
        o.fecha_inicio, o.fecha_fin, o.fecha_de_registro,
        ou.fk_t_usuario_id_usuario as id_usuario_legacy,
        u.celular::text as celular_usuario
    FROM sinb.t_observacion o
    JOIN sinb.t_observacion_usuario ou ON ou.fk_t_observacion_id_observacion = o.id_observacion
    JOIN sinb.t_usuario u ON u.id_usuario = ou.fk_t_usuario_id_usuario
    WHERE o.estado = 1
),
obs_unificada AS (
    SELECT DISTINCT ON (id_legacy)
        id_legacy, fecha_inicio, fecha_fin, fecha_de_registro, id_usuario_legacy, celular_usuario
    FROM obs_base ORDER BY id_legacy, id_usuario_legacy
),
obs_con_territorio AS (
    SELECT 
        ob.id_legacy, ob.fecha_inicio, ob.fecha_fin, ob.fecha_de_registro, ob.celular_usuario,
        c.comunidad as nombre_comunidad_legacy,
        m.municipio as nombre_municipio
    FROM obs_unificada ob
    JOIN sinb.t_usuario_comunidad uc ON uc.fk_t_usuario_id_usuario = ob.id_usuario_legacy
    JOIN sinb.t_comunidad c ON c.id_comunidad = uc.fk_t_comunidad_id_comunidad
    JOIN sinb.t_municipio_comunidad mc ON mc.fk_t_comunidad_id_comunidad = c.id_comunidad
    JOIN sinb.t_municipio m ON m.id_municipio = mc.fk_t_municipio_id_municipio
),
obs_match AS (
    SELECT DISTINCT ON (oc.id_legacy)
        oc.id_legacy, oc.fecha_inicio, oc.fecha_fin, oc.fecha_de_registro, oc.celular_usuario,
        sc.codigo_ine as codigo_comunidad_shared,
        sm.id as id_municipio_shared
    FROM obs_con_territorio oc
    LEFT JOIN shared.comunidades sc ON lower(sc.nombre) = lower(oc.nombre_comunidad_legacy)
    LEFT JOIN shared.municipio sm ON lower(sm.nombre) = lower(oc.nombre_municipio)
    ORDER BY oc.id_legacy, sc.codigo_ine
)
SELECT 
    om.id_legacy, gen_random_uuid() as id_uuid, 'OBS-' || om.id_legacy::text as codigo_corto,
    COALESCE(om.codigo_comunidad_shared, '02417371843-M') as codigo_comunidad,
    COALESCE(om.id_municipio_shared, 10101) as id_municipio,
    uu.id_usuario as id_usuario_responsable,
    om.fecha_inicio, om.fecha_fin, om.fecha_de_registro as fecha_registro
FROM obs_match om
JOIN usuarios.usuario uu ON uu.usuario = om.celular_usuario;

SELECT 'Observaciones mapeadas' as info, count(*) FROM tmp_obs_mapeo;

INSERT INTO sinb.observacion (
    id, codigo_corto, codigo_comunidad, id_municipio, id_usuario_responsable,
    fecha_inicio, fecha_fin, fecha_registro, es_validada, estado, version_registro
)
SELECT id_uuid, codigo_corto, codigo_comunidad, id_municipio, id_usuario_responsable,
    fecha_inicio, fecha_fin, fecha_registro, false, 'ACTIVO', 1
FROM tmp_obs_mapeo ON CONFLICT (id) DO NOTHING;

SELECT 'Observaciones insertadas' as info, count(*) FROM sinb.observacion;

-- ============================================
-- 2. OBSERVACION_REGISTRO (mapeo de catálogos)
-- ============================================
CREATE TEMP TABLE tmp_cat_mapeo AS
SELECT 'indicador_natural' as tipo, t.id_indicador_natural as id_legacy, i.id as id_uuid
FROM sinb.t_indicador_natural t
JOIN sinb.indicador_natural i ON lower(i.nombre_cientifico) = lower(t.nombre_cientifico)
UNION ALL
SELECT 'caracteristica' as tipo, t.id_caracteristica as id_legacy, c.id as id_uuid
FROM sinb.t_caracteristica t
JOIN sinb.caracteristica c ON c.caracteristica = t.caracteristica
UNION ALL
SELECT 'comportamiento' as tipo, t.id_comportamiento as id_legacy, b.id as id_uuid
FROM sinb.t_comportamiento t
JOIN sinb.comportamiento b ON b.comportamiento = t.comportamiento;

SELECT 'Catálogo mapeado' as info, count(*) FROM tmp_cat_mapeo;

INSERT INTO sinb.observacion_registro (id_observacion, id_indicador_natural)
SELECT om.id_uuid, cm.id_uuid
FROM sinb.t_observacion_indicador_natural oin
JOIN tmp_obs_mapeo om ON om.id_legacy = oin.fk_t_observacion_id_observacion
JOIN tmp_cat_mapeo cm ON cm.tipo = 'indicador_natural' AND cm.id_legacy = oin.fk_t_indicador_natural_id_indicador_natural
ON CONFLICT DO NOTHING;

INSERT INTO sinb.observacion_registro (id_observacion, id_caracteristica)
SELECT om.id_uuid, cm.id_uuid
FROM sinb.t_observacion_caracteristica oc
JOIN tmp_obs_mapeo om ON om.id_legacy = oc.fk_t_observacion_id_observacion
JOIN tmp_cat_mapeo cm ON cm.tipo = 'caracteristica' AND cm.id_legacy = oc.fk_t_caracteristica_id_caracteristica
ON CONFLICT DO NOTHING;

INSERT INTO sinb.observacion_registro (id_observacion, id_comportamiento)
SELECT om.id_uuid, cm.id_uuid
FROM sinb.t_observacion_comportamiento obc
JOIN tmp_obs_mapeo om ON om.id_legacy = obc.fk_t_observacion_id_observacion
JOIN tmp_cat_mapeo cm ON cm.tipo = 'comportamiento' AND cm.id_legacy = obc.fk_t_comportamiento_id_comportamiento
ON CONFLICT DO NOTHING;

SELECT 'Observacion_registro' as info, count(*) FROM sinb.observacion_registro;

-- ============================================
-- 3. PRONÓSTICOS ESTACIONALES (usar primer campo disponible)
-- ============================================
INSERT INTO sinb.pronostico_estacional (id, codigo, id_campo_pronostico, fecha_emision, periodo_inicio, periodo_fin, estado, notas)
SELECT 
    gen_random_uuid(), 'PE-' || pe.id_pronostico_estacional::text,
    (SELECT id FROM sinb.campo_pronostico LIMIT 1),  -- Usar primer campo disponible (Lluvia)
    CURRENT_DATE, DATE_TRUNC('month', CURRENT_DATE)::date,
    (DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '2 months')::date,
    'EMITIDO', pe.pronostico_estacional
FROM sinb.t_pronostico_estacional pe WHERE pe.estado = 'ACTIVO'
ON CONFLICT (id) DO NOTHING;

SELECT 'Pronostico_estacional' as info, count(*) FROM sinb.pronostico_estacional;

-- ============================================
-- 4. PRONÓSTICOS TEMPORALES (usar primer campo disponible)
-- ============================================
INSERT INTO sinb.pronostico_temporal (id, codigo, id_categoria, id_campo_pronostico, fecha_emision, fecha_inicio, fecha_fin, valor_esperado, confianza, estado)
SELECT 
    gen_random_uuid(), 'PT-' || pt.id_pronostico_temporal::text,
    (SELECT id FROM sinb.categoria_pronostico_temporal LIMIT 1),
    (SELECT id FROM sinb.campo_pronostico LIMIT 1),  -- Usar primer campo disponible
    pt.fecha_registro, pt.fecha_registro,
    (pt.fecha_registro + (pt.tiempo_vigencia || ' days')::interval)::date,
    pt.descripcion_observacion, 'MEDIA'::sinb.confianza_nivel, 'EMITIDO'
FROM sinb.t_pronostico_temporal pt WHERE pt.estado = 1
ON CONFLICT (id) DO NOTHING;

SELECT 'Pronostico_temporal' as info, count(*) FROM sinb.pronostico_temporal;

-- ============================================
-- 5. RECOMENDACIONES LOCALES
-- ============================================
INSERT INTO sinb.recomendacion_local (id, texto, id_dimension, id_categoria, estado)
SELECT 
    gen_random_uuid(), rl.recomendacion_local,
    (SELECT id FROM sinb.dimension_recomendacion LIMIT 1),
    (SELECT id FROM sinb.categoria_comportamiento LIMIT 1),
    'ACTIVO'
FROM sinb.t_recomendacion_local rl WHERE rl.estado = 'ACTIVO'
ON CONFLICT (id) DO NOTHING;

SELECT 'Recomendacion_local' as info, count(*) FROM sinb.recomendacion_local;

-- ============================================
-- RESUMEN FINAL
-- ============================================
SELECT '=== MIGRACIÓN TRANSACCIONAL COMPLETADA ===' as resumen;
SELECT 'Observaciones' as tabla, count(*) as filas FROM sinb.observacion
UNION ALL SELECT 'Observacion_registro', count(*) FROM sinb.observacion_registro
UNION ALL SELECT 'Pronostico_estacional', count(*) FROM sinb.pronostico_estacional
UNION ALL SELECT 'Pronostico_temporal', count(*) FROM sinb.pronostico_temporal
UNION ALL SELECT 'Recomendacion_local', count(*) FROM sinb.recomendacion_local;
