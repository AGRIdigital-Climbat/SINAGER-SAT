-- ============================================================================
-- SINAGERSAT - Migración v2.17.5 (idempotente)
-- El motor de aprobaciones pasa a ser dueño de edan.edan.id_estado, y para
-- poder representar un EDAN devuelto se agrega el estado "Observado".
--
--   Problema: la maquina de aprobaciones maneja 3 estados por nivel
--   ('pendiente', 'aprobado', 'observado'), pero edan.estado_edan solo tenia
--   3 estados: 1 Pendiente aprobaciones, 2 Rechazado, 3 Aprobado. Faltaba el
--   equivalente de 'observado', asi que un EDAN devuelto por el DGR no tenia
--   donde verse: solo podia quedar en "Pendiente", igual que uno que nadie
--   reviso nunca. Y al reves, "Rechazado" (2) es inalcanzable desde el motor:
--   devolver exige un nivel ANTERIOR aprobado, y el primero de la cadena es
--   'ugr', que no tiene anterior. Nadie escribe el 2.
--
--   Que hace esta migracion:
--     1. Inserta el estado 4 = "Observado" en edan.estado_edan.
--     2. Backfillea edan.edan.id_estado SOLO para los EDANs que no cuadran con
--        su cadena de aprobaciones. No toca los que ya estan bien.
--
--   La sincronizacion en vivo la hace la API (_sincronizar_estado_edan) en la
--   misma transaccion que aprobar/devolver. Esto solo alinea el historico.
--
--   REGLA DE MAPEO (la misma en la migracion y en la API):
--     alguna fila 'observado'            -> 4 Observado
--     las 4 filas 'aprobado'             -> 3 Aprobado
--     cualquier otro caso (pendiente /
--     espera_correccion)                -> 1 Pendiente aprobaciones
--     2 Rechazado                        -> NADIE lo escribe
--
--   IDEMPOTENCIA:
--     - El INSERT del estado 4 usa ON CONFLICT (id_estado) DO UPDATE, asi que
--       un segundo apply actualiza nombre/descripcion/orden y no duplica.
--     - La secuencia va por detras (last_value = 12) porque se han borrado
--       filas 4..12; aun asi se deja un setval por si se aplica sobre una base
--       donde el 4 todavia no existio.
--     - El backfill se limita a filas que NO cuadran (IS DISTINCT FROM), asi
--       que aplicarlo dos veces no produce diferencias.
--
--   Nota: no se tocan las 4 filas de edan.aprobaciones_edan. Esta migracion
--   solo traduce su resultado a la cabecera.
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. Estado 4 = Observado (idempotente)
-- ----------------------------------------------------------------------------
INSERT INTO edan.estado_edan (id_estado, nombre, descripcion, orden)
VALUES (4, 'Observado', 'Formulario devuelto para correccion', 4)
ON CONFLICT (id_estado) DO UPDATE
    SET nombre      = EXCLUDED.nombre,
        descripcion = EXCLUDED.descripcion,
        orden       = EXCLUDED.orden;

-- La secuencia quedo atrasada (last_value = 12) por filas borradas. Se asegura
-- que el proximo INSERT del CRUD de catalogos no choque con un id usado.
SELECT setval(
    pg_get_serial_sequence('edan.estado_edan', 'id_estado'),
    GREATEST(
        (SELECT COALESCE(MAX(id_estado), 0) FROM edan.estado_edan),
        (SELECT COALESCE(last_value, 0) FROM edan.estado_edan_id_estado_seq)
    ),
    true
);

COMMENT ON TABLE edan.estado_edan IS
    'Estados del EDAN. Los escribe el motor de aprobaciones (api/edan/service.py::_sincronizar_estado_edan) al aprobar o devolver; la API no permite fijarlos a mano. El 2 Rechazado queda reservado: el motor no puede producirlo porque el primer nivel (ugr) no tiene nivel anterior que devolver.';

-- ----------------------------------------------------------------------------
-- 2. Backfill: alinear SOLO los EDANs que no cuadran (idempotente)
-- ----------------------------------------------------------------------------
WITH derivado AS (
    SELECT e.id_edan,
           CASE
               WHEN COUNT(*) FILTER (WHERE a.estado = 'observado') > 0 THEN 4
               WHEN COUNT(*) FILTER (WHERE a.estado = 'aprobado') = 4  THEN 3
               ELSE 1
           END AS id_estado_calc
    FROM edan.edan e
    JOIN edan.aprobaciones_edan a ON a.id_edan = e.id_edan
    GROUP BY e.id_edan
)
UPDATE edan.edan e
SET id_estado = d.id_estado_calc
FROM derivado d
WHERE d.id_edan = e.id_edan
  AND e.id_estado IS DISTINCT FROM d.id_estado_calc;

COMMIT;
