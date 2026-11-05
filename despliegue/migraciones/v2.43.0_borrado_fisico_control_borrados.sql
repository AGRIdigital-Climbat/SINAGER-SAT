-- ============================================================================
-- v2.43.0 Borrado físico + control de borrados (tombstones) + limpieza de pruebas
-- ============================================================================
-- Contexto: el DELETE de los catálogos SINB hacía `SET estado = 'ELIMINADO'`.
-- Ese estado no lo lee nadie (los 28 filtros de service.py piden 'ACTIVO'), no
-- existe papelera ni ruta de recuperación, y los UPDATE de grupo e indicador
-- filtran `estado = 'ACTIVO'`, así que la fila quedaba INTOCABLE por API. Peor
-- aún: los UNIQUE (grupo_codigo_key, indicador_natural_codigo_key,
-- zona_geografica_codigo_key, categoria_pronostico_temporal_nombre_key) no
-- excluyen borrados lógicos, de modo que reutilizar el código de una fila
-- "eliminada" choca contra la restricción y la API responde 500.
--
-- Esta migración deja la base lista para el borrado físico:
--   1. sinb.registro_borrado: cada DELETE físico deja rastro (tabla, id,
--      codigo, id_off, borrado_en, id_usuario) para que la app offline sepa qué
--      retirar de su caché. UNIQUE (tabla, id_registro).
--   2. Las FK de indicador_foto y observador_indice hacia indicador_natural
--      pasan de CASCADE a RESTRICT: una foto subida en campo o un índice de
--      aciertos NUNCA puede desaparecer por arrastre al borrar su indicador.
--      (Hoy: 20 fotos y 0 índices, ninguno colgado de una fila de prueba.)
--   3. Limpieza de datos de prueba con estado ELIMINADO que la API ya no puede
--      gestionar: 7 grupo + 7 indicador + 7 caracteristica + 7 comportamiento +
--      6 significado + 6 zona_geografica + 10 categoria_pronostico + 7 escenario
--      + 5 avisos = 62 filas, más los 7 pronósticos cortos de prueba PT-* (y sus
--      7 observadores asignados, hijos suyos). Cada fila borrada deja su
--      tombstone.
--
-- Ninguna fila ACTIVA referencia a las que se van (verificado antes de escribir
-- esta migración). Ninguna columna, ruta o shape de respuesta cambia.
--
-- Respaldo previo: backups/pre_v2.43.0_borrado_fisico_*.sql (13 tablas)
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. Control de borrados
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sinb.registro_borrado (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tabla         text    NOT NULL,
    id_registro   uuid    NOT NULL,
    codigo        text,
    id_off        text,
    borrado_en    timestamptz NOT NULL DEFAULT now(),
    id_usuario    integer REFERENCES usuarios.usuario(id_usuario) ON DELETE SET NULL,
    CONSTRAINT uk_registro_borrado UNIQUE (tabla, id_registro),
    CONSTRAINT ck_registro_borrado_tabla CHECK (tabla IN (
        'grupo', 'indicador_natural', 'caracteristica', 'comportamiento',
        'significado', 'zona_geografica', 'categoria_pronostico', 'escenario',
        'avisos', 'indicador_foto', 'observador_indice',
        'pronostico_largo', 'pronostico_corto'
    ))
);

COMMENT ON TABLE sinb.registro_borrado
    IS 'Rastro de cada borrado físico de SINB, para que la app offline retire de su caché lo que ya no existe';

CREATE INDEX IF NOT EXISTS idx_registro_borrado_desde
    ON sinb.registro_borrado (borrado_en DESC);
CREATE INDEX IF NOT EXISTS idx_registro_borrado_tabla_desde
    ON sinb.registro_borrado (tabla, borrado_en DESC);

-- ----------------------------------------------------------------------------
-- 2. Fotos e índices no pueden borrarse en cascada con su indicador
-- ----------------------------------------------------------------------------
ALTER TABLE sinb.indicador_foto
    DROP CONSTRAINT indicador_foto_id_indicador_natural_fkey;
ALTER TABLE sinb.indicador_foto
    ADD CONSTRAINT indicador_foto_id_indicador_natural_fkey
    FOREIGN KEY (id_indicador_natural) REFERENCES sinb.indicador_natural(id)
    ON DELETE RESTRICT;

ALTER TABLE sinb.observador_indice
    DROP CONSTRAINT observador_indice_id_indicador_natural_fkey;
ALTER TABLE sinb.observador_indice
    ADD CONSTRAINT observador_indice_id_indicador_natural_fkey
    FOREIGN KEY (id_indicador_natural) REFERENCES sinb.indicador_natural(id)
    ON DELETE RESTRICT;

-- ----------------------------------------------------------------------------
-- 3. Tombstones de lo que se va a limpiar (ids originales de las filas)
-- ----------------------------------------------------------------------------
INSERT INTO sinb.registro_borrado (tabla, id_registro, codigo)
SELECT 'significado', id, LEFT(significado, 80) FROM sinb.significado WHERE estado = 'ELIMINADO'
ON CONFLICT (tabla, id_registro) DO NOTHING;

INSERT INTO sinb.registro_borrado (tabla, id_registro, codigo)
SELECT 'comportamiento', id, LEFT(comportamiento, 80) FROM sinb.comportamiento WHERE estado = 'ELIMINADO'
ON CONFLICT (tabla, id_registro) DO NOTHING;

INSERT INTO sinb.registro_borrado (tabla, id_registro, codigo)
SELECT 'caracteristica', id, LEFT(caracteristica, 80) FROM sinb.caracteristica WHERE estado = 'ELIMINADO'
ON CONFLICT (tabla, id_registro) DO NOTHING;

INSERT INTO sinb.registro_borrado (tabla, id_registro, codigo)
SELECT 'indicador_natural', id, codigo FROM sinb.indicador_natural WHERE estado = 'ELIMINADO'
ON CONFLICT (tabla, id_registro) DO NOTHING;

INSERT INTO sinb.registro_borrado (tabla, id_registro, codigo)
SELECT 'escenario', id, nombre FROM sinb.escenario WHERE estado = 'ELIMINADO'
ON CONFLICT (tabla, id_registro) DO NOTHING;

INSERT INTO sinb.registro_borrado (tabla, id_registro, codigo)
SELECT 'categoria_pronostico', id, nombre FROM sinb.categoria_pronostico WHERE estado = 'ELIMINADO'
ON CONFLICT (tabla, id_registro) DO NOTHING;

INSERT INTO sinb.registro_borrado (tabla, id_registro, codigo)
SELECT 'zona_geografica', id, codigo FROM sinb.zona_geografica WHERE estado = 'ELIMINADO'
ON CONFLICT (tabla, id_registro) DO NOTHING;

INSERT INTO sinb.registro_borrado (tabla, id_registro, codigo, id_off)
SELECT 'avisos', id, codigo, id_aviso_off FROM sinb.avisos WHERE estado = 'ELIMINADO'
ON CONFLICT (tabla, id_registro) DO NOTHING;

INSERT INTO sinb.registro_borrado (tabla, id_registro, codigo)
SELECT 'grupo', id, codigo FROM sinb.grupo WHERE estado = 'ELIMINADO'
ON CONFLICT (tabla, id_registro) DO NOTHING;

INSERT INTO sinb.registro_borrado (tabla, id_registro, codigo, id_off)
SELECT 'pronostico_corto', id, codigo, id_pt_off FROM sinb.pronostico_corto WHERE codigo LIKE 'PT-%'
ON CONFLICT (tabla, id_registro) DO NOTHING;

-- ----------------------------------------------------------------------------
-- 4. Borrado, en orden de FK (hijos antes que padres: todo es RESTRICT)
-- ----------------------------------------------------------------------------
DELETE FROM sinb.significado           WHERE estado = 'ELIMINADO';
DELETE FROM sinb.comportamiento        WHERE estado = 'ELIMINADO';
DELETE FROM sinb.caracteristica        WHERE estado = 'ELIMINADO';
DELETE FROM sinb.indicador_natural     WHERE estado = 'ELIMINADO';
DELETE FROM sinb.escenario             WHERE estado = 'ELIMINADO';
DELETE FROM sinb.categoria_pronostico  WHERE estado = 'ELIMINADO';
DELETE FROM sinb.zona_geografica       WHERE estado = 'ELIMINADO';
DELETE FROM sinb.avisos                WHERE estado = 'ELIMINADO';
DELETE FROM sinb.grupo                 WHERE estado = 'ELIMINADO';
-- pronostico_corto_observador cae por CASCADE propio del pronóstico (hijo suyo)
DELETE FROM sinb.pronostico_corto      WHERE codigo LIKE 'PT-%';

COMMIT;

-- ============================================================================
-- Verificación
-- ============================================================================
-- SELECT count(*) FROM sinb.registro_borrado;                     -- 69
-- SELECT tabla, count(*) FROM sinb.registro_borrado GROUP BY 1;
-- SELECT count(*) FROM sinb.grupo                 WHERE estado <> 'ACTIVO';  -- 0
-- SELECT count(*) FROM sinb.indicador_natural     WHERE estado <> 'ACTIVO';  -- 0
-- SELECT count(*) FROM sinb.caracteristica        WHERE estado <> 'ACTIVO';  -- 0
-- SELECT count(*) FROM sinb.comportamiento        WHERE estado <> 'ACTIVO';  -- 0
-- SELECT count(*) FROM sinb.significado            WHERE estado <> 'ACTIVO';  -- 0
-- SELECT count(*) FROM sinb.zona_geografica        WHERE estado <> 'ACTIVO';  -- 0
-- SELECT count(*) FROM sinb.categoria_pronostico   WHERE estado <> 'ACTIVO';  -- 0
-- SELECT count(*) FROM sinb.escenario              WHERE estado <> 'ACTIVO';  -- 0
-- SELECT count(*) FROM sinb.avisos                 WHERE estado <> 'ACTIVO';  -- 0
-- SELECT count(*) FROM sinb.pronostico_corto;                              -- 0
-- SELECT count(*) FROM sinb.pronostico_corto_observador;                    -- 0
-- -- intacto:
-- SELECT count(*) FROM sinb.indicador_foto;                        -- 20
-- SELECT count(*) FROM sinb.pronostico_largo;                      -- 219
-- SELECT count(*) FROM sinb.indicador_natural WHERE estado='ACTIVO'; -- 77
-- SELECT conrelid::regclass, confdeltype FROM pg_constraint
--  WHERE conname IN ('indicador_foto_id_indicador_natural_fkey',
--                    'observador_indice_id_indicador_natural_fkey'); -- r, r
