-- v2.62.0: Módulo de Almacenes Autónomos (compatible con esquema actual)
BEGIN;

-- 1. Crear tabla rida.almacen
CREATE TABLE IF NOT EXISTS rida.almacen (
    id_almacen SERIAL PRIMARY KEY,
    codigo VARCHAR(30) UNIQUE NOT NULL,
    nombre VARCHAR(150) NOT NULL,
    descripcion TEXT,
    nivel VARCHAR(15) NOT NULL CHECK (nivel IN ('municipal','departamental','nacional')),
    id_municipio INTEGER REFERENCES shared.municipio(id),
    id_departamento INTEGER REFERENCES shared.departamento(id),
    direccion VARCHAR(250),
    lat NUMERIC(10,7),
    lon NUMERIC(10,7),
    capacidad_m2 NUMERIC(10,2),
    estado VARCHAR(15) NOT NULL DEFAULT 'ACTIVO' CHECK (estado IN ('ACTIVO','INACTIVO','MANTENIMIENTO')),
    id_responsable_operativo INTEGER REFERENCES usuarios.usuario(id_usuario),
    creado_por INTEGER REFERENCES usuarios.usuario(id_usuario),
    fecha_creacion TIMESTAMP NOT NULL DEFAULT NOW(),
    fecha_modificacion TIMESTAMP DEFAULT NOW()
);

-- Migrar
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='rida' AND table_name='cat_almacen') THEN
        INSERT INTO rida.almacen (codigo, nombre, nivel, id_municipio, id_departamento, estado, fecha_creacion)
        SELECT 
            COALESCE(c.codigo, 'ALM-' || LPAD(c.id_almacen::text, 6, '0')),
            c.nombre,
            CASE 
                WHEN c.nivel = 'regional' THEN 'departamental'
                WHEN c.nivel IN ('municipal','departamental','nacional') THEN c.nivel
                ELSE 'departamental'
            END,
            NULL,
            c.id_departamento,
            CASE WHEN c.activo THEN 'ACTIVO' ELSE 'INACTIVO' END,
            NOW()
        FROM rida.cat_almacen c
        ON CONFLICT (codigo) DO NOTHING;
    END IF;
END $$;

-- 2. Ampliar cat_articulo
ALTER TABLE rida.cat_articulo ADD COLUMN IF NOT EXISTS controla_lote BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE rida.cat_articulo ADD COLUMN IF NOT EXISTS controla_vencimiento BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE rida.cat_articulo ADD COLUMN IF NOT EXISTS volumen_unitario_m3 NUMERIC(10,4);

-- 3. Solicitud interna
CREATE TABLE IF NOT EXISTS rida.almacen_solicitud (
    id_solicitud_salida SERIAL PRIMARY KEY,
    nro_solicitud VARCHAR(30) UNIQUE NOT NULL,
    id_solicitud INTEGER REFERENCES rida.solicitud(id_solicitud),
    id_almacen INTEGER REFERENCES rida.almacen(id_almacen),
    id_municipio INTEGER REFERENCES shared.municipio(id),
    id_departamento INTEGER REFERENCES shared.departamento(id),
    tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('DESPACHO','MERMA','VENCIMIENTO','OTRO')),
    motivo TEXT NOT NULL,
    id_usuario_solicita INTEGER REFERENCES usuarios.usuario(id_usuario) NOT NULL,
    id_usuario_autoriza INTEGER REFERENCES usuarios.usuario(id_usuario),
    fecha_solicitud TIMESTAMP NOT NULL DEFAULT NOW(),
    fecha_autorizacion TIMESTAMP,
    estado VARCHAR(20) NOT NULL DEFAULT 'SOLICITADA' CHECK (estado IN ('SOLICITADA','APROBADA','RECHAZADA','ATENDIDA_PARCIAL','ATENDIDA_TOTAL','CANCELADA')),
    motivo_rechazo TEXT,
    observaciones TEXT
);

CREATE TABLE IF NOT EXISTS rida.almacen_solicitud_detalle (
    id_detalle_sol_salida SERIAL PRIMARY KEY,
    id_solicitud_salida INTEGER NOT NULL REFERENCES rida.almacen_solicitud(id_solicitud_salida) ON DELETE CASCADE,
    id_articulo INTEGER NOT NULL REFERENCES rida.cat_articulo(id_articulo),
    cantidad_solicitada NUMERIC(12,2) NOT NULL CHECK (cantidad_solicitada > 0),
    cantidad_atendida NUMERIC(12,2) DEFAULT 0,
    observaciones VARCHAR(250)
);

-- 4. NEA
CREATE TABLE IF NOT EXISTS rida.almacen_entrada (
    id_entrada BIGSERIAL PRIMARY KEY,
    nro_nea VARCHAR(30) UNIQUE NOT NULL,
    id_almacen INTEGER NOT NULL REFERENCES rida.almacen(id_almacen),
    tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('CARGA_INICIAL','DONACION','COMPRA','DEVOLUCION','AJUSTE','OTRO')),
    proveedor_donante VARCHAR(150),
    id_documento_soporte BIGINT,
    fecha_entrada DATE NOT NULL,
    hora_entrada TIME,
    id_usuario_registra INTEGER NOT NULL REFERENCES usuarios.usuario(id_usuario),
    id_usuario_verifica INTEGER REFERENCES usuarios.usuario(id_usuario),
    fecha_verificacion TIMESTAMP,
    conformidad BOOLEAN,
    estado VARCHAR(15) NOT NULL DEFAULT 'REGISTRADA' CHECK (estado IN ('BORRADOR','REGISTRADA','ANULADA')),
    observaciones TEXT,
    motivo_anulacion TEXT,
    anulado_por INTEGER REFERENCES usuarios.usuario(id_usuario),
    fecha_anulacion TIMESTAMP,
    fecha_creacion TIMESTAMP NOT NULL DEFAULT NOW(),
    fecha_modificacion TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS rida.almacen_entrada_detalle (
    id_detalle_entrada BIGSERIAL PRIMARY KEY,
    id_entrada BIGINT NOT NULL REFERENCES rida.almacen_entrada(id_entrada) ON DELETE RESTRICT,
    id_articulo INTEGER NOT NULL REFERENCES rida.cat_articulo(id_articulo),
    cantidad NUMERIC(12,2) NOT NULL CHECK (cantidad > 0),
    lote VARCHAR(40),
    fecha_vencimiento DATE,
    valor_unitario_bs NUMERIC(12,2),
    valor_total_bs NUMERIC(14,2),
    observaciones VARCHAR(250)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_alm_entrada_det_unq ON rida.almacen_entrada_detalle(id_entrada, id_articulo, COALESCE(lote,''), COALESCE(fecha_vencimiento,'0001-01-01'));

-- 5. Extender existentes
ALTER TABLE rida.entrega ADD COLUMN IF NOT EXISTS id_solicitud_salida INTEGER;
ALTER TABLE rida.entrega ADD COLUMN IF NOT EXISTS fecha_despacho TIMESTAMP;
ALTER TABLE rida.entrega ADD COLUMN IF NOT EXISTS id_usuario_despacha INTEGER;
ALTER TABLE rida.entrega ADD COLUMN IF NOT EXISTS id_documento_lista_firmada BIGINT;

ALTER TABLE rida.entrega_detalle ADD COLUMN IF NOT EXISTS lote VARCHAR(40);
ALTER TABLE rida.entrega_detalle ADD COLUMN IF NOT EXISTS fecha_vencimiento DATE;
ALTER TABLE rida.entrega_detalle ADD COLUMN IF NOT EXISTS cantidad_despachada NUMERIC(12,2);
ALTER TABLE rida.entrega_detalle ADD COLUMN IF NOT EXISTS cantidad_entregada_acumulada NUMERIC(12,2) DEFAULT 0;

ALTER TABLE rida.entrega_beneficiario ADD COLUMN IF NOT EXISTS codigo_familia VARCHAR(30);
ALTER TABLE rida.entrega_beneficiario ADD COLUMN IF NOT EXISTS ci_jefe_familia VARCHAR(20);
ALTER TABLE rida.entrega_beneficiario ADD COLUMN IF NOT EXISTS nombre_jefe_familia VARCHAR(150);
ALTER TABLE rida.entrega_beneficiario ADD COLUMN IF NOT EXISTS metodo_verificacion VARCHAR(30);
ALTER TABLE rida.entrega_beneficiario ADD COLUMN IF NOT EXISTS id_usuario_entrega INTEGER;
ALTER TABLE rida.entrega_beneficiario ADD COLUMN IF NOT EXISTS fecha_hora_entrega TIMESTAMP;
ALTER TABLE rida.entrega_beneficiario ADD COLUMN IF NOT EXISTS id_documento_lista_firmada BIGINT;

ALTER TABLE rida.solicitud_articulo ADD COLUMN IF NOT EXISTS cantidad_atendida_acumulada NUMERIC(12,2) DEFAULT 0;

-- 6. Kardex
CREATE TABLE IF NOT EXISTS rida.almacen_movimiento (
    id_movimiento BIGSERIAL PRIMARY KEY,
    id_almacen INTEGER NOT NULL REFERENCES rida.almacen(id_almacen),
    id_articulo INTEGER NOT NULL REFERENCES rida.cat_articulo(id_articulo),
    lote VARCHAR(40),
    fecha_vencimiento DATE,
    tipo_movimiento VARCHAR(15) NOT NULL CHECK (tipo_movimiento IN ('ENTRADA','SALIDA','AJUSTE')),
    cantidad_signed NUMERIC(12,2) NOT NULL,
    cantidad_abs NUMERIC(12,2) NOT NULL CHECK (cantidad_abs > 0),
    referencia_tipo VARCHAR(15) NOT NULL CHECK (referencia_tipo IN ('NEA','PECOSA','CONTEO','ANULACION','OTRO')),
    referencia_id BIGINT,
    nro_documento VARCHAR(30),
    id_usuario INTEGER NOT NULL REFERENCES usuarios.usuario(id_usuario),
    fecha_movimiento TIMESTAMP NOT NULL DEFAULT NOW(),
    observacion VARCHAR(500)
);

CREATE INDEX IF NOT EXISTS idx_alm_mov_alm_art_fecha ON rida.almacen_movimiento(id_almacen, id_articulo, fecha_movimiento);

-- 7. Stock
CREATE TABLE IF NOT EXISTS rida.almacen_stock (
    id_stock BIGSERIAL PRIMARY KEY,
    id_almacen INTEGER NOT NULL REFERENCES rida.almacen(id_almacen),
    id_articulo INTEGER NOT NULL REFERENCES rida.cat_articulo(id_articulo),
    lote VARCHAR(40) NOT NULL DEFAULT '',
    fecha_vencimiento DATE,
    cantidad_disponible NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (cantidad_disponible >= 0),
    stock_minimo NUMERIC(12,2),
    stock_maximo NUMERIC(12,2),
    costo_referencia_bs NUMERIC(12,2),
    fecha_ultima_actualizacion TIMESTAMP NOT NULL DEFAULT NOW(),
    fecha_ultima_entrada DATE,
    fecha_ultima_salida DATE
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_alm_stock_unq ON rida.almacen_stock(id_almacen, id_articulo, lote, COALESCE(fecha_vencimiento,'0001-01-01'));

-- 8. Evidencia offline
CREATE TABLE IF NOT EXISTS rida.almacen_entrega_evidencia_offline (
    id_evidencia_offline BIGSERIAL PRIMARY KEY,
    local_uuid UUID NOT NULL,
    local_uuid_evidencia UUID NOT NULL UNIQUE,
    id_entrega_beneficiario BIGINT,
    id_entrega BIGINT,
    id_almacen INTEGER,
    tipo_evidencia VARCHAR(25) NOT NULL CHECK (tipo_evidencia IN ('FIRMA_DIGITAL','FOTO_BENEFICIARIO','FOTO_ENTREGA','FOTO_IDENTIFICACION')),
    archivo_nombre VARCHAR(150) NOT NULL,
    archivo_tipo_mime VARCHAR(50) NOT NULL,
    archivo_tamano_bytes BIGINT,
    archivo_hash_sha256 VARCHAR(64) NOT NULL,
    ruta_local TEXT,
    id_documento_servidor BIGINT,
    sync_status VARCHAR(15) NOT NULL DEFAULT 'PENDIENTE' CHECK (sync_status IN ('PENDIENTE','SUBIENDO','SINCRONIZADO','ERROR')),
    intentos_sincronizacion INTEGER DEFAULT 0,
    ultimo_error TEXT,
    fecha_captura TIMESTAMP NOT NULL,
    dispositivo_id VARCHAR(100) NOT NULL
);

-- 9. Trigger
CREATE OR REPLACE FUNCTION rida.fn_almacen_stock_update()
RETURNS TRIGGER AS $$
DECLARE
    v_disponible NUMERIC(12,2);
BEGIN
    SELECT COALESCE(SUM(cantidad_signed), 0)
    INTO v_disponible
    FROM rida.almacen_movimiento
    WHERE id_almacen = NEW.id_almacen
      AND id_articulo = NEW.id_articulo
      AND COALESCE(lote,'') = COALESCE(NEW.lote,'')
      AND COALESCE(fecha_vencimiento,'0001-01-01') = COALESCE(NEW.fecha_vencimiento,'0001-01-01');
    
    IF v_disponible < 0 THEN
        RAISE EXCEPTION 'Stock insuficiente/disponible negativo';
    END IF;
    
    INSERT INTO rida.almacen_stock (id_almacen, id_articulo, lote, fecha_vencimiento, cantidad_disponible, fecha_ultima_actualizacion)
    VALUES (NEW.id_almacen, NEW.id_articulo, COALESCE(NEW.lote,''), NEW.fecha_vencimiento, v_disponible, NOW())
    ON CONFLICT (id_almacen, id_articulo, lote, COALESCE(fecha_vencimiento,'0001-01-01'))
    DO UPDATE SET cantidad_disponible = v_disponible, fecha_ultima_actualizacion = NOW();
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_almacen_stock_update ON rida.almacen_movimiento;
CREATE TRIGGER trg_almacen_stock_update
AFTER INSERT ON rida.almacen_movimiento
FOR EACH ROW
EXECUTE FUNCTION rida.fn_almacen_stock_update();

COMMIT;
