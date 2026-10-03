# Migración del Censo 2024 a PostgreSQL — qué cargar, columnas y datos geo

> **Documento**: `documentacion/POSTGRES_censo2024.md`
> **Fuente de verdad técnica**: `documentacion/README_censo2024.md` (diccionario de datos, semántica y controles). Léelo antes de tocar las tablas.
> **Origen de los archivos**: `procesado/` (CSV) y `geo/` (GeoPackage).

Guía concreta de qué hojas, qué columnas y qué datos geo llevar a tu base PostgreSQL, y desde qué archivo.

---

## 1. Objetivo

Cargar el universo censal de Bolivia (CPV-2024) en PostgreSQL conservando las **dos clasificaciones**
del INE (cartográfica y oficial de microdatos) sin perder precisión.

Regla de oro del proyecto: `area`/`tipo_unidad` es la clasificación **cartográfica** (tipo de unidad)
y `area_oficial` es la clasificación **oficial INE por municipio** (de los microdatos). Ambas coexisten
en todas las tablas de unidades; para reportar urbano/rural se usa `area_oficial` (README §8).

---

## 2. Hojas (archivos) a cargar

### 2.1 Sí cargar — desde `procesado/`

| Archivo | Filas | Uso en la BD | ¿Obligatorio? |
|---|---|---|---|
| `unidades_censo2024.csv` | 268.604 | **Tabla maestra**: una fila por unidad censal mínima | Sí |
| `manzanos_censo2024.csv` | 247.429 | Vista/tabla `manzanos` (tipo = Manzano) | Vistas (derivadas) |
| `comunidades_censo2024.csv` | 21.175 | Vista/tabla `comunidades` (tipo = Comunidad) | Vistas (derivadas) |
| `municipios_censo2024.csv` | 343 | Dim. `municipios` (códigos + nombres + atributos SDSN) | Sí |
| `resumen_municipios.csv` | 343 | Resumen por municipio (población/viviendas **cartográfica y oficial**) | Sí (reporte) |
| `area_oficial_municipios.csv` | 343 | ¿Urbano/rural oficial? → estadísticas municipales **oficiales** | Sí (reporte) |
| `comparacion_departamentos_censo2024.csv` | 9 | Control geoportal vs microdatos (diferencia 0) | Opcional |
| `provincias_2024.csv` | 113 | Dim. `provincias` | Opcional |
| `relacion_comunidad_provincia.csv` | 21.175 | Cruce comunidad → dep/prov/mun | Opcional |

**Recomendación**: cargar la maestra `unidades_censo2024.csv` y las vistas
`unidades_manzanos` / `unidades_comunidades` como `VIEW` sobre ella (nunca duplicar filas).

### 2.2 No cargar

- `fuentes/` — parquets crudos de descarga (universo, geometrías, microdatos, SDSN). Son insumos del pipeline, no de la BD.
- `graficas/` y `graficas/ejemplos/` — PNG y muestras para divulgación.
- Cualquier `.csv` de "muestra" (`muestra_*.csv`).

---

## 3. Columnas y tipos por hoja

### 3.1 `unidades_censo2024.csv` (y sus subconjuntos manzanos/comunidades) — 19 columnas

| Columna | Tipo PostgreSQL | Notas |
|---|---|---|
| `codigo` | `text` **PRIMARY KEY** | ej. `04121212556-D`; sufijo `-A`=Manzano, `-D`/`-M`=Comunidad |
| `nombre` | `text` | nombre de la unidad |
| `tipo_unidad` | `text` CHECK (`'Manzano','Comunidad'`) | **cartográfico** (derivado de `area`) |
| `area` | `smallint` | **cartográfico**: 1=Manzano (amanzanada), 2=Comunidad (dispersa) |
| `personas` | `integer` | población censada — **no renombrar** (nombre de la fuente INE) |
| `viviendas` | `integer` | viviendas particulares con personas presentes |
| `ficha` | `boolean` | el INE publica ficha de 150.744 unidades (reserva estadística) |
| `idep` | `smallint` | código departamento (01–09) |
| `iprov` | `smallint` | código provincia (dentro del dep.) |
| `imun` | `smallint` | código municipio (dentro de la prov.) |
| `codigo_departamento` | `smallint` | = `idep` (2 dígitos) |
| `codigo_provincia` | `integer` | = `idep`+`iprov` (4 dígitos) |
| `codigo_municipio` | `integer` | = `idep`+`iprov`+`imun` (6 dígitos) **FK → municipios** |
| `nombre_dep` | `text` | |
| `nombre_prov` | `text` | |
| `nombre_mun` | `text` | |
| `lat` | `numeric(10,7)` | comunidad = punto real; manzano = **centroide** (ver §5) |
| `lon` | `numeric(10,7)` | idem |
| `area_oficial` | `text` CHECK (`'Urbana','Rural','Mixto'`) | **oficial INE** por municipio (microdatos) |

### 3.2 `municipios_censo2024.csv` — 8 columnas

`codigo_municipio integer PK` · `nombre_dep text` · `nombre_prov text` · `nombre_mun text` ·
`capital text` · `poblacion_2012 integer` · `poblacion_2024 integer` · `superficie_km2 numeric`

> ⚠️ `poblacion_2024` suma 11.364.933 (400 menos que el oficial 11.365.333). Es atributo **SDSN**;
> para totales oficiales usar el conteo de las unidades o `resumen_municipios`.

### 3.3 `resumen_municipios.csv` — 16 columnas

`codigo_municipio` · `nombre_dep` · `nombre_prov` · `nombre_mun` · `n_manzanos` · `n_comunidades` ·
`n_unidades` · `poblacion_urbana` / `poblacion_rural` / `poblacion_total` (**cartográfica**) ·
`viviendas_urbana` / `viviendas_rural` / `viviendas_total` (**cartográfica**) ·
`poblacion_urbana_oficial` / `poblacion_rural_oficial` (**oficial INE**) · `area_oficial`

Todas `integer` salvo `codigo_municipio` (int PK/FK) y textos de nombre.

### 3.4 `area_oficial_municipios.csv` — 5 columnas

`codigo_municipio int PK` · `poblacion_urbana_oficial int` · `poblacion_rural_oficial int` ·
`poblacion_total_oficial int` · `area_oficial text CHECK`

### 3.5 Control (`comparacion_departamentos_censo2024.csv`) — 11 columnas

`dep int` · `nombre_dep` · `n_urbana`/`urbana` · `n_rural`/`rural` · `n_total`/`total` (n_*=cartográfica,
sin prefijo=oficial) · `d_total`/`d_urbana`/`d_rural` (diferencias, deben dar **0**).

---

## 4. Relaciones y reglas de unión

```sql
ALTER TABLE unidades ADD CONSTRAINT fk_unidades_muni
  FOREIGN KEY (codigo_municipio) REFERENCES municipios(codigo_municipio);

CREATE INDEX idx_unidades_codigo_municipio ON unidades(codigo_municipio);
CREATE INDEX idx_unidades_codigo_provincia ON unidades(codigo_provincia);
CREATE INDEX idx_unidades_area_oficial     ON unidades(area_oficial);
CREATE INDEX idx_unidades_tipo_unidad      ON unidades(tipo_unidad);
```

- Unir unidad → territorio **siempre** por `codigo_municipio` (6 dígitos) / `codigo_provincia` (4).
  **Nunca por `imun` solo** (se repite entre provincias).
- Unir unidades entre sí por `codigo`.
- `codigo_municipio` = `idep*10000 + iprov*100 + imun` (aritmético, no concatenación de texto).

---

## 5. Datos geo — qué y de dónde

> Este entorno tiene **PostGIS**, así que el plan recomendado es cargar también las geometrías del
> GPKG (§5.2) además de las tablas. `lat`/`lon` se cargan igual (son parte de los CSV de unidades).

Hay dos niveles de granularidad geo, del más simple al más completo:

### 5.1 Columnas `lat`/`lon` (siempre disponibles, desde los CSV)

- **Comunidad**: punto real publicado por el INE (geoportal).
- **Manzano**: **centroide** calculado (reproyección a ESRI:102033 y vuelta a EPSG:4326) — NO es la
  geometría del manzano.
- Si no usás PostGIS, estas dos columnas son suficientes para localizar/plotear puntos.

### 5.2 Geometrías reales — `geo/unidades_censo2024.gpkg` (3 capas, EPSG:4326)

| Capa | Tipo geom. | Tamaño | Fuente original |
|---|---|---|---|
| `manzanos` | MultiPolygon | ~155 MB (todo el GPKG) | geoportal INE vía censosbo |
| `comunidades` | Point | idem | geoportal INE vía censosbo |
| `municipios` | MultiPolygon | idem | shapefile SDSN Bolivia 2026 (reproyectado) |

Cargar a PostGIS con `ogr2ogr` (el GPKG ya está en EPSG:4326):

```bash
ogr2ogr -f "PostgreSQL" PG:"host=HOST dbname=DB user=USER password=PASSWORD" ^
  -nln geo_manzanos     -lco GEOMETRY_NAME=geom "geo/unidades_censo2024.gpkg" manzanos
ogr2ogr -f "PostgreSQL" PG:"host=HOST dbname=DB user=USER password=PASSWORD" ^
  -nln geo_comunidades  -lco GEOMETRY_NAME=geom "geo/unidades_censo2024.gpkg" comunidades
ogr2ogr -f "PostgreSQL" PG:"host=HOST dbname=DB user=USER password=PASSWORD" ^
  -nln geo_municipios   -lco GEOMETRY_NAME=geom "geo/unidades_censo2024.gpkg" municipios
```

- Clave de unión con la capa `municipios`: `codigo_municipio` (igual que en las tablas).
- Clave de unión de `manzanos`/`comunidades` con `unidades`: `codigo`.
- Si solo necesitás puntos, no cargues el GPKG (usa `lat`/`lon`).

### 5.3 PostGIS vs columnas — cuándo cada uno

| Necesidad | Qué usar |
|---|---|
| Listados, sumas, reportes, clave municipio | CSV de `procesado/` (tablas) |
| Mapas, buffers, consultas espaciales, intersecciones | GPKG → PostGIS (`geo_manzanos`, `geo_comunidades`, `geo_municipios`) |
| Cruzar tabla con geometría | JOIN por `codigo` / `codigo_municipio` |

---

## 6. Semántica crítica (no confundir en la BD)

1. **`area`/`tipo_unidad` ≠ urbano/rural**. Es cartografía: Manzano (amanzanada) / Comunidad (dispersa).
2. **`area_oficial` = clasificación oficial INE por municipio** (`Urbana`/`Rural`/`Mixto`) desde los
   microdatos. **Es lo que se usa para reportar urbano/rural.**
   - `Urbana`: 100 % urbano en microdatos (1 municipio: Colcapirhua).
   - `Rural`: 100 % rural (158).
   - `Mixto`: tiene urbana y rural (184) → **no es asignable por unidad**; todos los manzanos/comunidades
     de esos municipios quedan etiquetados `Mixto`.
3. Cruce documentado (268.604 unidades): manzanos → 907 Urbana / 28.024 Rural / 218.498 Mixto;
   comunidades → 0 Urbana / 7.942 Rural / 13.233 Mixto.
4. `personas`, `viviendas`, `area`, `ficha` conservan el **nombre de la fuente INE**; no renombrarlos.
5. `i00` de los microdatos es id de vivienda/hogar, **no** un código de lugar; los microdatos solo
   llegan a municipio.

---

## 7. Controles al cargar (invariantes de la base)

| Concepto | Valor esperado |
|---|---|
| Filas en `unidades` | 268.604 (247.429 manzanos + 21.175 comunidades) |
| `SUM(personas)` | 11.365.333 |
| `SUM(viviendas)` | 4.480.201 |
| Municipios | 343 |
| Provincias | 113 |
| Departamentos | 9 |
| `comparacion_departamentos` (d_*) | 0 en los 9 |

```sql
SELECT count(*), sum(personas), sum(viviendas) FROM unidades;                 -- 268604 | 11365333 | 4480201
SELECT count(*) FROM unidades WHERE tipo_unidad='Manzano';                    -- 247429
SELECT count(*) FROM unidades WHERE tipo_unidad='Comunidad';                  -- 21175
SELECT count(*) FROM municipios;                                              -- 343
```

---

## 8. Carga paso a paso

### 8.1 Tablas (desde `procesado/`)

**`psql \copy` (recomendado; sin Python):**

```bash
psql -h HOST -U USER -d DB -c "CREATE TABLE ..."   # definiciones del §3
psql -h HOST -U USER -d DB -c "\copy unidades FROM 'procesado/unidades_censo2024.csv' WITH (FORMAT csv, HEADER true)"
psql -h HOST -U USER -d DB -c "\copy municipios FROM 'procesado/municipios_censo2024.csv' WITH (FORMAT csv, HEADER true)"
psql -h HOST -U USER -d DB -c "\copy resumen_municipios FROM 'procesado/resumen_municipios.csv' WITH (FORMAT csv, HEADER true)"
psql -h HOST -U USER -d DB -c "\copy area_oficial_municipios FROM 'procesado/area_oficial_municipios.csv' WITH (FORMAT csv, HEADER true)"
```

**Opción Python/psycopg2 (solo si necesitás transformar antes de cargar):**

```python
import psycopg2, pandas as pd

conn = psycopg2.connect("host=HOST dbname=DB user=USER password=PASSWORD")
for f, tbl in [("procesado/unidades_censo2024.csv", "unidades"),
               ("procesado/municipios_censo2024.csv", "municipios"),
               ("procesado/resumen_municipios.csv", "resumen_municipios"),
               ("procesado/area_oficial_municipios.csv", "area_oficial_municipios")]:
    df = pd.read_csv(f)
    df.to_sql(tbl, conn, if_exists="append", index=False)   # o COPY vía `COPY ... FROM STDIN`
```

### 8.2 Geometrías — ver §5.2 (`ogr2ogr` con el GPKG).

### 8.3 Orden recomendado

1. `municipios` (dimensiones) → 2. `unidades` (FK) → 3. `resumen_municipios` / `area_oficial_municipios`
→ 4. vistas `manzanos`/`comunidades` → 5. capas PostGIS → 6. correr controles del §7.