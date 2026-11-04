-- v2.63.1_motor_ia_uso_embeddings_rollback.sql
-- Elimina las metricas de consumo de embeddings.
-- Idempotente.

DROP TABLE IF EXISTS motor_ia.uso_embeddings;
