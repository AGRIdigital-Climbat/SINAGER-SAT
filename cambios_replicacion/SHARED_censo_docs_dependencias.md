# SHARED / Censo — Alineación docs y dependencia pyarrow

> **Esquema/módulo:** `shared` / Censo 2024 (hogares, por-nombre) + documentación general.  
> **Migración:** **ninguna nueva** (v2.17.0 ya existe en `database/migrations/` y espejo `despliegue/migraciones/`, idempotente).  
> **Rama/commit:** `migraciones`.

## 1. Objetivo
Alinear documentación y dependencias con lo ya implementado/subido del paquete censo-hogares/PPH (v2.17.0, extremos `por-nombre`), sin cambiar lógica de API.

## 2. Archivos (modificados)
| Archivo | Cambio |
|---|---|
| `docs/manual/06-indicadores.md` | Endpoint `GET /api/v2/shared/censo/manzanos/por-nombre` y campos de resúmenes: `poblacion`, `viviendas`, `hogares`, `unidades_con_hogares`, `hogares_ine`, `personas_por_hogar` (redondeo normal; `NULL` = sin dato oficial). |
| `README.md` | Añade `scripts/cargar_hogares_censo2024.py` al listado de scripts. |
| `requirements.txt` | Añade `pyarrow>=15` (lectura parquet fichas INE), requerido por el cargador de hogares. |

## 3. Replicación
1. `git pull` y `pip install -r requirements.txt` (instala pyarrow si falta).
2. Migración v2.17.0 ya versionada (aplicar solo si no se aplicó): `psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f database/migrations/v2.17.0_shared_censo2024_hogares.sql`.
3. Sin reinicio obligatorio por estos cambios; reiniciar API si se despliega junto a otros.

## 4. Verificación
- `python3 -c "import pyarrow"` tras instalar dependencias.
- Consulta `GET /api/v2/shared/censo/manzanos/por-nombre?id_municipio=10101` devuelve grupos con `hogares`/`personas_por_hogar`.
