-- ============================================
-- MIGRACIÓN v1.2.1
-- ============================================
-- Ejecutar como usuario con permisos de creación en PostgreSQL.
-- ============================================

-- Corregir campo fotografia en REA: VARCHAR(500) → TEXT para guardar paths
ALTER TABLE rea.reporte_evento ALTER COLUMN fotografia TYPE TEXT;
