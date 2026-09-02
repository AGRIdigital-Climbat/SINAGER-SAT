-- Migración v1.3.3: fecha_modificacion por fila de sección
-- Permite resolución de conflictos LWW (última escritura gana) POR FILA
-- en el sync offline-first. La app envía su fecha UTC de edición y el
-- servidor la adopta (GREATEST con la actual).
--
-- DEFAULT NOW(): backfillea las filas existentes y sirve de default en INSERT.

ALTER TABLE edan.edan_localidades_danos_agricultura      ADD COLUMN fecha_modificacion timestamptz NOT NULL DEFAULT NOW();
ALTER TABLE edan.edan_localidades_danos_infra_publica    ADD COLUMN fecha_modificacion timestamptz NOT NULL DEFAULT NOW();
ALTER TABLE edan.edan_localidades_danos_pecuario         ADD COLUMN fecha_modificacion timestamptz NOT NULL DEFAULT NOW();
ALTER TABLE edan.edan_localidades_danos_viales           ADD COLUMN fecha_modificacion timestamptz NOT NULL DEFAULT NOW();
ALTER TABLE edan.edan_localidades_danos_vivienda         ADD COLUMN fecha_modificacion timestamptz NOT NULL DEFAULT NOW();
ALTER TABLE edan.edan_localidades_impacto_poblacion      ADD COLUMN fecha_modificacion timestamptz NOT NULL DEFAULT NOW();
ALTER TABLE edan.edan_localidades_infra_productiva       ADD COLUMN fecha_modificacion timestamptz NOT NULL DEFAULT NOW();
ALTER TABLE edan.edan_localidades_necesidades_humanitarias ADD COLUMN fecha_modificacion timestamptz NOT NULL DEFAULT NOW();
ALTER TABLE edan.edan_localidades_primera_respuesta      ADD COLUMN fecha_modificacion timestamptz NOT NULL DEFAULT NOW();
ALTER TABLE edan.edan_localidades_proteccion             ADD COLUMN fecha_modificacion timestamptz NOT NULL DEFAULT NOW();
ALTER TABLE edan.edan_localidades_salud_establecimientos ADD COLUMN fecha_modificacion timestamptz NOT NULL DEFAULT NOW();
ALTER TABLE edan.edan_localidades_salud_necesidades      ADD COLUMN fecha_modificacion timestamptz NOT NULL DEFAULT NOW();
ALTER TABLE edan.edan_localidades_servicios_basicos      ADD COLUMN fecha_modificacion timestamptz NOT NULL DEFAULT NOW();
ALTER TABLE edan.edan_localidades_unidades_educativas    ADD COLUMN fecha_modificacion timestamptz NOT NULL DEFAULT NOW();