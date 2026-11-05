-- ============================================================================
--  v2.55.0 - AYUDA HUMANITARIA: Work Queue VIDECI (pasos 4-9 de la infografia)
--  Fuente: AYUDA_HUMANITARIA_BACKEND.md v1.2
--
--  Que agrega:
--    1. rida.cat_estado_rida ........... catalogo de badges DERIVADOS (no
--                                        almacenados en solicitud).
--    2. rida.aprobacion_cadena_ayuda ... config de la cadena de 7 niveles
--                                        (evaluacion -> ... -> cierre), por
--                                        modalidad (NULL = default).
--    3. rida.aprobaciones_ayuda_humanitaria ... instancia del motor: una fila
--                                        por nivel por expediente. Cadena
--                                        SECUENCIAL (a diferencia del motor de
--                                        visaciones de solicitudes).
--    4. rida.solicitud_evaluacion ...... paso 4 (evaluacion nacional).
--    5. rida.cat_regla_calculo ......... reglas del motor de calculo DINAMICO
--                                        (cargables por API).
--    6. rida.solicitud_articulo ........ paso 5 (determinacion de articulos).
--    7. rida.entrega (ALTER) ........... REUTILIZADA como orden de despacho
--                                        (paso 7) y acta de recepcion (paso 8):
--                                        nro_orden, estado_despacho, firmas
--                                        JSONB, id_documento (PDF del acta en
--                                        el repositorio).
--    8. usuarios.rol 14 'Almacen' + permisos RIDA (READ/CREATE/UPDATE) para
--                                        los roles 3 (VIDECI Regional), 9
--                                        (VIDECI Departamental) y 14.
--
--  NOTA: la tabla rida.solicitud NO se modifica. El expediente ES la solicitud;
--        el estado de los pasos 4-9 vive en el motor y se DERIVA en cada
--        lectura (badge, dias_en_estado, asignado). Solo se actualiza
--        solicitud.etapa en los 3 anclas: EN_APROBACION / RECHAZADA / CERRADA.
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. Catalogo de badges (regla 3: el badge SE DERIVA, este es el catálogo de
--    valores que el motor puede derivar, con tono para la UI)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rida.cat_estado_rida (
    id_estado_rida SERIAL PRIMARY KEY,
    codigo         VARCHAR(40) NOT NULL UNIQUE,
    nombre         VARCHAR(80) NOT NULL,
    tono           VARCHAR(20) NOT NULL DEFAULT 'neutral'
                   CHECK (tono IN ('warning','success','info','danger','neutral')),
    orden          INT NOT NULL DEFAULT 0,
    activo         BOOLEAN NOT NULL DEFAULT TRUE
);

INSERT INTO rida.cat_estado_rida (codigo, nombre, tono, orden) VALUES
    ('EN_APROBACION',  'En aprobación',  'warning', 1),
    ('APROBADA',       'Aprobada',       'info',    2),
    ('AUTORIZADA',     'Autorizada',     'success', 3),
    ('EN_PREPARACION', 'En preparación', 'warning', 4),
    ('DESPACHADA',     'Despachada',     'info',    5),
    ('ENTREGADA',      'Entregada',      'success', 6),
    ('CERRADA',        'Cerrada',        'neutral', 7),
    ('OBSERVADA',      'Observada',      'warning', 8),
    ('RECHAZADA',      'Rechazada',      'danger',  9)
ON CONFLICT (codigo) DO NOTHING;

-- ----------------------------------------------------------------------------
-- 2. Reglas del motor de calculo (DINAMICO: se cargan/gestionan por API)
--    Cantidad = clamp(redondeo(agregacion * factor), cantidad_min, cantidad_max)
--    'condiciones' es JSONB: [{"campo":"edad","op":">=","valor":60}, ...]
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rida.cat_regla_calculo (
    id_regla           SERIAL PRIMARY KEY,
    codigo             VARCHAR(40) NOT NULL UNIQUE,
    nombre             VARCHAR(150) NOT NULL,
    id_categoria_ayuda INTEGER REFERENCES rida.cat_categoria_ayuda(id_categoria_ayuda),
    id_articulo        INTEGER NOT NULL REFERENCES rida.cat_articulo(id_articulo),
    base               VARCHAR(20) NOT NULL
                       CHECK (base IN ('familia','integrante','necesidad')),
    agregacion         VARCHAR(20) NOT NULL DEFAULT 'count'
                       CHECK (agregacion IN ('count','sum','count_familias')),
    factor             NUMERIC(12,3) NOT NULL DEFAULT 1,
    cantidad_min       NUMERIC(12,2) NOT NULL DEFAULT 0,
    cantidad_max       NUMERIC(12,2),
    redondeo           VARCHAR(10) NOT NULL DEFAULT 'techo'
                       CHECK (redondeo IN ('ninguno','techo','piso')),
    prioridad          INT NOT NULL DEFAULT 100,
    condiciones        JSONB NOT NULL DEFAULT '[]'::jsonb,
    activo             BOOLEAN NOT NULL DEFAULT TRUE,
    orden              INT NOT NULL DEFAULT 0,
    fecha_creacion     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_modificacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Semillas de ejemplo (articulos reales de cat_articulo, idempotente por codigo)
INSERT INTO rida.cat_regla_calculo
    (codigo, nombre, id_categoria_ayuda, id_articulo, base, agregacion,
     factor, cantidad_min, redondeo, prioridad, condiciones, orden)
SELECT 'REG-ARROZ',    'Arroz: 2 bolsas por familia',              12, a.id_articulo, 'familia',    'count', 2, 1, 'techo', 10, '[]'::jsonb, 1
FROM rida.cat_articulo a WHERE a.codigo = 'ALM-004'
ON CONFLICT (codigo) DO NOTHING;

INSERT INTO rida.cat_regla_calculo
    (codigo, nombre, id_categoria_ayuda, id_articulo, base, agregacion,
     factor, cantidad_min, redondeo, prioridad, condiciones, orden)
SELECT 'REG-CARPAS',   'Carpas: 1 por familia damnificada',        14, a.id_articulo, 'familia',    'count_familias', 1, 1, 'techo', 10, '[]'::jsonb, 2
FROM rida.cat_articulo a WHERE a.codigo = 'REF-001'
ON CONFLICT (codigo) DO NOTHING;

INSERT INTO rida.cat_regla_calculo
    (codigo, nombre, id_categoria_ayuda, id_articulo, base, agregacion,
     factor, cantidad_min, redondeo, prioridad, condiciones, orden)
SELECT 'REG-FRAZADA',  'Frazadas: 1 por integrante',               15, a.id_articulo, 'integrante', 'count', 1, 1, 'techo', 10, '[]'::jsonb, 3
FROM rida.cat_articulo a WHERE a.codigo = 'CAM-003'
ON CONFLICT (codigo) DO NOTHING;

INSERT INTO rida.cat_regla_calculo
    (codigo, nombre, id_categoria_ayuda, id_articulo, base, agregacion,
     factor, cantidad_min, redondeo, prioridad, condiciones, orden)
SELECT 'REG-HIG-ADULTO', 'Kit de higiene: 1 por integrante >= 12 años', 17, a.id_articulo, 'integrante', 'count', 1, 1, 'techo', 10,
       '[{"campo":"edad","op":">=","valor":12}]'::jsonb, 4
FROM rida.cat_articulo a WHERE a.codigo = 'HIG-002'
ON CONFLICT (codigo) DO NOTHING;

-- ----------------------------------------------------------------------------
-- 3. Config de la cadena de 7 niveles (por modalidad; NULL = default)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rida.aprobacion_cadena_ayuda (
    id_cadena    BIGSERIAL PRIMARY KEY,
    id_modalidad INTEGER NULL REFERENCES rida.cat_modalidad (id_modalidad) ON DELETE CASCADE,
    nivel        VARCHAR(20) NOT NULL
                 CHECK (nivel IN ('evaluacion','determinacion','autorizacion',
                                  'almacen','despacho','entrega','cierre')),
    orden        SMALLINT NOT NULL CHECK (orden >= 1 AND orden <= 7),
    activo       BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (id_modalidad, nivel)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_aprob_cadena_ayuda_default
    ON rida.aprobacion_cadena_ayuda (nivel) WHERE id_modalidad IS NULL;
CREATE INDEX IF NOT EXISTS idx_aprob_cadena_ayuda_modalidad
    ON rida.aprobacion_cadena_ayuda (id_modalidad);

INSERT INTO rida.aprobacion_cadena_ayuda (id_modalidad, nivel, orden) VALUES
    (NULL, 'evaluacion',    1),
    (NULL, 'determinacion', 2),
    (NULL, 'autorizacion',  3),
    (NULL, 'almacen',       4),
    (NULL, 'despacho',      5),
    (NULL, 'entrega',       6),
    (NULL, 'cierre',        7)
ON CONFLICT DO NOTHING;

-- ----------------------------------------------------------------------------
-- 4. Instancia del motor: una fila por nivel por expediente (SECUENCIAL)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rida.aprobaciones_ayuda_humanitaria (
    id_aprobacion BIGSERIAL PRIMARY KEY,
    id_solicitud  BIGINT NOT NULL REFERENCES rida.solicitud (id_solicitud) ON DELETE CASCADE,
    nivel         VARCHAR(20) NOT NULL
                  CHECK (nivel IN ('evaluacion','determinacion','autorizacion',
                                   'almacen','despacho','entrega','cierre')),
    estado        VARCHAR(20) NOT NULL DEFAULT 'pendiente'
                  CHECK (estado IN ('pendiente','aprobado','observado','espera_correccion')),
    observacion   TEXT,
    por           INTEGER REFERENCES usuarios.usuario (id_usuario),
    fecha         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (id_solicitud, nivel)
);

CREATE INDEX IF NOT EXISTS idx_aprob_ayuda_solicitud
    ON rida.aprobaciones_ayuda_humanitaria (id_solicitud);
CREATE INDEX IF NOT EXISTS idx_aprob_ayuda_estado
    ON rida.aprobaciones_ayuda_humanitaria (estado);

COMMENT ON TABLE rida.aprobaciones_ayuda_humanitaria IS
    'Motor SECUENCIAL de ayuda humanitaria (pasos 4-9 VIDECI). El badge, dias_en_estado y el asignado se DERIVAN de estas filas (regla 3 de AYUDA_HUMANITARIA_BACKEND.md).';

-- ----------------------------------------------------------------------------
-- 5. Paso 4: evaluacion nacional (historico, puede haber varias por expediente)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rida.solicitud_evaluacion (
    id_solicitud_evaluacion SERIAL PRIMARY KEY,
    id_solicitud            INTEGER NOT NULL REFERENCES rida.solicitud (id_solicitud) ON DELETE CASCADE,
    id_usuario_tecnico      INTEGER REFERENCES usuarios.usuario (id_usuario),
    observaciones           TEXT,
    fecha                   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_solicitud_evaluacion_sol
    ON rida.solicitud_evaluacion (id_solicitud);

-- ----------------------------------------------------------------------------
-- 6. Paso 5: determinacion de articulos (salida del motor de calculo)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rida.solicitud_articulo (
    id_solicitud_articulo SERIAL PRIMARY KEY,
    id_solicitud          INTEGER NOT NULL REFERENCES rida.solicitud (id_solicitud) ON DELETE CASCADE,
    id_articulo           INTEGER NOT NULL REFERENCES rida.cat_articulo (id_articulo),
    id_regla              INTEGER REFERENCES rida.cat_regla_calculo (id_regla),
    cantidad              NUMERIC(12,2) NOT NULL DEFAULT 0,
    unidad                VARCHAR(30),
    aprobado              BOOLEAN NOT NULL DEFAULT FALSE,
    fuente                VARCHAR(20) NOT NULL DEFAULT 'motor'
                          CHECK (fuente IN ('motor','manual')),
    observaciones         VARCHAR(500),
    fecha                 TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (id_solicitud, id_articulo)
);

CREATE INDEX IF NOT EXISTS idx_solicitud_articulo_sol
    ON rida.solicitud_articulo (id_solicitud);

-- ----------------------------------------------------------------------------
-- 7. rida.entrega: REUTILIZADA como orden de despacho (paso 7) + acta (paso 8)
-- ----------------------------------------------------------------------------
ALTER TABLE rida.entrega
    ADD COLUMN IF NOT EXISTS nro_orden VARCHAR(40),
    ADD COLUMN IF NOT EXISTS estado_despacho VARCHAR(30) DEFAULT 'GENERADA',
    ADD COLUMN IF NOT EXISTS firmas JSONB,
    ADD COLUMN IF NOT EXISTS id_documento INTEGER,
    ADD COLUMN IF NOT EXISTS observaciones_acta TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS uq_entrega_nro_orden
    ON rida.entrega (nro_orden) WHERE nro_orden IS NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'entrega_estado_despacho_check') THEN
        ALTER TABLE rida.entrega ADD CONSTRAINT entrega_estado_despacho_check
            CHECK (estado_despacho IS NULL OR
                   estado_despacho IN ('GENERADA','EN_PREPARACION','PREPARADA','DESPACHADA'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'entrega_id_documento_fkey') THEN
        ALTER TABLE rida.entrega ADD CONSTRAINT entrega_id_documento_fkey
            FOREIGN KEY (id_documento) REFERENCES repositorio.documentos (id_documento);
    END IF;
END $$;

COMMENT ON COLUMN rida.entrega.nro_orden IS
    'Orden de despacho (paso 7 ayuda humanitaria): OD-<anio>-<correlativo>. UNIQUE parcial.';
COMMENT ON COLUMN rida.entrega.estado_despacho IS
    'GENERADA|EN_PREPARACION|PREPARADA|DESPACHADA (paso 7). NULL = flujo legacy.';
COMMENT ON COLUMN rida.entrega.firmas IS
    'Acta de recepcion (paso 8): [{nombre, ci, cargo, fecha}].';
COMMENT ON COLUMN rida.entrega.id_documento IS
    'PDF del acta de recepcion en repositorio.documentos.';

-- ----------------------------------------------------------------------------
-- 8. Rol 14 'Almacen' + permisos RIDA para roles 3, 9 y 14
-- ----------------------------------------------------------------------------
INSERT INTO usuarios.rol (id_rol, nombre, descripcion)
SELECT 14, 'Almacen',
       'Gestiona el almacen: preparacion y despacho de ordenes de ayuda humanitaria'
WHERE NOT EXISTS (SELECT 1 FROM usuarios.rol WHERE id_rol = 14);

INSERT INTO usuarios.permiso (id_rol, id_aplicacion, id_accion)
SELECT r.id_rol, a.id_aplicacion, ac.id_accion
FROM (VALUES (3), (9), (14)) AS r(id_rol)
CROSS JOIN (SELECT id_aplicacion FROM usuarios.aplicacion WHERE codigo = 'RIDA') AS a
CROSS JOIN usuarios.accion AS ac
WHERE ac.codigo IN ('READ','CREATE','UPDATE')
ON CONFLICT DO NOTHING;

-- ----------------------------------------------------------------------------
-- 9. Verificacion
-- ----------------------------------------------------------------------------
DO $$
DECLARE
    n INT;
BEGIN
    SELECT COUNT(*) INTO n FROM rida.cat_estado_rida;
    IF n < 9 THEN RAISE EXCEPTION 'cat_estado_rida incompleto: % filas', n; END IF;
    SELECT COUNT(*) INTO n FROM rida.aprobacion_cadena_ayuda WHERE id_modalidad IS NULL;
    IF n < 7 THEN RAISE EXCEPTION 'cadena default incompleta: % niveles', n; END IF;
    IF NOT EXISTS (SELECT 1 FROM usuarios.rol WHERE id_rol = 14) THEN
        RAISE EXCEPTION 'rol 14 Almacen no creado';
    END IF;
    RAISE NOTICE 'IDEMPOTENT OK v2.55.0 ayuda_humanitaria';
END $$;

COMMIT;
