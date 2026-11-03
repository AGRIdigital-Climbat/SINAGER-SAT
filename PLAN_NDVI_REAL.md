# PLAN DE REANUDACIÓN — NDVI REAL (sin simulación)

> **Documento de reanudación.** Generado 2026-10-07. No se implementó nada del
> plan: sólo diagnóstico, mediciones de factibilidad y esta documentación.
> Leer completo antes de tocar código.

---

## 0. Contexto en 30 segundos

El módulo NDVI del SINB está **funcional pero simulado**: los valores vienen de
`random.uniform(0.3, 0.7)`, la cobertura histórica son **5 días** (2026-10-01 a
2026-10-05), `ndvi_anomalia` vale 0 en todas las filas y 2 endpoints tienen bugs.
Se midió la factibilidad de hacerlo **100% real** con Sentinel-2 (EarthSearch):
**es viable**. Faltan 3 decisiones del usuario y la implementación.

Reglas duras del usuario durante todo el proyecto:

1. **No hacer cambios sin pedido explícito.**
2. **No actualizar documentación existente** (`DOCUMENTACION_SINB.md`, `docs/`
   intactos; sólo archivos `??` untracked en git).
3. **NDVI: "no debe haber nada simulado, todo debe ser real".**
4. **"solo municipio" / "ya no hagas por comunidades"** (geografía de trabajo: 343
   municipios, NO las 21.175 comunidades).
5. **Visualización con degradé/mapa de calor** (celdas de color interpolado),
   **no un color plano por municipio**.
6. **APIs con filtros geográficos, por fechas y por municipio.**
7. **El cron no debe bloquear el servidor.**
8. **"mientras avanzas explícame lo que haces".**
9. Reinicio de API siempre con 4 workers (comando en §9).

---

## 1. Estado del sistema (medido 2026-10-07)

| Ítem | Valor |
|---|---|
| Servidor | 6 cores, load 2,30, RAM 5.924 MB (2.381 MB disponibles), swap 4 GB (1,5 GB usados) |
| Disco | 136 GB totales, **103 GB libres** (21% usado) |
| Python | 3.12.3 en `venv/` |
| Instalado en venv | **rasterio 1.5.2 (GDAL 3.12.2)**, numpy 2.5.3, shapely 2.1.2 |
| NO instalado | PIL/Pillow, fiona (no hace falta) |
| API | http://localhost:8000, uvicorn 4 workers, sin nginx |
| Herramientas cron | `nice`, `ionice`, `flock`, `timeout`, `systemctl` — todas presentes |
| systemd timers NDVI | ninguno (sólo crontab de root) |
| Frontend Leaflet | **no existe en el repo** (sólo props en `propuesta/*.md`, `SINB/sinb_20260714.sql`) |
| Git | repo con cambios sin commitear (no commitear sin pedido) |

### Estado de la base de datos (2026-10-07)

| Tabla | Filas | Notas |
|---|---|---|
| `sinb.serie_ndvi_comunidad` | **56.155** | **sólo 5 fechas**: 2026-10-01…2026-10-05; `ndvi_percentil` 100% NULL; datos aleatorios |
| `sinb.agregado_satelital` | **1.618.570** | **498 MB**, NDVI aleatorio |
| `sinb.escena_satelital` | 119 | 2026-09-24…2026-10-05, escenas STAC reales (sólo metadatos) |
| `sinb.ndvi_procesamiento_log` | 12 | estados: 1 inicializado, **5 en_progreso (colgadas)**, 1 error, 5 completado |

Vistas:
- `sinb.vw_alertas_ndvi` columnas: `codigo_ine, nombre, fecha, ndvi_promedio,
  ndvi_anomalia, estado_vegetacion, tipo_alerta, nivel_prioridad`
  → **NO tiene `departamento`, `provincia`, `municipio`**.
- `sinb.vw_evolucion_mensual_ndvi` columnas: `codigo_ine, nombre, mes,
  ndvi_promedio_mes, anomalia_promedio_mes, n_dias_con_datos`
  → expone **`codigo_ine`**, no `codigo_comunidad`.
- `sinb.vw_ultimo_ndvi_comunidad` existe.
- `v_verificaciones_pendientes` existe.

Geometrías:
- `shared.comunidades.geom` = **Point** (no polígono) — por eso NO se puede
  rasterizar por comunidad; otro motivo para trabajar sólo a nivel municipio.
- `shared.municipio.geom` = **MultiPolygon**, **343 municipios** (PK `id`).
- `shared.comunidades` PK = `codigo_ine` (21.175 filas).

---

## 2. Diagnóstico: qué está mal hoy

### 2.1 El NDVI es simulado (3 puntos exactos)

| Archivo:Línea | Código | Qué hace |
|---|---|---|
| `api/sinb/service_ndvi.py:430` | `base_ndvi = random.uniform(0.3, 0.7)` | NDVI inventado por escena |
| `api/sinb/service_ndvi.py:446` | `"pixeles": random.randint(100, 10000)` | píxeles inventados (por eso `pixeles_procesadas=0` en log: otro código) |
| `scripts/ndvi_ingesta_masiva.py:69` | `ndvi = Decimal(str(round(random.uniform(0.2, 0.8), 2)))` | ingestado masivo falso |

`procesar_escena_ndvi` (service_ndvi.py:378) tiene comentario explícito:
*"Implementación simplificada … aquí se simula con valor aleatorio"*.
La docstring confirma la intención original de reemplazarlo por rasterio.

### 2.2 Cobertura histórica inexistente

- `serie_ndvi_comunidad`: 5 fechas, 16,8k comunidades de 21.175.
- `n_escenas` = 1 siempre; `ndvi_percentil` NULL; `pixeles_procesadas` = 0.
- `ndvi_anomalia` ≈ 0 en todas las filas: `calcular_anomalia_ndvi` retorna 0
  cuando no hay línea base (no hay histórico previo).

### 2.3 Cron roto / colgado

- Crontab root: `0 18 * * * cd …/BaseData && venv/bin/python scripts/cron_ndvi_ingest.py >> /var/log/sinb/ndvi_cron.log 2>&1`
- Log `/var/log/sinb/ndvi_cron.log` — últimas líneas:
  ```
  ERROR CRÍTICO: (psycopg2.OperationalError) connection to server … FATAL: the database system is shutting down
  Killed
  ```
- Oct 4: OOM/`Killed` tras caída de Postgres. Oct 5 y 6: dejó filas
  `en_progreso` con 0 y **sin `hora_fin`** (5 filas colgadas hoy).
- Causa raíz: `ingestar_ndvi_comunidades` (service_ndvi.py:471) hace
  **21.175 comunidades × ~50 escenas con N+1 queries** (línea 510: `SELECT
  codigo_ine, lat, lon FROM shared.comunidades` y luego 1 query por comunidad,
  línea 526) sin límite de RAM ni de paralelismo.
- `scripts/cron_ndvi_ingest.py` sólo llama a esa función (líneas 38-40), sin
  `try/finally`, sin lock, sin timeout → filas eternas en `en_progreso`.

### 2.4 Bugs de API (verificados con respuestas HTTP)

| Endpoint | Estado | Causa |
|---|---|---|
| `GET /ndvi/comunidad/{codigo}/evolucion` | **500** | `service_ndvi.py:102` filtra `codigo_comunidad = :…` pero `vw_evolucion_mensual_ndvi` expone **`codigo_ine`** → error de columna |
| `GET /ndvi/alertas?departamento=…&provincia=…&municipio=…` | **siempre 0** | `service_ndvi.py:140-146` filtra en Python con `r.get('departamento')`, pero la vista no tiene esas columnas → todas las filas quedan fuera cuando hay filtro |
| `GET /geojson/mapa-calor?nivel=municipio` | 200 pero ignora `nivel` | `router_ndvi.py:246+` siempre consulta `shared.comunidades` → devuelve 21.175 **Points** (5,9 MB) |
| `GET /geojson/mapa-calor?nivel=comunidad` | **cuelga >20 s** (000) | mismo endpoint, volumen |
| `GET /geojson/bbox` | 200 | OK |
| `/ndvi/comunidad`, `/serie`, `/alertas`, `/procesamiento/log`, `/estadisticas/resumen` | 200 | OK |

---

## 3. Factibilidad — TODAS las mediciones (esto es lo importante)

### 3.1 Fuente de datos

- **EarthSearch STAC**: `POST https://earth-search.aws.element84.com/v1/search`
  - colección `sentinel-2-l2a`
  - assets COG: `red` (B04), `nir` (B08), `scl` (máscara de nubes/suelo)
  - base: `https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/...`
- Paginación: **POST con `limit=100` + `body` del link `rel=next`**
  (keys: `datetime, collections, bbox, limit, next`).
- **`limit=1000` y el filtro `query.eo:cloud_cover` devuelven 502 o 0** →
  el filtro de nubes se hace **client-side**.
- Overviews de los COG: `[2,4,8,16]` → leer @20 m usa el overview 2.

### 3.2 Escenas sobre bbox Bolivia (2025, ventana 10 días)

| Escenario | Escenas |
|---|---|
| Total 2025 (bbox Bolivia) | **36.162** |
| ≤30 % nubes | **15.564** |
| ≤20 % nubes | 13.540 |
| ≤10 % nubes | 10.870 |
| Nubes media | 47,3 % |

- ~114 escenas/día intersectan el bbox.
- **~240 tiles MGRS distintos / 10 días** tocan Bolivia (cobertura completa
  requiere ventana de 10 días).
- Ventana 10 d con ≤50 % nubes: **99–631 tiles** según temporada.

### 3.3 Escenas POR FECHA (medido, 2025) — clave para dimensionar

| Fecha | Escenas en bbox | Tiles | ≤50 % nubes | ≤30 % nubes |
|---|---|---|---|---|
| 15 ene (lluviosa) | 75 | 75 | 45 | 39 |
| 15 abr | 83 | 75 | 33 (30 tiles) | 25 |
| 15 jul (seca) | 153 | 123 | 147 (118 tiles) | 146 |
| 15 dic | 133 | 103 | 50 (46 tiles) | 33 |

→ En temporada lluviosa **un solo día no cubre Bolivia**; se necesita ventana
de 10–15 días (compuesto) para cobertura nacional.

### 3.4 Descarga (red) — medido

| Concepto | Valor |
|---|---|
| B04 completo | 152,8 MB |
| B08 completo | 152,5 MB |
| SCL completo | 0,3 MB |
| **Lectura @20 m (overview)** | B04 7,2 s + B08 4,9 s + SCL 0,8 s ≈ **13 s/escena** |
| Throughput S3 | **6,74 MB/s** (range requests OK, HTTP 206) |
| Estimado bytes/escena @20 m | ~70–80 MB reales |

### 3.5 Cómputo y RAM — medido (lo que mataba al cron)

| Modo | RSS pico | Tiempo/escena |
|---|---|---|
| Todo el tile en memoria | **1.874 MB** ❌ | 22,3 s |
| **Por bloques de 512 filas @20 m** (rasterize 343 labels) | **376–441 MB** ✅ | **18,2–18,3 s** (rasterize 2,6–2,8 s + cálculo 14,3–14,6 s) |
| Lectura ventana parcial @20 m | — | 47 s (más lento que tile completo) |
| Tile completo @20 m | — | 19,5–20 s |

Conclusiones técnicas extraídas:
- **Reproyección obligatoria**: `shared.*.geom` es EPSG:4326 → usar
  `transform_geom` al CRS UTM de la escena antes de `rasterize`; sin eso se
  pintan **0 píxeles**. El bbox STAC viene en lon/lat → `transform_bounds`
  antes de `from_bounds`.
- **SCL es 20 m (5490 px), B04/B08 son 10 m (10980 px)** → SCL se lee con su
  propia `Window(0, y0, W, y1-y0)`, nunca con la ventana 10 m.
- Leer el tile completo vía overviews y recortar en memoria **gana** a leer
  ventana parcial (20 s vs 47 s).
- 10/11 municipios de prueba con NDVI válido (los 1 sin píxeles = agua/nieve).

### 3.6 NDVI real — validado con valores creíbles

| Escena | Media | p10 | p50 | p90 |
|---|---|---|---|---|
| Beni húmedo (feb) | **0,752** | 0,558 | 0,791 | 0,887 |
| Altiplano seco (jun) | **0,137** | — | 0,131 | 0,195 |
| Rango global observado | −0,370 … 0,715 | | | |

**Fórmula**: NDVI = (B08 − B04) / (B08 + B04).

**Máscara SCL — CORRECCIÓN IMPORTANTE**:
- ❌ Lo usado antes: `scl > 4 and scl < 7` → **excluía vegetación (4)** y estaba mal.
- ✅ Correcto: **conservar `[4, 5, 7]`** (vegetación, suelo, sin clasificar);
  excluir `0,1,2,3` (agua/nieve/sombra), `8,9` (nube/nube fina), `10` (cirros),
  `11` (nieve).

### 3.7 Render del degradé (mapa de calor) — medido

- Rampa de colores interpolada + PNG puro (`zlib`, sin PIL) sobre COG local
  4096² float32: **22,2 ms/tile → 45 tiles/s**, PNG medio **39,8 KB**.
- Driver **COG disponible** en GDAL 3.12 (`driver='COG'`).
- Leaflet lo consumiría con `L.tileLayer('/api/v2/ndvi/tiles/{z}/{x}/{y}.png?fecha=…')`.

### 3.8 Espacio en disco — proyecciones

Bolivia ≈ 1.098.561 km².

| Resolución | Píxeles | COG float32 comprimido/fecha | 365 fechas |
|---|---|---|---|
| 20 m | ~2.746 M | ~1 GB | no viable (365 GB) |
| **100 m** | ~110 M | **~250 MB** | 91 GB (aprieta: sólo 103 GB libres) |
| **250 m** | ~17,6 M | **~35 MB** | **12,6 GB** ✅ |
| 500 m | ~4,4 M | ~10 MB | 3,7 GB |

Agregados municipio×fecha (343 filas): ~50 KB → insignificante (12 MB/año).

### 3.9 Tiempos de ingesta

| Tarea | Cálculo | Resultado |
|---|---|---|
| 1 fecha, cobertura Bolivia (~115 escenas) | 115 × 18,2 s | **35 min serie / 18 min con 2 workers** |
| Backfill 1 año (36 compuestos de 10 d) | 36 × 18 min | **~11 h con 2 workers** |
| Backfill 5 años (60 compuestos mensuales) | 60 × 18 min | **~18 h con 2 workers** ← habilita `ndvi_anomalia` real |
| Cron diario delta (sólo tiles nuevos) | ~30 escenas | **~10 min serie / ~4 min con 2 workers, ~1,5 GB** |

**Límite de RAM**: 2 workers × 441 MB = 882 MB (hay 2.381 MB disponibles) ✅.
3 workers = 1,3 GB (posible pero apretado con Postgres+API).

---

## 4. Decisiones del usuario AÚN ABIERTAS (preguntar antes de implementar)

En la última sesión se le presentaron 3 preguntas y respondió
**"solo documenta, no hagas nada"**, así que siguen sin resolverse:

1. **Resolución del mapa NDVI**
   - (a) 250 m, 365 fechas → 12,6 GB — *recomendada*
   - (b) 100 m, sólo 90 días → 22 GB
   - (c) 100 m, 365 fechas → 91 GB
   - (d) 500 m, 5 años → 18 GB
2. **Frecuencia de ingesta y profundidad del backfill**
   - (a) compuestos 10 días + 5 años de mensuales → cron ligero + anomalia real — *recomendada*
   - (b) diario + 1 año
   - (c) sólo backfill, cron parado
   - (d) diario + 5 años
3. **Alcance de la primera tanda**
   - (a) purga + NDVI real + tiles degradé + filtros + fix bugs (todo junto) — *recomendada*
   - (b) sólo NDVI real + purge
   - (c) sólo arreglar bugs

Además conviene confirmar:
4. ¿Mantener `shared.comunidades` fuera del NDVI (usuario ya dijo "solo
   municipio") → ¿renombrar endpoints `/comunidad` a `/municipio` o mantener
   alias por compatibilidad?
5. ¿Borrar también las vistas de comunidad o dejarlas desactivadas?

---

## 5. Arquitectura propuesta (sin implementar)

### 5.1 Modelo de datos nuevo

```sql
-- Series por municipio (reemplaza a serie_ndvi_comunidad como fuente de API)
CREATE TABLE sinb.serie_ndvi_municipio (
    id_municipio    integer NOT NULL REFERENCES shared.municipio(id) ON DELETE CASCADE,
    fecha           date NOT NULL,
    ndvi_promedio   numeric,
    ndvi_min        numeric,
    ndvi_max        numeric,
    ndvi_percentil  numeric,
    pixeles_validos integer,
    cobertura_nubes numeric,
    fuente_escena   text,
    PRIMARY KEY (id_municipio, fecha)
);
-- índice para el filtro por fecha: CREATE INDEX ... ON (fecha);
```

- `sinb.escena_satelital` se conserva (metadatos STAC reales ya cargados).
- `sinb.ndvi_procesamiento_log` se conserva + `try/finally` para `hora_fin`.
- Raster: `data/ndvi/COG/YYYY-MM-DD.tif` (float32, compresión DEFLATE,
  overviews, CRS UTM de la escena o EPSG:4326 georeferenciado).
- Opcional: tabla `sinb.ndvi_tile_cache` sólo si se pre-renderiza (probablemente
  NO: 22 ms/tile justifica render bajo demanda).

### 5.2 Pipeline de ingesta (por escena)

```
1. STAC POST limit=100 + next.body  → lista de features (bbox Bolivia)
2. Filtro client-side: cloud_cover ≤ umbral (30-50%)
3. Para cada escena:
   a. rasterio.open(B04/B08/SCL)  (overviews, window por bloques de 512 filas)
   b. transform_geom(geoms municipios, 4326 → CRS escena)
   c. rasterize labels (343) por bloque → 2,6 s
   d. NDVI = (nir-red)/(nir+red) enmascarado con SCL ∈ {4,5,7}
   e. np.bincount por label → mean/min/max/p75 por municipio
   f. UPSERT en serie_ndvi_municipio
4. Compuesto: promedio de escenas de la ventana para cada municipio
5. COG: np.float32 completo → rasterio.driver='COG' (o GTiff + overview)
6. log: hora_inicio/hora_fin/pixeles_procesadas reales + try/finally
```

### 5.3 API (endpoints nuevos/modificados)

| Endpoint | Qué hace |
|---|---|
| `GET /ndvi/tiles/{z}/{x}/{y}.png?fecha=YYYY-MM-DD` | **render 22 ms/tile** con rampa de degradé; caché por `Cache-Control` |
| `GET /ndvi/municipio?fecha=&departamento=&provincia=&municipio=` | lista con NDVI, filtros **en SQL** (no en Python) |
| `GET /ndvi/municipio/{id}/evolucion?desde=&hasta=` | fix: usar `codigo_ine`/`id_municipio` correcto |
| `GET /ndvi/alertas?departamento=&provincia=&municipio=&fecha=` | fix: JOIN a `shared.municipio/departamento` para filtrar |
| `GET /ndvi/serie?municipio=&desde=&hasta=` | series temporales con rango de fechas |
| `GET /geojson/mapa-calor?nivel=municipio&fecha=&bbox=` | **GeoJSON sólo de municipios** (343), MultiPolygon, con `color` hex |
| `POST /ndvi/ingestar` (admin) | ingesta on-demand con límite de workers |
| `/estadisticas/resumen`, `/procesamiento/log` | se mantienen |

Los filtros **siempre en SQL con JOIN a shared.departamento/provincia/municipio**,
nunca filtrando en Python sobre columnas inexistentes.

### 5.4 Visualización del degradé

- **Principal**: tiles PNG XYZ con rampa interpolada (verdad de píxel).
- **Secundario**: GeoJSON de 343 MultiPolygon con color por municipio
  (para tooltips/tablas/listados).
- Leaflet no existe aún en el repo → si el usuario lo pide, crear
  `static/` + `L.tileLayer`; si no, sólo exponer los endpoints.
- Rampa sugerida: rojo (NDVI ≤ 0,1) → naranja → amarillo → verde (0,4) →
  verde oscuro (≥ 0,8), con interpolación continua (degradé real).

### 5.5 Cron que NO bloquea el servidor

Preferido: **systemd timer** (hoy sólo hay crontab).

`/etc/systemd/system/sinb-ndvi.service`:
```ini
[Service]
Type=oneshot
WorkingDirectory=/home/prosuco/SINAGERSAT/BaseData
ExecStart=/home/prosuco/SINAGERSAT/BaseData/venv/bin/python scripts/cron_ndvi_ingest.py
Nice=19
IOSchedulingClass=idle
CPUWeight=50
IOWeight=50
MemoryMax=1500M
TimeoutStartSec=4h
```
`sinb-ndvi.timer`: `OnCalendar=*-*-01,11,21 *-*-* 03:00:00` (cada 10 días) +
`RandomizedDelaySec=30m` + `Persistent=true`.

Requisitos del script:
- `flock -n /tmp/sinb-ndvi.lock` → nunca dos ejecuciones.
- **2 workers máximo** (no todos los cores; dejar 4 libres para API+Postgres).
- `try/finally` → `hora_fin` siempre; jamás filas `en_progreso` colgadas.
- Checkpoint reanudable (procesar por lotes y marcar escenas hechas).
- `timeout` externo de 4 h.
- **Nunca** correr dentro de los workers de uvicorn.
- Alternativa mínima si no se quiere systemd:
  `nice -n 19 ionice -c3 flock -n /tmp/sinb-ndvi.lock timeout 4h venv/bin/python …`

### 5.6 Purga de datos falsos (ejecutar ANTES de la ingesta real)

```sql
BEGIN;
TRUNCATE sinb.agregado_satelital;          -- 1.618.570 filas / 498 MB aleatorios
TRUNCATE sinb.serie_ndvi_comunidad;        -- 56.155 filas / 5 fechas aleatorias
DELETE FROM sinb.ndvi_procesamiento_log WHERE estado = 'en_progreso';  -- 5 colgadas
COMMIT;
```
Y en código: eliminar `random` de `service_ndvi.py` (líneas 9, 401, 430, 446)
y de `ndvi_ingesta_masiva.py` (línea 69) — dejar de importar `random` del todo.

---

## 6. Plan de implementación por fases (orden recomendado)

**Fase 0 — Purga y saneamiento**
1. Purga SQL (§5.6) + eliminación de `random` del código.
2. Fix de las 5 filas `en_progreso` + `try/finally` en `cron_ndvi_ingest.py`.
3. Verificar con `psql` que quedan 0 filas aleatorias.

**Fase 1 — Motor NDVI real**
4. Nuevo módulo `api/sinb/ndvi_real.py` (o refactor de `service_ndvi.py`):
   query STAC paginado + descarga + cálculo por bloques + rasterize
   `transform_geom` + SCL `[4,5,7]` + agregación por municipio.
5. UPSERT en `sinb.serie_ndvi_municipio` + COG en disco.
6. Prueba con 1 escena y verificar valores creíbles (Beni ≈ 0,75 / Altiplano ≈ 0,14).

**Fase 2 — API**
7. Fix `/evolucion` (columna `codigo_ine`).
8. Fix `/alertas` (filtros SQL con JOIN, no Python).
9. Nuevo `/ndvi/tiles/{z}/{x}/{y}.png?fecha=` (22 ms/tile, rampa degradé).
10. Filtros de fecha/departamento/provincia/municipio en todos los listados.
11. `/geojson/mapa-calor` → sólo municipios MultiPolygon (matar el cuelgue).

**Fase 3 — Ingesta programada**
12. systemd timer + service (§5.5) con 2 workers, lock, checkpoint.
13. Quitar la línea NDVI del crontab de root (o dejarla desactivada).

**Fase 4 — Backfill histórico**
14. Según decisión §4.2 (recomendado: 5 años de mensuales + 10 días recientes).
15. Validar que `ndvi_anomalia` deja de ser 0.

**Fase 5 — Verificación final**
16. Reiniciar API (§9), smoke test de todos los endpoints.
17. `git status` y mostrar diff al usuario (NO commitear sin pedido).

---

## 7. Archivos relevantes

| Ruta | Rol |
|---|---|
| `api/sinb/service_ndvi.py` | Lógica NDVI actual; bugs en 102 y 140-146; simulación en 378-470; ingestión en 471 |
| `api/sinb/router_ndvi.py` | 11 endpoints; `mapa-calor` en 246; `bbox` en 374; `ingestar` en 471 |
| `scripts/cron_ndvi_ingest.py` | Entrada del cron; sin lock/timeout/finally |
| `scripts/ndvi_ingesta_masiva.py` | Ingesta masiva con `random` (línea 69) |
| `scripts/test_ndvi_final.py`, `test_ndvi_simple.py` | pruebas existentes |
| `database/migrations/v2.28.0_ndvi_satelital.sql` | esquema: `escena_satelital`, `agregado_satelital`, `serie_ndvi_comunidad`, vistas, `ndvi_procesamiento_log` |
| `/var/log/sinb/ndvi_cron.log` | log del cron (último: `Killed`) |
| `propuesta/09-SINB-NDVI-SATELITAL.md` | diseño previo (colores hex, GeoJSON) |
| `propuesta/06-FRONTEND.md` | diseño Leaflet previo |
| `/tmp/opencode/` | JWTs de prueba, `scenes_2025.json` (escenas escaneadas), `ndvi_test.tif` (56 MB, raster de prueba), scripts STAC |

---

## 8. Comandos de verificación (reutilizables)

```bash
# JWT de prueba (desde BaseData)
venv/bin/python3 -c "from datetime import timedelta; from api.auth.jwt import create_access_token; \
print(create_access_token({'sub':'1045'}, expires_delta=timedelta(hours=2)))"

# Consulta DB (contraseña en claro, sólo local)
PGPASSWORD=12345678 psql -h 127.0.0.1 -U sinagersat -d db_sinagersat -c "SELECT ..."

# Estado de filas NDVI
PGPASSWORD=12345678 psql -h 127.0.0.1 -U sinagersat -d db_sinagersat -c \
 "SELECT estado, count(*) FROM sinb.ndvi_procesamiento_log GROUP BY estado;"

# Smoke test endpoints (con token)
curl -s -o /dev/null -w "%{http_code}\n" -H "Authorization: Bearer $TOK" \
  http://localhost:8000/api/v2/ndvi/alertas

# Ver 4 workers
systemctl status sinagersat-api | grep -c spawn_main   # debe ser 4
```

**Truco SQL importante**: `:param::tipo` rompe en SQLAlchemy `text()` →
usar `CAST(:param AS tipo)`.

---

## 9. Reinicio de API (siempre así)

```bash
sudo systemctl daemon-reload && sudo systemctl restart sinagersat-api
# esperar ~9 segundos y verificar:
systemctl status sinagersat-api | grep -c spawn_main   # → 4
```

---

## 10. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| RAM (sólo 2,4 GB libres) | 2 workers × 441 MB; `MemoryMax=1500M` en systemd; bloques de 512 filas |
| Ancho de banda (6,74 MB/s) | descarga sólo lo visible con overviews @20 m; compuestos cada 10 d; delta diario |
| Disco (103 GB) | 250 m/365 fechas = 12,6 GB; purgar los 498 MB de agregados falsos primero |
| Cron colgado (ya pasó) | `flock` + `timeout` + `try/finally` + systemd `TimeoutStartSec` |
| Temporada lluviosa sin cobertura | compuestos de 10–15 días, no día único |
| `random` reapareciendo | grep en CI: `grep -rn "random\." api/sinb scripts/*ndvi*` debe dar 0 |
| Reproyección en 0 píxeles | siempre `transform_geom` antes de `rasterize`; asertar `pixeles>0` |
| Máscara SCL mal | conservar SCL ∈ {4,5,7}; teste con escena Beni (esperado ~0,75) |

---

## 11. Qué se hizo en la sesión anterior (NO repetir)

- Diagnóstico completo (§2) — ya hecho, no re-ejecutar.
- Todas las mediciones de §3 — ya hechas, no re-ejecutar salvo para regenerar COGs.
- Instalación en venv de rasterio/numpy/shapely — **ya instalado**, no instalar de nuevo.
- Pregunta de decisiones al usuario (§4) — **pendiente de respuesta**.
- Fix de permisos SINB, 13 CRUD, formatos de imagen — completados antes
  (no relacionado con NDVI; ver `git status`).

**Primer paso al retomar**: preguntar al usuario las 3 decisiones de §4,
luego ejecutar Fase 0 (§6).
