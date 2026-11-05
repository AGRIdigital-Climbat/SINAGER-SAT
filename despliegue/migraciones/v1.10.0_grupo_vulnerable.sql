-- Migración v1.10.0: Catálogo de grupos vulnerables
-- Reemplaza CHECK constraint por FK a tabla catálogo
-- Permite configuración dinámica sin cambiar schema

-- 1. Crear tabla catálogo (si no existe)
CREATE TABLE IF NOT EXISTS edan.grupo_vulnerable (
    id_grupo_vulnerable   SERIAL PRIMARY KEY,
    codigo                VARCHAR(50) UNIQUE NOT NULL,
    nombre                VARCHAR(100) NOT NULL,
    descripcion           TEXT,
    orden                 INTEGER NOT NULL DEFAULT 0,
    activo                BOOLEAN NOT NULL DEFAULT TRUE
);

-- 2. Insertar 8 grupos vulnerables (valores exactos solicitados por usuario)
INSERT INTO edan.grupo_vulnerable (codigo, nombre, descripcion, orden, activo) VALUES
  ('ninas_ninos_0_5', 'Niñas y niños 0-5 años', 'Primera infancia', 1, TRUE),
  ('ninas_ninos_5_10', 'Niñas y niños 5-10 años', 'Niñez temprana', 2, TRUE),
  ('adolescentes', 'Adolescentes', '10-19 años según OMS', 3, TRUE),
  ('mujeres_lactantes', 'Mujeres lactantes', 'Periodo de lactancia', 4, TRUE),
  ('mujeres_embarazadas', 'Mujeres embarazadas', 'Gestación', 5, TRUE),
  ('adultos_mayores', 'Adultos mayores', '60+ años', 6, TRUE),
  ('personas_discapacidad', 'Personas con discapacidad', 'Discapacidad física, mental, intelectual o sensorial', 7, TRUE),
  ('personas_enfermedad_cronica', 'Personas con enfermedad crónica', 'Enfermedades de larga duración', 8, TRUE)
ON CONFLICT (codigo) DO NOTHING;

-- 3. Modificar edan_localidades_proteccion
-- 3a. Agregar columna FK nueva (nullable temporalmente)
ALTER TABLE edan.edan_localidades_proteccion
  ADD COLUMN IF NOT EXISTS id_grupo_vulnerable_catalogo INTEGER;

-- 3b. Mapear datos existentes (si los hubiera) - mapeo de strings antiguos a nuevo catálogo
UPDATE edan.edan_localidades_proteccion p
SET id_grupo_vulnerable_catalogo = g.id_grupo_vulnerable
FROM edan.grupo_vulnerable g
WHERE 
  (g.codigo = 'ninas_ninos_0_5' AND p.grupo IN ('ninos', 'ninas_ninos_0_5', 'niñas_ninos_0_5')) OR
  (g.codigo = 'adolescentes' AND p.grupo = 'adolescentes') OR
  (g.codigo = 'mujeres_lactantes' AND p.grupo = 'mujeres_lactantes') OR
  (g.codigo = 'mujeres_embarazadas' AND p.grupo = 'mujeres_embarazadas') OR
  (g.codigo = 'adultos_mayores' AND p.grupo = 'adultos_mayores') OR
  (g.codigo = 'personas_discapacidad' AND p.grupo = 'personas_discapacidad') OR
  (g.codigo = 'personas_enfermedad_cronica' AND p.grupo IN ('personas_enfermedad', 'personas_enfermedad_cronica'));

-- 3c. Hacer NOT NULL
ALTER TABLE edan.edan_localidades_proteccion
  ALTER COLUMN id_grupo_vulnerable_catalogo SET NOT NULL;

-- 3d. Agregar FK (solo si no existe)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints 
    WHERE constraint_name = 'edan_localidades_proteccion_id_grupo_vulnerable_catalogo_fkey'
    AND table_schema = 'edan'
  ) THEN
    ALTER TABLE edan.edan_localidades_proteccion
      ADD CONSTRAINT edan_localidades_proteccion_id_grupo_vulnerable_catalogo_fkey
        FOREIGN KEY (id_grupo_vulnerable_catalogo)
        REFERENCES edan.grupo_vulnerable(id_grupo_vulnerable)
        ON DELETE RESTRICT;
  END IF;
END $$;

-- 3e. Eliminar CHECK constraint viejo (ya no necesario)
ALTER TABLE edan.edan_localidades_proteccion
  DROP CONSTRAINT IF EXISTS edan_localidades_proteccion_grupo_check;

-- 3f. Cambiar UNIQUE constraint para usar FK en vez de string
ALTER TABLE edan.edan_localidades_proteccion
  DROP CONSTRAINT IF EXISTS edan_localidades_proteccion_id_edan_localidad_grupo_key;

-- Agregar UNIQUE constraint (solo si no existe)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes 
    WHERE tablename = 'edan_localidades_proteccion' 
    AND indexname = 'edan_localidades_proteccion_id_edan_localidad_grupo_unique'
  ) THEN
    ALTER TABLE edan.edan_localidades_proteccion
      ADD CONSTRAINT edan_localidades_proteccion_id_edan_localidad_grupo_unique
        UNIQUE (id_edan_localidad, id_grupo_vulnerable_catalogo);
  END IF;
END $$;

-- 4. Índices para performance
CREATE INDEX IF NOT EXISTS idx_edan_proteccion_grupo_fk ON edan.edan_localidades_proteccion(id_grupo_vulnerable_catalogo);
CREATE INDEX IF NOT EXISTS idx_grupo_vulnerable_activo ON edan.grupo_vulnerable(activo, orden);

-- 5. Comentarios de documentación
COMMENT ON TABLE edan.grupo_vulnerable IS 'Catálogo de grupos vulnerables para protección civil';
COMMENT ON COLUMN edan.grupo_vulnerable.codigo IS 'Código único: ninas_ninos_0_5, adolescentes, etc.';
COMMENT ON COLUMN edan.grupo_vulnerable.nombre IS 'Nombre legible para UI';
COMMENT ON COLUMN edan.grupo_vulnerable.descripcion IS 'Descripción detallada del grupo';
COMMENT ON COLUMN edan.grupo_vulnerable.orden IS 'Orden de presentación en formularios';
COMMENT ON COLUMN edan.grupo_vulnerable.activo IS 'Si FALSE, no se muestra en UI pero se mantiene histórico';
COMMENT ON COLUMN edan.edan_localidades_proteccion.id_grupo_vulnerable_catalogo IS 'FK a edan.grupo_vulnerable (reemplaza columna grupo VARCHAR)';
