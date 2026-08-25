-- v2.9.1: Recrear índices únicos de secciones SIN WHERE clause
-- Los índices parciales WHERE (id_seccion IS NOT NULL) no son compatibles con
-- ON CONFLICT (id_seccion) de PostgreSQL. Los recreamos como índices regulares.
-- PostgreSQL permite múltiples NULLs en UNIQUE, así que id_seccion=NULL sigue
-- funcionando para inserts sin dedup.
--
-- FIX: error "there is no unique or exclusion constraint matching the ON CONFLICT
-- specification" al sincronizar localidades desde la app móvil.

BEGIN;

DROP INDEX IF EXISTS edan.idx_seccion_impacto_poblacion;
DROP INDEX IF EXISTS edan.idx_seccion_servicios_basicos;
DROP INDEX IF EXISTS edan.idx_seccion_salud_establecimientos;
DROP INDEX IF EXISTS edan.idx_seccion_danos_viales;
DROP INDEX IF EXISTS edan.idx_seccion_danos_infra_publica;
DROP INDEX IF EXISTS edan.idx_seccion_unidades_educativas;
DROP INDEX IF EXISTS edan.idx_seccion_danos_vivienda;
DROP INDEX IF EXISTS edan.idx_seccion_danos_agricultura;
DROP INDEX IF EXISTS edan.idx_seccion_danos_pecuario;
DROP INDEX IF EXISTS edan.idx_seccion_infra_productiva;
DROP INDEX IF EXISTS edan.idx_seccion_proteccion;

CREATE UNIQUE INDEX idx_seccion_impacto_poblacion ON edan.edan_localidades_impacto_poblacion (id_seccion);
CREATE UNIQUE INDEX idx_seccion_servicios_basicos ON edan.edan_localidades_servicios_basicos (id_seccion);
CREATE UNIQUE INDEX idx_seccion_salud_establecimientos ON edan.edan_localidades_salud_establecimientos (id_seccion);
CREATE UNIQUE INDEX idx_seccion_danos_viales ON edan.edan_localidades_danos_viales (id_seccion);
CREATE UNIQUE INDEX idx_seccion_danos_infra_publica ON edan.edan_localidades_danos_infra_publica (id_seccion);
CREATE UNIQUE INDEX idx_seccion_unidades_educativas ON edan.edan_localidades_unidades_educativas (id_seccion);
CREATE UNIQUE INDEX idx_seccion_danos_vivienda ON edan.edan_localidades_danos_vivienda (id_seccion);
CREATE UNIQUE INDEX idx_seccion_danos_agricultura ON edan.edan_localidades_danos_agricultura (id_seccion);
CREATE UNIQUE INDEX idx_seccion_danos_pecuario ON edan.edan_localidades_danos_pecuario (id_seccion);
CREATE UNIQUE INDEX idx_seccion_infra_productiva ON edan.edan_localidades_infra_productiva (id_seccion);
CREATE UNIQUE INDEX idx_seccion_proteccion ON edan.edan_localidades_proteccion (id_seccion);

COMMIT;
