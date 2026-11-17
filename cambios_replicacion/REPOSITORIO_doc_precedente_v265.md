# REPOSITORIO — Tercera subida (DOC_PRECEDENTE) y consulta general (v2.65.0)

> **Esquema/módulo:** `repositorio` / documentos PDF (`api/repositorio`).  
> **Migración:** `v2.65.0_repositorio_origen_doc_precedente.sql` + **espejo** `despliegue/migraciones/v2.65.0_repositorio_origen_doc_precedente.sql` (idempotente).  
> **Rama/commit:** `migraciones`.

## 1. Objetivo
Agregar una **tercera vía de subida** de documentos (respaldo **municipal**, fuera de EDAN/RIDA) sin modificar los contratos EDAN/RIDA en producción, y una **consulta general** de vista **nacional** (mezcla EDAN + RIDA + DOC_PRECEDENTE) con filtros geográficos.

- **Subida = municipal** (documento vinculado a `id_departamento/provincia/municipio`).
- **Consulta = vista nacional** (todos los orígenes, filtrable por departamento/provincia/municipio, etc.).
- **Origen asignado automáticamente por la URL/ruta** de subida (no lo envía el cliente).

## 2. Origen (etiqueta por ruta)

| Ruta POST | Origen | Vínculo |
|---|---|---|
| `POST /api/v2/repositorio/edan/{id_edan}/documentos` (existente, **sin cambios**) | `EDAN` | `id_edan` |
| `POST /api/v2/repositorio/rida/eventos/{id_evento_rida}/documentos` (existente, **sin cambios**) | `RIDA` | `id_evento_rida` + `id_edan` heredado |
| `POST /api/v2/repositorio/documentos` (**nueva**) | `DOC_PRECEDENTE` | sin `id_edan`/`id_evento_rida` (respaldo municipal) |

## 3. Base de datos
`repositorio.documentos`:
- Nueva columna explícita `origen varchar(20) NOT NULL DEFAULT 'EDAN'` con CHECK `('EDAN','RIDA','DOC_PRECEDENTE')`.
- Backfill desde estado actual: `id_evento_rida NOT NULL -> RIDA`, resto -> `EDAN` (idempotente, solo donde `origen IS NULL`).
- Constraint de consistencia `chk_documentos_origen_vinculos`: `RIDA` exige `id_evento_rida NOT NULL`; `EDAN` exige `id_evento_rida IS NULL`; `DOC_PRECEDENTE` exige `id_edan IS NULL` y `id_evento_rida IS NULL`.
- Índices: `idx_documentos_origen`, `idx_documentos_id_municipio`, `idx_documentos_fecha_documento`.
- Filas/contratos EDAN y RIDA existentes **no se modifican**.

## 4. API

### 4.1 Subidas (mismos campos multipart)
Campos comunes: `file` (PDF, máx 50MB, validación MIME/extensión + firma AGETIC ≤20MB), `id_tipo_documento`, `id_departamento`, `id_provincia`, `id_municipio`, `fecha_documento` (YYYY-MM-DD), `nombre_documento`, `observaciones` (**texto libre, opcional**).

- **EDAN (sin cambios):** `POST /api/v2/repositorio/edan/{id_edan}/documentos` → `origen=EDAN`.
- **RIDA (sin cambios):** `POST /api/v2/repositorio/rida/eventos/{id_evento_rida}/documentos` → `origen=RIDA`.
- **DOC_PRECEDENTE (nueva):** `POST /api/v2/repositorio/documentos` → `origen=DOC_PRECEDENTE`, `id_edan/id_evento_rida` NULL, vinculado al municipio del form y a `id_usuario_subio` (usuario autenticado). Subcarpeta: `uploads/repositorio/municipal/{id_municipio}/...`

Respuesta: `SuccessResponse` con `data` = documento (incluye `origen`, `id_edan`, `id_evento_rida`, geo, `id_usuario_subio`, firma).

### 4.2 Consulta general (vista nacional)
`GET /api/v2/repositorio/documentos` — listado dinámico (EDAN + RIDA + DOC_PRECEDENTE).

- Orden: más recientes primero (`fecha_documento DESC NULLS LAST, fecha_subida DESC`).
- Parámetros: `limit` (default 50, 1..200), `skip` (≥0), `todos` (bool, ignora limit/skip).
- Filtros: `origen` (EDAN|RIDA|DOC_PRECEDENTE), `id_departamento`, `id_provincia`, `id_municipio`, `id_edan`, `id_evento_rida`, `id_tipo_documento`, `id_usuario_subio`, `fecha_desde`/`fecha_hasta` (YYYY-MM-DD, sobre `fecha_documento`), `q` (ILIKE nombre_documento/nombre_original), `tiene_firma_digital`, `include_inactive`.
- Respuesta: `SuccessResponse(message, data, total)` con `total` **sin paginar** y mismos filtros.

Compatibilidad: `GET /repositorio/documentos/filtrar` y `GET /repositorio/documentos/buscar` mantienen contrato y ahora incluyen `DOC_PRECEDENTE`, aceptan `origen` extendido, filtros adicionales y devuelven `total` correcto. Listados por EDAN/evento RIDA sin cambios funcionales.

## 5. Archivos (nuevos/modificados)

| Archivo | Cambio |
|---|---|
| `database/migrations/v2.65.0_repositorio_origen_doc_precedente.sql` | **Nuevo**: columna `origen`, backfill, checks, índices, comentarios. |
| `despliegue/migraciones/v2.65.0_repositorio_origen_doc_precedente.sql` | **Espejo**. |
| `api/repositorio/service.py` | `origen` explícito (fallback), `upload_documento` con `origen`, filtros unificados (incl. `origen`, `id_usuario_subio`, `tiene_firma_digital`, `q`), `list/buscar/filtrar` con paginación y `total` correcto. |
| `api/repositorio/router.py` | `POST /documentos` (DOC_PRECEDENTE, mismos campos, etiqueta por ruta), `GET /documentos` general (skill), origen automático EDAN/RIDA preservado, filtros/compat extendidos, `observaciones` texto libre. Restricción dueño/72 h: helper `_validar_permiso_doc_precedente()` + llamadas en `PUT`, `DELETE` y `DELETE /hard` (403 si no cumple; no aplica a EDAN/RIDA). |
| `api/repositorio/schemas.py` | `DocumentoResponse.origen` documentado (EDAN|RIDA|DOC_PRECEDENTE), `observaciones` texto libre. |

## 6. Replicación

> **Orden obligatorio:** aplicar la migración **antes** de reiniciar la API con este
> código. El SQL nuevo lee `d.origen`; sin la columna, el listado_general devuelve 500
> (y si el proceso sigue corriendo código viejo, `GET /repositorio/documentos`
> responde 404). Situación detectada en dev el 2026-11-17: migración sin aplicar +
> proceso antiguo → 404; tras aplicar `v2.65.0` y reiniciar (`./stop.sh &&
> ./start_api.sh`), todo OK.

```bash
# 1) Código
git pull
# 2) Migración (idempotente, segura si ya aplicada)
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f database/migrations/v2.65.0_repositorio_origen_doc_precedente.sql
# (o despliegue/scripts/actualizar.sh)
# 3) Reiniciar API (verificar que todos los workers carguen el código nuevo)
./stop.sh && ./start_api.sh
```

## 7. Verificación

```sql
-- columna/constraint
SELECT column_name FROM information_schema.columns
 WHERE table_schema='repositorio' AND table_name='documentos' AND column_name='origen';
SELECT conname FROM pg_constraint
 WHERE conrelid='repositorio.documentos'::regclass AND conname IN ('chk_documentos_origen','chk_documentos_origen_vinculos');
-- backfill coherente
SELECT origen, count(*) FROM repositorio.documentos GROUP BY origen;
```

```bash
# 1) Subida DOC_PRECEDENTE (mismos campos; geo del municipio)
curl -X POST "$API/api/v2/repositorio/documentos" -H "Authorization: Bearer $TOKEN" \
  -F "file=@doc.pdf" -F "id_tipo_documento=1" \
  -F "id_departamento=2" -F "id_provincia=201" -F "id_municipio=20101" \
  -F "fecha_documento=2026-11-15" -F "nombre_documento=Convenio" -F "observaciones=Texto libre"

# 2) Consulta general (vista nacional) con filtros geo/origen y paginación
curl -H "Authorization: Bearer $TOKEN" "$API/api/v2/repositorio/documentos?limit=20&skip=0"
curl -H "Authorization: Bearer $TOKEN" "$API/api/v2/repositorio/documentos?origen=DOC_PRECEDENTE&id_municipio=20101&limit=50"
curl -H "Authorization: Bearer $TOKEN" "$API/api/v2/repositorio/documentos?id_departamento=2&todos=true"
curl -H "Authorization: Bearer $TOKEN" "$API/api/v2/repositorio/documentos?q=convenio&id_municipio=20101&limit=20"

# 3) EDAN/RIDA sin cambio de contrato
# POST /repositorio/edan/{id_edan}/documentos  y  POST /repositorio/rida/eventos/{id_evento_rida}/documentos

# 4) Restricción DOC_PRECEDENTE (duelo + 72 h) sobre PUT/DELETE/DELETE-hard
```

### 7.1 Resultados reales (dev 2026-11-17, tras aplicar v2.65.0 y reiniciar; 4 workers)

Preparación: admin `admin` (rol 1, sin geo = nacional) y usuario municipal `7051296`
(id_usuario 30, rol 7 Responsable Local, dep 7 / prov 701 / mun 70101).

| # | Prueba | Esperado | Obtenido |
|---|---|---|---|
| 1 | `GET /documentos?limit=20` (admin) | mezcla de orígenes | `200`, `total=4`, orígenes `[EDAN×2, RIDA×2]` (ids 72, 71, 19, 18) |
| 2 | `GET /documentos?origen=EDAN` / `origen=RIDA` | solo ese origen | `200` `total=2` y `200` `total=2` |
| 3 | `GET /documentos?id_departamento=7&limit=20` | filtra geo | `200` `total=4` |
| 4 | `GET /documentos?todos=true` | sin paginar | `200` `total=4`, `n=4` |
| 5 | `GET /documentos?q=RIDA` | ILIKE nombre | `200` `total=2` |
| 6 | `GET /documentos` (usuario UGR/municipal `7051296`) | vista nacional accesible | `200` `total=4`; `?id_departamento=2` → `total=0` (filtro funciona) |
| 7 | `POST /repositorio/documentos` (municipal, PDF) | crea `DOC_PRECEDENTE` | `201` id 364, `origen=DOC_PRECEDENTE`, `id_edan/id_evento_rida=null`, `id_usuario_subio=30`, path `/uploads/repositorio/municipal/70101/doc_070101_30_*.pdf` |
| 8 | `GET /documentos?origen=DOC_PRECEDENTE` (admin) | ve el nuevo | `200` `total=1`; sin filtro `total=5` con `[DOC_PRECEDENTE, EDAN×2, RIDA×2]` |
| 9 | `PUT` dueño (≤72 h) | `200` | `200`, `observaciones` actualizada |
| 10 | `PUT` de otro usuario (admin) | `403` | `403` “Solo el usuario que subió el documento puede editarlo o eliminarlo” |
| 11 | `DELETE` (soft) de otro usuario | `403` | `403` mismo detalle |
| 12 | `PUT` dueño con `fecha_subida = now()-4 days` | `403` | `403` “No se puede editar ni eliminar: han pasado más de 3 días desde la subida” |
| 13 | `DELETE .../hard` dueño fuera de plazo | `403` | `403` mismo detalle |
| 14 | `PUT` sobre doc **EDAN** (id 19) por admin | sin restricción | `200` (observaciones restauradas después) |
| 15 | `DELETE .../hard` dueño dentro de plazo (limpieza de la prueba) | `200` | `200` “Documento eliminado permanentemente”; BD vuelve a `EDAN=2, RIDA=2` y `uploads/repositorio/municipal/` vacío |


## 8.1 Regla edición/eliminación DOC_PRECEDENTE (solo tercera API)
- Aplica **solo** a `origen = DOC_PRECEDENTE` (no a `EDAN`/`RIDA`).
- `PUT /repositorio/documentos/{id}` y `DELETE /repositorio/documentos/{id}` (soft) y `/hard`: solo el **usuario que subió** (`id_usuario_subio`) y dentro de **72 horas** (3 días, constante `DIAS_MAX_DOC_PRECEDENTE`) desde `fecha_subida`.
- Fuera de esas condiciones responde **403** (ver resultados 10-13 en §7.1). Validación centralizada en `api/repositorio/router.py` → `_validar_permiso_doc_precedente()`, llamada desde los 3 endpoints de mutación. Sin migración adicional (usa `origen`, `id_usuario_subio`, `fecha_subida` ya existentes).
- Historial: el commit `438c019` documentó la regla pero **no incluyó** el cambio de `api/repositorio/router.py` (script de edición falló por sintaxis); detectado al probar la API (PUT/DELETE no dueño respondían 200). Corregido en el commit posterior de esta misma rama y verificado (§7.1 #10-#13).

## 8. Notas
- `observaciones` es texto libre opcional (sin restricción de contenido más allá del almacenamiento).
- Los endpoints EDAN/RIDA mantienen URL, campos y respuesta; solo se etiqueta el origen internamente por ruta.
- `DOC_PRECEDENTE` exige geografía del municipio en la subida (para filtros) y queda asociado al usuario que sube.
