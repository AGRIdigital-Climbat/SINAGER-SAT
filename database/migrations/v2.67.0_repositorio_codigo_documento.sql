-- ============================================================================
-- SINAGERSAT - Migracion v2.67.0 (idempotente)
-- Repositorio de documentos: codigo_documento (clave de agrupacion /
-- rastreo para DOC_PRECEDENTE) + secuencia + indice + metrica publica
-- 'expedientes'.
--
--   Contexto:
--   - Los documentos EDAN se agrupan por id_edan; los RIDA por
--     id_evento_rida (y heredan id_edan). Los DOC_PRECEDENTE (3a subida
--     municipal, v2.65.0) solo tenian id_documento: no existia forma de
--     vincular varios PDFs del mismo expediente.
--   - Se agrega 'codigo_documento varchar(64)' NO unico: varios documentos
--     pueden compartir el mismo codigo (= un expediente). Lo escribe la 3a
--     API (autogenerado RES-{codigo_ine}-{YYYY}-{seq} si el cliente no lo
--     envia) y el PUT de edicion. EDAN/RIDA quedan NULL: sus endpoints y
--     contratos NO cambian.
--   - Secuencia dedicada para codigos autogenerados sin condiciones de
--     carrera entre workers.
--   - Metricas publicas: publico.v_repo_resumen (re-creada desde v2.66.0)
--     anade la dimension 'expedientes' = distinct de la clave de agrupacion
--     por origen (id_edan / id_evento_rida / codigo_documento). Solo
--     conteos; nunca se exponen los codigos.
--
--   IDEMPOTENCIA: ADD COLUMN IF NOT EXISTS, CREATE INDEX/SEQUENCE IF NOT
--   EXISTS, DROP VIEW IF EXISTS + CREATE VIEW. Reaplicable.
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. Columna de agrupacion/rastreo
-- ----------------------------------------------------------------------------
ALTER TABLE repositorio.documentos
    ADD COLUMN IF NOT EXISTS codigo_documento varchar(64);

CREATE INDEX IF NOT EXISTS idx_documentos_codigo_documento
    ON repositorio.documentos (codigo_documento);

-- Secuencia para codigos autogenerados (RES-{codigo_ine}-{anio}-{seq})
CREATE SEQUENCE IF NOT EXISTS repositorio.codigo_documento_seq;

COMMENT ON COLUMN repositorio.documentos.codigo_documento IS
    'Clave de agrupacion/rastreo de documentos DOC_PRECEDENTE (respaldo '
    'municipal). NO unica: varios documentos pueden compartir el mismo codigo '
    '(expediente). Autogenerada por la API como RES-{codigo_ine}-{YYYY}-{seq} '
    'si no se envia; normalizada a MAYUSCULAS. NULL en documentos EDAN/RIDA, '
    'que se agrupan por id_edan / id_evento_rida.';

COMMENT ON SEQUENCE repositorio.codigo_documento_seq IS
    'Numeracion de codigos_documento autogenerados (3a subida municipal).';

-- ----------------------------------------------------------------------------
-- 2. Metrica publica: v_repo_resumen con dimension 'expedientes'
--    (se omite si aun no existe el esquema publico de v2.66.0; el orden
--    ascendente de despliegue/scripts/actualizar.sh lo aplica primero)
-- ----------------------------------------------------------------------------
DO $mig$
BEGIN
    IF to_regclass('publico.v_repo_resumen') IS NOT NULL
       OR to_regnamespace('publico') IS NOT NULL THEN

        DROP VIEW IF EXISTS publico.v_repo_resumen;
        CREATE VIEW publico.v_repo_resumen AS
SELECT 'total'::text AS dimension, 'documentos_activos'::text AS llave,
       count(*)::bigint AS total
  FROM repositorio.documentos WHERE activo = TRUE
UNION ALL
SELECT 'origen', origen::text, count(*)
  FROM repositorio.documentos WHERE activo = TRUE GROUP BY origen
UNION ALL
SELECT 'tipo', t.nombre::text, count(*)
  FROM repositorio.documentos d
  JOIN repositorio.tipo_documento t ON t.id_tipo_documento = d.id_tipo_documento
 WHERE d.activo = TRUE GROUP BY t.nombre
UNION ALL
SELECT 'firma',
       CASE WHEN tiene_firma_digital THEN 'con_firma' ELSE 'sin_firma' END::text,
       count(*)
  FROM repositorio.documentos WHERE activo = TRUE
 GROUP BY CASE WHEN tiene_firma_digital THEN 'con_firma' ELSE 'sin_firma' END
UNION ALL
-- Expedientes por origen: la clave de agrupacion es distinta en cada origen
SELECT 'expedientes', 'EDAN', count(DISTINCT id_edan)
  FROM repositorio.documentos
 WHERE activo = TRUE AND origen = 'EDAN' AND id_edan IS NOT NULL
UNION ALL
SELECT 'expedientes', 'RIDA', count(DISTINCT id_evento_rida)
  FROM repositorio.documentos
 WHERE activo = TRUE AND origen = 'RIDA' AND id_evento_rida IS NOT NULL
UNION ALL
SELECT 'expedientes', 'DOC_PRECEDENTE', count(DISTINCT codigo_documento)
  FROM repositorio.documentos
 WHERE activo = TRUE AND origen = 'DOC_PRECEDENTE'
   AND codigo_documento IS NOT NULL;

        COMMENT ON VIEW publico.v_repo_resumen IS
            'Metricas publicas del repositorio: total, por origen, por tipo, por '
            'firma y expedientes (distinct de la clave de agrupacion por origen). '
            'Solo conteos: nunca expone codigo_documento, rutas ni nombres.';

    END IF;
END $mig$;

COMMIT;
SELECT 'IDEMPOTENT OK v2.67.0 codigo_documento + metrica expedientes';
