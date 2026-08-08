-- ============================================
-- MIGRACIÓN v1.3.1
-- ============================================
-- Catálogo de cultivos agrícolas del SIIP
-- (https://siip.produccion.gob.bo/repSIIP2/formulario_mdryt.php)
-- Tabla shared.cultivo con 3 columnas: id, nombre, grupo.
-- Idempotente: se puede ejecutar varias veces sin error.
-- ============================================

BEGIN;

-- ── 1. Tabla de cultivos ──
CREATE TABLE IF NOT EXISTS shared.cultivo (
    id     INTEGER PRIMARY KEY,
    nombre TEXT NOT NULL,
    grupo  TEXT NOT NULL,
    CONSTRAINT chk_cultivo_grupo CHECK (grupo IN (
        'Cereales', 'Estimulantes', 'Frutales', 'Hortalizas',
        'Industriales', 'Tuberculos', 'Forrajes'
    ))
);

-- ── 2. Datos (códigos globales 1-73 del SIIP) ──
INSERT INTO shared.cultivo (id, nombre, grupo) VALUES
    -- Cereales
    (1,  'Arroz con cáscara', 'Cereales'),
    (2,  'Avena', 'Cereales'),
    (3,  'Cañahua', 'Cereales'),
    (4,  'Cebada en grano', 'Cereales'),
    (5,  'Centeno', 'Cereales'),
    (6,  'Maiz en grano', 'Cereales'),
    (7,  'Quínua', 'Cereales'),
    (8,  'Sorgo en grano', 'Cereales'),
    (9,  'Trigo', 'Cereales'),
    -- Estimulantes
    (10, 'Cacao', 'Estimulantes'),
    (11, 'Café', 'Estimulantes'),
    (12, 'Té', 'Estimulantes'),
    -- Frutales
    (13, 'Banano', 'Frutales'),
    (14, 'Ciruelo', 'Frutales'),
    (15, 'Chirimoya', 'Frutales'),
    (16, 'Durazno', 'Frutales'),
    (17, 'Frutilla', 'Frutales'),
    (18, 'Guinda', 'Frutales'),
    (19, 'Higo', 'Frutales'),
    (20, 'Lima', 'Frutales'),
    (21, 'Limón', 'Frutales'),
    (22, 'Mandarina', 'Frutales'),
    (23, 'Manga', 'Frutales'),
    (24, 'Manzana', 'Frutales'),
    (25, 'Membrillo', 'Frutales'),
    (26, 'Naranja', 'Frutales'),
    (27, 'Palta', 'Frutales'),
    (28, 'Papaya', 'Frutales'),
    (29, 'Pera', 'Frutales'),
    (30, 'Piña', 'Frutales'),
    (31, 'Plátano(Postre)', 'Frutales'),
    (32, 'Pomelo/toronja', 'Frutales'),
    (33, 'Sandia', 'Frutales'),
    (34, 'Tuna', 'Frutales'),
    (35, 'Uva (Vid)', 'Frutales'),
    -- Hortalizas
    (36, 'Aji', 'Hortalizas'),
    (37, 'Ajo', 'Hortalizas'),
    (38, 'Arveja', 'Hortalizas'),
    (39, 'Betarraga', 'Hortalizas'),
    (40, 'Cebolla', 'Hortalizas'),
    (41, 'Coliflor', 'Hortalizas'),
    (42, 'Frejol/poroto', 'Hortalizas'),
    (43, 'Garbanzo', 'Hortalizas'),
    (44, 'Haba', 'Hortalizas'),
    (45, 'Lechuga', 'Hortalizas'),
    (46, 'Locoto', 'Hortalizas'),
    (47, 'Maíz choclo', 'Hortalizas'),
    (48, 'Pepino', 'Hortalizas'),
    (49, 'Rábano', 'Hortalizas'),
    (50, 'Repollo', 'Hortalizas'),
    (51, 'Tomate', 'Hortalizas'),
    (52, 'Vainitas', 'Hortalizas'),
    (53, 'Zanahoria', 'Hortalizas'),
    (54, 'Zapallo', 'Hortalizas'),
    -- Industriales
    (55, 'Achiote (urucu)', 'Industriales'),
    (56, 'Algodón', 'Industriales'),
    (57, 'Caña de Azúcar', 'Industriales'),
    (58, 'Girasol', 'Industriales'),
    (59, 'Mani', 'Industriales'),
    (60, 'Sésamo', 'Industriales'),
    (61, 'Soya', 'Industriales'),
    (62, 'Tabaco', 'Industriales'),
    (73, 'Chia', 'Industriales'),
    -- Tuberculos
    (63, 'Camote', 'Tuberculos'),
    (64, 'Hualuza', 'Tuberculos'),
    (65, 'Oca', 'Tuberculos'),
    (66, 'Papa', 'Tuberculos'),
    (67, 'Papaliza', 'Tuberculos'),
    (68, 'Racacha', 'Tuberculos'),
    (69, 'Yuca', 'Tuberculos'),
    -- Forrajes
    (70, 'Alfalfa', 'Forrajes'),
    (71, 'Avena berza', 'Forrajes'),
    (72, 'Cebada berza', 'Forrajes')
ON CONFLICT (id) DO NOTHING;

COMMIT;
