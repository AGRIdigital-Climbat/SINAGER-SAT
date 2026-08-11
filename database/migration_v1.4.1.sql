-- ============================================================================
-- SINAGERSAT - Migración v1.4.1 (idempotente)
-- 1. Agrega la columna `descripcion` a edan.tipo_evento.
-- 2. Elimina 4 catálogos del modelo intermedio ya sin uso (sus datos hoy son
--    CHECKs / columnas directas en las sub-tablas): grupo_etario,
--    servicio_basico, categoria_proteccion y ayuda_humanitaria.
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

-- Catálogos intermedios sin uso en el modelo jerárquico actual
DROP TABLE IF EXISTS edan.grupo_etario;
DROP TABLE IF EXISTS edan.servicio_basico;
DROP TABLE IF EXISTS edan.categoria_proteccion;
DROP TABLE IF EXISTS edan.ayuda_humanitaria;

COMMIT;

SELECT 'IDEMPOTENT OK v1.4.1' AS resultado;
