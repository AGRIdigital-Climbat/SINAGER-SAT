-- ============================================================================
--  v2.57.0 - NUEVO MOTOR DE CALCULO POR KITS (Ayuda Humanitaria)
--
--  Que hace:
--    1. rida.regla_calculo_kit ....... catalogo de reglas por KIT (nombre,
--                                       criterio de aplicacion, rango de edad
--                                       en dias, sexo, requiere gestante/
--                                       discapacidad, dias de duracion libres,
--                                       redondeo, prioridad).
--    2. rida.detalle_parametro_kit ... articulos que componen cada kit con
--                                       su cantidad base DIARIA y minimos/
--                                       maximos por articulo (UNIQUE por
--                                       id_regla + id_articulo).
--    3. solicitud_articulo (ALTER) ... re-apunta id_regla de intro
--                                       cat_regla_calculo (obsoleto) al nuevo
--                                       regla_calculo_kit.
--    4. DROP rida.cat_regla_calculo ... el motor anterior (v2.55.0) se
--                                       REEMPLAZA; la BD drena los datos de
--                                       prueba, no hay transicion.
--
--  Idempotente: se puede aplicar mas de una vez.
-- ============================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS rida.regla_calculo_kit (
    id_regla               serial PRIMARY KEY,
    nombre_regla           varchar(100) NOT NULL,
    criterio_aplicacion    varchar(30)  NOT NULL
                           CHECK (criterio_aplicacion IN
                                  ('POR_FAMILIA', 'POR_INTEGRANTE', 'POR_CONDICION_ESPECIAL')),
    rango_edad_min_dias    integer CHECK (rango_edad_min_dias >= 0),
    rango_edad_max_dias    integer CHECK (rango_edad_max_dias >= 0),
    requiere_gestante      boolean NOT NULL DEFAULT FALSE,
    requiere_discapacidad  boolean NOT NULL DEFAULT FALSE,
    sexo                   char(1) CHECK (sexo IN ('M', 'F')),
    dias_duracion          integer CHECK (dias_duracion > 0),
    redondeo               varchar(10) NOT NULL DEFAULT 'piso'
                           CHECK (redondeo IN ('ninguno', 'techo', 'piso')),
    prioridad              integer NOT NULL DEFAULT 100,
    activo                 boolean NOT NULL DEFAULT TRUE,
    orden                  integer NOT NULL DEFAULT 0,
    fecha_creacion         timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_modificacion     timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_regla_edad_min_max CHECK (
        rango_edad_min_dias IS NULL OR rango_edad_max_dias IS NULL
        OR rango_edad_min_dias <= rango_edad_max_dias)
);

CREATE TABLE IF NOT EXISTS rida.detalle_parametro_kit (
    id_detalle_regla     serial PRIMARY KEY,
    id_regla             integer NOT NULL
                         REFERENCES rida.regla_calculo_kit(id_regla) ON DELETE CASCADE,
    id_articulo          integer NOT NULL
                         REFERENCES rida.cat_articulo(id_articulo) ON DELETE RESTRICT,
    cantidad_base_diaria numeric(8, 3) NOT NULL DEFAULT 0
                         CHECK (cantidad_base_diaria >= 0),
    cantidad_min         numeric(12, 2),
    cantidad_max         numeric(12, 2),
    CONSTRAINT uq_detalle_regla_articulo UNIQUE (id_regla, id_articulo)
);

-- Re-apunta solicitud_articulo.id_regla al nuevo catalogo de kits.
DO $$
DECLARE
    fk_name text;
BEGIN
    SELECT conname INTO fk_name
      FROM pg_constraint
     WHERE conrelid = 'rida.solicitud_articulo'::regclass
       AND contype = 'f'
       AND confrelid = to_regclass('rida.cat_regla_calculo')
     LIMIT 1;
    IF fk_name IS NOT NULL THEN
        EXECUTE format('ALTER TABLE rida.solicitud_articulo DROP CONSTRAINT %I', fk_name);
    END IF;

    -- Anula referencias que no existen en el nuevo catalogo (datos de prueba).
    UPDATE rida.solicitud_articulo
       SET id_regla = NULL
     WHERE id_regla IS NOT NULL
       AND NOT EXISTS (SELECT 1 FROM rida.regla_calculo_kit k
                       WHERE k.id_regla = rida.solicitud_articulo.id_regla);

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'solicitud_articulo_id_regla_fkey'
          AND conrelid = 'rida.solicitud_articulo'::regclass
    ) THEN
        ALTER TABLE rida.solicitud_articulo
            ADD CONSTRAINT solicitud_articulo_id_regla_fkey
            FOREIGN KEY (id_regla) REFERENCES rida.regla_calculo_kit(id_regla);
    END IF;
END $$;

-- DROP del motor anterior (v2.55.0): se REEMPLAZA por regla_calculo_kit.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'rida' AND table_name = 'cat_regla_calculo'
    ) THEN
        DROP TABLE rida.cat_regla_calculo;
    END IF;
    RAISE NOTICE 'IDEMPOTENT OK v2.57.0 regla_calculo_kit';
END $$;

-- ============================================================================
--  Seeds (datos de ejemplo cargables por la API)
-- ============================================================================

-- Kit 1: Racion Alimentaria Familiar Estandar (por familia, 30 dias).
INSERT INTO rida.regla_calculo_kit
    (nombre_regla, criterio_aplicacion, dias_duracion, redondeo, prioridad, orden)
SELECT 'Ración Alimentaria Familiar Estándar', 'POR_FAMILIA', 30, 'piso', 1, 1
 WHERE NOT EXISTS (SELECT 1 FROM rida.regla_calculo_kit
                   WHERE nombre_regla = 'Ración Alimentaria Familiar Estándar');

-- Kit 2: Kit de Higiene Infantil (por integrante de 0 a 2 anios, per vez).
INSERT INTO rida.regla_calculo_kit
    (nombre_regla, criterio_aplicacion, rango_edad_max_dias,
     dias_duracion, redondeo, prioridad, orden)
SELECT 'Kit de Higiene Infantil (0-2 años)', 'POR_INTEGRANTE', 730,
       1, 'piso', 2, 2
 WHERE NOT EXISTS (SELECT 1 FROM rida.regla_calculo_kit
                   WHERE nombre_regla = 'Kit de Higiene Infantil (0-2 años)');

-- Detalles de los kits (idempotente por UNIQUE id_regla+id_articulo).
INSERT INTO rida.detalle_parametro_kit
    (id_regla, id_articulo, cantidad_base_diaria, cantidad_min, cantidad_max)
SELECT k.id_regla, a.id_articulo, d.base_diaria::numeric,
       d.minimo::numeric, d.maximo::numeric
  FROM (VALUES
            ('Ración Alimentaria Familiar Estándar', 'ALM-004', 0.500, 1, NULL),
            ('Ración Alimentaria Familiar Estándar', 'ALM-005', 0.250, 1, NULL),
            ('Ración Alimentaria Familiar Estándar', 'COC-001', 0.050, 0, NULL),
            ('Kit de Higiene Infantil (0-2 años)',   'HIG-002', 1.000, 1, NULL)
       ) AS d(kit, codigo, base_diaria, minimo, maximo)
  JOIN rida.regla_calculo_kit k ON k.nombre_regla = d.kit
  JOIN rida.cat_articulo a ON a.codigo = d.codigo
ON CONFLICT (id_regla, id_articulo) DO NOTHING;

COMMIT;