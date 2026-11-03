# Cambios 2026-10-16 — LWW total, foto 1:1 y flujo completo POST→PUT (§20.14/§20.15/§20.16)

> **GUÍA PARA LA APP (Flutter).** Familia afectada: **solo** APIs nuevas
> (`/api/v2/edan/formularios*`, `/fotografias`, `/sync`). El **v2 legacy y el
> v1 quedan intactos**. Resumen institucional en `PLAN_APIS_V2_EDAN.md`
> §20.14 (LWW) y §20.15 (PUT /completo + estados booleanos).
> Todos los ejemplos de abajo fueron ejecutados contra la API real
> (2026-10-16, 4 workers) y sus respuestas están pegadas tal cual.

---

## IMPORTANTE — Flujo de la app (contrato de sincronización, ÚNELO BIEN)

Este es el flujo completo que la app debe implementar. Compuesto por:
**POST crea → flag sucia en SQLite local → consulta `/estados` al abrir →
solo envía lo sucio → el servidor resuelve.**

```
┌─ CREAR ────────────────────────────────────────────────────────────────┐
│ POST /formularios/completo   (documento completo, una sola llamada)    │
│   200 → creado. Marcá el registro local como "limpio" (flag=false).    │
│   409 → YA EXISTE. NO es un error de tu flujo: cambia a PUT.          │
└────────────────────────────────────────────────────────────────────────┘
┌─ AL ABRIR LA APP / sincronizar ────────────────────────────────────────┐
│ GET /formularios/estados?localidad=X&todos=true                       │
│         &fecha_modificacion_desde=<watermark guardado localmente>      │
│   → por cada item: "tiene_cambios": true|false                         │
│   true  → GET /formularios/{uuid}/completo  y refrescá la copia local  │
│            (al bajar, asentá el watermark = fecha_modificacion)        │
│   false → nada que bajar.                                              │
└────────────────────────────────────────────────────────────────────────┘
┌─ ENVIAR ───────────────────────────────────────────────────────────────┐
│ Tu SQLite local tiene una columna dirty (flag sucia) por formulario/   │
│ registro que VOS modificaste offline.                                  │
│   solo_enviados = registros con dirty = true                           │
│   PUT /formularios/completo   (mismo JSON que devolvió GET /completo)  │
│     "hubo_cambios": false → no-op, no se escribió nada.                │
│     "hubo_cambios": true  → aplicado; limpiá la flag local (dirty=0).  │
└────────────────────────────────────────────────────────────────────────┘
```

Reglas que la app **NO** debe romper:

1. **POST solo crea.** El mismo JSON reenviado da **409** (no regraba).
   Editar = `PUT /formularios/completo` con el mismo cuerpo y el uuid en
   el body. El 409 trae mensaje: *"…use PUT /formularios/completo"*.
2. **La app no decide si hubo cambios: lo decide el servidor.** Vos mandás
   el documento sucio; la respuesta trae `hubo_cambios` (bool) y
   `cambios` (lista de qué cambió). `false` = no-op total: **cero
   escrituras** (ni UPDATEs, ni bump de `fecha_modificacion`, ni watermark
   nuevo). La app solo debe confiar en ese booleano para limpiar su flag.
3. **`tiene_cambios` es booleano estricto, nunca `null`.**
   - Sin `fecha_modificacion_desde` → `false` para todos.
   - Con watermark → `true` sii `fecha_modificacion > watermark`
     (**estricto**; watermark **igual** a la fecha visto → `false`, ya
     asentado).
   - `fecha_modificacion_desde` **NO filtra la lista**: `items` y `total`
     son idénticos con o sin el parámetro; solo cambia el flag. Podés
     pedir `todos=true` + watermark en la misma llamada.
4. **El watermark tiene el MISMO formato que te devuelve
   `fecha_modificacion` en las respuestas** (ej.
   `2026-10-16T10:30:29.945997`, sin offset `Z`/`-04:00`). Guardá tal cual
   el string que llega del servidor y reenvialo tal cual. No lo parsees ni
   le agregues zona horaria (en la URL, si hace falta, escapá `:` como
   `%3A` o mandalo crudo en query string).
5. **Bajá el documento completo con `GET /formularios/{uuid}/completo`**
   (devuelve `{cabecera, secciones…, fotos}`) y **reenvialo tal cual con
   PUT** — el PUT acepta **ambos formatos**: plano (campo `danos_vivienda`
   como objeto) y el formato anidado exacto del GET (`cabecera:{...}` +
   `fotos`). Round-trip GET→PUT sobre un documento sin cambios = **no-op
   verificado** (`hubo_cambios:false`).
6. **Solo enviás lo sucio (flag local `true`).** Podés mandar el documento
   completo sucio o solo la sección cambiada vía endpoints sueltos
   (`POST/PUT .../secciones/{tipo}/{uuid}`); ambos caminos son idempotentes
   y LWW. Lo limpio (dirty=false) **no se envía** — evita escrituras
   fútiles y el no-op garantiza 0 writes aunque mandes de más.
7. **400 primero, existencia después.** Las reglas estáticas (payload
   inválido) se evalúan **antes** de mirar si el uuid existe: un payload
   malo devuelve 400 aunque el documento exista (y no lo toca).
8. **Si `GET /estados` no puede determinarse** (sin parámetro) el flag es
   `false`: la app asume "nada nuevo" y no rompe.

Ejemplo de ciclo completo real (respuestas de la API, 2026-10-16):

```http
# 1) Crear
POST /api/v2/edan/formularios/completo
→ 200 {"success":true,"message":"Formulario completo creado"}

# 2) Mismo JSON de nuevo
POST /api/v2/edan/formularios/completo
→ 409 {"detail":"El formulario ya existe (uuid_edan_localidad=…d001).
        POST /formularios/completo es SOLO creación: para editar el
        documento completo use PUT /formularios/completo con el mismo JSON."}

# 3) Al abrir: ¿hay algo nuevo desde mi watermark?
GET /formularios/estados?localidad=EJEMPLO_APP_WM&todos=true
    &fecha_modificacion_desde=2026-10-16T00:00:00
→ "tiene_cambios": true     (fecha_modificacion 10:30:29 > 00:00:00)

# 4) Bajo el documento
GET /formularios/aaaaaaaa-…d002/completo  → 200, documento completo

# 5) Edito localmente (dirty=true) y envío
PUT /api/v2/edan/formularios/completo      (mismo JSON del GET)
← 200 {"message":"Documento actualizado",
       "data":{"hubo_cambios":true,
               "cambios":["cabecera","impacto_poblacion"],
               "aplicados":9,…}}

# 6) Reenvío idéntico (la flag ya no importa)
PUT /api/v2/edan/formularios/completo      (mismo JSON)
← 200 {"message":"Documento sin cambios",
       "data":{"hubo_cambios":false,"cambios":[],
               "resultados":[],"aplicados":0,…}}   ← 0 escrituras

# 7) Al abrir de nuevo con mi watermark asentado (= fecha del paso 5)
GET /formularios/estados?…&fecha_modificacion_desde=2026-10-16T10:30:30.063189
→ "tiene_cambios": false    (igualdad → ya visto)
```

---

## 1. La regla en una frase

**LWW total — "gana el último que llega" + PUT para editar.** Se eliminó
`version` de todo el contrato: **no se envía, no se valida (ya NO hay 409
por versión) y no se recibe** en ninguna respuesta. La app manda campos de
 negocio + `uuid_*`; el 409 **solo** aparece en `POST /completo` cuando el
documento ya existe (señal de "usa PUT").

Motivo: la app no necesita UI de "tu versión o la mía"; el modelo offline
gana con "el último write gana" + pull posterior. Elimina la UI de
`conflicto` del flujo de la app.

---

## 2. Qué cambió (checklist para el desarrollador de la app)

| Antes (obsoleto) | Ahora (obligatorio) |
|---|---|
| POST `/completo` creaba **o** regrababa | POST = **solo creación**; reenvío = **409** → editar con **PUT `/formularios/completo`** |
| Edición del documento completo sin ruta clara | **PUT `/formularios/completo`** con el mismo JSON (uuid en body); también acepta el formato anidado del GET |
| PUT/POST con `"version": N` | **Sin** `version`. Si la envías se acepta y descarta |
| Respuestas con `"version": N` | **Nunca** aparece en ninguna respuesta |
| 409 + `version_servidor`/`version_cliente` | Imposible por versión. Aplica el último que llega y devuelve 200 |
| Push con estado `conflicto` | Solo `aplicado` \| `error`; `conflictos` siempre 0 |
| `GET /estados` con `tiene_cambios` nullable y que filtraba la lista | **Booleano estricto** (`false` sin watermark) y el watermark **solo marca el flag**, no filtra |
| Decidir localmente si "hubo cambios" | **El servidor lo decide**: respuesta `hubo_cambios` + `cambios[]`; no-op = 0 escrituras |
| Releer `version` tras subir foto | `POST /fotografias` trae **`fila_dueña`** con `fotografia` actualizado |
| Varios `uuid_fotografia` activos por fila | **1 foto activa por fila**: la anterior queda `borrado_logico=true` |

---

## 3. Contrato de los endpoints (ejemplos reales)

Base: `http://<host>:8000/api/v2/edan`. Auth: `Authorization: Bearer <JWT>`
(roles escritura 6/7; lectura admin también OK).

### 3.1 Crear documento completo — `POST /formularios/completo` (SOLO creación)

```http
POST /api/v2/edan/formularios/completo
Content-Type: application/json

{
  "uuid_edan_localidad": "aaaaaaaa-0000-4000-8000-00000000d001",
  "localidad": "EJEMPLO_APP_MD",
  "id_municipio": 10101,
  "id_usuario": 1207,
  "imp_impacto_poblacion": true,
  "imp_danos_vivienda": true,
  "imp_danos_agricultura": true,
  "imp_danos_pecuarios": true,
  "impacto_poblacion": [ { "uuid_registro": "…", "heridos": 3, "desaparecidos": 0 } ],
  "danos_vivienda": { "uuid_registro": "…", "comunidad": "…", "viviendas": [ … ] },
  "danos_agricultura": [ … ],
  "danos_pecuarios": [ … ]
}
```

Respuesta (recortada — 5 claves originales, compatibilidad intacta;
`grup_*` planos, sin `version`, sin nodo `grupos`):

```json
{
  "success": true,
  "message": "Formulario completo creado",
  "data": {
    "resultados": [
      { "indice": 0, "tipo": "impacto_poblacion", "seccion": "impacto_poblacion",
        "uuid_registro": "aaaaaaaa-0000-4000-8000-53509dfd3c56",
        "estado": "aplicado", "message": "OK" },
      { "indice": 4, "tipo": "danos_vivienda", "seccion": "danos_vivienda",
        "uuid_registro": "aaaaaaaa-0000-4000-8000-23aa53b2d6dd",
        "estado": "aplicado", "message": "OK" },
      { "indice": 5, "tipo": "vivienda",
        "uuid_registro": "aaaaaaaa-0000-4000-8000-162e81669e63",
        "estado": "aplicado", "message": "OK" }
    ],
    "aplicados": 9,
    "conflictos": 0,
    "errores": 0,
    "formulario": { "cabecera": { "id_edan_localidad": 343227,
      "localidad": "EJEMPLO_APP_MD", "grup_poblacion": true, "…": "…" },
      "secciones_resumen": [ … ] }
  }
}
```

Reenviar el mismo JSON → **409**:

```json
{ "detail": "El formulario ya existe (uuid_edan_localidad=aaaaaaaa-0000-4000-8000-00000000d001). POST /formularios/completo es SOLO creación: para editar el documento completo use PUT /formularios/completo con el mismo JSON." }
```

Payload inválido → **400 antes de mirar existencia** (probado: mismo
payload da 400 tanto si el uuid existe como si no, y en ninguno de los dos
casos se escribe nada).

### 3.2 Editar documento completo — `PUT /formularios/completo`

Mismo JSON que el POST (uuid obligatorio en el body). **Acepta también el
formato anidado exacto de `GET /…/completo`** (`cabecera:{…}` + secciones
planas + `fotos`) — round-trip sin transformaciones en la app.

```http
PUT /api/v2/edan/formularios/completo
Content-Type: application/json

{ "uuid_edan_localidad": "aaaaaaaa-…d001", "localidad": "EJEMPLO_APP_MD",
  "total_poblacion_afectada": 444, "imp_…": true, "impacto_poblacion": [ … ] }
```

Hubo cambios:

```json
{
  "success": true,
  "message": "Documento actualizado",
  "data": {
    "hubo_cambios": true,
    "cambios": ["cabecera", "impacto_poblacion"],
    "resultados": [ { "indice": 0, "tipo": "impacto_poblacion", "…": "…",
                      "estado": "aplicado", "message": "OK" } ],
    "aplicados": 9,
    "conflictos": 0,
    "errores": 0,
    "formulario": { "cabecera": { "…": "…" }, "secciones_resumen": [ … ] }
  }
}
```

- `cambios` puede traer `"cabecera"` y/o el tipo de sección (p. ej.
  `"impacto_poblacion"`), incluyendo purgas (`imp_*=false` con filas),
  altas y bajas de filas 1:N, y cambios en la fila 1:1
  (`danos_vivienda` incluye su hija `viviendas[]`).
- No-op (mismo documento):

```json
{
  "success": true,
  "message": "Documento sin cambios",
  "data": { "hubo_cambios": false, "cambios": [], "resultados": [],
            "aplicados": 0, "conflictos": 0, "errores": 0,
            "formulario": { "cabecera": { "…": "…" } } }
}
```

- No-op = **cero escrituras**: no hay UPDATE (los upserts comparan
  campo a campo antes de tocar la fila), no se mueve
  `fecha_modificacion` → el watermark de nadie queda invalidado.
- Errores del PUT: **404** si el uuid no existe (PUT nunca crea);
  **400** por reglas estáticas (evaluadas primero); **403** por scope/rol
  — el chequeo de acceso se hace **también** en el no-op.
- Campos inmutables (`id_usuario`/autor, ids internos) no cambian ni en
  un PUT que los traiga distintos.
- `version` en el body: aceptada y descartada (compat con colas viejas).

### 3.3 Estados y watermark — `GET /formularios/estados`

```http
GET /api/v2/edan/formularios/estados?localidad=EJEMPLO_APP_WM&todos=true
    &fecha_modificacion_desde=2026-10-16T00:00:00
```

```json
{ "success": true,
  "data": {
    "items": [ {
      "uuid_edan_localidad": "aaaaaaaa-…d002",
      "localidad": "EJEMPLO_APP_WM",
      "fecha_modificacion": "2026-10-16T10:30:29.945997",
      "grup_poblacion": true, "grup_vivienda": true, "…": "…",
      "tiene_cambios": true
    } ],
    "resumen": { "por_estado": [ … ], "por_grupo": [ … ] },
    "total": 1 } }
```

Comportamiento probado (suite `test_put_completo.sh`, sección F):

| Llamada | `tiene_cambios` |
|---|---|
| Sin `fecha_modificacion_desde` | `false` (nunca `null`) |
| Watermark **anterior** a `fecha_modificacion` | `true` |
| Watermark **igual** a `fecha_modificacion` | `false` (asentado) |
| Watermark **posterior** | `false` |
| Con/sin watermark, `items` y `total` | **idénticos** (no filtra) |

### 3.4 Descargar el documento — `GET /formularios/{uuid}/completo`

```json
{ "success": true, "data": {
  "cabecera": { "uuid_edan_localidad": "…", "localidad": "…",
    "grup_poblacion": true, "pendiente_actualizacion": false,
    "id_usuario": 1078,
    "usuario": { "id_usuario": 1078, "usuario": "10000006", "nombre": "LUIS HUANCA",
                 "id_rol": 7,
                 "rol": { "id_rol": 7, "nombre": "Responsable Local", "descripcion": "…" } },
    "municipio": { "id": 10101, "codigo_ine": "040101", "nombre": "Sucre",
                   "id_departamento": 4, "id_provincia": 401,
                   "departamento": { … }, "provincia": { …, "departamento": { … } } },
    "edan": null,          // si id_edan existe: {…, estado_edan:{…}, municipio:{…}, tipo_evento:{…}}
    "importacion": null,   // clave SIEMPRE presente; objeto si id_importacion (con usuario dentro)
    "sin version, sin nodo grupos, sin id_local ni id_seccion": true },
  "impacto_poblacion": [ … ], "danos_vivienda": [ … ],
  "servicios_basicos": [ … ], "fotos": [ … ] } }
```

Los **`id_*` de la cabecera traen su JSON anidado recursivo (§20.16)**:
`id_usuario → usuario → rol`, geografía (`municipio/provincia →
departamento`), `edan → estado_edan/municipio/tipo_evento` e
`id_importacion → importacion`. Si `id_edan` es NULL (primeras creaciones)
o `id_importacion` es NULL, las claves `edan`/`importacion` vienen en
**null**. Identidad (`id_edan_localidad`, `uuid_*`) sin JSON; `id_local` y
`id_seccion` **ya no se exponen** (las APIs nuevas van solo con uuid).

Claves de sección siempre presentes (aunque vacías, salvo
`?comprimido=true`, que omite las **inactivas**: sin flag `imp_*` y sin
filas). Este documento **se reenvía tal cual
por PUT /formularios/completo** → sin cambios = `hubo_cambios:false`.

### 3.5 Secciones sueltas (1:N y 1:1) — sin `version`

```http
POST /formularios/{uuid}/secciones/danos_agricultura     # crea fila (200)
PUT  /formularios/{uuid}/secciones/danos_agricultura/{uuid_registro}  # edita (LWW)
```

- Respuesta de POST con la **cadena de uuids** lista (`id_*`,
  `uuid_registro`, `uuid_edan_localidad`, `fecha_modificacion`) — sin GET
  extra para saber dónde quedó.
- Upsert **idempotente**: reenviar el mismo payload sin cambios no
  escribe (sin UPDATE, sin bump).
- `fotografia` en el payload de filas: aceptada y **descartada**.

### 3.6 Subir foto — `POST /fotografias` (multipart) — **1 activa por fila**

```http
POST /api/v2/edan/fotografias
Content-Type: multipart/form-data

uuid_fotografia=aaaaaaaa-0000-4000-8000-00000000c031
tipo_entidad=danos_agricultura
uuid_registro=aaaaaaaa-0000-4000-8000-00000000c011
archivo=<imagen real; magic bytes validados; ≤10MB>
```

Respuesta con **`fila_dueña`** (fila dueña ya con el path espejo — la app
actualiza su foto local sin GET extra):

```json
{ "success": true,
  "message": "Foto guardada (upsert idempotente por uuid_fotografia)",
  "data": {
    "uuid_fotografia": "aaaaaaaa-…c031", "tipo_entidad": "danos_agricultura",
    "uuid_registro": "aaaaaaaa-…c011",
    "ruta_archivo": "/uploads/reports/010101/010101_1207_921136565f4e.png",
    "borrado_logico": false, "…": "…",
    "fila_dueña": { "id_dano_agricultura": 5891, "tipo_cultivo": "MAIZ",
      "hectareas_afectadas": 8,
      "fotografia": "/uploads/reports/010101/010101_1207_921136565f4e.png",
      "uuid_registro": "aaaaaaaa-…c011" } } }
```

- 1 activa por fila: subir foto B a la misma fila pone A en
  `borrado_logico=true` (índice único parcial lo garantiza). Reenviar la
  MISMA foto (mismo uuid) reemplaza el archivo: no duplica.
- Debajo de `danos_vivienda`, las `viviendas[]` llevan su propia
  `fotografia`; el espejo `fotos[]` del GET se construye solo.

### 3.7 Lote offline — `POST /sync/push` / `GET /sync/pull`

```http
POST /api/v2/edan/sync/push
{ "id_dispositivo": "disp-app-1", "items": [
    { "accion": "upsert", "tipo": "seccion", "tipo_seccion": "danos_pecuario",
      "datos": { "uuid_edan_localidad": "…", "uuid_registro": "…",
                 "especie": "BOVINO", "animales_afectados": 3 } },
    { "accion": "borrar", "tipo": "seccion", "tipo_seccion": "danos_agricultura",
      "datos": { "uuid_edan_localidad": "…", "uuid_registro": "…" } } ] }
```

```json
{ "success": true, "message": "Lote procesado", "data": {
  "resultados": [ { "indice": 0, "estado": "aplicado", "…": "…" },
                  { "indice": 1, "estado": "error", "tipo": "seccion",
                    "message": "Fila de danos_agricultura no encontrada: …" } ],
  "aplicados": 1, "conflictos": 0, "errores": 1 } }
```

Cola local: `aplicado` → marca y borra de la cola; `error` → reintento
solo si recuperable; un ítem en `error` no tumba el lote; **ya no existe
`conflicto`**.

```http
GET /api/v2/edan/sync/pull?desde=2026-10-15T00:00:00&limit=200
```

Devuelve `watermark` + `formularios`/`secciones`/`viviendas`/`fotografias`
+ `tombstones` (sin `version` en ningún lado). Tras aplicar:
`POST /sync/ack {"id_dispositivo":"…","watermark":"…"}`.

> Nota: `pull` es para **bajar cambios de otros**. El chequeo de "¿mi
> formulario tiene cambios del servidor?" al abrir la app es
> `GET /formularios/estados` con tu watermark (sección 3.3).

### 3.8 Otros GET

- `GET /formularios/{uuid}` → **documento completo** `{cabecera,
  <secciones>, fotos, secciones_resumen}` — misma cabecera §20.16 (todo
  `id_*` con su JSON; sin `id_local`/`id_seccion`) y mismas claves de
  sección que `/completo`.
- `GET /formularios` → `data[]` son **documentos completos** (mismo formato
  de la línea anterior) en vez de cabeceras sueltas; mismos filtros
  (`id_departamento`, `id_provincia`, `id_municipio`, `localidad`, `todos`,
  `skip`, `limit`).
- **`modo` en ambos** (2026-10-19, §20.18 del PLAN): `comprimido`
  (default) = **sólo secciones activas** (flag `imp_*` true o con filas);
  `completo` = las 14 claves. Con `id_municipio=…&todos=true` se bajan
  **todos los del municipio en un solo GET**.
- `GET /formularios/{uuid}/completo` y `GET /sync/pull` (`formularios[]`) →
  idéntica cabecera recursiva.
- `GET /formularios/estados` → **intocado** (ligero: `id_usuario` crudo,
  sin `usuario`/`edan` anidados; sigue con `uuid_edan_localidad`).
- `GET /fotografias/{uuid}` y listados de la familia de catálogos: sin
  cambios de esta fase.

---

## 4. Reglas que NO cambian + reglas nuevas

No cambian (no son de versión):

- `imp_*` (14) obligatorias en `/completo`; `imp=false` + filas → 400.
- Enviados (estados 2/3/4/5): grupo `imp_*=true` exige ≥1 fila → 400 +
  rollback en POST/PUT cabecera, `/completo` y DELETE sección.
  `sync_push` usa `validar=False` (parcialidad offline OK).
- Sets 4/8 de campos; recálculo `grup_* := OR(imp_*)` en toda mutación;
  enviar `grup_*` en el wire → 400 (el cliente nunca los manda).
- uuid de ruta ≠ uuid de payload → 400.
- Foto: magic bytes validados (≤10 MB); dueña inexistente → 404; dueña
  de otro usuario → 403.

Nuevas (§20.15):

- **POST `/completo` solo crea** (409 si existe) y **las reglas estáticas
  van primero** (400 antes de cualquier 404/409 y sin escrituras).
- **PUT `/completo`** existe y requiere que el documento exista (404);
  acepta ambos formatos de JSON; responde `hubo_cambios`/`cambios`;
  no-op = 0 escrituras.
- **`GET /estados`**: `tiene_cambios` booleano estricto; watermark no
  filtra la lista; sin watermark → `false`.
- Upserts de cabecera, sección y vivienda **idempotentes campo a campo
  (`_cmp_iguales`)**: filas sin cambios no se actualizan (importa para
  `hora_evento`, fechas, decimales y round-trip GET→PUT).
- `GET → PUT` completa: `_SISTEMA`/`_FK_OBJETOS` se descartan del payload
  (antes 400) para que el documento leído pueda reenviarse tal cual;
  claves realmente desconocidas siguen en 400.

Nuevas (§20.16):

- **Cabecera con TODO `id_*` + su JSON anidado recursivo** en los 4 GET de
  la familia (`/formularios`, `/{uuid}`, `/completo`, `/sync/pull`):
  `id_usuario → usuario → rol`, geografía completa, `edan →
  estado_edan/municipio/tipo_evento`, `id_importacion → importacion`.
- `edan`/`importacion` son claves **siempre presentes**: null si el id es
  NULL (`id_edan` puede venir vacío en las primeras creaciones).
- **Los GET de las APIs nuevas NO traen `id_local` ni `id_seccion`**:
  identidad solo con uuid (`uuid_edan_localidad`, `uuid_registro`); el
  servidor los sigue escribiendo internamente. El legacy `/documento`
  (v1/v2 espejo) conserva su contrato con `id_local` sin cambios.

---

## 5. Cambios de implementación (solo referencia backend)

### `api/edan/service_v2_nuevas.py`
- `_validar_completo_payload(data) -> UUID`: reglas estáticas 400
  **antes** de existencia/escritura; `upsert_formulario_completo` → 409 si
  existe; `put_formulario_completo` → 404 si no existe, chequeo de acceso
  siempre, aplica con `_aplicar_completo`.
- `_aplanar_completo`: normaliza ambos formatos (plano y
  `cabecera:{…}`+`fotos`) a una estructura única de trabajo.
- `_cmp_iguales(actual, nuevo)` (bool/num/datetime/date/time/UUID/str) y
  `_diff_completo`, `_diff_seccion_filas` (hijas `viviendas[]` en el
  branch 1:1 de `danos_vivienda`), `_diff_fila`, `_diff_hijas` → alimentan
  `hubo_cambios`/`cambios` y los UPDATEs condicionales.
- `upsert_formulario`/`upsert_seccion`/`upsert_vivienda`: `SELECT *` +
  diff → **UPDATE solo de columnas cambiadas**; sin diff = sin UPDATE y
  sin bump de `fecha_modificacion`.
- `_upsert_seccion` descarta `_SISTEMA` y `_FK_OBJETOS` (round-trip);
  claves desconocidas reales → 400.
- `list_formularios_estados`: sin filtro SQL por fecha; flag
  `bool(fm and fm > desde.isoformat())` por item; sin `desde` → `false`.
- `list_formularios` / `get_formulario` (§20.18): los GET de la lista y de
  `{uuid_ref}` devuelven el **documento completo** vía
  `get_formulario_completo(chequear_acceso=False)` con el nuevo parámetro
  `modo`; el `SELECT` de la lista sólo pide `uuid_edan_localidad`.
- `get_formulario_completo`: `comprimido` = secciones **activas**
  (`imp_*` true **O** con filas); antes = sólo "con filas".

### `api/edan/router_v2_nuevas.py`
- `PUT /formularios/completo` en la línea 55, **antes** de
  `PUT /formularios/{uuid_ref}` (rutas verificadas: sin colisión).
- POST `/completo` → create-only, summary y docstring 409/400.
- Respuesta PUT → `SuccessResponse(message="Documento actualizado"
  | "Documento sin cambios")`; POST mantiene las 5 claves originales.
- Docstrings de `/estados` con el bloque FLUJO DE LA APP.
- `GET /formularios` y `GET /formularios/{uuid_ref}`: query param `modo`
  (default `comprimido`, orden según la convención de listados) y
  docstrings de documento completo (§20.18 del PLAN).

### `api/edan/schemas_v2_nuevas.py`
- `FormularioCompletoUpsert`: `model_validator(mode="before")` →
  `_aplana_formato_get` (acepta el formato del GET).
- `FormularioUpsert` (PUT `/formularios/{uuid}`) sigue `extra="forbid"`:
  ese endpoint **no** acepta documentos con secciones (usar `/completo`).

### BD
- Índice único parcial `edan.uq_fotografias_activa` UNIQUE
  `(tipo_entidad, uuid_registro) WHERE borrado_logico=false`.
- Columna `version` + trigger permanecen (migración intacta) pero el
  contrato no las usa.

---

## 6. Pruebas (2026-10-16)

Nueva suite `test_put_completo.sh`: **63 PASS / 0 FAIL** — secciones:
A creación y 409; B no-op sin bump de `fecha_modificacion` (leído de la
BD); C cambios/purga/reactivación; D 404/400-prueba-primero/LWW;
E idempotencia de upserts sueltos; F estados booleano estricto +
watermark no filtra; **G flujo de la app completo** (crea→edita→
`/estados` true→PUT→watermark asentado→false); H round-trip GET→PUT
no-op; I carrera de doble PUT; **J §20.16** (cabecera ids→JSON:
`id_usuario→usuario→rol`, geografía recursiva, `edan` objeto/null,
`importacion` con valor y null, lista/pull/completo idénticos, `/estados`
intacto) y **J8 sin `id_local`/`id_seccion` en los 6 GET**.

9 suites completas (todas migradas a POST-create-only + PUT + estados
booleano):

| Suite | PASS |
|---|---|
| `test_put_completo.sh` | 63 |
| `test_nuevas.sh` | 51 |
| `test_completo.sh` | 23 |
| `test_invariante.sh` | 25 |
| `test_crud_sync.sh` | 44 |
| `test_lww.sh` | 58 |
| `test_regresion_grup.sh` | 18 |
| `test_multifila.sh` | 46 |
| `test_final.sh` | 76 |

**Total: 9 suites, 404 PASS / 0 FAIL**, ejecutadas contra la instancia con
4 workers tras el reinicio final. Sin linter en el repo: verificación =
`py_compile` + `import api.main` + suites end-to-end.

---

## 7. Migración de clientes (qué tocar en el código de la app)

1. **Crear**: `POST /formularios/completo`; tratar `409` como "ya existe →
   editar con PUT" (no es un error fatal).
2. **Editar**: `PUT /formularios/completo` con el mismo JSON; leer
   `hubo_cambios` y `cambios[]` de la respuesta; si `true`, limpiar la
   flag dirty local; si `false`, asumir 0 escrituras.
3. **Columna dirty en SQLite** por formulario/registro local
   (`dirty=1` al modificar offline; `0` al crear/confirmar).
4. **Al abrir**, `GET /formularios/estados?…&fecha_modificacion_desde=`
   con el watermark guardado (string exacto de `fecha_modificacion`);
   `tiene_cambios:true` → `GET /formularios/{uuid}/completo` y asentar el
   watermark.
5. **Enviar solo dirty=true**; el resto no viaja.
6. **Borrar** de modelos Dart el campo `version` (o ignorarlo) y dejar de
   enviarlo; **quitar** la UI/manejo de 409 por versión y de `conflicto`
   (push solo `aplicado`/`error`).
7. Tras `POST /fotografias`, **usar `fila_dueña.fotografia`** para el
   espejo local; al reemplazar foto en el mismo registro, borrar la foto
   local anterior (el servidor solo mantiene 1 activa).
8. **`id_local` ya no viene en los GET de las APIs nuevas** (ni
   `id_seccion`): identificar todo por `uuid_edan_localidad` /
   `uuid_registro` (el valor de `id_local` era exactamente ese uuid, así
   que el dato local no se pierde). Sigue llegando `id_usuario` crudo y,
   desde §20.16, también `usuario` (con `rol`) anidado en la cabecera.

---

## 8. EDAN padre (cabecera) — familia uuid (2026-10-18, §20.17 del PLAN)

> Se documenta **solo la familia del EDAN padre (cabecera)**: la parte de
> **edan_localidades** ya quedó cubierta en las secciones 1–7 de este
> archivo. Todo lo de abajo es para los endpoints de la **cabecera**
> (`/api/v2/edan/…` que NO son `formularios*`), incluida la app/FE que
> lista, abre, consolida y deshace EDAN. Ejecutado contra la API real
> (2026-10-18, 4 workers).

### 8.1 Qué cambió (checklist para el desarrollador de la app)

1. **`GET /api/v2/edan/` (listar) — MISMO path, contrato nuevo.** Los
   items ya **no traen `version` ni `id_local`**; traen `id_edan` +
   `uuid_edan`, todos los `id_*` con su JSON anidado (`usuario_ugr` con
   `rol`, `municipio` con `departamento/provincia`, `estado_edan`,
   `tipo_evento`, `importacion`) y `localidades[]` como **documentos
   completos** (`{cabecera, 14 secciones, fotos}`) con id+uuid en todos
   los niveles. Filtros y scope iguales (6/7 ven sólo los suyos;
   `limit`/`skip`/`todos` + recientes primero).
2. **`GET /api/v2/edan/{ref}` — ahora acepta `uuid_edan` O `id_edan`**
   (antes sólo id numérico). Respuesta = documento estilo nuevo (sin
   `version`/`id_local`; `modo=compacto` sigue agregando `sumatorias`).
   La app puede guardar/quedar con el uuid y dejar de depender del id.
3. **`POST /api/v2/edan/consolidar` — canónico sólo uuid:**

   ```json
   POST /api/v2/edan/consolidar
   {"uuid_edan": "<uuid generado por el cliente>",
    "localidades": ["<uuid_edan_localidad>", "…"]}
   ```

   - `uuid_edan` opcional (si no llega, lo genera el servidor). El mismo
     `uuid_edan` + las **mismas** localidades es reintento idempotente →
     200 con el EDAN; con otro conjunto (o subconjunto) → **409**.
   - Localidades: `aprobadas` (estado 3), sin EDAN y del mismo
     municipio/tipo_evento → si no, **400** con el mensaje clásico;
     uuid desconocido → 404; sólo roles 6/7 (otros → 403).
   - La respuesta **ya es el EDAN completo estilo nuevo** (cabecera
     con ids anidados + `localidades[]` documentos) — la app puede
     refrescar su copia sin un GET extra.
   - **Compatibilidad (2026-10-18)**: el body **legado deprecado**
     sigue aceptado — `{"id_municipio": …, "id_tipo_evento": …,
     "localidad_ids": [ids]}` (exactamente XOR con el canónico; la app
     actual **ya no recibe 422**). Paridad vieja: id desconocido o
     mun/tipo incoherentes → 400 clásico; `localidad_ids=[]` → 400
     "Debe incluir al menos una localidad". Cuando la app migre,
     envíe `localidades[]` con los uuid de
     `GET /consolidar/pendientes`.
4. **`PUT /api/v2/edan/{ref}/deshacer`** (antes `PUT /{id}/deshacer`,
   sólo id): acepta **uuid o id**, aplica directo (sin preview) y
   responde:

   ```json
   {"edan": {"id_edan": 17000, "uuid_edan": "…", "codigo_edan": "…"},
    "localidades_liberadas": 2,
    "localidades": [{"id_edan_localidad": 278,
                     "uuid_edan_localidad": "…",
                     "localidad": "Tulipan", "id_edan": null}, …]}
   ```

   Mismas validaciones de siempre: sólo Borrador, sólo el UGR que lo
   consolidó, sin documentos en el repositorio (400/403); tras deshacer,
   el EDAN desaparece (404) y las localidades vuelven a `pendientes`.
5. **`GET /api/v2/edan/consolidar/pendientes` — paridad + uuid.** Mismo
   comportamiento que siempre (grupos municipio+tipo_evento, conteos,
   totales, filtros `estado`/`id_estado`, scope, `total`), y **cada grupo
   trae ahora `localidades[]` con `id_edan_localidad` +
   `uuid_edan_localidad`** (+ `localidad`, `id_edan_localidad_estado`,
   `id_usuario`) además de `localidad_ids[]`. El paso de "consolidar" de
   la app puede enviar uuid directo sin pasar por ids.
6. **Alias `POST /api/v2/edan/formularios/{uuid}`** (contrato de la
   marca "identidad en la ruta"): igual que `POST /formularios` pero el
   uuid va en la URL; si el uuid de la ruta y el del body no coinciden →
   400. `POST /formularios/completo` NO cambió (sigue respondiendo con
   su propio schema, 422 si va vacío).
7. **Bug arreglado**: `GET /?con_foto=true` / `sin_foto=true` devolvía
   **500** (apuntaba a una columna inexistente `edan.edan.fotografia`);
   ahora filtra de verdad (EDAN con/sin fotos en alguna sección de sus
   localidades) → 200.
8. **Rutas viejas eliminadas** (sus paths ya no sirven el contrato
   viejo): `GET /edan/`, `GET /edan/{id}`, `GET /edan/consolidar/pendientes`,
   `PUT /edan/{id}/deshacer`, `POST /edan/consolidar` del router
   cabecera — todas cubiertas arriba con la forma nueva. **Sigue
   intacto**: `/reportes/*`, `/mis-resumen`, `/mis-estados`,
   `/mis-reportes`, `PUT /edan/{id}`, `DELETE /edan/{id}`,
   `POST /edan/consolidar/auto`, `PUT /edan/localidades/*` y todo el
   v1 (`/api/v1/…`).

### 8.2 Reglas que NO cambian

- Scope: 5/8/9 geográfico (403 fuera de jurisdicción); 6/7 listan sólo
  sus EDAN en `GET /`, pero **pueden abrir cualquier EDAN** en
  `GET /{ref}` (paridad con la API vieja).
- Estados/`estado_edan`, códigos, `pendiente_eliminacion/actualizacion`,
  `orden` de los EDAN: sin cambios.
- Las fotos siguen el flujo de la sección 1 (push de filas primero,
  fotos después) — compatible tal cual.
- El consolidado conserva internamente `id_local = uuid` en las
  localidades; la app no lo necesita (usa uuid).

### 8.3 Pruebas (2026-10-18)

Nueva suite `test_edan_cabecera.sh`: **60 PASS / 0 FAIL** (listados,
filtros incl. `con_foto` arreglado, obtención uuid/id/404/compacto,
scope rol 8/6, `PUT /{id}` legacy, pendientes con `localidades[]`,
consolidar canónico con idempotencia/409/400/404/403 **+ forma legada**
— 422 XOR/forbid, 200 con uuid del server, paridad 400 clásica,
idempotente con `uuid_edan` —, deshacer con respuesta nueva y
restauración de pendientes, alias de formularios, invariantes).
Total con las 9 suites previas: **10 suites — 459 PASS / 0 FAIL**
(399 + 60), tras reinicio con 4 workers.

### 8.4 Punch-list para la app Flutter (cambios Dart pendientes)

Sólo impactos de la familia EDAN padre (§20.16/§20.17). Archivos y
líneas según el análisis de compatibilidad del 2026-10-18:

1. **Parser de localidades en documento** — `models/edan.dart`:
   `EdanLocalidad.fromJson` (≈3323) espera campos planos y
   `_migrarLocalidades` (≈3386) no cubre la forma nueva
   `{cabecera, 14 secciones, fotos}` → hoy `localidades` queda **vacía**
   al hacer `Edan.fromJson` (≈3318). Ajustar para leer la cabecera desde
   `doc["cabecera"]` y las secciones/fotos como hermanos. Impacto si no
   se arregla: `edanToCardMap` (`edan_tab:383`) y detalle
   (`edan_tab:336/353`) muestran 0 localidades.
   *(Nota: la app ya maneja ids anidados en cabecera — eso sigue OK.)*
2. **`id_local` ya no existe en la respuesta** — `ugr_edan_tab:331`
   usaba `edan['id_local']` para localizar su copia SQLite; re-identificar
   por `uuid_edan` (o `id_edan`) con el patrón
   `uuidEdanLocalidad ?? idLocal` ya usado en el flujo de localidades.
3. **Migrar `consolidar` a uuid (opcional, sin urgencia)** —
   `api_service.dart:1143` / `ugr_localidades_tab:301`: el body viejo
   **ya funciona de nuevo** (forma deprecada), pero la forma canónica es

   ```json
   {"uuid_edan": "<uuid propio>",
    "localidades": ["<uuid_edan_localidad>", "…"]}
   ```

   tomando los uuid de `GET /consolidar/pendientes`
   (`data[].localidades[].uuid_edan_localidad`; patrón
   `uuidEdanLocalidad ?? idLocal` ya existe en la app).
4. **Respuesta de `deshacer`** (`api_service.dart` desconsolidar /
   `ugr_localidades_tab`): la nueva forma es
   `{edan{id_edan,uuid_edan,codigo_edan}, localidades_liberadas,
   localidades[{id_edan_localidad,uuid_edan_localidad,localidad,id_edan:null}]}`
   — usar `localidades_liberadas`/`localidades` en vez del shape viejo.
5. **Detalle/listado `GET /edan/{ref}` y `GET /edan/`** — ya sin
   `version`/`id_local`; la app no debe requerirlos (el backend los
   acepta y descarta si se envían, LWW total).

---

## 9. Documentos completos en los GET de la familia nueva (2026-10-19)

**Antes**: `GET /formularios` (lista) devolvía sólo cabeceras y
`GET /formularios/{uuid}` sólo `{cabecera, secciones_resumen}` → N+1 GET
para pintar un listado con datos.

**Ahora** ambos devuelven **el documento de `GET /formularios/{uuid}/completo`**
(ver §3.8 y §20.18 del PLAN):

```json
{ "cabecera": { "uuid_edan_localidad": "…", "id_edan_localidad": 343307,
                "imp_*": …, "grup_*": …, /* §20.16 recursivo */ },
  "impacto_poblacion": [ … ], "danos_vivienda": [ … ], /* + filas reales */
  "fotos": [ … ], "secciones_resumen": { … } }
```

- `modo=comprimido` (default): sólo **secciones activas** (`imp_*` true o
  con filas). `modo=completo`: las 14 claves siempre.
- Filtros intactos; `id_municipio=…&todos=true` baja **todos los del
  municipio** en un solo GET.
- Sin cambios: `GET /formularios/estados`, `GET /sync/pull`, respuestas de
  `POST`/`PUT /formularios`.
- Auditoría: los GET del EDAN padre (`GET /`, `GET /{ref}`) ya cumplen —
  cero `id_local`/`id_seccion` en toda la respuesta (ahora con aserciones
  recursivas en `test_edan_cabecera.sh`).

**Pruebas (2026-10-19)**: 10 suites **465 PASS / 0 FAIL** (459 + `test_nuevas`
§23-24 x4 + `test_edan_cabecera` x2; migradas a la forma de documento:
`test_final`, `test_invariante`, `test_lww`, `test_put_completo`).

---

## 10. Corrección: alcance del rol 6 (mapa UGR) + coordenadas como string (2026-10-19)

**Problema**: `GET /formularios?id_municipio=70101&todos=true` con un UGR
(rol 6) devolvía **solo sus formularios**, nunca las 38 del municipio → no
servía para poblar el mapa UGR (el legado
`GET /localidades/municipio/{id}` sí las traía).

**Corrección** — la API de listado es **general con filtros**; `sync/pull`
sigue siendo la vista del usuario:

| Endpoint | Rol 6 (UGR Municipio) |
|---|---|
| `GET /formularios` | **todo su municipio** (`id_municipio` forzado; el del query se ignora, igual que rol 8) |
| `GET /formularios/{uuid o id}` (+ `/completo`, secciones, viviendas, foto) | **lectura en todo su municipio** |
| escritura (POST/PUT/DELETE/push) | **solo lo propio** (ajeno → 403) |
| `sync/pull`, `GET /formularios/estados` | **solo lo propio** (sin cambios) |

Rol 7 y el EDAN padre no cambian.

**Coordenadas**: `coordenada_lat`/`coordenada_lon` salen ahora como
**string** con la escala de la columna (`"-17.81277980"`), igual que el
legado — el parser del mapa ya espera texto.

Pruebas: `test_final.sh` §B (b3..b3g) y `test_crud_sync.sh`/`test_final.sh`
M7 actualizadas; correr las 10 suites.

---

## 11. APIs de resumen (v2.60) + fechas desde/hasta (2026-10-20)

### 11.1 Cuatro GET nuevos (tableros)

Base `/api/v2/edan/resumen`, **token obligatorio pero sin scope por rol**:

| Endpoint | Qué trae |
|---|---|
| `GET /resumen/formularios/contadores` | tarjetas de formularios (totales, estados, 9 grupos, tipo de evento, geografía) |
| `GET /resumen/formularios/graficas` | **65 gráficas** multi-tipo + `tabla` de cada una |
| `GET /resumen/edan/contadores` | tarjetas de EDAN padre + bloque `aprobaciones` |
| `GET /resumen/edan/graficas` | **48 gráficas** (incluye aprobaciones e importaciones) |

Para la app:

- **Sin paginación**: son consultas puntuales agregadas (no usar
  `limit/skip/todos`).
- **Filtros por query, todos combinables con AND**: geografía, evento
  (`id_tipo_evento`, `grupo_evento`), fechas (`fecha_llenado_*`,
  `fecha_evento_*`, `fecha_modificacion_*`), `q`, `procedencia`, `con_foto`,
  `sin_foto`, `pendiente_*`, `solo_huerfanas`, `id_usuario`, estado de
  localidad (formularios), estado/`id_estado`/UGG/alcalde/importación (EDAN),
  los 9 `grup_*` y las 14 `imp_*` (cada uno acepta `true` = la tiene,
  `false` = NO la tiene) y `tiene_agricultura`/`tiene_pecuario`.
- **Colores vienen del backend**: pintar `items[].color` tal cual.
- **Multi-tipo**: `tipos[]` + `tipo` sugerido, `items[]`, `categorias[]`,
  `series[]` y `tabla` (el agregado con `porcentaje` cuando hay una métrica);
  con `incluir_detalle=true` cada gráfica agrega `tabla_registros` (filas
  crudas paginadas con `detalle_limit`/`detalle_skip`).
- Presentación: `nivel` (nacional/departamento/provincia/municipio; omite
  gráficas más finas y desagregaciones degeneradas), `top`, `granularidad`
  (dia/semana/mes/anio), `rellenar_vacios`, `incluir` (CSV de ids).
- Geografía incoherente (`id_municipio` que no pertenece al
  `id_departamento`) → **400**.
- Detalle del contrato: PLAN §21.

### 11.2 Fechas desde/hasta en los GET existentes (sin romper nada)

| Endpoint | Añadido |
|---|---|
| `GET /formularios` | `fecha_llenado_*`, `fecha_evento_*`, `fecha_modificacion_*` |
| `GET /formularios/estados` | `fecha_llenado_*`, `fecha_evento_*`, `estado` (por nombre, ILIKE) |
| `GET /` (EDAN) | `fecha_llenado_*`, `fecha_modificacion_*`, `id_usuario_alcalde`, `id_importacion` |
| `GET /consolidar/pendientes` | `fecha_llenado_*`, `fecha_evento_*`, `fecha_modificacion_*` |

Nada se renombró ni se eliminó. Dos matices:

1. **`GET /formularios/estados`**: los filtros geográficos ahora se
   **combinan con AND** (antes 2+ → 400). `fecha_modificacion_desde` sigue
   siendo **sólo el watermark** del flag `tiene_cambios` (NO filtra).
2. Las fechas nuevas **sí filtran** en los otros tres endpoints.

### 11.3 Pruebas

- `/tmp/opencode/test_resumen.sh`: **54 PASS** (401/400, contadores, gráficas,
  multi-tipo, colores, donut 100 %, filtros `grup_*`/`imp_*`, `incluir`,
  `tabla_registros`, `nivel`, rol 6 sin scope).
- 10 suites de regresión: **471 PASS / 0 FAIL** (total **525 PASS**).
  `test_nuevas.sh` se actualizó: "2 filtros geo" ahora espera **200 con AND**.

---

## 12. Alcance municipio 6/7 + `GET /fotografias` (v2.61) (2026-10-20)

### 12.1 Un rol 6/7 ahora LEE todo su municipio

Antes solo veía sus propios formularios; ahora el **mapa/listado muestra TODO
su municipio** (como el rol 6 UGR y el rol 8 alcalde):

- `GET /edan/formularios`, `/formularios/estados`, `/formularios/{ref}`,
  `/completo` (lectura) y `/localidades/filtrar`: para 6/7 se fuerza el
  `id_municipio` del token; el del query **se ignora** (no puede ver fuera).
- `GET un formulario de otro usuario de SU municipio` → **200** (antes 403).
- Geografía ajena (otro municipio) → sigue **403**; fuera del departamento
  para 5/9 igual.
- **No aplica a las fotos**: `/fotografias*` es evidencia y se abre a cualquier
  token sin recorte (§12.3).

**No cambia lo que no se pidió**:

- **Escribir (POST/PUT/DELETE) sigue siendo SOLO lo propio** para 6/7
  (`id_usuario`). Un 6/7 puede VER el municipio pero no EDITAR ajeno → 403.
- **`sync pull` de 6/7 sigue trayendo solo lo propio** (el feed por
  dispositivo no descarga formularios de otros).

### 12.2 `fecha_evento_desde/hasta` en `GET /localidades/filtrar`

Ya existían en `/formularios`; ahora también en `/localidades/filtrar` (AND,
sobre `edan_localidades.fecha_evento`).

### 12.3 `GET /edan/fotografias` paginado + `/descargar` (anti N+1, **solo token**)

Las fotos son **evidencia informativa, no privada**: los 3 endpoints de fotos
**solo exigen token** (cualquier usuario autenticado, desde donde sea) y **NO**
tienen alcance geográfico ni por dueño → cualquiera lista/descarga **todas**.

- `GET /fotografias`: listado paginado (`limit`/`skip`/`todos`, `total` real)
  de fotos activas, **nacional para cualquier token**. Filtros AND (opcionales,
  no son restricción de alcance): `id_edan_localidad` (id o uuid), `id_municipio`
  (JOIN), **`id_usuario`** (dueño, id numérico; propio o ajeno), `tipo_entidad`,
  `fecha_creacion_*`, `fecha_modificacion_*`. Cada item trae metadata +
  `url_descarga`. `JOIN`→`LEFT JOIN` (no se pierden fotos con localidad suelta).
- `GET /fotografias/{uuid}`: metadata de una foto + `url_descarga` (sin scope;
  404 si no existe o está borrada).
- `GET /fotografias/{uuid}/descargar`: sirve el **binario** (la imagen, vía
  `FileResponse`, anti path-traversal). Cualquier token descarga cualquier foto
  → ya **no** hay 403 por municipio. Sin token → 401; inexistente/borrada → 404.
- **Flujo de galería**: una sola `GET /fotografias` para saber qué fotos existen
  (adiós al N+1 de bajar cada archivo) + descargar la imagen bajo demanda con la
  `url_descarga` devuelta (una llamada por foto mostrada). No hay descarga
  múltiple.

### 12.4 `total` en el envelope (confirmado)

`GET /formularios`, `GET /localidades/filtrar` y `GET /fotografias` devuelven
`total` = COUNT real (paginación de tablas).

### 12.5 Pruebas

- `test_municipio.sh`: **37 PASS** (scope 6/7 municipio en formularios, muni
  ajeno ignorado, `fecha_evento_*`, `total` en envelope, `/fotografias`
  **nacional para rol 7**, `id_usuario` propio/ajeno/inexistente,
  cross-municipio `descargar`=**200**, 401/404, `todos`, **fecha final = día
  completo** en `/formularios`/`/fotografias`/`GET /`).
- Suite completa **567 PASS / 0 FAIL** (12 suites; lectura-municipio en
  `test_final`/`test_completo`; fotos abiertas y fecha inclusiva en
  `test_municipio`).
- `/api/v2/edan` pasa a **162** operaciones (2 GET nuevas).

### 12.6 Fecha final = día completo (v2.61.1)

**Bug corregido**: en los GET con rango de fecha, la **fecha final** (`*_hasta`)
comparada con `<=` contra columnas **`timestamp`** (`fecha_modificacion`,
`fecha_creacion`) **excluía el día indicado** (un registro de las 14:30 del 15
no salía con `hasta=15`, solo con `hasta=16`).

Ahora **toda fecha final incluye ese día completo**: se usa
`col < CAST(:x AS date) + interval '1 day'` (sargable, no rompe los índices).
En columnas `date` (`fecha_llenado`, `fecha_evento`) ya eran inclusivas y
**no cambian de resultado**. La fecha inicial (`*_desde`) sigue `>=` (arranca a
las 00:00 del día). Cubre `/formularios`, `/formularios/estados`,
`/consolidar/pendientes`, `GET /`, `mis-*`, `/localidades/filtrar`,
`/fotografias` y el **dashboard/resumen**.

⚠️ Contrato: si una pantalla sumaba 1 día para compensar el corte viejo, debe
dejar de hacerlo.

Detalle: `PLAN_APIS_V2_EDAN.md` §22 (fecha final en §22.7).
