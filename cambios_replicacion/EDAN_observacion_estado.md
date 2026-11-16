# Cambio: `observacion_estado` en EDAN localidades — instrucciones para replicar

> **Para qué sirve este documento.** Mismo patrón de handoff que
> [`INSTRUCCIONES.md`](INSTRUCCIONES.md) (hogares): registro completo del cambio
> **`observacion_estado`** en `edan.edan_localidades` para que el otro servidor lo replique.
>
> Fecha del cambio: **2026-11-15** · Migración: **v2.64.0** (aplicada y verificada en este servidor).

---

## 1. Objetivo y decisiones

**Objetivo:** cuando la API cambia el estado de una EDAN localidad (p. ej. a
**"Rechazado UGR"**), quien revisa debe poder indicar **el motivo del rechazo**.
Hoy solo existía `id_edan_localidad_estado`; no quedaba registro del porqué.

**Decisiones (cerradas con el equipo):**

1. Campo nuevo **`observacion_estado TEXT`** (NULL = sin observación; texto libre).
2. **Obligatoria solo al rechazar**: si el estado destino es "Rechazado…" y la
   observación viene vacía → **HTTP 422** (mismo patrón que las aprobaciones de EDAN
   en `router_v2_aprobaciones.py`).
3. **Si no se envía en otros cambios, se conserva la anterior** (`COALESCE` en el
   UPDATE): el campo refleja el motivo del último cambio que lo trajo.
4. **Escritura vía endpoints de cambio de estado + PUT genéricos**: el upsert del móvil
   (`_CABECERA_COLS`, `LocalidadCreate`) **NO** expone el campo; `LocalidadUpdate`
   y `LocalidadDocumentoResponse` **SÍ** lo incluyen para que los PUT genéricos
   (`PUT /localidades/{id}`, `PUT /edan/{id}/localidades/{id}`) también validen
   el 422 al rechazar y persistan la observación con COALESCE.
5. El handler global de 422 de la API (`api/main.py:147`) devuelve un envelope
   genérico sin `detail` (comportamiento preexistente, igual que en aprobaciones).
6. **`_db_error` en `router.py`** pasa `HTTPException` tal cual (antes convertía 422
   en 400 genérico). `router_v2_catalogos.py` tiene función análoga (no se tocó).

---

## 2. Cambios por archivo (lista exacta)

### 2.1 NUEVOS

| Archivo | Qué contiene |
|---|---|
| `database/migrations/v2.64.0_edan_localidades_observacion_estado.sql` | Migración idempotente (BEGIN/COMMIT, `ADD COLUMN IF NOT EXISTS`): `observacion_estado TEXT` + COMMENT en `edan.edan_localidades` |
| `despliegue/migraciones/v2.64.0_edan_localidades_observacion_estado.sql` | **Copia textual** (obligatoria: `despliegue/scripts/actualizar.sh` aplica esta carpeta) |
| `cambios_replicacion/EDAN_observacion_estado.md` | Este documento |

### 2.2 MODIFICADOS

| Archivo | Qué cambió |
|---|---|
| `api/edan/schemas.py` | `LocalidadEstadoUpdate` y `LocalidadEstadoUpdateV2`: + `observacion_estado` (entrada). `LocalidadNestedResponse`, **`LocalidadDocumentoResponse`**: + `observacion_estado` (salida). **`LocalidadUpdate`**: + `observacion_estado` (entrada) — permite escribirla en PUT genéricos. |
| `api/edan/service.py` | `cambiar_estado_localidad()` y `cambiar_estado_localidad_por_id_local()`: nueva 3.ª/4.ª arg `observacion_estado`; cargan `nombre` del estado destino; si `LOWER(nombre) LIKE 'rechazado%'` y la obs. viene vacía → **422**; el `UPDATE` escribe `observacion_estado = COALESCE(:obs, observacion_estado)` (conserva si no viene). **`update_localidad()`** (PUT genéricos huérfanas/consolidadas): validación idéntica **solo si el estado CAMBIA** (para no romper re-sync que pre-llena el estado actual) + `observacion_estado = COALESCE(:obs, observacion_estado)` en el UPDATE. Lecturas: `_build_localidad`, `_get_resumen_localidades`, `list_mis_localidades_estados` (+ `l.observacion_estado` en SELECTs). |
| `api/edan/service_v2_nuevas.py` | `list_formularios_estados()`: + `l.observacion_estado` en el SELECT del listado ligero |
| `api/edan/router.py` | `PUT /localidades/{id}/estado` (v1), `PUT /localidades/{id}` (huérfanas), `PUT /edan/{id}/localidades/{id}` (consolidadas): propagan `data.observacion_estado`; descripciones actualizadas. **`_db_error()`: pasa `HTTPException` sin envolver (422 se propaga correcto).** |
| `api/edan/router_v2_edan.py` | `PUT /localidades/{id}/estado` (v2): ídem |
| `api/edan/router_v2.py` | `PUT /localidades/estado` (por `id_local`, móvil): ídem |

**No se tocó ningún otro archivo.** (`GET /formularios/{uuid}` y `…/completo` devuelven
el campo **automáticamente**: usan `SELECT *` + `_row_public`.)

---

## 3. APIs afectadas

### Escritura (aceptan el campo)

| Método | Ruta | Auth |
|---|---|---|
| PUT | `/api/v1/edan/localidades/{id_localidad}/estado` | usuario autenticado + permiso EDAN |
| PUT | `/api/v2/edan/localidades/{id_localidad}/estado` | roles locales (6=UGR, 7=Responsable) |
| PUT | `/api/v2/edan/localidades/estado` (por `id_local` del móvil) | roles locales (6/7) |
| PUT | `/api/v1/edan/localidades/{id}` (huérfana) | roles locales (6/7) |
| PUT | `/api/v1/edan/edan/{id}/localidades/{id_localidad}` (consolidada) | roles locales (6/7) |

Cuerpo (los 5): `{"id_edan_localidad_estado": int, "observacion_estado": str|null}`.
Estados vigentes en `edan.edan_localidades_estado`: 1 Borrador · 2 Enviado UGR ·
3 Aprobado UGR · **4 Rechazado UGR** · 5 Aprobado Ajuste UGR · 6 En revisión UGR.

> **Nota:** los 2 PUT genéricos de localidad **también exigen `observacion_estado` al rechazar**
> (422) y la persisten con COALESCE. La validación solo dispara si el estado **cambia**
> (el sync pre-llena el estado actual → no rompe re-sincronizaciones).

### Lectura (devuelven `observacion_estado`)

- `GET /api/v1/…` localidad/listados/sync pull y la **respuesta de los 3 PUT** → vía `_build_localidad`
- `GET /api/v2/edan/formularios/estados` (listado ligero)
- `GET /api/v2/edan/localidades/mis-estados` (listado ligero web)
- `GET /api/v2/edan/formularios/{ref}` y `…/completo` (cabecera del documento)
- `GET` detalle EDAN (`_get_resumen_localidades`: resumen compacto de localidades)

---

## 4. Replicación en el servidor en limpio

```bash
# 1) Código (pull de esta rama o copiar los archivos de §2.2)

# 2) Migración (idempotente, se puede correr 2 veces)
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
  -f database/migrations/v2.64.0_edan_localidades_observacion_estado.sql
#    Alternativa: despliegue/scripts/actualizar.sh (aplica despliegue/migraciones/)

# 3) Reiniciar la API
./stop.sh && ./start_api.sh
```

No hay dependencias nuevas ni datos que cargar.

---

## 5. Verificación (checklist)

### SQL

```sql
-- columna existe (y la 2da corrida de la migración no falla)
SELECT column_name, data_type FROM information_schema.columns
WHERE table_schema='edan' AND table_name='edan_localidades'
  AND column_name='observacion_estado';
-- observacion_estado | text
```

### API (con token)

```bash
# a) rechazar SIN observación → 422
curl -s -X PUT "$B/api/v1/edan/localidades/{id}/estado" -H "Authorization: Bearer $T" \
  -H "Content-Type: application/json" -d '{"id_edan_localidad_estado":4}'          # → 422

# b) rechazar CON observación → 200 y el campo en la respuesta
curl -s -X PUT "$B/api/v1/edan/localidades/{id}/estado" -H "Authorization: Bearer $T" \
  -H "Content-Type: application/json" \
  -d '{"id_edan_localidad_estado":4,"observacion_estado":"Falta sección de daños"}'
#    → data.observacion_estado = "Falta sección de daños"

# c) cambiar a otro estado SIN observación → 200 y se CONSERVA la anterior
curl -s -X PUT "$B/api/v1/edan/localidades/{id}/estado" -H "Authorization: Bearer $T" \
  -H "Content-Type: application/json" -d '{"id_edan_localidad_estado":6}'
#    → data.observacion_estado sigue = "Falta sección de daños"

# d) listados y documento incluyen el campo
curl -s "$B/api/v2/edan/formularios/estados?todos=true" -H "Authorization: Bearer $T"
curl -s "$B/api/v2/edan/localidades/mis-estados"        -H "Authorization: Bearer $T"
curl -s "$B/api/v2/edan/formularios/{id}"               -H "Authorization: Bearer $T"
```

### Resultados obtenidos en este servidor (2026-01-… prueba real)

| Prueba | Resultado |
|---|---|
| Rechazo sin observación (v1, v2-por-id, v2-por-id_local) | **422** en los 3 |
| Rechazo sin observación (PUT genéricos huérfana/consolidada) | **422** en los 2 |
| Rechazo con observación | 200 · `observacion_estado` en la respuesta |
| Cambio posterior sin observación | 200 · observación **conservada** |
| `GET /formularios/estados` · `GET /localidades/mis-estados` · `GET /formularios/{id}` | campo presente con el valor |
| `compileall api/edan` | OK |
| Multi-worker (6 hits a 4 workers) | Todos 422/200 consistentes |
| Logs API | Sin errores/tracebacks |

---

## 6. Notas

- `NULL` = nunca se observó / sin motivo registrado; **no es string vacío**.
- La validación es por **nombre** del estado (`LIKE 'rechazado%'`), no por id: si el
  catálogo se re-semea, la regla sigue funcionando.
- El campo **no** viaja en el sync de cabecera del móvil (`_CABECERA_COLS`); si el
  frontend lo necesita en el pull, ya está en `_build_localidad` (pull de localidades)
  y en los listados.
- **`LocalidadUpdate` + `update_localidad`**: los PUT genéricos de localidad (huérfana
  y consolidada) ahora **también validan 422 al rechazar** y persisten la obs. con
  COALESCE. La validación es **solo si el estado cambia** (`nuevo != actual`) para
  no romper el flujo de sync incremental (pre-llena estado actual).
- **`router.py:_db_error`** ahora devuelve `HTTPException` tal cual (antes 422→400).
  `router_v2_catalogos.py:_db_error` no se tocó (no afecta este cambio).
