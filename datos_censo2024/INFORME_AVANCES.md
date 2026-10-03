# Informe Técnico de Avances — datos_censo2024

> Cabecera y resúmenes se completan/refinan con el comando /informe (skill: informe-avance).
**Fecha de actualización:** 2026-09-21
**Actividad / Objetivo:** <pendiente — ejecuta /informe para completarlo>
**Métodos aplicados:** <pendiente — ejecuta /informe para completarlo>
**Estado del trabajo:** EN PROGRESO

## Avances
### Avance 1 — 2026-09-21
- **Sesión:** "Create AGENTS.md for repo"
- **Objetivo del avance:** Create or update `AGENTS.md` for this repository. The goal is a compact instruction file that helps future OpenCode sessions avoid mistakes and ramp up quickly. Every line should answer: "Would an agent likely miss this without help?" If not, leave it out. User-provided focus or constraints (honor t…
- **Cambios (archivos):** Ninguno
- **Herramientas usadas:** bash, glob, read
- **Resultado del asistente:** Investigated the repo. It's a Python data pipeline (Censo 2024 Bolivia) with no git repo, no tests/lint, docs in Spanish. Key high-value facts an agent would otherwise miss are all here (OOM trap from string-concat, WKB reading quirk, `area` vs `area_oficial` semantics, script execution order). Plan…

### Avance 2 — 2026-09-21
- **Sesión:** "Create AGENTS.md for repo"
- **Objetivo del avance:** Create or update `AGENTS.md` for this repository. The goal is a compact instruction file that helps future OpenCode sessions avoid mistakes and ramp up quickly. Every line should answer: "Would an agent likely miss this without help?" If not, leave it out. User-provided focus or constraints (honor t…
- **Cambios (archivos):** Ninguno
- **Herramientas usadas:** bash, glob, read
- **Resultado del asistente:** Buena duda. La respuesta corta: **no hay ningún forzado** — `area_oficial` sale de la variable `area` de los **microdatos oficiales del INE** (`persona_dep*.parquet`), y `Urbana/Rural/Mixto` son etiquetas por **municipio**, no por unidad. Manzano/Comunidad quedan como una clasificación aparte. ## Qu…

### Avance 3 — 2026-09-21
- **Sesión:** "Create AGENTS.md for repo"
- **Objetivo del avance:** Create or update `AGENTS.md` for this repository. The goal is a compact instruction file that helps future OpenCode sessions avoid mistakes and ramp up quickly. Every line should answer: "Would an agent likely miss this without help?" If not, leave it out. User-provided focus or constraints (honor t…
- **Cambios (archivos):** Ninguno
- **Herramientas usadas:** bash, glob, read
- **Resultado del asistente:** Respuesta corta: **no son compatibles 1:1**. Manzano/Comunidad es **cartográfico** (tipo de unidad) y `area_oficial` es **urbano/rural oficial del INE** (etiqueta del municipio). Se superponen, pero no se equivalen — por eso coexisten como dos columnas en todas las tablas. El cruce real de las 268.6…

### Avance 4 — 2026-09-21
- **Sesión:** "Create AGENTS.md for repo"
- **Objetivo del avance:** Create or update `AGENTS.md` for this repository. The goal is a compact instruction file that helps future OpenCode sessions avoid mistakes and ramp up quickly. Every line should answer: "Would an agent likely miss this without help?" If not, leave it out. User-provided focus or constraints (honor t…
- **Cambios (archivos):** Ninguno
- **Herramientas usadas:** bash, glob, read
- **Resultado del asistente:** Sí, es correcta la idea de separar, pero con **tres advertencias** para que no te engañes con los nombres: ## 1. Qué contiene cada archivo si partes por `area_oficial` | Excel | Unidades | Composición (manzanos / comunidades) | |---|---|---| | **Urbana** | 907 | solo manzanos (Colcapirhua) | | **Rur…

### Avance 5 — 2026-09-21
- **Sesión:** "Create AGENTS.md for repo"
- **Objetivo del avance:** Create or update `AGENTS.md` for this repository. The goal is a compact instruction file that helps future OpenCode sessions avoid mistakes and ramp up quickly. Every line should answer: "Would an agent likely miss this without help?" If not, leave it out. User-provided focus or constraints (honor t…
- **Cambios (archivos):** Ninguno
- **Herramientas usadas:** bash, glob, read
- **Resultado del asistente:** Sí, es válido y es lo recomendado. `manzanos_censo2024.csv` y `comunidades_censo2024.csv` son las tablas **a nivel unidad** (las "hojas" correctas). Lo clave: `area_oficial` **ya viene como columna dentro de ambos** — no necesitas crear tablas separadas "urbana/rural/mixto" a nivel unidad, y de hech…

### Avance 6 — 2026-09-21
- **Sesión:** "Create AGENTS.md for repo"
- **Objetivo del avance:** Create or update `AGENTS.md` for this repository. The goal is a compact instruction file that helps future OpenCode sessions avoid mistakes and ramp up quickly. Every line should answer: "Would an agent likely miss this without help?" If not, leave it out. User-provided focus or constraints (honor t…
- **Cambios (archivos):** Ninguno
- **Herramientas usadas:** bash, glob, read
- **Resultado del asistente:** Plan listo. Verifiqué las columnas reales de cada CSV. Propongo crear **`documentacion/POSTGRES_censo2024.md`** con este contenido: ## Esquema del documento **1. Objetivo** — qué se lleva a Postgres y desde dónde. **2. Hojas/archivos a cargar (y cuáles NO)** - Cargar (de `procesado/`): - `unidades_c…

### Avance 7 — 2026-09-21
- **Sesión:** "Create AGENTS.md for repo"
- **Objetivo del avance:** Create or update `AGENTS.md` for this repository. The goal is a compact instruction file that helps future OpenCode sessions avoid mistakes and ramp up quickly. Every line should answer: "Would an agent likely miss this without help?" If not, leave it out. User-provided focus or constraints (honor t…
- **Cambios (archivos):** Ninguno
- **Herramientas usadas:** bash, edit, glob, read, write
- **Resultado del asistente:** Ajustado. Con PostGIS confirmado: - §5 ahora marca las geometrías del GPKG (3 capas, EPSG:4326) como parte del plan recomendado, además de `lat`/`lon`. - §8.1: `psql \copy` queda como vía principal y Python como opción solo si hay transformaciones. El flujo final: tablas de `procesado/` + capas `man…
