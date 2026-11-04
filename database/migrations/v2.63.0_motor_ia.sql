-- Integracion de MotorIA en db_sinagersat
-- Esquema separado: motor_ia
-- Idempotente: se puede ejecutar mas de una vez sin duplicar datos.

BEGIN;

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE SCHEMA IF NOT EXISTS motor_ia;

CREATE TABLE IF NOT EXISTS motor_ia.tipos_documento (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE,
    prioridad INTEGER NOT NULL,
    activo BOOLEAN DEFAULT TRUE
);

INSERT INTO motor_ia.tipos_documento (nombre, prioridad) VALUES
('Constitución', 1),
('Tratado', 2),
('Ley Nacional', 3),
('DS (Decreto Supremo)', 4),
('Resolución Suprema', 5),
('RM (Resolución Ministerial)', 6),
('Resolución Administrativa', 7),
('Reglamento', 8),
('Estatuto Autonómico Departamental', 9),
('Ley Departamental', 10),
('Decreto Departamental', 11),
('Resolución Departamental', 12),
('Carta Orgánica Municipal', 13),
('Ley Municipal', 14),
('Decreto Municipal', 15),
('Ordenanza Municipal', 16),
('Resolución Municipal', 17),
('Guía', 18),
('Manual', 19)
ON CONFLICT (nombre) DO NOTHING;

CREATE TABLE IF NOT EXISTS motor_ia.documentos (
    id SERIAL PRIMARY KEY,
    titulo VARCHAR(500) NOT NULL,
    tipo_id INTEGER REFERENCES motor_ia.tipos_documento(id),
    fecha_publicacion DATE,
    archivo_path VARCHAR(500),
    num_paginas INTEGER,
    contenido_completo TEXT,
    metadatos JSONB,
    creado_en TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS motor_ia.chunks (
    id SERIAL PRIMARY KEY,
    documento_id INTEGER REFERENCES motor_ia.documentos(id) ON DELETE CASCADE,
    contenido TEXT NOT NULL,
    numeral VARCHAR(100),
    orden INTEGER,
    embedding vector(384)
);

CREATE TABLE IF NOT EXISTS motor_ia.proveedores_llm (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE,
    base_url VARCHAR(255) NOT NULL,
    apikey TEXT,
    modelo_base VARCHAR(150) NOT NULL,
    estado_manual BOOLEAN DEFAULT TRUE,
    estado_modelo BOOLEAN DEFAULT FALSE,
    ultima_verificacion TIMESTAMP,
    fecha_creacion TIMESTAMP DEFAULT NOW(),
    razonamiento_tokens INTEGER DEFAULT 0
);

ALTER TABLE motor_ia.proveedores_llm
    ADD COLUMN IF NOT EXISTS razonamiento_tokens INTEGER DEFAULT 0;

CREATE TABLE IF NOT EXISTS motor_ia.uso_llm (
    id SERIAL PRIMARY KEY,
    fecha TIMESTAMP DEFAULT NOW(),
    proveedor_id INTEGER REFERENCES motor_ia.proveedores_llm(id) ON DELETE SET NULL,
    proveedor_nombre VARCHAR(100),
    modelo VARCHAR(150),
    tipo VARCHAR(30) DEFAULT 'chat',
    tokens_prompt INTEGER DEFAULT 0,
    tokens_completados INTEGER DEFAULT 0,
    tokens_total INTEGER DEFAULT 0,
    exitoso BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS motor_ia.grupo_documentos (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(200) NOT NULL UNIQUE,
    descripcion TEXT,
    creado_en TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS motor_ia.grupo_documentos_items (
    grupo_id INTEGER REFERENCES motor_ia.grupo_documentos(id) ON DELETE CASCADE,
    documento_id INTEGER REFERENCES motor_ia.documentos(id) ON DELETE CASCADE,
    PRIMARY KEY (grupo_id, documento_id)
);

-- Indices de busqueda
CREATE INDEX IF NOT EXISTS idx_chunks_embedding
    ON motor_ia.chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_chunks_contenido_trgm
    ON motor_ia.chunks USING gin (contenido gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_chunks_documento
    ON motor_ia.chunks(documento_id);
CREATE INDEX IF NOT EXISTS idx_documentos_tipo
    ON motor_ia.documentos(tipo_id);
CREATE INDEX IF NOT EXISTS idx_documentos_creado_en
    ON motor_ia.documentos(creado_en DESC);
CREATE INDEX IF NOT EXISTS idx_proveedores_llm_nombre
    ON motor_ia.proveedores_llm(nombre);
CREATE INDEX IF NOT EXISTS idx_proveedores_llm_estado
    ON motor_ia.proveedores_llm(estado_manual);
CREATE INDEX IF NOT EXISTS idx_uso_llm_fecha
    ON motor_ia.uso_llm(fecha);
CREATE INDEX IF NOT EXISTS idx_uso_llm_modelo
    ON motor_ia.uso_llm(modelo);
CREATE INDEX IF NOT EXISTS idx_uso_llm_tipo
    ON motor_ia.uso_llm(tipo);
CREATE INDEX IF NOT EXISTS idx_grupo_items_documento
    ON motor_ia.grupo_documentos_items(documento_id);

-- Permisos para el rol de la API
GRANT USAGE ON SCHEMA motor_ia TO sinagersat;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA motor_ia TO sinagersat;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA motor_ia TO sinagersat;
ALTER DEFAULT PRIVILEGES IN SCHEMA motor_ia GRANT ALL ON TABLES TO sinagersat;
ALTER DEFAULT PRIVILEGES IN SCHEMA motor_ia GRANT ALL ON SEQUENCES TO sinagersat;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA motor_ia GRANT ALL ON TABLES TO sinagersat;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA motor_ia GRANT ALL ON SEQUENCES TO sinagersat;

COMMENT ON SCHEMA motor_ia IS 'MotorIA: documentos, chunks vectoriales, proveedores LLM y uso.';

COMMIT;
