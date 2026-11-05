-- ============================================================================
-- SINAGERSAT - Migración v2.40.0 (idempotente)
-- RIDA: semántica habilitar / deshabilitar / cerrar del evento_rida
--
--   * HABILITAR  : crea el PADRE + HIJOS (vacíos) a partir del EDAN aprobado.
--   * DESHABILITAR: lo contrario de habilitar (habilitación por error, sin
--     datos). Es borrado FÍSICO del PADRE y sus HIJOS -> libera id_edan para
--     volver a habilitar (el UNIQUE(id_edan) lo exigía). Reemplaza al antiguo
--     "anular" (flag), que era inservible: habilitar auto-crea HIJOS y anular
--     los exigía cero.
--   * CERRAR     : terminal. Llena id_usuario_cierro + fecha_cierre con la
--     hora del sistema de Bolivia (America/La_Paz) y estado CERRADO.
--
-- Invariante en BD (trigger): fecha_cierre/id_usuario_cierro solo existen
-- cuando el estado es CERRADO; al pasar a CERRADO la fecha es obligatoria;
-- un CERRADO no se reabre. El trigger se resuelve por `codigo`, nunca por id.
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. Catálogo oficializado por `codigo` (clave canónica, ids estables).
--    Los estados intermedios HABILITAR/EN PROCESO/ATENDIDO existían solo a
--    mano en la BD; aquí quedan versionados.
-- ----------------------------------------------------------------------------
INSERT INTO rida.cat_estado_evento (codigo, nombre, descripcion, orden, activo)
VALUES
    ('HABILITADO', 'Habilitado',  'Evento RIDA habilitado a partir del EDAN aprobado', 1, TRUE),
    ('HABILITAR',  'Habilitar',   'Evento RIDA por habilitar',                          2, TRUE),
    ('EN PROCESO', 'En Proceso',  'Evento RIDA en proceso',                             3, TRUE),
    ('ATENDIDO',   'En Atención', 'Evento RIDA en atención',                            4, TRUE),
    ('CERRADO',    'Cerrado',     'Evento RIDA cerrado',                                5, TRUE)
ON CONFLICT (codigo) DO UPDATE
    SET nombre      = EXCLUDED.nombre,
        descripcion = EXCLUDED.descripcion,
        orden       = EXCLUDED.orden,
        activo      = EXCLUDED.activo;

-- ----------------------------------------------------------------------------
-- 2. Datos históricos: todo evento con fecha_cierre debe apuntar a CERRADO.
--    (El id 2 fue renumerado a mano y dejó los cierres apuntando a 'HABILITAR'.)
-- ----------------------------------------------------------------------------
UPDATE rida.evento_rida ev
SET id_estado = ce.id_estado_evento
FROM rida.cat_estado_evento ce
WHERE ce.codigo = 'CERRADO'
  AND ev.fecha_cierre IS NOT NULL
  AND ev.id_estado <> ce.id_estado_evento;

-- ----------------------------------------------------------------------------
-- 3. El "anular" lógico desaparece: lo reemplaza DESHABILITAR (borrado físico).
-- ----------------------------------------------------------------------------
ALTER TABLE rida.evento_rida
    DROP COLUMN IF EXISTS anulado,
    DROP COLUMN IF EXISTS id_usuario_anulo,
    DROP COLUMN IF EXISTS fecha_anulacion;

-- ----------------------------------------------------------------------------
-- 4. Defaults de hora boliviana, independientes de la config del servidor.
-- ----------------------------------------------------------------------------
ALTER TABLE rida.evento_rida
    ALTER COLUMN fecha_habilitacion SET DEFAULT (NOW() AT TIME ZONE 'America/La_Paz'),
    ALTER COLUMN fecha_creacion     SET DEFAULT (NOW() AT TIME ZONE 'America/La_Paz'),
    ALTER COLUMN fecha_modificacion SET DEFAULT (NOW() AT TIME ZONE 'America/La_Paz');

-- ----------------------------------------------------------------------------
-- 5. Trigger de la invariante fecha_cierre <-> CERRADO.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION rida.f_trg_evento_rida_cierre() RETURNS trigger AS $$
DECLARE
    v_codigo VARCHAR(30);
BEGIN
    SELECT codigo INTO v_codigo
    FROM rida.cat_estado_evento
    WHERE id_estado_evento = NEW.id_estado;

    IF v_codigo IS NULL THEN
        RAISE EXCEPTION 'id_estado % no existe en rida.cat_estado_evento', NEW.id_estado;
    END IF;

    -- Cerrar sin hora: se rellena automáticamente con la hora de Bolivia.
    IF v_codigo = 'CERRADO' AND NEW.fecha_cierre IS NULL THEN
        NEW.fecha_cierre := (NOW() AT TIME ZONE 'America/La_Paz');
    END IF;

    IF v_codigo <> 'CERRADO' AND (NEW.fecha_cierre IS NOT NULL OR NEW.id_usuario_cierro IS NOT NULL) THEN
        RAISE EXCEPTION 'fecha_cierre/id_usuario_cierro solo admiten con estado CERRADO (estado actual: %)', v_codigo;
    END IF;

    IF TG_OP = 'UPDATE' THEN
        IF EXISTS (SELECT 1 FROM rida.cat_estado_evento
                   WHERE id_estado_evento = OLD.id_estado AND codigo = 'CERRADO')
           AND v_codigo <> 'CERRADO' THEN
            RAISE EXCEPTION 'Un evento RIDA CERRADO es terminal; no se puede reabrir';
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_evento_rida_cierre ON rida.evento_rida;
CREATE TRIGGER trg_evento_rida_cierre
    BEFORE INSERT OR UPDATE ON rida.evento_rida
    FOR EACH ROW EXECUTE FUNCTION rida.f_trg_evento_rida_cierre();

SELECT 'IDEMPOTENT OK v2.40.0 evento_rida deshabilitar/cerrar';

COMMIT;
