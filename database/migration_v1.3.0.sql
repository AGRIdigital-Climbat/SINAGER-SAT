-- ============================================
-- MIGRACIÓN v1.3.0
-- ============================================
-- Edición de perfil con geografía.
-- 1. FKs compuestas en usuarios.usuario para garantizar coherencia
--    departamento → provincia → municipio.
-- 2. Idempotente: se puede ejecutar varias veces sin error.
-- ============================================

BEGIN;

-- ── 1. UNIQUE necesarios para poder referenciar FKs compuestas ──
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_provincia_departamento_id') THEN
        ALTER TABLE shared.provincia ADD CONSTRAINT uq_provincia_departamento_id UNIQUE (id_departamento, id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_municipio_provincia_id') THEN
        ALTER TABLE shared.municipio ADD CONSTRAINT uq_municipio_provincia_id UNIQUE (id_provincia, id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_municipio_departamento_id') THEN
        ALTER TABLE shared.municipio ADD CONSTRAINT uq_municipio_departamento_id UNIQUE (id_departamento, id);
    END IF;
END $$;

-- ── 2. FK simples de geografía en usuarios.usuario ──
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'usuario_id_departamento_fkey') THEN
        ALTER TABLE usuarios.usuario ADD CONSTRAINT usuario_id_departamento_fkey
            FOREIGN KEY (id_departamento) REFERENCES shared.departamento(id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'usuario_id_provincia_fkey') THEN
        ALTER TABLE usuarios.usuario ADD CONSTRAINT usuario_id_provincia_fkey
            FOREIGN KEY (id_provincia) REFERENCES shared.provincia(id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'usuario_id_municipio_fkey') THEN
        ALTER TABLE usuarios.usuario ADD CONSTRAINT usuario_id_municipio_fkey
            FOREIGN KEY (id_municipio) REFERENCES shared.municipio(id);
    END IF;
END $$;

-- ── 3. FK compuestas: la provincia debe pertenecer al departamento,
--        y el municipio a la provincia y al departamento ──
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'usuario_departamento_provincia_fkey') THEN
        ALTER TABLE usuarios.usuario ADD CONSTRAINT usuario_departamento_provincia_fkey
            FOREIGN KEY (id_departamento, id_provincia) REFERENCES shared.provincia(id_departamento, id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'usuario_provincia_municipio_fkey') THEN
        ALTER TABLE usuarios.usuario ADD CONSTRAINT usuario_provincia_municipio_fkey
            FOREIGN KEY (id_provincia, id_municipio) REFERENCES shared.municipio(id_provincia, id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'usuario_departamento_municipio_fkey') THEN
        ALTER TABLE usuarios.usuario ADD CONSTRAINT usuario_departamento_municipio_fkey
            FOREIGN KEY (id_departamento, id_municipio) REFERENCES shared.municipio(id_departamento, id);
    END IF;
END $$;

COMMIT;
