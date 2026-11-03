-- ============================================================================
-- SINAGERSAT - Migración v2.34.0 (idempotente)
-- RIDA: Motor de estados para solicitudes (Fase 1)
--
-- 1) Catálogo de etapas (para API/documentación)
-- 2) CHECK constraint en rida.solicitud.etapa
-- ============================================================================

BEGIN;

-- 1) Catálogo de etapas
CREATE TABLE IF NOT EXISTS rida.cat_etapa_solicitud (
    id_etapa        SERIAL PRIMARY KEY,
    codigo          VARCHAR(30) NOT NULL UNIQUE,
    nombre          VARCHAR(100) NOT NULL,
    orden           INTEGER NOT NULL,
    activo          BOOLEAN NOT NULL DEFAULT TRUE
);

INSERT INTO rida.cat_etapa_solicitud (codigo, nombre, orden, activo) VALUES
    ('BORRADOR', 'Borrador', 1, TRUE),
    ('ENVIADA', 'Enviada', 2, TRUE),
    ('EN_REVISION', 'En revisión', 3, TRUE),
    ('OBSERVADA', 'Observada', 4, TRUE),
    ('VALIDADA', 'Validada', 5, TRUE),
    ('EN_APROBACION', 'En aprobación', 6, TRUE),
    ('APROBADA', 'Aprobada', 7, TRUE),
    ('RECHAZADA', 'Rechazada', 8, TRUE),
    ('AUTORIZADA', 'Autorizada', 9, TRUE),
    ('EN_SUMINISTROS', 'En suministros', 10, TRUE),
    ('DESPACHO_AUTORIZADO', 'Despacho autorizado', 11, TRUE),
    ('DESPACHADA', 'Despachada', 12, TRUE),
    ('EN_TRANSPORTE', 'En transporte', 13, TRUE),
    ('RECIBIDA', 'Recibida', 14, TRUE),
    ('EN_DISTRIBUCION', 'En distribución', 15, TRUE),
    ('ENTREGADA', 'Entregada', 16, TRUE),
    ('CERRADA', 'Cerrada', 17, TRUE)
ON CONFLICT (codigo) DO UPDATE SET nombre = EXCLUDED.nombre, orden = EXCLUDED.orden, activo = EXCLUDED.activo;

-- 2) CHECK constraint en solicitud.etapa
ALTER TABLE rida.solicitud DROP CONSTRAINT IF EXISTS solicitud_etapa_check;
ALTER TABLE rida.solicitud ADD CONSTRAINT solicitud_etapa_check CHECK (
    etapa IN (
        'BORRADOR', 'ENVIADA', 'EN_REVISION', 'OBSERVADA', 'VALIDADA',
        'EN_APROBACION', 'APROBADA', 'RECHAZADA', 'AUTORIZADA',
        'EN_SUMINISTROS', 'DESPACHO_AUTORIZADO', 'DESPACHADA',
        'EN_TRANSPORTE', 'RECIBIDA', 'EN_DISTRIBUCION', 'ENTREGADA', 'CERRADA'
    )
);

COMMIT;

SELECT 'IDEMPOTENT OK v2.34.0 workflow_solicitud' AS resultado;
