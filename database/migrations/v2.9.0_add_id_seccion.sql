-- ============================================================================
--  Migración v2.9.0: Agregar id_seccion para soporte offline-first en secciones
-- ============================================================================
--  Propósito: Permitir identificación única de secciones (1:N) en modo offline
--  para evitar duplicados durante la sincronización.
--
--  Convención id_seccion:
--    - Generado por el cliente (app móvil/web)
--    - Formato: {timestamp_base32}-{uuid_short}
--    - Ejemplo: "1a0357323cb-659d0c9c3d415"
--    - Longitud: ~24 caracteres
--    - Único: índice único parcial WHERE id_seccion IS NOT NULL
-- ============================================================================

-- ============================================================================
--  1. Tablas 1:N (agregar id_seccion)
-- ============================================================================

-- 1.1 edan_localidades_impacto_poblacion
ALTER TABLE edan.edan_localidades_impacto_poblacion 
  ADD COLUMN id_seccion VARCHAR(50);

-- 1.2 edan_localidades_salud_establecimientos
ALTER TABLE edan.edan_localidades_salud_establecimientos 
  ADD COLUMN id_seccion VARCHAR(50);

-- 1.3 edan_localidades_danos_viales
ALTER TABLE edan.edan_localidades_danos_viales 
  ADD COLUMN id_seccion VARCHAR(50);

-- 1.4 edan_localidades_danos_infra_publica
ALTER TABLE edan.edan_localidades_danos_infra_publica 
  ADD COLUMN id_seccion VARCHAR(50);

-- 1.5 edan_localidades_servicios_basicos
ALTER TABLE edan.edan_localidades_servicios_basicos 
  ADD COLUMN id_seccion VARCHAR(50);

-- 1.6 edan_localidades_unidades_educativas
ALTER TABLE edan.edan_localidades_unidades_educativas 
  ADD COLUMN id_seccion VARCHAR(50);

-- 1.7 edan_localidades_danos_vivienda
ALTER TABLE edan.edan_localidades_danos_vivienda 
  ADD COLUMN id_seccion VARCHAR(50);

-- 1.8 edan_localidades_danos_agricultura
ALTER TABLE edan.edan_localidades_danos_agricultura 
  ADD COLUMN id_seccion VARCHAR(50);

-- 1.9 edan_localidades_danos_pecuario
ALTER TABLE edan.edan_localidades_danos_pecuario 
  ADD COLUMN id_seccion VARCHAR(50);

-- 1.10 edan_localidades_infra_productiva
ALTER TABLE edan.edan_localidades_infra_productiva 
  ADD COLUMN id_seccion VARCHAR(50);

-- 1.11 edan_localidades_proteccion
ALTER TABLE edan.edan_localidades_proteccion 
  ADD COLUMN id_seccion VARCHAR(50);

-- ============================================================================
--  2. Índices únicos parciales (WHERE id_seccion IS NOT NULL)
-- ============================================================================

CREATE UNIQUE INDEX IF NOT EXISTS idx_seccion_impacto_poblacion 
  ON edan.edan_localidades_impacto_poblacion (id_seccion) 
  WHERE id_seccion IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_seccion_salud_establecimientos 
  ON edan.edan_localidades_salud_establecimientos (id_seccion) 
  WHERE id_seccion IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_seccion_danos_viales 
  ON edan.edan_localidades_danos_viales (id_seccion) 
  WHERE id_seccion IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_seccion_danos_infra_publica 
  ON edan.edan_localidades_danos_infra_publica (id_seccion) 
  WHERE id_seccion IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_seccion_servicios_basicos 
  ON edan.edan_localidades_servicios_basicos (id_seccion) 
  WHERE id_seccion IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_seccion_unidades_educativas 
  ON edan.edan_localidades_unidades_educativas (id_seccion) 
  WHERE id_seccion IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_seccion_danos_vivienda 
  ON edan.edan_localidades_danos_vivienda (id_seccion) 
  WHERE id_seccion IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_seccion_danos_agricultura 
  ON edan.edan_localidades_danos_agricultura (id_seccion) 
  WHERE id_seccion IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_seccion_danos_pecuario 
  ON edan.edan_localidades_danos_pecuario (id_seccion) 
  WHERE id_seccion IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_seccion_infra_productiva 
  ON edan.edan_localidades_infra_productiva (id_seccion) 
  WHERE id_seccion IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_seccion_proteccion 
  ON edan.edan_localidades_proteccion (id_seccion) 
  WHERE id_seccion IS NOT NULL;

-- ============================================================================
--  3. Comentario de documentación
-- ============================================================================

COMMENT ON COLUMN edan.edan_localidades_impacto_poblacion.id_seccion IS 
  'ID único generado por el cliente para sincronización offline-first. Formato: timestamp-uuid (ej: 1a0357323cb-659d0c9c3d415)';

COMMENT ON COLUMN edan.edan_localidades_salud_establecimientos.id_seccion IS 
  'ID único generado por el cliente para sincronización offline-first. Formato: timestamp-uuid (ej: 1a0357323cb-659d0c9c3d415)';

COMMENT ON COLUMN edan.edan_localidades_danos_viales.id_seccion IS 
  'ID único generado por el cliente para sincronización offline-first. Formato: timestamp-uuid (ej: 1a0357323cb-659d0c9c3d415)';

COMMENT ON COLUMN edan.edan_localidades_danos_infra_publica.id_seccion IS 
  'ID único generado por el cliente para sincronización offline-first. Formato: timestamp-uuid (ej: 1a0357323cb-659d0c9c3d415)';

COMMENT ON COLUMN edan.edan_localidades_servicios_basicos.id_seccion IS 
  'ID único generado por el cliente para sincronización offline-first. Formato: timestamp-uuid (ej: 1a0357323cb-659d0c9c3d415)';

COMMENT ON COLUMN edan.edan_localidades_unidades_educativas.id_seccion IS 
  'ID único generado por el cliente para sincronización offline-first. Formato: timestamp-uuid (ej: 1a0357323cb-659d0c9c3d415)';

COMMENT ON COLUMN edan.edan_localidades_danos_vivienda.id_seccion IS 
  'ID único generado por el cliente para sincronización offline-first. Formato: timestamp-uuid (ej: 1a0357323cb-659d0c9c3d415)';

COMMENT ON COLUMN edan.edan_localidades_danos_agricultura.id_seccion IS 
  'ID único generado por el cliente para sincronización offline-first. Formato: timestamp-uuid (ej: 1a0357323cb-659d0c9c3d415)';

COMMENT ON COLUMN edan.edan_localidades_danos_pecuario.id_seccion IS 
  'ID único generado por el cliente para sincronización offline-first. Formato: timestamp-uuid (ej: 1a0357323cb-659d0c9c3d415)';

COMMENT ON COLUMN edan.edan_localidades_infra_productiva.id_seccion IS 
  'ID único generado por el cliente para sincronización offline-first. Formato: timestamp-uuid (ej: 1a0357323cb-659d0c9c3d415)';

COMMENT ON COLUMN edan.edan.edan_localidades_proteccion.id_seccion IS 
  'ID único generado por el cliente para sincronización offline-first. Formato: timestamp-uuid (ej: 1a0357323cb-659d0c9c3d415)';

-- ============================================================================
--  Notas:
--  - Las tablas 1:1 NO requieren id_seccion (usan id_edan_localidad como PK):
--    * edan_localidades_primera_respuesta
--    * edan_localidades_salud_necesidades
--    * edan_localidades_necesidades_humanitarias
--  - El índice es parcial (WHERE id_seccion IS NOT NULL) para compatibilidad
--    con registros existentes creados antes de esta migración.
-- ============================================================================
