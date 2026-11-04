-- Rollback de la integracion de MotorIA.
-- Elimina unicamente el esquema motor_ia. No elimina extensiones porque
-- pg_trgm ya existia y vector podria ser usado por otros esquemas.

BEGIN;

DROP SCHEMA IF EXISTS motor_ia CASCADE;

COMMIT;
