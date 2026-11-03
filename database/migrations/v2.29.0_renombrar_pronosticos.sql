-- ============================================================================
-- Migración v2.29.0: Renombrar tablas SINB + Modelo Observador/Recolector
-- ============================================================================
-- Fecha: 2026-10-04
-- Descripción: 
--   - Renombrar pronostico_estacional → pronostico_largo
--   - Renombrar pronostico_temporal → pronostico_corto
--   - Renombrar aviso → avisos
--   - Renombrar tablas hijas
--   - Renombrar columnas: id_usuario_elabora/emite → id_usuario_subio
--   - Renombrar columnas: valor_esperado/notas → texto_observador
--   - Agregar id_usuario_subio a pronostico_corto
--   - Agregar texto_observador a avisos
-- ============================================================================

BEGIN;

-- 1. Renombrar tablas principales
ALTER TABLE sinb.pronostico_estacional RENAME TO pronostico_largo;
ALTER TABLE sinb.pronostico_temporal RENAME TO pronostico_corto;
ALTER TABLE sinb.aviso RENAME TO avisos;

-- 2. Renombrar tablas hijas
ALTER TABLE sinb.pronostico_observador RENAME TO pronostico_largo_observador;
ALTER TABLE sinb.pronostico_temporal_observador RENAME TO pronostico_corto_observador;
ALTER TABLE sinb.aviso_observador RENAME TO avisos_observador;

-- 3. Renombrar columnas FK en tablas hijas (un statement por columna)
ALTER TABLE sinb.pronostico_largo_observador 
  RENAME COLUMN id_pronostico_estacional TO id_pronostico_largo;

ALTER TABLE sinb.pronostico_corto_observador 
  RENAME COLUMN id_pronostico_temporal TO id_pronostico_corto;

ALTER TABLE sinb.escenario_estacional 
  RENAME COLUMN id_pronostico_estacional TO id_pronostico_largo;

ALTER TABLE sinb.observacion_pronostico 
  RENAME COLUMN id_pronostico_estacional TO id_pronostico_largo;
ALTER TABLE sinb.observacion_pronostico 
  RENAME COLUMN id_pronostico_temporal TO id_pronostico_corto;

ALTER TABLE sinb.verificacion_pronostico 
  RENAME COLUMN id_pronostico_estacional TO id_pronostico_largo;
ALTER TABLE sinb.verificacion_pronostico 
  RENAME COLUMN id_pronostico_temporal TO id_pronostico_corto;

-- 4. Renombrar columnas en pronostico_largo
ALTER TABLE sinb.pronostico_largo 
  RENAME COLUMN id_usuario_elabora TO id_usuario_subio;
ALTER TABLE sinb.pronostico_largo 
  RENAME COLUMN notas TO texto_observador;

-- 5. Cambios en pronostico_corto
ALTER TABLE sinb.pronostico_corto 
  RENAME COLUMN valor_esperado TO texto_observador;
ALTER TABLE sinb.pronostico_corto 
  ADD COLUMN IF NOT EXISTS id_usuario_subio integer REFERENCES usuarios.usuario(id_usuario);

-- 6. Cambios en avisos
ALTER TABLE sinb.avisos 
  RENAME COLUMN id_usuario_emite TO id_usuario_subio;
ALTER TABLE sinb.avisos 
  ADD COLUMN IF NOT EXISTS texto_observador text;

-- 7. Recrear vista afectada
DROP VIEW IF EXISTS sinb.v_verificaciones_pendientes;
CREATE VIEW sinb.v_verificaciones_pendientes AS
SELECT v.id,
  COALESCE(pl.codigo, pc.codigo) AS pronostico_codigo,
  COALESCE(pl.periodo_fin, pc.fecha_fin) AS fecha_fin,
  v.estado, v.creado_en
FROM sinb.verificacion_pronostico v
LEFT JOIN sinb.pronostico_largo pl ON pl.id = v.id_pronostico_largo
LEFT JOIN sinb.pronostico_corto pc ON pc.id = v.id_pronostico_corto
WHERE v.estado = 'NO_VERIFICABLE'
  AND COALESCE(pl.periodo_fin, pc.fecha_fin) < CURRENT_DATE
ORDER BY COALESCE(pl.periodo_fin, pc.fecha_fin) DESC;

COMMENT ON VIEW sinb.v_verificaciones_pendientes IS 
  'Verificaciones pendientes de pronósticos (largo y corto plazo)';

COMMIT;

-- ============================================================================
-- Fin migración v2.29.0
-- ============================================================================
