-- v2.63.1_motor_ia_uso_embeddings.sql
-- Tabla de metricas de consumo de embeddings (por defecto Google Gemini Embedding).
-- Idempotente.

CREATE TABLE IF NOT EXISTS motor_ia.uso_embeddings (
    id SERIAL PRIMARY KEY,
    fecha TIMESTAMP DEFAULT NOW(),
    proveedor VARCHAR(100) NOT NULL DEFAULT 'google',
    modelo VARCHAR(150) NOT NULL,
    tipo VARCHAR(30) NOT NULL DEFAULT 'query',
    textos INTEGER NOT NULL DEFAULT 0,
    tokens_prompt INTEGER NOT NULL DEFAULT 0,
    tokens_total INTEGER NOT NULL DEFAULT 0,
    dimension INTEGER,
    exitoso BOOLEAN NOT NULL DEFAULT TRUE,
    tokens_estimados BOOLEAN NOT NULL DEFAULT FALSE,
    error TEXT
);

CREATE INDEX IF NOT EXISTS idx_uso_embeddings_fecha
    ON motor_ia.uso_embeddings(fecha);
CREATE INDEX IF NOT EXISTS idx_uso_embeddings_tipo
    ON motor_ia.uso_embeddings(tipo);
CREATE INDEX IF NOT EXISTS idx_uso_embeddings_proveedor
    ON motor_ia.uso_embeddings(proveedor);
CREATE INDEX IF NOT EXISTS idx_uso_embeddings_modelo
    ON motor_ia.uso_embeddings(modelo);
