# Paquete de replicación (handoff) — toda la BD y todas las APIs

> **Propósito.** Carpeta general para documentar y replicar **cualquier cambio** del
> proyecto en otro servidor (servidor limpio/clon). Aplica a **toda la base de datos**
> (todos los esquemas: `shared`, `edan`, `rida`, `sinb`, `rea`, `usuarios`, `repositorio`,
> etc.) y a **todas las APIs/módulos** (no solo EDAN ni hogares/censo).
>
> **Cómo usar esta carpeta (convención):** por cada cambio replicable crear/actualizar
> un `.md` con objetivo, decisiones, archivos (nuevos/modificados), migración
> (`database/migrations/` + **espejo** `despliegue/migraciones/`), BD (esquema/tablas/
> columnas), APIs y esquemas (escritura/lectura), pasos de replicación y verificación
> (SQL/curl). Registrar/actualizar su entrada en el **Índice** de abajo. (Ver skill
> `.opencode/skills/documentar-cambios-replicacion/SKILL.md`.)
>
> **Nota:** la carpeta se llamó antes `cambios_hogares_censo2024/` (renombrada a
> `cambios_replicacion/` para reflejar alcance general). El contenido histórico de
> hogares/censo se conserva en §A.

---

## Índice de cambios documentados

| # | Esquema(s) / módulo | Cambio | Documento | Migración | Estado / rama |
|---|---|---|---|---|---|
| A | `shared` / Censo 2024 (hogares) | Hogares oficiales INE (`hogares`, `personas_por_hogar`, `hogares_ine`, `/censo/manzanos/por-nombre`) + análisis NULLs + verificación | §A abajo · [ANALISIS_NULLS.md](ANALISIS_NULLS.md) · [INFORME_CASOS_EXTREMOS_PPH.md](INFORME_CASOS_EXTREMOS_PPH.md) | `v2.17.0_shared_censo2024_hogares.sql` (+ espejo despliegue) | docs+datos base `8a30496` (rama `feature/censo2024-hogares`); artefactos v2.17+script en `56e6ed4`; cambios API/shared originales listados en §A.3.2 |
| B | `edan` / EDAN localidades | `observacion_estado` (motivo de rechazo, 422 al rechazar, conserva anterior, expuesto en lecturas/3 PUT estado + 2 PUT genéricos) | [EDAN_observacion_estado.md](EDAN_observacion_estado.md) | `v2.64.0_edan_localidades_observacion_estado.sql` (+ espejo) | código+migración+doc `8f992f7` (`feature/edan-observacion-estado`, pushed) |
| C | `shared` / Censo 2024 (`por-nombre`) | Cap `personas_por_hogar` > 20 en `GET /censo/manzanos/por-nombre` → promedio oficial del municipio; acceso directo por unidad mantiene valor real (106 casos) | [INFORME_CASOS_EXTREMOS_PPH.md](INFORME_CASOS_EXTREMOS_PPH.md) | — (sin migración) | `e928ff9` + alineación `56e6ed4` (`feature/censo2024-pph-extremos`, pushed) |
| D | `rida` / solicitudes | Shim compat v2.60.0: `POST /revisar|validar|observar|corregir` traducen al motor de 7 niveles/AH (sin reabrir etapas retiradas; `observar` motivo≥10→422, `corregir`→409) | [RIDA_shim_compat_solicitudes_v260.md](RIDA_shim_compat_solicitudes_v260.md) | — (sin migración; usa motor existente) | `c9974fb` (rama `migraciones`, **pusheado**) |
| E | `rida` / ayuda humanitaria (necesidades) | Motor de necesidades v2.61.0 (`regla_necesidad`, `necesidad.fuente/id_regla_necesidad`, endpoints reglas/motor) — alineación documental | [RIDA_motor_necesidades_v261.md](RIDA_motor_necesidades_v261.md) · `PROPUESTA_MOTOR_CALCULO_NECESIDADES.md` (raíz) | **Ya existe**: `v2.61.0_motor_necesidades.sql` + espejo `despliegue/migraciones/` (idempotente; si aplicada se ignora) | rama `migraciones` (doc alineada; API/motor ya en repo) |
| F | `shared` / censo (docs/deps) | Alineación indicadores `por-nombre`/hogares, README script hogares y dependencia `pyarrow>=15` | [SHARED_censo_docs_dependencias.md](SHARED_censo_docs_dependencias.md) | — (v2.17.0 ya existe) | rama `migraciones` |
| G | `repositorio` / documentos | 3ª subida **DOC_PRECEDENTE** (respaldo municipal, `POST /repositorio/documentos`, mismos campos, origen por ruta, `observaciones` libre) + consulta general vista nacional EDAN/RIDA/DOC_PRECEDENTE con filtros geográficos y paginación; editar/eliminar DOC_PRECEDENTE solo dueño y ≤72h (403), no aplica a EDAN/RIDA | [REPOSITORIO_doc_precedente_v265.md](REPOSITORIO_doc_precedente_v265.md) · [mi_repositorio.md](../mi_repositorio.md) (guía de uso) | `v2.65.0_repositorio_origen_doc_precedente.sql` (+ espejo) **aplicada en dev 2026-11-17** | `c1bfbd7` + `438c019` (rama `migraciones`, pushed); **ojo:** el guard dueño/72h quedó fuera de `438c019` (script de edición falló) → se corrigió y verificó en el commit siguiente de esta rama (15 casos en §7.1) |
| H | `motor_ia` / servicio `services.motoria_embeddings` | Worker de embeddings (:8001, 2 workers) con **cache persistente** `EMBEDDINGS_LOCAL_CACHE_DIR` + precarga del modelo ONNX en la instalación + reintento de descarga si `HF_HUB_OFFLINE=1`; reactiva RAG/búsqueda (el servicio estaba caído por modelo en `/tmp`) | [MOTORIA_embeddings_worker.md](MOTORIA_embeddings_worker.md) | — (sin migración) | rama `migraciones` (código + `despliegue/scripts/05_instalar_servicios.sh`); unidad systemd y cache fuera del repo (documentadas). **Pendiente:** proveedor LLM externo en `motor_ia.proveedores_llm` (vacío → `/motor-ia/chat` responde 400/“No hay proveedores externos”) |
| I | `publico` / api `api/publico` | **Grupo de APIs PÚBLICAS de métricas** (solo `/api/v2/publico`, 19 GET sin auth ni filtros): KPIs globales; EDAN por ambito `consolidado|local` con series anuales/mensuales **desde el inicio rellenas en 0**, tipos mas recurrentes, estados, ranking por departamento, sectores (`imp_*`); repositorio por ano/origen/tipo (nunca rutas de archivo); **usuarios solo conteos** (rol/cargo/geografia/totales, sin datos personales); censo 2024 nacional/dpto/prov/municipio con `personas_por_hogar` integer (semantica oficial `hogares_ine`); MotorIA; geo. Todo respaldado en 22 vistas del esquema SQL nuevo `publico` | [PUBLICO_metricas_v266.md](PUBLICO_metricas_v266.md) · [mi_metricas_publicas.md](../mi_metricas_publicas.md) (guia front) | `v2.66.0_publico_metricas.sql` (+ espejo; `DROP VIEW IF EXISTS`+`CREATE VIEW`, aplicada 3x idempotente en dev) | rama `migraciones` (commits de este paquete); dump gemelo regenerado `despliegue/dump/db_sinagersat_20261117_024316.sql` (incluye esquema publico). Verificado 19/19=200, protegidos siguen 401, v1 no expone publico |
| J | `repositorio` (+`publico`) / documentos | `codigo_documento` varchar(64) **no único** = clave de rastreo/expediente de DOC_PRECEDENTE (equivalente a id_edan/id_evento_rida): la 3ª subida lo acepta (normaliza a MAYÚSCULAS) o lo **autogenera** `RES-{codigo_ine}-{YYYY}-{seq}` (secuencia nueva); filtro en `GET /documentos`+`/filtrar`, ruta nueva `GET /documentos/codigo/{código}`, PUT lo reasigna (guard dueño/72h intacto); métrica pública `expedientes` en `v_repo_resumen`. **EDAN/RIDA sin cambios** (código NULL); APIs nuevas **no públicas** | [REPOSITORIO_codigo_documento_v267.md](REPOSITORIO_codigo_documento_v267.md) · [mi_repositorio.md](../mi_repositorio.md) | `v2.67.0_repositorio_codigo_documento.sql` (+ espejo; aplicada 2x idempotente) | rama `migraciones`; verificado end-to-end con agrupación real y limpieza total |
| K | `repositorio` / api | El **mismo** `GET /api/v2/repositorio/documentos` ahora agupa **por defecto** (`modo=agrupado`): un grupo por expediente con `total_documentos` — RIDA por `id_evento_rida` (se mantiene RIDA aunque herede `id_edan`), EDAN por `id_edan`, DOC_PRECEDENTE por `codigo_documento`; `total`=nº de grupos; ; cada grupo incluye `documentos_compartidos`+`comparte_con` (copias idénticas cross-grupo por `hash_sha256` exacto, sin APIs nuevas, siempre activo); **`clave` = código real del grupo (codigo_edan / evento.codigo / codigo_documento; sin ED-/EV-; `etiqueta` eliminada por duplicada)**, filtro `codigo_grupo` y `GET /documentos/codigo/{código:path}` para cualquier tipo; **nueva `GET /documentos/todo`**: las 3 secciones (EDAN/RIDA/DOC_PRECEDENTE) con grupos y documentos anidados, obedeciendo todos los filtros + `limite_documentos` regla **id_edan gana**: el filtro `id_edan` (plano y agrupado, y /filtrar) solo empareja origen EDAN, los RIDA heredados quedan fuera; `/edan/{id}/documentos` intacto; drill-down con `?modo=plano&id_...` o `?modo=plano&codigo_documento=`; `modo=plano` conserva la lista clásica; `/filtrar` y `/buscar` sin cambios | [REPOSITORIO_get_agrupado.md](REPOSITORIO_get_agrupado.md) · [mi_repositorio.md](../mi_repositorio.md) §2 | — (sin migración) | rama `migraciones`; probado con los 4 docs reales (2 EDAN + 2 RIDA) y 2 de ensayo agrupados y luego eliminados; API reiniciada, 4 workers OK |

---

## A. Detalle histórico — Hogares del Censo 2024 (`shared`)

> **Qué es.** Dato oficial de **hogares** del CPV-2024 incorporado al módulo Censo 2024
> (equivalente censal de “familias”; NO se divide población/viviendas). Registro completo
> para replicar en servidor limpio.
>
> Fecha base: **2026-11-14**. Ver también: [ANALISIS_NULLS.md](ANALISIS_NULLS.md) (NULLs) y
> [INFORME_CASOS_EXTREMOS_PPH.md](INFORME_CASOS_EXTREMOS_PPH.md) (ratios extremos por unidad,
> regla `por-nombre`).

### A.1 Decisiones tomadas (cerradas)

1. **Dato = "hogares" del INE** (viviendas particulares ocupadas con personas presentes,
   `viv_tipo_presentes` de la ficha). El CPV-2024 no publica "familias por comunidad".
2. **NO** se divide población/viviendas.
3. **Cobertura oficial**: sin ficha INE → `hogares = NULL` (no estimado). Agregados exponen
   `unidades_con_hogares`.
4. **Municipio = fichas + tabulado INE** (cuadro 19, 343 municipios) en
   `shared.censo2024_hogares_municipio`.
5. **`personas_por_hogar` = redondeo normal** (3,5→4; 3,2→3). En agregados base preferente
   `hogares_ine` (343/343); si no, población cubierta y `hogares` de unidades.
6. **`GET /censo/manzanos/por-nombre`**: agrupado por (municipio, nombre) respetando
   jerarquía `id_departamento → id_provincia → id_municipio` (2.942 grupos, 100% manzanos).
   Exento de paginación (skill `api-get-listados`, regla 3).

### A.2 Fuentes (oficiales, verificables)

| Fuente | URL | Archivo | SHA-256 |
|---|---|---|---|
| Ficha por unidad (52k) | https://github.com/lab-tecnosocial/censosbo/releases/download/data-fichas-v1.0.0/ficha.parquet | `datos/ficha.parquet` | `500637b5bbde…aaeb7d6d3a` |
| Tabulado "Vivienda y hogar" (INE) | https://nube.ine.gob.bo/index.php/s/6H760RRaNemfydX/download | `datos/tabulado_vivienda_hogar.xlsx` | `3a88e42a5657…0f4e7ddac8f2` |

Hogares por unidad = `viv_tipo_presentes` = Σ(`hogar_unipersonal,pareja,monoparental,
nuclear,extendido,compuesto,otro,sinjefe`). Hogares por municipio = cuadro 19, columna 2024.

> Copias en `cambios_replicacion/datos/` (`git add -f`). El cargador busca en
> `cambios_replicacion/datos/` → `datos_censo2024/fuentes/` → descarga.
> `datos/verificacion_microdata_ine.json` = fixture de regresión (§A.7), no dato de carga.

### A.3 Cambios por archivo (lista exacta)

#### A.3.1 Nuevos
| Archivo | Qué contiene |
|---|---|
| `database/migrations/v2.17.0_shared_censo2024_hogares.sql` | Migración idempotente: `hogares` (NULL o ≥0) en `shared.manzanos` y `shared.comunidades` (+ COMMENT) y tabla `shared.censo2024_hogares_municipio (id_municipio PK/FK → shared.municipio, hogares NOT NULL ≥0, fuente, actualizado_en)` |
| `despliegue/migraciones/v2.17.0_shared_censo2024_hogares.sql` | **Copia textual** (obligatoria para `actualizar.sh`) |
| `scripts/cargar_hogares_censo2024.py` | Cargador `--simular`/`--importar`, idempotente, Fase A (pyarrow) y B (openpyxl), cruce/cobertura |
| `cambios_replicacion/INSTRUCCIONES.md` | Este índice/paquete |
| `cambios_replicacion/ANALISIS_NULLS.md` | Análisis de NULLs de `hogares` |
| `cambios_replicacion/INFORME_CASOS_EXTREMOS_PPH.md` | 106 unidades ratio >20 y regla `por-nombre` (promedio municipal) |
| `cambios_replicacion/EDAN_observacion_estado.md` | Cambio EDAN v2.64.0 |
| `cambios_replicacion/datos/*` | Fuentes + fixture verificación (`git add -f`) |

#### A.3.2 Modificados (solo se agregan campos/resúmenes; nada se elimina)
| Archivo | Qué cambió |
|---|---|
| `requirements.txt` | + `pyarrow>=15` |
| `api/shared/schemas.py` | `_UnidadCensoBase`/Create/Update: +`hogares`; responses: +`personas_por_hogar`; resúmenes: +`hogares,unidades_con_hogares,hogares_ine,personas_por_hogar`; **nuevo** `ManzanosPorNombreResponse` |
| `api/shared/service.py` | CRUD/queries/GeoJSON con `hogares` y `personas_por_hogar` (redondeo normal); resúmenes con `hogares_ine`; `get_manzanos_por_nombre()` + `_personas_por_hogar()` (+ cap >20 → promedio municipal en `por-nombre`) |
| `api/shared/router.py` | summaries/docstrings y **nuevo** `GET /censo/manzanos/por-nombre` |
| `DOCUMENTACION_SINB.md`, `docs/04-indicadores-y-reportes.md`, `docs/manual/06-indicadores.md`, `README.md`, `datos_censo2024/documentacion/README_censo2024.md` | Campos/endpoints/fuentes v2.17.0 y nota extremos |

### A.4 Replicación en servidor limpio
```bash
# 0) Prerrequisitos: migraciones previas (hasta v2.16.0) y shared.manzanos/comunidades cargadas.
# 1) Código + datos (este paquete/rama).
git pull
pip install -r requirements.txt   # incluye pyarrow
# 2) Fuentes: en cambios_replicacion/datos/ o dejar que el script las descargue.
# 3) Migración (idempotente)
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f database/migrations/v2.17.0_shared_censo2024_hogares.sql
#    (o despliegue/scripts/actualizar.sh)
# 4) Carga y verificación
python3 scripts/cargar_hogares_censo2024.py            # --simular
python3 scripts/cargar_hogares_censo2024.py --importar
# 5) Reiniciar API si aplica: ./stop.sh && ./start_api.sh
```

### A.5 Verificación rápida
```sql
SELECT count(*) FROM shared.censo2024_hogares_municipio; -- 343
SELECT sum(hogares) FROM shared.censo2024_hogares_municipio; -- 3623711
SELECT count(*) FROM shared.manzanos WHERE hogares IS NOT NULL; -- 134386
SELECT count(*) FROM shared.comunidades WHERE hogares IS NOT NULL; -- 16344
```
API: `GET /manzanos?limit=1` → `hogares`/`personas_por_hogar`; `GET /censo/poblacion/nacional` → `hogares_ine:3623711`, `personas_por_hogar:3`; `GET /censo/manzanos/por-nombre?id_municipio=20101` → 20 grupos, "NUESTRA SEÑORA DE LA PAZ" manzanos 8444, hogares 199674, `personas_por_hogar: 2`.

### A.6 Notas
- `hogares=NULL` ≠ 0 (sin ficha; ver [ANALISIS_NULLS.md](ANALISIS_NULLS.md)). `hogares` (suma unidades) vs `hogares_ine` (tabulado, exacto) — ratios usan `hogares_ine`.
- **Extremos >20 por unidad** (viviendas colectivas): valor real en acceso directo/listado; en `por-nombre` se reemplaza por promedio municipal — ver [INFORME_CASOS_EXTREMOS_PPH.md](INFORME_CASOS_EXTREMOS_PPH.md).
- Cobertura fichas 91,7%. Tabulado: se lee columna 2024 (cuadro 19); el script aborta si no cuadra (343 y suma = total Bolivia).
- Migraciones en doble ubicación (`database/migrations/` y `despliegue/migraciones/`). `por-nombre` exento de paginación.

### A.7 Verificación cruzada (resumen)
Microdata INE (413 MB, sha verificado) = 343/343 hogares/viviendas/población exactos vs BD; tabulado cuadro 19 = cuadro 6 (343/343) y reproduce promedio 3,0725767. Discrepancias documentadas: D1 (NULLs, reserva estadística, ver ANALISIS_NULLS.md), D2 (numerador incluye colectivos/calle → difiere ±1 en 28/343; nacional redondea igual), D3–D6 según registro original. Fixture: `datos/verificacion_microdata_ine.json`.

---

*Última alineación de este índice: 2026-11-17 (añade K: GET general del repositorio agrupado por expediente con modo=agrupado default; previa J: codigo_documento/expedientes v2.67.0; pendiente proveedor LLM externo).*
