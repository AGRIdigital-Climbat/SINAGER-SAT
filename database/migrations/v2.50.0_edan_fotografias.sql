-- ============================================================================
-- SINAGERSAT - Migración v2.50.0 (idempotente)
-- EDAN: tabla de fotografías con identidad propia (Fase 1: solo BD)
--
--   Contexto: hoy las fotos se guardan como ruta (varchar 500) en la columna
--   `fotografia` de 9 tablas de sección (108 archivos en uploads/reports/...),
--   sin identidad, sin validación de pertenencia ni ciclo de vida. El flujo
--   correcto (Fase 2) es: la foto se sube y se vincula a una fila de sección
--   ya existente, con reintentos idempotentes y propagación de borrados.
--
--   Esta migración CREA `edan.fotografias`:
--     * id_fotografia   bigserial PK (interna del servidor)
--     * uuid_fotografia identidad permanente (DEFAULT gen_random_uuid(), única)
--     * id_edan_localidad FK -> edan.edan_localidades ON DELETE CASCADE
--     * tipo_entidad    nombre corto de la sección (CHECK, 14 valores:
--                       nombre de tabla menos el prefijo `edan_localidades_`)
--     * uuid_registro   identidad de la fila dueña (polimórfica: SIN FK; se
--                       valida pertenencia en la capa de servicio de la API)
--     * ruta_archivo    la ruta existente (columna `fotografia` se CONSERVA)
--     * sha256          NULL en el backfill (se calcula al primer acceso/re-subida)
--     * borrado_logico  borrado lógico propagable por pull
--
--   Backfill: INSERT con guarda `WHERE NOT EXISTS (misma localidad+tipo+ruta)`
--   para que sea idempotente y no duplique al re-ejecutar la migración.
--   El orden con v2.49.0 garantiza que `uuid_registro` ya esté NOT NULL.
--
--   IDEMPOTENCIA: CREATE TABLE IF NOT EXISTS + INSERT ... WHERE NOT EXISTS +
--   CREATE INDEX IF NOT EXISTS. Se puede aplicar N veces.
--
--   Respaldo previo: backups/pre_v2.49.0_edan_uuid_*.sql
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. Tabla de fotografías
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS edan.fotografias (
    id_fotografia      bigserial PRIMARY KEY,
    uuid_fotografia    uuid NOT NULL DEFAULT gen_random_uuid(),
    id_edan_localidad  bigint NOT NULL
                       REFERENCES edan.edan_localidades (id_edan_localidad)
                       ON DELETE CASCADE,
    tipo_entidad       varchar(50) NOT NULL CHECK (tipo_entidad IN (
                           'danos_agricultura',
                           'danos_infra_publica',
                           'danos_pecuario',
                           'danos_viales',
                           'danos_vivienda',
                           'impacto_poblacion',
                           'infra_productiva',
                           'necesidades_humanitarias',
                           'primera_respuesta',
                           'proteccion',
                           'salud_establecimientos',
                           'salud_necesidades',
                           'servicios_basicos',
                           'unidades_educativas'
                       )),
    uuid_registro      uuid NOT NULL,
    ruta_archivo       varchar(500) NOT NULL,
    sha256             varchar(64),
    mime_type          varchar(100),
    tamano_bytes       bigint,
    fecha_creacion     timestamptz NOT NULL DEFAULT now(),
    fecha_modificacion timestamptz NOT NULL DEFAULT now(),
    borrado_logico     boolean NOT NULL DEFAULT false,
    CONSTRAINT uq_fotografias_uuid UNIQUE (uuid_fotografia)
);

COMMENT ON TABLE edan.fotografias IS
    'Fotos del EDAN con identidad propia (uuid_fotografia) y ciclo de vida de subida; vinculadas a la fila de sección por (tipo_entidad, uuid_registro) — validación de pertenencia en la API, no en la BD (polimórfico).';
COMMENT ON COLUMN edan.fotografias.uuid_fotografia IS
    'Identidad permanente de la foto: se genera una sola vez (cliente o servidor) y no cambia entre reintentos/sincronizaciones.';
COMMENT ON COLUMN edan.fotografias.uuid_registro IS
    'Identidad de la fila de sección dueña (polimórfico: una de las 14 tablas según tipo_entidad). Sin FK por diseño; validar pertenencia en servicio.';
COMMENT ON COLUMN edan.fotografias.sha256 IS
    'Hash del archivo para detección de duplicados/idempotencia. NULL en las 108 fotos del backfill: se calcula al primer acceso o re-subida.';
COMMENT ON COLUMN edan.fotografias.borrado_logico IS
    'Borrado lógico: la API vieja/futura marca en vez de eliminar, para que el borrado se propague por pull a los demás dispositivos.';

-- ----------------------------------------------------------------------------
-- 2. Índices
-- ----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_fotografias_localidad
    ON edan.fotografias (id_edan_localidad);
CREATE INDEX IF NOT EXISTS idx_fotografias_registro
    ON edan.fotografias (tipo_entidad, uuid_registro);
CREATE INDEX IF NOT EXISTS idx_fotografias_sync_pull
    ON edan.fotografias (fecha_modificacion);

-- ----------------------------------------------------------------------------
-- 3. Backfill de las 108 fotos existentes (guarda idempotente)
--    tipo_entidad = nombre de tabla menos el prefijo `edan_localidades_`
-- ----------------------------------------------------------------------------
INSERT INTO edan.fotografias
    (id_edan_localidad, tipo_entidad, uuid_registro, ruta_archivo, mime_type,
     fecha_creacion, fecha_modificacion)
SELECT t.id_edan_localidad, 'danos_vivienda', t.uuid_registro, t.fotografia,
       CASE
           WHEN lower(t.fotografia) LIKE '%.png' THEN 'image/png'
           WHEN lower(t.fotografia) LIKE '%.jpg'
             OR lower(t.fotografia) LIKE '%.jpeg' THEN 'image/jpeg'
           ELSE NULL
       END,
       t.fecha_modificacion, t.fecha_modificacion
FROM edan.edan_localidades_danos_vivienda t
WHERE t.fotografia IS NOT NULL AND t.fotografia <> ''
  AND NOT EXISTS (
      SELECT 1 FROM edan.fotografias f
      WHERE f.id_edan_localidad = t.id_edan_localidad
        AND f.tipo_entidad = 'danos_vivienda'
        AND f.ruta_archivo = t.fotografia);

INSERT INTO edan.fotografias
    (id_edan_localidad, tipo_entidad, uuid_registro, ruta_archivo, mime_type,
     fecha_creacion, fecha_modificacion)
SELECT t.id_edan_localidad, 'danos_agricultura', t.uuid_registro, t.fotografia,
       CASE
           WHEN lower(t.fotografia) LIKE '%.png' THEN 'image/png'
           WHEN lower(t.fotografia) LIKE '%.jpg'
             OR lower(t.fotografia) LIKE '%.jpeg' THEN 'image/jpeg'
           ELSE NULL
       END,
       t.fecha_modificacion, t.fecha_modificacion
FROM edan.edan_localidades_danos_agricultura t
WHERE t.fotografia IS NOT NULL AND t.fotografia <> ''
  AND NOT EXISTS (
      SELECT 1 FROM edan.fotografias f
      WHERE f.id_edan_localidad = t.id_edan_localidad
        AND f.tipo_entidad = 'danos_agricultura'
        AND f.ruta_archivo = t.fotografia);

INSERT INTO edan.fotografias
    (id_edan_localidad, tipo_entidad, uuid_registro, ruta_archivo, mime_type,
     fecha_creacion, fecha_modificacion)
SELECT t.id_edan_localidad, 'danos_pecuario', t.uuid_registro, t.fotografia,
       CASE
           WHEN lower(t.fotografia) LIKE '%.png' THEN 'image/png'
           WHEN lower(t.fotografia) LIKE '%.jpg'
             OR lower(t.fotografia) LIKE '%.jpeg' THEN 'image/jpeg'
           ELSE NULL
       END,
       t.fecha_modificacion, t.fecha_modificacion
FROM edan.edan_localidades_danos_pecuario t
WHERE t.fotografia IS NOT NULL AND t.fotografia <> ''
  AND NOT EXISTS (
      SELECT 1 FROM edan.fotografias f
      WHERE f.id_edan_localidad = t.id_edan_localidad
        AND f.tipo_entidad = 'danos_pecuario'
        AND f.ruta_archivo = t.fotografia);

INSERT INTO edan.fotografias
    (id_edan_localidad, tipo_entidad, uuid_registro, ruta_archivo, mime_type,
     fecha_creacion, fecha_modificacion)
SELECT t.id_edan_localidad, 'danos_viales', t.uuid_registro, t.fotografia,
       CASE
           WHEN lower(t.fotografia) LIKE '%.png' THEN 'image/png'
           WHEN lower(t.fotografia) LIKE '%.jpg'
             OR lower(t.fotografia) LIKE '%.jpeg' THEN 'image/jpeg'
           ELSE NULL
       END,
       t.fecha_modificacion, t.fecha_modificacion
FROM edan.edan_localidades_danos_viales t
WHERE t.fotografia IS NOT NULL AND t.fotografia <> ''
  AND NOT EXISTS (
      SELECT 1 FROM edan.fotografias f
      WHERE f.id_edan_localidad = t.id_edan_localidad
        AND f.tipo_entidad = 'danos_viales'
        AND f.ruta_archivo = t.fotografia);

INSERT INTO edan.fotografias
    (id_edan_localidad, tipo_entidad, uuid_registro, ruta_archivo, mime_type,
     fecha_creacion, fecha_modificacion)
SELECT t.id_edan_localidad, 'danos_infra_publica', t.uuid_registro, t.fotografia,
       CASE
           WHEN lower(t.fotografia) LIKE '%.png' THEN 'image/png'
           WHEN lower(t.fotografia) LIKE '%.jpg'
             OR lower(t.fotografia) LIKE '%.jpeg' THEN 'image/jpeg'
           ELSE NULL
       END,
       t.fecha_modificacion, t.fecha_modificacion
FROM edan.edan_localidades_danos_infra_publica t
WHERE t.fotografia IS NOT NULL AND t.fotografia <> ''
  AND NOT EXISTS (
      SELECT 1 FROM edan.fotografias f
      WHERE f.id_edan_localidad = t.id_edan_localidad
        AND f.tipo_entidad = 'danos_infra_publica'
        AND f.ruta_archivo = t.fotografia);

INSERT INTO edan.fotografias
    (id_edan_localidad, tipo_entidad, uuid_registro, ruta_archivo, mime_type,
     fecha_creacion, fecha_modificacion)
SELECT t.id_edan_localidad, 'infra_productiva', t.uuid_registro, t.fotografia,
       CASE
           WHEN lower(t.fotografia) LIKE '%.png' THEN 'image/png'
           WHEN lower(t.fotografia) LIKE '%.jpg'
             OR lower(t.fotografia) LIKE '%.jpeg' THEN 'image/jpeg'
           ELSE NULL
       END,
       t.fecha_modificacion, t.fecha_modificacion
FROM edan.edan_localidades_infra_productiva t
WHERE t.fotografia IS NOT NULL AND t.fotografia <> ''
  AND NOT EXISTS (
      SELECT 1 FROM edan.fotografias f
      WHERE f.id_edan_localidad = t.id_edan_localidad
        AND f.tipo_entidad = 'infra_productiva'
        AND f.ruta_archivo = t.fotografia);

INSERT INTO edan.fotografias
    (id_edan_localidad, tipo_entidad, uuid_registro, ruta_archivo, mime_type,
     fecha_creacion, fecha_modificacion)
SELECT t.id_edan_localidad, 'salud_establecimientos', t.uuid_registro, t.fotografia,
       CASE
           WHEN lower(t.fotografia) LIKE '%.png' THEN 'image/png'
           WHEN lower(t.fotografia) LIKE '%.jpg'
             OR lower(t.fotografia) LIKE '%.jpeg' THEN 'image/jpeg'
           ELSE NULL
       END,
       t.fecha_modificacion, t.fecha_modificacion
FROM edan.edan_localidades_salud_establecimientos t
WHERE t.fotografia IS NOT NULL AND t.fotografia <> ''
  AND NOT EXISTS (
      SELECT 1 FROM edan.fotografias f
      WHERE f.id_edan_localidad = t.id_edan_localidad
        AND f.tipo_entidad = 'salud_establecimientos'
        AND f.ruta_archivo = t.fotografia);

INSERT INTO edan.fotografias
    (id_edan_localidad, tipo_entidad, uuid_registro, ruta_archivo, mime_type,
     fecha_creacion, fecha_modificacion)
SELECT t.id_edan_localidad, 'servicios_basicos', t.uuid_registro, t.fotografia,
       CASE
           WHEN lower(t.fotografia) LIKE '%.png' THEN 'image/png'
           WHEN lower(t.fotografia) LIKE '%.jpg'
             OR lower(t.fotografia) LIKE '%.jpeg' THEN 'image/jpeg'
           ELSE NULL
       END,
       t.fecha_modificacion, t.fecha_modificacion
FROM edan.edan_localidades_servicios_basicos t
WHERE t.fotografia IS NOT NULL AND t.fotografia <> ''
  AND NOT EXISTS (
      SELECT 1 FROM edan.fotografias f
      WHERE f.id_edan_localidad = t.id_edan_localidad
        AND f.tipo_entidad = 'servicios_basicos'
        AND f.ruta_archivo = t.fotografia);

INSERT INTO edan.fotografias
    (id_edan_localidad, tipo_entidad, uuid_registro, ruta_archivo, mime_type,
     fecha_creacion, fecha_modificacion)
SELECT t.id_edan_localidad, 'unidades_educativas', t.uuid_registro, t.fotografia,
       CASE
           WHEN lower(t.fotografia) LIKE '%.png' THEN 'image/png'
           WHEN lower(t.fotografia) LIKE '%.jpg'
             OR lower(t.fotografia) LIKE '%.jpeg' THEN 'image/jpeg'
           ELSE NULL
       END,
       t.fecha_modificacion, t.fecha_modificacion
FROM edan.edan_localidades_unidades_educativas t
WHERE t.fotografia IS NOT NULL AND t.fotografia <> ''
  AND NOT EXISTS (
      SELECT 1 FROM edan.fotografias f
      WHERE f.id_edan_localidad = t.id_edan_localidad
        AND f.tipo_entidad = 'unidades_educativas'
        AND f.ruta_archivo = t.fotografia);

COMMIT;
SELECT 'IDEMPOTENT OK v2.50.0 edan.fotografias';
