-- =============================================================================
-- v2.58.0 — Ciclo de vida de reglas del motor de cálculo + historial de ejecuciones
-- (contrato /calculos: estados borrador/publicada, versiones inmutables JSONB,
--  detalle de ejecución por familia)
-- Idempotente: puede aplicarse 2 veces sin efecto adverso.
-- =============================================================================

-- 1. Estado del ciclo de vida en la regla existente ---------------------------
-- Las reglas existentes pasan a 'publicada' para no alterar el comportamiento
-- del motor (solo las publicadas corren).
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='rida' AND table_name='regla_calculo_kit' AND column_name='estado'
  ) THEN
    ALTER TABLE rida.regla_calculo_kit
      ADD COLUMN estado VARCHAR(20) NOT NULL DEFAULT 'borrador';
    UPDATE rida.regla_calculo_kit SET estado = 'publicada';
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'regla_calculo_kit_estado_check'
  ) THEN
    ALTER TABLE rida.regla_calculo_kit
      ADD CONSTRAINT regla_calculo_kit_estado_check
      CHECK (estado IN ('borrador','publicada'));
  END IF;
END $$;

-- 1b. Snapshot de versión 1 para reglas publicadas sin versiones --------------
-- (las reglas migradas a 'publicada' necesitan su versión para que el
--  historial de ejecuciones pueda referenciar la configuración exacta usada).
DO $$
DECLARE
  r RECORD;
  det jsonb;
BEGIN
  FOR r IN SELECT k.* FROM rida.regla_calculo_kit k
           WHERE k.estado = 'publicada'
             AND NOT EXISTS (SELECT 1 FROM rida.regla_calculo_version v
                             WHERE v.id_regla = k.id_regla)
  LOOP
    SELECT COALESCE(jsonb_agg(jsonb_build_object(
             'id_articulo', d.id_articulo,
             'cantidad_base_diaria', d.cantidad_base_diaria,
             'cantidad_min', d.cantidad_min,
             'cantidad_max', d.cantidad_max) ORDER BY d.id_detalle_regla), '[]'::jsonb)
      INTO det
      FROM rida.detalle_parametro_kit d
      WHERE d.id_regla = r.id_regla;
    INSERT INTO rida.regla_calculo_version
        (id_regla, numero_version, configuracion_json, publicado_por)
    VALUES (r.id_regla, 1, jsonb_build_object(
        'nombre_regla', r.nombre_regla,
        'criterio_aplicacion', r.criterio_aplicacion,
        'rango_edad_min_dias', r.rango_edad_min_dias,
        'rango_edad_max_dias', r.rango_edad_max_dias,
        'requiere_gestante', r.requiere_gestante,
        'requiere_discapacidad', r.requiere_discapacidad,
        'sexo', r.sexo,
        'dias_duracion', r.dias_duracion,
        'redondeo', r.redondeo,
        'prioridad', r.prioridad,
        'orden', r.orden,
        'estado', 'publicada',
        'detalles', det), NULL);
  END LOOP;
END $$;

-- 2. Versiones inmutables (configuración exacta publicada) --------------------
CREATE TABLE IF NOT EXISTS rida.regla_calculo_version (
  id_version         BIGSERIAL PRIMARY KEY,
  id_regla           INT NOT NULL REFERENCES rida.regla_calculo_kit ON DELETE CASCADE,
  numero_version     INT NOT NULL,
  configuracion_json JSONB NOT NULL,
  fecha_publicacion  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  publicado_por      INT,
  CONSTRAINT regla_calculo_version_unica UNIQUE (id_regla, numero_version)
);

-- 3. Historial de ejecuciones (solo el modo operativo se registra) ------------
CREATE TABLE IF NOT EXISTS rida.ejecucion_calculo (
  id_calculo      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  id_solicitud    INT NOT NULL REFERENCES rida.solicitud(id_solicitud) ON DELETE CASCADE,
  modo            VARCHAR(20) NOT NULL DEFAULT 'operativo'
                  CHECK (modo IN ('previsualizacion','operativo')),
  estado          VARCHAR(20) NOT NULL DEFAULT 'completado',
  fecha_ejecucion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  id_usuario      INT
);

CREATE INDEX IF NOT EXISTS idx_ejecucion_calculo_solicitud
  ON rida.ejecucion_calculo (id_solicitud, fecha_ejecucion DESC);

-- 4. Detalle de ejecución por familia y artículo ------------------------------
CREATE TABLE IF NOT EXISTS rida.ejecucion_calculo_detalle (
  id_detalle         BIGSERIAL PRIMARY KEY,
  id_calculo         UUID NOT NULL REFERENCES rida.ejecucion_calculo ON DELETE CASCADE,
  id_familia         INT NOT NULL REFERENCES rida.familia(id_familia),
  id_regla           INT NOT NULL REFERENCES rida.regla_calculo_kit(id_regla),
  id_version         INT NOT NULL REFERENCES rida.regla_calculo_version(id_version),
  id_articulo        INT NOT NULL REFERENCES rida.cat_articulo(id_articulo),
  cantidad_calculada NUMERIC(12,2) NOT NULL,
  unidad_medida      VARCHAR(20),
  CONSTRAINT ejecucion_calculo_detalle_unica
    UNIQUE (id_calculo, id_familia, id_regla, id_articulo)
);

CREATE INDEX IF NOT EXISTS idx_ejecucion_detalle_calculo
  ON rida.ejecucion_calculo_detalle (id_calculo);
