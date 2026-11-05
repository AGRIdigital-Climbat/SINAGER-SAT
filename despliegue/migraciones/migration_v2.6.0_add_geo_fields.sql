-- ============================================================================
-- SINAGERSAT - Migración v2.6.0 (idempotente)
-- Agrega campos fotografia, coordenada_lat, coordenada_lon a las tablas de
-- daños y servicios del EDAN (8 tablas). Permite adjuntar evidencia fotográfica
-- y geolocalización por item de daño. Todos los campos son NULLABLE para
-- preservar datos existentes (los items preexistentes quedan con NULL).
-- El frontend exigirá visualmente completar estos campos, pero la BD no los
-- requiere para mantener compatibilidad con registros antiguos.
-- Aplica sobre migration_v2.5.0.
-- ============================================================================

BEGIN;

-- 1. Daños agricultura
ALTER TABLE edan.edan_localidades_danos_agricultura
  ADD COLUMN IF NOT EXISTS fotografia VARCHAR(500) NULL,
  ADD COLUMN IF NOT EXISTS coordenada_lat DECIMAL(10,8) NULL,
  ADD COLUMN IF NOT EXISTS coordenada_lon DECIMAL(11,8) NULL;

-- 2. Daños infraestructura pública
ALTER TABLE edan.edan_localidades_danos_infra_publica
  ADD COLUMN IF NOT EXISTS fotografia VARCHAR(500) NULL,
  ADD COLUMN IF NOT EXISTS coordenada_lat DECIMAL(10,8) NULL,
  ADD COLUMN IF NOT EXISTS coordenada_lon DECIMAL(11,8) NULL;

-- 3. Daños pecuarios
ALTER TABLE edan.edan_localidades_danos_pecuario
  ADD COLUMN IF NOT EXISTS fotografia VARCHAR(500) NULL,
  ADD COLUMN IF NOT EXISTS coordenada_lat DECIMAL(10,8) NULL,
  ADD COLUMN IF NOT EXISTS coordenada_lon DECIMAL(11,8) NULL;

-- 4. Daños viales
ALTER TABLE edan.edan_localidades_danos_viales
  ADD COLUMN IF NOT EXISTS fotografia VARCHAR(500) NULL,
  ADD COLUMN IF NOT EXISTS coordenada_lat DECIMAL(10,8) NULL,
  ADD COLUMN IF NOT EXISTS coordenada_lon DECIMAL(11,8) NULL;

-- 5. Daños vivienda
ALTER TABLE edan.edan_localidades_danos_vivienda
  ADD COLUMN IF NOT EXISTS fotografia VARCHAR(500) NULL,
  ADD COLUMN IF NOT EXISTS coordenada_lat DECIMAL(10,8) NULL,
  ADD COLUMN IF NOT EXISTS coordenada_lon DECIMAL(11,8) NULL;

-- 6. Establecimientos de salud
ALTER TABLE edan.edan_localidades_salud_establecimientos
  ADD COLUMN IF NOT EXISTS fotografia VARCHAR(500) NULL,
  ADD COLUMN IF NOT EXISTS coordenada_lat DECIMAL(10,8) NULL,
  ADD COLUMN IF NOT EXISTS coordenada_lon DECIMAL(11,8) NULL;

-- 7. Servicios básicos
ALTER TABLE edan.edan_localidades_servicios_basicos
  ADD COLUMN IF NOT EXISTS fotografia VARCHAR(500) NULL,
  ADD COLUMN IF NOT EXISTS coordenada_lat DECIMAL(10,8) NULL,
  ADD COLUMN IF NOT EXISTS coordenada_lon DECIMAL(11,8) NULL;

-- 8. Unidades educativas
ALTER TABLE edan.edan_localidades_unidades_educativas
  ADD COLUMN IF NOT EXISTS fotografia VARCHAR(500) NULL,
  ADD COLUMN IF NOT EXISTS coordenada_lat DECIMAL(10,8) NULL,
  ADD COLUMN IF NOT EXISTS coordenada_lon DECIMAL(11,8) NULL;

COMMIT;

SELECT 'IDEMPOTENT OK v2.6.0' AS resultado;
