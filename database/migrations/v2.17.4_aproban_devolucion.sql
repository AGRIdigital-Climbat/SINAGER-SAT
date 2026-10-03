-- ============================================================================
-- SINAGERSAT - Migración v2.17.4 (idempotente)
-- Aprobaciones EDAN: separar quién aprobó de quién devolvió, y renombrar las
-- columnas opacas 'por' / 'fecha'.
--
--   Problema: 'por' mezclaba dos cosas. Se escribía tanto al aprobar como al
--   devolver, así que en el GET el mismo número significaba dos cosas según el
--   estado: con estado 'observado' era el DGR que devolvió, con estado
--   'aprobado' era quien aprobó. Además, al devolver se sobrescribía y el
--   aprobador original quedaba perdido para siempre.
--
--   Que hace esta migracion:
--     1. Agrega 4 columnas: id_usuario_aprobacion, fecha_aprobacion,
--        id_usuario_devolucion, fecha_devolucion.
--     2. Backfill del aprobador desde 'por' para las filas ya aprobadas.
--     3. Renombra por -> id_usuario_ultima_accion y fecha ->
--        fecha_ultima_accion. Se conservan como registro de auditoría; la API
--        no las expone porque son derivables del estado y porque exponer un id
--        sin su usuario anidado romperia la convencion de la API.
--
--   'observacion' (motivo) NO cambia de columna, ni el estado 'observado', ni
--   los 4 estados de la maquina.
--
--   IDEMPOTENCIA: el backfill y los renombres van dentro de bloques DO que
--   primero preguntan a information_schema si la columna legacy todavia existe.
--   Sin esas guardas un segundo apply fallaria: despues del primer apply 'por'
--   ya no existe, y tanto el UPDATE del backfill como el RENAME darían error.
--
--   Limitacion honesta: una fila que ya estaba 'observada' cuando corrio esta
--   migracion tiene el 'por' de el que devolvio, no la del que aprobo antes, y
--   no hay forma de recuperarlo. Al momento de aplicarla no hay ninguna fila
--   en ese estado.
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. Columnas de aprobacion y devolucion (idempotente por construccion)
-- ----------------------------------------------------------------------------
ALTER TABLE edan.aprobaciones_edan
    ADD COLUMN IF NOT EXISTS id_usuario_aprobacion INTEGER REFERENCES usuarios.usuario (id_usuario),
    ADD COLUMN IF NOT EXISTS fecha_aprobacion      TIMESTAMP,
    ADD COLUMN IF NOT EXISTS id_usuario_devolucion INTEGER REFERENCES usuarios.usuario (id_usuario),
    ADD COLUMN IF NOT EXISTS fecha_devolucion      TIMESTAMP;

-- ----------------------------------------------------------------------------
-- 2. Backfill del aprobador, solo si la columna legacy 'por' sigue existiendo
-- ----------------------------------------------------------------------------
DO $mig$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'edan'
                  AND table_name   = 'aprobaciones_edan'
                  AND column_name  = 'por') THEN
        EXECUTE $q$
            UPDATE edan.aprobaciones_edan
               SET id_usuario_aprobacion = por,
                   fecha_aprobacion      = fecha
             WHERE estado = 'aprobado'
               AND por IS NOT NULL
               AND id_usuario_aprobacion IS NULL
        $q$;
    END IF;
END
$mig$;

-- ----------------------------------------------------------------------------
-- 3. Renombrar las columnas opacas (se conservan para auditoria)
-- ----------------------------------------------------------------------------
DO $mig$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'edan'
                  AND table_name   = 'aprobaciones_edan'
                  AND column_name  = 'por') THEN
        EXECUTE 'ALTER TABLE edan.aprobaciones_edan
                 RENAME COLUMN por TO id_usuario_ultima_accion';
    END IF;

    IF EXISTS (SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'edan'
                  AND table_name   = 'aprobaciones_edan'
                  AND column_name  = 'fecha') THEN
        EXECUTE 'ALTER TABLE edan.aprobaciones_edan
                 RENAME COLUMN fecha TO fecha_ultima_accion';
    END IF;
END
$mig$;

COMMENT ON COLUMN edan.aprobaciones_edan.id_usuario_aprobacion IS
    'Quien aprobo este nivel. Se conserva aunque el nivel luego sea devuelto, '
    'para no perder la identidad del aprobador.';
COMMENT ON COLUMN edan.aprobaciones_edan.id_usuario_devolucion IS
    'Quien devolvio este nivel. Se limpia al aprobar de nuevo o al resolverse el '
    'ciclo de correccion, de modo que el GET refleje el estado actual.';
COMMENT ON COLUMN edan.aprobaciones_edan.id_usuario_ultima_accion IS
    'Ultimo usuario que actuo en este nivel (aprobo o devolvio). Auditoria; la '
    'API no lo expone. Es derivable del estado y de las columnas de '
    'aprobacion/devolucion.';
COMMENT ON COLUMN edan.aprobaciones_edan.fecha_ultima_accion IS
    'Fecha de la ultima accion sobre este nivel. Auditoria; la API no lo '
    'expone (usar fecha_aprobacion / fecha_devolucion).';

COMMIT;

SELECT 'IDEMPOTENT OK v2.17.4 aprobacion/devolucion aprobaciones_edan' AS resultado;
