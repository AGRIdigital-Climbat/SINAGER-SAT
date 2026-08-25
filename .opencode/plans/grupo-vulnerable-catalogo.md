# Plan: Crear catálogo `edan.grupo_vulnerable`

## Contexto actual

La tabla `edan.edan_localidades_proteccion` tiene:
- `grupo` VARCHAR(50) con CHECK constraint con 7 valores fijos
- `id_grupo_vulnerable` SERIAL (PK técnica, sin significado)
- No hay tabla catálogo

## Nueva estructura propuesta

### 1. Tabla catálogo `edan.grupo_vulnerable`

```sql
CREATE TABLE edan.grupo_vulnerable (
    id_grupo_vulnerable   SERIAL PRIMARY KEY,
    codigo                VARCHAR(50) UNIQUE NOT NULL,  -- 'ninos_0_5', 'adolescentes', etc.
    nombre                VARCHAR(100) NOT NULL,        -- 'Niñas y niños 0-5 años', etc.
    descripcion           TEXT,
    orden                 INTEGER NOT NULL DEFAULT 0,   -- para ordenamiento en UI
    activo                BOOLEAN NOT NULL DEFAULT TRUE -- para desactivar sin borrar
);
```

**Datos iniciales:**

| id | codigo | nombre | orden |
|----|--------|--------|-------|
| 1 | `ninos_0_5` | Niñas y niños 0-5 años | 1 |
| 2 | `ninos_5_10` | Niñas y niños 5-10 años | 2 |
| 3 | `adolescentes` | Adolescentes | 3 |
| 4 | `mujeres_lactantes` | Mujeres lactantes | 4 |
| 5 | `mujeres_embarazadas` | Mujeres embarazadas | 5 |
| 6 | `adultos_mayores` | Adultos mayores | 6 |
| 7 | `personas_discapacidad` | Personas con discapacidad | 7 |
| 8 | `personas_enfermedad_cronica` | Personas con enfermedad crónica | 8 |

> **Nota:** Se separa `ninos_0_5` y `ninos_5_10` (antes era solo `ninos`). Total: 8 grupos.

### 2. Modificar `edan.edan_localidades_proteccion`

**Schema actual:**
```sql
CREATE TABLE edan.edan_localidades_proteccion (
    id_edan_localidad     BIGINT NOT NULL,
    id_grupo_vulnerable   INTEGER NOT NULL,  -- SERIAL (PK técnica)
    grupo                 VARCHAR(50) NOT NULL,  -- CHECK constraint
    ...
    FOREIGN KEY (id_edan_localidad) REFERENCES edan.edan_localidades,
    UNIQUE (id_edan_localidad, grupo)
);
```

**Schema propuesto:**
```sql
CREATE TABLE edan.edan_localidades_proteccion (
    id_edan_localidad     BIGINT NOT NULL,
    id_grupo_vulnerable   INTEGER NOT NULL,  -- FK → edan.grupo_vulnerable
    -- grupo VARCHAR(50) -- ELIMINAR (ya no necesario, está en el catálogo)
    mujeres               INTEGER NOT NULL DEFAULT 0,
    hombres               INTEGER NOT NULL DEFAULT 0,
    total                 INTEGER NOT NULL DEFAULT 0,
    apoyo_psicologico     BOOLEAN,
    reposicion_documentos BOOLEAN,
    observaciones         TEXT NOT NULL DEFAULT '',
    FOREIGN KEY (id_edan_localidad) REFERENCES edan.edan_localidades(id_edan_localidad) ON DELETE CASCADE,
    FOREIGN KEY (id_grupo_vulnerable) REFERENCES edan.grupo_vulnerable(id_grupo_vulnerable) ON DELETE RESTRICT,
    UNIQUE (id_edan_localidad, id_grupo_vulnerable)  -- UNIQUE por localidad + grupo
);
```

**Cambios:**
1. `id_grupo_vulnerable` deja de ser SERIAL → es FK a `edan.grupo_vulnerable`
2. Se elimina la columna `grupo` (el nombre está en el catálogo)
3. UNIQUE constraint cambia de `(id_edan_localidad, grupo)` a `(id_edan_localidad, id_grupo_vulnerable)`

### 3. Migración de datos existentes

```sql
-- 1. Crear tabla catálogo con IDs que coincidan con los valores actuales
CREATE TABLE edan.grupo_vulnerable (...);
INSERT INTO edan.grupo_vulnerable (codigo, nombre, orden) VALUES
  ('ninos', 'Niñas y niños 0-5 años', 1),  -- id=1
  ('adolescentes', 'Adolescentes', 2),      -- id=2
  ...;

-- 2. Actualizar FK en edan_localidades_proteccion
-- Mapear grupo (string) → id_grupo_vulnerable (FK)
ALTER TABLE edan.edan_localidades_proteccion
  ADD COLUMN id_grupo_vulnerable_new INTEGER;

UPDATE edan.edan_localidades_proteccion p
SET id_grupo_vulnerable_new = g.id_grupo_vulnerable
FROM edan.grupo_vulnerable g
WHERE g.codigo = p.grupo;

-- 3. Eliminar columna grupo y renombrar FK
ALTER TABLE edan.edan_localidades_proteccion
  DROP COLUMN grupo,
  DROP CONSTRAINT edan_localidades_proteccion_id_grupo_vulnerable_seq,
  RENAME COLUMN id_grupo_vulnerable_new TO id_grupo_vulnerable,
  ADD CONSTRAINT edan_localidades_proteccion_id_grupo_vulnerable_fkey
    FOREIGN KEY (id_grupo_vulnerable)
    REFERENCES edan.grupo_vulnerable(id_grupo_vulnerable);
```

### 4. Actualizar código Python

**Archivos a modificar:**

| Archivo | Cambios |
|---------|---------|
| `api/edan/schemas.py` | `GrupoVulnerable` schema: agregar `id_grupo_vulnerable: int`, `grupo` → `codigo: str` |
| `api/edan/service.py` | `_grupos_vulnerables()`: hacer JOIN con catálogo; `_insert_sections_only()`: validar FK |
| `api/edan/router.py` | Endpoint para listar catálogo: `GET /edan/grupo-vulnerable` |

**Schema Pydantic:**
```python
class GrupoVulnerable(BaseModel):
    """→ edan.edan_localidades_proteccion (1:N por grupo vulnerable)."""
    id_grupo_vulnerable: int | None = None  # FK a edan.grupo_vulnerable
    id_grupo_vulnerable_catalogo: int  # FK al catálogo
    grupo: dict | None = None  # { id, codigo, nombre, orden }
    mujeres: int = 0
    hombres: int = 0
    total: int = 0
    apoyo_psicologico: bool | None = None
    reposicion_documentos: bool | None = None
    observaciones: str = ''
```

### 5. Endpoints nuevos

```
GET /api/v1/edan/grupo-vulnerable
  → Lista todos los grupos del catálogo (activos)
  → Response: [{ id, codigo, nombre, descripcion, orden }, ...]

GET /api/v1/edan/grupo-vulnerable/{id}
  → Detalle de un grupo específico
```

### 6. Migración SQL (archivo `migrations/v1.10.0_grupo_vulnerable.sql`)

```sql
-- 1. Crear catálogo
CREATE TABLE edan.grupo_vulnerable (
    id_grupo_vulnerable   SERIAL PRIMARY KEY,
    codigo                VARCHAR(50) UNIQUE NOT NULL,
    nombre                VARCHAR(100) NOT NULL,
    descripcion           TEXT,
    orden                 INTEGER NOT NULL DEFAULT 0,
    activo                BOOLEAN NOT NULL DEFAULT TRUE
);

-- 2. Insertar datos
INSERT INTO edan.grupo_vulnerable (codigo, nombre, orden) VALUES
  ('ninos_0_5', 'Niñas y niños 0-5 años', 1),
  ('ninos_5_10', 'Niñas y niños 5-10 años', 2),
  ('adolescentes', 'Adolescentes', 3),
  ('mujeres_lactantes', 'Mujeres lactantes', 4),
  ('mujeres_embarazadas', 'Mujeres embarazadas', 5),
  ('adultos_mayores', 'Adultos mayores', 6),
  ('personas_discapacidad', 'Personas con discapacidad', 7),
  ('personas_enfermedad_cronica', 'Personas con enfermedad crónica', 8);

-- 3. Modificar edan_localidades_proteccion
-- (ver sección 3 arriba para detalles)

-- 4. Índices
CREATE INDEX idx_edan_proteccion_grupo ON edan.edan_localidades_proteccion(id_grupo_vulnerable);
CREATE INDEX idx_grupo_vulnerable_activo ON edan.grupo_vulnerable(activo, orden);
```

## Tradeoffs

| Opción | Ventaja | Desventaja |
|--------|---------|------------|
| **Catálogo (propuesta)** | Valores configurables sin migración, descripciones, orden UI, se puede desactivar | Requiere JOIN en queries, tabla adicional |
| **CHECK constraint (actual)** | Simple, sin joins, más rápido | Requiere migración para cambiar valores, sin descripciones |

## Preguntas para el usuario

1. **¿Separar `ninos_0_5` y `ninos_5_10`?** El usuario indicó "Niñas y niños 0-5 años" y "Niñas y niños 5-10 años" como dos grupos distintos. ¿Confirmar?

2. **¿Mantener `id_grupo_vulnerable` como PK técnica o eliminarla?** 
   - Opción A: Mantener SERIAL como PK, agregar `id_grupo_vulnerable_catalogo` como FK
   - Opción B: `id_grupo_vulnerable` es directamente la FK al catálogo (elimina columna técnica)

3. **¿Incluir campo `descripcion` en el catálogo?** ¿Para qué se usaría?

4. **¿Campo `activo` para soft-delete?** ¿O los grupos son inmutables una vez creados?

5. **¿Migrar datos existentes?** Actualmente hay datos con `grupo` como string. ¿Se debe migrar automáticamente o se asume que no hay datos en producción?
