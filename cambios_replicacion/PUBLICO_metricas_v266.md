# PUBLICO — Grupo de APIs públicas de métricas para el dashboard (v2.66.0)

> **Contexto:** esquema BD nuevo `publico` (vistas) + módulo API nuevo
> `api/publico` montado **solo en v2**. Rama `migraciones`. Fecha: 2026-11-17.
> Servidor gemelo: aplicar TODO este documento; nada más existe.

## 1. Objetivo y decisiones

Dar a la **página principal** (frontend público) endpoints GET de métricas
agregadas, **sin autenticación y sin filtros**, con series anuales/mensuales
**completas desde el primer dato (huecos rellenos en 0)**, diferenciando
explícitamente **EDAN consolidado (padre)** de **EDAN local (localidades)**.

Decisiones cerradas con el usuario:
- **Solo `/api/v2/publico`** (no existe alias v1; `/api/v1/publico/*` devuelve 404).
- **Sin k-anonimato**: usuarios se muestra **todo, pero solo cantidades** (por rol,
  cargo, departamento/provincia/municipio y totales). Prohibido exponer datos
  personales.
- Repositorio: métricas por origen y tipo; **nunca** `path_archivo`/`nombre_original`.
- **Caché** en memoria por endpoint: `PUBLICO_CACHE_TTL` segundos, default **60**
  (0 desactiva). Por proceso uvicorn (4 workers → hasta 4 queries por ventana;
  aceptable).
- Todo el SQL de agregación vive en **vistas del esquema `publico`** creadas por la
  migración `v2.66.0` (decision del usuario: "con migración debe respaldarse"), para
  que el gemelo obtenga la misma semántica aunque su código tardara en llegar.
- El cambio NO toca ningún router/endpoint existente.

## 2. Archivos

### 2.1 Nuevos
| Ruta | Contenido |
|---|---|
| `database/migrations/v2.66.0_publico_metricas.sql` | `CREATE SCHEMA IF NOT EXISTS publico` + 22 vistas (`DROP VIEW IF EXISTS` + `CREATE VIEW`, idempotente) + `COMMENT ON SCHEMA`. |
| `despliegue/migraciones/v2.66.0_publico_metricas.sql` | **Espejo textual idéntico** (verificado `diff -q` OK). |
| `api/publico/__init__.py` | Paquete. |
| `api/publico/service.py` | Lectura de vistas con caché TTL (`_cached`, `_rows`); una función por métrica. |
| `api/publico/router.py` | `APIRouter(prefix="/publico")`, 19 endpoints GET, tag `Público > Métricas`, sin auth. |
| `cambios_replicacion/PUBLICO_metricas_v266.md` | Este documento. |
| `mi_metricas_publicas.md` (raíz) | Guía de consumo para el frontend (curls listos). |

### 2.2 Modificados
| Ruta | Qué cambió |
|---|---|
| `api/main.py` | +`from .publico.router import router as publico_router` (tras el import de `motor_ia`); +entrada `("publico", publico_router)` **solo en `V2_ROUTERS`** (última, tras `motor_ia`). V1 sin cambios. |
| `cambios_replicacion/INSTRUCCIONES.md` | Fila I del índice + footer. |
| `.opencode/skills/documentar-cambios-replicacion/SKILL.md` | Skill ampliada (plantilla gemelo con detalle de APIs/vistas/env/systemd). Sin impacto en runtime. |

### 2.3 Fuera del repo (estado del servidor)
- `despliegue/dump/db_sinagersat_20261117_024316.sql` (408 MB) — dump regenerado
  tras aplicar v2.66.0; **contiene** `CREATE SCHEMA publico;` y las 22 vistas
  (`grep -c "publico\." = 22`). Es el paquete de respaldo que viaja al gemelo.

## 3. Migración

- Archivo: `database/migrations/v2.66.0_publico_metricas.sql`
- Espejo: `despliegue/migraciones/v2.66.0_publico_metricas.sql` (idéntico).
- Idempotencia: `CREATE SCHEMA IF NOT EXISTS` + `DROP VIEW IF EXISTS`/`CREATE VIEW`
  envueltos en `BEGIN; ... COMMIT;`. **Probado en dev: aplicada 3 veces seguidas sin
  error** (la 1ª creó; las siguientes re-crearon).
- Aplicar:
  ```bash
  psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f database/migrations/v2.66.0_publico_metricas.sql
  # o: bash despliegue/scripts/actualizar.sh   (usa el espejo de despliegue/migraciones/)
  ```
- Orden: no depende de otras nuevas; requiere que existan los esquemas de origen
  (`edan`, `shared`, `repositorio`, `usuarios`, `motor_ia`) — el gemelo ya los tiene
  (hasta v2.65.0).
- Salida de éxito: `IDEMPOTENT OK v2.66.0 vistas publico metricas`.

## 4. BD — esquema `publico` (22 vistas y sus columnas exactas)

Convenciones: `ambito` = `'consolidado'` (`edan.edan`, padre) | `'local'`
(`edan.edan_localidades`). Todos los conteos EDAN excluyen
`pendiente_eliminacion = TRUE`. En censo, `personas_por_hogar` es **integer** y usa
la misma semántica que `api/shared/service.py`: base oficial `hogares_ine`
(tabulado INE, tabla `shared.censo2024_hogares_municipio`), fallback
`poblacion_con_hogares/hogares` de unidades; redondeo normal
`div(2*p + b, 2*b)` (3,5→4).

| Vista | Columnas (en orden) | Fuente/semántica |
|---|---|---|
| `publico.v_edan_resumen` | ambito, total, con_fecha, sin_fecha, primer_evento, ultimo_evento, poblacion_afectada, familias_afectadas, familias_damnificadas | 2 filas (consolidado/local); `sin_fecha` = `fecha_evento IS NULL` (hoy 6 locales). |
| `publico.v_edan_serie_anios` | ambito, anio, total | `generate_series` del año mínimo al actual, relleno 0. |
| `publico.v_edan_serie_anios_tipo` | ambito, anio, id_tipo_evento, tipo, total | idem por tipo (`edan.tipo_evento`), solo tipos con historial. |
| `publico.v_edan_serie_meses` | ambito, mes, total | mes = `YYYY-MM` (`date_trunc`), serie continua hasta el mes actual. |
| `publico.v_edan_tipos_evento` | ambito, tipo, total | histórico total, `ORDER BY total DESC`. |
| `publico.v_edan_estados` | ambito, orden, estado, total | consolidado→`edan.estado_edan` (1-4); local→`edan.edan_localidades_estado` (1-6). |
| `publico.v_edan_departamentos` | ambito, id_departamento, departamento, eventos, poblacion_afectada | ranking `ORDER BY eventos DESC` (top 15 por ambito en la API). |
| `publico.v_edan_sectores` | sector, total | UNPIVOT de los 14 flags `imp_*` de `edan.edan_localidades`. |
| `publico.v_repo_serie_anios` | origen, anio, total | docs `activo=TRUE`; año de `coalesce(fecha_documento, fecha_subida)`; relleno 0. |
| `publico.v_repo_serie_anios_tipo` | id_tipo_documento, tipo, anio, total | idem por tipo (solo tipos con historial). |
| `publico.v_repo_resumen` | dimension, llave, total | long: `total/documentos_activos`, `origen/*`, `tipo/<nombre>`, `firma/con_firma|sin_firma`. |
| `publico.v_usuarios_rol` | rol, cantidad | `usuarios.rol` LEFT JOIN usuarios **activos** (incluye roles con 0). |
| `publico.v_usuarios_cargo` | cargo, cantidad | `coalesce(nullif(trim(cargo),''),'sin_especificar')`, activos. |
| `publico.v_usuarios_geografia` | nivel, id, nombre, cantidad | niveles `departamento|provincia|municipio`, activos con geo asignada. |
| `publico.v_usuarios_resumen` | llave, cantidad | `total`, `activos`, `inactivos`, `con_municipio`. |
| `publico.v_motoria_resumen` | llave, cantidad | `documentos`, `chunks`, `proveedores_llm`, `uso_llm(_exitoso)`, `uso_embeddings(_exitoso)`. |
| `publico.v_geo_resumen` | llave, cantidad | `departamentos/provincias/municipios/manzanos/comunidades`. |
| `publico.v_censo_nacional` | nivel, id_departamento, id_provincia, id_municipio, codigo_ine, nombre, poblacion, viviendas, hogares, unidades_con_hogares, hogares_ine, personas_por_hogar | 1 fila nacional; suma manzanos+comunidades; pph con `hogares_ine` (NULL si no hay). |
| `publico.v_censo_departamentos` | idem | 9 filas, agrupado por `id_departamento` de manzanos+comunidades; `hogares_ine` suma municipios del dpto. |
| `publico.v_censo_provincias` | idem | 113 filas, por `id_provincia`. |
| `publico.v_censo_municipios` | idem | 343 filas; `hogares_ine` = `shared.censo2024_hogares_municipio.hogares`. |
| `publico.v_kpis_globales` | edan_consolidado_total, edan_local_total, edan_poblacion_afectada, edan_local_aprobados, edan_departamentos_afectados, edan_primera_fecha, edan_ultima_fecha, repo_documentos, repo_doc_precedentes, usuarios_activos, geo_departamentos, geo_provincias, geo_municipios, geo_manzanos, geo_comunidades, censo_poblacion, censo_hogares_ine, motoria_documentos, motoria_chunks | 1 fila con subconsultas. `edan_local_aprobados` = estados 3 y 5. |

## 5. APIs (19 endpoints, todos `GET`, **sin auth**, **sin parámetros**)

Prefijo: `/api/v2/publico`. Envelope: `{"success": true, "message": "...",
"data": ..., "total": N}` (listas traen `total = len(data)`; `/resumen` y
`/usuarios/resumen` devuelven `data` objeto con `total: null`). Tag OpenAPI:
**`Público > Métricas`**. Sin autenticación; `AuditMiddleware` NO registra GET
(solo muta en POST/PUT/PATCH/DELETE), así que no ensucia `usuarios.auditoria`.

| # | Método y ruta | data (forma) |
|---|---|---|
| 1 | `GET /api/v2/publico/resumen` | objeto con las 19 columnas de `v_kpis_globales` |
| 2 | `GET /api/v2/publico/edan/resumen` | lista `[{ambito, total, con_fecha, sin_fecha, primer_evento, ultimo_evento, poblacion_afectada, familias_afectadas, familias_damnificadas}]` |
| 3 | `GET /api/v2/publico/edan/serie-anios` | `[{ambito, anio, total}]` |
| 4 | `GET /api/v2/publico/edan/serie-anios-por-tipo` | `[{ambito, anio, id_tipo_evento, tipo, total}]` |
| 5 | `GET /api/v2/publico/edan/serie-meses` | `[{ambito, mes:"YYYY-MM", total}]` |
| 6 | `GET /api/v2/publico/edan/tipos-evento` | `[{ambito, tipo, total}]` DESC |
| 7 | `GET /api/v2/publico/edan/estados` | `[{ambito, orden, estado, total}]` |
| 8 | `GET /api/v2/publico/edan/departamentos` | `[{ambito, id_departamento, departamento, eventos, poblacion_afectada}]` top 15 por ambito |
| 9 | `GET /api/v2/publico/edan/sectores` | `[{sector, total}]` (ámbito local) |
| 10 | `GET /api/v2/publico/repositorio/serie-anios` | `[{origen, anio, total}]` |
| 11 | `GET /api/v2/publico/repositorio/serie-anios-por-tipo` | `[{id_tipo_documento, tipo, anio, total}]` |
| 12 | `GET /api/v2/publico/repositorio/resumen` | `[{dimension, llave, total}]` |
| 13 | `GET /api/v2/publico/usuarios/resumen` | objeto `{totales:[{llave,cantidad}], por_rol:[{rol,cantidad}], por_cargo:[{cargo,cantidad}], por_geografia:[{nivel,id,nombre,cantidad}]}` |
| 14 | `GET /api/v2/publico/motor-ia/resumen` | `[{llave, cantidad}]` |
| 15 | `GET /api/v2/publico/geo/resumen` | `[{llave, cantidad}]` |
| 16 | `GET /api/v2/publico/censo/nacional` | `[{nivel, ..., personas_por_hogar}]` (1 fila) |
| 17 | `GET /api/v2/publico/censo/departamentos` | 9 filas |
| 18 | `GET /api/v2/publico/censo/provincias` | 113 filas |
| 19 | `GET /api/v2/publico/censo/municipios` | 343 filas |

Ejemplo real (dev 2026-11-17):
```json
GET /api/v2/publico/edan/serie-anios
{"success":true,"message":"Serie anual EDAN",
 "data":[{"ambito":"consolidado","anio":2026,"total":7},
         {"ambito":"local","anio":2026,"total":137}],"total":2}

GET /api/v2/publico/censo/municipios (fragmento)
{"codigo_ine":"070101","nombre":"Santa Cruz de la Sierra","poblacion":1610982,
 "hogares_ine":453158,"personas_por_hogar":4}   // pph es NUMERO, no string

GET /api/v2/publico/resumen (fragmento)
{"edan_consolidado_total":7,"edan_local_total":143,"edan_local_aprobados":27,
 "repo_documentos":4,"usuarios_activos":518,"censo_poblacion":11365333,
 "censo_hogares_ine":3623711, "motoria_documentos":0}
```

**Otros endpoints ya públicos que la página puede seguir usando** (no creados
aquí; se listan para completar el dashboard): `/api/v2/shared/departamentos|provincias|municipios|manzanos|comunidades` (+ `*/geojson` y `/municipios/geojson`), `/api/v2/shared/censo/poblacion/{nacional,departamentos,provincias,municipios}` y `/censo/manzanos/por-nombre`, `/api/v2/motor-ia/busqueda` y `/api/v2/motor-ia/documentos` (GET), `/health`, estáticos `/uploads/...`.

## 6. Config / entorno / servicios
- `requirements.txt`: **sin cambios**.
- `.env`: **sin cambios obligatorios**. Opcional: `PUBLICO_CACHE_TTL` (int segundos;
  si ausente = 60; `0` = sin caché).
- systemd: **ninguna unidad nueva**. El API (servicio `sinagersat-api` o
  `./start_api.sh` con **4 workers**) ya sirve `/api/v2/publico`; la caché es por
  worker. El worker de embeddings (`motoria-embeddings`, `:8001`) es independiente.
- CORS: ya permite `*` (`api/main.py`, `allow_origins=["*"]`) — el dashboard puede
  llamar desde cualquier dominio.

## 7. Replicación en el gemelo (orden exacto)

```bash
# 0) Respaldo de seguridad ANTES de tocar nada
cd /ruta/al/BaseData
bash despliegue/scripts/generar_dump.sh        # deja despliegue/dump/db_sinagersat_<ts>.sql

# 1) Código (rama migraciones, commits de este cambio)
git fetch origin && git pull origin migraciones

# 2) Migración (idempotente; puede llevarse del espejo si el repo no está sync)
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f database/migrations/v2.66.0_publico_metricas.sql
#    esperado: "IDEMPOTENT OK v2.66.0 vistas publico metricas"

# 3) Dependencias y servicios (sin cambios nuevas; solo reinicio)
./stop.sh && ./start_api.sh                    # o systemctl restart sinagersat-api

# 4) (Opcional) usar el dump gemelo en vez de aplicar la migración suelta:
#    el dump 20261117 ya trae el esquema publico; ver despliegue/scripts/02_restaurar_bd.sh
```

## 8. Verificación (esperada en gemelo; resultados reales de dev 2026-11-17)

```sql
SELECT count(*) FROM information_schema.views
 WHERE table_schema='publico';                       -- esperado 22
SELECT data_type FROM information_schema.columns
 WHERE table_schema='publico' AND table_name='v_censo_municipios'
   AND column_name='personas_por_hogar';             -- esperado integer
SELECT * FROM publico.v_edan_serie_anios ORDER BY ambito, anio;
SELECT * FROM publico.v_kpis_globales;               -- 1 fila
```

```bash
for r in resumen edan/resumen edan/serie-anios edan/serie-anios-por-tipo \
  edan/serie-meses edan/tipos-evento edan/estados edan/departamentos edan/sectores \
  repositorio/serie-anios repositorio/serie-anios-por-tipo repositorio/resumen \
  usuarios/resumen motor-ia/resumen geo/resumen \
  censo/nacional censo/departamentos censo/provincias censo/municipios; do
  curl -s -o /dev/null -w "%{http_code} $r\n" "http://localhost:8000/api/v2/publico/$r"
done                                            # esperado: 200 en las 19
curl -s http://localhost:8000/api/v1/publico/resumen -o /dev/null -w "%{http_code}\n"   # esperado 404 (solo v2)
curl -s http://localhost:8000/api/v2/edan/localidades -o /dev/null -w "%{http_code}\n"  # esperado 401 (protegido intacto)
curl -s http://localhost:8000/api/v2/repositorio/documentos -o /dev/null -w "%{http_code}\n" # 401
curl -s "http://localhost:8000/api/v2/usuarios/" -o /dev/null -w "%{http_code}\n"       # 401
```

**Resultados observados en dev (línea base):** 19/19 `200`; conteos locales:
`edan/serie-anios` → consolidado 2026=7, local 2026=137 (+6 sin fecha en
`edan/resumen`); `edan/tipos-evento` local top: Granizadas=21, Heladas=19,
Inundaciones=17; `geo/resumen` → 9/113/343/…; `censo/nacional` →
`poblacion=11365333, hogares_ine=3623711, personas_por_hogar=3`; municipio
070101 pph=**4** (número); `usuarios/resumen` → activos 518 (Responsable Local 215,
UGR Municipio 194, Observador local 77…); `motor-ia/resumen` → documentos 0,
uso_embeddings 3/exitosas 3. Repetición de llamada cacheada: 137 ms → 25 ms.
`/api/v2/publico` **no** aparece en v1 (`404`).

## 9. Notas / pendientes / rollback
- **Pendiente público**: DOC_PRECEDENTE aún sin datos (0 docs en dev); su fila
  aparecerá en `repositorio/serie-anios` cuando existan documentos.
- Las vistas reflejan SOLO datos no borrados lógicamente; MotorIA depende de que
  haya documentos indexados (hoy 0 en dev).
- El proveedor LLM externo sigue **PENDIENTE de alta** en el gemelo
  (`motor_ia.proveedores_llm` vacío) — ver `MOTORIA_embeddings_worker.md` §8.
- Rollback: `DROP SCHEMA publico CASCADE;` y quitar las 2 líneas de `api/main.py`
  + borrar `api/publico/` (o `git revert` del commit). No hay datos que restaurar
  (solo vistas).
- Correcciones durante la implementación (para que el gemelo valide contra el
  estado FINAL): (a) la 1ª versión de la migración usó `CREATE OR REPLACE VIEW`,
  que no permite cambiar tipos → se cambió a `DROP VIEW IF EXISTS + CREATE VIEW`;
  (b) `div()` devolvía `numeric` y JSON daba `"4"` string → se casteó
  `::int` (`personas_por_hogar integer`); ambas correcciones ya están en el
  archivo versionado y aplicadas en dev.
