-- ============================================================================
-- SINAGERSAT API v2.31.0
-- Unificar categoría de pronósticos
-- ============================================================================

BEGIN;

-- 1. Renombrar tabla
ALTER TABLE sinb.categoria_pronostico_temporal RENAME TO categoria_pronostico;

-- 2. DROPEAR TODAS LAS FKs PRIMERO
ALTER TABLE sinb.escenario DROP CONSTRAINT IF EXISTS escenario_id_campo_pronostico_fkey;
ALTER TABLE sinb.pronostico_largo DROP CONSTRAINT IF EXISTS pronostico_estacional_id_campo_pronostico_fkey;
ALTER TABLE sinb.pronostico_corto DROP CONSTRAINT IF EXISTS pronostico_temporal_id_campo_pronostico_fkey;
ALTER TABLE sinb.avisos DROP CONSTRAINT IF EXISTS aviso_id_campo_pronostico_fkey;
ALTER TABLE sinb.pronostico_digital DROP CONSTRAINT IF EXISTS pronostico_digital_id_campo_pronostico_fkey;

-- 3. Insertar Cosecha, Granizo, terremoto desde campo_pronostico
INSERT INTO sinb.categoria_pronostico (id, nombre, descripcion, estado)
SELECT id, nombre, nombre as descripcion, 'ACTIVO'
FROM sinb.campo_pronostico
WHERE nombre IN ('Cosecha', 'Granizo', 'terremoto')
ON CONFLICT (nombre) DO NOTHING;

-- 4. Actualizar FKs: Helada y Lluvia (campo→categoria)
UPDATE sinb.escenario SET id_campo_pronostico = '01f7aa3d-5736-44b5-8004-d9b56becd265'
WHERE id_campo_pronostico = '5e9cd147-d88e-4efc-b7c7-fa776ffebf4a';
UPDATE sinb.escenario SET id_campo_pronostico = 'f8996cb0-dd0e-4501-bf26-fa9bebb3bcf3'
WHERE id_campo_pronostico = 'c31b0be4-9e1d-4da5-a02f-38a27ea7b4fd';

UPDATE sinb.pronostico_largo SET id_campo_pronostico = '01f7aa3d-5736-44b5-8004-d9b56becd265'
WHERE id_campo_pronostico = '5e9cd147-d88e-4efc-b7c7-fa776ffebf4a';
UPDATE sinb.pronostico_largo SET id_campo_pronostico = 'f8996cb0-dd0e-4501-bf26-fa9bebb3bcf3'
WHERE id_campo_pronostico = 'c31b0be4-9e1d-4da5-a02f-38a27ea7b4fd';

UPDATE sinb.pronostico_corto SET id_campo_pronostico = '01f7aa3d-5736-44b5-8004-d9b56becd265'
WHERE id_campo_pronostico = '5e9cd147-d88e-4efc-b7c7-fa776ffebf4a';
UPDATE sinb.pronostico_corto SET id_campo_pronostico = 'f8996cb0-dd0e-4501-bf26-fa9bebb3bcf3'
WHERE id_campo_pronostico = 'c31b0be4-9e1d-4da5-a02f-38a27ea7b4fd';

UPDATE sinb.avisos SET id_campo_pronostico = '01f7aa3d-5736-44b5-8004-d9b56becd265'
WHERE id_campo_pronostico = '5e9cd147-d88e-4efc-b7c7-fa776ffebf4a';
UPDATE sinb.avisos SET id_campo_pronostico = 'f8996cb0-dd0e-4501-bf26-fa9bebb3bcf3'
WHERE id_campo_pronostico = 'c31b0be4-9e1d-4da5-a02f-38a27ea7b4fd';

UPDATE sinb.pronostico_digital SET id_campo_pronostico = '01f7aa3d-5736-44b5-8004-d9b56becd265'
WHERE id_campo_pronostico = '5e9cd147-d88e-4efc-b7c7-fa776ffebf4a';
UPDATE sinb.pronostico_digital SET id_campo_pronostico = 'f8996cb0-dd0e-4501-bf26-fa9bebb3bcf3'
WHERE id_campo_pronostico = 'c31b0be4-9e1d-4da5-a02f-38a27ea7b4fd';

-- 5. Unificar Granizo → Granizada
DO $$
DECLARE
    id_granizo uuid;
    id_granizada uuid;
BEGIN
    SELECT id INTO id_granizo FROM sinb.categoria_pronostico WHERE nombre = 'Granizo';
    SELECT id INTO id_granizada FROM sinb.categoria_pronostico WHERE nombre = 'Granizada';
    
    IF id_granizo IS NOT NULL AND id_granizada IS NOT NULL THEN
        UPDATE sinb.escenario SET id_campo_pronostico = id_granizada WHERE id_campo_pronostico = id_granizo;
        DELETE FROM sinb.categoria_pronostico WHERE id = id_granizo;
    END IF;
END $$;

-- 6. Borrar "prueba"
DELETE FROM sinb.categoria_pronostico WHERE nombre = 'prueba';

-- 7. RENOMBRAR columnas (excepto pronostico_corto que ya tiene id_categoria)
ALTER TABLE sinb.escenario RENAME COLUMN id_campo_pronostico TO id_categoria;
ALTER TABLE sinb.pronostico_largo RENAME COLUMN id_campo_pronostico TO id_categoria;
ALTER TABLE sinb.avisos RENAME COLUMN id_campo_pronostico TO id_categoria;
ALTER TABLE sinb.pronostico_digital RENAME COLUMN id_campo_pronostico TO id_categoria;

-- 8. pronostico_corto: SOLO dropear id_campo_pronostico (ya tiene id_categoria)
ALTER TABLE sinb.pronostico_corto DROP COLUMN IF EXISTS id_campo_pronostico;

-- 9. Crear FKs nuevas
ALTER TABLE sinb.escenario ADD CONSTRAINT escenario_id_categoria_fkey 
    FOREIGN KEY (id_categoria) REFERENCES sinb.categoria_pronostico(id) ON DELETE RESTRICT;
ALTER TABLE sinb.pronostico_largo ADD CONSTRAINT pronostico_largo_id_categoria_fkey 
    FOREIGN KEY (id_categoria) REFERENCES sinb.categoria_pronostico(id) ON DELETE RESTRICT;
ALTER TABLE sinb.pronostico_corto ADD CONSTRAINT pronostico_corto_id_categoria_fkey 
    FOREIGN KEY (id_categoria) REFERENCES sinb.categoria_pronostico(id) ON DELETE RESTRICT;
ALTER TABLE sinb.avisos ADD CONSTRAINT avisos_id_categoria_fkey 
    FOREIGN KEY (id_categoria) REFERENCES sinb.categoria_pronostico(id) ON DELETE RESTRICT;
ALTER TABLE sinb.pronostico_digital ADD CONSTRAINT pronostico_digital_id_categoria_fkey 
    FOREIGN KEY (id_categoria) REFERENCES sinb.categoria_pronostico(id) ON DELETE RESTRICT;

-- 10. Eliminar campo_pronostico
DROP TABLE IF EXISTS sinb.campo_pronostico;

COMMIT;
