# DESPLIEGUE API V2 — SINAGERSAT

> **Versión:** v1.4.0 · **Base URL:** `http://<host>:8000` · **Prefijo:** `/api/v2`
> **Swagger interactivo:** `/docs/v2` (agrupado jerárquicamente) y `/docs/v1` (legacy).
> **Docs de referencia:** [`EDAN_LOCALIDADES_V2.md`](EDAN_LOCALIDADES_V2.md), [`SINCRONIZACION.md`](SINCRONIZACION.md),
> [`EJEMPLOS_POR_SECCION.md`](EJEMPLOS_POR_SECCION.md) (campos por sección).

**Para migrar de v1 a v2** solo cambia la URL base: `/api/v1/...` → `/api/v2/...`. Las rutas y el JSON de respuesta son los mismos.
La API v1 queda intacta por compatibilidad.

### Especificación OpenAPI (JSON) de la v2

Para obtener el esquema OpenAPI (OpenAPI 3.1) de la **v2** como JSON:

| Recurso | URL | Contenido |
|---|---|---|
| OpenAPI completo (v1 + v2) | `GET /openapi.json` | Todas las rutas, sin separar |
| OpenAPI solo v1 | `GET /openapi.v1.json` | Solo `/api/v1/*` |
| **OpenAPI solo v2** | `GET /openapi.v2.json` | **Solo `/api/v2/*`** |
| Swagger UI v2 | `GET /docs/v2` | Interfaz interactiva |
| Redoc v2 | `GET /redoc` | Documentación alternativa |

Para guardarlo localmente (por ejemplo para alimentar el cliente o generar el SDK):

```bash
# Sin autenticación
curl -s http://<host>:8000/openapi.v2.json -o openapi_v2.json

# Solo las rutas v2 (filtro rápido por prefijo)
curl -s http://<host>:8000/openapi.v2.json | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('openapi:', d.get('openapi'))
print('endpoints:', len(d.get('paths', {})))
print('tags:', len(d.get('tags', [])))
"
```

> El endpoint `openapi.json`/`openapi.v1.json`/`openapi.v2.json` **no requiere token** y está excluido del propio esquema (no aparecen como rutas dentro del JSON). Los 45 tags de la v2 se emiten como objetos `{"name": ...}` (Compatibilidad OpenAPI); las 9 secciones `(con foto)` aparecen como tags propios en `tags[]`.

---

## 1. Índice de rutas v2 por módulo

| Módulo | Prefijo | Endpoints | Ejemplo |
|---|---|---|---|
| Autenticación | `/api/v2/auth` | login, register, verificar-identidad, cambiar-contrasena, mis-permisos | `POST /api/v2/auth/login` |
| Shared (catálogos) | `/api/v2/shared` | departamentos, provincias, municipios, cultivo, pecuaria… (tipo_evento está bajo `/edan`) | `GET /api/v2/shared/municipios` |
| Usuarios | `/api/v2/usuarios` | usuarios, roles, permisos | `GET /api/v2/usuarios/` |
| Upload | `/api/v2/upload` | subida de archivos | `POST /api/v2/upload` |
| Repositorio | `/api/v2/repositorio` | documentos por EDAN | `GET /api/v2/repositorio/edan/{id}/documentos` |
| EDAN cabecera | `/api/v2/edan` | listar, crear, editar, estado, consolidar/desconsolidar, reportes (resumen/geografico/agricultura/pecuario/localidades), **mis-reportes**, **mis-resumen**, **mis-estados**, sync (push/pull), consolidar/pendientes | `POST /api/v2/edan/consolidar` |
| EDAN localidades (sync) | `/api/v2/edan/localidades` | cabecera, 14 secciones, estado, con-foto, **mis-reportes**, **mis-resumen**, **mis-estados**, municipio/{id}, municipio/{id}/resumen | ver §3 y §4 |

---

## 2. Autenticación

```bash
# Login (campo = "usuario", no "ci")
curl -s -X POST $BASE/api/v2/auth/login \
  -H "Content-Type: application/json" \
  -d '{"usuario":"7051296","contrasena":"12345678"}'
```

```json
{ "success": true, "data": { "access_token": "eyJhbGciOiJIUzI1NiIs..." } }
```

```bash
TOKEN=eyJhbGciOiJIUzI1NiIs...    # usar en cada llamada
H="Authorization: Bearer $TOKEN"
CT="Content-Type: application/json"
```

---

## 3. Sync por secciones — dos modos

Toda sección acepta el ID de la localidad de **dos maneras** en el path:

| Modo | Path usa | Clave | Cuándo usarlo |
|---|---|---|---|
| **Online** | `{id_edan_localidad}` (int) | serial de BDD | Cuando ya tienes la localidad creada en el servidor |
| **Offline** | `{id_local}` (UUID) | UUID que generó el móvil | **Siempre se puede usar**; el servidor resuelve automáticamente |

Regla:
- Los endpoints de secciones **aceptan ambos**. Solo cambia el valor del path.
- Si la cabecera (con ese `id_local`) aún no existe al momento de la sección, el servidor responde:
  ```
  HTTP 400
  X-Retry-After: 2
  {"detail": "Cabecera no encontrada. Envía POST /cabecera primero o reintenta."}
  ```
  El móvil debe **reintentar con backoff** (1s, 2s, 4s…) hasta que la cabecera esté creada. Eso permite **envío en paralelo** (cabecera y secciones al mismo tiempo sin esperar la respuesta de la cabecera).

---

## 4. Ejemplos OFFLINE (prioridad) — flujo completo

### Paso 1 — Generar IDs en el móvil (UNA sola vez, se reusan siempre)

```
id_local       = UUID  v4 → "d1e8f2a4-6b3c-4d5e-9f01-2a3b4c5d6e7f"
id_seccion     = UUID  v4 → "9f3c1e8a-7b2d-4e5f-8a90-1b2c3d4e5f60"  (uno por ítem de cada sección)
```

### Paso 2 — Crear cabecera (offline, sin esperar nada)

```bash
curl -s -X POST $BASE/api/v2/edan/localidades/cabecera \
  -H "$H" -H "$CT" \
  -d '{
        "id_local": "d1e8f2a4-6b3c-4d5e-9f01-2a3b4c5d6e7f",
        "localidad": "Comunidad Nuevo Amanecer",
        "id_municipio": 70101,
        "id_departamento": 7,
        "id_provincia": 701,
        "id_tipo_evento": 7,
        "id_tipo_localidad": 2,
        "total_poblacion_afectada": 255,
        "total_familias_afectadas": 60,
        "total_familias_damnificadas": 30,
        "imp_poblacion": true,
        "imp_agropecuario": true,
        "imp_infraestructura": true,
        "imp_servicios": true
      }'
```

```json
{
  "success": true,
  "message": "Cabecera guardada correctamente",
  "data": {
    "id_edan_localidad": 412,
    "id_local": "d1e8f2a4-6b3c-4d5e-9f01-2a3b4c5d6e7f",
    "localidad": "Comunidad Nuevo Amanecer",
    "es_huerfana": true,
    "pendiente_actualizacion": false
  }
}
```

> ✅ Si reenvías la **misma** `id_local`, actualiza la cabecera sin duplicar.
> ✅ Guarda el `id_edan_localidad` (412) para el modo online, pero **puedes seguir usando el UUID** en todos los paths.

### Paso 3 — Secciones por `id_local` (OFFLINE) mientras la cabecera viaja en paralelo

```bash
# 3.1 Impacto en población (objeto único o array)
curl -s -X POST "$BASE/api/v2/edan/localidades/d1e8f2a4-6b3c-4d5e-9f01-2a3b4c5d6e7f/impacto-poblacion" \
  -H "$H" -H "$CT" \
  -d '{
        "id_seccion": "9f3c1e8a-7b2d-4e5f-8a90-1b2c3d4e5f60",
        "rango": "Adulto 19-60",
        "fallecidos": 2,
        "heridos": 8,
        "desaparecidos": 0
      }'
```

```bash
# 3.2 Danos viales (offline, con GPS, sin foto → endpoint JSON sin-foto)
curl -s -X POST "$BASE/api/v2/edan/localidades/d1e8f2a4-6b3c-4d5e-9f01-2a3b4c5d6e7f/danos-viales" \
  -H "$H" -H "$CT" \
  -d '{
        "id_seccion": "9f3c1e8a-7b2d-4e5f-8a90-1b2c3d4e5f61",
        "via": true,
        "puente": false,
        "tramo": "Carretera al norte km 5",
        "dano_parcial": true,
        "dano_total": false,
        "km_danio": 3.5,
        "coordenada_lat": -17.3934,
        "coordenada_lon": -66.1574
      }'
```

```bash
# 3.3 Servicios básicos (offline)
curl -s -X POST "$BASE/api/v2/edan/localidades/d1e8f2a4-6b3c-4d5e-9f01-2a3b4c5d6e7f/servicios-basicos" \
  -H "$H" -H "$CT" \
  -d '{
        "id_seccion": "9f3c1e8a-7b2d-4e5f-8a90-1b2c3d4e5f62",
        "tipo": "energia_electrica",
        "dano_parcial": false,
        "dano_total": true
      }'
```

```bash
# 3.4 Sección 1:1 (UPSERT, nunca duplica) — Primera respuesta
curl -s -X POST "$BASE/api/v2/edan/localidades/d1e8f2a4-6b3c-4d5e-9f01-2a3b4c5d6e7f/primera-respuesta" \
  -H "$H" -H "$CT" \
  -d '{ "id_seccion": "9f3c1e8a-7b2d-4e5f-8a90-1b2c3d4e5f63", "busqueda": true, "salvamento": false, "evacuacion": true }'
```

### Paso 4 — Mapear `id_local` → `id_edan_localidad` (verificación)

```bash
curl -s "$BASE/api/v2/edan/localidades/por-id-local/d1e8f2a4-6b3c-4d5e-9f01-2a3b4c5d6e7f" -H "$H"
```

```json
{
  "success": true,
  "data": { "id_edan_localidad": 412, "localidad": "Comunidad Nuevo Amanecer", "pendiente_actualizacion": true }
}
```

### Paso 5 — Cambiar estado (por `id_local`)

```bash
# Estados: 1 Borrador · 2 Enviado UGR · 3 Aprobado UGR · 4 Rechazado UGR · 5 Aprobado Ajuste UGR · 6 En revisión UGR
curl -s -X PUT "$BASE/api/v2/edan/localidades/estado" \
  -H "$H" -H "$CT" \
  -d '{
        "id_local": "d1e8f2a4-6b3c-4d5e-9f01-2a3b4c5d6e7f",
        "id_edan_localidad_estado": 2
      }'
```

---

## 5. Ejemplos ONLINE (usando `id_edan_localidad`)

```bash
# Listar una sección
curl -s "$BASE/api/v2/edan/localidades/412/danos-viales" -H "$H"

# Crear/actualizar ítem (mismo id_seccion = actualiza, no duplica)
curl -s -X POST "$BASE/api/v2/edan/localidades/412/danos-viales" -H "$H" -H "$CT" \
  -d '{ "id_seccion": "9f3c1e8a-7b2d-4e5f-8a90-1b2c3d4e5f61", "km_danio": 4.0 }'

# Grupo en array (una sola llamada, varias filas)
curl -s -X POST "$BASE/api/v2/edan/localidades/412/impacto-poblacion" -H "$H" -H "$CT" \
  -d '[
        { "id_seccion": "s1", "rango": "Niño 0-5", "fallecidos": 0, "heridos": 3 },
        { "id_seccion": "s2", "rango": "Adulto mayor 60+", "fallecidos": 1, "heridos": 2 }
      ]'

# Eliminar un ítem por id_seccion
curl -s -X DELETE "$BASE/api/v2/edan/localidades/412/impacto-poblacion/seccion/s2" -H "$H"

# Vaciar una sección completa
curl -s -X DELETE "$BASE/api/v2/edan/localidades/412/danos-agricultura" -H "$H"
```

**Aislamiento de errores:** si una fila del grupo falla (FK inválida, CHECK), las demás se guardan y la respuesta incluye `errors[]` con el `index` de la fila y el motivo.

> **Nota v2:** el flujo por secciones exige que cada fila tenga su propio `id_seccion` como identidad. Por eso se **eliminaron** los índices UNIQUE heredados de v1 que impedían varias filas por `(localidad, tipo)`, `(localidad, rango)` y `(localidad, grupo)` en `servicios_basicos`, `impacto_poblacion` y `proteccion`. El UNIQUE por `id_seccion` se mantiene. Además, el middleware de auditoría acepta bodies en array (envíos en grupo), por lo que la auditoría registra correctamente estos POST.

---

## 6. Secciones con FOTO

La v2 maneja las fotos de **dos maneras equivalentes**, según lo que tenga el cliente en ese momento:

- **A. Endpoint `/con-foto` (multipart):** sube el archivo físico (`file`) junto con los campos de la fila **en una sola llamada**. `file` es **opcional** (regla 6.4). Una llamada = **una fila**.
- **B. Endpoint JSON de grupo (`POST …/<seccion>`):** la foto viaja como **path (string)** en el campo `fotografia` de cada fila del objeto/array. Requiere haber subido antes el archivo por `POST /api/v2/upload` y usar el `path` devuelto. Una llamada = la **sección completa** (objeto o array), con filas con foto y sin foto mezcladas.

> Ambas escriben en las mismas columnas (`fotografia`, `coordenada_lat`, `coordenada_lon`) y hacen **UPSERT por `id_seccion`**. Es la misma fila de BD; solo cambia el transporte del archivo.

Las 9 secciones con foto usan su propio grupo en `/docs/v2` → `EDAN_LOCALIDADES > <Sección> (con foto)`:

| Sección | Endpoint `/con-foto` (A) | Endpoint JSON (B) | Campos clave |
|---|---|---|---|
| Daños viales | `danos-viales/con-foto` | `danos-viales` | via, puente, tramo, km_danio |
| Infraestructura pública | `danos-infra-publica/con-foto` | `danos-infra-publica` | comunidad, tipo_estructura |
| Daños vivienda | `danos-vivienda/con-foto` | `danos-vivienda` | comunidad, dano_parcial (int), dano_total (int) |
| Daños agricultura | `danos-agricultura/con-foto` | `danos-agricultura` | tipo_cultivo, id_cultivo, hectareas_* |
| Daños pecuarios | `danos-pecuarios/con-foto` | `danos-pecuarios` | especie, id_especie, animales_* |
| Establecimientos de salud | `salud-establecimientos/con-foto` | `salud-establecimientos` | nombre_establecimiento, nivel_atencion, *afectados |
| Servicios básicos | `servicios-basicos/con-foto` | `servicios-basicos` | tipo (5 valores) |
| Unidades educativas | `unidades-educativas/con-foto` | `unidades-educativas` | nombre_establecimiento, estudiantes, profesores |
| Infraestructura productiva | `infra-productiva/con-foto` | `infra-productiva` | tipo, dano_parcial (int), dano_total (int) |

### 6.1 ¿Cuál usar? — Criterio de decisión

| Situación del cliente | Usa | Motivo |
|---|---|---|
| Tiene el archivo en el dispositivo y **conectividad** (o aún no subió la foto a ningún lado) | **A** `/con-foto` | Sube archivo + datos en 1 llamada |
| Ya subió las fotos antes (`POST /upload`) y tiene los paths | **B** JSON de grupo | Envía toda la sección (mix con/sin foto) en 1 llamada |
| Grupo/array con **filas mezcladas** (unas con foto, otras sin) | **B** JSON de grupo | Cada fila lleva o no `fotografia`+`coordenadas` |
| Editar una fila que ya tiene foto y solo cambia datos | **B** JSON con `fotografia` existente | Evita re-subir el archivo (ver 6.5) |
| Agregar/reemplazar la foto de una fila existente | **A** `/con-foto` con el **mismo** `id_seccion` | UPSERT: la nueva foto reemplaza a la anterior |

### 6.2 Vía A — `/con-foto` (multipart), una fila por llamada

**Ejemplo OFFLINE con foto (por `id_local`):**

```bash
curl -s -X POST "$BASE/api/v2/edan/localidades/d1e8f2a4-6b3c-4d5e-9f01-2a3b4c5d6e7f/servicios-basicos/con-foto" \
  -H "$H" \
  -F "file=@foto_servicio.jpg" \
  -F "tipo=energia_electrica" \
  -F "dano_parcial=false" \
  -F "dano_total=true" \
  -F "id_seccion=9f3c1e8a-7b2d-4e5f-8a90-1b2c3d4e5f62" \
  -F "coordenada_lat=-17.3934" \
  -F "coordenada_lon=-66.1574"
```

**Ejemplo ONLINE sin foto (solo datos + GPS):**

```bash
curl -s -X POST "$BASE/api/v2/edan/localidades/412/danos-viales/con-foto" \
  -H "$H" \
  -F "via=true" \
  -F "tramo=Puente Río Grande" \
  -F "dano_total=true" \
  -F "id_seccion=9f3c1e8a-7b2d-4e5f-8a90-1b2c3d4e5f61" \
  -F "coordenada_lat=-17.40" \
  -F "coordenada_lon=-66.16"
```

### 6.3 Vía B — subir foto por `POST /upload` y enlazarla con el path

Paso 1 — sube cada foto y conserva el `path` devuelto:

```bash
# Sube el archivo (multipart). Respuesta: { "data": { "path": "/uploads/reports/70101/70101_12_8800abcd.jpg" } }
curl -s -X POST "$BASE/api/v2/upload" -H "$H" -F "file=@salud_1.jpg" -F "id_municipio=70101"
```

Paso 2 — envía la sección (objeto o array) con ese `path` en `fotografia`:

```bash
curl -s -X POST "$BASE/api/v2/edan/localidades/412/salud-establecimientos" -H "$H" -H "$CT" -d '{
  "id_seccion": "s_salud_01",
  "nombre_establecimiento": "Centro de Salud 15 de Agosto",
  "comunidad": "Nuevo Amanecer",
  "nivel_atencion": "2do Nivel",
  "fotografia": "/uploads/reports/70101/70101_12_8800abcd.jpg",
  "coordenada_lat": -17.3934,
  "coordenada_lon": -66.1574
}'
```

> El endpoint `/upload` acepta JPG/PNG/WebP/GIF, máx. **5 MB** (api/upload.py). Si el municipio o el usuario se omiten, guarda en `uploads/reports/general/`.

### 6.4 Grupo MIXTO — filas con foto y sin foto en el mismo array

Escenario real: en la sección salud, 3 de 5 establecimientos tienen foto y 2 todavía no. **No llames a `/con-foto` por cada fila.** Envía el array completo por el endpoint JSON; cada fila pone `fotografia`+`coordenadas` **solo si tiene foto**:

```bash
curl -s -X POST "$BASE/api/v2/edan/localidades/d1e8f2a4-6b3c-4d5e-9f01-2a3b4c5d6e7f/salud-establecimientos" -H "$H" -H "$CT" -d '[
  { "id_seccion": "s1", "nombre_establecimiento": "CS Candelaria",  "comunidad": "Candelaria",  "fotografia": "/uploads/reports/70101/a1.jpg", "coordenada_lat": -17.30, "coordenada_lon": -66.10 },
  { "id_seccion": "s2", "nombre_establecimiento": "CS San José",     "comunidad": "San José",     "fotografia": "/uploads/reports/70101/a2.jpg", "coordenada_lat": -17.31, "coordenada_lon": -66.11 },
  { "id_seccion": "s3", "nombre_establecimiento": "CS El Rosal",     "comunidad": "El Rosal",     "fotografia": "/uploads/reports/70101/a3.jpg", "coordenada_lat": -17.32, "coordenada_lon": -66.12 },
  { "id_seccion": "s4", "nombre_establecimiento": "CS San Marcos",   "comunidad": "San Marcos" },
  { "id_seccion": "s5", "nombre_establecimiento": "CS Villa Nueva",  "comunidad": "Villa Nueva" }
]'
```

Se guarda **una sola llamada**, UPSERT por `id_seccion`; cada fila conserva o no su foto. La misma regla aplica entre secciones distintas: una sección con fotos y otra sin fotos son **POST independientes**.

### 6.5 Edición de una fila con foto (lo importante)

Regla de oro: **el `id_seccion` nunca cambia al editar**; los cambios reenvían el mismo `id_seccion` y el servidor hace UPDATE sobre la misma fila.

| Qué quieres hacer | Endpoint | Payload |
|---|---|---|
| Cambiar solo **datos** de una fila que ya tiene foto | **B** `POST …/{seccion}` | Mismo `id_seccion` + solo los campos que cambian. **No reenvíes `fotografia`** (o envíala `null`): el UPSERT v2 solo toca campos presentes y no nulos, así que la foto se conserva. |
| **Reemplazar la foto** de una fila | **A** `…/{seccion}/con-foto` | Mismo `id_seccion` + `file` nuevo + `coordenadas`. La nueva foto sobrescribe el path. |
| **Agregar foto** a una fila que no tenía | **A** `…/{seccion}/con-foto` | Mismo `id_seccion` + `file` + `coordenadas`. Ahora la fila tiene foto. |
| **Quitar la foto** (sin borrar la fila) | **B** `POST …/{seccion}` | Mismo `id_seccion` + `fotografia: ""` (string vacío). La fila queda sin foto pero con sus datos. |
| Corregir un dato de una fila | **B** `POST …/{seccion}` | Mismo `id_seccion` + solo el campo corregido. No destructivo: el resto no se toca. |
| Borrar la fila completa | `DELETE …/{seccion}/seccion/{id_seccion}` | Elimina la fila (y queda su archivo en uploads como huérfano). |

> **Importante:** al editar por **B (JSON)**, si necesitas re-subir una *nueva* foto primero haz `POST /upload` y luego reenvía la fila con el nuevo path + el mismo `id_seccion`. Si reenvías `fotografia` con el **mismo path que ya tenía**, es un no-op (no se re-subie ni se duplica el archivo). Nota: en la vía B el UPSERT es **no destructivo** (solo campos presentes y no nulos); en la vía A `/con-foto` el campo `fotografia` se **escribe siempre** con lo que haya (path nuevo o vacío si no mandas `file`).

### 6.6 Reglas de validación foto ↔ GPS

Aplican en los endpoints **`/con-foto` (A)** de forma automática (422) y en la **vía B** el cliente debe respetar la misma regla:

| file / fotografia | coordenadas | Resultado |
|---|---|---|
| ✅ con foto | ✅ lat+lon | ✅ 201 guardado |
| ❌ sin foto | ✅ lat+lon | ✅ 201 guardado (datos + GPS) |
| ✅ con foto | ❌ sin coords | ❌ 422 "Foto requiere coordenadas GPS" (en A) |
| ❌ sin foto | ❌ sin coords | ✅ 201 guardado (solo datos) |

### 6.7 Upsert por `id_seccion` (con foto)

Si reenvías el **mismo** `id_seccion` por cualquiera de las dos vías, **actualiza el registro** en lugar de duplicar. En `/con-foto`, una nueva foto reemplaza a la anterior; en el JSON de grupo, un reenvío con "fields presentes" sobrescribe solo esos campos.

---

## 7. EDAN cabecera (consolidar / desconsolidar)

```bash
# Listar EDANs
curl -s "$BASE/api/v2/edan/" -H "$H"

# Obtener EDAN completo (detallado)
curl -s "$BASE/api/v2/edan/45?modo=detallado" -H "$H"

# Consolidar localidades en un EDAN
curl -s -X POST "$BASE/api/v2/edan/consolidar" -H "$H" -H "$CT" \
  -d '{ "id_municipio": 70101, "id_tipo_evento": 7, "localidad_ids": [412, 413] }'

# Consolidación automática
curl -s -X POST "$BASE/api/v2/edan/consolidar/auto?id_municipio=70101&id_tipo_evento=7" -H "$H"

# Desconsolidar una localidad
curl -s -X PUT "$BASE/api/v2/edan/localidades/412/desconsolidar" -H "$H"

# Cambiar estado de localidad por id_edan_localidad
curl -s -X PUT "$BASE/api/v2/edan/localidades/412/estado" -H "$H" -H "$CT" \
  -d '{ "id_edan_localidad_estado": 2 }'

# Deshacer consolidación de un EDAN
curl -s -X PUT "$BASE/api/v2/edan/45/deshacer" -H "$H"

# Estado de EDAN (cabecera)
curl -s -X PUT "$BASE/api/v2/edan/45/estado" -H "$H" -H "$CT" -d '{ "id_estado": 4 }'
```

---

## 8. Mis reportes, resumen y estados — flujo de carga en la web

La web no necesita listar con todo el payload: primero refresca la lista y los **badges de estado**, y solo al entrar a un ítem carga el contenido completo con su API de detalle.

> **Importante:** existen **dos catálogos de estado distintos**:
> - `edan_localidades_estado` → estados de **localidades** (`id_edan_localidad_estado`): 1 Borrador · 6 En revisión UGR · 2 Enviado UGR · 3 Aprobado UGR · 4 Rechazado UGR · 5 Aprobado Ajuste UGR.
> - `estado_edan` → estados del **EDAN cabecera** (`id_estado`): 1 Borrador · 2 Enviado · 3 Aprobado · 4 Rechazado · 5 Aprobado ajuste · 6 En revisión.

Por eso hay endpoints paralelos: uno para `localidades` y otro para `edan`. Ambos respetan el mismo scope: el usuario ve solo sus registros (`id_usuario`). Un usuario con rol 1 (admin) o 9 puede consultar otros usuarios con el query `?id_usuario=`.

### 8.1 Localidades

| Endpoint | Para qué | Payload |
|---|---|---|
| `GET /api/v2/edan/localidades/mis-resumen` | Totales + **desglose por estado** (badges) | Ligero |
| `GET /api/v2/edan/localidades/mis-estados` | Lista ligera (cabecera + estado, **sin secciones**) para refrescar badges por `id` | Muy ligero |
| `GET /api/v2/edan/localidades/mis-reportes` | Lista COMPLETA (todas las secciones anidadas) | Pesado |
| `GET /api/v2/edan/localidades/{id_localidad}` | **UNA localidad completa** al entrar al ítem | `id_local` (UUID) o `id_edan_localidad` (int) |

```bash
# 1er load — resumen con badges por estado
curl -s "$BASE/api/v2/edan/localidades/mis-resumen" -H "$H"
```

```json
{
  "success": true,
  "data": {
    "total_localidades": 4,
    "total_consolidadas": 0,
    "total_huerfanas": 4,
    "por_estado": [
      { "id_edan_localidad_estado": 1, "estado": "Borrador",           "cantidad": 2 },
      { "id_edan_localidad_estado": 6, "estado": "En revision UGR",    "cantidad": 1 },
      { "id_edan_localidad_estado": 2, "estado": "Enviado UGR",        "cantidad": 1 }
    ]
  }
}
```

```bash
# Refresco de lista (ligero) — actualizar el badge con el id + estado
curl -s "$BASE/api/v2/edan/localidades/mis-estados?limit=200" -H "$H"
```

```json
{
  "success": true,
  "total": 4,
  "data": [
    {
      "id_edan_localidad": 292,
      "id_local": "1a042b1eac3-65a0486fd0d19",
      "localidad": "San Bernardo",
      "id_edan_localidad_estado": 2,
      "id_edan": null,
      "es_huerfana": true,
      "pendiente_actualizacion": true,
      "fecha_modificacion": "2026-08-27T06:09:11.364205",
      "estado_localidad": { "id_edan_localidad_estado": 2, "nombre": "Enviado UGR", "orden": 4 }
    }
  ]
}
```

```bash
# Entrar al ítem → cargar TODO el contenido (solo esta localidad)
# Acepta el UUID (id_local) o el int (id_edan_localidad)
curl -s "$BASE/api/v2/edan/localidades/292" -H "$H"
curl -s "$BASE/api/v2/edan/localidades/1a042b1eac3-65a0486fd0d19" -H "$H"
```

La respuesta es exactamente la estructura de `mis-reportes` pero de **una sola** localidad: cabecera + las 14 secciones + `estado_localidad` + `usuario`. **Este endpoint de detalle es el que siempre carga el contenido al abrir el formulario** (para evitar que la web manipule la estructura anidada).

### 8.2 EDAN cabecera

| Endpoint | Para qué |
|---|---|
| `GET /api/v2/edan/mis-resumen` | Totales + `por_estado[]` (**estado_edan**) + `por_tipo_evento[]` |
| `GET /api/v2/edan/mis-estados` | Lista ligera de EDAN (cabecera + estado + tipo evento, **sin localidades** anidadas) |
| `GET /api/v2/edan/{id}` | EDAN **completo** (con localidades) al entrar al ítem |

```bash
# Resumen EDAN con badges de estado_edan
curl -s "$BASE/api/v2/edan/mis-resumen" -H "$H"
```

```json
{
  "success": true,
  "data": {
    "totales": { "total_edans": 2, "total_localidades": 1, "total_poblacion_afectada": 120,
                 "total_familias_afectadas": 10, "total_familias_damnificadas": 4 },
    "por_estado": [ { "estado": "Borrador", "id_estado": 1, "cantidad": 2 } ],
    "por_tipo_evento": [ { "id_tipo_evento": 4, "tipo_evento": "Helada", "cantidad": 1 },
                          { "id_tipo_evento": 6, "tipo_evento": "Sequía", "cantidad": 1 } ]
  }
}
```

```bash
# Lista ligera para refrescar badges (id + estado)
curl -s "$BASE/api/v2/edan/mis-estados?limit=200" -H "$H"
```

```bash
# Entrar al ítem → EDAN completo (cabecera + localidades consolidadas)
curl -s "$BASE/api/v2/edan/45?modo=detallado" -H "$H"
```

> **Flujo resumido:** login → `mis-resumen` (badges) + `mis-estados` (lista ligera) → clic en ítem → `GET /localidades/{id}` (o `/edan/{id}`) carga el contenido → edición/estado por los endpoints de sección/cabecera ya documentados.

### 8.3 Reportes de solo totales (agregados con filtros)

Consulta el EDAN de forma **agregada** (sin arrastrar filas). Mismos filtros que v1:

`GET /api/v2/edan/reportes/{resumen|geografico|agricultura|pecuario|localidades}`

| Endpoint | Qué devuelve | Filtr | Ejemplo |
|---|---|---|---|
| `GET /reportes/resumen` | `totales` + `por_estado[]` + `por_tipo_evento[]` | Todos | `curl "$BASE/api/v2/edan/reportes/resumen?id_municipio=70101&id_estado=1" -H "$H"` |
| `GET /reportes/geografico` | EDANs agrupados por departamento/provincia/municipio | Todos | `curl "$BASE/api/v2/edan/reportes/geografico" -H "$H"` |
| `GET /reportes/agricultura` | Hectáreas afectadas/perdidas por cultivo | Todos | `$BASE/api/v2/edan/reportes/agricultura?fecha_evento_desde=2026-08-01` |
| `GET /reportes/pecuario` | Animales afectados/muertos por especie | Todos | `$BASE/api/v2/edan/reportes/pecuario` |
| `GET /reportes/localidades` | Localidades consolidadas (banderas de impacto), paginado `skip`/`limit` | Todos | `$BASE/api/v2/edan/reportes/localidades?limit=200` |
| `GET /reportes/mis-reportes` | Listado EDAN del usuario (completo) | Scope por usuario | `?id_usuario=28` (solo admin/rol 9) |
| `GET /reportes/mis-resumen` | Resumen EDAN del usuario | Scope por usuario | alias de `/edan/mis-resumen` |

**Filtros aceptados** (igual que v1): `q`, `id_departamento`, `id_provincia`, `id_municipio`, `id_tipo_evento`, `id_estado`, `estado`, `id_usuario_ugr`, `fecha_evento_desde/hasta`, `fecha_creacion_desde/hasta`, `pendiente_eliminacion`, `pendiente_actualizacion`, `con_foto`, `sin_foto`, `imp_*`, `tiene_agricultura`, `tiene_pecuario`.

**Scope por rol:** rol 1 (admin) y 9 ven todo (filtro libre). Otros roles (2-8) ven **solo sus EDAN** (`id_usuario_ugr` = usuario autenticado) salvo que se indique `id_usuario_ugr` explícito.

```bash
# Ejemplo real (admin): resumen con badges
curl -s "$BASE/api/v2/edan/reportes/resumen" -H "$H" | python3 -m json.tool
```

```json
{
  "success": true,
  "data": {
    "totales": {
      "total_edans": 2, "total_localidades": 1,
      "total_poblacion_afectada": 120, "total_familias_afectadas": 10, "total_familias_damnificadas": 4
    },
    "por_estado": [ { "estado": "Borrador", "id_estado": 1, "cantidad": 2 } ],
    "por_tipo_evento": [
      { "id_tipo_evento": 4, "tipo_evento": "Helada", "cantidad": 1 },
      { "id_tipo_evento": 6, "tipo_evento": "Sequía", "cantidad": 1 }
    ]
  }
}
```

> **Nota:** el "EDAN con solo totales" para un **EDAN individual** es el `?modo=compacto` de `GET /api/v2/edan/{id}` (`resumen_localidades` + `sumatorias`). Los `reportes/*` son agregados sobre **varios/ todos** los EDAN con filtros.

---

## 9. Catálogos EDAN en v2

Los catálogos de EDAN ahora están disponibles en **v2** con las mismas rutas que en v1. La app solo necesita cambiar el prefijo `baseUrl` de `/api/v1` a `/api/v2`.

### Endpoints disponibles

| Catálogo | Endpoint | Registros | Descripción |
|---|---|---|---|
| Tipo de evento | `GET /api/v2/edan/tipo-evento` | 22 | Sismos, inundaciones, etc. |
| Estado EDAN | `GET /api/v2/edan/estados` | 6 | Borrador, Enviado, etc. |
| Tipo de localidad | `GET /api/v2/edan/tipo-localidad` | 11 | Urbana, rural, etc. |
| Estado localidad | `GET /api/v2/edan/localidades-estado` | 6 | Estados del ciclo de vida |
| Grupo vulnerable | `GET /api/v2/edan/grupo-vulnerable` | 8 | Grupos de protección social |
| **Grupo etario** | `GET /api/v2/edan/grupo-etario` | **4** | **Nuevo:** rangos de edad para impacto_poblacion |

Cada catálogo soporta CRUD completo: `GET /`, `GET /{id}`, `POST /`, `PUT /{id}`, `DELETE /{id}`.

### Grupo etario (nuevo)

```bash
curl -s "$BASE/api/v2/edan/grupo-etario" | python3 -m json.tool
```

| id | código | nombre | orden |
|---|---|---|---|
| 1 | ninas_ninos_0_5 | Niño (a) 0-5 años | 1 |
| 2 | escolar_6_18 | Escolar de 6-18 años | 2 |
| 3 | adulto_19_60 | Adulto de 19-60 años | 3 |
| 4 | adulto_mayor_60 | Adulto mayor de 60 años adelante | 4 |

> **Recomendado:** usar `id_grupo_etario` (int) en lugar del campo legacy `rango` (string). El campo `rango` se mantiene en la respuesta por compatibilidad pero está deprecado para escritura.

---

## 10. Sync EDAN + Consolidar Pendientes (v2)

Estos 3 endpoints completan la compatibilidad entre la app Flutter y la API v2. Tienen la misma firma que en v1.

### `GET /edan/consolidar/pendientes`

Lista las localidades huérfanas listas para consolidar, agrupadas por municipio/tipo_evento.

```bash
curl -s "$BASE/api/v2/edan/consolidar/pendientes" -H "$H" | python3 -m json.tool
# Con filtro:
curl -s "$BASE/api/v2/edan/consolidar/pendientes?id_municipio=70101&estado=aprobado" -H "$H"
```

| Param | Tipo | Descripción |
|---|---|---|
| `id_municipio` | int, opcional | Filtrar por municipio del UGR |
| `estado` | string, opcional | ILIKE sobre nombre de estado (ej: `aprobado`) |
| `id_estado` | int, opcional | ID exacto de estado |

### `POST /edan/sync`

Push de EDANs desde la app móvil (offline-first). Ejecuta upsert por EDAN.

```bash
curl -s -X POST "$BASE/api/v2/edan/sync" -H "$H" -H "$CT" \
  -d '{"edans": [{"id_local": "uuid-abc", "localidad": "Test", "id_municipio": 70101, "id_tipo_evento": 1}]}'
```

Respuesta por fila: `aplicado`, `id_local`, `id_edan`, `conflicto`, `tombstone`, `data`, `error`.

### `GET /edan/sync/pull`

Descarga EDANs del usuario para sincronización incremental.

```bash
curl -s "$BASE/api/v2/edan/sync/pull?skip=0&limit=50" -H "$H"
# Con filtro de fecha:
curl -s "$BASE/api/v2/edan/sync/pull?fecha_desde=2026-08-01T00:00:00" -H "$H"
```

| Param | Tipo | Descripción |
|---|---|---|
| `id_usuario` | int, opcional | Solo admin/rol 9 puede consultar otros usuarios |
| `fecha_desde` | ISO timestamp | Filtra `fecha_modificacion >= fecha_desde` |
| `skip` | int | Offset (default 0) |
| `limit` | int | Máximo 1000 (default 50) |

### `GET /edan/localidades/municipio/{id_municipio}`

Devuelve TODAS las localidades de un municipio (huérfanas + consolidadas), de TODOS los usuarios, con la estructura completa (14 secciones anidadas).

```bash
curl -s "$BASE/api/v2/edan/localidades/municipio/70101" -H "$H" | python3 -m json.tool
# Con filtros:
curl -s "$BASE/api/v2/edan/localidades/municipio/70101?estado=aprobado&solo_huerfanas=true" -H "$H"
```

| Param | Tipo | Descripción |
|---|---|---|
| `id_tipo_evento` | int, opcional | Filtrar por tipo de evento |
| `id_estado` | int, opcional | ID de estado de localidad |
| `estado` | string, opcional | Nombre de estado (ILIKE, ej: `aprobado`) |
| `solo_huerfanas` | bool, opcional | `true`=solo huérfanas, `false`=solo consolidadas, `null`=todas |
| `id_usuario` | int, opcional | Filtrar por usuario creador |
| `con_foto` | bool, opcional | `true`=solo con foto, `false`=solo sin foto |
| `skip` | int | Offset (default 0) |
| `limit` | int | Máximo 500 (default 50) |

### `GET /edan/localidades/municipio/{id_municipio}/resumen`

Conteos agregados de todas las localidades de un municipio: total, huérfanas vs consolidadas, por estado, por tipo de evento, totales de población/familias afectadas.

```bash
curl -s "$BASE/api/v2/edan/localidades/municipio/70101/resumen" -H "$H" | python3 -m json.tool
```

> **Nota:** los endpoints `POST /localidades/sync`, `GET /localidades/sync/pull`, `PUT /localidades/{id}` y `DELETE /localidades/{id}/proteccion/{id}` son **código muerto** en la app (nadie los llama). No se portaron a v2 intencionalmente. Si se necesitan en el futuro, se agregan con la misma firma v1.

---

## 11. Checklist de migración app/web (v1 → v2)

1. Cambia el `baseUrl` de `/api/v1` a `/api/v2`. Nada más.
2. (Recomendado) En v2 puedes usar `id_local` (UUID) en paths de secciones para **envío en paralelo** el primer sync.
3. Si usas la sección como **grupo o array**, la respuesta de errores es `errors[]` por fila (no un 422 global).
4. Para ediciones sin foto usa el endpoint JSON (`POST .../danos-viales`). Para ediciones con foto muy reciente viajando en el mismo lote, usa el endpoint `/con-foto` con el mismo `id_seccion`.
5. Estados de localidad: `2 = Enviado UGR` para que el UGR vea data fresca.
6. Revisa `/docs/v2` → cada sección tiene su ejemplo en "Request body / Examples".

---

## 12. Verificación rápida del despliegue

```bash
curl -s $BASE/health                       # {"status":"ok"}
curl -s $BASE/                            # versión 1.4.0 + rutas de docs
curl -s $BASE/docs/v2                     # Swagger interactivo v2 (agrupado)
curl -s $BASE/openapi.v2.json | python3 -c "import sys,json; print(len(json.load(sys.stdin)['paths']))"
```

> **Nota:** `/docs/v2` usa `swagger-ui-plugin-hierarchical-tags`: los tags con `>` se anidan
> (ej. `EDAN_LOCALIDADES > Danos Viales (con foto)`). También puedes revisar `/docs/v1` si necesitas el esquema legacy.