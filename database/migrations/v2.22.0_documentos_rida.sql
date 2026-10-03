-- ============================================================================
-- SINAGERSAT - Migración v2.22.0 (idempotente)
-- Repositorio de documentos compartido: EDAN y RIDA.
--
--   Contexto: la migración v2.17.0 (§5, "Adaptador mínimo de repositorio
--   documentos") habia preparado el reuso del PDF de AGETIC para RIDA: hizo
--   nullable 'documentos.id_edan' y agrego 'id_solicitud_rida' (FK a
--   rida.solicitud). Pero esa columna apuntaba a rida.solicitud, que NO expone
--   ninguna ruta de API — el modulo rida solo expone rida.formulario_rida
--   (/rida/formularios) — y ningun documento la uso jamas.
--
--   Que hace esta migracion:
--     1. Elimina 'id_solicitud_rida' (y su FK, que cae con la columna).
--     2. Agrega 'id_formulario_rida' (FK a rida.formulario_rida), que es el
--        vinculo real: la entidad que la API de RIDA si maneja.
--     3. Indexa la columna nueva.
--
--   NOTA: rida.solicitud_documento (tabla puente solicitud <-> documentos) NO
--   se toca. Sigue apuntando a documentos.id_documento, que no cambia.
--
--   Modelo resultante. Las dos columnas quedan NULLABLE y se permite que un
--   documento tenga ambas, porque rida.formulario_rida tiene su propio
--   id_edan: un documento de RIDA se guarda con 'id_formulario_rida' Y con el
--   'id_edan' que hereda del formulario, para que quede vinculado a las dos
--   tablas (EDAN y RIDA) y se pueda rastrear desde cualquiera de las dos
--   pantallas.
--
--       id_edan=NULL  id_formulario_rida=NULL  -> invalido (la API lo rechaza)
--       id_edan=X     id_formulario_rida=NULL  -> documento de EDAN
--       id_edan=X     id_formulario_rida=Y     -> documento de RIDA
--       id_edan=NULL  id_formulario_rida=Y     -> documento de RIDA cuyo
--                                               formulario aun no tiene EDAN
--
--   El origen NO es una columna: se deriva de 'id_formulario_rida IS NULL'. Asi
--   no puede quedar desincronizado del dato real, y no necesita backfill.
--
--   IDEMPOTENCIA: DROP COLUMN IF EXISTS y ADD COLUMN IF NOT EXISTS. El indice
--   tambien con IF NOT EXISTS. Se puede aplicar N veces.
--
--   No se reescribe v2.17.0_rida_schema.sql: una migración ya aplicada es
--   historia y no se toca. Este archivo es el que registra el cambio.
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. Fuera el vinculo que nunca se uso
-- ----------------------------------------------------------------------------
-- La FK fk_documentos_solicitud_rida cae automaticamente con la columna.
ALTER TABLE repositorio.documentos
    DROP COLUMN IF EXISTS id_solicitud_rida;

-- ----------------------------------------------------------------------------
-- 2. El vinculo real de RIDA
-- ----------------------------------------------------------------------------
ALTER TABLE repositorio.documentos
    ADD COLUMN IF NOT EXISTS id_formulario_rida INTEGER
    REFERENCES rida.formulario_rida (id_formulario) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_documentos_formulario_rida
    ON repositorio.documentos (id_formulario_rida);

COMMENT ON COLUMN repositorio.documentos.id_edan IS
    'EDAN al que pertenece el documento. NULLABLE: un documento de RIDA lo trae heredado de rida.formulario_rida.id_edan para que quede rastreable desde la pantalla del EDAN. La API lo escribe, no el cliente.';

COMMENT ON COLUMN repositorio.documentos.id_formulario_rida IS
    'Formulario RIDA al que pertenece el documento. NULLABLE: NULL = documento de EDAN, no NULL = documento de RIDA. Define el "origen" que expone la API. Lo escribe la API, no el cliente.';

COMMIT;
