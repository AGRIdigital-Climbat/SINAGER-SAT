-- ============================================================================
-- SINAGERSAT - Migración v2.36.0 (idempotente)
-- RIDA: máquina de aprobaciones de solicitudes (tablas + backfill)
--
-- Sustituye los 15 booleanos de rida.solicitud (aprob_<nivel>, _fecha, _por)
-- por una fila por nivel en rida.aprobaciones_solicitud, igual que se hizo en
-- EDAN (v2.17.1). Las dos diferencias deliberadas con EDAN:
--
--   1) Se agrega rida.aprobacion_cadena: define QUE niveles participan y en que
--      orden, por modalidad. Es lo que hace dinamico el motor (el cliente pidio
--      que algunos sectores/departamentos usen solo 3 niveles). El EDAN tiene la
--      cadena fija en codigo; RIDA la resuelve desde la tabla.
--
--   2) Los 15 booleanos NO se eliminan aqui. RIDA los lee hoy en el detalle y en
--      la bandeja (GET /rida/solicitudes). Hasta que el frontend consuma
--      GET /rida/solicitudes/{id}/aprobacion siguen siendo la fuente que usa el
--      cliente, pero pasan a ser DERIVADOS de solo lectura: los recalcula el
--      servidor en cada PUT de la maquina y ya no se aceptan en PUT /{id}.
--      El borrado queda para la migracion de la fase 2.
--
-- El orden de la cadena lo define resolver_cadena() en
-- api/rida/solicitudes/service.py, no la BD: no hay columna 'ordinal' (el EDAN
-- la tuvo y se elimino en v2.17.2).
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. Cadena configurable: que niveles participan y en que orden
-- ----------------------------------------------------------------------------
-- id_modalidad NULL = cadena por defecto, la que se usa cuando la modalidad no
-- tiene filas propias. Nunca son 0 filas: si no, resolver_cadena() falla.
CREATE TABLE IF NOT EXISTS rida.aprobacion_cadena (
    id_cadena    BIGSERIAL   PRIMARY KEY,
    id_modalidad INTEGER    NULL REFERENCES rida.cat_modalidad (id_modalidad) ON DELETE CASCADE,
    nivel        VARCHAR(20) NOT NULL CHECK (nivel IN ('ugr', 'alcalde', 'dgr', 'videcid', 'direccion')),
    orden        SMALLINT   NOT NULL CHECK (orden BETWEEN 1 AND 5),
    activo       BOOLEAN    NOT NULL DEFAULT TRUE,
    UNIQUE (id_modalidad, nivel)
);

COMMENT ON TABLE rida.aprobacion_cadena IS
    'Niveles de la cadena de aprobacion por modalidad de ayuda. '
    'id_modalidad NULL = cadena por defecto (los 5 niveles).';
COMMENT ON COLUMN rida.aprobacion_cadena.id_modalidad IS
    'Modalidad a la que aplica la cadena. NULL = cadena por defecto.';
COMMENT ON COLUMN rida.aprobacion_cadena.orden IS
    'Posicion dentro de la cadena (1 = primer nivel). Debe respetar el orden '
    'semantico ugr < alcalde < dgr < videcid < direccion.';
COMMENT ON COLUMN rida.aprobacion_cadena.activo IS
    'Permite desactivar un nivel sin borrarlo. Las filas inactivas se ignoran al resolver la cadena.';

-- UNIQUE (id_modalidad, nivel) NO protege la fila por defecto: en Postgres los
-- NULL no colisionan entre si, asi que se podrian insertar 5 filas
-- id_modalidad IS NULL duplicadas y resolver_cadena() leeria un default
-- ambiguo. Este indice unico parcial si lo cierra.
CREATE UNIQUE INDEX IF NOT EXISTS idx_aprobacion_cadena_default
    ON rida.aprobacion_cadena (nivel) WHERE id_modalidad IS NULL;

CREATE INDEX IF NOT EXISTS idx_aprobacion_cadena_modalidad
    ON rida.aprobacion_cadena (id_modalidad);

-- ----------------------------------------------------------------------------
-- 2. Semilla: los 5 niveles como cadena por defecto
-- ----------------------------------------------------------------------------
-- Siembra UNA sola vez (la guarda del indice parcial la hace idempotente).
-- Si despues hay que corregir la cadena, se corrige con UPDATE, no re-sembrando:
-- re-sembrar solo atraparia (NULL, nivel), que es justo lo que ya cubre el
-- indice parcial, y una fila desincronizada pasaria inadvertida.
INSERT INTO rida.aprobacion_cadena (id_modalidad, nivel, orden, activo)
SELECT NULL, v.nivel, v.orden, TRUE
FROM (VALUES ('ugr', 1), ('alcalde', 2), ('dgr', 3), ('videcid', 4), ('direccion', 5))
     AS v(nivel, orden)
WHERE NOT EXISTS (SELECT 1 FROM rida.aprobacion_cadena WHERE id_modalidad IS NULL);

-- ----------------------------------------------------------------------------
-- 3. Aprobaciones: una fila por nivel de la cadena activa
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rida.aprobaciones_solicitud (
    id_aprobacion BIGSERIAL   PRIMARY KEY,
    id_solicitud  BIGINT      NOT NULL REFERENCES rida.solicitud (id_solicitud) ON DELETE CASCADE,
    nivel         VARCHAR(20) NOT NULL CHECK (nivel IN ('ugr', 'alcalde', 'dgr', 'videcid', 'direccion')),
    estado        VARCHAR(20) NOT NULL DEFAULT 'pendiente'
                  CHECK (estado IN ('pendiente', 'aprobado', 'observado', 'espera_correccion')),
    observacion   TEXT,
    por           INTEGER     REFERENCES usuarios.usuario (id_usuario),
    fecha         TIMESTAMP,
    UNIQUE (id_solicitud, nivel)
);

COMMENT ON TABLE rida.aprobaciones_solicitud IS
    'Maquina de aprobaciones del RIDA: una fila por nivel de la cadena activa de '
    'la modalidad. Solo tiene sentido mientras la solicitud esta en EN_APROBACION. '
    'observacion = motivo de devolucion, vive solo en la fila del nivel observado. '
    'estado_global NO se almacena: se deriva en cada lectura (estado + sufijo de nivel).';
COMMENT ON COLUMN rida.aprobaciones_solicitud.observacion IS
    'Motivo de la devolucion. Solo en la fila del nivel DEVUELTO (estado observado); '
    'se limpia cuando ese nivel vuelve a aprobar.';
COMMENT ON COLUMN rida.aprobaciones_solicitud.por IS
    'Usuario que hizo la ultima accion (aprobar o devolver) en este nivel. Viene del token JWT, nunca del cuerpo.';
COMMENT ON COLUMN rida.aprobaciones_solicitud.fecha IS
    'Fecha de la ultima accion en este nivel. SIN DEFAULT a proposito: con '
    'DEFAULT CURRENT_TIMESTAMP una fila recien creada en pendiente naceria con '
    'fecha y el frontend la leeria como si el nivel ya hubiera decidido.';

CREATE INDEX IF NOT EXISTS idx_aprobaciones_solicitud_solicitud
    ON rida.aprobaciones_solicitud (id_solicitud);

-- ----------------------------------------------------------------------------
-- 4. Backfill: una fila por nivel de la cadena, desde los 15 booleanos
-- ----------------------------------------------------------------------------
-- Cubre las solicitudes que pasaron por la maquina, ESTEN donde esten ahora: la
-- cadena tiene valor historico para toda solicitud que la cruzo, no solo para
-- las que siguen abiertas.
--
--   - EN_APROBACION: cadena en curso.
--   - APROBADA y las 6 etapas posteriores (AUTORIZADA ... CERRADA): completaron.
--   - RECHAZADA: solo si tiene AL MENOS un flag en TRUE. Un rechazo puede venir
--     de VALIDADA (nunca entro a la cadena, 0 flags) o de EN_APROBACION (tenia
--     aprobaciones parciales); el flag lo desambigua. Sin el, se crearian filas
--     'pendiente' para solicitudes que nunca se visaron.
--
-- Las etapas previas (BORRADOR, ENVIADA, EN_REVISION, OBSERVADA, VALIDADA) no
-- se tocan: alli la maquina todavia no existe y sus filas las crea
-- asegurar_aprobaciones() al entrar en EN_APROBACION.
--
-- La precedencia de cadena_replicada replica exactamente resolver_cadena():
--   (a) si la modalidad tiene filas activas, la cadena son esas filas;
--   (b) si no tiene ninguna, la cadena es la de id_modalidad IS NULL.
-- El default NO se mezcla nivel a nivel con la modalidad: si la modalidad
-- tiene 3 niveles, no puede heredar videcid/direccion del default, porque la
-- regla es "cadena propia o default", no "nivel propio o default".
WITH recap_solicitud AS (
    SELECT s.id_solicitud, s.id_modalidad
    FROM rida.solicitud s
    WHERE s.etapa IN ('EN_APROBACION', 'APROBADA', 'AUTORIZADA', 'EN_SUMINISTROS',
                      'DESPACHO_AUTORIZADO', 'DESPACHADA', 'EN_TRANSPORTE', 'RECIBIDA',
                      'EN_DISTRIBUCION', 'ENTREGADA', 'CERRADA')
       OR (s.etapa = 'RECHAZADA'
           AND COALESCE(s.aprob_ugr, FALSE) OR s.aprob_alcalde OR s.aprob_dgr
               OR s.aprob_videcid OR s.aprob_direccion)
),
cadena AS (
    SELECT r.id_solicitud, c.nivel, c.orden
    FROM recap_solicitud r
    JOIN rida.aprobacion_cadena c
      ON c.activo
     AND (c.id_modalidad = r.id_modalidad
          OR (c.id_modalidad IS NULL
              AND NOT EXISTS (SELECT 1 FROM rida.aprobacion_cadena c2
                               WHERE c2.activo AND c2.id_modalidad = r.id_modalidad)))
)
INSERT INTO rida.aprobaciones_solicitud (id_solicitud, nivel, estado, por, fecha)
SELECT c.id_solicitud,
       c.nivel,
       CASE WHEN COALESCE((to_jsonb(s) ->> ('aprob_' || c.nivel))::boolean, FALSE)
            THEN 'aprobado' ELSE 'pendiente' END,
       (to_jsonb(s) ->> ('aprob_' || c.nivel || '_por'))::integer,
       (to_jsonb(s) ->> ('aprob_' || c.nivel || '_fecha'))::timestamp
FROM cadena c
JOIN rida.solicitud s ON s.id_solicitud = c.id_solicitud
ON CONFLICT (id_solicitud, nivel) DO NOTHING;

-- Nota de por que NO hay trigger como en v2.17.3 (trg_edan_crear_aprobaciones):
-- a diferencia del EDAN, aqui las filas solo tienen sentido en EN_APROBACION y la
-- cadena que corresponde se resuelve por id_modalidad. Crearlas al INSERT de
-- rida.solicitud congelaria la cadena de una solicitud que todavia no ha pasado
-- por validacion. La red de seguridad es asegurar_aprobaciones() en Python, que
-- se llama al entrar en EN_APROBACION y en cada GET/PUT de la maquina.

COMMIT;

SELECT 'IDEMPOTENT OK v2.36.0 aprobaciones rida' AS resultado;