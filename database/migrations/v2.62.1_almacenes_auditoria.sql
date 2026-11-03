-- v2.62.1: Completar auditoría en tablas de almacenes
BEGIN;

-- Asegurar campos de auditoría en tablas nuevas
ALTER TABLE rida.almacen ADD COLUMN IF NOT EXISTS fecha_modificacion TIMESTAMP DEFAULT NOW();
ALTER TABLE rida.almacen_solicitud ADD COLUMN IF NOT EXISTS fecha_modificacion TIMESTAMP DEFAULT NOW();
ALTER TABLE rida.almacen_solicitud ADD COLUMN IF NOT EXISTS id_usuario_modifica INTEGER REFERENCES usuarios.usuario(id_usuario);
ALTER TABLE rida.almacen_entrada ADD COLUMN IF NOT EXISTS fecha_modificacion TIMESTAMP DEFAULT NOW();
ALTER TABLE rida.almacen_entrada ADD COLUMN IF NOT EXISTS id_usuario_modifica INTEGER REFERENCES usuarios.usuario(id_usuario);
ALTER TABLE rida.almacen_movimiento ADD COLUMN IF NOT EXISTS fecha_creacion TIMESTAMP DEFAULT NOW();
ALTER TABLE rida.almacen_stock ADD COLUMN IF NOT EXISTS fecha_creacion TIMESTAMP DEFAULT NOW();

-- Extender entrega para auditoría completa
ALTER TABLE rida.entrega ADD COLUMN IF NOT EXISTS fecha_creacion TIMESTAMP DEFAULT NOW();
ALTER TABLE rida.entrega ADD COLUMN IF NOT EXISTS fecha_modificacion TIMESTAMP DEFAULT NOW();
ALTER TABLE rida.entrega ADD COLUMN IF NOT EXISTS id_usuario_crea INTEGER REFERENCES usuarios.usuario(id_usuario);
ALTER TABLE rida.entrega ADD COLUMN IF NOT EXISTS id_usuario_modifica INTEGER REFERENCES usuarios.usuario(id_usuario);

ALTER TABLE rida.entrega_detalle ADD COLUMN IF NOT EXISTS fecha_creacion TIMESTAMP DEFAULT NOW();
ALTER TABLE rida.entrega_beneficiario ADD COLUMN IF NOT EXISTS fecha_creacion TIMESTAMP DEFAULT NOW();
ALTER TABLE rida.entrega_beneficiario ADD COLUMN IF NOT EXISTS fecha_modificacion TIMESTAMP DEFAULT NOW();
ALTER TABLE rida.entrega_beneficiario ADD COLUMN IF NOT EXISTS id_usuario_crea INTEGER REFERENCES usuarios.usuario(id_usuario);
ALTER TABLE rida.entrega_beneficiario ADD COLUMN IF NOT EXISTS id_usuario_modifica INTEGER REFERENCES usuarios.usuario(id_usuario);

-- Triggers para actualizar fecha_modificacion
CREATE OR REPLACE FUNCTION rida.fn_update_fecha_modificacion()
RETURNS TRIGGER AS $$
BEGIN
    NEW.fecha_modificacion = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_almacen_mod ON rida.almacen;
CREATE TRIGGER trg_almacen_mod BEFORE UPDATE ON rida.almacen FOR EACH ROW EXECUTE FUNCTION rida.fn_update_fecha_modificacion();

DROP TRIGGER IF EXISTS trg_almacen_solicitud_mod ON rida.almacen_solicitud;
CREATE TRIGGER trg_almacen_solicitud_mod BEFORE UPDATE ON rida.almacen_solicitud FOR EACH ROW EXECUTE FUNCTION rida.fn_update_fecha_modificacion();

DROP TRIGGER IF EXISTS trg_almacen_entrada_mod ON rida.almacen_entrada;
CREATE TRIGGER trg_almacen_entrada_mod BEFORE UPDATE ON rida.almacen_entrada FOR EACH ROW EXECUTE FUNCTION rida.fn_update_fecha_modificacion();

DROP TRIGGER IF EXISTS trg_entrega_mod ON rida.entrega;
CREATE TRIGGER trg_entrega_mod BEFORE UPDATE ON rida.entrega FOR EACH ROW EXECUTE FUNCTION rida.fn_update_fecha_modificacion();

DROP TRIGGER IF EXISTS trg_entrega_benef_mod ON rida.entrega_beneficiario;
CREATE TRIGGER trg_entrega_benef_mod BEFORE UPDATE ON rida.entrega_beneficiario FOR EACH ROW EXECUTE FUNCTION rida.fn_update_fecha_modificacion();

COMMIT;
