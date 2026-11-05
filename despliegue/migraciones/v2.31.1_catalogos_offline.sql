-- ============================================================================
-- SINAGERSAT API v2.31.1
-- Agregar campos offline a catálogos SINB
-- ============================================================================

BEGIN;

-- 1. grupo
ALTER TABLE sinb.grupo ADD COLUMN IF NOT EXISTS id_grupo_off varchar(36);
CREATE INDEX IF NOT EXISTS idx_grupo_off ON sinb.grupo(id_grupo_off);

-- 2. indicador_natural
ALTER TABLE sinb.indicador_natural ADD COLUMN IF NOT EXISTS id_indicador_off varchar(36);
CREATE INDEX IF NOT EXISTS idx_indicador_off ON sinb.indicador_natural(id_indicador_off);

-- 3. caracteristica
ALTER TABLE sinb.caracteristica ADD COLUMN IF NOT EXISTS id_caracteristica_off varchar(36);
CREATE INDEX IF NOT EXISTS idx_caracteristica_off ON sinb.caracteristica(id_caracteristica_off);

-- 4. comportamiento
ALTER TABLE sinb.comportamiento ADD COLUMN IF NOT EXISTS id_comportamiento_off varchar(36);
CREATE INDEX IF NOT EXISTS idx_comportamiento_off ON sinb.comportamiento(id_comportamiento_off);

-- 5. significado
ALTER TABLE sinb.significado ADD COLUMN IF NOT EXISTS id_significado_off varchar(36);
CREATE INDEX IF NOT EXISTS idx_significado_off ON sinb.significado(id_significado_off);

-- 6. zona_geografica
ALTER TABLE sinb.zona_geografica ADD COLUMN IF NOT EXISTS id_zona_off varchar(36);
CREATE INDEX IF NOT EXISTS idx_zona_off ON sinb.zona_geografica(id_zona_off);

-- 7. categoria_pronostico (unificado)
ALTER TABLE sinb.categoria_pronostico ADD COLUMN IF NOT EXISTS id_categoria_off varchar(36);
CREATE INDEX IF NOT EXISTS idx_categoria_off ON sinb.categoria_pronostico(id_categoria_off);

-- 8. escenario (hijo de categoria_pronostico)
ALTER TABLE sinb.escenario ADD COLUMN IF NOT EXISTS id_escenario_off varchar(36);
CREATE INDEX IF NOT EXISTS idx_escenario_off ON sinb.escenario(id_escenario_off);

COMMIT;
