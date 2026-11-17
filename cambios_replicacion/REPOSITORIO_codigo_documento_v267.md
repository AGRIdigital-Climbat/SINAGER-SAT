# REPOSITORIO — `codigo_documento`: clave de agrupación/rastreo de DOC_PRECEDENTE (v2.67.0)

> **Contexto (esquema/módulo):** esquema `repositorio` (+ métrica en `publico`) /
> módulo `api/repositorio`. Rama `migraciones`. Fecha: 2026-11-17.
> **Contratos EDAN y RIDA: SIN CAMBIOS** (ni rutas, ni campos, ni respuestas).

## 1. Objetivo y decisiones

Los documentos EDAN/RIDA ya se agrupan por su padre (`id_edan` / `id_evento_rida`).
Los respaldos municipales (`DOC_PRECEDENTE`, 3ª subida `POST /api/v2/repositorio/documentos`)
no tenían equivalente: cada PDF quedaba aislado con solo `id_documento`. Se añade una
**clave de rastreo/expediente propia**:

- Columna `repositorio.documentos.codigo_documento varchar(64)`, **NO única** (varios
  documentos comparten el mismo código = mismo expediente). NULL en EDAN/RIDA.
- La escribe **solo la 3ª API** (y el PUT de edición con sus guardas de dueño/72 h):
  - el cliente manda `codigo_documento` (se normaliza **trim + MAYÚSCULAS**, máx 64,
    patrón libre) → el documento se anexa a ese expediente;
  - si no lo manda → la API **autogenera** `RES-{codigo_ine}-{YYYY}-{sec:05d}` (p. ej.
    `RES-070101-2026-00002`) usando la secuencia BD nueva.
- **No es pública**: todas las rutas nuevas van tras `get_current_user` como el resto
  del repositorio (decisión del usuario). Solo se añade UNA métrica agregada al grupo
  público existente (conteos, nunca códigos).
- Las APIs públicas de otras áreas siguen igual (v2.66.0), esta no las toca salvo la
  dimensión `expedientes` de `v_repo_resumen`.

## 2. Archivos

### 2.1 Nuevos
| Ruta | Contenido |
|---|---|
| `database/migrations/v2.67.0_repositorio_codigo_documento.sql` | Columna + índice + secuencia + comments + re-creación de `publico.v_repo_resumen` con dimensión `expedientes` (DO $mig$ protegido si aún no existe el esquema `publico`). |
| `despliegue/migraciones/v2.67.0_repositorio_codigo_documento.sql` | Espejo textual idéntico (`diff -q` OK). |
| `cambios_replicacion/REPOSITORIO_codigo_documento_v267.md` | Este documento. |

### 2.2 Modificados
| Ruta | Qué cambió |
|---|---|
| `api/repositorio/service.py` | +`normalizar_codigo_documento(codigo)` (trim+upper); +`generar_codigo_documento(db, id_municipio)` (`RES-{codigo_ine}-{YYYY}-{nextval(repositorio.codigo_documento_seq):05d}`); `upload_documento` acepta `codigo_documento` y lo inserta normalizado; `_aplicar_filtros_documentos` acepta `codigo_documento` (igualdad exacta, filtrable en cualquier origen aunque solo DOC_PRECEDENTE lo usa); `list_documentos_filtrados` lo propaga; +`list_documentos_by_codigo(db, codigo, limit, skip, todos)`; `update_documento` normaliza el campo cuando viene en el payload. |
| `api/repositorio/router.py` | `_procesar_subida(..., codigo_documento=None)` → pasa a `upload_documento` (EDAN/RIDA no lo pasan: NULL). `subir_documento_municipal`: Form opcional `codigo_documento` (max 64; 400 si excede; autogenera si falta). GET `/documentos` (general): Query `codigo_documento`. **Nueva ruta** GET `/documentos/codigo/{codigo_documento}` (normaliza; 400 si vacío; paginación `limit/skip/todos`). GET `/documentos/filtrar`: Query `codigo_documento`. PUT existente sin cambios de código (el schema ya acepta el campo). |
| `api/repositorio/schemas.py` | `DocumentoResponse` + `codigo_documento: Optional[str]`; `DocumentoUpdate` + `codigo_documento: Optional[str] (max 64)`. |
| `mi_repositorio.md` | Documenta campo/endpoints nuevos. |
| `mi_metricas_publicas.md` | Documenta la dimensión `expedientes` en `/publico/repositorio/resumen`. |
| `cambios_replicacion/INSTRUCCIONES.md` | Fila J del índice. |

## 3. BD — objetos exactos (esquemas `repositorio` y `publico`)

- **Tabla `repositorio.documentos`**: columna nueva `codigo_documento varchar(64) NULL`.
- **Índice**: `idx_documentos_codigo_documento` (sobre `codigo_documento`).
- **Secuencia**: `repositorio.codigo_documento_seq` (solo autogeneración; nunca la usa el cliente).
- **Vista re-creada `publico.v_repo_resumen`** (dimension, llave, total): dimensiones
  `total`, `origen`, `tipo`, `firma` (como v2.66.0) **+ `expedientes`** con llaves:
  - `EDAN` = `count(distinct id_edan)` de docs EDAN activos
  - `RIDA` = `count(distinct id_evento_rida)` de docs RIDA activos
  - `DOC_PRECEDENTE` = `count(distinct codigo_documento)` de DOC_PRECEDENTE activos con código
- Comentario de columna/secuencia/vista incluidos en la migración.
- **Sin backfill**: los 4 documentos históricos quedan `codigo_documento NULL`.

## 4. API (auth JWT `get_current_user`, igual que el resto del repositorio)

| Método y ruta | Auth | Novedad |
|---|---|---|
| `POST /api/v2/repositorio/documentos` (DOC_PRECEDENTE) | JWT | Form opcional `codigo_documento` (≤64). Respuesta `data.codigo_documento` **siempre** (cliente o autogenerado). |
| `GET /api/v2/repositorio/documentos` | JWT | Filtro nuevo `codigo_documento` (exacto, normalizado). |
| `GET /api/v2/repositorio/documentos/codigo/{codigo_documento}` | JWT | **NUEVO**: lista el expediente (activos, recientes primero, `limit/skip/todos`). 400 si vacío. |
| `GET /api/v2/repositorio/documentos/filtrar` | JWT | Filtro nuevo `codigo_documento`. |
| `PUT /api/v2/repositorio/documentos/{id_documento}` | JWT + guard DOC_PRECEDENTE (dueño ≤72 h) | Body puede incluir `codigo_documento` (reasigna el expediente). EDAN/RIDA: sin nuevas restricciones (igual que antes). |
| `GET /api/v2/repositorio/documentos/{id_documento}` y listados | JWT | `data.codigo_documento` (null en EDAN/RIDA). |
| `POST /edan/{id}/documentos`, `POST /rida/eventos/{id}/documentos` | JWT | **sin cambios** (código NULL). |
| `GET /api/v2/publico/repositorio/resumen` | sin auth (era público) | +3 filas `dimension='expedientes'` (solo conteos). |

Ejemplo de subida con agrupación (curl real probado):
```bash
# 1ª subida del expediente (sin código → autogenerado en la respuesta)
curl -X POST "$API/api/v2/repositorio/documentos" -H "Authorization: Bearer $TOKEN" \
  -F "file=@acta.pdf" -F "id_tipo_documento=5" \
  -F "id_departamento=7" -F "id_provincia=701" -F "id_municipio=70101" \
  -F "fecha_documento=2026-11-17" -F "nombre_documento=Acta de barrio"
# -> data.codigo_documento = "RES-070101-2026-00002"

# 2ª subida: MISMO expediente (puede ser minusculas; se normaliza)
curl -X POST "$API/api/v2/repositorio/documentos" -H "Authorization: Bearer $TOKEN" \
  -F "file=@anexofotos.pdf" -F "id_tipo_documento=5" \
  -F "id_departamento=7" -F "id_provincia=701" -F "id_municipio=70101" \
  -F "fecha_documento=2026-11-17" -F "nombre_documento=Anexo fotos del acta" \
  -F "codigo_documento=res-070101-2026-00002"
# -> data.codigo_documento = "RES-070101-2026-00002" (mismo grupo)

# Ver el expediente
curl -H "Authorization: Bearer $TOKEN" \
  "$API/api/v2/repositorio/documentos/codigo/RES-070101-2026-00002"
# -> total=2, ambas con origen=DOC_PRECEDENTE
```

Envelope (listas): `{"success":true,"message":"Documentos del expediente listados","data":[...],"total":N}`.
Errores observados: `400 codigo_documento vacío`, `422` (max_length 64 en Form/Query),
`403` (PUT/DELETE DOC_PRECEDENTE por no dueño o >72 h — regla previa intacta).

## 5. Replicación en el gemelo (orden)

```bash
# 0) Respaldo previo
bash despliegue/scripts/generar_dump.sh

# 1) Código
git pull origin migraciones

# 2) Migracion (idempotente; requiere v2.66.0 aplicada si se quiere la metrica;
#    sin esquema publico, hace igualmente columna/indice/secuencia)
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f database/migrations/v2.67.0_repositorio_codigo_documento.sql
#    esperado: IDEMPOTENT OK v2.67.0 codigo_documento + metrica expedientes

# 3) Reiniciar API
./stop.sh && ./start_api.sh     # o systemctl restart sinagersat-api
```

## 6. Verificación (esperada en gemelo; resultados reales dev 2026-11-17)

```sql
SELECT column_name FROM information_schema.columns
 WHERE table_schema='repositorio' AND table_name='documentos' AND column_name='codigo_documento';  -- 1 fila
SELECT indexname FROM pg_indexes WHERE schemaname='repositorio' AND indexname='idx_documentos_codigo_documento';
SELECT sequencename FROM pg_sequences WHERE schemaname='repositorio' AND sequencename='codigo_documento_seq';
SELECT dimension, llave, total FROM publico.v_repo_resumen WHERE dimension='expedientes';
```

```bash
# Subida sin codigo -> codigo autogenerado formato RES-<ine>-<anio>-<seq>
# Subida con codigo en minusculas -> devuelto en MAYUSCULAS, agrupa con el previo
# GET /documentos?codigo_documento=X -> solo los del expediente
# GET /documentos/codigo/<x en minusculas> -> mismo total (normaliza)
# GET /publico/repositorio/resumen -> filas expedientes (EDAN|RIDA|DOC_PRECEDENTE), sin exponer codigos
# PUT /documentos/{id} por otro usuario sobre DOC_PRECEDENTE -> 403 (regla previa)
# PUT /documentos/{id} (dueno, en plazo) con codigo -> 200 y reAgrupa
```

**Resultados reales observados (dev):** migración aplicada 2× sin error; doc A `368` →
`RES-070101-2026-00002`; doc C enviado con el código en minúsculas quedó en el mismo
grupo (filtro `?codigo_documento` → total 2 `[370,368]`; `/codigo/...` → total 2 ambos
`DOC_PRECEDENTE`); métrica pública devolvió
`expedientes/EDAN=1, RIDA=1, DOC_PRECEDENTE=3`; PUT de admin sobre doc del user 30 →
`403 "Solo el usuario que subió el documento puede editarlo o eliminarlo"`; PUT del dueño
reasignando código → `200` y `/codigo/EXPEDIENTE-REASIGNADO-1` → total 1; doc EDAN 19 →
`codigo_documento=null` (contrato intacto). **Limpieza**: docs prueba 367-370 hard-deleted
por el dueño (200×4), BD volvió a `EDAN=2,RIDA=2`, `uploads/repositorio/municipal/70101/`
vacía.

## 7. Notas / rollback
- El código es **literal normalizado**, no un FK: no exige crear el expediente antes
  (cualquier string ≤64 lo inicia). Dos municipios pueden coincidir en código (raro, no
  bloqueado); si se quisiera aislamiento duro, sería tabla propia (decisión futura).
- `RES-...` autogenerado usa el `codigo_ine` del municipio enviado (si el municipio no
  existe en `shared.municipio` → marcador `SINMUN`, el documento se guarda igual).
- Rollback: `ALTER TABLE repositorio.documentos DROP COLUMN codigo_documento`,
  `DROP INDEX idx_documentos_codigo_documento`, `DROP SEQUENCE
  repositorio.codigo_documento_seq`, re-crear `v_repo_resumen` versión v2.66.0; revertir
  los commits. Sin pérdida de datos de origen.
