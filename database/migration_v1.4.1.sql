-- ============================================================================
-- SINAGERSAT - Migración v1.4.1 (idempotente)
-- Agrega la columna `descripcion` a edan.tipo_evento para alinear el catálogo
-- con los schemas Pydantic (TipoEventoCreate/Update/Response).
-- Aplica sobre migration_v1.4.0.
-- ============================================================================

BEGIN;

ALTER TABLE edan.tipo_evento ADD COLUMN IF NOT EXISTS descripcion VARCHAR(150);

-- Backfill de descripciones por tipo de evento
UPDATE edan.tipo_evento SET descripcion = 'Inundación por desborde de ríos o lluvias' WHERE id_tipo_evento = 1 AND descripcion IS NULL;
UPDATE edan.tipo_evento SET descripcion = 'Crecida repentina de un cauce' WHERE id_tipo_evento = 2 AND descripcion IS NULL;
UPDATE edan.tipo_evento SET descripcion = 'Deslizamiento de laderas y taludes' WHERE id_tipo_evento = 3 AND descripcion IS NULL;
UPDATE edan.tipo_evento SET descripcion = 'Helada y bajas temperaturas' WHERE id_tipo_evento = 4 AND descripcion IS NULL;
UPDATE edan.tipo_evento SET descripcion = 'Granizada' WHERE id_tipo_evento = 5 AND descripcion IS NULL;
UPDATE edan.tipo_evento SET descripcion = 'Sequía y déficit hídrico' WHERE id_tipo_evento = 6 AND descripcion IS NULL;
UPDATE edan.tipo_evento SET descripcion = 'Incendios (forestales, pastizales)' WHERE id_tipo_evento = 7 AND descripcion IS NULL;
UPDATE edan.tipo_evento SET descripcion = 'Otros tipos de evento' WHERE id_tipo_evento = 8 AND descripcion IS NULL;

COMMIT;

SELECT 'IDEMPOTENT OK v1.4.1' AS resultado;
