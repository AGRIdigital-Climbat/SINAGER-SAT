-- ============================================================================
-- SINAGERSAT - Migración v2.7.0 (idempotente)
-- Crea el esquema `repositorio` y la tabla de catálogo `tipo_documento`.
-- El esquema está separado de `edan` para que RIDA pueda accederlo
-- independientemente y mantener una mejor organización.
-- ============================================================================

BEGIN;

CREATE SCHEMA IF NOT EXISTS repositorio;

CREATE TABLE IF NOT EXISTS repositorio.tipo_documento (
    id_tipo_documento       SERIAL PRIMARY KEY,
    codigo                  VARCHAR(50) UNIQUE NOT NULL,
    nombre                  VARCHAR(100) NOT NULL,
    descripcion             TEXT,
    orden                   INTEGER DEFAULT 0,
    activo                  BOOLEAN DEFAULT TRUE,
    requiere_versionado     BOOLEAN DEFAULT FALSE,
    extensiones_permitidas  VARCHAR(50) DEFAULT 'pdf',
    tamano_maximo_bytes     INTEGER DEFAULT 52428800
);

INSERT INTO repositorio.tipo_documento
    (codigo, nombre, descripcion, orden, requiere_versionado, extensiones_permitidas, tamano_maximo_bytes)
VALUES
    ('informe_legal',        'Informe Legal',                'Informe jurídico del caso o gestión',                  1, TRUE,  'pdf', 52428800),
    ('informe_tecnico',      'Informe Técnico',              'Informe técnico del daño o evaluación',                 2, TRUE,  'pdf', 52428800),
    ('informe_financiero',   'Informe Técnico-Financiero',   'Evaluación financiera de daños y costos',               3, TRUE,  'pdf', 52428800),
    ('ley_municipal',        'Ley Municipal',                'Ley municipal de declaratoria de emergencia',           4, TRUE,  'pdf', 52428800),
    ('resolucion_alcaldicia','Resolución de Alcaldía',       'Resolución oficial de alcaldía',                        5, TRUE,  'pdf', 52428800),
    ('certificado_dano',     'Certificado de Daño',          'Certificación oficial del daño',                        6, FALSE, 'pdf', 52428800),
    ('otro',                 'Otro',                         'Otros documentos PDF',                                  99, FALSE, 'pdf', 52428800)
ON CONFLICT (codigo) DO NOTHING;

COMMIT;

SELECT 'IDEMPOTENT OK v2.7.0' AS resultado;
