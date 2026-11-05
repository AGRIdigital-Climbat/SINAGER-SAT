-- ============================================================================
-- SINAGERSAT - Migración v2.35.0 (idempotente)
-- RIDA: Separar Ayuda Humanitaria de Rehabilitación
--
-- 1) Desactivar 5 categorías antiguas de cat_categoria_ayuda
-- 2) Insertar 7 nuevas categorías de Ayuda Humanitaria
-- 3) Crear cat_tipo_rehabilitacion (5 tipos)
-- 4) Crear cat_insumo_rehabilitacion (25 insumos/servicios)
-- 5) Insertar 22 artículos de ayuda humanitaria
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1) DESACTIVAR CATEGORÍAS ANTIGUAS
-- ============================================================================
UPDATE rida.cat_categoria_ayuda SET activo = FALSE;

-- ============================================================================
-- 2) NUEVAS 7 CATEGORÍAS DE AYUDA HUMANITARIA
-- ============================================================================
INSERT INTO rida.cat_categoria_ayuda (codigo, nombre, descripcion, activo) VALUES
    ('ALIMENTOS', 'Alimentos', 'Alimentos básicos y no perecibles', TRUE),
    ('HERRAMIENTAS_MENORES', 'Herramientas menores', 'Herramientas manuales y equipamiento menor', TRUE),
    ('REF_VIVIENDA', 'Refugio y vivienda', 'Materiales de refugio temporal y vivienda', TRUE),
    ('ROPA_CAMA', 'Ropa de cama', 'Sábanas, frazadas, mantas, almohadas', TRUE),
    ('ROPA_AGUA', 'Ropa de agua', 'Impermeables, botas de agua, ponchos', TRUE),
    ('ARTICULOS_HIGIENE', 'Artículos de higiene', 'Jabón, pasta dental, shampoo, toallas, pastillas potabilizadoras', TRUE),
    ('ARTICULOS_COCINA', 'Artículos de cocina', 'Ollas, platos, cubiertos, utensilios de cocina', TRUE)
ON CONFLICT (codigo) DO UPDATE SET nombre = EXCLUDED.nombre, descripcion = EXCLUDED.descripcion, activo = TRUE;

-- ============================================================================
-- 3) TABLA cat_tipo_rehabilitacion (5 tipos)
-- ============================================================================
CREATE TABLE IF NOT EXISTS rida.cat_tipo_rehabilitacion (
    id_tipo_rehabilitacion  SERIAL PRIMARY KEY,
    codigo                  VARCHAR(50) NOT NULL UNIQUE,
    nombre                  VARCHAR(150) NOT NULL,
    descripcion             TEXT,
    id_modalidad            INTEGER REFERENCES rida.cat_modalidad(id_modalidad),
    activo                  BOOLEAN NOT NULL DEFAULT TRUE
);

INSERT INTO rida.cat_tipo_rehabilitacion (codigo, nombre, descripcion, id_modalidad, activo) VALUES
    ('DEFENSIVOS', 'Rehabilitación de defensivos', 'Defensas ribereñas y control de erosión', 3, TRUE),
    ('SECTOR_PECUARIO', 'Rehabilitación sector pecuario', 'Infraestructura ganadera y acuícola', 3, TRUE),
    ('SISTEMAS_AGUA', 'Rehabilitación de sistemas de agua', 'Sistemas de agua potable y riego', 3, TRUE),
    ('VIAS_TALUDES', 'Rehabilitación de vías, taludes y encauses', 'Vías de acceso, taludes y encausamiento de ríos', 3, TRUE),
    ('CUBIERTAS', 'Rehabilitación de cubiertas', 'Techos y cubiertas de infraestructura', 3, TRUE)
ON CONFLICT (codigo) DO UPDATE SET nombre = EXCLUDED.nombre, descripcion = EXCLUDED.descripcion, activo = TRUE;

-- ============================================================================
-- 4) TABLA cat_insumo_rehabilitacion (25 insumos/servicios)
-- ============================================================================
CREATE TABLE IF NOT EXISTS rida.cat_insumo_rehabilitacion (
    id_insumo             SERIAL PRIMARY KEY,
    id_tipo_rehabilitacion INTEGER NOT NULL REFERENCES rida.cat_tipo_rehabilitacion(id_tipo_rehabilitacion),
    codigo                VARCHAR(30) UNIQUE,
    nombre                VARCHAR(150) NOT NULL,
    unidad_de_medida      VARCHAR(20) DEFAULT 'unidad',
    costo_referencia_bs   NUMERIC(12,2),
    activo                BOOLEAN NOT NULL DEFAULT TRUE
);

INSERT INTO rida.cat_insumo_rehabilitacion (id_tipo_rehabilitacion, codigo, nombre, unidad_de_medida, activo) VALUES
    -- DEFENSIVOS (2)
    ((SELECT id_tipo_rehabilitacion FROM rida.cat_tipo_rehabilitacion WHERE codigo='DEFENSIVOS'), 'DEF-001', 'Colchonetas de gavión', 'unidad', TRUE),
    ((SELECT id_tipo_rehabilitacion FROM rida.cat_tipo_rehabilitacion WHERE codigo='DEFENSIVOS'), 'DEF-002', 'Mallas de gavión', 'm2', TRUE),
    
    -- SECTOR PECUARIO (5)
    ((SELECT id_tipo_rehabilitacion FROM rida.cat_tipo_rehabilitacion WHERE codigo='SECTOR_PECUARIO'), 'PEC-001', 'Reconstituyente para animales', 'kg', TRUE),
    ((SELECT id_tipo_rehabilitacion FROM rida.cat_tipo_rehabilitacion WHERE codigo='SECTOR_PECUARIO'), 'PEC-002', 'Alimento balanceado', 'kg', TRUE),
    ((SELECT id_tipo_rehabilitacion FROM rida.cat_tipo_rehabilitacion WHERE codigo='SECTOR_PECUARIO'), 'PEC-003', 'Forraje de avena', 'kg', TRUE),
    ((SELECT id_tipo_rehabilitacion FROM rida.cat_tipo_rehabilitacion WHERE codigo='SECTOR_PECUARIO'), 'PEC-004', 'Forraje de cebada', 'kg', TRUE),
    ((SELECT id_tipo_rehabilitacion FROM rida.cat_tipo_rehabilitacion WHERE codigo='SECTOR_PECUARIO'), 'PEC-005', 'Forraje de alfalfa', 'kg', TRUE),
    
    -- SISTEMAS DE AGUA (13)
    ((SELECT id_tipo_rehabilitacion FROM rida.cat_tipo_rehabilitacion WHERE codigo='SISTEMAS_AGUA'), 'AGU-001', 'Bebederos de 300 LT', 'unidad', TRUE),
    ((SELECT id_tipo_rehabilitacion FROM rida.cat_tipo_rehabilitacion WHERE codigo='SISTEMAS_AGUA'), 'AGU-002', 'Politubo de 3"', 'metro_lineal', TRUE),
    ((SELECT id_tipo_rehabilitacion FROM rida.cat_tipo_rehabilitacion WHERE codigo='SISTEMAS_AGUA'), 'AGU-003', 'Politubo de 2"', 'metro_lineal', TRUE),
    ((SELECT id_tipo_rehabilitacion FROM rida.cat_tipo_rehabilitacion WHERE codigo='SISTEMAS_AGUA'), 'AGU-004', 'Politubo de 1.5"', 'metro_lineal', TRUE),
    ((SELECT id_tipo_rehabilitacion FROM rida.cat_tipo_rehabilitacion WHERE codigo='SISTEMAS_AGUA'), 'AGU-005', 'Tanque de almacenamiento de agua 1000LT', 'unidad', TRUE),
    ((SELECT id_tipo_rehabilitacion FROM rida.cat_tipo_rehabilitacion WHERE codigo='SISTEMAS_AGUA'), 'AGU-006', 'Tanque de almacenamiento de agua 2500LT', 'unidad', TRUE),
    ((SELECT id_tipo_rehabilitacion FROM rida.cat_tipo_rehabilitacion WHERE codigo='SISTEMAS_AGUA'), 'AGU-007', 'Tanque de almacenamiento de agua 3500LT', 'unidad', TRUE),
    ((SELECT id_tipo_rehabilitacion FROM rida.cat_tipo_rehabilitacion WHERE codigo='SISTEMAS_AGUA'), 'AGU-008', 'Tanque de almacenamiento de agua 5000LT', 'unidad', TRUE),
    ((SELECT id_tipo_rehabilitacion FROM rida.cat_tipo_rehabilitacion WHERE codigo='SISTEMAS_AGUA'), 'AGU-009', 'Tanque de almacenamiento de agua 10000LT', 'unidad', TRUE),
    ((SELECT id_tipo_rehabilitacion FROM rida.cat_tipo_rehabilitacion WHERE codigo='SISTEMAS_AGUA'), 'AGU-010', 'Tanque de almacenamiento de agua 20000LT', 'unidad', TRUE),
    ((SELECT id_tipo_rehabilitacion FROM rida.cat_tipo_rehabilitacion WHERE codigo='SISTEMAS_AGUA'), 'AGU-011', 'Tanque de almacenamiento de agua 25000LT', 'unidad', TRUE),
    
    -- VIAS/TALUDES (5) - SERVICIOS DE ALQUILER
    ((SELECT id_tipo_rehabilitacion FROM rida.cat_tipo_rehabilitacion WHERE codigo='VIAS_TALUDES'), 'VIA-001', 'Alquiler de volqueta', 'dia', TRUE),
    ((SELECT id_tipo_rehabilitacion FROM rida.cat_tipo_rehabilitacion WHERE codigo='VIAS_TALUDES'), 'VIA-002', 'Alquiler de motoniveladora', 'dia', TRUE),
    ((SELECT id_tipo_rehabilitacion FROM rida.cat_tipo_rehabilitacion WHERE codigo='VIAS_TALUDES'), 'VIA-003', 'Alquiler de pala frontal', 'dia', TRUE),
    ((SELECT id_tipo_rehabilitacion FROM rida.cat_tipo_rehabilitacion WHERE codigo='VIAS_TALUDES'), 'VIA-004', 'Alquiler de retroexcavadora', 'dia', TRUE),
    ((SELECT id_tipo_rehabilitacion FROM rida.cat_tipo_rehabilitacion WHERE codigo='VIAS_TALUDES'), 'VIA-005', 'Alquiler de excavadora', 'dia', TRUE),
    
    -- CUBIERTAS (1)
    ((SELECT id_tipo_rehabilitacion FROM rida.cat_tipo_rehabilitacion WHERE codigo='CUBIERTAS'), 'CUB-001', 'Calaminas', 'unidad', TRUE)
ON CONFLICT (codigo) DO UPDATE SET nombre = EXCLUDED.nombre, unidad_de_medida = EXCLUDED.unidad_de_medida, activo = TRUE;

-- ============================================================================
-- 5) ARTÍCULOS DE AYUDA HUMANITARIA (22 artículos)
-- Actualizar el artículo test existente y agregar nuevos
-- ============================================================================

-- Actualizar el artículo test existente a la categoría ALIMENTOS
UPDATE rida.cat_articulo 
SET nombre = 'Kit de ración seca', 
    unidad_de_medida = 'kit',
    id_categoria_ayuda = (SELECT id_categoria_ayuda FROM rida.cat_categoria_ayuda WHERE codigo = 'ALIMENTOS')
WHERE codigo = 'TEST001';

INSERT INTO rida.cat_articulo (id_categoria_ayuda, codigo, nombre, unidad_de_medida, activo) VALUES
    -- ALIMENTOS (4 adicionales)
    ((SELECT id_categoria_ayuda FROM rida.cat_categoria_ayuda WHERE codigo = 'ALIMENTOS'), 'ALM-002', 'Fideo', 'bolsa', TRUE),
    ((SELECT id_categoria_ayuda FROM rida.cat_categoria_ayuda WHERE codigo = 'ALIMENTOS'), 'ALM-003', 'Harina', 'bolsa', TRUE),
    ((SELECT id_categoria_ayuda FROM rida.cat_categoria_ayuda WHERE codigo = 'ALIMENTOS'), 'ALM-004', 'Arroz', 'bolsa', TRUE),
    ((SELECT id_categoria_ayuda FROM rida.cat_categoria_ayuda WHERE codigo = 'ALIMENTOS'), 'ALM-005', 'Azúcar', 'bolsa', TRUE),
    
    -- HERRAMIENTAS MENORES (6)
    ((SELECT id_categoria_ayuda FROM rida.cat_categoria_ayuda WHERE codigo = 'HERRAMIENTAS_MENORES'), 'HER-001', 'Carretilla', 'unidad', TRUE),
    ((SELECT id_categoria_ayuda FROM rida.cat_categoria_ayuda WHERE codigo = 'HERRAMIENTAS_MENORES'), 'HER-002', 'Machete', 'unidad', TRUE),
    ((SELECT id_categoria_ayuda FROM rida.cat_categoria_ayuda WHERE codigo = 'HERRAMIENTAS_MENORES'), 'HER-003', 'Azadón con mango', 'unidad', TRUE),
    ((SELECT id_categoria_ayuda FROM rida.cat_categoria_ayuda WHERE codigo = 'HERRAMIENTAS_MENORES'), 'HER-004', 'Hacha con mango', 'unidad', TRUE),
    ((SELECT id_categoria_ayuda FROM rida.cat_categoria_ayuda WHERE codigo = 'HERRAMIENTAS_MENORES'), 'HER-005', 'Picota con mango', 'unidad', TRUE),
    ((SELECT id_categoria_ayuda FROM rida.cat_categoria_ayuda WHERE codigo = 'HERRAMIENTAS_MENORES'), 'HER-006', 'Pala con mango', 'unidad', TRUE),
    
    -- REF/VIVIENDA (1)
    ((SELECT id_categoria_ayuda FROM rida.cat_categoria_ayuda WHERE codigo = 'REF_VIVIENDA'), 'REF-001', 'Carpas', 'unidad', TRUE),
    
    -- ROPA DE CAMA (3)
    ((SELECT id_categoria_ayuda FROM rida.cat_categoria_ayuda WHERE codigo = 'ROPA_CAMA'), 'CAM-001', 'Mosquiteros', 'unidad', TRUE),
    ((SELECT id_categoria_ayuda FROM rida.cat_categoria_ayuda WHERE codigo = 'ROPA_CAMA'), 'CAM-002', 'Colchonetas', 'unidad', TRUE),
    ((SELECT id_categoria_ayuda FROM rida.cat_categoria_ayuda WHERE codigo = 'ROPA_CAMA'), 'CAM-003', 'Frazada', 'unidad', TRUE),
    
    -- ROPA DE AGUA (2)
    ((SELECT id_categoria_ayuda FROM rida.cat_categoria_ayuda WHERE codigo = 'ROPA_AGUA'), 'AGU-001', 'Botas de goma', 'par', TRUE),
    ((SELECT id_categoria_ayuda FROM rida.cat_categoria_ayuda WHERE codigo = 'ROPA_AGUA'), 'AGU-002', 'Ponchos de agua', 'unidad', TRUE),
    
    -- ARTICULOS DE HIGIENE (3)
    ((SELECT id_categoria_ayuda FROM rida.cat_categoria_ayuda WHERE codigo = 'ARTICULOS_HIGIENE'), 'HIG-001', 'Pastillas potabilizadoras', 'caja', TRUE),
    ((SELECT id_categoria_ayuda FROM rida.cat_categoria_ayuda WHERE codigo = 'ARTICULOS_HIGIENE'), 'HIG-002', 'Kit de higiene', 'kit', TRUE),
    ((SELECT id_categoria_ayuda FROM rida.cat_categoria_ayuda WHERE codigo = 'ARTICULOS_HIGIENE'), 'HIG-003', 'Kit de limpieza', 'kit', TRUE),
    
    -- ARTICULOS DE COCINA (1)
    ((SELECT id_categoria_ayuda FROM rida.cat_categoria_ayuda WHERE codigo = 'ARTICULOS_COCINA'), 'COC-001', 'Kit de cocina', 'kit', TRUE)
ON CONFLICT (codigo) DO UPDATE SET nombre = EXCLUDED.nombre, unidad_de_medida = EXCLUDED.unidad_de_medida, activo = TRUE;

COMMIT;

SELECT 'IDEMPOTENT OK v2.35.0 separar_rehabilitacion' AS resultado;
