-- SINAGERSAT/BaseData - SINB modelo limpio v2
-- Esquema sinb limpio: sin identidad propia (usa usuarios.*), sin territorio propio (usa shared.*),
-- sin id_legacy, sin tablas t_*. FKs reales a shared.municipio, shared.comunidades, usuarios.usuario.
-- Autor: opencode | Fecha: 2026-10-03 | Paso 1: estructura vacía para revisión

SET statement_timeout = 0;

-- 1. Schema y extensiones
DROP SCHEMA IF EXISTS sinb CASCADE;
CREATE SCHEMA sinb;

CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- 2. Tipos enum
CREATE TYPE sinb.estado_registro AS ENUM ('ACTIVO', 'INACTIVO', 'ELIMINADO');
CREATE TYPE sinb.rol_en_sesion AS ENUM ('RESPONSABLE', 'ANOTADOR', 'REVISOR');
CREATE TYPE sinb.tipo_pronostico AS ENUM ('ESTACIONAL', 'TEMPORAL');
CREATE TYPE sinb.confianza_nivel AS ENUM ('ALTA', 'MEDIA', 'BAJA');
CREATE TYPE sinb.estado_validacion AS ENUM ('EMITIDO', 'ACEPTADO', 'RECHAZADO', 'EN_REVISION');
CREATE TYPE sinb.tipo_desviacion AS ENUM ('PRECOZ', 'TARDIO', 'AUSENTE', 'NORMAL');

-- 3. Catálogos bioculturales
CREATE TABLE sinb.grupo (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    codigo character varying(20) NOT NULL UNIQUE,
    nombre text NOT NULL,
    descripcion text,
    estado sinb.estado_registro NOT NULL DEFAULT 'ACTIVO',
    creado_en timestamptz NOT NULL DEFAULT now(),
    actualizado_en timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE sinb.indicador_natural (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    codigo character varying(20) NOT NULL UNIQUE,
    nombre_cientifico text NOT NULL,
    nombre_comun text,
    id_grupo uuid REFERENCES sinb.grupo(id) ON DELETE RESTRICT,
    descripcion text,
    requiere_consentimiento boolean NOT NULL DEFAULT false,
    estado sinb.estado_registro NOT NULL DEFAULT 'ACTIVO',
    creado_en timestamptz NOT NULL DEFAULT now(),
    actualizado_en timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uk_indicador_grupo UNIQUE (codigo, id_grupo)
);

CREATE TABLE sinb.caracteristica (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    id_indicador_natural uuid NOT NULL REFERENCES sinb.indicador_natural(id) ON DELETE RESTRICT,
    caracteristica text NOT NULL,
    estado sinb.estado_registro NOT NULL DEFAULT 'ACTIVO',
    creado_en timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE sinb.comportamiento (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    id_grupo uuid REFERENCES sinb.grupo(id) ON DELETE RESTRICT,
    id_caracteristica uuid NOT NULL REFERENCES sinb.caracteristica(id) ON DELETE RESTRICT,
    comportamiento text NOT NULL,
    estado sinb.estado_registro NOT NULL DEFAULT 'ACTIVO',
    creado_en timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE sinb.significado (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    id_grupo uuid REFERENCES sinb.grupo(id) ON DELETE RESTRICT,
    id_comportamiento uuid NOT NULL REFERENCES sinb.comportamiento(id) ON DELETE RESTRICT,
    significado text NOT NULL,
    categoria text,
    estado sinb.estado_registro NOT NULL DEFAULT 'ACTIVO',
    creado_en timestamptz NOT NULL DEFAULT now()
);

-- Territorio: zona_geografica + puentes a shared
CREATE TABLE sinb.zona_geografica (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    codigo character varying(10) NOT NULL UNIQUE,
    nombre character varying(100) NOT NULL,
    descripcion text,
    estado sinb.estado_registro NOT NULL DEFAULT 'ACTIVO'
);

CREATE TABLE sinb.zona_comunidad (
    id_zona uuid NOT NULL REFERENCES sinb.zona_geografica(id) ON DELETE CASCADE,
    codigo_comunidad text NOT NULL REFERENCES shared.comunidades(codigo_ine) ON DELETE CASCADE,
    PRIMARY KEY (id_zona, codigo_comunidad)
);

CREATE TABLE sinb.zona_manzano (
    id_zona uuid NOT NULL REFERENCES sinb.zona_geografica(id) ON DELETE CASCADE,
    codigo_manzano text NOT NULL REFERENCES shared.manzanos(codigo_ine) ON DELETE CASCADE,
    PRIMARY KEY (id_zona, codigo_manzano)
);

-- Observación
CREATE TABLE sinb.observacion (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    codigo_corto text NOT NULL UNIQUE,
    codigo_comunidad text NOT NULL REFERENCES shared.comunidades(codigo_ine) ON DELETE RESTRICT,
    id_municipio integer NOT NULL REFERENCES shared.municipio(id) ON DELETE RESTRICT,
    id_usuario_responsable integer NOT NULL REFERENCES usuarios.usuario(id_usuario) ON DELETE RESTRICT,
    fecha_inicio date NOT NULL,
    fecha_fin date NOT NULL,
    hora_inicio time,
    hora_fin time,
    fecha_registro date NOT NULL,
    clima_observado text,
    es_validada boolean NOT NULL DEFAULT false,
    validada_por integer REFERENCES usuarios.usuario(id_usuario) ON DELETE SET NULL,
    validada_en timestamptz,
    observacion_rechazada_motivo text,
    estado sinb.estado_registro NOT NULL DEFAULT 'ACTIVO',
    creado_en timestamptz NOT NULL DEFAULT now(),
    actualizado_en timestamptz NOT NULL DEFAULT now(),
    version_registro integer NOT NULL DEFAULT 1 CHECK (version_registro >= 1),
    CONSTRAINT chk_fechas CHECK (fecha_fin >= fecha_inicio),
    CONSTRAINT chk_horas CHECK (hora_fin IS NULL OR hora_inicio IS NULL OR hora_fin >= hora_inicio),
    CONSTRAINT chk_validacion CHECK (
        (es_validada AND validada_por IS NOT NULL AND validada_en IS NOT NULL)
        OR (NOT es_validada)
    )
);

CREATE TABLE sinb.observacion_registro (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    id_observacion uuid NOT NULL REFERENCES sinb.observacion(id) ON DELETE CASCADE,
    id_caracteristica uuid REFERENCES sinb.caracteristica(id) ON DELETE RESTRICT,
    id_comportamiento uuid REFERENCES sinb.comportamiento(id) ON DELETE RESTRICT,
    id_significado uuid REFERENCES sinb.significado(id) ON DELETE RESTRICT,
    id_indicador_natural uuid REFERENCES sinb.indicador_natural(id) ON DELETE RESTRICT,
    valor_observado text,
    unidad text,
    creado_en timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT chk_al_menos_uno CHECK (
        id_caracteristica IS NOT NULL OR id_comportamiento IS NOT NULL 
        OR id_significado IS NOT NULL OR id_indicador_natural IS NOT NULL
    )
);

-- Pronósticos
CREATE TABLE sinb.campo_pronostico (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre character varying(100) NOT NULL UNIQUE,
    unidad text,
    tipo character varying(20) NOT NULL,
    estado sinb.estado_registro NOT NULL DEFAULT 'ACTIVO'
);

CREATE TABLE sinb.escenario (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    id_campo_pronostico uuid NOT NULL REFERENCES sinb.campo_pronostico(id) ON DELETE RESTRICT,
    nombre character varying(100) NOT NULL,
    descripcion text,
    valor_min numeric,
    valor_max numeric,
    estado sinb.estado_registro NOT NULL DEFAULT 'ACTIVO'
);

CREATE TABLE sinb.categoria_pronostico_temporal (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre character varying(100) NOT NULL UNIQUE,
    descripcion text,
    estado sinb.estado_registro NOT NULL DEFAULT 'ACTIVO'
);

CREATE TABLE sinb.pronostico_estacional (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    codigo character varying(50) NOT NULL UNIQUE,
    id_campo_pronostico uuid NOT NULL REFERENCES sinb.campo_pronostico(id) ON DELETE RESTRICT,
    fecha_emision date NOT NULL,
    periodo_inicio date NOT NULL,
    periodo_fin date NOT NULL,
    estado sinb.estado_validacion NOT NULL DEFAULT 'EMITIDO',
    id_usuario_elabora integer REFERENCES usuarios.usuario(id_usuario) ON DELETE SET NULL,
    notas text,
    creado_en timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT chk_periodo CHECK (periodo_fin >= periodo_inicio)
);

CREATE TABLE sinb.escenario_estacional (
    id_pronostico_estacional uuid NOT NULL REFERENCES sinb.pronostico_estacional(id) ON DELETE CASCADE,
    id_escenario uuid NOT NULL REFERENCES sinb.escenario(id) ON DELETE RESTRICT,
    probabilidad numeric(5,2) NOT NULL CHECK (probabilidad BETWEEN 0 AND 100),
    PRIMARY KEY (id_pronostico_estacional, id_escenario)
);

CREATE TABLE sinb.pronostico_temporal (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    codigo character varying(50) NOT NULL UNIQUE,
    id_categoria uuid NOT NULL REFERENCES sinb.categoria_pronostico_temporal(id) ON DELETE RESTRICT,
    id_campo_pronostico uuid NOT NULL REFERENCES sinb.campo_pronostico(id) ON DELETE RESTRICT,
    fecha_emision date NOT NULL,
    fecha_inicio date NOT NULL,
    fecha_fin date NOT NULL,
    valor_esperado text,
    confianza sinb.confianza_nivel,
    estado sinb.estado_validacion NOT NULL DEFAULT 'EMITIDO',
    creado_en timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT chk_fechas_pronostico CHECK (fecha_fin >= fecha_inicio)
);

CREATE TABLE sinb.observacion_pronostico (
    id_observacion uuid NOT NULL REFERENCES sinb.observacion(id) ON DELETE CASCADE,
    id_pronostico_estacional uuid REFERENCES sinb.pronostico_estacional(id) ON DELETE CASCADE,
    id_pronostico_temporal uuid REFERENCES sinb.pronostico_temporal(id) ON DELETE CASCADE,
    PRIMARY KEY (id_observacion),
    CONSTRAINT chk_un_pronostico CHECK (
        (id_pronostico_estacional IS NOT NULL AND id_pronostico_temporal IS NULL)
        OR (id_pronostico_estacional IS NULL AND id_pronostico_temporal IS NOT NULL)
    )
);

-- Recomendaciones
CREATE TABLE sinb.dimension_recomendacion (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    codigo character varying(20) NOT NULL UNIQUE,
    nombre character varying(100) NOT NULL,
    descripcion text,
    estado sinb.estado_registro NOT NULL DEFAULT 'ACTIVO'
);

CREATE TABLE sinb.categoria_comportamiento (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    id_dimension uuid NOT NULL REFERENCES sinb.dimension_recomendacion(id) ON DELETE RESTRICT,
    nombre character varying(100) NOT NULL,
    descripcion text,
    estado sinb.estado_registro NOT NULL DEFAULT 'ACTIVO'
);

CREATE TABLE sinb.recomendacion_local (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    texto text NOT NULL,
    id_dimension uuid NOT NULL REFERENCES sinb.dimension_recomendacion(id) ON DELETE RESTRICT,
    id_categoria uuid NOT NULL REFERENCES sinb.categoria_comportamiento(id) ON DELETE RESTRICT,
    codigo_comunidad text REFERENCES shared.comunidades(codigo_ine) ON DELETE CASCADE,
    id_municipio integer REFERENCES shared.municipio(id) ON DELETE CASCADE,
    id_usuario_elabora integer REFERENCES usuarios.usuario(id_usuario) ON DELETE SET NULL,
    estado sinb.estado_registro NOT NULL DEFAULT 'ACTIVO',
    creado_en timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE sinb.variante_local (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    id_recomendacion uuid NOT NULL REFERENCES sinb.recomendacion_local(id) ON DELETE CASCADE,
    variante text NOT NULL,
    ambito character varying(50),
    estado sinb.estado_registro NOT NULL DEFAULT 'ACTIVO',
    creado_en timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE sinb.observacion_recomendacion (
    id_observacion uuid NOT NULL REFERENCES sinb.observacion(id) ON DELETE CASCADE,
    id_recomendacion uuid NOT NULL REFERENCES sinb.recomendacion_local(id) ON DELETE CASCADE,
    PRIMARY KEY (id_observacion, id_recomendacion)
);

-- Aviso (pronóstico corto plazo)
CREATE TABLE sinb.aviso (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    codigo character varying(50) NOT NULL UNIQUE,
    id_campo_pronostico uuid NOT NULL REFERENCES sinb.campo_pronostico(id) ON DELETE RESTRICT,
    codigo_comunidad text NOT NULL REFERENCES shared.comunidades(codigo_ine) ON DELETE RESTRICT,
    id_municipio integer NOT NULL REFERENCES shared.municipio(id) ON DELETE RESTRICT,
    mensaje text NOT NULL,
    fecha_emision timestamptz NOT NULL DEFAULT now(),
    vigencia_horas integer NOT NULL DEFAULT 24,
    fecha_vencimiento timestamptz NOT NULL,
    estado sinb.estado_registro NOT NULL DEFAULT 'ACTIVO',
    id_usuario_emite integer REFERENCES usuarios.usuario(id_usuario) ON DELETE SET NULL,
    CONSTRAINT chk_vigencia CHECK (fecha_vencimiento > fecha_emision)
);

CREATE TABLE sinb.aviso_observador (
    id_aviso uuid NOT NULL REFERENCES sinb.aviso(id) ON DELETE CASCADE,
    id_usuario integer NOT NULL REFERENCES usuarios.usuario(id_usuario) ON DELETE CASCADE,
    confianza sinb.confianza_nivel,
    fecha_asignacion timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (id_aviso, id_usuario)
);

-- Pronóstico observador
CREATE TABLE sinb.pronostico_observador (
    id_pronostico_estacional uuid NOT NULL REFERENCES sinb.pronostico_estacional(id) ON DELETE CASCADE,
    id_usuario integer NOT NULL REFERENCES usuarios.usuario(id_usuario) ON DELETE CASCADE,
    confianza sinb.confianza_nivel,
    fecha_asignacion timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (id_pronostico_estacional, id_usuario)
);

CREATE TABLE sinb.observador_indice (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    id_usuario integer NOT NULL REFERENCES usuarios.usuario(id_usuario) ON DELETE CASCADE,
    id_indicador_natural uuid NOT NULL REFERENCES sinb.indicador_natural(id) ON DELETE CASCADE,
    tipo sinb.tipo_pronostico NOT NULL,
    valor numeric(5,2),
    fecha_calculo date NOT NULL DEFAULT CURRENT_DATE,
    CONSTRAINT uk_observador_indice UNIQUE (id_usuario, id_indicador_natural, tipo)
);

CREATE TABLE sinb.pronostico_digital (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    id_campo_pronostico uuid NOT NULL REFERENCES sinb.campo_pronostico(id) ON DELETE RESTRICT,
    codigo_comunidad text NOT NULL REFERENCES shared.comunidades(codigo_ine) ON DELETE CASCADE,
    fuente character varying(100) NOT NULL,
    fecha_modelo date NOT NULL,
    valor numeric,
    unidad text,
    creado_en timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uk_pronostico_digital UNIQUE (id_campo_pronostico, codigo_comunidad, fecha_modelo)
);

-- Climatología / Series
CREATE TABLE sinb.variable_climatica (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    codigo character varying(20) NOT NULL UNIQUE,
    nombre character varying(100) NOT NULL,
    unidad character varying(50) NOT NULL,
    descripcion text,
    estado sinb.estado_registro NOT NULL DEFAULT 'ACTIVO'
);

CREATE TABLE sinb.ventana_observacion (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    id_indicador_natural uuid NOT NULL REFERENCES sinb.indicador_natural(id) ON DELETE RESTRICT,
    id_comportamiento uuid REFERENCES sinb.comportamiento(id) ON DELETE SET NULL,
    nombre character varying(100) NOT NULL,
    mes_inicio integer NOT NULL CHECK (mes_inicio BETWEEN 1 AND 12),
    dia_inicio integer NOT NULL CHECK (dia_inicio BETWEEN 1 AND 31),
    mes_fin integer NOT NULL CHECK (mes_fin BETWEEN 1 AND 12),
    dia_fin integer NOT NULL CHECK (dia_fin BETWEEN 1 AND 31),
    estado sinb.estado_registro NOT NULL DEFAULT 'ACTIVO',
    CONSTRAINT chk_mes_fin CHECK (mes_fin >= mes_inicio OR (mes_fin < mes_inicio))
);

CREATE TABLE sinb.serie_climatica (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    id_variable_climatica uuid NOT NULL REFERENCES sinb.variable_climatica(id) ON DELETE RESTRICT,
    codigo_comunidad text NOT NULL REFERENCES shared.comunidades(codigo_ine) ON DELETE CASCADE,
    fecha date NOT NULL,
    valor numeric,
    fuente character varying(100),
    creado_en timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uk_serie UNIQUE (id_variable_climatica, codigo_comunidad, fecha)
);

CREATE TABLE sinb.norma_climatica (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    id_variable_climatica uuid NOT NULL REFERENCES sinb.variable_climatica(id) ON DELETE RESTRICT,
    codigo_comunidad text NOT NULL REFERENCES shared.comunidades(codigo_ine) ON DELETE CASCADE,
    mes integer NOT NULL CHECK (mes BETWEEN 1 AND 12),
    media_climatica numeric,
    minimo_climatico numeric,
    maximo_climatico numeric,
    anios_base character varying(20),
    estado sinb.estado_registro NOT NULL DEFAULT 'ACTIVO',
    CONSTRAINT uk_norma UNIQUE (id_variable_climatica, codigo_comunidad, mes)
);

CREATE TABLE sinb.escena_satelital (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    producto character varying(50) NOT NULL,
    fecha_adquisicion date NOT NULL,
    cobertura_nubes numeric(5,2) CHECK (cobertura_nubes BETWEEN 0 AND 100),
    huella geometry(MULTIPOLYGON, 4326),
    path_archivo text,
    creado_en timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE sinb.agregado_satelital (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    id_escena_satelital uuid NOT NULL REFERENCES sinb.escena_satelital(id) ON DELETE CASCADE,
    codigo_comunidad text NOT NULL REFERENCES shared.comunidades(codigo_ine) ON DELETE CASCADE,
    ndvi numeric(5,4),
    fecha_proceso timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uk_agregado UNIQUE (id_escena_satelital, codigo_comunidad)
);

CREATE TABLE sinb.serie_indicador (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    id_indicador_natural uuid NOT NULL REFERENCES sinb.indicador_natural(id) ON DELETE RESTRICT,
    codigo_comunidad text NOT NULL REFERENCES shared.comunidades(codigo_ine) ON DELETE CASCADE,
    id_ventana uuid REFERENCES sinb.ventana_observacion(id) ON DELETE SET NULL,
    id_comportamiento uuid REFERENCES sinb.comportamiento(id) ON DELETE SET NULL,
    anio integer NOT NULL,
    dia_ocurrencia integer,
    creado_en timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uk_serie_indicador UNIQUE (id_indicador_natural, codigo_comunidad, anio)
);

CREATE TABLE sinb.desviacion_indicador (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    id_indicador_natural uuid NOT NULL REFERENCES sinb.indicador_natural(id) ON DELETE RESTRICT,
    codigo_comunidad text NOT NULL REFERENCES shared.comunidades(codigo_ine) ON DELETE CASCADE,
    id_ventana uuid REFERENCES sinb.ventana_observacion(id) ON DELETE SET NULL,
    id_variable_climatica uuid REFERENCES sinb.variable_climatica(id) ON DELETE SET NULL,
    anio integer NOT NULL,
    tipo_desviacion sinb.tipo_desviacion,
    dias_desviacion integer,
    creado_en timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uk_desviacion UNIQUE (id_indicador_natural, codigo_comunidad, anio)
);

CREATE TABLE sinb.calificacion_indicador (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    id_indicador_natural uuid NOT NULL REFERENCES sinb.indicador_natural(id) ON DELETE RESTRICT,
    id_municipio integer NOT NULL REFERENCES shared.municipio(id) ON DELETE CASCADE,
    nivel character varying(20) NOT NULL CHECK (nivel IN ('EN_VERIFICACION', 'USABLE', 'REVISAR')),
    id_usuario_evalua integer REFERENCES usuarios.usuario(id_usuario) ON DELETE SET NULL,
    nota_evaluacion text,
    fecha_evaluacion timestamptz,
    estado sinb.estado_registro NOT NULL DEFAULT 'ACTIVO',
    creado_en timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uk_calificacion UNIQUE (id_indicador_natural, id_municipio)
);

-- Verificación
CREATE TABLE sinb.verificacion_pronostico (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    id_pronostico_estacional uuid REFERENCES sinb.pronostico_estacional(id) ON DELETE CASCADE,
    id_pronostico_temporal uuid REFERENCES sinb.pronostico_temporal(id) ON DELETE CASCADE,
    id_variable_climatica uuid REFERENCES sinb.variable_climatica(id) ON DELETE SET NULL,
    codigo_comunidad text REFERENCES shared.comunidades(codigo_ine) ON DELETE CASCADE,
    acierto_categoria boolean,
    error_absoluto numeric,
    sesgo numeric,
    estado character varying(20) NOT NULL DEFAULT 'NO_VERIFICABLE',
    notas text,
    es_autoevaluada boolean NOT NULL DEFAULT true,
    verificado_por integer REFERENCES usuarios.usuario(id_usuario) ON DELETE SET NULL,
    fecha_verificacion timestamptz,
    creado_en timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT chk_un_pronostico_verif CHECK (
        (id_pronostico_estacional IS NOT NULL AND id_pronostico_temporal IS NULL)
        OR (id_pronostico_estacional IS NULL AND id_pronostico_temporal IS NOT NULL)
    )
);

-- Gobernanza
CREATE TABLE sinb.evidencia (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    id_indicador_natural uuid REFERENCES sinb.indicador_natural(id) ON DELETE SET NULL,
    id_observacion_registro uuid REFERENCES sinb.observacion_registro(id) ON DELETE CASCADE,
    id_usuario_subio integer REFERENCES usuarios.usuario(id_usuario) ON DELETE SET NULL,
    path_archivo text NOT NULL,
    descripcion text,
    formato character varying(20),
    tamano_bytes integer,
    hash_sha256 character(64),
    fecha_carga timestamptz NOT NULL DEFAULT now(),
    activo boolean NOT NULL DEFAULT true,
    CONSTRAINT chk_sujeto CHECK (id_indicador_natural IS NOT NULL OR id_observacion_registro IS NOT NULL)
);

CREATE TABLE sinb.sinonimo_indicador (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    id_indicador_natural uuid NOT NULL REFERENCES sinb.indicador_natural(id) ON DELETE CASCADE,
    sinonimo text NOT NULL,
    codigo_comunidad text REFERENCES shared.comunidades(codigo_ine) ON DELETE CASCADE,
    id_usuario_aporta integer REFERENCES usuarios.usuario(id_usuario) ON DELETE SET NULL,
    estado sinb.estado_registro NOT NULL DEFAULT 'ACTIVO',
    CONSTRAINT uk_sinonimo UNIQUE (id_indicador_natural, sinonimo)
);

-- Índices
CREATE INDEX ind_observacion_comunidad ON sinb.observacion (codigo_comunidad, fecha_inicio DESC);
CREATE INDEX ind_observacion_municipio ON sinb.observacion (id_municipio, fecha_inicio DESC);
CREATE INDEX ind_observacion_pendiente ON sinb.observacion (id_municipio, fecha_inicio) WHERE es_validada = false AND estado = 'ACTIVO';
CREATE INDEX ind_observacion_responsable ON sinb.observacion (id_usuario_responsable, fecha_inicio DESC);

CREATE INDEX ind_observacion_registro ON sinb.observacion_registro (id_observacion);
CREATE INDEX ind_observacion_registro_indicador ON sinb.observacion_registro (id_indicador_natural) WHERE id_indicador_natural IS NOT NULL;

CREATE INDEX ind_serie_climatica ON sinb.serie_climatica (id_variable_climatica, codigo_comunidad, fecha);
CREATE INDEX ind_serie_indicador ON sinb.serie_indicador (id_indicador_natural, codigo_comunidad, anio);

CREATE INDEX ind_evidencia_indicador ON sinb.evidencia (id_indicador_natural, fecha_carga) WHERE id_indicador_natural IS NOT NULL;
CREATE INDEX ind_evidencia_observacion ON sinb.evidencia (id_observacion_registro) WHERE id_observacion_registro IS NOT NULL;

-- Índices de texto (trgm)
CREATE INDEX ind_significado_trgm ON sinb.significado USING gin (significado gin_trgm_ops);
CREATE INDEX ind_caracteristica_trgm ON sinb.caracteristica USING gin (caracteristica gin_trgm_ops);
CREATE INDEX ind_indicador_nombre_trgm ON sinb.indicador_natural USING gin (nombre_cientifico gin_trgm_ops);

-- 4. Vistas
CREATE VIEW sinb.v_registro_territorial AS
SELECT 
    o.id AS observacion_id,
    o.codigo_corto,
    c.nombre AS comunidad,
    c.codigo_ine AS codigo_comunidad,
    m.nombre AS municipio,
    m.id AS id_municipio,
    p.nombre AS provincia,
    d.nombre AS departamento,
    o.fecha_inicio,
    o.fecha_fin,
    u.usuario AS responsable
FROM sinb.observacion o
JOIN shared.comunidades c ON c.codigo_ine = o.codigo_comunidad
JOIN shared.municipio m ON m.id = o.id_municipio
JOIN shared.provincia p ON p.id = m.id_provincia
JOIN shared.departamento d ON d.id = m.id_departamento
JOIN usuarios.usuario u ON u.id_usuario = o.id_usuario_responsable
WHERE o.estado = 'ACTIVO';

CREATE VIEW sinb.v_primera_observacion AS
SELECT 
    r.id_indicador_natural,
    r.id_observacion,
    o.codigo_comunidad,
    DATE_TRUNC('day', o.fecha_inicio) AS fecha,
    EXTRACT(YEAR FROM o.fecha_inicio)::integer AS anio,
    EXTRACT(DOY FROM o.fecha_inicio)::integer AS dia_del_anio
FROM sinb.observacion_registro r
JOIN sinb.observacion o ON o.id = r.id_observacion
WHERE r.id_indicador_natural IS NOT NULL AND o.estado = 'ACTIVO';

CREATE VIEW sinb.v_tendencia_fenologia AS
SELECT 
    id_indicador_natural AS indicador_id,
    codigo_comunidad AS comunidad_id,
    dia_del_anio,
    (REGR_SLOPE(dia_del_anio, anio))::numeric(8,4) AS dias_por_anio,
    (REGR_SLOPE(dia_del_anio, anio) * 10)::numeric(8,2) AS dias_por_decada,
    COUNT(*) AS n_anos,
    CASE WHEN COUNT(*) >= 10 THEN true ELSE false END AS es_concluyente
FROM sinb.v_primera_observacion
GROUP BY id_indicador_natural, codigo_comunidad, dia_del_anio;

CREATE VIEW sinb.v_indicador_confiabilidad AS
SELECT 
    i.id AS indicador_id,
    i.nombre_cientifico,
    i.codigo,
    COUNT(DISTINCT s.codigo_comunidad) AS comunidades_con_serie,
    COUNT(DISTINCT s.anio) AS anos_registrados,
    CASE 
        WHEN COUNT(DISTINCT s.anio) >= 10 AND COUNT(DISTINCT s.codigo_comunidad) >= 5 THEN 'ALTA'
        WHEN COUNT(DISTINCT s.anio) >= 5 AND COUNT(DISTINCT s.codigo_comunidad) >= 3 THEN 'MEDIA'
        ELSE 'BAJA'
    END AS nivel_confiabilidad
FROM sinb.indicador_natural i
LEFT JOIN sinb.serie_indicador s ON s.id_indicador_natural = i.id
WHERE i.estado = 'ACTIVO'
GROUP BY i.id, i.nombre_cientifico, i.codigo;

CREATE VIEW sinb.v_calificacion_vigente AS
SELECT DISTINCT ON (c.id_indicador_natural, c.id_municipio)
    c.id,
    c.id_indicador_natural,
    c.id_municipio,
    c.nivel,
    c.fecha_evaluacion,
    c.estado,
    i.nombre_cientifico AS indicador,
    m.nombre AS municipio
FROM sinb.calificacion_indicador c
JOIN sinb.indicador_natural i ON i.id = c.id_indicador_natural
JOIN shared.municipio m ON m.id = c.id_municipio
WHERE c.estado = 'ACTIVO'
ORDER BY c.id_indicador_natural, c.id_municipio, c.fecha_evaluacion DESC NULLS LAST;

CREATE VIEW sinb.v_verificaciones_pendientes AS
SELECT 
    v.id,
    COALESCE(pe.codigo, pt.codigo) AS pronostico_codigo,
    COALESCE(pe.periodo_fin, pt.fecha_fin) AS fecha_fin,
    v.estado,
    v.creado_en
FROM sinb.verificacion_pronostico v
LEFT JOIN sinb.pronostico_estacional pe ON pe.id = v.id_pronostico_estacional
LEFT JOIN sinb.pronostico_temporal pt ON pt.id = v.id_pronostico_temporal
WHERE v.estado = 'NO_VERIFICABLE'
  AND COALESCE(pe.periodo_fin, pt.fecha_fin) < CURRENT_DATE
ORDER BY fecha_fin DESC;

-- 5. Grants (opcional, para roles de aplicación)
-- GRANT USAGE ON SCHEMA sinb TO sinagersat;
-- GRANT SELECT ON ALL TABLES IN SCHEMA sinb TO sinagersat;
-- GRANT INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA sinb TO sinagersat;
