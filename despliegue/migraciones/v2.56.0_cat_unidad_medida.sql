-- ============================================================================
--  v2.56.0 - CATALOGO DE UNIDADES DE MEDIDA (Ayuda Humanitaria)
--
--  Que agrega:
--    1. rida.cat_unidad_medida ........ catalogo de unidades (kit, caja, kg,
--                                        litro, unidad) cargable por API.
--    2. rida.cat_articulo (ALTER) ..... vinculado a cat_unidad_medida por FK
--                                        sobre unidad_de_medida (codigo);
--                                        normaliza bolsa/par -> unidad.
--                                        El motor sigue leyendo
--                                        a.unidad_de_medida SIN cambios.
--
--  Idempotente: se puede aplicar mas de una vez.
-- ============================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS rida.cat_unidad_medida (
    id_unidad_medida serial PRIMARY KEY,
    codigo           varchar(20) NOT NULL UNIQUE,
    nombre           varchar(50) NOT NULL,
    activo           boolean     NOT NULL DEFAULT TRUE
);

INSERT INTO rida.cat_unidad_medida (codigo, nombre) VALUES
    ('kit',    'Kit'),
    ('caja',   'Caja'),
    ('kg',     'Kilogramo'),
    ('litro',  'Litro'),
    ('unidad', 'Unidad')
ON CONFLICT (codigo) DO NOTHING;

-- Normaliza unidades que no estan en el catalogo (bolsa/par) -> unidad
UPDATE rida.cat_articulo
   SET unidad_de_medida = 'unidad'
 WHERE unidad_de_medida IS NULL
    OR unidad_de_medida NOT IN (SELECT codigo FROM rida.cat_unidad_medida);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'fk_articulo_unidad_medida'
          AND conrelid = 'rida.cat_articulo'::regclass
    ) THEN
        ALTER TABLE rida.cat_articulo
            ADD CONSTRAINT fk_articulo_unidad_medida
            FOREIGN KEY (unidad_de_medida)
            REFERENCES rida.cat_unidad_medida(codigo)
            ON UPDATE CASCADE;
    END IF;
    RAISE NOTICE 'IDEMPOTENT OK v2.56.0 cat_unidad_medida';
END $$;

COMMIT;