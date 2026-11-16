# Cambio: HOGARES del Censo 2024 — instrucciones para replicar en el servidor limpio

> **Para qué sirve este documento.** Este repositorio (servidor de prueba) incorporó el dato
> oficial de **hogares** del CPV-2024 al módulo Censo 2024. El servidor "en limpio" (clon idéntico
> que se está montando aparte) debe recibir **exactamente los mismos cambios**. Aquí está el
> registro completo: decisiones, fuentes, tabla de cambios por archivo, pasos de replicación y
> verificación. **No falta nada: todo lo que se tocó está listado aquí.**
>
> Fecha del cambio: **2026-11-14** · Rama: **`feature/censo2024-hogares`** (esta carpeta
> versionada: instrucciones + análisis de NULLs + datos fuente). El **código** de §3 vive en el
> servidor de prueba aún sin commitear; la lista de §3 es la definitiva para replicar.
>
> **Nota:** esta carpeta también documenta otro cambio del mismo patrón de handoff —
> **`observacion_estado`** en EDAN localidades: ver [`EDAN_observacion_estado.md`](EDAN_observacion_estado.md)
> (migración v2.64.0).

---

## 1. Decisiones tomadas (cerradas con el equipo)

1. **Dato = "hogares" del INE**, equivalente censal oficial de "familias". El CPV-2024 **no
   publica "familias por comunidad"**. Hogares = viviendas particulares ocupadas con personas
   presentes (`viv_tipo_presentes` de la ficha del geoportal), la misma base del promedio de
   personas por hogar del INE.
2. **NO se divide población/viviendas** (las viviendas incluyen desocupadas; daría ~2,5 vs el
   real 3,1 nacional).
3. **Cobertura solo oficial**: unidades sin ficha INE quedan con `hogares = NULL` (reserva
   estadística). Los agregados exponen `unidades_con_hogares` como indicador de transparencia.
   No se estimó ningún dato.
4. **Municipio = fichas + tabulado INE 8,7 MB**: además de las fichas por unidad se carga el
   tabulado oficial "Vivienda y hogar" (cuadro 19) con los **hogares exactos de los 343
   municipios** en la tabla nueva `shared.censo2024_hogares_municipio`.
5. **`personas_por_hogar` = redondeo normal** (el definido por el equipo: **3,5 → 4;
   3,2 → 3**) en **todas** las respuestas nuevas.
   En agregados la base preferente es `hogares_ine` (dato exacto INE, cobertura 343/343); si no
   está cargado, se usa la población cubierta y `hogares` de unidades.
6. **API nueva** `GET /censo/manzanos/por-nombre`: los manzanos **no tienen nombre único** (el
   más repetido es el del municipio: 20.775 manzanos "SANTA CRUZ DE LA SIERRA"). Se agrupa por
   **(municipio, nombre)** respetando la jerarquía `id_departamento → id_provincia → id_municipio`
   → 2.942 grupos que cubren el 100 % de los 247.429 manzanos (nunca se mezclan municipios
   distintos: "VIACHA" en Viacha y Colcha "K" quedan separados).
7. **Los endpoints existentes NO cambian de forma ni de filtros** (regla del skill de listados):
   solo se **agregan campos** al JSON.

---

## 2. Fuentes de datos (ya descargadas en esta carpeta)

| Archivo | En esta carpeta | URL oficial | SHA-256 |
|---|---|---|---|
| `ficha.parquet` (15,4 MB, 150.744 unidades) | `datos/ficha.parquet` | `https://github.com/lab-tecnosocial/censosbo/releases/download/data-fichas-v1.0.0/ficha.parquet` | `93bcc04633a60c9f5cb8ce44a742b8ce4ed3276488d1761b2ae51cbd51bfb59d` |
| `tabulado_vivienda_hogar.xlsx` (9,1 MB, cuadro 19) | `datos/tabulado_vivienda_hogar.xlsx` | `https://nube.ine.gob.bo/index.php/s/6H760RRaNemfydX/download` (pestaña "Tabulados > Vivienda y hogar" de cpv2024.ine.gob.bo) | `4b7a3d4e292e6b63aecac9970a760cc2d0d61e7535dcaeb8c6848943b8b67caa` |

Validaciones que ya pasaron (las repite el script en cada corrida):

- Por unidad: `Σ(hogar_*) = viv_tipo_presentes` en el **100 %** de las 150.744 filas; ningún
  negativo; ningún `hogares > viviendas`.
- Tabulado: cuadro 19, columna del año **2024** (índice 24), fila total de cada municipio
  (`NIVEL = Municipio/TIOC` y `ÁREA = MUNICIPIO/TIOC`), cruces por nombre dep/prov/mun
  normalizados (tildes/mayúsculas) → **343/343 exactos**; **suma 3.623.711 = total Bolivia**.
- Resultado cargado: 150.744 unidades con `hogares` (131.801 manzanos + 18.943 comunidades;
  117.860 unidades sin ficha → `NULL`); `SUM(hogares unidades) = 3.322.402` = **91,7 %** del
  total INE; cruce `SUM(unidades) ≤ hogares_ine` OK en los 343 municipios.

> **Fixture de verificación** (`datos/verificacion_microdata_ine.json`, ~30 KB, commiteable sin
> `-f`): los 343 municipios con hogares/viviendas/población agregados desde la **microdata
> oficial INE** (CSV 413 MB), con URL y SHA-256 de la fuente. No es dato de carga: sirve para
> regresión en el servidor limpio. Ver **§7** (verificación cruzada y discrepancias).

> **Git:** `.gitignore` ignora `*.parquet` y `*.xlsx`. Para versionar los datos de esta carpeta
> hay que añadirlos con `git add -f cambios_hogares_censo2024/datos/` (ya hay precedente:
> `datos_censo2024/fuentes/unidad.parquet` está trackeado con `-f`). El script además puede
> **descargarlas solo** si no encuentra los archivos.

---

## 3. Cambios por archivo (lista exacta)

### 3.1 Archivos NUEVOS

| Archivo | Qué contiene |
|---|---|
| `database/migrations/v2.17.0_shared_censo2024_hogares.sql` | Migración idempotente (BEGIN/COMMIT, `IF NOT EXISTS`): columna `hogares integer CHECK (hogares IS NULL OR hogares >= 0)` en `shared.manzanos` **y** `shared.comunidades` (+ COMMENT), y tabla `shared.censo2024_hogares_municipio (id_municipio PK/FK → shared.municipio, hogares NOT NULL CHECK ≥ 0, fuente DEFAULT 'INE tabulado Vivienda y hogar', actualizado_en DEFAULT now())` |
| `despliegue/migraciones/v2.17.0_shared_censo2024_hogares.sql` | **Copia textual** de la anterior (obligatoria: `despliegue/scripts/actualizar.sh` aplica esta carpeta) |
| `scripts/cargar_hogares_censo2024.py` | Cargador nuevo: `--simular` (default) / `--importar`, `DATABASE_URL` env (mismo default que `cargar_censo2024_shared.py`), idempotente. Busca fuentes en `cambios_hogares_censo2024/datos/` → `datos_censo2024/fuentes/` → descarga. Fase A (pyarrow, unidades) y Fase B (openpyxl, 343 municipios), con reporte de cruce y cobertura |
| `cambios_hogares_censo2024/INSTRUCCIONES.md` | Este documento |
| `cambios_hogares_censo2024/ANALISIS_NULLS.md` | Análisis completo de los `NULL` de `hogares`: cifras exactas, dónde están (depto/grupos/municipios), por qué no hay otra fuente (reserva estadística INE), estimación evaluada y descartada, comportamiento de la API y SQL de reproducción |
| `cambios_hogares_censo2024/datos/ficha.parquet` + `…/tabulado_vivienda_hogar.xlsx` | Copias de los datos fuente (`git add -f`) |
| `cambios_hogares_censo2024/datos/verificacion_microdata_ine.json` | Fixture de verificación (343 municipios con hogares/viviendas/población agregados desde la microdata oficial INE 413 MB + URL/sha256); **no es dato de carga**, solo regresión (§7) |

### 3.2 Archivos MODIFICADOS (solo se agregan campos/resúmenes; nada se elimina)

| Archivo | Qué cambió |
|---|---|
| `requirements.txt` | + `pyarrow>=15` (bloque "Censo 2024") |
| `api/shared/schemas.py` | `_UnidadCensoBase`, `ManzanoCreate`, `ManzanoUpdate`: + `hogares: int \| None = None`. `ManzanoResponse`: + `personas_por_hogar: int \| None` (hereda a `ComunidadResponse`). `ResumenPoblacion`: + `hogares`, `unidades_con_hogares`, `hogares_ine`, `personas_por_hogar`. `ResumenPoblacionUnidad`: + `hogares`, `personas_por_hogar`. **Nuevo** `ManzanosPorNombreResponse` (ids jerárquicos, `municipio`, `nombre`, `manzanos`, `poblacion`, `viviendas`, `hogares`, `unidades_con_hogares`, `poblacion_con_hogares`, `personas_por_hogar`) |
| `api/shared/service.py` | `UNIDAD_CENSO_COLUMNAS`: + `hogares` (CRUD create/update). `_sql_unidad_censo`: + `a.hogares` y `personas_por_hogar` = `ROUND(personas/hogares)` (redondeo normal; NULL si `hogares` NULL/0). `_SQL_GEOJSON_UNIDAD`: + `hogares` y `personas_por_hogar` en `properties`. `_CTE_UNIDADES`: + `hog`, `hog_n`, `pers_hog`. `_SEL_RESUMEN`: + `hogares` (NULL si ninguna unidad del grupo tiene ficha), `unidades_con_hogares`, `poblacion_con_hogares`. `resumen_censo_nacional`: + totales de hogares, cobertura, `hogares_ine` (SUM de la tabla INE) y ratio. `resumen_censo_por_nivel`: + escalar `hogares_ine` por nivel (`_SQL_HOGARES_INE`: municipio directo; provincia/departamento = SUM de sus municipios; NULL si la tabla está vacía) y ratio con `_personas_por_hogar()`. `get_poblacion_unidad`: + `hogares`, `personas_por_hogar`. **Nuevo** `get_manzanos_por_nombre()` (agrupa manzanos por nombre dentro del municipio, filtros jerárquicos + `q`, `ORDER BY id_municipio, nombre`) y helper `_personas_por_hogar(poblacion, *bases)` (redondeo normal entero media hacia arriba; primera base no nula > 0) |
| `api/shared/router.py` | Import de `ManzanosPorNombreResponse`. Summaries/docstrings de `/censo/poblacion/*` y `/{codigo_ine}/poblacion` → "…población, viviendas y hogares". **Nuevo endpoint** `GET /censo/manzanos/por-nombre` (tag `Censo 2024 > Población y Viviendas`, `DataListResponse[ManzanosPorNombreResponse]`, filtros `id_departamento`, `id_provincia`, `id_municipio`, `q`; **sin paginación** — es consulta puntual como `/censo/poblacion/*` según el skill) |
| `DOCUMENTACION_SINB.md` | Tabla `shared`: + `hogares` en manzanos/comunidades, + fila `censo2024_hogares_municipio`, DDL con `v2.17.0`, nota "familias ≈ hogares". §6.4/6.5: campos nuevos, endpoint `por-nombre`, totales con hogares. §6.6: etapa de carga de hogares en el pipeline. Cap. 10: fila en el índice de APIs. Inventario de scripts: + `cargar_hogares_censo2024.py` |
| `docs/04-indicadores-y-reportes.md` | §5: fila `por-nombre`, párrafo de campos `hogares`/`unidades_con_hogares`/`hogares_ine`/`personas_por_hogar`, fuentes con `v2.17.0` |
| `docs/manual/06-indicadores.md` | §2: fila `por-nombre`, párrafo de campos + ejemplo curl del agrupado |
| `README.md` | Tabla "Scripts de Utilidad": + `scripts/cargar_hogares_censo2024.py` |
| `datos_censo2024/documentacion/README_censo2024.md` | Nueva **§12 "Hogares (dato oficial de familias)"**: fuentes con URLs/sha256, validaciones, resultados cargados |

**No se tocó ningún otro archivo.** (Los cambios que aparezca en `git status` de otros módulos —
RID A, motor de necesidades, manuales de solicitudes — son trabajo previo/paralelo del equipo,
ajeno a este cambio.)

---

## 4. Pasos de replicación en el servidor en limpio

```bash
# 0) Prerrequisitos (los mismos del repo)
#    - BD con las migraciones previas ya aplicadas (hasta v2.16.0)
#    - shared.manzanos/shared.comunidades CARGADAS (scripts/cargar_censo2024_shared.py)
#      El cargador de hogares aborta si las tablas están vacías.

# 1) Código + datos (si este repo ya está commiteado, basta un pull)
git pull   # o copiar los archivos listados en §3

# 2) Dependencias (pyarrow es lo nuevo)
pip install -r requirements.txt        # o: venv/bin/pip install -r requirements.txt

# 3) Datos fuente: si NO están en cambios_hogares_censo2024/datos/, copiarlos ahí
#    desde este servidor, o dejar que el script los descargue solo (mismas URLs/sha256).
#    (Ambos binarios van con git add -f: .gitignore tiene *.parquet y *.xlsx)

# 4) Migración (idempotente, se puede correr 2 veces)
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
  -f database/migrations/v2.17.0_shared_censo2024_hogares.sql
#    Alternativa de despliegue: despliegue/scripts/actualizar.sh
#    (aplica TODO despliegue/migraciones/; incluye esta copia)

# 5) Simular (no escribe; valida todo)
venv/bin/python scripts/cargar_hogares_censo2024.py --simular

# 6) Importar
venv/bin/python scripts/cargar_hogares_censo2024.py --importar

# 7) Reiniciar la API para cargar el código nuevo
./stop.sh && ./start_api.sh
```

---

## 5. Verificación (checklist de aceptación)

### SQL

```sql
-- idempotencia de la migración (correr el -f dos veces, debe decir IDEMPOTENT OK)
SELECT to_regclass('shared.censo2024_hogares_municipio');

SELECT count(*) AS con_hogares FROM shared.manzanos   WHERE hogares IS NOT NULL; -- 131.801
SELECT count(*) AS con_hogares FROM shared.comunidades WHERE hogares IS NOT NULL; -- 18.943
SELECT count(*) FROM shared.manzanos   WHERE hogares > viviendas;                -- 0
SELECT count(*) FROM shared.comunidades WHERE hogares > viviendas;               -- 0
SELECT count(*), sum(hogares) FROM shared.censo2024_hogares_municipio;
-- 343 | 3623711

-- coherencia: los 9 departamentos suman el total INE
SELECT sum(hogares) FROM shared.censo2024_hogares_municipio;                     -- 3.623.711
```

### API (con la API corriendo, base `http://localhost:8000/api/v2/shared`)

```bash
# 1) Listado de manzanos: agrega hogares + personas_por_hogar (campos viejos intactos)
curl -s "$B/manzanos?limit=2" | python3 -m json.tool

# 2) Población de una unidad
curl -s "$B/comunidades/02417371843-M/poblacion"
#    → {"poblacion":20,"viviendas":29,"hogares":10,"personas_por_hogar":2}

# 3) GeoJSON con hogares en properties
curl -s "$B/manzanos/00629371306-A/geojson"

# 4) Resumen nacional (hogares_ine = 3.623.711, unidades_con_hogares = 150.744)
curl -s "$B/censo/poblacion/nacional" | python3 -m json.tool

# 5) Resumen por municipio con filtros jerárquicos (hogares_ine exacto)
curl -s "$B/censo/poblacion/municipios?id_departamento=5"
curl -s "$B/censo/poblacion/municipio/10101"     # Sucre: hogares_ine 92.531

# 6) NUEVO: manzanos agrupados por nombre
curl -s "$B/censo/manzanos/por-nombre" | python3 -c "import json,sys;print(json.load(sys.stdin)['total'])"  # 2.942
curl -s "$B/censo/manzanos/por-nombre?id_municipio=10101"    # 28 grupos de Sucre
curl -s "$B/censo/manzanos/por-nombre?id_departamento=1&q=chull"
```

Esperado: **ningún campo existente desaparece ni cambia de tipo**; los nuevos son aditivos y
`SuccessResponse`/`DataListResponse` siguen igual (`total = len(data)` en los listados censo).

### Regresión básica

- `GET /api/v2/shared/departamentos` y `/municipios?limit=2` (catálogos intactos).
- `GET /api/v2/shared/manzanos/geojson?limit=1` (GeoJSON renderiza con las propiedades nuevas).
- `python3 -m compileall api/shared scripts/cargar_hogares_censo2024.py` sin errores.

---

## 6. Notas y advertencias

- **`hogares = NULL` ≠ 0**: es "sin ficha del INE" (reserva estadística). `personas_por_hogar`
  también es `NULL` en ese caso. Nunca inventar datos. **Análisis completo (cifras, ubicación,
  fuentes descartadas): [`ANALISIS_NULLS.md`](ANALISIS_NULLS.md).**
- **Dos cifras de hogares en municipio**: `hogares` (suma de unidades con ficha, con su
  cobertura `unidades_con_hogares`) y `hogares_ine` (tabulado INE, exacto). Los ratios usan
  `hogares_ine`; es intencional y documentado.
- **`personas_por_hogar` usa redondeo normal** (media hacia arriba: 3,5→4; 3,2→3), como definió
  el equipo: el INE publica 3,07 nacional y con este redondeo la respuesta es **3** (igual que
  redondeando nuestro 3,14). La base del numerador es
  `personas` (población **total** de la unidad/municipio, incluye colectivas y calle); el INE
  calcula su 3,07 solo con población **en viviendas particulares** (11.134.130). Detalle y
  impacto cuantificado en **§7.2 (D2)**.
- **Casos extremos por unidad (>20 pers/hogar)**: en manzanas/comunidades con viviendas
  colectivas el ratio puede ser alto (p.ej. 77, 363) y no representa tamaño de familia.
  Se **mantiene el valor real** en acceso directo/listados por unidad (`/manzanos/{codigo}`,
  `/comunidades/{codigo}`, `/manzanos`, `/comunidades`). En `GET /censo/manzanos/por-nombre`,
  si el ratio del grupo es **> 20** se reemplaza por el **promedio oficial del municipio**
  (`ROUND(población total / hogares_ine)`). Informe completo: **[`INFORME_CASOS_EXTREMOS_PPH.md`](INFORME_CASOS_EXTREMOS_PPH.md)**.
- **Cobertura de fichas**: 91,7 % de los hogares del país; las unidades sin ficha (sobre todo
  en algunos municipios rurales) quedan en `NULL` y se reflejan en `unidades_con_hogares`.
- **El tabulado tiene 3 columnas por bloque** (2001 / 2012 / **2024**): el cargador lee
  siempre la columna 2024 (índice 24) del cuadro 19. Si el INE republica el archivo con otra
  estructura, el script valida 343 filas y suma = total Bolivia y **aborta** si no cuadra.
- Migraciones: este repo usa doble ubicación (`database/migrations/` + espejo en
  `despliegue/migraciones/`). Si se añade una migración futura relacionada, copiarla en ambas.
- El endpoint `por-nombre` es **exento de paginación** por ser consulta puntual (skill
  `api-get-listados`, regla 3); los listados dinámicos `/manzanos` y `/comunidades` conservan
  su `limit`/`skip`/`todos` originales sin cambios.

---

## 7. Verificación cruzada desde otras fuentes y discrepancias revisadas

> Hecho el **2026-11-14**, después de cargar los datos. Objetivo: responder "¿los números
> cargados coinciden con fuentes independientes?" y "¿qué discrepancias existen y por qué?".

### 7.1 Matriz de verificación (4 fuentes independientes)

| # | Fuente | Qué se comparó | Resultado |
|---|---|---|---|
| 1 | **Microdata oficial INE** — "BASE DE DATOS CSV 413,1 MB (ZIP)" de `cpv2024.ine.gob.bo/index.php/principal/descargas/`, `https://nimbus.ine.gob.bo/index.php/s/qEmK9gnkGCZ3K7D/download`, SHA-256 `9c41c13e655b99bbe4944801953b70678317e3ae9599f35d791e1262ab372160` (**verificado: coincide con el publicado**) | Recuento desde **registros crudos** (`Vivienda_CPV-2024.csv` 4,48 M filas + `Persona_CPV-2024.csv` 11,36 M filas) agrupado por `idep‖iprov‖imun` = `shared.municipio.codigo_ine` | **343/343 hogares exactos · 343/343 viviendas exactas · 343/343 poblaciones exactas** contra la BD; totales nacionales exactos: hogares **3.623.711**, viviendas **4.480.201**, población **11.365.333**, población en viviendas particulares **11.134.130** |
| 2 | **Tabulado oficial "Vivienda y hogar"** (el de `datos/`) | Cuadro 19 vs **cuadro 6** ("viviendas particulares ocupadas con personas presentes") vs cuadro 1 vs cuadro 3, a nivel municipio y departamento | Cuadro 19 = cuadro 6 en **343/343**; suma de municipios = fila departamento **9/9** (en los 3 cuadros); cuadro 22 (promedio publicado 3,07257670382655) = 11.134.130 / 3.623.711 = **reproducción exacta** |
| 3 | **Fichas censales (censosbo)** | BD por unidad vs ficha fuente | **0 desajustes**: 150.744/150.744 unidades idénticas en `personas` y `viviendas` |
| 4 | **Notas de prensa oficiales INE** (`cpv2024.ine.gob.bo`, ago-2025) | Cifras publicadas vs BD/tabulado | Población **11.365.333** ✓ · viviendas **4.480.201** ✓ (serie 2.270.731 → 3.159.350 → 4.480.201) · "promedio de personas por hogar **3,1**" ✓ (3,07 → **3** con redondeo normal) · tipología: pareja nuclear 6,7 % = 6,7 % ✓, monoparental 17,3 ≈ 17,2 %, unipersonal 25,3 ≈ 25,9 % (brecha esperada: la tipología de las fichas solo cubre el 91,7 % de los hogares) |

**Reglas del recuento de la microdata** (para reproducirlo):

- `particular` = `v01_tipoviv ∈ 1–6` (el tipo 6 "establecimiento no destinado para vivienda"
  lo cuenta INE como particular: 4.448.326 + 15.447 = **4.463.773** exacto); `colectiva` =
  7–14 (**16.428**); `calle/tránsito` = 15–16 (10.287 filas, no son viviendas).
- `hogares` = particulares con `v02_condocup ∈ {0,1}` (0 = "ocupada con personas presentes sin
  jefe": 3.985) → **3.623.711**. `v02_condocup` viene vacío exactamente en las 26.715 filas de
  colectiva/calle (16.428 + 10.287), consistente.
- `tot_pers` de esos hogares suma **11.134.130** = población en viviendas particulares (la base
  del promedio del INE).

### 7.2 Discrepancias revisadas (todas diagnosticadas)

| ID | Qué se detectó | Diagnóstico | Estado |
|---|---|---|---|
| D1 | 117.860 unidades con `hogares = NULL` (cobertura: 91,7 % hogares, 91,65 % población, 90,0 % viviendas) | La fuente censosbo solo publica fichas de 150.744 unidades | **Por diseño**: `NULL` = sin ficha (≠ 0); `unidades_con_hogares` lo publica en todos los agregados. Análisis detallado en [`ANALISIS_NULLS.md`](ANALISIS_NULLS.md) |
| D2 | **Base del ratio**: `personas_por_hogar` agregado usa `poblacion` **total** (incluye 207.801 personas en viviendas colectivas + 23.402 en calle/tránsito); el INE calcula su 3,07 solo con población **en viviendas particulares** (11.134.130) | Nacional: 3,14 (nuestra) vs 3,07 (INE) → **con redondeo normal ambos = 3 (idéntico)**. A nivel municipio: **28/343 difieren en ±1** (ej.: Santa Cruz de la Sierra → nosotros 4, INE 3; Antequera → 3 vs 2) porque sus viviendas colectivas/calle empujan el cociente por encima de 3,5. La fórmula vigente `ROUND(poblacion/hogares)` es internamente coherente: usa los mismos `poblacion` y `hogares` que muestra la respuesta | **Documentado, sin cambio.** Alineación estricta con INE exigiría cargar `poblacion_particular` por municipio (tabulado cuadro 3, columna 16) y usarla solo en agregados → **mejora futura opcional**, no implementada |
| D3 | 250 unidades con `personas/hogares > 10` (máx 362,7: `00629371306-A` = 5.441 pob / 35 viv / 15 hog) | Contrastado contra la ficha fuente: **mismos valores** (5.441/35/15) | **No es error de carga**: anomalía del dato censal publicado; no se modificó nada (0 unidades con `viviendas < hogares`, 0 con `hogares` de unidades > INE) |
| D4 | `viviendas` de la BD (4.480.201) incluye **16.428 colectivas** (particulares 4.463.773) | El dato por unidad del geoportal es vivienda total; coincide **exacto** con el total oficial INE (cuadro 1) | **Correcto**: `hogares ≤ viviendas` en 343/343 municipios y en las 150.744 unidades con ficha |
| D5 | Unidades sin ficha tienen `personas`/`viviendas` (948.711 pob) pero `hogares = NULL` | Población y viviendas vienen del geoportal; el desglose de hogares solo existe donde hay ficha | OK: cobertura declarada, nunca se estimó |
| D6 | 14 unidades con ficha pero `hogares = 0` | `viv_tipo_presentes = 0` en la fuente | Válido: `0 ≠ NULL` (vivienda registrada sin personas presentes) |

**Cobertura por municipio**: 343/343 tienen al menos una unidad con ficha;
`SUM(unidades) ≤ hogares_ine` en los 343 (un solo empate exacto: San Pedro/La Paz 612 = 612).
Menor cobertura: San Agustín (Potosí) 175/667 = 26 %, Coipasa (Oruro) 125/357,
San Antonio de Lomerio (Santa Cruz) 612/1.475, Yunguyo del Litoral (Oruro) 72/173, Llica
(Potosí) 819/1.856.

### 7.3 Reproducir la verificación en el servidor limpio

```bash
# A) Fixture ya agregada (sin descargar la microdata): comparar BD vs microdata oficial
venv/bin/python - <<'PY'
import json, psycopg2, os
fx = json.load(open('cambios_hogares_censo2024/datos/verificacion_microdata_ine.json'))['por_municipio']
conn = psycopg2.connect(os.environ.get('DATABASE_URL',
      'postgresql://sinagersat:12345678@127.0.0.1:5432/db_sinagersat'))
cur = conn.cursor()
cur.execute("""SELECT m.codigo_ine, h.hogares FROM shared.censo2024_hogares_municipio h
               JOIN shared.municipio m ON m.id=h.id_municipio""")
bd_hog = dict(cur.fetchall())
cur.execute("""SELECT m.codigo_ine, SUM(t.viviendas), SUM(t.personas) FROM (
                 SELECT id_municipio, viviendas, personas FROM shared.manzanos
                 UNION ALL SELECT id_municipio, viviendas, personas FROM shared.comunidades)
               t JOIN shared.municipio m ON m.id=t.id_municipio GROUP BY m.codigo_ine""")
bd_uni = {r[0]: (r[1], r[2]) for r in cur.fetchall()}
mal_h = [k for k in fx if bd_hog.get(k) != fx[k]['hogares']]
mal_v = [k for k in fx if bd_uni.get(k, (0,0))[0] != fx[k]['viviendas']]
mal_p = [k for k in fx if bd_uni.get(k, (0,0))[1] != fx[k]['poblacion']]
print('hogares', len(fx)-len(mal_h), '| viviendas', len(fx)-len(mal_v),
      '| poblacion', len(fx)-len(mal_p), 'de', len(fx), '| malos:', (mal_h+mal_v+mal_p)[:5])
PY
# Esperado: "hogares 343 | viviendas 343 | poblacion 343 de 343 | malos: []"

# B) FULL (opcional): microdata completa 413 MB (~7 min; SHA-256 OBLIGATORIO)
curl -sL -o /tmp/cpv2024.zip "https://nimbus.ine.gob.bo/index.php/s/qEmK9gnkGCZ3K7D/download"
sha256sum /tmp/cpv2024.zip   # debe dar 9c41c13e655b99bbe4944801953b70678317e3ae9599f35d791e1262ab372160
unzip -l /tmp/cpv2024.zip    # Vivienda_CPV-2024.csv + Persona_CPV-2024.csv + diccionario
# Reglas de agregación: ver §7.1. Al terminar: borrar el zip y lo extraído (~3,9 GB).
```

Spot checks rápidos (valores de la microdata, por `codigo_ine`):

```sql
SELECT m.codigo_ine, m.nombre, h.hogares FROM shared.censo2024_hogares_municipio h
JOIN shared.municipio m ON m.id=h.id_municipio
WHERE m.codigo_ine IN ('010101','020101','020105','070101');
-- 010101 Sucre 92531 · 020101 Nuestra Señora de La Paz 250931
-- 020105 El Alto 297898 · 070101 Santa Cruz de la Sierra 453158
```
