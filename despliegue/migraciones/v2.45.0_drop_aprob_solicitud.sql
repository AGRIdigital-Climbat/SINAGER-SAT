-- ============================================================================
-- SINAGERSAT - Migración v2.45.0 (idempotente)
-- RIDA: FASE 2 de la máquina de aprobaciones — retira los 15 booleanos
--       derivados de rida.solicitud
--
-- La fuente de verdad es rida.aprobaciones_solicitud (una fila por nivel de la
-- cadena activa, creada por asegurar_aprobaciones() al entrar en EN_APROBACION).
-- Los 15 campos aprob_<nivel> / _fecha / _por de rida.solicitud eran una copia
-- espejada por _sincronizar_cabecera() para que la bandeja del frontend pudiera
-- leer el estado sin un GET de la máquina por fila.
--
-- Ahora el listado y el detalle derivan las aprobaciones con un subquery
-- json_agg sobre la tabla nueva, así que la copia deja de existir.
--
-- Se elimina también la cascada de 5 FKs de los *_por que acompañaban a las
-- columnas (las dropea PostgreSQL al caer la columna).
--
-- (La documentación preveía "v2.37.0_drop_aprob_solicitud.sql"; los versionados
-- ya iban en v2.44.0, así que corresponde v2.45.0.)
-- ============================================================================

BEGIN;

ALTER TABLE rida.solicitud
    DROP COLUMN IF EXISTS aprob_ugr,
    DROP COLUMN IF EXISTS aprob_ugr_fecha,
    DROP COLUMN IF EXISTS aprob_ugr_por,
    DROP COLUMN IF EXISTS aprob_alcalde,
    DROP COLUMN IF EXISTS aprob_alcalde_fecha,
    DROP COLUMN IF EXISTS aprob_alcalde_por,
    DROP COLUMN IF EXISTS aprob_dgr,
    DROP COLUMN IF EXISTS aprob_dgr_fecha,
    DROP COLUMN IF EXISTS aprob_dgr_por,
    DROP COLUMN IF EXISTS aprob_videcid,
    DROP COLUMN IF EXISTS aprob_videcid_fecha,
    DROP COLUMN IF EXISTS aprob_videcid_por,
    DROP COLUMN IF EXISTS aprob_direccion,
    DROP COLUMN IF EXISTS aprob_direccion_fecha,
    DROP COLUMN IF EXISTS aprob_direccion_por;

SELECT 'IDEMPOTENT OK v2.45.0 drop aprob_solicitud (15 columnas)' AS resultado;

COMMIT;
