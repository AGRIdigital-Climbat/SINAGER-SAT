-- ============================================================================
-- SINAGERSAT - Migración v2.17.3 (idempotente)
-- Aprobaciones EDAN: garantizar 4 filas por EDAN.
--
--   Problema: v2.17.1 creo la tabla y la lleno con un backfill de UNA SOLA VEZ
--   (bloque DO $$ que corre si la tabla estaba vacia). Ningun INSERT posterior
--   creo las 4 filas de aprobaciones, y no habia trigger sobre edan.edan. Por
--   eso todo EDAN creado despues de v2.17.1 (create_edan, consolidar,
--   importar_excel) se quedaba con 0 filas y:
--     - GET  /edan/{id}/aprobacion    -> 500 (KeyError al derivar estado_global)
--     - PUT  /edan/{id}/aprobacion/*   -> 500 (KeyError al leer el nivel)
--
--   Que hace esta migracion:
--     1. Trigger AFTER INSERT sobre edan.edan que crea las 4 filas 'pendiente'
--        al insertar un EDAN. AFTER (no BEFORE) porque aprobaciones_edan.id_edan
--        tiene FK a edan.edan(id_edan) y en BEFORE la fila padre aun no existe.
--        Cubre los 3 caminos de creacion y cualquier futuro.
--     2. Backfill de los EDANs ya existentes a los que les falte algun nivel
--        (ON CONFLICT DO NOTHING: no pisa estados ya decididos).
--
--   Idempotente: se puede correr N veces sin efectos colaterales.
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. Funcion + trigger de creacion automatica
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION edan.fn_crear_aprobaciones_edan() RETURNS trigger AS $$
BEGIN
    INSERT INTO edan.aprobaciones_edan (id_edan, nivel, estado)
    SELECT NEW.id_edan, v.nivel, 'pendiente'
    FROM (VALUES ('ugr'), ('alcalde'), ('dgr'), ('videcid')) AS v(nivel)
    ON CONFLICT (id_edan, nivel) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION edan.fn_crear_aprobaciones_edan() IS
    'Crea las 4 filas de edan.aprobaciones_edan (ugr/alcalde/dgr/videcid) en '
    'pendiente cada vez que se inserta un EDAN.';

DROP TRIGGER IF EXISTS trg_edan_crear_aprobaciones ON edan.edan;

CREATE TRIGGER trg_edan_crear_aprobaciones
    AFTER INSERT ON edan.edan
    FOR EACH ROW
    EXECUTE FUNCTION edan.fn_crear_aprobaciones_edan();

-- ----------------------------------------------------------------------------
-- 2. Backfill de EDANs existentes a los que les falte algun nivel
-- ----------------------------------------------------------------------------
INSERT INTO edan.aprobaciones_edan (id_edan, nivel, estado)
SELECT e.id_edan, v.nivel, 'pendiente'
FROM edan.edan e
CROSS JOIN (VALUES ('ugr'), ('alcalde'), ('dgr'), ('videcid')) AS v(nivel)
ON CONFLICT (id_edan, nivel) DO NOTHING;

COMMIT;

SELECT 'IDEMPOTENT OK v2.17.3 asegurar aprobaciones_edan' AS resultado;
