--
-- PostgreSQL database dump
--

\restrict f7LU5TBfUsTy1YmT2NbwXH2qlHa5r8Q9OJF5HZpdAKYBGdQm9gdH7GaJijEk6cb

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
-- Name: recursos; Type: SCHEMA; Schema: -; Owner: sinagersat
--

CREATE SCHEMA recursos;


ALTER SCHEMA recursos OWNER TO sinagersat;

--
-- Name: rida; Type: SCHEMA; Schema: -; Owner: sinagersat
--

CREATE SCHEMA rida;


ALTER SCHEMA rida OWNER TO sinagersat;

--
-- Name: shared; Type: SCHEMA; Schema: -; Owner: sinagersat
--

CREATE SCHEMA shared;


ALTER SCHEMA shared OWNER TO sinagersat;

--
-- Name: sinb; Type: SCHEMA; Schema: -; Owner: sinagersat
--

CREATE SCHEMA sinb;


ALTER SCHEMA sinb OWNER TO sinagersat;

--
-- Name: usuarios; Type: SCHEMA; Schema: -; Owner: sinagersat
--

CREATE SCHEMA usuarios;


ALTER SCHEMA usuarios OWNER TO sinagersat;

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
    fecha_actualizacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP
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
-- Name: aplicacion; Type: TABLE; Schema: usuarios; Owner: sinagersat
--

CREATE TABLE usuarios.aplicacion (
    id_aplicacion integer NOT NULL,
    codigo character varying(20) NOT NULL,
    nombre character varying(100) NOT NULL,
    descripcion character varying(255),
    activo boolean DEFAULT true
);


ALTER TABLE usuarios.aplicacion OWNER TO sinagersat;

--
-- Name: aplicacion_id_aplicacion_seq; Type: SEQUENCE; Schema: usuarios; Owner: sinagersat
--

CREATE SEQUENCE usuarios.aplicacion_id_aplicacion_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE usuarios.aplicacion_id_aplicacion_seq OWNER TO sinagersat;

--
-- Name: aplicacion_id_aplicacion_seq; Type: SEQUENCE OWNED BY; Schema: usuarios; Owner: sinagersat
--

ALTER SEQUENCE usuarios.aplicacion_id_aplicacion_seq OWNED BY usuarios.aplicacion.id_aplicacion;


--
-- Name: auditoria; Type: TABLE; Schema: usuarios; Owner: sinagersat
--

CREATE TABLE usuarios.auditoria (
    id_auditoria bigint NOT NULL,
    id_usuario integer,
    id_aplicacion integer,
    accion character varying(100) NOT NULL,
    detalle jsonb,
    ip_origen character varying(50),
    fecha timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE usuarios.auditoria OWNER TO sinagersat;

--
-- Name: auditoria_id_auditoria_seq; Type: SEQUENCE; Schema: usuarios; Owner: sinagersat
--

CREATE SEQUENCE usuarios.auditoria_id_auditoria_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE usuarios.auditoria_id_auditoria_seq OWNER TO sinagersat;

--
-- Name: auditoria_id_auditoria_seq; Type: SEQUENCE OWNED BY; Schema: usuarios; Owner: sinagersat
--

ALTER SEQUENCE usuarios.auditoria_id_auditoria_seq OWNED BY usuarios.auditoria.id_auditoria;


--
-- Name: permiso_aplicacion; Type: TABLE; Schema: usuarios; Owner: sinagersat
--

CREATE TABLE usuarios.permiso_aplicacion (
    id_permiso integer NOT NULL,
    id_rol integer NOT NULL,
    id_aplicacion integer NOT NULL
);


ALTER TABLE usuarios.permiso_aplicacion OWNER TO sinagersat;

--
-- Name: permiso_aplicacion_id_permiso_seq; Type: SEQUENCE; Schema: usuarios; Owner: sinagersat
--

CREATE SEQUENCE usuarios.permiso_aplicacion_id_permiso_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE usuarios.permiso_aplicacion_id_permiso_seq OWNER TO sinagersat;

--
-- Name: permiso_aplicacion_id_permiso_seq; Type: SEQUENCE OWNED BY; Schema: usuarios; Owner: sinagersat
--

ALTER SEQUENCE usuarios.permiso_aplicacion_id_permiso_seq OWNED BY usuarios.permiso_aplicacion.id_permiso;


--
-- Name: reset_contrasena; Type: TABLE; Schema: usuarios; Owner: sinagersat
--

CREATE TABLE usuarios.reset_contrasena (
    id_reset integer NOT NULL,
    id_usuario integer NOT NULL,
    token character varying(255) NOT NULL,
    usado boolean DEFAULT false,
    fecha_solicitud timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    fecha_expiracion timestamp without time zone NOT NULL,
    ip_origen character varying(50)
);


ALTER TABLE usuarios.reset_contrasena OWNER TO sinagersat;

--
-- Name: reset_contrasena_id_reset_seq; Type: SEQUENCE; Schema: usuarios; Owner: sinagersat
--

CREATE SEQUENCE usuarios.reset_contrasena_id_reset_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE usuarios.reset_contrasena_id_reset_seq OWNER TO sinagersat;

--
-- Name: reset_contrasena_id_reset_seq; Type: SEQUENCE OWNED BY; Schema: usuarios; Owner: sinagersat
--

ALTER SEQUENCE usuarios.reset_contrasena_id_reset_seq OWNED BY usuarios.reset_contrasena.id_reset;


--
-- Name: rol; Type: TABLE; Schema: usuarios; Owner: sinagersat
--

CREATE TABLE usuarios.rol (
    id_rol integer NOT NULL,
    nombre character varying(50) NOT NULL,
    descripcion character varying(255),
    jerarquia integer NOT NULL
);


ALTER TABLE usuarios.rol OWNER TO sinagersat;

--
-- Name: rol_id_rol_seq; Type: SEQUENCE; Schema: usuarios; Owner: sinagersat
--

CREATE SEQUENCE usuarios.rol_id_rol_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE usuarios.rol_id_rol_seq OWNER TO sinagersat;

--
-- Name: rol_id_rol_seq; Type: SEQUENCE OWNED BY; Schema: usuarios; Owner: sinagersat
--

ALTER SEQUENCE usuarios.rol_id_rol_seq OWNED BY usuarios.rol.id_rol;


--
-- Name: sesion; Type: TABLE; Schema: usuarios; Owner: sinagersat
--

CREATE TABLE usuarios.sesion (
    id_sesion integer NOT NULL,
    id_usuario integer NOT NULL,
    token character varying(255) NOT NULL,
    fecha_inicio timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    fecha_expiracion timestamp without time zone NOT NULL,
    ip_origen character varying(50),
    activo boolean DEFAULT true
);


ALTER TABLE usuarios.sesion OWNER TO sinagersat;

--
-- Name: sesion_id_sesion_seq; Type: SEQUENCE; Schema: usuarios; Owner: sinagersat
--

CREATE SEQUENCE usuarios.sesion_id_sesion_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE usuarios.sesion_id_sesion_seq OWNER TO sinagersat;

--
-- Name: sesion_id_sesion_seq; Type: SEQUENCE OWNED BY; Schema: usuarios; Owner: sinagersat
--

ALTER SEQUENCE usuarios.sesion_id_sesion_seq OWNED BY usuarios.sesion.id_sesion;


--
-- Name: usuario; Type: TABLE; Schema: usuarios; Owner: sinagersat
--

CREATE TABLE usuarios.usuario (
    id_usuario integer NOT NULL,
    usuario character varying(50) NOT NULL,
    email character varying(200) NOT NULL,
    contrasena_hash character varying(255) NOT NULL,
    nombre_completo character varying(200) NOT NULL,
    cargo character varying(100),
    telefono character varying(30),
    activo boolean DEFAULT true,
    intentos_fallidos integer DEFAULT 0,
    bloqueado_hasta timestamp without time zone,
    debe_cambiar_contrasena boolean DEFAULT true,
    ultimo_acceso timestamp without time zone,
    fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    creado_por integer,
    fecha_actualizacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE usuarios.usuario OWNER TO sinagersat;

--
-- Name: usuario_id_usuario_seq; Type: SEQUENCE; Schema: usuarios; Owner: sinagersat
--

CREATE SEQUENCE usuarios.usuario_id_usuario_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE usuarios.usuario_id_usuario_seq OWNER TO sinagersat;

--
-- Name: usuario_id_usuario_seq; Type: SEQUENCE OWNED BY; Schema: usuarios; Owner: sinagersat
--

ALTER SEQUENCE usuarios.usuario_id_usuario_seq OWNED BY usuarios.usuario.id_usuario;


--
-- Name: usuario_rol; Type: TABLE; Schema: usuarios; Owner: sinagersat
--

CREATE TABLE usuarios.usuario_rol (
    id_usuario integer NOT NULL,
    id_rol integer NOT NULL
);


ALTER TABLE usuarios.usuario_rol OWNER TO sinagersat;

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
-- Name: aplicacion id_aplicacion; Type: DEFAULT; Schema: usuarios; Owner: sinagersat
--

ALTER TABLE ONLY usuarios.aplicacion ALTER COLUMN id_aplicacion SET DEFAULT nextval('usuarios.aplicacion_id_aplicacion_seq'::regclass);


--
-- Name: auditoria id_auditoria; Type: DEFAULT; Schema: usuarios; Owner: sinagersat
--

ALTER TABLE ONLY usuarios.auditoria ALTER COLUMN id_auditoria SET DEFAULT nextval('usuarios.auditoria_id_auditoria_seq'::regclass);


--
-- Name: permiso_aplicacion id_permiso; Type: DEFAULT; Schema: usuarios; Owner: sinagersat
--

ALTER TABLE ONLY usuarios.permiso_aplicacion ALTER COLUMN id_permiso SET DEFAULT nextval('usuarios.permiso_aplicacion_id_permiso_seq'::regclass);


--
-- Name: reset_contrasena id_reset; Type: DEFAULT; Schema: usuarios; Owner: sinagersat
--

ALTER TABLE ONLY usuarios.reset_contrasena ALTER COLUMN id_reset SET DEFAULT nextval('usuarios.reset_contrasena_id_reset_seq'::regclass);


--
-- Name: rol id_rol; Type: DEFAULT; Schema: usuarios; Owner: sinagersat
--

ALTER TABLE ONLY usuarios.rol ALTER COLUMN id_rol SET DEFAULT nextval('usuarios.rol_id_rol_seq'::regclass);


--
-- Name: sesion id_sesion; Type: DEFAULT; Schema: usuarios; Owner: sinagersat
--

ALTER TABLE ONLY usuarios.sesion ALTER COLUMN id_sesion SET DEFAULT nextval('usuarios.sesion_id_sesion_seq'::regclass);


--
-- Name: usuario id_usuario; Type: DEFAULT; Schema: usuarios; Owner: sinagersat
--

ALTER TABLE ONLY usuarios.usuario ALTER COLUMN id_usuario SET DEFAULT nextval('usuarios.usuario_id_usuario_seq'::regclass);


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

COPY edan.edan (id_edan, codigo_edan, id_departamento, id_municipio, nombre_alcalde, telefono_alcalde, fecha_llenado, fecha_evento, hora_evento, localidades_afectadas, total_poblacion_afectada, total_familias_afectadas, total_familias_damnificadas, nombre_responsable, cargo_responsable, telefono_responsable, email_responsable, usuario_registro, fecha_registro, fecha_actualizacion) FROM stdin;
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
9	09	Pando
\.


--
-- Data for Name: municipio; Type: TABLE DATA; Schema: shared; Owner: postgres
--

COPY shared.municipio (id, codigo_ine, id_departamento, id_provincia, nombre) FROM stdin;
10101	010101	1	101	Sucre
10102	010102	1	101	Yotala
10103	010103	1	101	Poroma
10201	010201	1	102	Azurduy
10202	010202	1	102	Tarvita
10301	010401	1	103	Padilla
10302	010402	1	103	Tomina
10303	010403	1	103	Sopachuy
10304	010404	1	103	Villa Alcalá
10305	010405	1	103	El Villar
10401	010501	1	104	Monteagudo
10402	010502	1	104	Huacareta
10501	010601	1	105	Tarabuco
10502	010602	1	105	Yamparáez
10601	010701	1	106	Camargo
10602	010702	1	106	San Lucas
10603	010703	1	106	Incahuasi
10604	010704	1	106	Villa Charcas
10701	010901	1	107	Villa Abecia
10702	010902	1	107	Culpina
10703	010903	1	107	Las Carreras
10801	010801	1	108	Villa Serrano
10901	010301	1	109	Villa Zudáñez
10902	010302	1	109	Presto
10903	010303	1	109	Villa Mojocoya
10904	010304	1	109	Icla
11001	011001	1	110	Villa Vaca Guzmán (Muyupampa)
11002	011002	1	110	Huacaya
11003	011003	1	110	Macharetí
20101	020101	2	201	La Paz
20102	020102	2	201	Palca
20103	020103	2	201	Mecapaca
20104	020104	2	201	Achocalla
20105	020105	2	201	El Alto
20201	020201	2	202	Achacachi
20202	020202	2	202	Ancoraimes
20203	020203	2	202	Chua Cocani
20204	020204	2	202	Huarina
20205	020205	2	202	Santiago de Huata
20206	020206	2	202	Huatajata
20301	020301	2	203	Coro Coro
20302	020302	2	203	Caquiaviri
20303	020303	2	203	Calacoto
20304	020304	2	203	Comanche
20305	020305	2	203	Charaña
20306	020306	2	203	Waldo Ballivián
20307	020307	2	203	Nazacara de Pacajes
20308	020308	2	203	Callapa
20401	020401	2	204	Puerto Acosta
20402	020402	2	204	Mocomoco
20403	020403	2	204	Puerto Carabuco
20404	020404	2	204	Humanata
20405	020405	2	204	Escoma
20501	020501	2	205	Chuma
20502	020502	2	205	Ayata
20503	020503	2	205	Aucapata
20601	020601	2	206	Sorata
20602	020602	2	206	Guanay
20603	020603	2	206	Tacacoma
20604	020604	2	206	Quiabaya
20605	020605	2	206	Combaya
20606	020606	2	206	Tipuani
20607	020607	2	206	Mapiri
20608	020608	2	206	Teoponte
20701	020701	2	207	Apolo
20702	020702	2	207	Pelechuco
20801	020801	2	208	Viacha
20802	020802	2	208	Guaqui
20803	020803	2	208	Tiahuanaco
20804	020804	2	208	Desaguadero
20805	020805	2	208	San Andrés de Machaca
20806	020806	2	208	Jesús de Machaca
20807	020807	2	208	Taraco
20901	020901	2	209	Luribay
20902	020902	2	209	Sapahaqui
20903	020903	2	209	Yaco
20904	020904	2	209	Malla
20905	020905	2	209	Cairoma
21001	021001	2	210	Inquisivi
21002	021002	2	210	Quime
21003	021003	2	210	Cajuata
21004	021004	2	210	Colquiri
21005	021005	2	210	Ichoca
21006	021006	2	210	Licoma Pampa
21101	021101	2	211	Chulumani
21102	021102	2	211	Irupana
21103	021103	2	211	Yanacachi
21104	021104	2	211	Palos Blancos
21105	021105	2	211	La Asunta
21201	021201	2	212	Pucarani
21202	021202	2	212	Laja
21203	021203	2	212	Batallas
21204	021204	2	212	Puerto Pérez
21301	021301	2	213	Sica Sica
21302	021302	2	213	Umala
21303	021303	2	213	Ayo Ayo
21304	021304	2	213	Calamarca
21305	021305	2	213	Patacamaya
21306	021306	2	213	Colquencha
21307	021307	2	213	Collana
21401	021401	2	214	Coroico
21402	021402	2	214	Coripata
21501	021501	2	215	Ixiamas
21502	021502	2	215	San Buenaventura
21601	021601	2	216	Charazani
21602	021602	2	216	Curva
21701	021701	2	217	Copacabana
21702	021702	2	217	San Pedro de Tiquina
21703	021703	2	217	Tito Yupanqui
21801	021801	2	218	San Pedro de Curahuara
21802	021802	2	218	Papel Pampa
21803	021803	2	218	Chacarilla
21901	021901	2	219	Santiago de Machaca
21902	021902	2	219	Catacora
22001	022001	2	220	Caranavi
22002	022002	2	220	Alto Beni
30101	030101	3	301	Cochabamba
30201	031001	3	302	Sacaba
30202	031002	3	302	Colomi
30203	031003	3	302	Villa Tunari
30301	031201	3	303	Totora
30302	031202	3	303	Pojo
30303	031203	3	303	Pocona
30304	031204	3	303	Chimoré
30305	031205	3	303	Puerto Villarroel
30306	031206	3	303	Entre Ríos
30401	031301	3	304	Mizque
30402	031302	3	304	Vila Vila
30403	031303	3	304	Alalay
30501	031401	3	305	Punata
30502	031402	3	305	Villa Rivero
30503	031403	3	305	San Benito
30504	031404	3	305	Tacachi
30505	031405	3	305	Cuchumuela
30601	030901	3	306	Quillacollo
30602	030902	3	306	Sipe Sipe
30603	030903	3	306	Tiquipaya
30604	030904	3	306	Vinto
30605	030905	3	306	Colcapirhua
30701	031101	3	307	Tapacarí
30801	031601	3	308	Tiraque
30802	031602	3	308	Shinahota
30901	031501	3	309	Bolívar
31001	030501	3	310	Arani
31002	030502	3	310	Vacas
31101	030601	3	311	Arque
31102	030602	3	311	Tacopaya
31201	030701	3	312	Capinota
31202	030702	3	312	Santiváñez
31203	030703	3	312	Sicaya
31301	030801	3	313	Cliza
31302	030802	3	313	Toco
31303	030803	3	313	Tolata
31401	030401	3	314	Tarata
31402	030402	3	314	Anzaldo
31403	030403	3	314	Arbieto
31404	030404	3	314	Sacabamba
31501	030201	3	315	Aiquile
31502	030202	3	315	Pasorapa
31503	030203	3	315	Omereque
31601	030301	3	316	Independencia
31602	030302	3	316	Morochata
31603	030303	3	316	Cocapata
40101	040101	4	401	Oruro
40102	040102	4	401	Caracollo
40103	040103	4	401	El Choro
40104	040104	4	401	Paria
40201	040901	4	402	Sabaya
40202	040902	4	402	Coipasa
40203	040903	4	402	Chipaya
40301	040301	4	403	Corque
40302	040302	4	403	Choquecota
40401	040601	4	404	Poopó
40402	040602	4	404	Pazña
40403	040603	4	404	Antequera
40501	040401	4	405	Curahuara de Carangas
40502	040402	4	405	Turco
40601	041301	4	406	Totora
40701	040801	4	407	Salinas de Garci Mendoza
40702	040802	4	407	Pampa Aullagas
40801	041401	4	408	Santiago de Huari
40901	041201	4	409	Santiago de Andamarca
40902	041202	4	409	Belén de Andamarca
41001	040501	4	410	Huachacalla
41002	040502	4	410	Escara
41003	040503	4	410	Cruz de Machacamarca
41004	040504	4	410	Yunguyo de Litoral
41005	040505	4	410	Esmeralda
41101	040701	4	411	Huanuni
41102	040702	4	411	Machacamarca
41201	041101	4	412	Eucaliptus
41301	041001	4	413	Toledo
41401	041501	4	414	La Rivera
41402	041502	4	414	Todos Santos
41403	041503	4	414	Carangas
41501	041601	4	415	Huayllamarca
41601	040201	4	416	Challapata
41602	040202	4	416	Santuario de Quillacas
50101	050101	5	501	Potosí
50102	050102	5	501	Tinguipaya
50103	050103	5	501	Yocalla
50104	050104	5	501	Urmiri
50201	050201	5	502	Uncía
50202	050202	5	502	Chayanta
50203	050203	5	502	Llallagua
50204	050204	5	502	Chuquihuta
50301	050301	5	503	Betanzos
50302	050302	5	503	Chaquí
50303	050303	5	503	Tacobamba
50401	050501	5	504	San Pedro de Buena Vista
50402	050502	5	504	Toro Toro
50501	050401	5	505	Colquechaca
50502	050402	5	505	Ravelo
50503	050403	5	505	Pocoata
50504	050404	5	505	Ocurí
50505	050405	5	505	San Pedro de Macha
50601	050601	5	506	Santiago de Cotagaita
50602	050602	5	506	Vitichi
50701	050701	5	507	Sacaca
50702	050702	5	507	Caripuyo
50801	051601	5	508	San Agustín
50901	051101	5	509	Puna
50902	051102	5	509	Caiza D
50903	051103	5	509	Ckochas
51001	051501	5	510	Villazón
51101	050801	5	511	Tupiza
51102	050802	5	511	Atocha
51201	051001	5	512	San Pablo de Lípez
51202	051002	5	512	Mojinete
51203	051003	5	512	San Antonio de Esmoruco
51301	050901	5	513	Colcha K
51302	050902	5	513	San Pedro de Quemes
51401	051401	5	514	Llica
51402	051402	5	514	Tahua
51501	051201	5	515	Uyuni
51502	051202	5	515	Tomave
51503	051203	5	515	Porco
51701	051301	5	517	Arampampa
51702	051302	5	517	Acasio
60101	060101	6	601	Tarija
60201	060201	6	602	Padcaya
60202	060202	6	602	Bermejo
60301	060301	6	603	Yacuiba
60302	060302	6	603	Caraparí
60303	060303	6	603	Villa Montes
60401	060501	6	604	San Lorenzo
60402	060502	6	604	El Puente
60501	060401	6	605	Uriondo
60502	060402	6	605	Yunchará
60601	060601	6	606	Entre Ríos
70101	070101	7	701	Santa Cruz de la Sierra
70102	070102	7	701	Cotoca
70103	070103	7	701	Porongo
70104	070104	7	701	La Guardia
70105	070105	7	701	El Torno
70201	070201	7	702	Warnes
70202	070202	7	702	Okinawa Uno
70301	070301	7	703	San Ignacio de Velasco
70302	070302	7	703	San Miguel de Velasco
70303	070303	7	703	San Rafael de Velasco
70401	070401	7	704	Buena Vista
70402	070402	7	704	San Carlos
70403	070403	7	704	Villa Yapacaní
70404	070404	7	704	San Juan de Yapacaní
70501	070501	7	705	San José de Chiquitos
70502	070502	7	705	Pailón
70503	070503	7	705	Roboré
70601	071201	7	706	San Matías
70701	071401	7	707	Puerto Suárez
70702	071402	7	707	Puerto Quijarro
70703	071403	7	707	El Carmen Rivero Tórrez
70801	071301	7	708	Comarapa
70802	071302	7	708	Saipina
70901	070901	7	709	Samaipata
70902	070902	7	709	Pampagrande
70903	070903	7	709	Mairana
70904	070904	7	709	Quirusillas
71001	071001	7	710	Montero
71002	071002	7	710	General Saavedra
71003	071003	7	710	Mineros
71004	071004	7	710	Fernández Alonso
71005	071005	7	710	San Pedro
71101	071101	7	711	Concepción
71102	071102	7	711	San Javier
71103	071103	7	711	San Ramón
71104	071104	7	711	San Julián
71105	071105	7	711	San Antonio de Lomerío
71106	071106	7	711	Cuatro Cañadas
71201	070801	7	712	Vallegrande
71202	070802	7	712	El Trigal
71203	070803	7	712	Moro Moro
71204	070804	7	712	Postrervalle
71205	070805	7	712	Pucará
71301	071501	7	713	Ascensión de Guarayos
71302	071502	7	713	Urubichá
71303	071503	7	713	El Puente
71601	070601	7	716	Portachuelo
71602	070602	7	716	Santa Rosa del Sara
71603	070603	7	716	Colpa Bélgica
71701	070701	7	717	Lagunillas
71702	070702	7	717	Charagua
71703	070703	7	717	Cabezas
71704	070704	7	717	Cuevo
71705	070705	7	717	Gutiérrez (Kereimba Iyambae)
71706	070706	7	717	Camiri
71707	070707	7	717	Boyuibe
80101	080101	8	801	Trinidad
80102	080102	8	801	San Javier
80201	080201	8	802	Riberalta
80202	080202	8	802	Guayaramerín
80301	080301	8	803	Reyes
80302	080302	8	803	San Borja
80303	080303	8	803	Santa Rosa
80304	080304	8	803	Rurrenabaque
80401	080401	8	804	Santa Ana del Yacuma
80402	080402	8	804	Exaltación
80501	080501	8	805	San Ignacio de Moxos
80601	080601	8	806	Loreto
80602	080602	8	806	San Andrés
80701	080701	8	807	San Joaquín
80702	080702	8	807	San Ramón
80703	080703	8	807	Puerto Siles
80801	080801	8	808	Magdalena
80802	080802	8	808	Baures
80803	080803	8	808	Huacaraje
90101	090101	9	901	Cobija
90102	090102	9	901	Porvenir
90103	090103	9	901	Bolpebra
90104	090104	9	901	Bella Flor
90201	090201	9	902	Puerto Rico
90202	090202	9	902	San Pedro
90203	090203	9	902	Filadelfia
90301	090301	9	903	Puerto Gonzalo Moreno
90302	090302	9	903	San Lorenzo
90303	090303	9	903	Sena
90401	090401	9	904	Santa Rosa del Abuná
90402	090402	9	904	Ingavi
90501	090501	9	905	Nueva Esperanza
90502	090502	9	905	Villa Nueva
90503	090503	9	905	Santos Mercado
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
-- Data for Name: aplicacion; Type: TABLE DATA; Schema: usuarios; Owner: sinagersat
--

COPY usuarios.aplicacion (id_aplicacion, codigo, nombre, descripcion, activo) FROM stdin;
1	EDAN	Evaluacion de Danos y Analisis de Necesidades	Formulario EDAN - Evaluacion de Danos	t
2	RIDA	Registro de Informacion de Danos y Afectados	Sistema RIDA (futuro)	t
3	SINB	Sistema de Informacion de Necesidades Basicas	Sistema SINB (futuro)	t
\.


--
-- Data for Name: auditoria; Type: TABLE DATA; Schema: usuarios; Owner: sinagersat
--

COPY usuarios.auditoria (id_auditoria, id_usuario, id_aplicacion, accion, detalle, ip_origen, fecha) FROM stdin;
\.


--
-- Data for Name: permiso_aplicacion; Type: TABLE DATA; Schema: usuarios; Owner: sinagersat
--

COPY usuarios.permiso_aplicacion (id_permiso, id_rol, id_aplicacion) FROM stdin;
1	1	1
2	2	1
3	1	2
4	2	2
5	1	3
6	2	3
7	3	1
8	4	1
\.


--
-- Data for Name: reset_contrasena; Type: TABLE DATA; Schema: usuarios; Owner: sinagersat
--

COPY usuarios.reset_contrasena (id_reset, id_usuario, token, usado, fecha_solicitud, fecha_expiracion, ip_origen) FROM stdin;
\.


--
-- Data for Name: rol; Type: TABLE DATA; Schema: usuarios; Owner: sinagersat
--

COPY usuarios.rol (id_rol, nombre, descripcion, jerarquia) FROM stdin;
1	superadmin	Acceso total a todos los sistemas y gestion de usuarios	5
2	admin	Gestiona usuarios y datos de su sistema	4
3	encuestador	Carga y edita formularios propios	2
4	visor	Solo lectura en todos los modulos	1
\.


--
-- Data for Name: sesion; Type: TABLE DATA; Schema: usuarios; Owner: sinagersat
--

COPY usuarios.sesion (id_sesion, id_usuario, token, fecha_inicio, fecha_expiracion, ip_origen, activo) FROM stdin;
\.


--
-- Data for Name: usuario; Type: TABLE DATA; Schema: usuarios; Owner: sinagersat
--

COPY usuarios.usuario (id_usuario, usuario, email, contrasena_hash, nombre_completo, cargo, telefono, activo, intentos_fallidos, bloqueado_hasta, debe_cambiar_contrasena, ultimo_acceso, fecha_creacion, creado_por, fecha_actualizacion) FROM stdin;
1	admin	admin@sinagersat.gob.bo	$2b$12$LJ3m4ys3Lg3YOKqGULXN4eBm1XBq.5yzFQqY3Y5m5m5m5m5m5m5u	Administrador del Sistema	Administrador	\N	t	0	\N	f	\N	2026-07-16 14:36:04.546695	\N	2026-07-16 14:36:04.546695
\.


--
-- Data for Name: usuario_rol; Type: TABLE DATA; Schema: usuarios; Owner: sinagersat
--

COPY usuarios.usuario_rol (id_usuario, id_rol) FROM stdin;
1	1
\.


--
-- Name: catalogo_ayuda_humanitaria_id_ayuda_humanitaria_seq; Type: SEQUENCE SET; Schema: edan; Owner: postgres
--

SELECT pg_catalog.setval('edan.catalogo_ayuda_humanitaria_id_ayuda_humanitaria_seq', 9, true);


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

SELECT pg_catalog.setval('edan.edan_id_edan_seq', 1, false);


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
-- Name: aplicacion_id_aplicacion_seq; Type: SEQUENCE SET; Schema: usuarios; Owner: sinagersat
--

SELECT pg_catalog.setval('usuarios.aplicacion_id_aplicacion_seq', 3, true);


--
-- Name: auditoria_id_auditoria_seq; Type: SEQUENCE SET; Schema: usuarios; Owner: sinagersat
--

SELECT pg_catalog.setval('usuarios.auditoria_id_auditoria_seq', 1, false);


--
-- Name: permiso_aplicacion_id_permiso_seq; Type: SEQUENCE SET; Schema: usuarios; Owner: sinagersat
--

SELECT pg_catalog.setval('usuarios.permiso_aplicacion_id_permiso_seq', 8, true);


--
-- Name: reset_contrasena_id_reset_seq; Type: SEQUENCE SET; Schema: usuarios; Owner: sinagersat
--

SELECT pg_catalog.setval('usuarios.reset_contrasena_id_reset_seq', 1, false);


--
-- Name: rol_id_rol_seq; Type: SEQUENCE SET; Schema: usuarios; Owner: sinagersat
--

SELECT pg_catalog.setval('usuarios.rol_id_rol_seq', 4, true);


--
-- Name: sesion_id_sesion_seq; Type: SEQUENCE SET; Schema: usuarios; Owner: sinagersat
--

SELECT pg_catalog.setval('usuarios.sesion_id_sesion_seq', 1, false);


--
-- Name: usuario_id_usuario_seq; Type: SEQUENCE SET; Schema: usuarios; Owner: sinagersat
--

SELECT pg_catalog.setval('usuarios.usuario_id_usuario_seq', 1, true);


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
-- Name: aplicacion aplicacion_codigo_key; Type: CONSTRAINT; Schema: usuarios; Owner: sinagersat
--

ALTER TABLE ONLY usuarios.aplicacion
    ADD CONSTRAINT aplicacion_codigo_key UNIQUE (codigo);


--
-- Name: aplicacion aplicacion_pkey; Type: CONSTRAINT; Schema: usuarios; Owner: sinagersat
--

ALTER TABLE ONLY usuarios.aplicacion
    ADD CONSTRAINT aplicacion_pkey PRIMARY KEY (id_aplicacion);


--
-- Name: auditoria auditoria_pkey; Type: CONSTRAINT; Schema: usuarios; Owner: sinagersat
--

ALTER TABLE ONLY usuarios.auditoria
    ADD CONSTRAINT auditoria_pkey PRIMARY KEY (id_auditoria);


--
-- Name: permiso_aplicacion permiso_aplicacion_id_rol_id_aplicacion_key; Type: CONSTRAINT; Schema: usuarios; Owner: sinagersat
--

ALTER TABLE ONLY usuarios.permiso_aplicacion
    ADD CONSTRAINT permiso_aplicacion_id_rol_id_aplicacion_key UNIQUE (id_rol, id_aplicacion);


--
-- Name: permiso_aplicacion permiso_aplicacion_pkey; Type: CONSTRAINT; Schema: usuarios; Owner: sinagersat
--

ALTER TABLE ONLY usuarios.permiso_aplicacion
    ADD CONSTRAINT permiso_aplicacion_pkey PRIMARY KEY (id_permiso);


--
-- Name: reset_contrasena reset_contrasena_pkey; Type: CONSTRAINT; Schema: usuarios; Owner: sinagersat
--

ALTER TABLE ONLY usuarios.reset_contrasena
    ADD CONSTRAINT reset_contrasena_pkey PRIMARY KEY (id_reset);


--
-- Name: reset_contrasena reset_contrasena_token_key; Type: CONSTRAINT; Schema: usuarios; Owner: sinagersat
--

ALTER TABLE ONLY usuarios.reset_contrasena
    ADD CONSTRAINT reset_contrasena_token_key UNIQUE (token);


--
-- Name: rol rol_nombre_key; Type: CONSTRAINT; Schema: usuarios; Owner: sinagersat
--

ALTER TABLE ONLY usuarios.rol
    ADD CONSTRAINT rol_nombre_key UNIQUE (nombre);


--
-- Name: rol rol_pkey; Type: CONSTRAINT; Schema: usuarios; Owner: sinagersat
--

ALTER TABLE ONLY usuarios.rol
    ADD CONSTRAINT rol_pkey PRIMARY KEY (id_rol);


--
-- Name: sesion sesion_pkey; Type: CONSTRAINT; Schema: usuarios; Owner: sinagersat
--

ALTER TABLE ONLY usuarios.sesion
    ADD CONSTRAINT sesion_pkey PRIMARY KEY (id_sesion);


--
-- Name: sesion sesion_token_key; Type: CONSTRAINT; Schema: usuarios; Owner: sinagersat
--

ALTER TABLE ONLY usuarios.sesion
    ADD CONSTRAINT sesion_token_key UNIQUE (token);


--
-- Name: usuario usuario_email_key; Type: CONSTRAINT; Schema: usuarios; Owner: sinagersat
--

ALTER TABLE ONLY usuarios.usuario
    ADD CONSTRAINT usuario_email_key UNIQUE (email);


--
-- Name: usuario usuario_pkey; Type: CONSTRAINT; Schema: usuarios; Owner: sinagersat
--

ALTER TABLE ONLY usuarios.usuario
    ADD CONSTRAINT usuario_pkey PRIMARY KEY (id_usuario);


--
-- Name: usuario_rol usuario_rol_pkey; Type: CONSTRAINT; Schema: usuarios; Owner: sinagersat
--

ALTER TABLE ONLY usuarios.usuario_rol
    ADD CONSTRAINT usuario_rol_pkey PRIMARY KEY (id_usuario, id_rol);


--
-- Name: usuario usuario_usuario_key; Type: CONSTRAINT; Schema: usuarios; Owner: sinagersat
--

ALTER TABLE ONLY usuarios.usuario
    ADD CONSTRAINT usuario_usuario_key UNIQUE (usuario);


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
-- Name: idx_edan_salud_necesidades_edan; Type: INDEX; Schema: edan; Owner: postgres
--

CREATE INDEX idx_edan_salud_necesidades_edan ON edan.edan_salud_necesidades USING btree (id_edan);


--
-- Name: idx_edan_servicio_basico_edan; Type: INDEX; Schema: edan; Owner: postgres
--

CREATE INDEX idx_edan_servicio_basico_edan ON edan.edan_servicio_basico USING btree (id_edan);


--
-- Name: idx_edan_tipo_evento_edan; Type: INDEX; Schema: edan; Owner: postgres
--

CREATE INDEX idx_edan_tipo_evento_edan ON edan.edan_tipo_evento USING btree (id_edan);


--
-- Name: idx_edan_vivienda_edan; Type: INDEX; Schema: edan; Owner: postgres
--

CREATE INDEX idx_edan_vivienda_edan ON edan.edan_vivienda USING btree (id_edan);


--
-- Name: idx_municipio_dep; Type: INDEX; Schema: shared; Owner: postgres
--

CREATE INDEX idx_municipio_dep ON shared.municipio USING btree (id_departamento);


--
-- Name: idx_municipio_prov; Type: INDEX; Schema: shared; Owner: postgres
--

CREATE INDEX idx_municipio_prov ON shared.municipio USING btree (id_provincia);


--
-- Name: idx_provincia_dep; Type: INDEX; Schema: shared; Owner: postgres
--

CREATE INDEX idx_provincia_dep ON shared.provincia USING btree (id_departamento);


--
-- Name: edan_agricultura edan_agricultura_id_edan_fkey; Type: FK CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_agricultura
    ADD CONSTRAINT edan_agricultura_id_edan_fkey FOREIGN KEY (id_edan) REFERENCES edan.edan(id_edan) ON DELETE CASCADE;


--
-- Name: edan_ayuda_humanitaria edan_ayuda_humanitaria_id_ayuda_humanitaria_fkey; Type: FK CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_ayuda_humanitaria
    ADD CONSTRAINT edan_ayuda_humanitaria_id_ayuda_humanitaria_fkey FOREIGN KEY (id_ayuda_humanitaria) REFERENCES edan.ayuda_humanitaria(id_ayuda_humanitaria);


--
-- Name: edan_ayuda_humanitaria edan_ayuda_humanitaria_id_edan_fkey; Type: FK CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_ayuda_humanitaria
    ADD CONSTRAINT edan_ayuda_humanitaria_id_edan_fkey FOREIGN KEY (id_edan) REFERENCES edan.edan(id_edan) ON DELETE CASCADE;


--
-- Name: edan_comunidad edan_comunidad_id_edan_fkey; Type: FK CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_comunidad
    ADD CONSTRAINT edan_comunidad_id_edan_fkey FOREIGN KEY (id_edan) REFERENCES edan.edan(id_edan) ON DELETE CASCADE;


--
-- Name: edan_educacion_afectacion edan_educacion_afectacion_id_edan_fkey; Type: FK CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_educacion_afectacion
    ADD CONSTRAINT edan_educacion_afectacion_id_edan_fkey FOREIGN KEY (id_edan) REFERENCES edan.edan(id_edan) ON DELETE CASCADE;


--
-- Name: edan_educacion_afectacion edan_educacion_afectacion_id_educacion_dano_fkey; Type: FK CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_educacion_afectacion
    ADD CONSTRAINT edan_educacion_afectacion_id_educacion_dano_fkey FOREIGN KEY (id_educacion_dano) REFERENCES edan.edan_educacion_dano(id_educacion_dano) ON DELETE CASCADE;


--
-- Name: edan_educacion_dano edan_educacion_dano_id_edan_fkey; Type: FK CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_educacion_dano
    ADD CONSTRAINT edan_educacion_dano_id_edan_fkey FOREIGN KEY (id_edan) REFERENCES edan.edan(id_edan) ON DELETE CASCADE;


--
-- Name: edan edan_id_departamento_fkey; Type: FK CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan
    ADD CONSTRAINT edan_id_departamento_fkey FOREIGN KEY (id_departamento) REFERENCES shared.departamento(id);


--
-- Name: edan edan_id_municipio_fkey; Type: FK CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan
    ADD CONSTRAINT edan_id_municipio_fkey FOREIGN KEY (id_municipio) REFERENCES shared.municipio(id);


--
-- Name: edan_infraestructura_productiva edan_infraestructura_productiva_id_edan_fkey; Type: FK CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_infraestructura_productiva
    ADD CONSTRAINT edan_infraestructura_productiva_id_edan_fkey FOREIGN KEY (id_edan) REFERENCES edan.edan(id_edan) ON DELETE CASCADE;


--
-- Name: edan_infraestructura_publica edan_infraestructura_publica_id_edan_fkey; Type: FK CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_infraestructura_publica
    ADD CONSTRAINT edan_infraestructura_publica_id_edan_fkey FOREIGN KEY (id_edan) REFERENCES edan.edan(id_edan) ON DELETE CASCADE;


--
-- Name: edan_infraestructura_vial edan_infraestructura_vial_id_edan_fkey; Type: FK CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_infraestructura_vial
    ADD CONSTRAINT edan_infraestructura_vial_id_edan_fkey FOREIGN KEY (id_edan) REFERENCES edan.edan(id_edan) ON DELETE CASCADE;


--
-- Name: edan_pecuaria edan_pecuaria_id_edan_fkey; Type: FK CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_pecuaria
    ADD CONSTRAINT edan_pecuaria_id_edan_fkey FOREIGN KEY (id_edan) REFERENCES edan.edan(id_edan) ON DELETE CASCADE;


--
-- Name: edan_poblacion_grupo edan_poblacion_grupo_id_edan_fkey; Type: FK CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_poblacion_grupo
    ADD CONSTRAINT edan_poblacion_grupo_id_edan_fkey FOREIGN KEY (id_edan) REFERENCES edan.edan(id_edan) ON DELETE CASCADE;


--
-- Name: edan_poblacion_grupo edan_poblacion_grupo_id_grupo_etario_fkey; Type: FK CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_poblacion_grupo
    ADD CONSTRAINT edan_poblacion_grupo_id_grupo_etario_fkey FOREIGN KEY (id_grupo_etario) REFERENCES edan.grupo_etario(id_grupo_etario);


--
-- Name: edan_primera_respuesta edan_primera_respuesta_id_edan_fkey; Type: FK CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_primera_respuesta
    ADD CONSTRAINT edan_primera_respuesta_id_edan_fkey FOREIGN KEY (id_edan) REFERENCES edan.edan(id_edan) ON DELETE CASCADE;


--
-- Name: edan_proteccion edan_proteccion_id_categoria_proteccion_fkey; Type: FK CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_proteccion
    ADD CONSTRAINT edan_proteccion_id_categoria_proteccion_fkey FOREIGN KEY (id_categoria_proteccion) REFERENCES edan.categoria_proteccion(id_categoria_proteccion);


--
-- Name: edan_proteccion edan_proteccion_id_edan_fkey; Type: FK CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_proteccion
    ADD CONSTRAINT edan_proteccion_id_edan_fkey FOREIGN KEY (id_edan) REFERENCES edan.edan(id_edan) ON DELETE CASCADE;


--
-- Name: edan_salud_establecimiento edan_salud_establecimiento_id_edan_fkey; Type: FK CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_salud_establecimiento
    ADD CONSTRAINT edan_salud_establecimiento_id_edan_fkey FOREIGN KEY (id_edan) REFERENCES edan.edan(id_edan) ON DELETE CASCADE;


--
-- Name: edan_salud_necesidades edan_salud_necesidades_id_edan_fkey; Type: FK CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_salud_necesidades
    ADD CONSTRAINT edan_salud_necesidades_id_edan_fkey FOREIGN KEY (id_edan) REFERENCES edan.edan(id_edan) ON DELETE CASCADE;


--
-- Name: edan_servicio_basico edan_servicio_basico_id_edan_fkey; Type: FK CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_servicio_basico
    ADD CONSTRAINT edan_servicio_basico_id_edan_fkey FOREIGN KEY (id_edan) REFERENCES edan.edan(id_edan) ON DELETE CASCADE;


--
-- Name: edan_servicio_basico edan_servicio_basico_id_servicio_basico_fkey; Type: FK CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_servicio_basico
    ADD CONSTRAINT edan_servicio_basico_id_servicio_basico_fkey FOREIGN KEY (id_servicio_basico) REFERENCES edan.servicio_basico(id_servicio_basico);


--
-- Name: edan_tipo_evento edan_tipo_evento_id_edan_fkey; Type: FK CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_tipo_evento
    ADD CONSTRAINT edan_tipo_evento_id_edan_fkey FOREIGN KEY (id_edan) REFERENCES edan.edan(id_edan) ON DELETE CASCADE;


--
-- Name: edan_tipo_evento edan_tipo_evento_id_tipo_evento_fkey; Type: FK CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_tipo_evento
    ADD CONSTRAINT edan_tipo_evento_id_tipo_evento_fkey FOREIGN KEY (id_tipo_evento) REFERENCES edan.tipo_evento(id_tipo_evento);


--
-- Name: edan edan_usuario_registro_fkey; Type: FK CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan
    ADD CONSTRAINT edan_usuario_registro_fkey FOREIGN KEY (usuario_registro) REFERENCES usuarios.usuario(id_usuario);


--
-- Name: edan_vivienda edan_vivienda_id_edan_fkey; Type: FK CONSTRAINT; Schema: edan; Owner: postgres
--

ALTER TABLE ONLY edan.edan_vivienda
    ADD CONSTRAINT edan_vivienda_id_edan_fkey FOREIGN KEY (id_edan) REFERENCES edan.edan(id_edan) ON DELETE CASCADE;


--
-- Name: municipio catalogo_municipio_id_departamento_fkey; Type: FK CONSTRAINT; Schema: shared; Owner: postgres
--

ALTER TABLE ONLY shared.municipio
    ADD CONSTRAINT catalogo_municipio_id_departamento_fkey FOREIGN KEY (id_departamento) REFERENCES shared.departamento(id);


--
-- Name: provincia catalogo_provincia_id_departamento_fkey; Type: FK CONSTRAINT; Schema: shared; Owner: postgres
--

ALTER TABLE ONLY shared.provincia
    ADD CONSTRAINT catalogo_provincia_id_departamento_fkey FOREIGN KEY (id_departamento) REFERENCES shared.departamento(id);


--
-- Name: municipio municipio_id_provincia_fkey; Type: FK CONSTRAINT; Schema: shared; Owner: postgres
--

ALTER TABLE ONLY shared.municipio
    ADD CONSTRAINT municipio_id_provincia_fkey FOREIGN KEY (id_provincia) REFERENCES shared.provincia(id);


--
-- Name: auditoria auditoria_id_aplicacion_fkey; Type: FK CONSTRAINT; Schema: usuarios; Owner: sinagersat
--

ALTER TABLE ONLY usuarios.auditoria
    ADD CONSTRAINT auditoria_id_aplicacion_fkey FOREIGN KEY (id_aplicacion) REFERENCES usuarios.aplicacion(id_aplicacion);


--
-- Name: auditoria auditoria_id_usuario_fkey; Type: FK CONSTRAINT; Schema: usuarios; Owner: sinagersat
--

ALTER TABLE ONLY usuarios.auditoria
    ADD CONSTRAINT auditoria_id_usuario_fkey FOREIGN KEY (id_usuario) REFERENCES usuarios.usuario(id_usuario);


--
-- Name: permiso_aplicacion permiso_aplicacion_id_aplicacion_fkey; Type: FK CONSTRAINT; Schema: usuarios; Owner: sinagersat
--

ALTER TABLE ONLY usuarios.permiso_aplicacion
    ADD CONSTRAINT permiso_aplicacion_id_aplicacion_fkey FOREIGN KEY (id_aplicacion) REFERENCES usuarios.aplicacion(id_aplicacion) ON DELETE CASCADE;


--
-- Name: permiso_aplicacion permiso_aplicacion_id_rol_fkey; Type: FK CONSTRAINT; Schema: usuarios; Owner: sinagersat
--

ALTER TABLE ONLY usuarios.permiso_aplicacion
    ADD CONSTRAINT permiso_aplicacion_id_rol_fkey FOREIGN KEY (id_rol) REFERENCES usuarios.rol(id_rol) ON DELETE CASCADE;


--
-- Name: reset_contrasena reset_contrasena_id_usuario_fkey; Type: FK CONSTRAINT; Schema: usuarios; Owner: sinagersat
--

ALTER TABLE ONLY usuarios.reset_contrasena
    ADD CONSTRAINT reset_contrasena_id_usuario_fkey FOREIGN KEY (id_usuario) REFERENCES usuarios.usuario(id_usuario) ON DELETE CASCADE;


--
-- Name: sesion sesion_id_usuario_fkey; Type: FK CONSTRAINT; Schema: usuarios; Owner: sinagersat
--

ALTER TABLE ONLY usuarios.sesion
    ADD CONSTRAINT sesion_id_usuario_fkey FOREIGN KEY (id_usuario) REFERENCES usuarios.usuario(id_usuario) ON DELETE CASCADE;


--
-- Name: usuario usuario_creado_por_fkey; Type: FK CONSTRAINT; Schema: usuarios; Owner: sinagersat
--

ALTER TABLE ONLY usuarios.usuario
    ADD CONSTRAINT usuario_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES usuarios.usuario(id_usuario);


--
-- Name: usuario_rol usuario_rol_id_rol_fkey; Type: FK CONSTRAINT; Schema: usuarios; Owner: sinagersat
--

ALTER TABLE ONLY usuarios.usuario_rol
    ADD CONSTRAINT usuario_rol_id_rol_fkey FOREIGN KEY (id_rol) REFERENCES usuarios.rol(id_rol) ON DELETE CASCADE;


--
-- Name: usuario_rol usuario_rol_id_usuario_fkey; Type: FK CONSTRAINT; Schema: usuarios; Owner: sinagersat
--

ALTER TABLE ONLY usuarios.usuario_rol
    ADD CONSTRAINT usuario_rol_id_usuario_fkey FOREIGN KEY (id_usuario) REFERENCES usuarios.usuario(id_usuario) ON DELETE CASCADE;


--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: pg_database_owner
--

GRANT ALL ON SCHEMA public TO sinagersat;


--
-- Name: TABLE ayuda_humanitaria; Type: ACL; Schema: edan; Owner: postgres
--

GRANT ALL ON TABLE edan.ayuda_humanitaria TO sinagersat;


--
-- Name: SEQUENCE catalogo_ayuda_humanitaria_id_ayuda_humanitaria_seq; Type: ACL; Schema: edan; Owner: postgres
--

GRANT ALL ON SEQUENCE edan.catalogo_ayuda_humanitaria_id_ayuda_humanitaria_seq TO sinagersat;


--
-- Name: TABLE categoria_proteccion; Type: ACL; Schema: edan; Owner: postgres
--

GRANT ALL ON TABLE edan.categoria_proteccion TO sinagersat;


--
-- Name: SEQUENCE catalogo_categoria_proteccion_id_categoria_proteccion_seq; Type: ACL; Schema: edan; Owner: postgres
--

GRANT ALL ON SEQUENCE edan.catalogo_categoria_proteccion_id_categoria_proteccion_seq TO sinagersat;


--
-- Name: TABLE grupo_etario; Type: ACL; Schema: edan; Owner: postgres
--

GRANT ALL ON TABLE edan.grupo_etario TO sinagersat;


--
-- Name: SEQUENCE catalogo_grupo_etario_id_grupo_etario_seq; Type: ACL; Schema: edan; Owner: postgres
--

GRANT ALL ON SEQUENCE edan.catalogo_grupo_etario_id_grupo_etario_seq TO sinagersat;


--
-- Name: TABLE servicio_basico; Type: ACL; Schema: edan; Owner: postgres
--

GRANT ALL ON TABLE edan.servicio_basico TO sinagersat;


--
-- Name: SEQUENCE catalogo_servicio_basico_id_servicio_basico_seq; Type: ACL; Schema: edan; Owner: postgres
--

GRANT ALL ON SEQUENCE edan.catalogo_servicio_basico_id_servicio_basico_seq TO sinagersat;


--
-- Name: TABLE tipo_evento; Type: ACL; Schema: edan; Owner: postgres
--

GRANT ALL ON TABLE edan.tipo_evento TO sinagersat;


--
-- Name: SEQUENCE catalogo_tipo_evento_id_tipo_evento_seq; Type: ACL; Schema: edan; Owner: postgres
--

GRANT ALL ON SEQUENCE edan.catalogo_tipo_evento_id_tipo_evento_seq TO sinagersat;


--
-- Name: TABLE edan; Type: ACL; Schema: edan; Owner: postgres
--

GRANT ALL ON TABLE edan.edan TO sinagersat;


--
-- Name: TABLE edan_agricultura; Type: ACL; Schema: edan; Owner: postgres
--

GRANT ALL ON TABLE edan.edan_agricultura TO sinagersat;


--
-- Name: SEQUENCE edan_agricultura_id_agricultura_seq; Type: ACL; Schema: edan; Owner: postgres
--

GRANT ALL ON SEQUENCE edan.edan_agricultura_id_agricultura_seq TO sinagersat;


--
-- Name: TABLE edan_ayuda_humanitaria; Type: ACL; Schema: edan; Owner: postgres
--

GRANT ALL ON TABLE edan.edan_ayuda_humanitaria TO sinagersat;


--
-- Name: SEQUENCE edan_ayuda_humanitaria_id_ayuda_edan_seq; Type: ACL; Schema: edan; Owner: postgres
--

GRANT ALL ON SEQUENCE edan.edan_ayuda_humanitaria_id_ayuda_edan_seq TO sinagersat;


--
-- Name: TABLE edan_comunidad; Type: ACL; Schema: edan; Owner: postgres
--

GRANT ALL ON TABLE edan.edan_comunidad TO sinagersat;


--
-- Name: SEQUENCE edan_comunidad_id_comunidad_seq; Type: ACL; Schema: edan; Owner: postgres
--

GRANT ALL ON SEQUENCE edan.edan_comunidad_id_comunidad_seq TO sinagersat;


--
-- Name: TABLE edan_educacion_afectacion; Type: ACL; Schema: edan; Owner: postgres
--

GRANT ALL ON TABLE edan.edan_educacion_afectacion TO sinagersat;


--
-- Name: SEQUENCE edan_educacion_afectacion_id_educacion_afectacion_seq; Type: ACL; Schema: edan; Owner: postgres
--

GRANT ALL ON SEQUENCE edan.edan_educacion_afectacion_id_educacion_afectacion_seq TO sinagersat;


--
-- Name: TABLE edan_educacion_dano; Type: ACL; Schema: edan; Owner: postgres
--

GRANT ALL ON TABLE edan.edan_educacion_dano TO sinagersat;


--
-- Name: SEQUENCE edan_educacion_dano_id_educacion_dano_seq; Type: ACL; Schema: edan; Owner: postgres
--

GRANT ALL ON SEQUENCE edan.edan_educacion_dano_id_educacion_dano_seq TO sinagersat;


--
-- Name: SEQUENCE edan_id_edan_seq; Type: ACL; Schema: edan; Owner: postgres
--

GRANT ALL ON SEQUENCE edan.edan_id_edan_seq TO sinagersat;


--
-- Name: TABLE edan_infraestructura_productiva; Type: ACL; Schema: edan; Owner: postgres
--

GRANT ALL ON TABLE edan.edan_infraestructura_productiva TO sinagersat;


--
-- Name: SEQUENCE edan_infraestructura_productiva_id_infra_productiva_seq; Type: ACL; Schema: edan; Owner: postgres
--

GRANT ALL ON SEQUENCE edan.edan_infraestructura_productiva_id_infra_productiva_seq TO sinagersat;


--
-- Name: TABLE edan_infraestructura_publica; Type: ACL; Schema: edan; Owner: postgres
--

GRANT ALL ON TABLE edan.edan_infraestructura_publica TO sinagersat;


--
-- Name: SEQUENCE edan_infraestructura_publica_id_infraestructura_publica_seq; Type: ACL; Schema: edan; Owner: postgres
--

GRANT ALL ON SEQUENCE edan.edan_infraestructura_publica_id_infraestructura_publica_seq TO sinagersat;


--
-- Name: TABLE edan_infraestructura_vial; Type: ACL; Schema: edan; Owner: postgres
--

GRANT ALL ON TABLE edan.edan_infraestructura_vial TO sinagersat;


--
-- Name: SEQUENCE edan_infraestructura_vial_id_infraestructura_vial_seq; Type: ACL; Schema: edan; Owner: postgres
--

GRANT ALL ON SEQUENCE edan.edan_infraestructura_vial_id_infraestructura_vial_seq TO sinagersat;


--
-- Name: TABLE edan_pecuaria; Type: ACL; Schema: edan; Owner: postgres
--

GRANT ALL ON TABLE edan.edan_pecuaria TO sinagersat;


--
-- Name: SEQUENCE edan_pecuaria_id_pecuaria_seq; Type: ACL; Schema: edan; Owner: postgres
--

GRANT ALL ON SEQUENCE edan.edan_pecuaria_id_pecuaria_seq TO sinagersat;


--
-- Name: TABLE edan_poblacion_grupo; Type: ACL; Schema: edan; Owner: postgres
--

GRANT ALL ON TABLE edan.edan_poblacion_grupo TO sinagersat;


--
-- Name: SEQUENCE edan_poblacion_grupo_id_poblacion_grupo_seq; Type: ACL; Schema: edan; Owner: postgres
--

GRANT ALL ON SEQUENCE edan.edan_poblacion_grupo_id_poblacion_grupo_seq TO sinagersat;


--
-- Name: TABLE edan_primera_respuesta; Type: ACL; Schema: edan; Owner: postgres
--

GRANT ALL ON TABLE edan.edan_primera_respuesta TO sinagersat;


--
-- Name: SEQUENCE edan_primera_respuesta_id_primera_respuesta_seq; Type: ACL; Schema: edan; Owner: postgres
--

GRANT ALL ON SEQUENCE edan.edan_primera_respuesta_id_primera_respuesta_seq TO sinagersat;


--
-- Name: TABLE edan_proteccion; Type: ACL; Schema: edan; Owner: postgres
--

GRANT ALL ON TABLE edan.edan_proteccion TO sinagersat;


--
-- Name: SEQUENCE edan_proteccion_id_proteccion_seq; Type: ACL; Schema: edan; Owner: postgres
--

GRANT ALL ON SEQUENCE edan.edan_proteccion_id_proteccion_seq TO sinagersat;


--
-- Name: TABLE edan_salud_establecimiento; Type: ACL; Schema: edan; Owner: postgres
--

GRANT ALL ON TABLE edan.edan_salud_establecimiento TO sinagersat;


--
-- Name: SEQUENCE edan_salud_establecimiento_id_salud_establecimiento_seq; Type: ACL; Schema: edan; Owner: postgres
--

GRANT ALL ON SEQUENCE edan.edan_salud_establecimiento_id_salud_establecimiento_seq TO sinagersat;


--
-- Name: TABLE edan_salud_necesidades; Type: ACL; Schema: edan; Owner: postgres
--

GRANT ALL ON TABLE edan.edan_salud_necesidades TO sinagersat;


--
-- Name: SEQUENCE edan_salud_necesidades_id_salud_necesidad_seq; Type: ACL; Schema: edan; Owner: postgres
--

GRANT ALL ON SEQUENCE edan.edan_salud_necesidades_id_salud_necesidad_seq TO sinagersat;


--
-- Name: TABLE edan_servicio_basico; Type: ACL; Schema: edan; Owner: postgres
--

GRANT ALL ON TABLE edan.edan_servicio_basico TO sinagersat;


--
-- Name: SEQUENCE edan_servicio_basico_id_servicio_basico_edan_seq; Type: ACL; Schema: edan; Owner: postgres
--

GRANT ALL ON SEQUENCE edan.edan_servicio_basico_id_servicio_basico_edan_seq TO sinagersat;


--
-- Name: TABLE edan_tipo_evento; Type: ACL; Schema: edan; Owner: postgres
--

GRANT ALL ON TABLE edan.edan_tipo_evento TO sinagersat;


--
-- Name: SEQUENCE edan_tipo_evento_id_tipo_evento_edan_seq; Type: ACL; Schema: edan; Owner: postgres
--

GRANT ALL ON SEQUENCE edan.edan_tipo_evento_id_tipo_evento_edan_seq TO sinagersat;


--
-- Name: TABLE edan_vivienda; Type: ACL; Schema: edan; Owner: postgres
--

GRANT ALL ON TABLE edan.edan_vivienda TO sinagersat;


--
-- Name: SEQUENCE edan_vivienda_id_vivienda_seq; Type: ACL; Schema: edan; Owner: postgres
--

GRANT ALL ON SEQUENCE edan.edan_vivienda_id_vivienda_seq TO sinagersat;


--
-- Name: TABLE departamento; Type: ACL; Schema: shared; Owner: postgres
--

GRANT ALL ON TABLE shared.departamento TO sinagersat;


--
-- Name: TABLE municipio; Type: ACL; Schema: shared; Owner: postgres
--

GRANT ALL ON TABLE shared.municipio TO sinagersat;


--
-- Name: TABLE provincia; Type: ACL; Schema: shared; Owner: postgres
--

GRANT ALL ON TABLE shared.provincia TO sinagersat;


--
-- PostgreSQL database dump complete
--

\unrestrict f7LU5TBfUsTy1YmT2NbwXH2qlHa5r8Q9OJF5HZpdAKYBGdQm9gdH7GaJijEk6cb

