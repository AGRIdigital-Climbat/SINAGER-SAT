-- ============================================================================
-- SINAGERSAT - Migración v2.24.0 (idempotente)
-- RIDA: jerarquía PADRE/HIJO del evento RIDA
--
-- El RIDA es un módulo independiente que solo nace del EDAN aprobado.
-- Se introduce la tabla explícita PADRE `rida.evento_rida` (1:1 con el EDAN).
-- La tabla SOLO guarda IDs (id_edan, id_estado, id_usuario); nadie desnormaliza
-- campos del EDAN (tipo evento, geografía, alcalde/UGR, localidades): esos
-- nodos se desglosan por JOIN en la API (patrón id-empotente).
--
-- Los HIJO son los formularios existentes `rida.formulario_rida` (1:1 por
-- localidad), que reciben `id_evento_rida` como FK al padre.
--
-- Flujo:
--   1) POST habilitar  -> crea el PADRE + auto-crea los HIJO (uno por localidad)
--      del EDAN aprobado, quedando listos para el empadronamiento manual.
--   2) POST cerrar     -> marca el PADRE como CERRADO (auditoría: quién/cuándo).
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. Catálogo de estados del evento RIDA
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rida.cat_estado_evento (
    id_estado_evento SERIAL PRIMARY KEY,
    codigo           VARCHAR(30) UNIQUE NOT NULL,
    nombre           VARCHAR(80)  NOT NULL,
    descripcion      TEXT,
    orden            INTEGER,
    activo           BOOLEAN DEFAULT TRUE
);

INSERT INTO rida.cat_estado_evento (codigo, nombre, descripcion, orden, activo)
VALUES
    ('HABILITADO', 'Habilitado', 'Evento RIDA habilitado a partir del EDAN aprobado', 1, TRUE),
    ('CERRADO',    'Cerrado',    'Evento RIDA cerrado',                                 2, TRUE)
ON CONFLICT (codigo) DO NOTHING;

-- ----------------------------------------------------------------------------
-- 2. Tabla PADRE: rida.evento_rida
--    Guarda SOLO ids. El detalle (tipo evento, fecha, geografía, alcalde/UGR,
--    localidades) se resuelve vía JOIN a edan.edan en la API.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rida.evento_rida (
    id_evento_rida     SERIAL PRIMARY KEY,
    id_edan            BIGINT     NOT NULL UNIQUE REFERENCES edan.edan(id_edan),
    id_estado          INTEGER    NOT NULL DEFAULT 1 REFERENCES rida.cat_estado_evento(id_estado_evento),
    id_usuario_habilito INTEGER   REFERENCES usuarios.usuario(id_usuario),
    fecha_habilitacion TIMESTAMP  DEFAULT CURRENT_TIMESTAMP,
    id_usuario_cierro  INTEGER    REFERENCES usuarios.usuario(id_usuario),
    fecha_cierre       TIMESTAMP,
    fecha_creacion     TIMESTAMP  DEFAULT CURRENT_TIMESTAMP,
    fecha_modificacion TIMESTAMP  DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE rida.evento_rida IS
'PADRE del RIDA. 1:1 con edan.edan aprobado. Solo guarda ids; el desglose se hace por JOIN en la API.';

-- ----------------------------------------------------------------------------
-- 3. HIJO: rida.formulario_rida recibe el vínculo explícito al padre
-- ----------------------------------------------------------------------------
ALTER TABLE rida.formulario_rida
    ADD COLUMN IF NOT EXISTS id_evento_rida INTEGER
        REFERENCES rida.evento_rida(id_evento_rida);

CREATE INDEX IF NOT EXISTS idx_formulario_rida_id_evento_rida
    ON rida.formulario_rida (id_evento_rida);

SELECT 'IDEMPOTENT OK v2.24.0 evento_rida';

COMMIT;