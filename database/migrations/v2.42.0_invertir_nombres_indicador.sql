-- ============================================================================
-- v2.42.0 Indicador natural: invertir el contenido de nombre_cientifico y nombre_comun
-- ============================================================================
-- Hoy el nombre corriente (Zorro, Qariwa, "Escarcha (jump'ita)") está guardado en
-- `nombre_cientifico` y `nombre_comun` está vacío. Se invierten los contenidos de
-- ambas columnas tal cual están, sin transformar ni agregar ningún texto.
--
-- `nombre_cientifico` es NOT NULL, así que las 77 filas cuyo nombre_comun estaba
-- NULL reciben cadena vacía ('') en lugar de NULL: es el contenido que "venía del
-- otro lado" (no había nada) y es lo único que permite ejecutar la inversión.
--
-- Las 7 filas con ambas columnas llenas (catalogos de prueba, estado ELIMINADO)
-- también se invierten.
--
-- El WHERE hace la migración re-ejecutable: después de invertir, ninguna fila
-- vuelve a cumplir la condición (nombre_comun ya no es NULL y los científicos de
-- prueba ya no dicen "especie"/"Prueba sp"), así que un segundo RUN afecta 0 filas.
--
-- Respaldo previo: backups/pre_v2.42.0_inversion_nombres_*.sql
-- ============================================================================

BEGIN;

UPDATE sinb.indicador_natural
   SET nombre_cientifico = COALESCE(nombre_comun, ''),
       nombre_comun      = nombre_cientifico,
       actualizado_en    = now()
 WHERE nombre_comun IS NULL
    OR (nombre_comun IS NOT NULL AND (nombre_cientifico LIKE '%especie%'
                                      OR nombre_cientifico LIKE 'Prueba sp%'));

COMMIT;

-- Verificación
-- SELECT count(*) FROM sinb.indicador_natural WHERE coalesce(nombre_comun,'')<>'';  -- 84
-- SELECT count(*) FROM sinb.indicador_natural WHERE nombre_cientifico='';          -- 77
-- SELECT codigo, nombre_cientifico, nombre_comun FROM sinb.indicador_natural
--  WHERE codigo IN ('I-1','I-2','I-33') ORDER BY codigo;
--   I-1  | ''     | Zorro
--   I-2  | ''     | Liqi liqi /Tero tero /leuqi leuqi
--   I-33 | ''     | Escarcha (jump'ita)

-- Reversión (deja todo como estaba):
-- UPDATE sinb.indicador_natural i
--    SET nombre_cientifico = b.nombre_cientifico, nombre_comun = b.nombre_comun,
--        actualizado_en = now()
--   FROM (VALUES
--         -- reconstruir desde backups/pre_v2.42.0_inversion_nombres_*.sql
--        ) b WHERE b.id = i.id;
