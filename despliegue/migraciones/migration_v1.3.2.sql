-- ============================================
-- MIGRACIÓN v1.3.2
-- ============================================
-- Catálogo pecuario (especies animales de producción en Bolivia).
-- Base: especies del módulo pecuario del SIIP
-- (https://siip.produccion.gob.bo/repSIIP2/formulario_pecuario.php)
-- ampliadas con especies de producción típicas, agrupadas por tipo de ganado.
-- Tabla shared.pecuario con 3 columnas: id, nombre, grupo.
-- Idempotente: se puede ejecutar varias veces sin error.
-- ============================================

BEGIN;

-- ── 1. Tabla de especies pecuarias ──
CREATE TABLE IF NOT EXISTS shared.pecuario (
    id     INTEGER PRIMARY KEY,
    nombre TEXT NOT NULL,
    grupo  TEXT NOT NULL,
    CONSTRAINT chk_pecuario_grupo CHECK (grupo IN (
        'Ganado mayor', 'Ganado menor', 'Camélidos',
        'Aves de corral', 'Piscicultura', 'Otros'
    ))
);

-- ── 2. Datos (los ids 41-46 preservan el código del SIIP) ──
INSERT INTO shared.pecuario (id, nombre, grupo) VALUES
    -- Ganado mayor
    (44, 'Bovinos', 'Ganado mayor'),
    (47, 'Búfalos', 'Ganado mayor'),
    (48, 'Equinos', 'Ganado mayor'),
    (49, 'Mulares', 'Ganado mayor'),
    (50, 'Asnos', 'Ganado mayor'),
    -- Ganado menor
    (41, 'Ovinos', 'Ganado menor'),
    (45, 'Caprinos', 'Ganado menor'),
    (46, 'Porcino', 'Ganado menor'),
    (51, 'Cuyes', 'Ganado menor'),
    (52, 'Conejos', 'Ganado menor'),
    -- Camélidos
    (42, 'Alpacas', 'Camélidos'),
    (43, 'Llamas', 'Camélidos'),
    (53, 'Vicuñas', 'Camélidos'),
    (54, 'Guanacos', 'Camélidos'),
    -- Aves de corral
    (55, 'Pollos', 'Aves de corral'),
    (56, 'Gallinas', 'Aves de corral'),
    (57, 'Patos', 'Aves de corral'),
    (58, 'Pavos', 'Aves de corral'),
    (59, 'Gansos', 'Aves de corral'),
    (60, 'Codornices', 'Aves de corral'),
    -- Piscicultura
    (61, 'Trucha', 'Piscicultura'),
    (62, 'Tilapia', 'Piscicultura'),
    (63, 'Pacú', 'Piscicultura'),
    (64, 'Surubí', 'Piscicultura'),
    (65, 'Sábalo', 'Piscicultura'),
    (66, 'Tambaquí', 'Piscicultura'),
    (67, 'Pejerrey', 'Piscicultura'),
    (68, 'Carpa', 'Piscicultura'),
    -- Otros
    (69, 'Abejas (apicultura)', 'Otros')
ON CONFLICT (id) DO NOTHING;

COMMIT;
