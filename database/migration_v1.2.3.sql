-- ============================================
-- MIGRACIÓN v1.2.3
-- ============================================
-- Ejecutar como usuario con permisos de creación en PostgreSQL.
-- Contiene: columna id_rol, fixes EDAN, esquema REA completo con datos iniciales.
-- ============================================

-- ── 1. Agregar columna id_rol a usuarios.usuario ──
ALTER TABLE usuarios.usuario ADD COLUMN IF NOT EXISTS id_rol INTEGER;
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'usuario_id_rol_fkey'
    ) THEN
        ALTER TABLE usuarios.usuario
            ADD CONSTRAINT usuario_id_rol_fkey
            FOREIGN KEY (id_rol) REFERENCES usuarios.rol(id_rol);
    END IF;
END $$;
ALTER TABLE usuarios.usuario ALTER COLUMN id_rol SET DEFAULT 4;

-- ── 2. UNIQUE constraint en carnet ──
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'uq_usuario_carnet'
    ) THEN
        ALTER TABLE usuarios.usuario ADD CONSTRAINT uq_usuario_carnet UNIQUE (carnet);
    END IF;
END $$;

-- ── 3. Columna fotografia en edan.edan ──
ALTER TABLE edan.edan ADD COLUMN IF NOT EXISTS fotografia TEXT;

-- ── 4. Crear esquema REA ──
CREATE SCHEMA IF NOT EXISTS rea;

-- ── 3. Tabla de estados del reporte ──
CREATE TABLE IF NOT EXISTS rea.estado_reporte (
    id_estado   SERIAL PRIMARY KEY,
    nombre      VARCHAR(100) NOT NULL,
    descripcion TEXT,
    orden       INTEGER NOT NULL DEFAULT 0
);

-- ── 4. Tabla de categorías de afectación ──
CREATE TABLE IF NOT EXISTS rea.afectacion_categoria (
    id_categoria SERIAL PRIMARY KEY,
    nombre       VARCHAR(200) NOT NULL,
    descripcion  TEXT,
    orden        INTEGER NOT NULL DEFAULT 0
);

-- ── 5. Tabla principal de reportes de eventos ──
CREATE TABLE IF NOT EXISTS rea.reporte_evento (
    id_reporte      SERIAL PRIMARY KEY,
    id_usuario      INTEGER NOT NULL,
    id_departamento INTEGER NOT NULL,
    id_provincia    INTEGER NOT NULL,
    id_municipio    INTEGER NOT NULL,
    comunidad       VARCHAR(200) NOT NULL,
    fecha_evento    VARCHAR(20) NOT NULL,
    hora_evento     VARCHAR(10),
    fecha_reporte   TIMESTAMP DEFAULT NOW(),
    id_tipo_evento  INTEGER NOT NULL,
    coordenada_lat  NUMERIC(10,7),
    coordenada_lon  NUMERIC(10,7),
    fotografia      TEXT,
    descripcion     TEXT,
    id_estado       INTEGER NOT NULL DEFAULT 1,

    CONSTRAINT reporte_evento_id_usuario_fkey
        FOREIGN KEY (id_usuario) REFERENCES usuarios.usuario(id_usuario),
    CONSTRAINT reporte_evento_id_departamento_fkey
        FOREIGN KEY (id_departamento) REFERENCES shared.departamento(id),
    CONSTRAINT reporte_evento_id_provincia_fkey
        FOREIGN KEY (id_provincia) REFERENCES shared.provincia(id),
    CONSTRAINT reporte_evento_id_municipio_fkey
        FOREIGN KEY (id_municipio) REFERENCES shared.municipio(id),
    CONSTRAINT reporte_evento_id_tipo_evento_fkey
        FOREIGN KEY (id_tipo_evento) REFERENCES edan.tipo_evento(id_tipo_evento),
    CONSTRAINT reporte_evento_id_estado_fkey
        FOREIGN KEY (id_estado) REFERENCES rea.estado_reporte(id_estado)
);

-- ── 6. Tabla de afectaciones por reporte (N:N) ──
CREATE TABLE IF NOT EXISTS rea.reporte_afectacion (
    id_reporte   INTEGER NOT NULL,
    id_categoria INTEGER NOT NULL,

    PRIMARY KEY (id_reporte, id_categoria),
    CONSTRAINT reporte_afectacion_id_reporte_fkey
        FOREIGN KEY (id_reporte) REFERENCES rea.reporte_evento(id_reporte) ON DELETE CASCADE,
    CONSTRAINT reporte_afectacion_id_categoria_fkey
        FOREIGN KEY (id_categoria) REFERENCES rea.afectacion_categoria(id_categoria)
);

-- ── 7. Índices ──
CREATE INDEX IF NOT EXISTS idx_reporte_usuario    ON rea.reporte_evento(id_usuario);
CREATE INDEX IF NOT EXISTS idx_reporte_estado     ON rea.reporte_evento(id_estado);
CREATE INDEX IF NOT EXISTS idx_reporte_municipio  ON rea.reporte_evento(id_municipio);

-- ── 8. Datos iniciales: estados ──
INSERT INTO rea.estado_reporte (nombre, descripcion, orden) VALUES
    ('Pendiente',   'Reporte registrado, pendiente de revisión', 1),
    ('En revisión', 'Siendo revisado por un administrador',      2),
    ('Aprobado',    'Reporte verificado y aprobado',             3),
    ('Rechazado',   'Reporte rechazado',                         4),
    ('Cerrado',     'Caso cerrado o resuelto',                   5)
ON CONFLICT DO NOTHING;

-- ── 9. Datos iniciales: categorías de afectación ──
INSERT INTO rea.afectacion_categoria (nombre, descripcion, orden) VALUES
    ('Víctimas fatales',                'Personas fallecidas',                 1),
    ('Heridos',                         'Personas con lesiones',               2),
    ('Desplazados',                     'Personas desplazadas de sus hogares', 3),
    ('Viviendas dañadas',               'Viviendas con daño total o parcial',  4),
    ('Infraestructura dañada',          'Infraestructura pública afectada',    5),
    ('Servicios básicos interrumpidos', 'Agua, luz, alcantarillado',           6),
    ('Pérdida de cultivos',             'Áreas agrícolas afectadas',           7),
    ('Pérdida ganadera',                'Animales muertos o perdidos',         8)
ON CONFLICT DO NOTHING;

-- ── 10. Ajustar secuencias ──
SELECT setval('rea.estado_reporte_id_estado_seq', (SELECT COALESCE(MAX(id_estado), 1) FROM rea.estado_reporte));
SELECT setval('rea.afectacion_categoria_id_categoria_seq', (SELECT COALESCE(MAX(id_categoria), 1) FROM rea.afectacion_categoria));
