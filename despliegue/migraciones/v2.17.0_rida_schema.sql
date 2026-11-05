-- ============================================================================
-- SINAGERSAT - Migración v2.17.0 (idempotente)
-- Esquema rida: Sistema RIDA Integral (VIDECI) — SOLO BASE DE DATOS.
--
-- Crea el esquema `rida` con sus 27 tablas (11 catálogos + 16 de operación),
-- índices y semillas, y su relación (FK) con los esquemas existentes:
--   - edan.edan / edan.edan_localidades      (evento y localidad 1:1)
--   - shared.departamento / shared.municipio (geografía INE, PostGIS 4326)
--   - usuarios.usuario                       (firmas de aprobación / auditoría)
--   - repositorio.documentos                 (PDF con firma AGETIC)
--   - repositorio.tipo_documento             (checklist documental)
--   - usuarios.aplicacion/accion/permiso     (matriz RIDA, aplicación id 2)
--
-- Adaptador mínimo de repositorio.documentos:
--   id_edan pasa a NULLABLE + nueva columna id_solicitud_rida (FK a rida.solicitud)
--   para reutilizar el repositorio de PDF sin romper EDAN.
--
-- Semillas: 4 modalidades, catálogos de empadronamiento, 23 códigos de documento
-- RIDA y 74 pasos de flujo (21 AH + 25 UMEE + 15 REHR + 13 REHI) en cat_requisito.
--
-- Basado en docs/RIDA_BD.md (diseño aprobado).
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. Esquema y extensión PostGIS
-- ----------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS rida;

CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA public;

-- ----------------------------------------------------------------------------
-- 2. Catálogos (11)
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS rida.cat_modalidad (
    id_modalidad SERIAL PRIMARY KEY,
    codigo       VARCHAR(30)  NOT NULL UNIQUE,
    nombre       VARCHAR(100) NOT NULL,
    descripcion  TEXT,
    orden        INTEGER,
    activo       BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS rida.cat_categoria_ayuda (
    id_categoria SERIAL PRIMARY KEY,
    codigo       VARCHAR(30)  NOT NULL UNIQUE,
    nombre       VARCHAR(100) NOT NULL,
    descripcion  TEXT,
    activo       BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS rida.cat_articulo (
    id_articulo         SERIAL PRIMARY KEY,
    id_categoria        INTEGER NOT NULL REFERENCES rida.cat_categoria_ayuda(id_categoria),
    codigo              VARCHAR(30) UNIQUE,
    nombre              VARCHAR(150) NOT NULL,
    unidad_medida       VARCHAR(20) DEFAULT 'unidad',
    peso_unitario_kg    NUMERIC(10,3),
    costo_referencia_bs NUMERIC(12,2),
    activo              BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS rida.cat_condicion_hogar (
    id_condicion SERIAL PRIMARY KEY,
    codigo       VARCHAR(20) NOT NULL UNIQUE,
    nombre       VARCHAR(50) NOT NULL,
    descripcion  TEXT
);

CREATE TABLE IF NOT EXISTS rida.cat_parentesco (
    id_parentesco SERIAL PRIMARY KEY,
    codigo        VARCHAR(20) NOT NULL UNIQUE,
    nombre        VARCHAR(50) NOT NULL,
    activo        BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS rida.cat_tipo_discapacidad (
    id_discapacidad    SERIAL PRIMARY KEY,
    codigo             VARCHAR(20) NOT NULL UNIQUE,
    nombre             VARCHAR(50) NOT NULL,
    requiere_movilidad BOOLEAN DEFAULT FALSE,
    activo             BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS rida.cat_enfermedad_cronica (
    id_enfermedad                SERIAL PRIMARY KEY,
    codigo                       VARCHAR(20) NOT NULL UNIQUE,
    nombre                       VARCHAR(80) NOT NULL,
    requiere_medicacion_continua BOOLEAN DEFAULT TRUE,
    activo                       BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS rida.cat_sector (
    id_sector SERIAL PRIMARY KEY,
    codigo    VARCHAR(20) NOT NULL UNIQUE,
    nombre    VARCHAR(80) NOT NULL,
    activo    BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS rida.cat_almacen (
    id_almacen      SERIAL PRIMARY KEY,
    codigo          VARCHAR(20)  NOT NULL UNIQUE,
    nombre          VARCHAR(100) NOT NULL,
    nivel           VARCHAR(20) DEFAULT 'nacional' CHECK (nivel IN ('nacional','departamental','regional')),
    id_departamento INTEGER REFERENCES shared.departamento(id),
    responsable     VARCHAR(150),
    activo          BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS rida.cat_unidad_militar (
    id_unidad SERIAL PRIMARY KEY,
    codigo    VARCHAR(20)  NOT NULL UNIQUE,
    nombre    VARCHAR(150) NOT NULL,
    comando   VARCHAR(20),
    activo    BOOLEAN DEFAULT TRUE
);

-- Almacena la línea de secuencia: los pasos de cada modalidad (§4 de RIDA_BD.md).
CREATE TABLE IF NOT EXISTS rida.cat_requisito (
    id_requisito       SERIAL PRIMARY KEY,
    id_modalidad       INTEGER NOT NULL REFERENCES rida.cat_modalidad(id_modalidad),
    orden              INTEGER NOT NULL,
    nombre_paso        VARCHAR(150) NOT NULL,
    id_tipo_documento  INTEGER REFERENCES repositorio.tipo_documento(id_tipo_documento),
    instancia          INTEGER NOT NULL CHECK (instancia IN (1, 2, 3)),
    es_documento       BOOLEAN DEFAULT TRUE,
    es_hito_aprobacion BOOLEAN DEFAULT FALSE,
    activo             BOOLEAN DEFAULT TRUE,
    UNIQUE (id_modalidad, orden)
);

-- ----------------------------------------------------------------------------
-- 3. Operación (16 tablas)
-- ----------------------------------------------------------------------------

-- 1:1 con la localidad/campamento (UNIQUE + NULL para campamentos SIN EDAN)
CREATE TABLE IF NOT EXISTS rida.formulario_rida (
    id_formulario      SERIAL PRIMARY KEY,
    id_edan_localidad  INTEGER UNIQUE REFERENCES edan.edan_localidades(id_edan_localidad),
    id_edan            BIGINT REFERENCES edan.edan(id_edan),
    nombre_localidad   VARCHAR(200),
    id_municipio       INTEGER NOT NULL REFERENCES shared.municipio(id),
    id_departamento    INTEGER REFERENCES shared.departamento(id),
    tipo_asentamiento  VARCHAR(20) DEFAULT 'localidad' CHECK (tipo_asentamiento IN ('localidad','campamento','albergue')),
    n_carpa            INTEGER DEFAULT 0,
    lat                NUMERIC(10,8),
    lon                NUMERIC(11,8),
    geom               GEOMETRY(Polygon,4326),
    estado             VARCHAR(20) DEFAULT 'PENDIENTE',
    id_usuario         INTEGER REFERENCES usuarios.usuario(id_usuario),
    fecha_creacion     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- FK circular id_jefe -> integrante se agrega al final (sección 3.1)
CREATE TABLE IF NOT EXISTS rida.familia (
    id_familia        SERIAL PRIMARY KEY,
    id_formulario     INTEGER NOT NULL REFERENCES rida.formulario_rida(id_formulario),
    codigo_ficha      VARCHAR(20) NOT NULL UNIQUE,
    id_condicion      INTEGER REFERENCES rida.cat_condicion_hogar(id_condicion),
    ubicacion_original JSONB,
    ubicacion_actual  VARCHAR(50) CHECK (ubicacion_actual IN ('albergue_temporal','casa_acogida','predio_danado','calle','vivienda_propia')),
    id_jefe           INTEGER,
    n_integrantes     INTEGER DEFAULT 1,
    estado            VARCHAR(20) DEFAULT 'ACTIVA',
    observaciones     TEXT
);

CREATE TABLE IF NOT EXISTS rida.integrante (
    id_integrante     SERIAL PRIMARY KEY,
    id_familia        INTEGER NOT NULL REFERENCES rida.familia(id_familia),
    nombres           VARCHAR(100) NOT NULL,
    apellidos         VARCHAR(100) NOT NULL,
    sexo              CHAR(1) CHECK (sexo IN ('M','F')),
    fecha_nacimiento  DATE,
    numero_ci         VARCHAR(15),
    id_parentesco     INTEGER REFERENCES rida.cat_parentesco(id_parentesco),
    es_jefe           BOOLEAN DEFAULT FALSE,
    gestante_semanas  INTEGER CHECK (gestante_semanas BETWEEN 0 AND 45),
    lactante_meses    INTEGER CHECK (lactante_meses BETWEEN 0 AND 36),
    id_discapacidad   INTEGER REFERENCES rida.cat_tipo_discapacidad(id_discapacidad),
    id_enfermedad     INTEGER REFERENCES rida.cat_enfermedad_cronica(id_enfermedad),
    medicacion_continua BOOLEAN DEFAULT FALSE,
    actividad_economica VARCHAR(50),
    telefono          VARCHAR(20),
    observaciones     TEXT
);

-- Necesidad transversal (de familia o de localidad)
CREATE TABLE IF NOT EXISTS rida.necesidad (
    id_necesidad   SERIAL PRIMARY KEY,
    id_familia     INTEGER REFERENCES rida.familia(id_familia),
    id_formulario  INTEGER REFERENCES rida.formulario_rida(id_formulario),
    id_categoria   INTEGER NOT NULL REFERENCES rida.cat_categoria_ayuda(id_categoria),
    id_articulo    INTEGER REFERENCES rida.cat_articulo(id_articulo),
    cantidad       NUMERIC(12,2) NOT NULL DEFAULT 0,
    unidad_medida  VARCHAR(20),
    prioridad      SMALLINT DEFAULT 3 CHECK (prioridad IN (1,2,3)),
    justificacion  TEXT,
    fecha_requerida DATE,
    estado         VARCHAR(20) DEFAULT 'PENDIENTE'
);

-- Expediente central (una solicitud por modalidad)
CREATE TABLE IF NOT EXISTS rida.solicitud (
    id_solicitud          SERIAL PRIMARY KEY,
    id_formulario         INTEGER NOT NULL REFERENCES rida.formulario_rida(id_formulario),
    id_modalidad          INTEGER NOT NULL REFERENCES rida.cat_modalidad(id_modalidad),
    codigo_expediente     VARCHAR(30) NOT NULL UNIQUE,
    etapa                 VARCHAR(30) NOT NULL DEFAULT 'BORRADOR',
    id_municipio          INTEGER REFERENCES shared.municipio(id),
    id_departamento       INTEGER REFERENCES shared.departamento(id),
    fecha_inicio          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    aprob_ugr             BOOLEAN DEFAULT FALSE,
    aprob_ugr_fecha       TIMESTAMP,
    aprob_ugr_por         INTEGER REFERENCES usuarios.usuario(id_usuario),
    aprob_alcalde         BOOLEAN DEFAULT FALSE,
    aprob_alcalde_fecha   TIMESTAMP,
    aprob_alcalde_por     INTEGER REFERENCES usuarios.usuario(id_usuario),
    aprob_dgr             BOOLEAN DEFAULT FALSE,
    aprob_dgr_fecha       TIMESTAMP,
    aprob_dgr_por         INTEGER REFERENCES usuarios.usuario(id_usuario),
    aprob_videcid         BOOLEAN DEFAULT FALSE,
    aprob_videcid_fecha   TIMESTAMP,
    aprob_videcid_por     INTEGER REFERENCES usuarios.usuario(id_usuario),
    aprob_direccion       BOOLEAN DEFAULT FALSE,
    aprob_direccion_fecha TIMESTAMP,
    aprob_direccion_por   INTEGER REFERENCES usuarios.usuario(id_usuario),
    observaciones         TEXT,
    fecha_cierre          TIMESTAMP,
    id_usuario_crea       INTEGER REFERENCES usuarios.usuario(id_usuario)
);

CREATE TABLE IF NOT EXISTS rida.bitacora (
    id_bitacora       BIGSERIAL PRIMARY KEY,
    id_solicitud      INTEGER NOT NULL REFERENCES rida.solicitud(id_solicitud),
    paso_orden        INTEGER,
    paso_nombre       VARCHAR(150),
    accion            VARCHAR(20),
    estado_resultante VARCHAR(30),
    observaciones     TEXT,
    id_usuario        INTEGER REFERENCES usuarios.usuario(id_usuario),
    fecha             TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS rida.solicitud_documento (
    id_solicitud_documento SERIAL PRIMARY KEY,
    id_solicitud           INTEGER NOT NULL REFERENCES rida.solicitud(id_solicitud),
    id_requisito           INTEGER REFERENCES rida.cat_requisito(id_requisito),
    id_documento           BIGINT NOT NULL REFERENCES repositorio.documentos(id_documento),
    id_tipo_documento      INTEGER REFERENCES repositorio.tipo_documento(id_tipo_documento),
    id_usuario_subio       INTEGER REFERENCES usuarios.usuario(id_usuario),
    fecha_subida           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    valido                 BOOLEAN DEFAULT TRUE,
    observaciones          TEXT
);

CREATE TABLE IF NOT EXISTS rida.comando_incidente (
    id_comando         SERIAL PRIMARY KEY,
    id_solicitud       INTEGER REFERENCES rida.solicitud(id_solicitud),
    codigo             VARCHAR(20) UNIQUE,
    fecha_conformacion TIMESTAMP,
    responsable        VARCHAR(150),
    estado             VARCHAR(20) DEFAULT 'ACTIVO'
);

CREATE TABLE IF NOT EXISTS rida.requerimiento_umee (
    id_requerimiento   SERIAL PRIMARY KEY,
    id_comando         INTEGER REFERENCES rida.comando_incidente(id_comando),
    id_solicitud       INTEGER NOT NULL REFERENCES rida.solicitud(id_solicitud),
    informe_necesidades TEXT,
    prioridad          SMALLINT DEFAULT 3 CHECK (prioridad IN (1,2,3)),
    fecha              DATE,
    estado             VARCHAR(20) DEFAULT 'PENDIENTE'
);

CREATE TABLE IF NOT EXISTS rida.proveedor (
    id_proveedor SERIAL PRIMARY KEY,
    nombre       VARCHAR(200) NOT NULL UNIQUE,
    nit          VARCHAR(30),
    rubro        VARCHAR(100),
    representante VARCHAR(150),
    telefono     VARCHAR(20),
    activo       BOOLEAN DEFAULT TRUE
);

-- Las 3 proformas obligatorias de Rehabilitación-Reconstrucción
CREATE TABLE IF NOT EXISTS rida.proforma (
    id_proforma          SERIAL PRIMARY KEY,
    id_solicitud         INTEGER NOT NULL REFERENCES rida.solicitud(id_solicitud),
    id_proveedor         INTEGER NOT NULL REFERENCES rida.proveedor(id_proveedor),
    monto_bs             NUMERIC(14,2),
    horas_maquinaria     NUMERIC(10,2),
    descripcion_servicio TEXT,
    seleccionada         BOOLEAN DEFAULT FALSE,
    fecha_presentacion   DATE
);

CREATE TABLE IF NOT EXISTS rida.contratacion (
    id_contratacion       SERIAL PRIMARY KEY,
    id_solicitud          INTEGER NOT NULL REFERENCES rida.solicitud(id_solicitud),
    id_proforma           INTEGER REFERENCES rida.proforma(id_proforma),
    id_proveedor          INTEGER REFERENCES rida.proveedor(id_proveedor),
    responsable_recepcion VARCHAR(150),
    fecha_inicio          DATE,
    fecha_fin             DATE,
    codigo_siges          VARCHAR(50),
    estado                VARCHAR(20) DEFAULT 'EN_EJECUCION'
);

CREATE TABLE IF NOT EXISTS rida.proyecto (
    id_proyecto             SERIAL PRIMARY KEY,
    id_solicitud            INTEGER NOT NULL REFERENCES rida.solicitud(id_solicitud),
    id_sector               INTEGER REFERENCES rida.cat_sector(id_sector),
    tipo                    VARCHAR(30) CHECK (tipo IN ('REHABILITACION','RECONSTRUCCION','INSUMOS')),
    nombre                  VARCHAR(200) NOT NULL,
    descripcion             TEXT,
    geom                    GEOMETRY(Geometry,4326),
    monto_estimado          NUMERIC(14,2),
    moneda                  CHAR(3) DEFAULT 'BOB',
    fuente_financiamiento   VARCHAR(100),
    incorpora_gestion_riesgo BOOLEAN DEFAULT TRUE,
    criterios_prospectiva   TEXT,
    criterios_correctiva    TEXT,
    estado                  VARCHAR(20) DEFAULT 'EN_EVALUACION',
    fecha_inicio            DATE,
    fecha_fin               DATE
);

CREATE TABLE IF NOT EXISTS rida.entrega (
    id_entrega        SERIAL PRIMARY KEY,
    id_solicitud      INTEGER NOT NULL REFERENCES rida.solicitud(id_solicitud),
    id_almacen        INTEGER REFERENCES rida.cat_almacen(id_almacen),
    tipo              VARCHAR(30) CHECK (tipo IN ('AYUDA_HUMANITARIA','INSUMOS_REHABILITACION','EQUIPAMIENTO_UMEE')),
    id_unidad_militar INTEGER REFERENCES rida.cat_unidad_militar(id_unidad),
    responsable       VARCHAR(150),
    transporte        VARCHAR(100),
    placa             VARCHAR(20),
    fecha_salida      TIMESTAMP,
    fecha_entrega     TIMESTAMP,
    estado            VARCHAR(20) DEFAULT 'AUTORIZADA',
    observaciones     TEXT
);

CREATE TABLE IF NOT EXISTS rida.entrega_detalle (
    id_detalle   SERIAL PRIMARY KEY,
    id_entrega   INTEGER NOT NULL REFERENCES rida.entrega(id_entrega),
    id_articulo  INTEGER NOT NULL REFERENCES rida.cat_articulo(id_articulo),
    cantidad     NUMERIC(12,2) NOT NULL,
    peso_kg      NUMERIC(12,2),
    valor_bs     NUMERIC(14,2)
);

CREATE TABLE IF NOT EXISTS rida.entrega_beneficiario (
    id_entrega_beneficiario SERIAL PRIMARY KEY,
    id_entrega   INTEGER NOT NULL REFERENCES rida.entrega(id_entrega),
    id_familia   INTEGER NOT NULL REFERENCES rida.familia(id_familia),
    id_articulo  INTEGER REFERENCES rida.cat_articulo(id_articulo),
    cantidad     NUMERIC(12,2) NOT NULL,
    fecha        DATE,
    evidencia    VARCHAR(500),
    firma_digital BOOLEAN DEFAULT FALSE,
    observaciones TEXT
);

-- 3.1 FK circular: jefe/a de hogar (familia -> integrante)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_familia_jefe_integrante') THEN
        ALTER TABLE rida.familia
            ADD CONSTRAINT fk_familia_jefe_integrante
            FOREIGN KEY (id_jefe) REFERENCES rida.integrante(id_integrante);
    END IF;
END $$;

-- ----------------------------------------------------------------------------
-- 4. Índices recomendados (§6.3 de RIDA_BD.md)
-- ----------------------------------------------------------------------------

CREATE UNIQUE INDEX IF NOT EXISTS idx_formulario_id_edan_localidad
    ON rida.formulario_rida (id_edan_localidad) WHERE id_edan_localidad IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_formulario_id_municipio
    ON rida.formulario_rida (id_municipio);
CREATE INDEX IF NOT EXISTS idx_formulario_rida_geom
    ON rida.formulario_rida USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_solicitud_id_formulario
    ON rida.solicitud (id_formulario);
CREATE INDEX IF NOT EXISTS idx_solicitud_etapa
    ON rida.solicitud (etapa);
CREATE INDEX IF NOT EXISTS idx_solicitud_id_departamento_id_municipio
    ON rida.solicitud (id_departamento, id_municipio);
CREATE INDEX IF NOT EXISTS idx_bitacora_id_solicitud
    ON rida.bitacora (id_solicitud);
CREATE INDEX IF NOT EXISTS idx_solicitud_documento_id_solicitud
    ON rida.solicitud_documento (id_solicitud);
CREATE INDEX IF NOT EXISTS idx_familia_id_formulario
    ON rida.familia (id_formulario);
CREATE INDEX IF NOT EXISTS idx_entrega_id_solicitud
    ON rida.entrega (id_solicitud);
CREATE INDEX IF NOT EXISTS idx_proyecto_geom
    ON rida.proyecto USING GIST (geom);

-- ----------------------------------------------------------------------------
-- 5. Adaptador mínimo de repositorio.documentos (reuso del PDF AGETIC)
-- ----------------------------------------------------------------------------

ALTER TABLE repositorio.documentos ALTER COLUMN id_edan DROP NOT NULL;

ALTER TABLE repositorio.documentos ADD COLUMN IF NOT EXISTS id_solicitud_rida INTEGER;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_documentos_solicitud_rida') THEN
        ALTER TABLE repositorio.documentos
            ADD CONSTRAINT fk_documentos_solicitud_rida
            FOREIGN KEY (id_solicitud_rida) REFERENCES rida.solicitud(id_solicitud);
    END IF;
END $$;

COMMENT ON COLUMN repositorio.documentos.id_solicitud_rida IS
    'Vínculo opcional a rida.solicitud: permite subir PDF de un expediente RIDA (id_edan queda NULL).';

-- ----------------------------------------------------------------------------
-- 6. Semillas — catálogos
-- ----------------------------------------------------------------------------

INSERT INTO rida.cat_modalidad (codigo, nombre, descripcion, orden) VALUES
    ('AYUDA_HUMANITARIA', 'Ayuda Humanitaria', 'Entrega de bienes de asistencia humanitaria a familias damnificadas desde los almacenes de VIDECI', 1),
    ('RESPUESTA_RAPIDA_UMEE', 'Respuesta Rápida UMEE', 'Equipamiento y logística para la Unidad Militar de Emergencias y unidades de respuesta inmediata', 2),
    ('REHABILITACION_INSUMOS', 'Rehabilitación-Insumos', 'Entrega de insumos de rehabilitación a familias damnificadas para reparación a corto plazo', 3),
    ('REHABILITACION_RECONSTRUCCION', 'Rehabilitación-Reconstrucción', 'Contratación de empresas para servicios de rehabilitación o reconstrucción (Ley N.º 602)', 4)
ON CONFLICT (codigo) DO NOTHING;

INSERT INTO rida.cat_categoria_ayuda (codigo, nombre, descripcion) VALUES
    ('TECHO_ABRIGO', 'Techo y abrigo', 'Vivienda, abrigo y enseres'),
    ('ALIMENTACION_AGUA', 'Alimentación y agua segura', 'Alimentación y agua potable'),
    ('SALUD_HIGIENE', 'Salud e higiene', 'Salud, higiene y salubridad'),
    ('MEDIOS_VIDA', 'Medios de vida', 'Recuperación económica y medios de vida'),
    ('EQUIPAMIENTO_UMEE', 'Equipamiento UMEE', 'Equipamiento de respuesta militar (UMEE)')
ON CONFLICT (codigo) DO NOTHING;

INSERT INTO rida.cat_condicion_hogar (codigo, nombre, descripcion) VALUES
    ('DAMNIFICADO', 'Damnificado', 'Pérdida directa de vivienda — prioriza recursos'),
    ('AFECTADO', 'Afectado', 'Daño indirecto')
ON CONFLICT (codigo) DO NOTHING;

INSERT INTO rida.cat_parentesco (codigo, nombre) VALUES
    ('JEFE_HOGAR', 'Jefe/a de hogar'),
    ('CONYUGE', 'Cónyuge'),
    ('HIJO', 'Hijo/a'),
    ('OTRO', 'Otro parentesco')
ON CONFLICT (codigo) DO NOTHING;

INSERT INTO rida.cat_tipo_discapacidad (codigo, nombre, requiere_movilidad) VALUES
    ('FISICA', 'Discapacidad física', TRUE),
    ('SENSORIAL', 'Discapacidad sensorial', FALSE),
    ('INTELECTUAL', 'Discapacidad intelectual', FALSE),
    ('NINGUNA', 'Sin discapacidad', FALSE)
ON CONFLICT (codigo) DO NOTHING;

INSERT INTO rida.cat_enfermedad_cronica (codigo, nombre, requiere_medicacion_continua) VALUES
    ('DIABETES', 'Diabetes', TRUE),
    ('HIPERTENSION', 'Hipertensión', TRUE),
    ('VIH', 'VIH/SIDA', TRUE),
    ('DIALISIS', 'Enfermedad renal (diálisis)', TRUE),
    ('OTRAS', 'Otras enfermedades crónicas', TRUE)
ON CONFLICT (codigo) DO NOTHING;

INSERT INTO rida.cat_sector (codigo, nombre) VALUES
    ('SALUD', 'Salud'),
    ('EDUCACION', 'Educación'),
    ('VIVIENDA', 'Vivienda'),
    ('INFRAESTRUCTURA', 'Infraestructura'),
    ('MEDIOS_VIDA', 'Medios de vida')
ON CONFLICT (codigo) DO NOTHING;

INSERT INTO rida.cat_almacen (codigo, nombre, nivel, id_departamento, responsable) VALUES
    ('ALM-CENTRAL', 'Almacén Central VIDECI', 'nacional', NULL, 'Encargado de Almacenes VIDECI'),
    ('ALM-LP', 'Almacén departamental La Paz', 'departamental', (SELECT id FROM shared.departamento WHERE codigo_ine = '02'), NULL),
    ('ALM-CBBA', 'Almacén departamental Cochabamba', 'departamental', (SELECT id FROM shared.departamento WHERE codigo_ine = '03'), NULL),
    ('ALM-SCZ', 'Almacén departamental Santa Cruz', 'departamental', (SELECT id FROM shared.departamento WHERE codigo_ine = '07'), NULL)
ON CONFLICT (codigo) DO NOTHING;

INSERT INTO rida.cat_unidad_militar (codigo, nombre, comando) VALUES
    ('UMEE', 'Unidad Militar de Emergencias', 'COMAE'),
    ('GED-1', 'Grupo de Emergencia y Desastres 1', 'Región Militar 1'),
    ('REG-1', 'Regimiento de Infantería 1', 'Región Militar 1'),
    ('BA-1', 'Batallón de Ingeniería 1', 'Región Militar 1')
ON CONFLICT (codigo) DO NOTHING;

-- ----------------------------------------------------------------------------
-- 7. Semillas — tipos de documento RIDA en repositorio.tipo_documento
--    (codigo ya es UNIQUE; reutiliza informe_tecnico/informe_financiero/
--     informe_legal/edan_firmado existentes)
-- ----------------------------------------------------------------------------

INSERT INTO repositorio.tipo_documento (codigo, nombre, descripcion, orden) VALUES
    ('declaratoria_desastre', 'Declaratoria de desastre', 'Declaratoria emitida por la autoridad competente (Gobierno Municipal, COE/COMURADE)', 10),
    ('lista_familias', 'Lista de familias damnificadas', 'Empadronamiento de familias afectadas y damnificadas', 11),
    ('fotograma_evento', 'Fotograma del evento', 'Registro fotográfico / cuadro del evento', 12),
    ('certificacion_presupuestaria', 'Certificación presupuestaria', 'Certificado de disponibilidad presupuestaria del municipio', 13),
    ('solicitud_viceministro', 'Solicitud al Viceministro', 'Solicitud formal de atención al Sr. Viceministro de Defensa Civil', 14),
    ('solicitud_mae', 'Solicitud MAE municipal', 'Solicitud del municipio (Máxima Autoridad Ejecutiva)', 15),
    ('informe_validacion_departamental', 'Informe de validación departamental', 'Informe de la instancia departamental/regional', 16),
    ('nota_elevacion', 'Nota de elevación de carpeta', 'Nota que eleva el expediente al nivel nacional', 17),
    ('informe_factibilidad_departamental', 'Informe de factibilidad departamental', 'Factibilidad técnica y operativa departamental', 18),
    ('requerimiento_umee', 'Requerimiento UMEE', 'Solicitud de equipamiento y logística de la UMEE', 19),
    ('informe_necesidades_umee', 'Informe de necesidades UMEE', 'Detalle de necesidades de la unidad militar', 20),
    ('proforma_empresa', 'Proforma de empresa', 'Cotización formal de empresa legalmente constituida', 21),
    ('documentacion_legal_empresa', 'Documentación legal de empresa', 'NIT, matrícula y habilitación de la empresa', 22),
    ('informe_inicio_especificaciones', 'Informe de inicio y especificaciones técnicas', 'Inicio de proceso y especificaciones técnicas de la obra', 23),
    ('contratacion_empresa', 'Contratación y responsable de recepción', 'Documento de contratación y designación del responsable de recepción', 24),
    ('solicitud_salida_bienes', 'Solicitud de salida de bienes', 'Solicitud de salida de bienes e insumos del almacén', 25),
    ('acta_salida_almacen', 'Nota/acta de salida del almacén', 'Comprobante de salida emitido por el almacén', 26),
    ('acta_entrega_recepcion', 'Acta de entrega-recepción', 'Acta de entrega entre la departamental y el beneficiario', 27),
    ('planilla_trabajo', 'Planillas de trabajo', 'Planillas de avance de la empresa contratista', 28),
    ('acta_conformidad', 'Actas de conformidad', 'Actas de conformidad firmadas por el municipio', 29),
    ('informe_comision', 'Informe de la comisión (recepción)', 'Informe de la comisión de recepción de obra', 30),
    ('acta_descargo_umee', 'Actas de descargo UMEE', 'Actas de recepción firmadas por las unidades militares', 31),
    ('carpeta_descargo', 'Carpeta de descargo', 'Carpeta de descargo firmada por las familias (UGR)', 32)
ON CONFLICT (codigo) DO NOTHING;

-- ----------------------------------------------------------------------------
-- 8. Semillas — cat_requisito: 74 pasos de flujo (semilla de la línea de secuencia)
-- ----------------------------------------------------------------------------

INSERT INTO rida.cat_requisito
    (id_modalidad, orden, nombre_paso, id_tipo_documento, instancia, es_documento, es_hito_aprobacion)
SELECT m.id_modalidad, v.orden, v.nombre_paso, t.id_tipo_documento, v.instancia, v.es_documento, v.es_hito_aprobacion
FROM (VALUES
-- Ayuda Humanitaria (21)
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'AYUDA_HUMANITARIA'),  1, 'Ocurrencia del evento adverso',                       NULL::text, 1, FALSE, FALSE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'AYUDA_HUMANITARIA'),  2, 'Formulario EDAN del municipio',                       'edan_firmado', 1, TRUE,  FALSE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'AYUDA_HUMANITARIA'),  3, 'Lista de familias damnificadas',                      'lista_familias', 1, TRUE, FALSE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'AYUDA_HUMANITARIA'),  4, 'Fotograma del evento',                                'fotograma_evento', 1, TRUE, FALSE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'AYUDA_HUMANITARIA'),  5, 'Informe técnico del municipio',                       'informe_tecnico', 1, TRUE, FALSE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'AYUDA_HUMANITARIA'),  6, 'Informe técnico financiero',                          'informe_financiero', 1, TRUE, FALSE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'AYUDA_HUMANITARIA'),  7, 'Certificación presupuestaria del municipio',          'certificacion_presupuestaria', 1, TRUE, FALSE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'AYUDA_HUMANITARIA'),  8, 'Informe legal del municipio',                         'informe_legal', 1, TRUE, FALSE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'AYUDA_HUMANITARIA'),  9, 'Declaratoria de desastre del municipio',              'declaratoria_desastre', 1, TRUE, FALSE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'AYUDA_HUMANITARIA'), 10, 'Solicitud de ayuda humanitaria al Sr. Viceministro',  'solicitud_viceministro', 1, TRUE, TRUE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'AYUDA_HUMANITARIA'), 11, 'Informe de validación departamental',                 'informe_validacion_departamental', 2, TRUE, FALSE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'AYUDA_HUMANITARIA'), 12, 'Nota elevando la carpeta al Sr. Viceministro',        'nota_elevacion', 2, TRUE, TRUE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'AYUDA_HUMANITARIA'), 13, 'Autorización de carpeta por el Viceministro',          NULL::text, 3, FALSE, TRUE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'AYUDA_HUMANITARIA'), 14, 'Aprobación por el Director General de Emergencia y Auxilio (DGEA)', NULL::text, 3, FALSE, TRUE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'AYUDA_HUMANITARIA'), 15, 'Revisión por la Unidad de Respuesta',                 NULL::text, 3, FALSE, FALSE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'AYUDA_HUMANITARIA'), 16, 'Gestión y autorización de suministros y transportes',  NULL::text, 3, FALSE, TRUE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'AYUDA_HUMANITARIA'), 17, 'Solicitud de salida de bienes por la departamental',   'solicitud_salida_bienes', 2, TRUE, FALSE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'AYUDA_HUMANITARIA'), 18, 'Salida de bienes y emisión de nota por almacén',       'acta_salida_almacen', 3, TRUE, FALSE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'AYUDA_HUMANITARIA'), 19, 'Entrega de ayuda por la departamental y regional',     'acta_entrega_recepcion', 2, TRUE, FALSE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'AYUDA_HUMANITARIA'), 20, 'Distribución por el municipio o gobernación',          NULL::text, 1, FALSE, FALSE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'AYUDA_HUMANITARIA'), 21, 'Elaboración de carpeta de descargo por el UGR',        'carpeta_descargo', 1, TRUE, TRUE),
-- Respuesta Rápida UMEE (25)
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'RESPUESTA_RAPIDA_UMEE'),  1, 'Evento adverso',                                                     NULL::text, 1, FALSE, FALSE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'RESPUESTA_RAPIDA_UMEE'),  2, 'Conformación del Comando de Incidentes',                            NULL::text, 2, FALSE, FALSE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'RESPUESTA_RAPIDA_UMEE'),  3, 'Decisión: ¿existe declaratoria de desastre? (No → respuesta local)', NULL::text, 2, FALSE, FALSE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'RESPUESTA_RAPIDA_UMEE'),  4, 'Requerimiento de la UMEE (sí hay desastre)',                        'requerimiento_umee', 2, TRUE, FALSE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'RESPUESTA_RAPIDA_UMEE'),  5, 'Informe de necesidades de la UMEE',                                 'informe_necesidades_umee', 2, TRUE, FALSE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'RESPUESTA_RAPIDA_UMEE'),  6, 'Informe de factibilidad departamental',                             'informe_factibilidad_departamental', 2, TRUE, FALSE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'RESPUESTA_RAPIDA_UMEE'),  7, 'Nota elevando la carpeta al Sr. Viceministro',                     'nota_elevacion', 2, TRUE, TRUE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'RESPUESTA_RAPIDA_UMEE'),  8, 'Autorización del Viceministro',                                    NULL::text, 3, FALSE, TRUE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'RESPUESTA_RAPIDA_UMEE'),  9, 'Aprobación de la DGEA',                                            NULL::text, 3, FALSE, TRUE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'RESPUESTA_RAPIDA_UMEE'), 10, 'Revisión en la Unidad de Respuesta',                               NULL::text, 3, FALSE, FALSE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'RESPUESTA_RAPIDA_UMEE'), 11, 'Informe de necesidades por la UMEE (consolidado)',                 'informe_necesidades_umee', 2, TRUE, FALSE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'RESPUESTA_RAPIDA_UMEE'), 12, 'Revisión departamental y solicitud de salida de almacenes',        'solicitud_salida_bienes', 2, TRUE, TRUE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'RESPUESTA_RAPIDA_UMEE'), 13, 'Salida de bienes y emisión de nota (almacén)',                     'acta_salida_almacen', 3, TRUE, FALSE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'RESPUESTA_RAPIDA_UMEE'), 14, 'Autorizaciones de almacén — salida',                               NULL::text, 2, FALSE, TRUE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'RESPUESTA_RAPIDA_UMEE'), 15, 'Autorizaciones de almacén — revisión',                             NULL::text, 2, FALSE, TRUE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'RESPUESTA_RAPIDA_UMEE'), 16, 'Autorizaciones de almacén — autorización',                         NULL::text, 3, FALSE, TRUE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'RESPUESTA_RAPIDA_UMEE'), 17, 'Autorizaciones de almacén — entrega',                              NULL::text, 3, FALSE, TRUE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'RESPUESTA_RAPIDA_UMEE'), 18, 'Autorizaciones de almacén — cierre',                               NULL::text, 3, FALSE, TRUE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'RESPUESTA_RAPIDA_UMEE'), 19, 'Entrega a la entidad — UMEE',                                     'acta_entrega_recepcion', 2, TRUE, FALSE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'RESPUESTA_RAPIDA_UMEE'), 20, 'Revisión en la Unidad de Respuesta (documentos técnicos/legales)', NULL::text, 3, FALSE, FALSE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'RESPUESTA_RAPIDA_UMEE'), 21, 'Disposición de suministros y transporte',                          NULL::text, 3, FALSE, TRUE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'RESPUESTA_RAPIDA_UMEE'), 22, 'Solicitud de salida de almacenes territoriales',                   'solicitud_salida_bienes', 2, TRUE, FALSE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'RESPUESTA_RAPIDA_UMEE'), 23, 'Distribución a unidades militares',                                'acta_entrega_recepcion', 2, TRUE, FALSE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'RESPUESTA_RAPIDA_UMEE'), 24, 'Carpeta de descargo y cierre (actas firmadas por unidades)',       'acta_descargo_umee', 2, TRUE, TRUE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'RESPUESTA_RAPIDA_UMEE'), 25, 'Final de la entrega',                                              NULL::text, 3, FALSE, TRUE),
-- Rehabilitación-Reconstrucción (15)
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'REHABILITACION_RECONSTRUCCION'),  1, 'Evento adverso',                                               NULL::text, 1, FALSE, FALSE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'REHABILITACION_RECONSTRUCCION'),  2, 'Municipio: documentación (EDAN, técnico, legal, presupuestario, declaratoria)', 'edan_firmado', 1, TRUE, FALSE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'REHABILITACION_RECONSTRUCCION'),  3, 'Municipio: 3 proformas de empresas legalmente constituidas',   'proforma_empresa', 1, TRUE, FALSE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'REHABILITACION_RECONSTRUCCION'),  4, 'Documentación complementaria (legal empresas + horas)',         'documentacion_legal_empresa', 1, TRUE, FALSE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'REHABILITACION_RECONSTRUCCION'),  5, 'Elevación de documentación al nivel nacional',                  'nota_elevacion', 2, TRUE, FALSE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'REHABILITACION_RECONSTRUCCION'),  6, 'Informe de validación departamental → despacho',                'informe_validacion_departamental', 2, TRUE, TRUE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'REHABILITACION_RECONSTRUCCION'),  7, 'Viceministro autoriza carpeta → DGPR',                          NULL::text, 3, FALSE, TRUE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'REHABILITACION_RECONSTRUCCION'),  8, 'DGPR aprueba carpeta → Unidad de Rehabilitación y Reconstrucción', NULL::text, 3, FALSE, TRUE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'REHABILITACION_RECONSTRUCCION'),  9, 'Unidad revisa documentación y observa errores (subsanar)',      NULL::text, 3, FALSE, FALSE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'REHABILITACION_RECONSTRUCCION'), 10, 'Informe de inicio de proceso + especificaciones técnicas',      'informe_inicio_especificaciones', 3, TRUE, FALSE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'REHABILITACION_RECONSTRUCCION'), 11, 'Unidad Administrativa: contratación + responsable de recepción','contratacion_empresa', 3, TRUE, TRUE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'REHABILITACION_RECONSTRUCCION'), 12, 'Empresa ejecuta: planillas de trabajo + actas de conformidad',  'planilla_trabajo', 3, TRUE, FALSE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'REHABILITACION_RECONSTRUCCION'), 13, 'Informe de la comisión + descargo a despacho del Ministro',     'informe_comision', 3, TRUE, FALSE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'REHABILITACION_RECONSTRUCCION'), 14, 'Unidad de Contrataciones: cierre en SIGES',                     NULL::text, 3, FALSE, TRUE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'REHABILITACION_RECONSTRUCCION'), 15, 'Proceso de pago',                                              NULL::text, 3, FALSE, TRUE),
-- Rehabilitación-Insumos (13)
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'REHABILITACION_INSUMOS'),  1, 'Evento adverso',                                          NULL::text, 1, FALSE, FALSE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'REHABILITACION_INSUMOS'),  2, 'Municipio: documentación inicial (EDAN, técnico, legal, financiero, certificación)', 'edan_firmado', 1, TRUE, FALSE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'REHABILITACION_INSUMOS'),  3, 'Documentación social: fotos + lista de familias + solicitud MAE', 'solicitud_mae', 1, TRUE, FALSE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'REHABILITACION_INSUMOS'),  4, 'Remisión de la documentación a la instancia departamental',  'nota_elevacion', 2, TRUE, FALSE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'REHABILITACION_INSUMOS'),  5, 'Viceministro aprueba la carpeta → DGPR',                    NULL::text, 3, FALSE, TRUE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'REHABILITACION_INSUMOS'),  6, 'DGPR aprueba la carpeta → Unidad',                          NULL::text, 3, FALSE, TRUE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'REHABILITACION_INSUMOS'),  7, 'Unidad revisa la documentación y coordina subsanación',     NULL::text, 3, FALSE, FALSE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'REHABILITACION_INSUMOS'),  8, 'Autorización de salida de insumos',                         NULL::text, 3, FALSE, TRUE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'REHABILITACION_INSUMOS'),  9, 'Departamentales elevan solicitud de insumos',               'solicitud_salida_bienes', 2, TRUE, FALSE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'REHABILITACION_INSUMOS'), 10, 'Unidad gestiona la salida con la Unidad Administrativa',   NULL::text, 3, FALSE, FALSE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'REHABILITACION_INSUMOS'), 11, 'Unidad Administrativa autoriza la salida de insumos',      NULL::text, 3, FALSE, TRUE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'REHABILITACION_INSUMOS'), 12, 'Entrega de insumos al municipio',                          'acta_entrega_recepcion', 2, TRUE, FALSE),
    ((SELECT id_modalidad FROM rida.cat_modalidad WHERE codigo = 'REHABILITACION_INSUMOS'), 13, 'Documento de descargo en coordinación con la UGR',          'carpeta_descargo', 2, TRUE, TRUE)
) AS v(id_modalidad, orden, nombre_paso, codigo_doc, instancia, es_documento, es_hito_aprobacion)
JOIN rida.cat_modalidad m ON m.id_modalidad = v.id_modalidad
LEFT JOIN repositorio.tipo_documento t ON t.codigo = v.codigo_doc
ON CONFLICT (id_modalidad, orden) DO NOTHING;

-- ----------------------------------------------------------------------------
-- 9. Matriz de permisos RIDA (§8.3 de RIDA_BD.md) en usuarios.permiso
--    DELETE de rol 6 limitado a borradores propios se valida en la capa API.
--    (PostgreSQL no puede expresar el "borrador propio" a nivel de permiso.)
-- ----------------------------------------------------------------------------

INSERT INTO usuarios.permiso (id_rol, id_aplicacion, id_accion)
SELECT v.id_rol, a.id_aplicacion, ac.id_accion
FROM (VALUES
    (1, ARRAY['CREATE','READ','UPDATE','DELETE']),
    (2, ARRAY['CREATE','READ','UPDATE','DELETE']),
    (3, ARRAY['READ','UPDATE']),
    (4, ARRAY['READ']),
    (5, ARRAY['READ','UPDATE']),
    (6, ARRAY['CREATE','READ','UPDATE','DELETE']),
    (7, ARRAY['CREATE','READ','UPDATE']),
    (8, ARRAY['READ']),
    (9, ARRAY['READ','UPDATE'])
) AS v(id_rol, acciones)
CROSS JOIN LATERAL unnest(v.acciones) AS acc(codigo)
JOIN usuarios.aplicacion a ON a.codigo = 'RIDA'
JOIN usuarios.accion ac     ON ac.codigo = acc.codigo
ON CONFLICT (id_rol, id_aplicacion, id_accion) DO NOTHING;

COMMIT;

SELECT 'IDEMPOTENT OK v2.17.0 rida_schema' AS resultado;