-- ============================================
-- BASE DE DATOS: EDAN (Evaluación de Daños y Análisis de Necesidades)
-- ============================================
--
-- ORDEN DE EJECUCIÓN:
--   1. Este archivo (crear_edan_db.sql)  → Crea esquema + catálogos básicos
--   2. insert_provincias_municipios.sql  → Carga geografía (dep/prov/mun INE)
--
-- Ejecutar como usuario con permisos de creación en PostgreSQL.
-- ============================================

-- ============================================
-- CATÁLOGOS GEOGRÁFICOS (códigos INE Bolivia)
-- ============================================
--
-- Codificación INE:
--   Departamento : DD       (2 dígitos)  PK = id (INTEGER), UNIQUE = codigo_ine
--   Provincia    : DDPP     (4 dígitos)  PK = id (INTEGER), UNIQUE = codigo_ine
--   Municipio    : DDPPMM   (6 dígitos)  PK = id (INTEGER), UNIQUE = codigo_ine
--
-- id = valor numérico de codigo_ine (sin ceros a la izquierda)
--   Ejemplo: codigo_ine '02' → id=2, '0214' → id=214, '021401' → id=21401

CREATE TABLE catalogo_departamento (
    id          INTEGER      PRIMARY KEY,
    codigo_ine  VARCHAR(2)   NOT NULL UNIQUE,
    nombre      VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE catalogo_provincia (
    id                  INTEGER      PRIMARY KEY,
    codigo_ine          VARCHAR(4)   NOT NULL UNIQUE,
    id_departamento     INTEGER      NOT NULL REFERENCES catalogo_departamento(id),
    nombre              VARCHAR(100) NOT NULL
);

CREATE TABLE catalogo_municipio (
    id                  INTEGER      PRIMARY KEY,
    codigo_ine          VARCHAR(6)   NOT NULL UNIQUE,
    id_departamento     INTEGER      NOT NULL REFERENCES catalogo_departamento(id),
    id_provincia        INTEGER      NOT NULL REFERENCES catalogo_provincia(id),
    nombre              VARCHAR(100) NOT NULL
);

-- ============================================
-- CATÁLOGOS DE FORMULARIO EDAN
-- ============================================

CREATE TABLE catalogo_tipo_evento (
    id_tipo_evento SERIAL PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE catalogo_grupo_etario (
    id_grupo_etario SERIAL PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL UNIQUE,
    orden INTEGER NOT NULL
);

CREATE TABLE catalogo_servicio_basico (
    id_servicio_basico SERIAL PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL UNIQUE,
    orden INTEGER NOT NULL
);

CREATE TABLE catalogo_categoria_proteccion (
    id_categoria_proteccion SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE,
    orden INTEGER NOT NULL
);

CREATE TABLE catalogo_ayuda_humanitaria (
    id_ayuda_humanitaria SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE,
    orden INTEGER NOT NULL
);

-- ============================================
-- DATOS INICIALES - CATÁLOGOS DE FORMULARIO
-- ============================================

INSERT INTO catalogo_tipo_evento (nombre) VALUES
    ('Inundación'),
    ('Riada'),
    ('Deslizamiento'),
    ('Helada'),
    ('Granizada'),
    ('Sequía'),
    ('Incendios'),
    ('Otros')
ON CONFLICT (nombre) DO NOTHING;

INSERT INTO catalogo_grupo_etario (nombre, orden) VALUES
    ('Niño(a) 0-5 años', 1),
    ('Escolar 6-18 años', 2),
    ('Adulto 19-60 años', 3),
    ('Adulto mayor 60+ años', 4)
ON CONFLICT (nombre) DO NOTHING;

INSERT INTO catalogo_servicio_basico (nombre, orden) VALUES
    ('Luz eléctrica', 1),
    ('Agua Potable', 2),
    ('Alcantarillado', 3),
    ('Gas domiciliario', 4),
    ('Telecomunicaciones', 5)
ON CONFLICT (nombre) DO NOTHING;

INSERT INTO catalogo_categoria_proteccion (nombre, orden) VALUES
    ('Niñas y Niños', 1),
    ('Adolescentes', 2),
    ('Mujeres Lactantes', 3),
    ('Mujeres Embarazadas', 4),
    ('Adultos Mayores', 5),
    ('Personas con Discapacidad', 6),
    ('Personas con Enfermedad Inhabilitante', 7)
ON CONFLICT (nombre) DO NOTHING;

INSERT INTO catalogo_ayuda_humanitaria (nombre, orden) VALUES
    ('Alimentos', 1),
    ('Prendas de Vestir', 2),
    ('Refugio y Vivienda', 3),
    ('Herramientas y Accesorios', 4),
    ('Ropa de Cama', 5),
    ('Almacenamiento de Agua', 6),
    ('Artículos de Higiene', 7),
    ('Baños', 8),
    ('Artículos de Cocina', 9)
ON CONFLICT (nombre) DO NOTHING;


-- ============================================
-- TABLA PADRE: EDAN
-- ============================================

CREATE TABLE edan (
    id_edan BIGSERIAL PRIMARY KEY,
    codigo_edan VARCHAR(30),

    -- Datos geográficos (FK por id numérico)
    id_departamento INTEGER REFERENCES catalogo_departamento(id),
    id_municipio    INTEGER REFERENCES catalogo_municipio(id),

    -- Datos generales
    nombre_alcalde VARCHAR(200),
    telefono_alcalde VARCHAR(30),
    fecha_llenado DATE,
    fecha_evento DATE,
    hora_evento TIME,
    localidades_afectadas INTEGER DEFAULT 0,

    -- Población general
    total_poblacion_afectada INTEGER DEFAULT 0,
    total_familias_afectadas INTEGER DEFAULT 0,
    total_familias_damnificadas INTEGER DEFAULT 0,

    -- Responsable del llenado
    nombre_responsable VARCHAR(200),
    cargo_responsable VARCHAR(100),
    telefono_responsable VARCHAR(30),
    email_responsable VARCHAR(150),

    -- Auditoría
    usuario_registro VARCHAR(50),
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- ============================================
-- SECCIÓN 2: POBLACIÓN - GRUPO ETARIO
-- ============================================

CREATE TABLE edan_poblacion_grupo (
    id_poblacion_grupo SERIAL PRIMARY KEY,
    id_edan BIGINT NOT NULL REFERENCES edan(id_edan) ON DELETE CASCADE,
    id_grupo_etario INTEGER NOT NULL REFERENCES catalogo_grupo_etario(id_grupo_etario),
    fallecidos INTEGER DEFAULT 0,
    heridos INTEGER DEFAULT 0,
    desaparecidos INTEGER DEFAULT 0,
    observaciones TEXT,
    UNIQUE(id_edan, id_grupo_etario)
);


-- ============================================
-- SECCIÓN 3.1: TIPO DE EVENTO (puente)
-- ============================================

CREATE TABLE edan_tipo_evento (
    id_tipo_evento_edan SERIAL PRIMARY KEY,
    id_edan BIGINT NOT NULL REFERENCES edan(id_edan) ON DELETE CASCADE,
    id_tipo_evento INTEGER NOT NULL REFERENCES catalogo_tipo_evento(id_tipo_evento),
    UNIQUE(id_edan, id_tipo_evento)
);


-- ============================================
-- SECCIÓN 3.3: NECESIDADES EN PRIMERA RESPUESTA
-- ============================================

CREATE TABLE edan_primera_respuesta (
    id_primera_respuesta SERIAL PRIMARY KEY,
    id_edan BIGINT NOT NULL REFERENCES edan(id_edan) ON DELETE CASCADE,
    busqueda_requerimiento BOOLEAN DEFAULT FALSE,
    busqueda_observaciones TEXT,
    salvamento_requerimiento BOOLEAN DEFAULT FALSE,
    salvamento_observaciones TEXT,
    evacuacion_requerimiento BOOLEAN DEFAULT FALSE,
    evacuacion_observaciones TEXT,
    otros_requerimiento BOOLEAN DEFAULT FALSE,
    otros_observaciones TEXT,
    observaciones_generales TEXT
);


-- ============================================
-- SECCIÓN 4.1: DAÑOS EN SERVICIOS DE SALUD
-- ============================================

CREATE TABLE edan_salud_establecimiento (
    id_salud_establecimiento SERIAL PRIMARY KEY,
    id_edan BIGINT NOT NULL REFERENCES edan(id_edan) ON DELETE CASCADE,
    nombre_establecimiento VARCHAR(200) NOT NULL,
    localidad_comunidad VARCHAR(200),
    nivel_atencion SMALLINT CHECK (nivel_atencion IN (1, 2, 3)),
    dano_parcial BOOLEAN DEFAULT FALSE,
    dano_total BOOLEAN DEFAULT FALSE,
    personal_medicos INTEGER DEFAULT 0,
    personal_enfermeras INTEGER DEFAULT 0,
    personal_otros INTEGER DEFAULT 0,
    observaciones TEXT
);


-- ============================================
-- SECCIÓN 4.2: NECESIDADES EN SALUD
-- ============================================

CREATE TABLE edan_salud_necesidades (
    id_salud_necesidad SERIAL PRIMARY KEY,
    id_edan BIGINT NOT NULL REFERENCES edan(id_edan) ON DELETE CASCADE,
    botiquin_personas INTEGER DEFAULT 0,
    otras_necesidades TEXT,
    observaciones TEXT
);


-- ============================================
-- SECCIÓN 5.1: DAÑOS EN INFRAESTRUCTURA VIAL
-- ============================================

CREATE TABLE edan_infraestructura_vial (
    id_infraestructura_vial SERIAL PRIMARY KEY,
    id_edan BIGINT NOT NULL REFERENCES edan(id_edan) ON DELETE CASCADE,
    via_acceso_puentes VARCHAR(200),
    tramo VARCHAR(200),
    localidad_origen VARCHAR(200),
    localidad_destino VARCHAR(200),
    dano_parcial_km DECIMAL(10,2) DEFAULT 0,
    dano_total_km DECIMAL(10,2) DEFAULT 0,
    necesidades_inmediatas TEXT,
    observaciones TEXT
);


-- ============================================
-- SECCIÓN 5.2: DAÑOS EN INFRAESTRUCTURA PÚBLICA
-- ============================================

CREATE TABLE edan_infraestructura_publica (
    id_infraestructura_publica SERIAL PRIMARY KEY,
    id_edan BIGINT NOT NULL REFERENCES edan(id_edan) ON DELETE CASCADE,
    localidad_comunidad VARCHAR(200),
    tipo_estructura VARCHAR(200),
    dano_parcial INTEGER DEFAULT 0,
    dano_total INTEGER DEFAULT 0,
    observaciones TEXT
);


-- ============================================
-- SECCIÓN 6: DAÑO EN SERVICIOS BÁSICOS
-- ============================================

CREATE TABLE edan_servicio_basico (
    id_servicio_basico_edan SERIAL PRIMARY KEY,
    id_edan BIGINT NOT NULL REFERENCES edan(id_edan) ON DELETE CASCADE,
    id_servicio_basico INTEGER NOT NULL REFERENCES catalogo_servicio_basico(id_servicio_basico),
    dano_parcial BOOLEAN DEFAULT FALSE,
    dano_total BOOLEAN DEFAULT FALSE,
    necesidades_inmediatas TEXT,
    observaciones TEXT,
    UNIQUE(id_edan, id_servicio_basico)
);


-- ============================================
-- SECCIÓN 7.1: DAÑOS EN UNIDADES EDUCATIVAS
-- ============================================

CREATE TABLE edan_educacion_dano (
    id_educacion_dano SERIAL PRIMARY KEY,
    id_edan BIGINT NOT NULL REFERENCES edan(id_edan) ON DELETE CASCADE,
    nombre_establecimiento VARCHAR(200) NOT NULL,
    comunidad VARCHAR(200),
    dano_parcial BOOLEAN DEFAULT FALSE,
    dano_total BOOLEAN DEFAULT FALSE,
    suspension_clases BOOLEAN DEFAULT FALSE,
    perdida_material BOOLEAN DEFAULT FALSE,
    funciona_albergue BOOLEAN DEFAULT FALSE,
    observaciones TEXT
);


-- ============================================
-- SECCIÓN 7.2: AFECTACIÓN EN EDUCACIÓN (por escuela)
-- ============================================

CREATE TABLE edan_educacion_afectacion (
    id_educacion_afectacion SERIAL PRIMARY KEY,
    id_edan BIGINT NOT NULL REFERENCES edan(id_edan) ON DELETE CASCADE,
    id_educacion_dano INTEGER REFERENCES edan_educacion_dano(id_educacion_dano) ON DELETE CASCADE,
    nombre_establecimiento VARCHAR(200) NOT NULL,
    estudiantes_afectados INTEGER DEFAULT 0,
    profesores_afectados INTEGER DEFAULT 0,
    administrativos_afectados INTEGER DEFAULT 0,
    total_afectados INTEGER DEFAULT 0,
    observaciones TEXT
);


-- ============================================
-- SECCIÓN 8: DAÑOS EN VIVIENDA
-- ============================================

CREATE TABLE edan_vivienda (
    id_vivienda SERIAL PRIMARY KEY,
    id_edan BIGINT NOT NULL REFERENCES edan(id_edan) ON DELETE CASCADE,
    comunidad VARCHAR(200),
    viviendas_dano_parcial INTEGER DEFAULT 0,
    viviendas_dano_total INTEGER DEFAULT 0,
    necesidades_inmediatas TEXT,
    observaciones TEXT
);


-- ============================================
-- SECCIÓN 9.1: DAÑOS EN AGRICULTURA
-- ============================================

CREATE TABLE edan_agricultura (
    id_agricultura SERIAL PRIMARY KEY,
    id_edan BIGINT NOT NULL REFERENCES edan(id_edan) ON DELETE CASCADE,
    tipo_cultivo VARCHAR(200),
    hectareas_afectadas DECIMAL(10,2) DEFAULT 0,
    hectareas_perdidas DECIMAL(10,2) DEFAULT 0,
    necesidades_inmediatas TEXT,
    observaciones TEXT
);


-- ============================================
-- SECCIÓN 9.2: DAÑOS PECUARIOS
-- ============================================

CREATE TABLE edan_pecuaria (
    id_pecuaria SERIAL PRIMARY KEY,
    id_edan BIGINT NOT NULL REFERENCES edan(id_edan) ON DELETE CASCADE,
    tipo_especie VARCHAR(200),
    raza VARCHAR(200),
    animales_afectados INTEGER DEFAULT 0,
    animales_muertos INTEGER DEFAULT 0,
    necesidades_inmediatas TEXT,
    observaciones TEXT
);


-- ============================================
-- SECCIÓN 9.3: DAÑO EN INFRAESTRUCTURA PRODUCTIVA
-- ============================================

CREATE TABLE edan_infraestructura_productiva (
    id_infra_productiva SERIAL PRIMARY KEY,
    id_edan BIGINT NOT NULL REFERENCES edan(id_edan) ON DELETE CASCADE,
    tipo VARCHAR(200),
    dano_parcial INTEGER DEFAULT 0,
    dano_total INTEGER DEFAULT 0,
    observaciones TEXT
);


-- ============================================
-- SECCIÓN 10: NECESIDADES DE PROTECCIÓN
-- ============================================

CREATE TABLE edan_proteccion (
    id_proteccion SERIAL PRIMARY KEY,
    id_edan BIGINT NOT NULL REFERENCES edan(id_edan) ON DELETE CASCADE,
    id_categoria_proteccion INTEGER NOT NULL REFERENCES catalogo_categoria_proteccion(id_categoria_proteccion),
    mujeres INTEGER DEFAULT 0,
    hombres INTEGER DEFAULT 0,
    total INTEGER DEFAULT 0,
    apoyo_psicosocial BOOLEAN DEFAULT FALSE,
    reposicion_documentos BOOLEAN DEFAULT FALSE,
    observaciones TEXT,
    UNIQUE(id_edan, id_categoria_proteccion)
);


-- ============================================
-- SECCIÓN 11: NECESIDADES HUMANITARIAS / AYUDA
-- ============================================

CREATE TABLE edan_ayuda_humanitaria (
    id_ayuda_edan SERIAL PRIMARY KEY,
    id_edan BIGINT NOT NULL REFERENCES edan(id_edan) ON DELETE CASCADE,
    id_ayuda_humanitaria INTEGER NOT NULL REFERENCES catalogo_ayuda_humanitaria(id_ayuda_humanitaria),
    requiere BOOLEAN DEFAULT FALSE,
    observaciones TEXT,
    UNIQUE(id_edan, id_ayuda_humanitaria)
);


-- ============================================
-- SECCIÓN 12: COMUNIDADES / LOCALIDADES / BARRIOS AFECTADOS
-- ============================================

CREATE TABLE edan_comunidad (
    id_comunidad SERIAL PRIMARY KEY,
    id_edan BIGINT NOT NULL REFERENCES edan(id_edan) ON DELETE CASCADE,
    nombre_comunidad VARCHAR(200) NOT NULL
);


-- ============================================
-- ÍNDICES PARA RENDIMIENTO
-- ============================================

-- Geografía (FKs por id)
CREATE INDEX idx_provincia_dep ON catalogo_provincia(id_departamento);
CREATE INDEX idx_municipio_dep ON catalogo_municipio(id_departamento);
CREATE INDEX idx_municipio_prov ON catalogo_municipio(id_provincia);

-- edan
CREATE INDEX idx_edan_dep ON edan(id_departamento);
CREATE INDEX idx_edan_mun ON edan(id_municipio);
CREATE INDEX idx_edan_fecha_evento ON edan(fecha_evento);

-- Tablas hijas
CREATE INDEX idx_edan_poblacion_grupo_edan ON edan_poblacion_grupo(id_edan);
CREATE INDEX idx_edan_tipo_evento_edan ON edan_tipo_evento(id_edan);
CREATE INDEX idx_edan_primera_respuesta_edan ON edan_primera_respuesta(id_edan);
CREATE INDEX idx_edan_salud_establecimiento_edan ON edan_salud_establecimiento(id_edan);
CREATE INDEX idx_edan_salud_necesidades_edan ON edan_salud_necesidades(id_edan);
CREATE INDEX idx_edan_infraestructura_vial_edan ON edan_infraestructura_vial(id_edan);
CREATE INDEX idx_edan_infraestructura_publica_edan ON edan_infraestructura_publica(id_edan);
CREATE INDEX idx_edan_servicio_basico_edan ON edan_servicio_basico(id_edan);
CREATE INDEX idx_edan_educacion_dano_edan ON edan_educacion_dano(id_edan);
CREATE INDEX idx_edan_educacion_afectacion_edan ON edan_educacion_afectacion(id_edan);
CREATE INDEX idx_edan_vivienda_edan ON edan_vivienda(id_edan);
CREATE INDEX idx_edan_agricultura_edan ON edan_agricultura(id_edan);
CREATE INDEX idx_edan_pecuaria_edan ON edan_pecuaria(id_edan);
CREATE INDEX idx_edan_infraestructura_productiva_edan ON edan_infraestructura_productiva(id_edan);
CREATE INDEX idx_edan_proteccion_edan ON edan_proteccion(id_edan);
CREATE INDEX idx_edan_ayuda_humanitaria_edan ON edan_ayuda_humanitaria(id_edan);
CREATE INDEX idx_edan_comunidad_edan ON edan_comunidad(id_edan);

-- ============================================
-- COMENTARIOS EN TABLAS
-- ============================================

COMMENT ON TABLE catalogo_departamento IS 'Catálogo de 9 departamentos de Bolivia (PK: id INTEGER, UNIQUE: codigo_ine)';
COMMENT ON TABLE catalogo_provincia IS 'Catálogo de provincias por departamento (PK: id INTEGER, UNIQUE: codigo_ine)';
COMMENT ON TABLE catalogo_municipio IS 'Catálogo de municipios por provincia (PK: id INTEGER, UNIQUE: codigo_ine)';
COMMENT ON TABLE edan IS 'Tabla principal - Evaluación de Daños y Análisis de Necesidades';
COMMENT ON TABLE edan_poblacion_grupo IS 'Sección 2 - Población por grupo etario';
COMMENT ON TABLE edan_tipo_evento IS 'Sección 3.1 - Tipo de evento adverso (puente)';
COMMENT ON TABLE edan_primera_respuesta IS 'Sección 3.3 - Necesidades en primera respuesta';
COMMENT ON TABLE edan_salud_establecimiento IS 'Sección 4.1 - Daños en servicios de salud';
COMMENT ON TABLE edan_salud_necesidades IS 'Sección 4.2 - Necesidades en salud';
COMMENT ON TABLE edan_infraestructura_vial IS 'Sección 5.1 - Daños en infraestructura vial';
COMMENT ON TABLE edan_infraestructura_publica IS 'Sección 5.2 - Daños en infraestructura pública';
COMMENT ON TABLE edan_servicio_basico IS 'Sección 6 - Daño en servicios básicos';
COMMENT ON TABLE edan_educacion_dano IS 'Sección 7.1 - Daños en unidades educativas';
COMMENT ON TABLE edan_educacion_afectacion IS 'Sección 7.2 - Afectación a alumnos, profesores y admin';
COMMENT ON TABLE edan_vivienda IS 'Sección 8 - Daños en vivienda';
COMMENT ON TABLE edan_agricultura IS 'Sección 9.1 - Daños y necesidades en agricultura';
COMMENT ON TABLE edan_pecuaria IS 'Sección 9.2 - Daños y necesidades pecuarias';
COMMENT ON TABLE edan_infraestructura_productiva IS 'Sección 9.3 - Daño en infraestructura productiva';
COMMENT ON TABLE edan_proteccion IS 'Sección 10 - Necesidades de protección';
COMMENT ON TABLE edan_ayuda_humanitaria IS 'Sección 11 - Necesidades humanitarias';
COMMENT ON TABLE edan_comunidad IS 'Sección 12 - Comunidades/localidades/barrios afectados';
