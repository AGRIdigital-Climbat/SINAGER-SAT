--
-- PostgreSQL database dump
--

\restrict 0bt6cxd9cAWF4PmiIuwpuXMbbZlW1MiP6hH8gfItVtb81nTLD80NVKZz16nmtWI

-- Dumped from database version 16.14 (Ubuntu 16.14-0ubuntu0.24.04.1)
-- Dumped by pg_dump version 16.14 (Ubuntu 16.14-0ubuntu0.24.04.1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: edan; Type: SCHEMA; Schema: -; Owner: sinagersat
--

CREATE SCHEMA edan;


ALTER SCHEMA edan OWNER TO sinagersat;

--
-- Name: shared; Type: SCHEMA; Schema: -; Owner: sinagersat
--

CREATE SCHEMA shared;


ALTER SCHEMA shared OWNER TO sinagersat;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: ayuda_humanitaria; Type: TABLE; Schema: edan; Owner: postgres
--

CREATE TABLE edan.ayuda_humanitaria (
    id_ayuda_humanitaria integer NOT NULL,
    nombre character varying(100) NOT NULL,
    orden integer NOT NULL
);


ALTER TABLE edan.ayuda_humanitaria OWNER TO postgres;

--
-- Name: catalogo_ayuda_humanitaria_id_ayuda_humanitaria_seq; Type: SEQUENCE; Schema: edan; Owner: postgres
--

CREATE SEQUENCE edan.catalogo_ayuda_humanitaria_id_ayuda_humanitaria_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE edan.catalogo_ayuda_humanitaria_id_ayuda_humanitaria_seq OWNER TO postgres;

--
-- Name: catalogo_ayuda_humanitaria_id_ayuda_humanitaria_seq; Type: SEQUENCE OWNED BY; Schema: edan; Owner: postgres
--

ALTER SEQUENCE edan.catalogo_ayuda_humanitaria_id_ayuda_humanitaria_seq OWNED BY edan.ayuda_humanitaria.id_ayuda_humanitaria;


--
-- Name: categoria_proteccion; Type: TABLE; Schema: edan; Owner: postgres
--

CREATE TABLE edan.categoria_proteccion (
    id_categoria_proteccion integer NOT NULL,
    nombre character varying(100) NOT NULL,
    orden integer NOT NULL
);


ALTER TABLE edan.categoria_proteccion OWNER TO postgres;

--
-- Name: catalogo_categoria_proteccion_id_categoria_proteccion_seq; Type: SEQUENCE; Schema: edan; Owner: postgres
--

CREATE SEQUENCE edan.catalogo_categoria_proteccion_id_categoria_proteccion_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE edan.catalogo_categoria_proteccion_id_categoria_proteccion_seq OWNER TO postgres;

--
-- Name: catalogo_categoria_proteccion_id_categoria_proteccion_seq; Type: SEQUENCE OWNED BY; Schema: edan; Owner: postgres
--

ALTER SEQUENCE edan.catalogo_categoria_proteccion_id_categoria_proteccion_seq OWNED BY edan.categoria_proteccion.id_categoria_proteccion;


--
-- Name: grupo_etario; Type: TABLE; Schema: edan; Owner: postgres
--

CREATE TABLE edan.grupo_etario (
    id_grupo_etario integer NOT NULL,
    nombre character varying(50) NOT NULL,
    orden integer NOT NULL
);


ALTER TABLE edan.grupo_etario OWNER TO postgres;

--
-- Name: catalogo_grupo_etario_id_grupo_etario_seq; Type: SEQUENCE; Schema: edan; Owner: postgres
--

CREATE SEQUENCE edan.catalogo_grupo_etario_id_grupo_etario_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE edan.catalogo_grupo_etario_id_grupo_etario_seq OWNER TO postgres;

--
-- Name: catalogo_grupo_etario_id_grupo_etario_seq; Type: SEQUENCE OWNED BY; Schema: edan; Owner: postgres
--

ALTER SEQUENCE edan.catalogo_grupo_etario_id_grupo_etario_seq OWNED BY edan.grupo_etario.id_grupo_etario;


--
-- Name: servicio_basico; Type: TABLE; Schema: edan; Owner: postgres
--

CREATE TABLE edan.servicio_basico (
    id_servicio_basico integer NOT NULL,
    nombre character varying(50) NOT NULL,
    orden integer NOT NULL
);


ALTER TABLE edan.servicio_basico OWNER TO postgres;

--
-- Name: catalogo_servicio_basico_id_servicio_basico_seq; Type: SEQUENCE; Schema: edan; Owner: postgres
--

CREATE SEQUENCE edan.catalogo_servicio_basico_id_servicio_basico_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE edan.catalogo_servicio_basico_id_servicio_basico_seq OWNER TO postgres;

--
-- Name: catalogo_servicio_basico_id_servicio_basico_seq; Type: SEQUENCE OWNED BY; Schema: edan; Owner: postgres
--

ALTER SEQUENCE edan.catalogo_servicio_basico_id_servicio_basico_seq OWNED BY edan.servicio_basico.id_servicio_basico;


--
-- Name: tipo_evento; Type: TABLE; Schema: edan; Owner: postgres
--

CREATE TABLE edan.tipo_evento (
    id_tipo_evento integer NOT NULL,
    nombre character varying(50) NOT NULL
);


ALTER TABLE edan.tipo_evento OWNER TO postgres;

--
-- Name: catalogo_tipo_evento_id_tipo_evento_seq; Type: SEQUENCE; Schema: edan; Owner: postgres
--

CREATE SEQUENCE edan.catalogo_tipo_evento_id_tipo_evento_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE edan.catalogo_tipo_evento_id_tipo_evento_seq OWNER TO postgres;

--
-- Name: catalogo_tipo_evento_id_tipo_evento_seq; Type: SEQUENCE OWNED BY; Schema: edan; Owner: postgres
--

ALTER SEQUENCE edan.catalogo_tipo_evento_id_tipo_evento_seq OWNED BY edan.tipo_evento.id_tipo_evento;


--
-- Name: edan; Type: TABLE; Schema: edan; Owner: postgres
--

CREATE TABLE edan.edan (
    id_edan bigint NOT NULL,
    codigo_edan character varying(30),
    id_departamento integer,
    id_municipio integer,
    nombre_alcalde character varying(200),
    telefono_alcalde character varying(30),
    fecha_llenado date,
    fecha_evento date,
    hora_evento time without time zone,
    localidades_afectadas integer DEFAULT 0,
    total_poblacion_afectada integer DEFAULT 0,
    total_familias_afectadas integer DEFAULT 0,
    total_familias_damnificadas integer DEFAULT 0,
    nombre_responsable character varying(200),
    cargo_responsable character varying(100),
    telefono_responsable character varying(30),
    email_responsable character varying(150),
    usuario_registro integer,
    fecha_registro timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    id_reporte_rea bigint,
    fotografia text
);


ALTER TABLE edan.edan OWNER TO postgres;

--
-- Name: TABLE edan; Type: COMMENT; Schema: edan; Owner: postgres
--

COMMENT ON TABLE edan.edan IS 'Tabla principal - Evaluación de Daños y Análisis de Necesidades';


--
-- Name: edan_agricultura; Type: TABLE; Schema: edan; Owner: postgres
--

CREATE TABLE edan.edan_agricultura (
    id_agricultura integer NOT NULL,
    id_edan bigint NOT NULL,
    tipo_cultivo character varying(200),
    hectareas_afectadas numeric(10,2) DEFAULT 0,
    hectareas_perdidas numeric(10,2) DEFAULT 0,
    necesidades_inmediatas text,
    observaciones text
);


ALTER TABLE edan.edan_agricultura OWNER TO postgres;

--
-- Name: TABLE edan_agricultura; Type: COMMENT; Schema: edan; Owner: postgres
--

COMMENT ON TABLE edan.edan_agricultura IS 'Sección 9.1 - Daños y necesidades en agricultura';


--
-- Name: edan_agricultura_id_agricultura_seq; Type: SEQUENCE; Schema: edan; Owner: postgres
--

CREATE SEQUENCE edan.edan_agricultura_id_agricultura_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE edan.edan_agricultura_id_agricultura_seq OWNER TO postgres;

--
-- Name: edan_agricultura_id_agricultura_seq; Type: SEQUENCE OWNED BY; Schema: edan; Owner: postgres
--

ALTER SEQUENCE edan.edan_agricultura_id_agricultura_seq OWNED BY edan.edan_agricultura.id_agricultura;


--
-- Name: edan_ayuda_humanitaria; Type: TABLE; Schema: edan; Owner: postgres
--

CREATE TABLE edan.edan_ayuda_humanitaria (
    id_ayuda_edan integer NOT NULL,
    id_edan bigint NOT NULL,
    id_ayuda_humanitaria integer NOT NULL,
    requiere boolean DEFAULT false,
    observaciones text
);


ALTER TABLE edan.edan_ayuda_humanitaria OWNER TO postgres;

--
-- Name: TABLE edan_ayuda_humanitaria; Type: COMMENT; Schema: edan; Owner: postgres
--

COMMENT ON TABLE edan.edan_ayuda_humanitaria IS 'Sección 11 - Necesidades humanitarias';


--
-- Name: edan_ayuda_humanitaria_id_ayuda_edan_seq; Type: SEQUENCE; Schema: edan; Owner: postgres
--

CREATE SEQUENCE edan.edan_ayuda_humanitaria_id_ayuda_edan_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE edan.edan_ayuda_humanitaria_id_ayuda_edan_seq OWNER TO postgres;

--
-- Name: edan_ayuda_humanitaria_id_ayuda_edan_seq; Type: SEQUENCE OWNED BY; Schema: edan; Owner: postgres
--

ALTER SEQUENCE edan.edan_ayuda_humanitaria_id_ayuda_edan_seq OWNED BY edan.edan_ayuda_humanitaria.id_ayuda_edan;


--
-- Name: edan_comunidad; Type: TABLE; Schema: edan; Owner: postgres
--

CREATE TABLE edan.edan_comunidad (
    id_comunidad integer NOT NULL,
    id_edan bigint NOT NULL,
    nombre_comunidad character varying(200) NOT NULL
);


ALTER TABLE edan.edan_comunidad OWNER TO postgres;

--
-- Name: TABLE edan_comunidad; Type: COMMENT; Schema: edan; Owner: postgres
--

COMMENT ON TABLE edan.edan_comunidad IS 'Sección 12 - Comunidades/localidades/barrios afectados';


--
-- Name: edan_comunidad_id_comunidad_seq; Type: SEQUENCE; Schema: edan; Owner: postgres
--

CREATE SEQUENCE edan.edan_comunidad_id_comunidad_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE edan.edan_comunidad_id_comunidad_seq OWNER TO postgres;

--
-- Name: edan_comunidad_id_comunidad_seq; Type: SEQUENCE OWNED BY; Schema: edan; Owner: postgres
--

ALTER SEQUENCE edan.edan_comunidad_id_comunidad_seq OWNED BY edan.edan_comunidad.id_comunidad;


--
-- Name: edan_educacion_afectacion; Type: TABLE; Schema: edan; Owner: postgres
--

CREATE TABLE edan.edan_educacion_afectacion (
    id_educacion_afectacion integer NOT NULL,
    id_edan bigint NOT NULL,
    id_educacion_dano integer,
    nombre_establecimiento character varying(200) NOT NULL,
    estudiantes_afectados integer DEFAULT 0,
    profesores_afectados integer DEFAULT 0,
    administrativos_afectados integer DEFAULT 0,
    total_afectados integer DEFAULT 0,
    observaciones text
);


ALTER TABLE edan.edan_educacion_afectacion OWNER TO postgres;

--
-- Name: TABLE edan_educacion_afectacion; Type: COMMENT; Schema: edan; Owner: postgres
--

COMMENT ON TABLE edan.edan_educacion_afectacion IS 'Sección 7.2 - Afectación a alumnos, profesores y admin';


--
-- Name: edan_educacion_afectacion_id_educacion_afectacion_seq; Type: SEQUENCE; Schema: edan; Owner: postgres
--

CREATE SEQUENCE edan.edan_educacion_afectacion_id_educacion_afectacion_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE edan.edan_educacion_afectacion_id_educacion_afectacion_seq OWNER TO postgres;

--
-- Name: edan_educacion_afectacion_id_educacion_afectacion_seq; Type: SEQUENCE OWNED BY; Schema: edan; Owner: postgres
--

ALTER SEQUENCE edan.edan_educacion_afectacion_id_educacion_afectacion_seq OWNED BY edan.edan_educacion_afectacion.id_educacion_afectacion;


--
-- Name: edan_educacion_dano; Type: TABLE; Schema: edan; Owner: postgres
--

CREATE TABLE edan.edan_educacion_dano (
    id_educacion_dano integer NOT NULL,
    id_edan bigint NOT NULL,
    nombre_establecimiento character varying(200) NOT NULL,
    comunidad character varying(200),
    dano_parcial boolean DEFAULT false,
    dano_total boolean DEFAULT false,
    suspension_clases boolean DEFAULT false,
    perdida_material boolean DEFAULT false,
    funciona_albergue boolean DEFAULT false,
    observaciones text
);


ALTER TABLE edan.edan_educacion_dano OWNER TO postgres;

--
-- Name: TABLE edan_educacion_dano; Type: COMMENT; Schema: edan; Owner: postgres
--

COMMENT ON TABLE edan.edan_educacion_dano IS 'Sección 7.1 - Daños en unidades educativas';


--
-- Name: edan_educacion_dano_id_educacion_dano_seq; Type: SEQUENCE; Schema: edan; Owner: postgres
--

CREATE SEQUENCE edan.edan_educacion_dano_id_educacion_dano_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE edan.edan_educacion_dano_id_educacion_dano_seq OWNER TO postgres;

--
-- Name: edan_educacion_dano_id_educacion_dano_seq; Type: SEQUENCE OWNED BY; Schema: edan; Owner: postgres
--

ALTER SEQUENCE edan.edan_educacion_dano_id_educacion_dano_seq OWNED BY edan.edan_educacion_dano.id_educacion_dano;


--
-- Name: edan_id_edan_seq; Type: SEQUENCE; Schema: edan; Owner: postgres
--

CREATE SEQUENCE edan.edan_id_edan_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE edan.edan_id_edan_seq OWNER TO postgres;

--
-- Name: edan_id_edan_seq; Type: SEQUENCE OWNED BY; Schema: edan; Owner: postgres
--

ALTER SEQUENCE edan.edan_id_edan_seq OWNED BY edan.edan.id_edan;


--
-- Name: edan_infraestructura_productiva; Type: TABLE; Schema: edan; Owner: postgres
--

CREATE TABLE edan.edan_infraestructura_productiva (
    id_infra_productiva integer NOT NULL,
    id_edan bigint NOT NULL,
    tipo character varying(200),
    dano_parcial integer DEFAULT 0,
    dano_total integer DEFAULT 0,
    observaciones text
);


ALTER TABLE edan.edan_infraestructura_productiva OWNER TO postgres;

--
-- Name: TABLE edan_infraestructura_productiva; Type: COMMENT; Schema: edan; Owner: postgres
--

COMMENT ON TABLE edan.edan_infraestructura_productiva IS 'Sección 9.3 - Daño en infraestructura productiva';


--
-- Name: edan_infraestructura_productiva_id_infra_productiva_seq; Type: SEQUENCE; Schema: edan; Owner: postgres
--

CREATE SEQUENCE edan.edan_infraestructura_productiva_id_infra_productiva_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE edan.edan_infraestructura_productiva_id_infra_productiva_seq OWNER TO postgres;

--
-- Name: edan_infraestructura_productiva_id_infra_productiva_seq; Type: SEQUENCE OWNED BY; Schema: edan; Owner: postgres
--

ALTER SEQUENCE edan.edan_infraestructura_productiva_id_infra_productiva_seq OWNED BY edan.edan_infraestructura_productiva.id_infra_productiva;


--
-- Name: edan_infraestructura_publica; Type: TABLE; Schema: edan; Owner: postgres
--

CREATE TABLE edan.edan_infraestructura_publica (
    id_infraestructura_publica integer NOT NULL,
    id_edan bigint NOT NULL,
    localidad_comunidad character varying(200),
    tipo_estructura character varying(200),
    dano_parcial integer DEFAULT 0,
    dano_total integer DEFAULT 0,
    observaciones text
);


ALTER TABLE edan.edan_infraestructura_publica OWNER TO postgres;

--
-- Name: TABLE edan_infraestructura_publica; Type: COMMENT; Schema: edan; Owner: postgres
--

COMMENT ON TABLE edan.edan_infraestructura_publica IS 'Sección 5.2 - Daños en infraestructura pública';


--
-- Name: edan_infraestructura_publica_id_infraestructura_publica_seq; Type: SEQUENCE; Schema: edan; Owner: postgres
--

CREATE SEQUENCE edan.edan_infraestructura_publica_id_infraestructura_publica_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE edan.edan_infraestructura_publica_id_infraestructura_publica_seq OWNER TO postgres;

--
-- Name: edan_infraestructura_publica_id_infraestructura_publica_seq; Type: SEQUENCE OWNED BY; Schema: edan; Owner: postgres
--

ALTER SEQUENCE edan.edan_infraestructura_publica_id_infraestructura_publica_seq OWNED BY edan.edan_infraestructura_publica.id_infraestructura_publica;


--
-- Name: edan_infraestructura_vial; Type: TABLE; Schema: edan; Owner: postgres
--

CREATE TABLE edan.edan_infraestructura_vial (
    id_infraestructura_vial integer NOT NULL,
    id_edan bigint NOT NULL,
    via_acceso_puentes character varying(200),
    tramo character varying(200),
    localidad_origen character varying(200),
    localidad_destino character varying(200),
    dano_parcial_km numeric(10,2) DEFAULT 0,
    dano_total_km numeric(10,2) DEFAULT 0,
    necesidades_inmediatas text,
    observaciones text
);


ALTER TABLE edan.edan_infraestructura_vial OWNER TO postgres;

--
-- Name: TABLE edan_infraestructura_vial; Type: COMMENT; Schema: edan; Owner: postgres
--

COMMENT ON TABLE edan.edan_infraestructura_vial IS 'Sección 5.1 - Daños en infraestructura vial';


--
-- Name: edan_infraestructura_vial_id_infraestructura_vial_seq; Type: SEQUENCE; Schema: edan; Owner: postgres
--

CREATE SEQUENCE edan.edan_infraestructura_vial_id_infraestructura_vial_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE edan.edan_infraestructura_vial_id_infraestructura_vial_seq OWNER TO postgres;

--
-- Name: edan_infraestructura_vial_id_infraestructura_vial_seq; Type: SEQUENCE OWNED BY; Schema: edan; Owner: postgres
--

ALTER SEQUENCE edan.edan_infraestructura_vial_id_infraestructura_vial_seq OWNED BY edan.edan_infraestructura_vial.id_infraestructura_vial;


--
-- Name: edan_pecuaria; Type: TABLE; Schema: edan; Owner: postgres
--

CREATE TABLE edan.edan_pecuaria (
    id_pecuaria integer NOT NULL,
    id_edan bigint NOT NULL,
    tipo_especie character varying(200),
    raza character varying(200),
    animales_afectados integer DEFAULT 0,
    animales_muertos integer DEFAULT 0,
    necesidades_inmediatas text,
    observaciones text
);


ALTER TABLE edan.edan_pecuaria OWNER TO postgres;

--
-- Name: TABLE edan_pecuaria; Type: COMMENT; Schema: edan; Owner: postgres
--

COMMENT ON TABLE edan.edan_pecuaria IS 'Sección 9.2 - Daños y necesidades pecuarias';


--
-- Name: edan_pecuaria_id_pecuaria_seq; Type: SEQUENCE; Schema: edan; Owner: postgres
--

CREATE SEQUENCE edan.edan_pecuaria_id_pecuaria_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE edan.edan_pecuaria_id_pecuaria_seq OWNER TO postgres;

--
-- Name: edan_pecuaria_id_pecuaria_seq; Type: SEQUENCE OWNED BY; Schema: edan; Owner: postgres
--

ALTER SEQUENCE edan.edan_pecuaria_id_pecuaria_seq OWNED BY edan.edan_pecuaria.id_pecuaria;


--
-- Name: edan_poblacion_grupo; Type: TABLE; Schema: edan; Owner: postgres
--

CREATE TABLE edan.edan_poblacion_grupo (
    id_poblacion_grupo integer NOT NULL,
    id_edan bigint NOT NULL,
    id_grupo_etario integer NOT NULL,
    fallecidos integer DEFAULT 0,
    heridos integer DEFAULT 0,
    desaparecidos integer DEFAULT 0,
    observaciones text
);


ALTER TABLE edan.edan_poblacion_grupo OWNER TO postgres;

--
-- Name: TABLE edan_poblacion_grupo; Type: COMMENT; Schema: edan; Owner: postgres
--

COMMENT ON TABLE edan.edan_poblacion_grupo IS 'Sección 2 - Población por grupo etario';


--
-- Name: edan_poblacion_grupo_id_poblacion_grupo_seq; Type: SEQUENCE; Schema: edan; Owner: postgres
--

CREATE SEQUENCE edan.edan_poblacion_grupo_id_poblacion_grupo_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE edan.edan_poblacion_grupo_id_poblacion_grupo_seq OWNER TO postgres;

--
-- Name: edan_poblacion_grupo_id_poblacion_grupo_seq; Type: SEQUENCE OWNED BY; Schema: edan; Owner: postgres
--

ALTER SEQUENCE edan.edan_poblacion_grupo_id_poblacion_grupo_seq OWNED BY edan.edan_poblacion_grupo.id_poblacion_grupo;


--
-- Name: edan_primera_respuesta; Type: TABLE; Schema: edan; Owner: postgres
--

CREATE TABLE edan.edan_primera_respuesta (
    id_primera_respuesta integer NOT NULL,
    id_edan bigint NOT NULL,
    busqueda_requerimiento boolean DEFAULT false,
    busqueda_observaciones text,
    salvamento_requerimiento boolean DEFAULT false,
    salvamento_observaciones text,
    evacuacion_requerimiento boolean DEFAULT false,
    evacuacion_observaciones text,
    otros_requerimiento boolean DEFAULT false,
    otros_observaciones text,
    observaciones_generales text
);


ALTER TABLE edan.edan_primera_respuesta OWNER TO postgres;

--
-- Name: TABLE edan_primera_respuesta; Type: COMMENT; Schema: edan; Owner: postgres
--

COMMENT ON TABLE edan.edan_primera_respuesta IS 'Sección 3.3 - Necesidades en primera respuesta';


--
-- Name: edan_primera_respuesta_id_primera_respuesta_seq; Type: SEQUENCE; Schema: edan; Owner: postgres
--

CREATE SEQUENCE edan.edan_primera_respuesta_id_primera_respuesta_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE edan.edan_primera_respuesta_id_primera_respuesta_seq OWNER TO postgres;

--
-- Name: edan_primera_respuesta_id_primera_respuesta_seq; Type: SEQUENCE OWNED BY; Schema: edan; Owner: postgres
--

ALTER SEQUENCE edan.edan_primera_respuesta_id_primera_respuesta_seq OWNED BY edan.edan_primera_respuesta.id_primera_respuesta;


--
-- Name: edan_proteccion; Type: TABLE; Schema: edan; Owner: postgres
--

CREATE TABLE edan.edan_proteccion (
    id_proteccion integer NOT NULL,
    id_edan bigint NOT NULL,
    id_categoria_proteccion integer NOT NULL,
    mujeres integer DEFAULT 0,
    hombres integer DEFAULT 0,
    total integer DEFAULT 0,
    apoyo_psicosocial boolean DEFAULT false,
    reposicion_documentos boolean DEFAULT false,
    observaciones text
);


ALTER TABLE edan.edan_proteccion OWNER TO postgres;

--
-- Name: TABLE edan_proteccion; Type: COMMENT; Schema: edan; Owner: postgres
--

COMMENT ON TABLE edan.edan_proteccion IS 'Sección 10 - Necesidades de protección';


--
-- Name: edan_proteccion_id_proteccion_seq; Type: SEQUENCE; Schema: edan; Owner: postgres
--

CREATE SEQUENCE edan.edan_proteccion_id_proteccion_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE edan.edan_proteccion_id_proteccion_seq OWNER TO postgres;

--
-- Name: edan_proteccion_id_proteccion_seq; Type: SEQUENCE OWNED BY; Schema: edan; Owner: postgres
--

ALTER SEQUENCE edan.edan_proteccion_id_proteccion_seq OWNED BY edan.edan_proteccion.id_proteccion;


--
-- Name: edan_salud_establecimiento; Type: TABLE; Schema: edan; Owner: postgres
--

CREATE TABLE edan.edan_salud_establecimiento (
    id_salud_establecimiento integer NOT NULL,
    id_edan bigint NOT NULL,
    nombre_establecimiento character varying(200) NOT NULL,
    localidad_comunidad character varying(200),
    nivel_atencion smallint,
    dano_parcial boolean DEFAULT false,
    dano_total boolean DEFAULT false,
    personal_medicos integer DEFAULT 0,
    personal_enfermeras integer DEFAULT 0,
    personal_otros integer DEFAULT 0,
    observaciones text,
    CONSTRAINT edan_salud_establecimiento_nivel_atencion_check CHECK ((nivel_atencion = ANY (ARRAY[1, 2, 3])))
);


ALTER TABLE edan.edan_salud_establecimiento OWNER TO postgres;

--
-- Name: TABLE edan_salud_establecimiento; Type: COMMENT; Schema: edan; Owner: postgres
--

COMMENT ON TABLE edan.edan_salud_establecimiento IS 'Sección 4.1 - Daños en servicios de salud';


--
-- Name: edan_salud_establecimiento_id_salud_establecimiento_seq; Type: SEQUENCE; Schema: edan; Owner: postgres
--

CREATE SEQUENCE edan.edan_salud_establecimiento_id_salud_establecimiento_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE edan.edan_salud_establecimiento_id_salud_establecimiento_seq OWNER TO postgres;

--
-- Name: edan_salud_establecimiento_id_salud_establecimiento_seq; Type: SEQUENCE OWNED BY; Schema: edan; Owner: postgres
--

ALTER SEQUENCE edan.edan_salud_establecimiento_id_salud_establecimiento_seq OWNED BY edan.edan_salud_establecimiento.id_salud_establecimiento;


--
-- Name: edan_salud_necesidades; Type: TABLE; Schema: edan; Owner: postgres
--

CREATE TABLE edan.edan_salud_necesidades (
    id_salud_necesidad integer NOT NULL,
    id_edan bigint NOT NULL,
    botiquin_personas integer DEFAULT 0,
    otras_necesidades text,
    observaciones text
);


ALTER TABLE edan.edan_salud_necesidades OWNER TO postgres;

--
-- Name: TABLE edan_salud_necesidades; Type: COMMENT; Schema: edan; Owner: postgres
--

COMMENT ON TABLE edan.edan_salud_necesidades IS 'Sección 4.2 - Necesidades en salud';


--
-- Name: edan_salud_necesidades_id_salud_necesidad_seq; Type: SEQUENCE; Schema: edan; Owner: postgres
--

CREATE SEQUENCE edan.edan_salud_necesidades_id_salud_necesidad_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE edan.edan_salud_necesidades_id_salud_necesidad_seq OWNER TO postgres;

--
-- Name: edan_salud_necesidades_id_salud_necesidad_seq; Type: SEQUENCE OWNED BY; Schema: edan; Owner: postgres
--

ALTER SEQUENCE edan.edan_salud_necesidades_id_salud_necesidad_seq OWNED BY edan.edan_salud_necesidades.id_salud_necesidad;


--
-- Name: edan_servicio_basico; Type: TABLE; Schema: edan; Owner: postgres
--

CREATE TABLE edan.edan_servicio_basico (
    id_servicio_basico_edan integer NOT NULL,
    id_edan bigint NOT NULL,
    id_servicio_basico integer NOT NULL,
    dano_parcial boolean DEFAULT false,
    dano_total boolean DEFAULT false,
    necesidades_inmediatas text,
    observaciones text
);


ALTER TABLE edan.edan_servicio_basico OWNER TO postgres;

--
-- Name: TABLE edan_servicio_basico; Type: COMMENT; Schema: edan; Owner: postgres
--

COMMENT ON TABLE edan.edan_servicio_basico IS 'Sección 6 - Daño en servicios básicos';


--
-- Name: edan_servicio_basico_id_servicio_basico_edan_seq; Type: SEQUENCE; Schema: edan; Owner: postgres
--

CREATE SEQUENCE edan.edan_servicio_basico_id_servicio_basico_edan_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE edan.edan_servicio_basico_id_servicio_basico_edan_seq OWNER TO postgres;

--
-- Name: edan_servicio_basico_id_servicio_basico_edan_seq; Type: SEQUENCE OWNED BY; Schema: edan; Owner: postgres
--

ALTER SEQUENCE edan.edan_servicio_basico_id_servicio_basico_edan_seq OWNED BY edan.edan_servicio_basico.id_servicio_basico_edan;


--
-- Name: edan_tipo_evento; Type: TABLE; Schema: edan; Owner: postgres
--

CREATE TABLE edan.edan_tipo_evento (
    id_tipo_evento_edan integer NOT NULL,
    id_edan bigint NOT NULL,
    id_tipo_evento integer NOT NULL
);


ALTER TABLE edan.edan_tipo_evento OWNER TO postgres;

--
-- Name: TABLE edan_tipo_evento; Type: COMMENT; Schema: edan; Owner: postgres
--

COMMENT ON TABLE edan.edan_tipo_evento IS 'Sección 3.1 - Tipo de evento adverso (puente)';


--
-- Name: edan_tipo_evento_id_tipo_evento_edan_seq; Type: SEQUENCE; Schema: edan; Owner: postgres
--

CREATE SEQUENCE edan.edan_tipo_evento_id_tipo_evento_edan_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE edan.edan_tipo_evento_id_tipo_evento_edan_seq OWNER TO postgres;

--
-- Name: edan_tipo_evento_id_tipo_evento_edan_seq; Type: SEQUENCE OWNED BY; Schema: edan; Owner: postgres
--

ALTER SEQUENCE edan.edan_tipo_evento_id_tipo_evento_edan_seq OWNED BY edan.edan_tipo_evento.id_tipo_evento_edan;


--
-- Name: edan_vivienda; Type: TABLE; Schema: edan; Owner: postgres
--

CREATE TABLE edan.edan_vivienda (
    id_vivienda integer NOT NULL,
    id_edan bigint NOT NULL,
    comunidad character varying(200),
    viviendas_dano_parcial integer DEFAULT 0,
    viviendas_dano_total integer DEFAULT 0,
    necesidades_inmediatas text,
    observaciones text
);


ALTER TABLE edan.edan_vivienda OWNER TO postgres;

--
-- Name: TABLE edan_vivienda; Type: COMMENT; Schema: edan; Owner: postgres
--

COMMENT ON TABLE edan.edan_vivienda IS 'Sección 8 - Daños en vivienda';


--
-- Name: edan_vivienda_id_vivienda_seq; Type: SEQUENCE; Schema: edan; Owner: postgres
--

CREATE SEQUENCE edan.edan_vivienda_id_vivienda_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE edan.edan_vivienda_id_vivienda_seq OWNER TO postgres;

--
-- Name: edan_vivienda_id_vivienda_seq; Type: SEQUENCE OWNED BY; Schema: edan; Owner: postgres
--

ALTER SEQUENCE edan.edan_vivienda_id_vivienda_seq OWNED BY edan.edan_vivienda.id_vivienda;


--
-- Name: cultivo; Type: TABLE; Schema: shared; Owner: sinagersat
--

CREATE TABLE shared.cultivo (
    id integer NOT NULL,
    nombre text NOT NULL,
    grupo text NOT NULL,
    CONSTRAINT chk_cultivo_grupo CHECK ((grupo = ANY (ARRAY['Cereales'::text, 'Estimulantes'::text, 'Frutales'::text, 'Hortalizas'::text, 'Industriales'::text, 'Tuberculos'::text, 'Forrajes'::text])))
);


ALTER TABLE shared.cultivo OWNER TO sinagersat;

--
-- Name: departamento; Type: TABLE; Schema: shared; Owner: postgres
--

CREATE TABLE shared.departamento (
    id integer NOT NULL,
    codigo_ine character varying(2) NOT NULL,
    nombre character varying(100) NOT NULL
);


ALTER TABLE shared.departamento OWNER TO postgres;

--
-- Name: TABLE departamento; Type: COMMENT; Schema: shared; Owner: postgres
--

COMMENT ON TABLE shared.departamento IS 'Catálogo de 9 departamentos de Bolivia (PK: id INTEGER, UNIQUE: codigo_ine)';


--
-- Name: municipio; Type: TABLE; Schema: shared; Owner: postgres
--

CREATE TABLE shared.municipio (
    id integer NOT NULL,
    codigo_ine character varying(6) NOT NULL,
    id_departamento integer NOT NULL,
    id_provincia integer NOT NULL,
    nombre character varying(100) NOT NULL
);


ALTER TABLE shared.municipio OWNER TO postgres;

--
-- Name: TABLE municipio; Type: COMMENT; Schema: shared; Owner: postgres
--

COMMENT ON TABLE shared.municipio IS 'Catálogo de municipios por provincia (PK: id INTEGER, UNIQUE: codigo_ine)';


--
-- Name: pecuario; Type: TABLE; Schema: shared; Owner: sinagersat
--

CREATE TABLE shared.pecuario (
    id integer NOT NULL,
    nombre text NOT NULL,
    grupo text NOT NULL,
    CONSTRAINT chk_pecuario_grupo CHECK ((grupo = ANY (ARRAY['Ganado mayor'::text, 'Ganado menor'::text, 'Camélidos'::text, 'Aves de corral'::text, 'Piscicultura'::text, 'Otros'::text])))
);


ALTER TABLE shared.pecuario OWNER TO sinagersat;

--
-- Name: provincia; Type: TABLE; Schema: shared; Owner: postgres
--

CREATE TABLE shared.provincia (
    id integer NOT NULL,
    codigo_ine character varying(4) NOT NULL,
    id_departamento integer NOT NULL,
    nombre character varying(100) NOT NULL
);


ALTER TABLE shared.provincia OWNER TO postgres;

--
-- Name: TABLE provincia; Type: COMMENT; Schema: shared; Owner: postgres
--

COMMENT ON TABLE shared.provincia IS 'Catálogo de provincias por departamento (PK: id INTEGER, UNIQUE: codigo_ine)';


--
-- Name: ayuda_humanitaria id_ayuda_humanitaria; Type: DEFAULT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.ayuda_humanitaria ALTER COLUMN id_ayuda_humanitaria SET DEFAULT nextval('edan.catalogo_ayuda_humanitaria_id_ayuda_humanitaria_seq'::regclass);


--
-- Name: categoria_proteccion id_categoria_proteccion; Type: DEFAULT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.categoria_proteccion ALTER COLUMN id_categoria_proteccion SET DEFAULT nextval('edan.catalogo_categoria_proteccion_id_categoria_proteccion_seq'::regclass);


--
-- Name: edan id_edan; Type: DEFAULT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan ALTER COLUMN id_edan SET DEFAULT nextval('edan.edan_id_edan_seq'::regclass);


--
-- Name: edan_agricultura id_agricultura; Type: DEFAULT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_agricultura ALTER COLUMN id_agricultura SET DEFAULT nextval('edan.edan_agricultura_id_agricultura_seq'::regclass);


--
-- Name: edan_ayuda_humanitaria id_ayuda_edan; Type: DEFAULT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_ayuda_humanitaria ALTER COLUMN id_ayuda_edan SET DEFAULT nextval('edan.edan_ayuda_humanitaria_id_ayuda_edan_seq'::regclass);


--
-- Name: edan_comunidad id_comunidad; Type: DEFAULT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_comunidad ALTER COLUMN id_comunidad SET DEFAULT nextval('edan.edan_comunidad_id_comunidad_seq'::regclass);


--
-- Name: edan_educacion_afectacion id_educacion_afectacion; Type: DEFAULT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_educacion_afectacion ALTER COLUMN id_educacion_afectacion SET DEFAULT nextval('edan.edan_educacion_afectacion_id_educacion_afectacion_seq'::regclass);


--
-- Name: edan_educacion_dano id_educacion_dano; Type: DEFAULT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_educacion_dano ALTER COLUMN id_educacion_dano SET DEFAULT nextval('edan.edan_educacion_dano_id_educacion_dano_seq'::regclass);


--
-- Name: edan_infraestructura_productiva id_infra_productiva; Type: DEFAULT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_infraestructura_productiva ALTER COLUMN id_infra_productiva SET DEFAULT nextval('edan.edan_infraestructura_productiva_id_infra_productiva_seq'::regclass);


--
-- Name: edan_infraestructura_publica id_infraestructura_publica; Type: DEFAULT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_infraestructura_publica ALTER COLUMN id_infraestructura_publica SET DEFAULT nextval('edan.edan_infraestructura_publica_id_infraestructura_publica_seq'::regclass);


--
-- Name: edan_infraestructura_vial id_infraestructura_vial; Type: DEFAULT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_infraestructura_vial ALTER COLUMN id_infraestructura_vial SET DEFAULT nextval('edan.edan_infraestructura_vial_id_infraestructura_vial_seq'::regclass);


--
-- Name: edan_pecuaria id_pecuaria; Type: DEFAULT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_pecuaria ALTER COLUMN id_pecuaria SET DEFAULT nextval('edan.edan_pecuaria_id_pecuaria_seq'::regclass);


--
-- Name: edan_poblacion_grupo id_poblacion_grupo; Type: DEFAULT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_poblacion_grupo ALTER COLUMN id_poblacion_grupo SET DEFAULT nextval('edan.edan_poblacion_grupo_id_poblacion_grupo_seq'::regclass);


--
-- Name: edan_primera_respuesta id_primera_respuesta; Type: DEFAULT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_primera_respuesta ALTER COLUMN id_primera_respuesta SET DEFAULT nextval('edan.edan_primera_respuesta_id_primera_respuesta_seq'::regclass);


--
-- Name: edan_proteccion id_proteccion; Type: DEFAULT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_proteccion ALTER COLUMN id_proteccion SET DEFAULT nextval('edan.edan_proteccion_id_proteccion_seq'::regclass);


--
-- Name: edan_salud_establecimiento id_salud_establecimiento; Type: DEFAULT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_salud_establecimiento ALTER COLUMN id_salud_establecimiento SET DEFAULT nextval('edan.edan_salud_establecimiento_id_salud_establecimiento_seq'::regclass);


--
-- Name: edan_salud_necesidades id_salud_necesidad; Type: DEFAULT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_salud_necesidades ALTER COLUMN id_salud_necesidad SET DEFAULT nextval('edan.edan_salud_necesidades_id_salud_necesidad_seq'::regclass);


--
-- Name: edan_servicio_basico id_servicio_basico_edan; Type: DEFAULT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_servicio_basico ALTER COLUMN id_servicio_basico_edan SET DEFAULT nextval('edan.edan_servicio_basico_id_servicio_basico_edan_seq'::regclass);


--
-- Name: edan_tipo_evento id_tipo_evento_edan; Type: DEFAULT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_tipo_evento ALTER COLUMN id_tipo_evento_edan SET DEFAULT nextval('edan.edan_tipo_evento_id_tipo_evento_edan_seq'::regclass);


--
-- Name: edan_vivienda id_vivienda; Type: DEFAULT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_vivienda ALTER COLUMN id_vivienda SET DEFAULT nextval('edan.edan_vivienda_id_vivienda_seq'::regclass);


--
-- Name: grupo_etario id_grupo_etario; Type: DEFAULT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.grupo_etario ALTER COLUMN id_grupo_etario SET DEFAULT nextval('edan.catalogo_grupo_etario_id_grupo_etario_seq'::regclass);


--
-- Name: servicio_basico id_servicio_basico; Type: DEFAULT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.servicio_basico ALTER COLUMN id_servicio_basico SET DEFAULT nextval('edan.catalogo_servicio_basico_id_servicio_basico_seq'::regclass);


--
-- Name: tipo_evento id_tipo_evento; Type: DEFAULT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.tipo_evento ALTER COLUMN id_tipo_evento SET DEFAULT nextval('edan.catalogo_tipo_evento_id_tipo_evento_seq'::regclass);


--
-- Data for Name: ayuda_humanitaria; Type: TABLE DATA; Schema: edan; Owner: postgres
--

COPY edan.ayuda_humanitaria (id_ayuda_humanitaria, nombre, orden) FROM stdin;
1	Alimentos	1
2	Prendas de Vestir	2
3	Refugio y Vivienda	3
4	Herramientas y Accesorios	4
5	Ropa de Cama	5
6	Almacenamiento de Agua	6
7	Artículos de Higiene	7
8	Baños	8
9	Artículos de Cocina	9
\.


--
-- Data for Name: categoria_proteccion; Type: TABLE DATA; Schema: edan; Owner: postgres
--

COPY edan.categoria_proteccion (id_categoria_proteccion, nombre, orden) FROM stdin;
1	Niñas y Niños	1
2	Adolescentes	2
3	Mujeres Lactantes	3
4	Mujeres Embarazadas	4
5	Adultos Mayores	5
6	Personas con Discapacidad	6
7	Personas con Enfermedad Inhabilitante	7
\.


--
-- Data for Name: edan; Type: TABLE DATA; Schema: edan; Owner: postgres
--

COPY edan.edan (id_edan, codigo_edan, id_departamento, id_municipio, nombre_alcalde, telefono_alcalde, fecha_llenado, fecha_evento, hora_evento, localidades_afectadas, total_poblacion_afectada, total_familias_afectadas, total_familias_damnificadas, nombre_responsable, cargo_responsable, telefono_responsable, email_responsable, usuario_registro, fecha_registro, fecha_actualizacion, id_reporte_rea, fotografia) FROM stdin;
1	EDAN-TEST-001	2	20101	Test Alcalde	70000000	2026-07-20	2026-07-20	\N	5	1000	0	0	Test Responsable	Director	71111111	test@test.com	\N	2026-07-20 14:31:34.271587	2026-07-20 14:31:34.271587	\N	/uploads/reports/general/upload_1784572294_0739aaa1.png
\.


--
-- Data for Name: edan_agricultura; Type: TABLE DATA; Schema: edan; Owner: postgres
--

COPY edan.edan_agricultura (id_agricultura, id_edan, tipo_cultivo, hectareas_afectadas, hectareas_perdidas, necesidades_inmediatas, observaciones) FROM stdin;
\.


--
-- Data for Name: edan_ayuda_humanitaria; Type: TABLE DATA; Schema: edan; Owner: postgres
--

COPY edan.edan_ayuda_humanitaria (id_ayuda_edan, id_edan, id_ayuda_humanitaria, requiere, observaciones) FROM stdin;
\.


--
-- Data for Name: edan_comunidad; Type: TABLE DATA; Schema: edan; Owner: postgres
--

COPY edan.edan_comunidad (id_comunidad, id_edan, nombre_comunidad) FROM stdin;
\.


--
-- Data for Name: edan_educacion_afectacion; Type: TABLE DATA; Schema: edan; Owner: postgres
--

COPY edan.edan_educacion_afectacion (id_educacion_afectacion, id_edan, id_educacion_dano, nombre_establecimiento, estudiantes_afectados, profesores_afectados, administrativos_afectados, total_afectados, observaciones) FROM stdin;
\.


--
-- Data for Name: edan_educacion_dano; Type: TABLE DATA; Schema: edan; Owner: postgres
--

COPY edan.edan_educacion_dano (id_educacion_dano, id_edan, nombre_establecimiento, comunidad, dano_parcial, dano_total, suspension_clases, perdida_material, funciona_albergue, observaciones) FROM stdin;
\.


--
-- Data for Name: edan_infraestructura_productiva; Type: TABLE DATA; Schema: edan; Owner: postgres
--

COPY edan.edan_infraestructura_productiva (id_infra_productiva, id_edan, tipo, dano_parcial, dano_total, observaciones) FROM stdin;
\.


--
-- Data for Name: edan_infraestructura_publica; Type: TABLE DATA; Schema: edan; Owner: postgres
--

COPY edan.edan_infraestructura_publica (id_infraestructura_publica, id_edan, localidad_comunidad, tipo_estructura, dano_parcial, dano_total, observaciones) FROM stdin;
\.


--
-- Data for Name: edan_infraestructura_vial; Type: TABLE DATA; Schema: edan; Owner: postgres
--

COPY edan.edan_infraestructura_vial (id_infraestructura_vial, id_edan, via_acceso_puentes, tramo, localidad_origen, localidad_destino, dano_parcial_km, dano_total_km, necesidades_inmediatas, observaciones) FROM stdin;
\.


--
-- Data for Name: edan_pecuaria; Type: TABLE DATA; Schema: edan; Owner: postgres
--

COPY edan.edan_pecuaria (id_pecuaria, id_edan, tipo_especie, raza, animales_afectados, animales_muertos, necesidades_inmediatas, observaciones) FROM stdin;
\.


--
-- Data for Name: edan_poblacion_grupo; Type: TABLE DATA; Schema: edan; Owner: postgres
--

COPY edan.edan_poblacion_grupo (id_poblacion_grupo, id_edan, id_grupo_etario, fallecidos, heridos, desaparecidos, observaciones) FROM stdin;
\.


--
-- Data for Name: edan_primera_respuesta; Type: TABLE DATA; Schema: edan; Owner: postgres
--

COPY edan.edan_primera_respuesta (id_primera_respuesta, id_edan, busqueda_requerimiento, busqueda_observaciones, salvamento_requerimiento, salvamento_observaciones, evacuacion_requerimiento, evacuacion_observaciones, otros_requerimiento, otros_observaciones, observaciones_generales) FROM stdin;
\.


--
-- Data for Name: edan_proteccion; Type: TABLE DATA; Schema: edan; Owner: postgres
--

COPY edan.edan_proteccion (id_proteccion, id_edan, id_categoria_proteccion, mujeres, hombres, total, apoyo_psicosocial, reposicion_documentos, observaciones) FROM stdin;
\.


--
-- Data for Name: edan_salud_establecimiento; Type: TABLE DATA; Schema: edan; Owner: postgres
--

COPY edan.edan_salud_establecimiento (id_salud_establecimiento, id_edan, nombre_establecimiento, localidad_comunidad, nivel_atencion, dano_parcial, dano_total, personal_medicos, personal_enfermeras, personal_otros, observaciones) FROM stdin;
\.


--
-- Data for Name: edan_salud_necesidades; Type: TABLE DATA; Schema: edan; Owner: postgres
--

COPY edan.edan_salud_necesidades (id_salud_necesidad, id_edan, botiquin_personas, otras_necesidades, observaciones) FROM stdin;
\.


--
-- Data for Name: edan_servicio_basico; Type: TABLE DATA; Schema: edan; Owner: postgres
--

COPY edan.edan_servicio_basico (id_servicio_basico_edan, id_edan, id_servicio_basico, dano_parcial, dano_total, necesidades_inmediatas, observaciones) FROM stdin;
\.


--
-- Data for Name: edan_tipo_evento; Type: TABLE DATA; Schema: edan; Owner: postgres
--

COPY edan.edan_tipo_evento (id_tipo_evento_edan, id_edan, id_tipo_evento) FROM stdin;
\.


--
-- Data for Name: edan_vivienda; Type: TABLE DATA; Schema: edan; Owner: postgres
--

COPY edan.edan_vivienda (id_vivienda, id_edan, comunidad, viviendas_dano_parcial, viviendas_dano_total, necesidades_inmediatas, observaciones) FROM stdin;
\.


--
-- Data for Name: grupo_etario; Type: TABLE DATA; Schema: edan; Owner: postgres
--

COPY edan.grupo_etario (id_grupo_etario, nombre, orden) FROM stdin;
1	Niño(a) 0-5 años	1
2	Escolar 6-18 años	2
3	Adulto 19-60 años	3
4	Adulto mayor 60+ años	4
\.


--
-- Data for Name: servicio_basico; Type: TABLE DATA; Schema: edan; Owner: postgres
--

COPY edan.servicio_basico (id_servicio_basico, nombre, orden) FROM stdin;
1	Luz eléctrica	1
2	Agua Potable	2
3	Alcantarillado	3
4	Gas domiciliario	4
5	Telecomunicaciones	5
\.


--
-- Data for Name: tipo_evento; Type: TABLE DATA; Schema: edan; Owner: postgres
--

COPY edan.tipo_evento (id_tipo_evento, nombre) FROM stdin;
1	Inundación
2	Riada
3	Deslizamiento
4	Helada
5	Granizada
6	Sequía
7	Incendios
8	Otros
\.


--
-- Data for Name: cultivo; Type: TABLE DATA; Schema: shared; Owner: sinagersat
--

COPY shared.cultivo (id, nombre, grupo) FROM stdin;
1	Arroz con cáscara	Cereales
2	Avena	Cereales
3	Cañahua	Cereales
4	Cebada en grano	Cereales
5	Centeno	Cereales
6	Maiz en grano	Cereales
7	Quínua	Cereales
8	Sorgo en grano	Cereales
9	Trigo	Cereales
10	Cacao	Estimulantes
11	Café	Estimulantes
12	Té	Estimulantes
13	Banano	Frutales
14	Ciruelo	Frutales
15	Chirimoya	Frutales
16	Durazno	Frutales
17	Frutilla	Frutales
18	Guinda	Frutales
19	Higo	Frutales
20	Lima	Frutales
21	Limón	Frutales
22	Mandarina	Frutales
23	Manga	Frutales
24	Manzana	Frutales
25	Membrillo	Frutales
26	Naranja	Frutales
27	Palta	Frutales
28	Papaya	Frutales
29	Pera	Frutales
30	Piña	Frutales
31	Plátano(Postre)	Frutales
32	Pomelo/toronja	Frutales
33	Sandia	Frutales
34	Tuna	Frutales
35	Uva (Vid)	Frutales
36	Aji	Hortalizas
37	Ajo	Hortalizas
38	Arveja	Hortalizas
39	Betarraga	Hortalizas
40	Cebolla	Hortalizas
41	Coliflor	Hortalizas
42	Frejol/poroto	Hortalizas
43	Garbanzo	Hortalizas
44	Haba	Hortalizas
45	Lechuga	Hortalizas
46	Locoto	Hortalizas
47	Maíz choclo	Hortalizas
48	Pepino	Hortalizas
49	Rábano	Hortalizas
50	Repollo	Hortalizas
51	Tomate	Hortalizas
52	Vainitas	Hortalizas
53	Zanahoria	Hortalizas
54	Zapallo	Hortalizas
55	Achiote (urucu)	Industriales
56	Algodón	Industriales
57	Caña de Azúcar	Industriales
58	Girasol	Industriales
59	Mani	Industriales
60	Sésamo	Industriales
61	Soya	Industriales
62	Tabaco	Industriales
73	Chia	Industriales
63	Camote	Tuberculos
64	Hualuza	Tuberculos
65	Oca	Tuberculos
66	Papa	Tuberculos
67	Papaliza	Tuberculos
68	Racacha	Tuberculos
69	Yuca	Tuberculos
70	Alfalfa	Forrajes
71	Avena berza	Forrajes
72	Cebada berza	Forrajes
\.


--
-- Data for Name: departamento; Type: TABLE DATA; Schema: shared; Owner: postgres
--

COPY shared.departamento (id, codigo_ine, nombre) FROM stdin;
1	01	Chuquisaca
2	02	La Paz
3	03	Cochabamba
4	04	Oruro
5	05	Potosí
6	06	Tarija
7	07	Santa Cruz
8	08	Beni
\.


--
-- Data for Name: municipio; Type: TABLE DATA; Schema: shared; Owner: postgres
--

COPY shared.municipio (id, codigo_ine, id_departamento, id_provincia, nombre) FROM stdin;
10904	010304	1	109	Icla
20302	020302	2	203	Caquiaviri
10801	010801	1	108	Villa Serrano
21105	021105	2	211	La Asunta
21303	021303	2	213	Ayo Ayo
11002	011002	1	110	Huacaya
22001	022001	2	220	Caranavi
90401	090401	9	904	Santa Rosa del Abuná
30601	030901	3	306	Quillacollo
71706	070706	7	717	Camiri
70904	070904	7	709	Quirusillas
90201	090201	9	902	Puerto Rico
70403	070403	7	704	Villa Yapacaní
80202	080202	8	802	Guayaramerín
80301	080301	8	803	Reyes
71106	071106	7	711	Cuatro Cañadas
80802	080802	8	808	Baures
71201	070801	7	712	Vallegrande
80803	080803	8	808	Huacaraje
90302	090302	9	903	San Lorenzo
71102	071102	7	711	San Javier
80501	080501	8	805	San Ignacio de Moxos
70701	071401	7	707	Puerto Suárez
80601	080601	8	806	Loreto
70703	071403	7	707	El Carmen Rivero Tórrez
80602	080602	8	806	San Andrés
71701	070701	7	717	Lagunillas
70502	070502	7	705	Pailón
80102	080102	8	801	San Javier
71004	071004	7	710	Fernández Alonso
90102	090102	9	901	Porvenir
70901	070901	7	709	Samaipata
80702	080702	8	807	San Ramón
71704	070704	7	717	Cuevo
90103	090103	9	901	Bolpebra
71601	070601	7	716	Portachuelo
30605	030905	3	306	Colcapirhua
50501	050401	5	505	Colquechaca
51302	050902	5	513	San Pedro de Quemes
21307	021307	2	213	Collana
40701	040801	4	407	Salinas de Garci Mendoza
51502	051202	5	515	Tomave
11003	011003	1	110	Macharetí
20102	020102	2	201	Palca
20901	020901	2	209	Luribay
21003	021003	2	210	Cajuata
21204	021204	2	212	Puerto Pérez
20404	020404	2	204	Humanata
21104	021104	2	211	Palos Blancos
41403	041503	4	414	Carangas
30201	031001	3	302	Sacaba
41001	040501	4	410	Huachacalla
31001	030501	3	310	Arani
60402	060502	6	604	El Puente
41602	040202	4	416	Santuario de Quillacas
30304	031204	3	303	Chimoré
31603	030303	3	316	Cocapata
21304	021304	2	213	Calamarca
20306	020306	2	203	Waldo Ballivián
20401	020401	2	204	Puerto Acosta
31302	030802	3	313	Toco
41004	040504	4	410	Yunguyo de Litoral
31602	030302	3	316	Morochata
60301	060301	6	603	Yacuiba
50502	050402	5	505	Ravelo
30602	030902	3	306	Sipe Sipe
10501	010601	1	105	Tarabuco
10602	010702	1	106	San Lucas
10901	010301	1	109	Villa Zudáñez
21801	021801	2	218	San Pedro de Curahuara
20502	020502	2	205	Ayata
21901	021901	2	219	Santiago de Machaca
30202	031002	3	302	Colomi
21001	021001	2	210	Inquisivi
20604	020604	2	206	Quiabaya
20804	020804	2	208	Desaguadero
30604	030904	3	306	Vinto
50102	050102	5	501	Tinguipaya
51702	051302	5	517	Acasio
30401	031301	3	304	Mizque
20304	020304	2	203	Comanche
10701	010901	1	107	Villa Abecia
20902	020902	2	209	Sapahaqui
71603	070603	7	716	Colpa Bélgica
40702	040802	4	407	Pampa Aullagas
20105	020105	2	201	El Alto
21305	021305	2	213	Patacamaya
51401	051401	5	514	Llica
21602	021602	2	216	Curva
41301	041001	4	413	Toledo
21703	021703	2	217	Tito Yupanqui
20802	020802	2	208	Guaqui
50203	050203	5	502	Llallagua
80101	080101	8	801	Trinidad
10401	010501	1	104	Monteagudo
41402	041502	4	414	Todos Santos
20405	020405	2	204	Escoma
40601	041301	4	406	Totora
20402	020402	2	204	Mocomoco
50103	050103	5	501	Yocalla
60101	060101	6	601	Tarija
21101	021101	2	211	Chulumani
50202	050202	5	502	Chayanta
40901	041201	4	409	Santiago de Andamarca
20903	020903	2	209	Yaco
10301	010401	1	103	Padilla
40902	041202	4	409	Belén de Andamarca
70103	070103	7	701	Porongo
21002	021002	2	210	Quime
40103	040103	4	401	El Choro
40403	040603	4	404	Antequera
40502	040402	4	405	Turco
51102	050802	5	511	Atocha
20103	020103	2	201	Mecapaca
31203	030703	3	312	Sicaya
90303	090303	9	903	Sena
30505	031405	3	305	Cuchumuela
51402	051402	5	514	Tahua
20205	020205	2	202	Santiago de Huata
71702	070702	7	717	Charagua
30603	030903	3	306	Tiquipaya
40202	040902	4	402	Coipasa
60202	060202	6	602	Bermejo
21005	021005	2	210	Ichoca
31503	030203	3	315	Omereque
30701	031101	3	307	Tapacarí
31303	030803	3	313	Tolata
10604	010704	1	106	Villa Charcas
30203	031003	3	302	Villa Tunari
40102	040102	4	401	Caracollo
90503	090503	9	905	Santos Mercado
71101	071101	7	711	Concepción
90402	090402	9	904	Ingavi
21202	021202	2	212	Laja
50301	050301	5	503	Betanzos
30306	031206	3	303	Entre Ríos
21401	021401	2	214	Coroico
50903	051103	5	509	Ckochas
21802	021802	2	218	Papel Pampa
30101	030101	3	301	Cochabamba
30302	031202	3	303	Pojo
20602	020602	2	206	Guanay
10201	010201	1	102	Azurduy
70201	070201	7	702	Warnes
51203	051003	5	512	San Antonio de Esmoruco
40203	040903	4	402	Chipaya
20403	020403	2	204	Puerto Carabuco
20104	020104	2	201	Achocalla
31002	030502	3	310	Vacas
30303	031203	3	303	Pocona
20203	020203	2	202	Chua Cocani
40104	040104	4	401	Paria
51701	051301	5	517	Arampampa
20608	020608	2	206	Teoponte
20806	020806	2	208	Jesús de Machaca
40801	041401	4	408	Santiago de Huari
41101	040701	4	411	Huanuni
10302	010402	1	103	Tomina
31401	030401	3	314	Tarata
21103	021103	2	211	Yanacachi
31403	030403	3	314	Arbieto
60501	060401	6	605	Uriondo
70102	070102	7	701	Cotoca
31402	030402	3	314	Anzaldo
60401	060501	6	604	San Lorenzo
71204	070804	7	712	Postrervalle
31102	030602	3	311	Tacopaya
21701	021701	2	217	Copacabana
41401	041501	4	414	La Rivera
20204	020204	2	202	Huarina
51101	050801	5	511	Tupiza
60303	060303	6	603	Villa Montes
50901	051101	5	509	Puna
21306	021306	2	213	Colquencha
30501	031401	3	305	Punata
70601	071201	7	706	San Matías
10703	010903	1	107	Las Carreras
21902	021902	2	219	Catacora
80401	080401	8	804	Santa Ana del Yacuma
50602	050602	5	506	Vitichi
50302	050302	5	503	Chaquí
30502	031402	3	305	Villa Rivero
11001	011001	1	110	Villa Vaca Guzmán (Muyupampa)
20206	020206	2	202	Huatajata
71703	070703	7	717	Cabezas
10202	010202	1	102	Tarvita
70202	070202	7	702	Okinawa Uno
71001	071001	7	710	Montero
50402	050502	5	504	Toro Toro
30403	031303	3	304	Alalay
70401	070401	7	704	Buena Vista
60302	060302	6	603	Caraparí
10103	010103	1	101	Poroma
51301	050901	5	513	Colcha K
80701	080701	8	807	San Joaquín
31301	030801	3	313	Cliza
10601	010701	1	106	Camargo
70702	071402	7	707	Puerto Quijarro
41501	041601	4	415	Huayllamarca
41003	040503	4	410	Cruz de Machacamarca
41201	041101	4	412	Eucaliptus
60601	060601	6	606	Entre Ríos
80801	080801	8	808	Magdalena
31601	030301	3	316	Independencia
80201	080201	8	802	Riberalta
31404	030404	3	314	Sacabamba
20201	020201	2	202	Achacachi
90101	090101	9	901	Cobija
50505	050405	5	505	San Pedro de Macha
40101	040101	4	401	Oruro
60502	060402	6	605	Yunchará
71705	070705	7	717	Gutiérrez (Kereimba Iyambae)
31502	030202	3	315	Pasorapa
70404	070404	7	704	San Juan de Yapacaní
70301	070301	7	703	San Ignacio de Velasco
71005	071005	7	710	San Pedro
40201	040901	4	402	Sabaya
10303	010403	1	103	Sopachuy
31202	030702	3	312	Santiváñez
40301	040301	4	403	Corque
50801	051601	5	508	San Agustín
50101	050101	5	501	Potosí
20301	020301	2	203	Coro Coro
70801	071301	7	708	Comarapa
10402	010502	1	104	Huacareta
51202	051002	5	512	Mojinete
20308	020308	2	203	Callapa
70903	070903	7	709	Mairana
20905	020905	2	209	Cairoma
71002	071002	7	710	General Saavedra
80303	080303	8	803	Santa Rosa
30305	031205	3	303	Puerto Villarroel
30802	031602	3	308	Shinahota
90202	090202	9	902	San Pedro
70501	070501	7	705	San José de Chiquitos
20803	020803	2	208	Tiahuanaco
90301	090301	9	903	Puerto Gonzalo Moreno
20503	020503	2	205	Aucapata
90104	090104	9	901	Bella Flor
30503	031403	3	305	San Benito
70302	070302	7	703	San Miguel de Velasco
10305	010405	1	103	El Villar
21502	021502	2	215	San Buenaventura
22002	022002	2	220	Alto Beni
30504	031404	3	305	Tacachi
80703	080703	8	807	Puerto Siles
41601	040201	4	416	Challapata
20702	020702	2	207	Pelechuco
70503	070503	7	705	Roboré
20101	020101	2	201	La Paz
10902	010302	1	109	Presto
51001	051501	5	510	Villazón
90502	090502	9	905	Villa Nueva
20805	020805	2	208	San Andrés de Machaca
10304	010404	1	103	Villa Alcalá
71707	070707	7	717	Boyuibe
71301	071501	7	713	Ascensión de Guarayos
70105	070105	7	701	El Torno
21601	021601	2	216	Charazani
30301	031201	3	303	Totora
20904	020904	2	209	Malla
70303	070303	7	703	San Rafael de Velasco
41005	040505	4	410	Esmeralda
70402	070402	7	704	San Carlos
71105	071105	7	711	San Antonio de Lomerío
21803	021803	2	218	Chacarilla
20801	020801	2	208	Viacha
51201	051001	5	512	San Pablo de Lípez
71602	070602	7	716	Santa Rosa del Sara
21102	021102	2	211	Irupana
20501	020501	2	205	Chuma
21402	021402	2	214	Coripata
50902	051102	5	509	Caiza D
21201	021201	2	212	Pucarani
71203	070803	7	712	Moro Moro
90501	090501	9	905	Nueva Esperanza
70902	070902	7	709	Pampagrande
80402	080402	8	804	Exaltación
31501	030201	3	315	Aiquile
50504	050404	5	505	Ocurí
70101	070101	7	701	Santa Cruz de la Sierra
70802	071302	7	708	Saipina
50204	050204	5	502	Chuquihuta
21004	021004	2	210	Colquiri
50702	050702	5	507	Caripuyo
71303	071503	7	713	El Puente
20601	020601	2	206	Sorata
51501	051201	5	515	Uyuni
30901	031501	3	309	Bolívar
50401	050501	5	504	San Pedro de Buena Vista
20305	020305	2	203	Charaña
30801	031601	3	308	Tiraque
50503	050403	5	505	Pocoata
20307	020307	2	203	Nazacara de Pacajes
60201	060201	6	602	Padcaya
71003	071003	7	710	Mineros
20603	020603	2	206	Tacacoma
21301	021301	2	213	Sica Sica
40501	040401	4	405	Curahuara de Carangas
70104	070104	7	701	La Guardia
40401	040601	4	404	Poopó
20606	020606	2	206	Tipuani
21302	021302	2	213	Umala
31201	030701	3	312	Capinota
10101	010101	1	101	Sucre
90203	090203	9	902	Filadelfia
41102	040702	4	411	Machacamarca
20202	020202	2	202	Ancoraimes
50104	050104	5	501	Urmiri
20701	020701	2	207	Apolo
71205	070805	7	712	Pucará
10502	010602	1	105	Yamparáez
21702	021702	2	217	San Pedro de Tiquina
20303	020303	2	203	Calacoto
10102	010102	1	101	Yotala
40302	040302	4	403	Choquecota
21203	021203	2	212	Batallas
51503	051203	5	515	Porco
50303	050303	5	503	Tacobamba
20607	020607	2	206	Mapiri
50701	050701	5	507	Sacaca
21501	021501	2	215	Ixiamas
71104	071104	7	711	San Julián
21006	021006	2	210	Licoma Pampa
10702	010902	1	107	Culpina
10903	010303	1	109	Villa Mojocoya
20605	020605	2	206	Combaya
80304	080304	8	803	Rurrenabaque
30402	031302	3	304	Vila Vila
71103	071103	7	711	San Ramón
41002	040502	4	410	Escara
71202	070802	7	712	El Trigal
20807	020807	2	208	Taraco
80302	080302	8	803	San Borja
10603	010703	1	106	Incahuasi
31101	030601	3	311	Arque
40402	040602	4	404	Pazña
50201	050201	5	502	Uncía
50601	050601	5	506	Santiago de Cotagaita
71302	071502	7	713	Urubichá
\.


--
-- Data for Name: pecuario; Type: TABLE DATA; Schema: shared; Owner: sinagersat
--

COPY shared.pecuario (id, nombre, grupo) FROM stdin;
44	Bovinos	Ganado mayor
47	Búfalos	Ganado mayor
48	Equinos	Ganado mayor
49	Mulares	Ganado mayor
50	Asnos	Ganado mayor
41	Ovinos	Ganado menor
45	Caprinos	Ganado menor
46	Porcino	Ganado menor
51	Cuyes	Ganado menor
52	Conejos	Ganado menor
42	Alpacas	Camélidos
43	Llamas	Camélidos
53	Vicuñas	Camélidos
54	Guanacos	Camélidos
55	Pollos	Aves de corral
56	Gallinas	Aves de corral
57	Patos	Aves de corral
58	Pavos	Aves de corral
59	Gansos	Aves de corral
60	Codornices	Aves de corral
61	Trucha	Piscicultura
62	Tilapia	Piscicultura
63	Pacú	Piscicultura
64	Surubí	Piscicultura
65	Sábalo	Piscicultura
66	Tambaquí	Piscicultura
67	Pejerrey	Piscicultura
68	Carpa	Piscicultura
69	Abejas (apicultura)	Otros
\.


--
-- Data for Name: provincia; Type: TABLE DATA; Schema: shared; Owner: postgres
--

COPY shared.provincia (id, codigo_ine, id_departamento, nombre) FROM stdin;
703	0703	7	José Miguel de Velasco
704	0704	7	Ichilo
101	0101	1	Oropeza
102	0102	1	Azurduy
103	0103	1	Tomina
104	0104	1	Hernando Siles
105	0105	1	Yamparáez
106	0106	1	Nor Cinti
107	0107	1	Sud Cinti
108	0108	1	Belisario Boeto
109	0109	1	Jaime Zudáñez
110	0110	1	Luis Calvo
201	0201	2	Murillo
202	0202	2	Omasuyos
203	0203	2	Pacajes
204	0204	2	Camacho
205	0205	2	Muñecas
206	0206	2	Larecaja
207	0207	2	Franz Tamayo
208	0208	2	Ingavi
209	0209	2	Loayza
210	0210	2	Inquisivi
211	0211	2	Sud Yungas
212	0212	2	Los Andes
213	0213	2	Aroma
214	0214	2	Nor Yungas
215	0215	2	Iturralde
216	0216	2	Bautista Saavedra
217	0217	2	Manco Kapac
218	0218	2	Gualberto Villarroel
219	0219	2	General José Manuel Pando
220	0220	2	Caranavi
301	0301	3	Cercado
302	0302	3	Chapare
303	0303	3	Carrasco
304	0304	3	Mizque
305	0305	3	Punata
306	0306	3	Quillacollo
307	0307	3	Tapacarí
308	0308	3	Tiraque
309	0309	3	Bolívar
310	0310	3	Arani
311	0311	3	Arque
312	0312	3	Capinota
313	0313	3	Germán Jordán
314	0314	3	Esteban Arce
315	0315	3	Campero
316	0316	3	Ayopaya
401	0401	4	Cercado
402	0402	4	Sabaya
403	0403	4	Carangas
404	0404	4	Poopó
405	0405	4	Sajama
406	0406	4	San Pedro de Totora
407	0407	4	Ladislao Cabrera
408	0408	4	Sebastián Pagador
409	0409	4	Sur Carangas
410	0410	4	Litoral
411	0411	4	Dalence
412	0412	4	Tomás Barrón
413	0413	4	Saucarí
414	0414	4	Mejillones
415	0415	4	Nor Carangas
416	0416	4	Abaroa
501	0501	5	Tomás Frías
502	0502	5	Rafael Bustillo
503	0503	5	Cornelio Saavedra
504	0504	5	Charcas
505	0505	5	Chayanta
506	0506	5	Nor Chichas
507	0507	5	Alonso de Ibáñez
508	0508	5	Enrique Baldivieso
509	0509	5	José María Linares
510	0510	5	Modesto Omiste
511	0511	5	Sud Chichas
512	0512	5	Sud Lípez
513	0513	5	Nor Lípez
514	0514	5	Daniel Campos
515	0515	5	Antonio Quijarro
517	0517	5	Bernardino Bilbao
601	0601	6	Cercado
602	0602	6	Arce
603	0603	6	Gran Chaco
604	0604	6	Méndez
605	0605	6	José María Avilés
606	0606	6	O'Connor
701	0701	7	Andrés Ibáñez
702	0702	7	Ignacio Warnes
705	0705	7	Chiquitos
706	0706	7	Ángel Sandóval
707	0707	7	Germán Busch
708	0708	7	Caballero
709	0709	7	Florida
710	0710	7	Obispo Santistevan
711	0711	7	Ñuflo de Chaves
712	0712	7	Vallegrande
713	0713	7	Guarayos
716	0716	7	Sara
717	0717	7	Cordillera
801	0801	8	Cercado
802	0802	8	Vaca Díez
803	0803	8	General José Ballivián
804	0804	8	Yacuma
805	0805	8	Moxos
806	0806	8	Marbán
807	0807	8	Mamoré
808	0808	8	Iténez
901	0901	9	Nicolás Suárez
902	0902	9	General Federico Román
903	0903	9	Madre de Dios
904	0904	9	Manuripi
905	0905	9	Abuná
\.


--
-- Name: catalogo_ayuda_humanitaria_id_ayuda_humanitaria_seq; Type: SEQUENCE SET; Schema: edan; Owner: postgres
--

SELECT pg_catalog.setval('edan.catalogo_ayuda_humanitaria_id_ayuda_humanitaria_seq', 1, false);


--
-- Name: catalogo_categoria_proteccion_id_categoria_proteccion_seq; Type: SEQUENCE SET; Schema: edan; Owner: postgres
--

SELECT pg_catalog.setval('edan.catalogo_categoria_proteccion_id_categoria_proteccion_seq', 7, true);


--
-- Name: catalogo_grupo_etario_id_grupo_etario_seq; Type: SEQUENCE SET; Schema: edan; Owner: postgres
--

SELECT pg_catalog.setval('edan.catalogo_grupo_etario_id_grupo_etario_seq', 4, true);


--
-- Name: catalogo_servicio_basico_id_servicio_basico_seq; Type: SEQUENCE SET; Schema: edan; Owner: postgres
--

SELECT pg_catalog.setval('edan.catalogo_servicio_basico_id_servicio_basico_seq', 5, true);


--
-- Name: catalogo_tipo_evento_id_tipo_evento_seq; Type: SEQUENCE SET; Schema: edan; Owner: postgres
--

SELECT pg_catalog.setval('edan.catalogo_tipo_evento_id_tipo_evento_seq', 8, true);


--
-- Name: edan_agricultura_id_agricultura_seq; Type: SEQUENCE SET; Schema: edan; Owner: postgres
--

SELECT pg_catalog.setval('edan.edan_agricultura_id_agricultura_seq', 1, false);


--
-- Name: edan_ayuda_humanitaria_id_ayuda_edan_seq; Type: SEQUENCE SET; Schema: edan; Owner: postgres
--

SELECT pg_catalog.setval('edan.edan_ayuda_humanitaria_id_ayuda_edan_seq', 1, false);


--
-- Name: edan_comunidad_id_comunidad_seq; Type: SEQUENCE SET; Schema: edan; Owner: postgres
--

SELECT pg_catalog.setval('edan.edan_comunidad_id_comunidad_seq', 1, false);


--
-- Name: edan_educacion_afectacion_id_educacion_afectacion_seq; Type: SEQUENCE SET; Schema: edan; Owner: postgres
--

SELECT pg_catalog.setval('edan.edan_educacion_afectacion_id_educacion_afectacion_seq', 1, false);


--
-- Name: edan_educacion_dano_id_educacion_dano_seq; Type: SEQUENCE SET; Schema: edan; Owner: postgres
--

SELECT pg_catalog.setval('edan.edan_educacion_dano_id_educacion_dano_seq', 1, false);


--
-- Name: edan_id_edan_seq; Type: SEQUENCE SET; Schema: edan; Owner: postgres
--

SELECT pg_catalog.setval('edan.edan_id_edan_seq', 1, true);


--
-- Name: edan_infraestructura_productiva_id_infra_productiva_seq; Type: SEQUENCE SET; Schema: edan; Owner: postgres
--

SELECT pg_catalog.setval('edan.edan_infraestructura_productiva_id_infra_productiva_seq', 1, false);


--
-- Name: edan_infraestructura_publica_id_infraestructura_publica_seq; Type: SEQUENCE SET; Schema: edan; Owner: postgres
--

SELECT pg_catalog.setval('edan.edan_infraestructura_publica_id_infraestructura_publica_seq', 1, false);


--
-- Name: edan_infraestructura_vial_id_infraestructura_vial_seq; Type: SEQUENCE SET; Schema: edan; Owner: postgres
--

SELECT pg_catalog.setval('edan.edan_infraestructura_vial_id_infraestructura_vial_seq', 1, false);


--
-- Name: edan_pecuaria_id_pecuaria_seq; Type: SEQUENCE SET; Schema: edan; Owner: postgres
--

SELECT pg_catalog.setval('edan.edan_pecuaria_id_pecuaria_seq', 1, false);


--
-- Name: edan_poblacion_grupo_id_poblacion_grupo_seq; Type: SEQUENCE SET; Schema: edan; Owner: postgres
--

SELECT pg_catalog.setval('edan.edan_poblacion_grupo_id_poblacion_grupo_seq', 1, false);


--
-- Name: edan_primera_respuesta_id_primera_respuesta_seq; Type: SEQUENCE SET; Schema: edan; Owner: postgres
--

SELECT pg_catalog.setval('edan.edan_primera_respuesta_id_primera_respuesta_seq', 1, false);


--
-- Name: edan_proteccion_id_proteccion_seq; Type: SEQUENCE SET; Schema: edan; Owner: postgres
--

SELECT pg_catalog.setval('edan.edan_proteccion_id_proteccion_seq', 1, false);


--
-- Name: edan_salud_establecimiento_id_salud_establecimiento_seq; Type: SEQUENCE SET; Schema: edan; Owner: postgres
--

SELECT pg_catalog.setval('edan.edan_salud_establecimiento_id_salud_establecimiento_seq', 1, false);


--
-- Name: edan_salud_necesidades_id_salud_necesidad_seq; Type: SEQUENCE SET; Schema: edan; Owner: postgres
--

SELECT pg_catalog.setval('edan.edan_salud_necesidades_id_salud_necesidad_seq', 1, false);


--
-- Name: edan_servicio_basico_id_servicio_basico_edan_seq; Type: SEQUENCE SET; Schema: edan; Owner: postgres
--

SELECT pg_catalog.setval('edan.edan_servicio_basico_id_servicio_basico_edan_seq', 1, false);


--
-- Name: edan_tipo_evento_id_tipo_evento_edan_seq; Type: SEQUENCE SET; Schema: edan; Owner: postgres
--

SELECT pg_catalog.setval('edan.edan_tipo_evento_id_tipo_evento_edan_seq', 1, false);


--
-- Name: edan_vivienda_id_vivienda_seq; Type: SEQUENCE SET; Schema: edan; Owner: postgres
--

SELECT pg_catalog.setval('edan.edan_vivienda_id_vivienda_seq', 1, false);


--
-- Name: ayuda_humanitaria catalogo_ayuda_humanitaria_nombre_key; Type: CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.ayuda_humanitaria
    ADD CONSTRAINT catalogo_ayuda_humanitaria_nombre_key UNIQUE (nombre);


--
-- Name: ayuda_humanitaria catalogo_ayuda_humanitaria_pkey; Type: CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.ayuda_humanitaria
    ADD CONSTRAINT catalogo_ayuda_humanitaria_pkey PRIMARY KEY (id_ayuda_humanitaria);


--
-- Name: categoria_proteccion catalogo_categoria_proteccion_nombre_key; Type: CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.categoria_proteccion
    ADD CONSTRAINT catalogo_categoria_proteccion_nombre_key UNIQUE (nombre);


--
-- Name: categoria_proteccion catalogo_categoria_proteccion_pkey; Type: CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.categoria_proteccion
    ADD CONSTRAINT catalogo_categoria_proteccion_pkey PRIMARY KEY (id_categoria_proteccion);


--
-- Name: grupo_etario catalogo_grupo_etario_nombre_key; Type: CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.grupo_etario
    ADD CONSTRAINT catalogo_grupo_etario_nombre_key UNIQUE (nombre);


--
-- Name: grupo_etario catalogo_grupo_etario_pkey; Type: CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.grupo_etario
    ADD CONSTRAINT catalogo_grupo_etario_pkey PRIMARY KEY (id_grupo_etario);


--
-- Name: servicio_basico catalogo_servicio_basico_nombre_key; Type: CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.servicio_basico
    ADD CONSTRAINT catalogo_servicio_basico_nombre_key UNIQUE (nombre);


--
-- Name: servicio_basico catalogo_servicio_basico_pkey; Type: CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.servicio_basico
    ADD CONSTRAINT catalogo_servicio_basico_pkey PRIMARY KEY (id_servicio_basico);


--
-- Name: tipo_evento catalogo_tipo_evento_nombre_key; Type: CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.tipo_evento
    ADD CONSTRAINT catalogo_tipo_evento_nombre_key UNIQUE (nombre);


--
-- Name: tipo_evento catalogo_tipo_evento_pkey; Type: CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.tipo_evento
    ADD CONSTRAINT catalogo_tipo_evento_pkey PRIMARY KEY (id_tipo_evento);


--
-- Name: edan_agricultura edan_agricultura_pkey; Type: CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_agricultura
    ADD CONSTRAINT edan_agricultura_pkey PRIMARY KEY (id_agricultura);


--
-- Name: edan_ayuda_humanitaria edan_ayuda_humanitaria_id_edan_id_ayuda_humanitaria_key; Type: CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_ayuda_humanitaria
    ADD CONSTRAINT edan_ayuda_humanitaria_id_edan_id_ayuda_humanitaria_key UNIQUE (id_edan, id_ayuda_humanitaria);


--
-- Name: edan_ayuda_humanitaria edan_ayuda_humanitaria_pkey; Type: CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_ayuda_humanitaria
    ADD CONSTRAINT edan_ayuda_humanitaria_pkey PRIMARY KEY (id_ayuda_edan);


--
-- Name: edan_comunidad edan_comunidad_pkey; Type: CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_comunidad
    ADD CONSTRAINT edan_comunidad_pkey PRIMARY KEY (id_comunidad);


--
-- Name: edan_educacion_afectacion edan_educacion_afectacion_pkey; Type: CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_educacion_afectacion
    ADD CONSTRAINT edan_educacion_afectacion_pkey PRIMARY KEY (id_educacion_afectacion);


--
-- Name: edan_educacion_dano edan_educacion_dano_pkey; Type: CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_educacion_dano
    ADD CONSTRAINT edan_educacion_dano_pkey PRIMARY KEY (id_educacion_dano);


--
-- Name: edan_infraestructura_productiva edan_infraestructura_productiva_pkey; Type: CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_infraestructura_productiva
    ADD CONSTRAINT edan_infraestructura_productiva_pkey PRIMARY KEY (id_infra_productiva);


--
-- Name: edan_infraestructura_publica edan_infraestructura_publica_pkey; Type: CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_infraestructura_publica
    ADD CONSTRAINT edan_infraestructura_publica_pkey PRIMARY KEY (id_infraestructura_publica);


--
-- Name: edan_infraestructura_vial edan_infraestructura_vial_pkey; Type: CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_infraestructura_vial
    ADD CONSTRAINT edan_infraestructura_vial_pkey PRIMARY KEY (id_infraestructura_vial);


--
-- Name: edan_pecuaria edan_pecuaria_pkey; Type: CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_pecuaria
    ADD CONSTRAINT edan_pecuaria_pkey PRIMARY KEY (id_pecuaria);


--
-- Name: edan edan_pkey; Type: CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan
    ADD CONSTRAINT edan_pkey PRIMARY KEY (id_edan);


--
-- Name: edan_poblacion_grupo edan_poblacion_grupo_id_edan_id_grupo_etario_key; Type: CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_poblacion_grupo
    ADD CONSTRAINT edan_poblacion_grupo_id_edan_id_grupo_etario_key UNIQUE (id_edan, id_grupo_etario);


--
-- Name: edan_poblacion_grupo edan_poblacion_grupo_pkey; Type: CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_poblacion_grupo
    ADD CONSTRAINT edan_poblacion_grupo_pkey PRIMARY KEY (id_poblacion_grupo);


--
-- Name: edan_primera_respuesta edan_primera_respuesta_pkey; Type: CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_primera_respuesta
    ADD CONSTRAINT edan_primera_respuesta_pkey PRIMARY KEY (id_primera_respuesta);


--
-- Name: edan_proteccion edan_proteccion_id_edan_id_categoria_proteccion_key; Type: CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_proteccion
    ADD CONSTRAINT edan_proteccion_id_edan_id_categoria_proteccion_key UNIQUE (id_edan, id_categoria_proteccion);


--
-- Name: edan_proteccion edan_proteccion_pkey; Type: CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_proteccion
    ADD CONSTRAINT edan_proteccion_pkey PRIMARY KEY (id_proteccion);


--
-- Name: edan_salud_establecimiento edan_salud_establecimiento_pkey; Type: CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_salud_establecimiento
    ADD CONSTRAINT edan_salud_establecimiento_pkey PRIMARY KEY (id_salud_establecimiento);


--
-- Name: edan_salud_necesidades edan_salud_necesidades_pkey; Type: CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_salud_necesidades
    ADD CONSTRAINT edan_salud_necesidades_pkey PRIMARY KEY (id_salud_necesidad);


--
-- Name: edan_servicio_basico edan_servicio_basico_id_edan_id_servicio_basico_key; Type: CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_servicio_basico
    ADD CONSTRAINT edan_servicio_basico_id_edan_id_servicio_basico_key UNIQUE (id_edan, id_servicio_basico);


--
-- Name: edan_servicio_basico edan_servicio_basico_pkey; Type: CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_servicio_basico
    ADD CONSTRAINT edan_servicio_basico_pkey PRIMARY KEY (id_servicio_basico_edan);


--
-- Name: edan_tipo_evento edan_tipo_evento_id_edan_id_tipo_evento_key; Type: CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_tipo_evento
    ADD CONSTRAINT edan_tipo_evento_id_edan_id_tipo_evento_key UNIQUE (id_edan, id_tipo_evento);


--
-- Name: edan_tipo_evento edan_tipo_evento_pkey; Type: CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_tipo_evento
    ADD CONSTRAINT edan_tipo_evento_pkey PRIMARY KEY (id_tipo_evento_edan);


--
-- Name: edan_vivienda edan_vivienda_pkey; Type: CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_vivienda
    ADD CONSTRAINT edan_vivienda_pkey PRIMARY KEY (id_vivienda);


--
-- Name: departamento catalogo_departamento_codigo_ine_key; Type: CONSTRAINT; Schema: shared; Owner: postgres
--

ALTER TABLE ONLY shared.departamento
    ADD CONSTRAINT catalogo_departamento_codigo_ine_key UNIQUE (codigo_ine);


--
-- Name: departamento catalogo_departamento_nombre_key; Type: CONSTRAINT; Schema: shared; Owner: postgres
--

ALTER TABLE ONLY shared.departamento
    ADD CONSTRAINT catalogo_departamento_nombre_key UNIQUE (nombre);


--
-- Name: departamento catalogo_departamento_pkey; Type: CONSTRAINT; Schema: shared; Owner: postgres
--

ALTER TABLE ONLY shared.departamento
    ADD CONSTRAINT catalogo_departamento_pkey PRIMARY KEY (id);


--
-- Name: municipio catalogo_municipio_codigo_ine_key; Type: CONSTRAINT; Schema: shared; Owner: postgres
--

ALTER TABLE ONLY shared.municipio
    ADD CONSTRAINT catalogo_municipio_codigo_ine_key UNIQUE (codigo_ine);


--
-- Name: municipio catalogo_municipio_pkey; Type: CONSTRAINT; Schema: shared; Owner: postgres
--

ALTER TABLE ONLY shared.municipio
    ADD CONSTRAINT catalogo_municipio_pkey PRIMARY KEY (id);


--
-- Name: provincia catalogo_provincia_codigo_ine_key; Type: CONSTRAINT; Schema: shared; Owner: postgres
--

ALTER TABLE ONLY shared.provincia
    ADD CONSTRAINT catalogo_provincia_codigo_ine_key UNIQUE (codigo_ine);


--
-- Name: provincia catalogo_provincia_pkey; Type: CONSTRAINT; Schema: shared; Owner: postgres
--

ALTER TABLE ONLY shared.provincia
    ADD CONSTRAINT catalogo_provincia_pkey PRIMARY KEY (id);


--
-- Name: cultivo cultivo_pkey; Type: CONSTRAINT; Schema: shared; Owner: sinagersat
--

ALTER TABLE ONLY shared.cultivo
    ADD CONSTRAINT cultivo_pkey PRIMARY KEY (id);


--
-- Name: pecuario pecuario_pkey; Type: CONSTRAINT; Schema: shared; Owner: sinagersat
--

ALTER TABLE ONLY shared.pecuario
    ADD CONSTRAINT pecuario_pkey PRIMARY KEY (id);


--
-- Name: municipio uq_municipio_departamento_id; Type: CONSTRAINT; Schema: shared; Owner: postgres
--

ALTER TABLE ONLY shared.municipio
    ADD CONSTRAINT uq_municipio_departamento_id UNIQUE (id_departamento, id);


--
-- Name: municipio uq_municipio_provincia_id; Type: CONSTRAINT; Schema: shared; Owner: postgres
--

ALTER TABLE ONLY shared.municipio
    ADD CONSTRAINT uq_municipio_provincia_id UNIQUE (id_provincia, id);


--
-- Name: provincia uq_provincia_departamento_id; Type: CONSTRAINT; Schema: shared; Owner: postgres
--

ALTER TABLE ONLY shared.provincia
    ADD CONSTRAINT uq_provincia_departamento_id UNIQUE (id_departamento, id);


--
-- Name: idx_edan_agricultura_edan; Type: INDEX; Schema: edan; Owner: postgres
--

CREATE INDEX idx_edan_agricultura_edan ON edan.edan_agricultura USING btree (id_edan);


--
-- Name: idx_edan_ayuda_humanitaria_edan; Type: INDEX; Schema: edan; Owner: postgres
--

CREATE INDEX idx_edan_ayuda_humanitaria_edan ON edan.edan_ayuda_humanitaria USING btree (id_edan);


--
-- Name: idx_edan_comunidad_edan; Type: INDEX; Schema: edan; Owner: postgres
--

CREATE INDEX idx_edan_comunidad_edan ON edan.edan_comunidad USING btree (id_edan);


--
-- Name: idx_edan_dep; Type: INDEX; Schema: edan; Owner: postgres
--

CREATE INDEX idx_edan_dep ON edan.edan USING btree (id_departamento);


--
-- Name: idx_edan_educacion_afectacion_edan; Type: INDEX; Schema: edan; Owner: postgres
--

CREATE INDEX idx_edan_educacion_afectacion_edan ON edan.edan_educacion_afectacion USING btree (id_edan);


--
-- Name: idx_edan_educacion_dano_edan; Type: INDEX; Schema: edan; Owner: postgres
--

CREATE INDEX idx_edan_educacion_dano_edan ON edan.edan_educacion_dano USING btree (id_edan);


--
-- Name: idx_edan_fecha_evento; Type: INDEX; Schema: edan; Owner: postgres
--

CREATE INDEX idx_edan_fecha_evento ON edan.edan USING btree (fecha_evento);


--
-- Name: idx_edan_infraestructura_productiva_edan; Type: INDEX; Schema: edan; Owner: postgres
--

CREATE INDEX idx_edan_infraestructura_productiva_edan ON edan.edan_infraestructura_productiva USING btree (id_edan);


--
-- Name: idx_edan_infraestructura_publica_edan; Type: INDEX; Schema: edan; Owner: postgres
--

CREATE INDEX idx_edan_infraestructura_publica_edan ON edan.edan_infraestructura_publica USING btree (id_edan);


--
-- Name: idx_edan_infraestructura_vial_edan; Type: INDEX; Schema: edan; Owner: postgres
--

CREATE INDEX idx_edan_infraestructura_vial_edan ON edan.edan_infraestructura_vial USING btree (id_edan);


--
-- Name: idx_edan_mun; Type: INDEX; Schema: edan; Owner: postgres
--

CREATE INDEX idx_edan_mun ON edan.edan USING btree (id_municipio);


--
-- Name: idx_edan_pecuaria_edan; Type: INDEX; Schema: edan; Owner: postgres
--

CREATE INDEX idx_edan_pecuaria_edan ON edan.edan_pecuaria USING btree (id_edan);


--
-- Name: idx_edan_poblacion_grupo_edan; Type: INDEX; Schema: edan; Owner: postgres
--

CREATE INDEX idx_edan_poblacion_grupo_edan ON edan.edan_poblacion_grupo USING btree (id_edan);


--
-- Name: idx_edan_primera_respuesta_edan; Type: INDEX; Schema: edan; Owner: postgres
--

CREATE INDEX idx_edan_primera_respuesta_edan ON edan.edan_primera_respuesta USING btree (id_edan);


--
-- Name: idx_edan_proteccion_edan; Type: INDEX; Schema: edan; Owner: postgres
--

CREATE INDEX idx_edan_proteccion_edan ON edan.edan_proteccion USING btree (id_edan);


--
-- Name: idx_edan_salud_establecimiento_edan; Type: INDEX; Schema: edan; Owner: postgres
--

CREATE INDEX idx_edan_salud_establecimiento_edan ON edan.edan_salud_establecimiento USING btree (id_edan);


--
-- PostgreSQL database dump complete
--

\unrestrict 0bt6cxd9cAWF4PmiIuwpuXMbbZlW1MiP6hH8gfItVtb81nTLD80NVKZz16nmtWI

