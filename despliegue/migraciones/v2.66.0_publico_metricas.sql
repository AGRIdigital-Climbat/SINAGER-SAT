-- ============================================================================
-- SINAGERSAT - Migracion v2.66.0 (idempotente)
-- Esquema PUBLICO: vistas de metricas agregadas para el dashboard publico
-- (GET /api/v2/publico/... sin autenticacion y sin filtros).
--
--   * Solo agrega el esquema `publico` y sus VISTAS (no toca datos de origen).
--   * EDAN distingue SIEMPRE los dos ambitos:
--       - 'consolidado' = edan.edan            (formulario del municipio;
--         estado_edan: 1 Pendiente, 2 Rechazado, 3 Aprobado, 4 Observado)
--       - 'local'       = edan.edan_localidades (una fila por localidad;
--         su propio tipo_evento/fecha_evento y workflow edan_localidades_estado)
--   * Repositorio: metricas por origen (EDAN / RIDA / DOC_PRECEDENTE) y por
--     tipo; nunca expone path_archivo ni nombres de archivo.
--   * Usuarios: SOLO conteos agregados (rol, cargo, geografia, activos). Ninguna
--     vista selecciona datos personales (usuario/nombre/correo/celular/carnet).
--   * Censo: mismos calculos que api/shared (hogares_ine oficial como base del
--     promedio de personas por hogar; redondeo normal (2p+b)/(2b)).
--   * Series anuales y mensuales se generan desde el primer dato hasta la fecha
--     actual, rellenable en 0 (generate_series), con contador de filas sin fecha.
--
-- Idempotencia: CREATE SCHEMA IF NOT EXISTS + CREATE OR REPLACE VIEW.
-- ============================================================================

BEGIN;

CREATE SCHEMA IF NOT EXISTS publico;

-- ----------------------------------------------------------------------------
-- EDAN - resumen base (ambos ambitos)
-- ----------------------------------------------------------------------------
DROP VIEW IF EXISTS publico.v_edan_resumen;
CREATE VIEW publico.v_edan_resumen AS
SELECT 'consolidado'::text AS ambito,
       count(*)                                   AS total,
       count(*) FILTER (WHERE fecha_evento IS NOT NULL) AS con_fecha,
       count(*) FILTER (WHERE fecha_evento IS NULL)     AS sin_fecha,
       min(fecha_evento) AS primer_evento,
       max(fecha_evento) AS ultimo_evento,
       COALESCE(sum(total_poblacion_afectada), 0) AS poblacion_afectada,
       COALESCE(sum(total_familias_afectadas), 0) AS familias_afectadas,
       COALESCE(sum(total_familias_damnificadas), 0) AS familias_damnificadas
  FROM edan.edan
 WHERE pendiente_eliminacion = FALSE
UNION ALL
SELECT 'local',
       count(*),
       count(*) FILTER (WHERE fecha_evento IS NOT NULL),
       count(*) FILTER (WHERE fecha_evento IS NULL),
       min(fecha_evento),
       max(fecha_evento),
       COALESCE(sum(total_poblacion_afectada), 0),
       COALESCE(sum(total_familias_afectadas), 0),
       COALESCE(sum(total_familias_damnificadas), 0)
  FROM edan.edan_localidades
 WHERE pendiente_eliminacion = FALSE;

-- ----------------------------------------------------------------------------
-- EDAN - serie anual completa (0 en anios sin datos)
-- ----------------------------------------------------------------------------
DROP VIEW IF EXISTS publico.v_edan_serie_anios;
CREATE VIEW publico.v_edan_serie_anios AS
WITH base AS (
    SELECT 'consolidado'::text AS ambito,
           extract(year FROM e.fecha_evento)::int AS anio
      FROM edan.edan e
     WHERE e.pendiente_eliminacion = FALSE AND e.fecha_evento IS NOT NULL
    UNION ALL
    SELECT 'local', extract(year FROM l.fecha_evento)::int
      FROM edan.edan_localidades l
     WHERE l.pendiente_eliminacion = FALSE AND l.fecha_evento IS NOT NULL
), limites AS (
    SELECT ambito,
           min(anio) AS anio_ini,
           greatest(max(anio), extract(year FROM current_date)::int) AS anio_fin
      FROM base GROUP BY ambito
), serie AS (
    SELECT lm.ambito, gs.y::int AS anio
      FROM limites lm
      CROSS JOIN LATERAL generate_series(lm.anio_ini, lm.anio_fin) AS gs(y)
), conteo AS (
    SELECT ambito, anio, count(*) AS total FROM base GROUP BY 1, 2
)
SELECT s.ambito, s.anio, COALESCE(c.total, 0) AS total
  FROM serie s
  LEFT JOIN conteo c USING (ambito, anio)
 ORDER BY ambito, anio;

-- ----------------------------------------------------------------------------
-- EDAN - serie anual por tipo de evento (apilable, rellena en 0)
-- ----------------------------------------------------------------------------
DROP VIEW IF EXISTS publico.v_edan_serie_anios_tipo;
CREATE VIEW publico.v_edan_serie_anios_tipo AS
WITH base AS (
    SELECT 'consolidado'::text AS ambito,
           extract(year FROM e.fecha_evento)::int AS anio,
           te.id_tipo_evento, te.nombre AS tipo
      FROM edan.edan e
      JOIN edan.tipo_evento te ON te.id_tipo_evento = e.id_tipo_evento
     WHERE e.pendiente_eliminacion = FALSE AND e.fecha_evento IS NOT NULL
    UNION ALL
    SELECT 'local', extract(year FROM l.fecha_evento)::int,
           te.id_tipo_evento, te.nombre
      FROM edan.edan_localidades l
      JOIN edan.tipo_evento te ON te.id_tipo_evento = l.id_tipo_evento
     WHERE l.pendiente_eliminacion = FALSE AND l.fecha_evento IS NOT NULL
), tipos AS (
    SELECT DISTINCT ambito, id_tipo_evento, tipo FROM base
), limites AS (
    SELECT ambito, min(anio) AS anio_ini,
           greatest(max(anio), extract(year FROM current_date)::int) AS anio_fin
      FROM base GROUP BY ambito
), serie AS (
    SELECT t.ambito, t.id_tipo_evento, t.tipo, gs.y::int AS anio
      FROM tipos t
      JOIN limites lm ON lm.ambito = t.ambito
      CROSS JOIN LATERAL generate_series(lm.anio_ini, lm.anio_fin) AS gs(y)
), conteo AS (
    SELECT ambito, id_tipo_evento, anio, count(*) AS total FROM base GROUP BY 1, 2, 3
)
SELECT s.ambito, s.anio, s.id_tipo_evento, s.tipo, COALESCE(c.total, 0) AS total
  FROM serie s
  LEFT JOIN conteo c USING (ambito, id_tipo_evento, anio)
 ORDER BY ambito, anio, id_tipo_evento;

-- ----------------------------------------------------------------------------
-- EDAN - serie mensual completa (YYYY-MM, rellena en 0)
-- ----------------------------------------------------------------------------
DROP VIEW IF EXISTS publico.v_edan_serie_meses;
CREATE VIEW publico.v_edan_serie_meses AS
WITH base AS (
    SELECT 'consolidado'::text AS ambito,
           date_trunc('month', e.fecha_evento)::date AS mes
      FROM edan.edan e
     WHERE e.pendiente_eliminacion = FALSE AND e.fecha_evento IS NOT NULL
    UNION ALL
    SELECT 'local', date_trunc('month', l.fecha_evento)::date
      FROM edan.edan_localidades l
     WHERE l.pendiente_eliminacion = FALSE AND l.fecha_evento IS NOT NULL
), limites AS (
    SELECT ambito, min(mes) AS mes_ini,
           date_trunc('month', current_date)::date AS mes_fin
      FROM base GROUP BY ambito
), serie AS (
    SELECT lm.ambito, gs.m::date AS mes
      FROM limites lm
      CROSS JOIN LATERAL generate_series(lm.mes_ini, lm.mes_fin,
                                         interval '1 month') AS gs(m)
), conteo AS (
    SELECT ambito, mes, count(*) AS total FROM base GROUP BY 1, 2
)
SELECT s.ambito, to_char(s.mes, 'YYYY-MM') AS mes, COALESCE(c.total, 0) AS total
  FROM serie s
  LEFT JOIN conteo c USING (ambito, mes)
 ORDER BY ambito, s.mes;

-- ----------------------------------------------------------------------------
-- EDAN - tipos de evento mas recurrentes (historico total)
-- ----------------------------------------------------------------------------
DROP VIEW IF EXISTS publico.v_edan_tipos_evento;
CREATE VIEW publico.v_edan_tipos_evento AS
WITH base AS (
    SELECT 'consolidado'::text AS ambito, te.nombre AS tipo
      FROM edan.edan e
      JOIN edan.tipo_evento te ON te.id_tipo_evento = e.id_tipo_evento
     WHERE e.pendiente_eliminacion = FALSE
    UNION ALL
    SELECT 'local', te.nombre
      FROM edan.edan_localidades l
      JOIN edan.tipo_evento te ON te.id_tipo_evento = l.id_tipo_evento
     WHERE l.pendiente_eliminacion = FALSE
)
SELECT ambito, tipo, count(*) AS total
  FROM base
 GROUP BY ambito, tipo
 ORDER BY ambito, total DESC;

-- ----------------------------------------------------------------------------
-- EDAN - distribucion de estados del workflow (por ambito)
-- ----------------------------------------------------------------------------
DROP VIEW IF EXISTS publico.v_edan_estados;
CREATE VIEW publico.v_edan_estados AS
SELECT 'consolidado'::text AS ambito, es.orden, es.nombre AS estado, count(*) AS total
  FROM edan.edan e
  JOIN edan.estado_edan es ON es.id_estado = e.id_estado
 WHERE e.pendiente_eliminacion = FALSE
 GROUP BY es.orden, es.nombre
UNION ALL
SELECT 'local', le.id_edan_localidad_estado::int, le.nombre, count(*)
  FROM edan.edan_localidades l
  JOIN edan.edan_localidades_estado le
    ON le.id_edan_localidad_estado = l.id_edan_localidad_estado
 WHERE l.pendiente_eliminacion = FALSE
 GROUP BY le.id_edan_localidad_estado, le.nombre
 ORDER BY ambito, orden;

-- ----------------------------------------------------------------------------
-- EDAN - ranking por departamento (eventos y poblacion afectada)
-- ----------------------------------------------------------------------------
DROP VIEW IF EXISTS publico.v_edan_departamentos;
CREATE VIEW publico.v_edan_departamentos AS
WITH base AS (
    SELECT 'consolidado'::text AS ambito, e.id_departamento,
           COALESCE(e.total_poblacion_afectada, 0) AS pob
      FROM edan.edan e
     WHERE e.pendiente_eliminacion = FALSE AND e.id_departamento IS NOT NULL
    UNION ALL
    SELECT 'local', l.id_departamento, COALESCE(l.total_poblacion_afectada, 0)
      FROM edan.edan_localidades l
     WHERE l.pendiente_eliminacion = FALSE AND l.id_departamento IS NOT NULL
)
SELECT b.ambito, d.id AS id_departamento, d.nombre AS departamento,
       count(*) AS eventos, sum(b.pob) AS poblacion_afectada
  FROM base b
  JOIN shared.departamento d ON d.id = b.id_departamento
 GROUP BY b.ambito, d.id, d.nombre
 ORDER BY ambito, eventos DESC;

-- ----------------------------------------------------------------------------
-- EDAN - sectores afectados (flags imp_* de edan_localidades)
-- ----------------------------------------------------------------------------
DROP VIEW IF EXISTS publico.v_edan_sectores;
CREATE VIEW publico.v_edan_sectores AS
WITH l AS (
    SELECT * FROM edan.edan_localidades WHERE pendiente_eliminacion = FALSE
)
SELECT v.sector, count(*) FILTER (WHERE v.flag) AS total
  FROM l
  CROSS JOIN LATERAL (VALUES
      ('Impacto poblacion',          l.imp_impacto_poblacion),
      ('Salud - establecimientos',   l.imp_salud_establecimientos),
      ('Salud - necesidades',        l.imp_necesidad_salud),
      ('Danos viales',               l.imp_danos_viales),
      ('Infraestructura publica',    l.imp_danos_infra_publica),
      ('Servicios basicos',          l.imp_servicios_basicos),
      ('Unidades educativas',        l.imp_unidades_educativas),
      ('Danos en vivienda',          l.imp_danos_vivienda),
      ('Danos agricultura',          l.imp_danos_agricultura),
      ('Danos pecuarios',            l.imp_danos_pecuarios),
      ('Infraestructura productiva', l.imp_infra_productiva),
      ('Primera respuesta',          l.imp_primera_respuesta),
      ('Proteccion',                 l.imp_proteccion),
      ('Necesidad humanitaria',      l.imp_necesidad_humanitaria)
  ) AS v(sector, flag)
 GROUP BY v.sector
 ORDER BY total DESC;

-- ----------------------------------------------------------------------------
-- REPOSITORIO - serie anual por origen (EDAN/RIDA/DOC_PRECEDENTE, rellena en 0)
-- ----------------------------------------------------------------------------
DROP VIEW IF EXISTS publico.v_repo_serie_anios;
CREATE VIEW publico.v_repo_serie_anios AS
WITH base AS (
    SELECT d.origen,
           extract(year FROM COALESCE(d.fecha_documento, d.fecha_subida))::int AS anio
      FROM repositorio.documentos d
     WHERE d.activo = TRUE
), origenes AS (SELECT DISTINCT origen FROM base),
limites AS (
    SELECT min(anio) AS anio_ini,
           greatest(max(anio), extract(year FROM current_date)::int) AS anio_fin
      FROM base
), serie AS (
    SELECT o.origen, gs.y::int AS anio
      FROM origenes o CROSS JOIN limites lm
      CROSS JOIN LATERAL generate_series(lm.anio_ini, lm.anio_fin) AS gs(y)
), conteo AS (
    SELECT origen, anio, count(*) AS total FROM base GROUP BY 1, 2
)
SELECT s.origen, s.anio, COALESCE(c.total, 0) AS total
  FROM serie s LEFT JOIN conteo c USING (origen, anio)
 ORDER BY origen, anio;

-- ----------------------------------------------------------------------------
-- REPOSITORIO - serie anual por tipo de documento (solo tipos con historial)
-- ----------------------------------------------------------------------------
DROP VIEW IF EXISTS publico.v_repo_serie_anios_tipo;
CREATE VIEW publico.v_repo_serie_anios_tipo AS
WITH base AS (
    SELECT t.id_tipo_documento, t.nombre AS tipo,
           extract(year FROM COALESCE(d.fecha_documento, d.fecha_subida))::int AS anio
      FROM repositorio.documentos d
      JOIN repositorio.tipo_documento t ON t.id_tipo_documento = d.id_tipo_documento
     WHERE d.activo = TRUE
), tipos AS (SELECT DISTINCT id_tipo_documento, tipo FROM base),
limites AS (
    SELECT min(anio) AS anio_ini,
           greatest(max(anio), extract(year FROM current_date)::int) AS anio_fin
      FROM base
), serie AS (
    SELECT tp.id_tipo_documento, tp.tipo, gs.y::int AS anio
      FROM tipos tp CROSS JOIN limites lm
      CROSS JOIN LATERAL generate_series(lm.anio_ini, lm.anio_fin) AS gs(y)
), conteo AS (
    SELECT id_tipo_documento, anio, count(*) AS total FROM base GROUP BY 1, 2
)
SELECT s.id_tipo_documento, s.tipo, s.anio, COALESCE(c.total, 0) AS total
  FROM serie s LEFT JOIN conteo c USING (id_tipo_documento, anio)
 ORDER BY anio, id_tipo_documento;

-- ----------------------------------------------------------------------------
-- REPOSITORIO - resumen long (dimension, llave, total)
-- ----------------------------------------------------------------------------
DROP VIEW IF EXISTS publico.v_repo_resumen;
CREATE VIEW publico.v_repo_resumen AS
SELECT 'total'::text AS dimension, 'documentos_activos'::text AS llave,
       count(*)::bigint AS total
  FROM repositorio.documentos WHERE activo = TRUE
UNION ALL
SELECT 'origen', origen, count(*)
  FROM repositorio.documentos WHERE activo = TRUE GROUP BY origen
UNION ALL
SELECT 'tipo', t.nombre, count(*)
  FROM repositorio.documentos d
  JOIN repositorio.tipo_documento t ON t.id_tipo_documento = d.id_tipo_documento
 WHERE d.activo = TRUE GROUP BY t.nombre
UNION ALL
SELECT 'firma', CASE WHEN tiene_firma_digital THEN 'con_firma' ELSE 'sin_firma' END, count(*)
  FROM repositorio.documentos WHERE activo = TRUE
 GROUP BY CASE WHEN tiene_firma_digital THEN 'con_firma' ELSE 'sin_firma' END;

-- ----------------------------------------------------------------------------
-- USUARIOS - solo conteos agregados (sin datos personales)
-- ----------------------------------------------------------------------------
DROP VIEW IF EXISTS publico.v_usuarios_rol;
CREATE VIEW publico.v_usuarios_rol AS
SELECT r.nombre AS rol, count(u.id_usuario) AS cantidad
  FROM usuarios.rol r
  LEFT JOIN usuarios.usuario u ON u.id_rol = r.id_rol AND u.activo = TRUE
 GROUP BY r.nombre
 ORDER BY cantidad DESC;

DROP VIEW IF EXISTS publico.v_usuarios_cargo;
CREATE VIEW publico.v_usuarios_cargo AS
SELECT COALESCE(NULLIF(TRIM(u.cargo), ''), 'sin_especificar') AS cargo,
       count(*) AS cantidad
  FROM usuarios.usuario u
 WHERE u.activo = TRUE
 GROUP BY 1
 ORDER BY cantidad DESC;

DROP VIEW IF EXISTS publico.v_usuarios_geografia;
CREATE VIEW publico.v_usuarios_geografia AS
SELECT 'departamento'::text AS nivel, d.id AS id, d.nombre, count(u.id_usuario) AS cantidad
  FROM usuarios.usuario u
  JOIN shared.departamento d ON d.id = u.id_departamento
 WHERE u.activo = TRUE
 GROUP BY d.id, d.nombre
UNION ALL
SELECT 'provincia', p.id, p.nombre, count(u.id_usuario)
  FROM usuarios.usuario u
  JOIN shared.provincia p ON p.id = u.id_provincia
 WHERE u.activo = TRUE
 GROUP BY p.id, p.nombre
UNION ALL
SELECT 'municipio', m.id, m.nombre, count(u.id_usuario)
  FROM usuarios.usuario u
  JOIN shared.municipio m ON m.id = u.id_municipio
 WHERE u.activo = TRUE
 GROUP BY m.id, m.nombre
 ORDER BY nivel, cantidad DESC;

DROP VIEW IF EXISTS publico.v_usuarios_resumen;
CREATE VIEW publico.v_usuarios_resumen AS
SELECT 'total'::text AS llave, count(*) AS cantidad FROM usuarios.usuario
UNION ALL
SELECT 'activos', count(*) FROM usuarios.usuario WHERE activo = TRUE
UNION ALL
SELECT 'inactivos', count(*) FROM usuarios.usuario WHERE activo = FALSE
UNION ALL
SELECT 'con_municipio', count(*) FROM usuarios.usuario
 WHERE activo = TRUE AND id_municipio IS NOT NULL;

-- ----------------------------------------------------------------------------
-- MOTORIA - resumen de acervo y uso (solo conteos)
-- ----------------------------------------------------------------------------
DROP VIEW IF EXISTS publico.v_motoria_resumen;
CREATE VIEW publico.v_motoria_resumen AS
SELECT 'documentos'::text AS llave, count(*) AS cantidad FROM motor_ia.documentos
UNION ALL
SELECT 'chunks', count(*) FROM motor_ia.chunks
UNION ALL
SELECT 'proveedores_llm', count(*) FROM motor_ia.proveedores_llm
UNION ALL
SELECT 'uso_llm', count(*) FROM motor_ia.uso_llm
UNION ALL
SELECT 'uso_llm_exitoso', count(*) FROM motor_ia.uso_llm WHERE exitoso = TRUE
UNION ALL
SELECT 'uso_embeddings', count(*) FROM motor_ia.uso_embeddings
UNION ALL
SELECT 'uso_embeddings_exitoso', count(*) FROM motor_ia.uso_embeddings WHERE exitoso = TRUE;

-- ----------------------------------------------------------------------------
-- GEO - conteos de la division territorial
-- ----------------------------------------------------------------------------
DROP VIEW IF EXISTS publico.v_geo_resumen;
CREATE VIEW publico.v_geo_resumen AS
SELECT 'departamentos'::text AS llave, count(*) AS cantidad FROM shared.departamento
UNION ALL
SELECT 'provincias', count(*) FROM shared.provincia
UNION ALL
SELECT 'municipios', count(*) FROM shared.municipio
UNION ALL
SELECT 'manzanos', count(*) FROM shared.manzanos
UNION ALL
SELECT 'comunidades', count(*) FROM shared.comunidades;

-- ----------------------------------------------------------------------------
-- CENSO 2024 - poblacion y personas por hogar por nivel (misma semantica que
-- api/shared: base oficial hogares_ine; redondeo normal (2p+b)/(2b))
-- ----------------------------------------------------------------------------
DROP VIEW IF EXISTS publico.v_censo_nacional;
CREATE VIEW publico.v_censo_nacional AS
WITH u AS (
    SELECT COALESCE(sum(personas), 0) AS pob,
           COALESCE(sum(viviendas), 0) AS viv,
           COALESCE(sum(hogares), 0) AS hog,
           count(hogares) AS hog_n,
           sum(CASE WHEN hogares IS NOT NULL THEN personas ELSE 0 END) AS pob_hog
      FROM (SELECT personas, viviendas, hogares FROM shared.manzanos
            UNION ALL
            SELECT personas, viviendas, hogares FROM shared.comunidades) s
), ine AS (
    SELECT CASE WHEN count(*) = 0 THEN NULL ELSE sum(h.hogares) END AS hog_ine
      FROM shared.censo2024_hogares_municipio h
)
SELECT 'nacional'::text AS nivel,
       NULL::int AS id_departamento, NULL::int AS id_provincia, NULL::int AS id_municipio,
       NULL::varchar AS codigo_ine,
       'Estado Plurinacional de Bolivia'::text AS nombre,
       u.pob AS poblacion, u.viv AS viviendas,
       CASE WHEN u.hog_n = 0 THEN NULL ELSE u.hog END AS hogares,
       u.hog_n AS unidades_con_hogares,
       i.hog_ine AS hogares_ine,
       CASE
         WHEN COALESCE(i.hog_ine, 0) > 0
           THEN div(2 * u.pob + i.hog_ine, 2 * i.hog_ine)::int
         WHEN COALESCE(u.hog, 0) > 0
           THEN div(2 * u.pob_hog + u.hog, 2 * u.hog)::int
         ELSE NULL
       END AS personas_por_hogar
  FROM u CROSS JOIN ine i;

DROP VIEW IF EXISTS publico.v_censo_departamentos;
CREATE VIEW publico.v_censo_departamentos AS
WITH s AS (
    SELECT id_departamento AS k, personas, viviendas, hogares FROM shared.manzanos
    UNION ALL
    SELECT id_departamento, personas, viviendas, hogares FROM shared.comunidades
), u AS (
    SELECT k, sum(personas) AS pob, sum(viviendas) AS viv, sum(hogares) AS hog,
           count(hogares) AS hog_n,
           sum(CASE WHEN hogares IS NOT NULL THEN personas ELSE 0 END) AS pob_hog
      FROM s GROUP BY k
), ine AS (
    SELECT m.id_departamento AS k, sum(h.hogares) AS hog_ine
      FROM shared.municipio m
      JOIN shared.censo2024_hogares_municipio h ON h.id_municipio = m.id
     GROUP BY m.id_departamento
)
SELECT 'departamento'::text AS nivel,
       d.id AS id_departamento, NULL::int AS id_provincia, NULL::int AS id_municipio,
       d.codigo_ine, d.nombre,
       COALESCE(u.pob, 0) AS poblacion,
       COALESCE(u.viv, 0) AS viviendas,
       CASE WHEN COALESCE(u.hog_n, 0) = 0 THEN NULL ELSE COALESCE(u.hog, 0) END AS hogares,
       COALESCE(u.hog_n, 0) AS unidades_con_hogares,
       i.hog_ine AS hogares_ine,
       CASE
         WHEN COALESCE(i.hog_ine, 0) > 0
           THEN div(2 * COALESCE(u.pob, 0) + i.hog_ine, 2 * i.hog_ine)::int
         WHEN COALESCE(u.hog, 0) > 0
           THEN div(2 * COALESCE(u.pob_hog, 0) + u.hog, 2 * u.hog)::int
         ELSE NULL
       END AS personas_por_hogar
  FROM shared.departamento d
  LEFT JOIN u ON u.k = d.id
  LEFT JOIN ine i ON i.k = d.id
 ORDER BY d.id;

DROP VIEW IF EXISTS publico.v_censo_provincias;
CREATE VIEW publico.v_censo_provincias AS
WITH s AS (
    SELECT id_provincia AS k, personas, viviendas, hogares FROM shared.manzanos
    UNION ALL
    SELECT id_provincia, personas, viviendas, hogares FROM shared.comunidades
), u AS (
    SELECT k, sum(personas) AS pob, sum(viviendas) AS viv, sum(hogares) AS hog,
           count(hogares) AS hog_n,
           sum(CASE WHEN hogares IS NOT NULL THEN personas ELSE 0 END) AS pob_hog
      FROM s GROUP BY k
), ine AS (
    SELECT m.id_provincia AS k, sum(h.hogares) AS hog_ine
      FROM shared.municipio m
      JOIN shared.censo2024_hogares_municipio h ON h.id_municipio = m.id
     GROUP BY m.id_provincia
)
SELECT 'provincia'::text AS nivel,
       p.id_departamento, p.id AS id_provincia, NULL::int AS id_municipio,
       p.codigo_ine, p.nombre,
       COALESCE(u.pob, 0) AS poblacion,
       COALESCE(u.viv, 0) AS viviendas,
       CASE WHEN COALESCE(u.hog_n, 0) = 0 THEN NULL ELSE COALESCE(u.hog, 0) END AS hogares,
       COALESCE(u.hog_n, 0) AS unidades_con_hogares,
       i.hog_ine AS hogares_ine,
       CASE
         WHEN COALESCE(i.hog_ine, 0) > 0
           THEN div(2 * COALESCE(u.pob, 0) + i.hog_ine, 2 * i.hog_ine)::int
         WHEN COALESCE(u.hog, 0) > 0
           THEN div(2 * COALESCE(u.pob_hog, 0) + u.hog, 2 * u.hog)::int
         ELSE NULL
       END AS personas_por_hogar
  FROM shared.provincia p
  LEFT JOIN u ON u.k = p.id
  LEFT JOIN ine i ON i.k = p.id
 ORDER BY p.id;

DROP VIEW IF EXISTS publico.v_censo_municipios;
CREATE VIEW publico.v_censo_municipios AS
WITH s AS (
    SELECT id_municipio AS k, personas, viviendas, hogares FROM shared.manzanos
    UNION ALL
    SELECT id_municipio, personas, viviendas, hogares FROM shared.comunidades
), u AS (
    SELECT k, sum(personas) AS pob, sum(viviendas) AS viv, sum(hogares) AS hog,
           count(hogares) AS hog_n,
           sum(CASE WHEN hogares IS NOT NULL THEN personas ELSE 0 END) AS pob_hog
      FROM s GROUP BY k
)
SELECT 'municipio'::text AS nivel,
       m.id_departamento, m.id_provincia, m.id AS id_municipio,
       m.codigo_ine, m.nombre,
       COALESCE(u.pob, 0) AS poblacion,
       COALESCE(u.viv, 0) AS viviendas,
       CASE WHEN COALESCE(u.hog_n, 0) = 0 THEN NULL ELSE COALESCE(u.hog, 0) END AS hogares,
       COALESCE(u.hog_n, 0) AS unidades_con_hogares,
       h.hogares AS hogares_ine,
       CASE
         WHEN COALESCE(h.hogares, 0) > 0
           THEN div(2 * COALESCE(u.pob, 0) + h.hogares, 2 * h.hogares)::int
         WHEN COALESCE(u.hog, 0) > 0
           THEN div(2 * COALESCE(u.pob_hog, 0) + u.hog, 2 * u.hog)::int
         ELSE NULL
       END AS personas_por_hogar
  FROM shared.municipio m
  LEFT JOIN u ON u.k = m.id
  LEFT JOIN shared.censo2024_hogares_municipio h ON h.id_municipio = m.id
 ORDER BY m.id;

-- ----------------------------------------------------------------------------
-- KPIs globales (una fila para las tarjetas de portada)
-- ----------------------------------------------------------------------------
DROP VIEW IF EXISTS publico.v_kpis_globales;
CREATE VIEW publico.v_kpis_globales AS
SELECT
    (SELECT count(*) FROM edan.edan WHERE pendiente_eliminacion = FALSE)
        AS edan_consolidado_total,
    (SELECT count(*) FROM edan.edan_localidades WHERE pendiente_eliminacion = FALSE)
        AS edan_local_total,
    (SELECT COALESCE(sum(total_poblacion_afectada), 0) FROM edan.edan_localidades
      WHERE pendiente_eliminacion = FALSE) AS edan_poblacion_afectada,
    (SELECT count(*) FROM edan.edan_localidades
      WHERE pendiente_eliminacion = FALSE AND id_edan_localidad_estado IN (3, 5))
        AS edan_local_aprobados,
    (SELECT count(DISTINCT id_departamento) FROM edan.edan_localidades
      WHERE pendiente_eliminacion = FALSE) AS edan_departamentos_afectados,
    (SELECT min(fecha_evento) FROM edan.edan_localidades
      WHERE pendiente_eliminacion = FALSE) AS edan_primera_fecha,
    (SELECT max(fecha_evento) FROM edan.edan_localidades
      WHERE pendiente_eliminacion = FALSE) AS edan_ultima_fecha,
    (SELECT count(*) FROM repositorio.documentos WHERE activo = TRUE)
        AS repo_documentos,
    (SELECT count(*) FROM repositorio.documentos
      WHERE activo = TRUE AND origen = 'DOC_PRECEDENTE') AS repo_doc_precedentes,
    (SELECT count(*) FROM usuarios.usuario WHERE activo = TRUE) AS usuarios_activos,
    (SELECT count(*) FROM shared.departamento) AS geo_departamentos,
    (SELECT count(*) FROM shared.provincia)    AS geo_provincias,
    (SELECT count(*) FROM shared.municipio)    AS geo_municipios,
    (SELECT count(*) FROM shared.manzanos)     AS geo_manzanos,
    (SELECT count(*) FROM shared.comunidades)  AS geo_comunidades,
    (SELECT COALESCE(sum(personas), 0) FROM (
        SELECT personas FROM shared.manzanos
        UNION ALL SELECT personas FROM shared.comunidades) x) AS censo_poblacion,
    (SELECT CASE WHEN count(*) = 0 THEN NULL ELSE sum(hogares) END
       FROM shared.censo2024_hogares_municipio) AS censo_hogares_ine,
    (SELECT count(*) FROM motor_ia.documentos) AS motoria_documentos,
    (SELECT count(*) FROM motor_ia.chunks)     AS motoria_chunks;

COMMENT ON SCHEMA publico IS
    'Vistas de metricas agregadas y publicas (GET /api/v2/publico) - sin datos personales.';

COMMIT;
SELECT 'IDEMPOTENT OK v2.66.0 vistas publico metricas';
