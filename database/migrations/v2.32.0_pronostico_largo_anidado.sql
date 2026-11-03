-- ============================================================================
-- SINAGERSAT API v2.32.0
-- Pronóstico de Largo Plazo: borrado de estructura previa + contrato anidado
-- (propuesta/15-REGISTRO-PRONOSTICO-LARGO-PLAZO.md)
--
-- - Se eliminan las tablas transaccionales de largo plazo (237 filas + hijas).
--   NO se respalda ni se hace backfill: arranque limpio.
-- - Catálogos intactos: grupo, indicador_natural, caracteristica, comportamiento,
--   categoria_pronostico, escenario, categoria_recomendacion, recomendacion_local.
-- - Estructura nueva: cabecera con cadena biocultural + contexto, ítems de
--   pronóstico con sus escenarios, recomendaciones con comportamientos de siembra.
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. OBJETOS QUE DEPENDEN DE LA ESTRUCTURA VIEJA
-- ----------------------------------------------------------------------------
DROP VIEW IF EXISTS sinb.v_verificaciones_pendientes;

ALTER TABLE sinb.verificacion_pronostico
    DROP CONSTRAINT IF EXISTS verificacion_pronostico_id_pronostico_estacional_fkey;

DROP TABLE IF EXISTS sinb.escenario_estacional;
DROP TABLE IF EXISTS sinb.pronostico_largo_observador;
DROP TABLE IF EXISTS sinb.pronostico_largo;

-- ----------------------------------------------------------------------------
-- 2. CATÁLOGOS NUEVOS: recomendación de siembra
--    (t_recomendaciones y t_comportamientos del dump legacy)
-- ----------------------------------------------------------------------------
CREATE TABLE sinb.recomendacion (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre      varchar(100) NOT NULL UNIQUE,
    estado      sinb.estado_registro NOT NULL DEFAULT 'ACTIVO',
    creado_en   timestamptz NOT NULL DEFAULT now()
);

INSERT INTO sinb.recomendacion (id, nombre) VALUES
    ('a1111111-0000-4000-8000-000000000001', 'Epoca de siembra'),
    ('a1111111-0000-4000-8000-000000000002', 'Lugar de siembra');

CREATE TABLE sinb.comportamiento_recomendacion (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    id_recomendacion uuid NOT NULL REFERENCES sinb.recomendacion(id) ON DELETE RESTRICT,
    nombre          varchar(100) NOT NULL,
    estado          sinb.estado_registro NOT NULL DEFAULT 'ACTIVO',
    creado_en       timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_comport_recom UNIQUE (id_recomendacion, nombre)
);

INSERT INTO sinb.comportamiento_recomendacion (id, id_recomendacion, nombre) VALUES
    ('b1111111-0000-4000-8000-000000000001', 'a1111111-0000-4000-8000-000000000001', 'Retrasada'),
    ('b1111111-0000-4000-8000-000000000002', 'a1111111-0000-4000-8000-000000000001', 'Adelantada'),
    ('b1111111-0000-4000-8000-000000000003', 'a1111111-0000-4000-8000-000000000001', 'Intermedia'),
    ('b1111111-0000-4000-8000-000000000004', 'a1111111-0000-4000-8000-000000000001', 'Tardia'),
    ('b1111111-0000-4000-8000-000000000005', 'a1111111-0000-4000-8000-000000000002', 'Retrasada'),
    ('b1111111-0000-4000-8000-000000000006', 'a1111111-0000-4000-8000-000000000002', 'Bajos'),
    ('b1111111-0000-4000-8000-000000000007', 'a1111111-0000-4000-8000-000000000002', 'Altos'),
    ('b1111111-0000-4000-8000-000000000008', 'a1111111-0000-4000-8000-000000000002', 'Secos'),
    ('b1111111-0000-4000-8000-000000000009', 'a1111111-0000-4000-8000-000000000002', 'Repetir lugar'),
    ('b1111111-0000-4000-8000-000000000010', 'a1111111-0000-4000-8000-000000000002', 'Humedos');

-- ----------------------------------------------------------------------------
-- 3. INTEGRIDAD DE LA CADENA (FK compuestas: grupo → indicador →
--    característica → comportamiento). Habilita el error CADENA_INCOHERENTE
--    a nivel de base de datos (05-APIS §5).
-- ----------------------------------------------------------------------------
ALTER TABLE sinb.indicador_natural
    ADD CONSTRAINT uq_indicador_grupo UNIQUE (id, id_grupo);
ALTER TABLE sinb.caracteristica
    ADD CONSTRAINT uq_caracteristica_indicador UNIQUE (id, id_indicador_natural);
ALTER TABLE sinb.comportamiento
    ADD CONSTRAINT uq_comportamiento_caracteristica UNIQUE (id, id_caracteristica);

-- ----------------------------------------------------------------------------
-- 4. CABECERA DEL PRONÓSTICO DE LARGO PLAZO
-- ----------------------------------------------------------------------------
CREATE TABLE sinb.pronostico_largo (
    id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    codigo                varchar(50) NOT NULL UNIQUE,
    fecha_emision         date NOT NULL DEFAULT current_date,
    periodo_inicio        date NOT NULL,
    periodo_fin           date NOT NULL,
    estado                sinb.estado_validacion NOT NULL DEFAULT 'EMITIDO',
    id_usuario_subio      integer REFERENCES usuarios.usuario(id_usuario) ON DELETE SET NULL,
    id_municipio          integer REFERENCES shared.municipio(id) ON DELETE RESTRICT,
    texto_observador      text,
    -- Cadena biocultural (4 niveles obligatorios, FK compuestas restrictivas)
    id_grupo              uuid NOT NULL REFERENCES sinb.grupo(id) ON DELETE RESTRICT,
    id_indicador_natural  uuid NOT NULL REFERENCES sinb.indicador_natural(id) ON DELETE RESTRICT,
    id_caracteristica     uuid NOT NULL REFERENCES sinb.caracteristica(id) ON DELETE RESTRICT,
    id_comportamiento     uuid NOT NULL REFERENCES sinb.comportamiento(id) ON DELETE RESTRICT,
    -- Contexto de la observación
    latitud               numeric,
    longitud              numeric,
    altitud               numeric,
    notas                 text,
    -- Offline / ingesta
    id_pe_off             varchar(36),
    es_ingesta            boolean NOT NULL DEFAULT false,
    creado_en             timestamptz NOT NULL DEFAULT now(),
    actualizado_en        timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT chk_periodo_largo CHECK (periodo_fin >= periodo_inicio),
    CONSTRAINT fk_largo_cadena_indicador FOREIGN KEY (id_indicador_natural, id_grupo)
        REFERENCES sinb.indicador_natural(id, id_grupo) ON DELETE RESTRICT,
    CONSTRAINT fk_largo_cadena_caracteristica FOREIGN KEY (id_caracteristica, id_indicador_natural)
        REFERENCES sinb.caracteristica(id, id_indicador_natural) ON DELETE RESTRICT,
    CONSTRAINT fk_largo_cadena_comportamiento FOREIGN KEY (id_comportamiento, id_caracteristica)
        REFERENCES sinb.comportamiento(id, id_caracteristica) ON DELETE RESTRICT,
    CONSTRAINT chk_latitud  CHECK (latitud  IS NULL OR (latitud  >= -90  AND latitud  <= 90)),
    CONSTRAINT chk_longitud CHECK (longitud IS NULL OR (longitud >= -180 AND longitud <= 180))
);

CREATE INDEX idx_pronostico_largo_municipio ON sinb.pronostico_largo (id_municipio);
CREATE INDEX idx_pronostico_largo_usuario   ON sinb.pronostico_largo (id_usuario_subio);
CREATE INDEX idx_pronostico_largo_periodo   ON sinb.pronostico_largo (periodo_fin);
CREATE INDEX idx_pronostico_largo_pe_off    ON sinb.pronostico_largo (id_pe_off)
    WHERE id_pe_off IS NOT NULL;

-- ----------------------------------------------------------------------------
-- 5. ÍTEMS DE PRONÓSTICO (uno por campo/categoría, con su validación)
-- ----------------------------------------------------------------------------
CREATE TABLE sinb.pronostico_largo_item (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    id_pronostico_largo uuid NOT NULL REFERENCES sinb.pronostico_largo(id) ON DELETE CASCADE,
    id_categoria        uuid NOT NULL REFERENCES sinb.categoria_pronostico(id) ON DELETE RESTRICT,
    metodo_validacion   varchar(50),
    id_regla_pronostica integer,
    confianza           numeric(5,4) CHECK (confianza IS NULL OR (confianza >= 0 AND confianza <= 1)),
    ejecutar_en         timestamptz,
    fuente              varchar(200),
    orden               integer NOT NULL DEFAULT 0,
    creado_en           timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_item_pronostico_categoria UNIQUE (id_pronostico_largo, id_categoria)
);

CREATE INDEX idx_item_pronostico ON sinb.pronostico_largo_item (id_pronostico_largo);

-- ----------------------------------------------------------------------------
-- 6. ESCENARIOS POR ÍTEM (probabilidad opcional 0-100)
-- ----------------------------------------------------------------------------
CREATE TABLE sinb.escenario_estacional (
    id_pronostico_largo_item uuid NOT NULL
        REFERENCES sinb.pronostico_largo_item(id) ON DELETE CASCADE,
    id_escenario             uuid NOT NULL REFERENCES sinb.escenario(id) ON DELETE RESTRICT,
    probabilidad             numeric(5,2)
        CHECK (probabilidad IS NULL OR (probabilidad >= 0 AND probabilidad <= 100)),
    PRIMARY KEY (id_pronostico_largo_item, id_escenario)
);

-- ----------------------------------------------------------------------------
-- 7. RECOMENDACIONES DEL PRONÓSTICO + COMPORTAMIENTOS DE SIEMBRA
-- ----------------------------------------------------------------------------
CREATE TABLE sinb.pronostico_largo_recomendacion (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    id_pronostico_largo uuid NOT NULL REFERENCES sinb.pronostico_largo(id) ON DELETE CASCADE,
    id_recomendacion    uuid NOT NULL REFERENCES sinb.recomendacion(id) ON DELETE RESTRICT,
    creado_en           timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_pronostico_recomendacion UNIQUE (id_pronostico_largo, id_recomendacion)
);

CREATE TABLE sinb.pronostico_largo_recomendacion_comportamiento (
    id_pronostico_largo_recomendacion uuid NOT NULL
        REFERENCES sinb.pronostico_largo_recomendacion(id) ON DELETE CASCADE,
    id_comportamiento uuid NOT NULL
        REFERENCES sinb.comportamiento_recomendacion(id) ON DELETE RESTRICT,
    PRIMARY KEY (id_pronostico_largo_recomendacion, id_comportamiento)
);

-- ----------------------------------------------------------------------------
-- 8. OBSERVADORES DEL PRONÓSTICO (misma estructura que antes)
-- ----------------------------------------------------------------------------
CREATE TABLE sinb.pronostico_largo_observador (
    id_pronostico_largo uuid NOT NULL
        REFERENCES sinb.pronostico_largo(id) ON DELETE CASCADE,
    id_usuario          integer NOT NULL REFERENCES usuarios.usuario(id_usuario) ON DELETE CASCADE,
    confianza           sinb.confianza_nivel,
    fecha_asignacion    timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (id_pronostico_largo, id_usuario)
);

-- ----------------------------------------------------------------------------
-- 9. VERIFICACIÓN: re-apuntar FK a la nueva cabecera
-- ----------------------------------------------------------------------------
ALTER TABLE sinb.verificacion_pronostico
    ADD CONSTRAINT verificacion_pronostico_id_pronostico_largo_fkey
    FOREIGN KEY (id_pronostico_largo) REFERENCES sinb.pronostico_largo(id)
    ON DELETE CASCADE;

-- ----------------------------------------------------------------------------
-- 10. VISTA DE VERIFICACIONES PENDIENTES (idéntica a la anterior)
-- ----------------------------------------------------------------------------
CREATE VIEW sinb.v_verificaciones_pendientes AS
SELECT v.id,
    COALESCE(pl.codigo, pc.codigo) AS pronostico_codigo,
    COALESCE(pl.periodo_fin, pc.fecha_fin) AS fecha_fin,
    v.estado,
    v.creado_en
FROM sinb.verificacion_pronostico v
LEFT JOIN sinb.pronostico_largo pl ON pl.id = v.id_pronostico_largo
LEFT JOIN sinb.pronostico_corto pc ON pc.id = v.id_pronostico_corto
WHERE v.estado = 'NO_VERIFICABLE'
  AND COALESCE(pl.periodo_fin, pc.fecha_fin) < CURRENT_DATE
ORDER BY COALESCE(pl.periodo_fin, pc.fecha_fin) DESC;

COMMIT;
