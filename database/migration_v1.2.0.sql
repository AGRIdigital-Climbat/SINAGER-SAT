-- ============================================
-- MIGRACIÓN v1.2.0
-- ============================================
-- Ejecutar como usuario con permisos de creación en PostgreSQL.
-- ============================================

-- UNIQUE constraint en carnet para prevenir duplicados
ALTER TABLE usuarios.usuario ADD CONSTRAINT uq_usuario_carnet UNIQUE (carnet);

-- Campo fotografia en tabla EDAN para soporte de imágenes base64
ALTER TABLE edan.edan ADD COLUMN IF NOT EXISTS fotografia TEXT;
