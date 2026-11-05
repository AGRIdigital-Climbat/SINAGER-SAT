-- v2.62.2: Detalle de entrega por beneficiario + reforzar acta
BEGIN;

CREATE TABLE IF NOT EXISTS rida.almacen_entrega_beneficiario_detalle (
    id_detalle_eb BIGSERIAL PRIMARY KEY,
    id_entrega_beneficiario BIGINT NOT NULL REFERENCES rida.entrega_beneficiario(id_entrega_beneficiario) ON DELETE CASCADE,
    id_articulo INTEGER NOT NULL REFERENCES rida.cat_articulo(id_articulo),
    lote VARCHAR(40),
    fecha_vencimiento DATE,
    cantidad_entregada NUMERIC(12,2) NOT NULL CHECK (cantidad_entregada > 0),
    fecha_creacion TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alm_ebd_eb ON rida.almacen_entrega_beneficiario_detalle(id_entrega_beneficiario);
CREATE INDEX IF NOT EXISTS idx_alm_ebd_art ON rida.almacen_entrega_beneficiario_detalle(id_articulo);

-- Reforzar campos en entrega_beneficiario
ALTER TABLE rida.entrega_beneficiario ADD COLUMN IF NOT EXISTS id_acta_entrega BIGINT;
ALTER TABLE rida.entrega_beneficiario ADD COLUMN IF NOT EXISTS testigo_nombre VARCHAR(150);
ALTER TABLE rida.entrega_beneficiario ADD COLUMN IF NOT EXISTS testigo_ci VARCHAR(20);
ALTER TABLE rida.entrega_beneficiario ADD COLUMN IF NOT EXISTS parentesco VARCHAR(50);
ALTER TABLE rida.entrega_beneficiario ADD COLUMN IF NOT EXISTS tipo_documento VARCHAR(15) DEFAULT 'CI';
ALTER TABLE rida.entrega_beneficiario ADD COLUMN IF NOT EXISTS id_usuario_recibe_distinto INTEGER;

COMMIT;
