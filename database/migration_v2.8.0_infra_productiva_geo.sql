-- ============================================================================
-- SINAGERSAT - Migración v2.8.0 (idempotente)
-- Agrega campos fotografia, coordenada_lat, coordenada_lon a la tabla
-- edan.edan_localidades_infra_productiva (sección 9.3 del formulario).
-- La migración v2.6.0 agregó estos campos a las otras 8 tablas de daños/servicios
-- pero omitió infra_productiva. Todos los campos son NULLABLE para preservar
-- datos existentes.
-- Aplica sobre migration_v2.7.3.
-- ============================================================================

BEGIN;

-- Infraestructura productiva (1:N)
ALTER TABLE edan.edan_localidades_infra_productiva
  ADD COLUMN IF NOT EXISTS fotografia VARCHAR(500) NULL,
  ADD COLUMN IF NOT EXISTS coordenada_lat DECIMAL(10,8) NULL,
  ADD COLUMN IF NOT EXISTS coordenada_lon DECIMAL(11,8) NULL;

COMMIT;

SELECT 'IDEMPOTENT OK v2.8.0' AS resultado;
