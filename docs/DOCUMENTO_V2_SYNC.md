# Localidad completa EDAN v2 — sync todo en uno (SIEMPRE compacto)

> **Documento GLOBAL.** Este es el flujo recomendado para la app/web actual.
> Reemplaza la sincronización sección por sección (ver `SQLITE_OFFLINE_APP.md`)
> por **UN solo JSON de la localidad completa** que viaja en cada dirección: el
> servidor lo descarga (`GET /documento`) y la app lo sube (`POST` o `PUT /documento`).
> Es **simétrico**: lo que el GET devuelve, el PUT lo acepta.
>
> **SIEMPRE COMPACTO:** no existe modo completo/extendido. La **salida** (`GET`)
> muestra **solo las secciones con `imp_*=true` o con datos** (las `false`/vacías
> se omiten); la **entrada** (`POST`/`PUT`) **recibe** las secciones `true` y las
> que no se envían (false) no se recrean ni se tocan.

## 1. Endpoints (grupo Swagger *EDAN_LOCALIDADES > edan_local_completo*)

| Método | Ruta | Descripción |
|---|---|---|
| `GET`  | `/api/v2/edan/localidades/{id_localidad}/documento` | Descarga la localidad completa |
| `POST` | `/api/v2/edan/localidades/documento` | Crea una localidad nueva desde el documento |
| `PUT`  | `/api/v2/edan/localidades/{id_localidad}/documento` | Actualiza una localidad existente |
| `DELETE` | `/api/v2/edan/localidades/{id_localidad}/documento` | Elimina físicamente la localidad completa (solo huérfanas) |

- `id_localidad` acepta el `id_local` (UUID offline) **o** el `id_edan_localidad` (int).
- `POST` usa `id_local` como clave de dedupe: si ya existe, **actualiza**; si no, **crea**.
- `PUT` **nunca crea**: fuerza la localidad indicada en el path (evita duplicados).
- `DELETE` **solo borra si la localidad es huérfana** (`id_edan` NULL). Si está
  consolidada en un EDAN responde **403** (debe eliminarse con
  `DELETE /edan/{id}/localidades/{id_localidad}`).

## 2. Contrato simétrico → FORMA FIJA por sección

Cada clave va en **una sola forma** (serializar y deserializar idéntico). La app
DEBE emitir y esperar estas formas:

| Forma | Secciones (11 array) |
|---|---|
| **ARRAY** | `impacto_poblacion`, `establecimientos_salud`, `danos_viales`, `danos_infra_publica`, `servicios_basicos`, `unidades_educativas`, `danos_vivienda`, `danos_agricultura`, `danos_pecuarios`, `infra_productiva`, `proteccion` |

| Forma | Secciones (3 objeto) |
|---|---|
| **OBJETO** | `necesidad_primera_respuesta`, `necesidad_salud`, `necesidad_humanitaria` |

- La app puede **enviar** una 1:N como objeto único (el servidor la envuelve en
  array), pero **siempre recibe** array (aunque haya un solo elemento).
- Una 1:1 recibida como array de **1** se acepta (se toma el objeto); array de
  **>1** responde **HTTP 400** con el motivo.

## 3. Los flags `imp_*` son el corazón

El documento trae los flags `imp_*` (9 legacy + 14 por sección). Regla:

- **SIEMPRE COMPACTO:** el JSON **solo viaja con las secciones `true` o con datos**;
  las `false`/vacías se omiten de la salida y no se envían en la entrada.
- **Sección presente** en el JSON → se procesa (con o sin flag).
- **flag true + sin datos** → normal (p. ej. se marcó "hay daños en viales" pero
  aún no se ingresan filas). No rompe nada.
- **flag false + sección ausente** → el servidor **no borra** lo existente
  (sync no destructivo).
- Tras persistir, el servidor **recalcula** los 14 flags por datos reales
  (`_marcar_impacto`), de modo que los flags siempre reflejan la verdad.

## 4. LWW por `fecha_modificacion`

- El documento lleva `fecha_modificacion` **top-level** (cabecera) y cada sección
  lleva **su propia** `fecha_modificacion` por fila.
- Al subir, el servidor aplica `GREATEST(fecha_modificacion, env)`:
  - datos **siempre** se actualizan (la fila cambia);
  - la **fecha no retrocede**: un envío desactualizado no "adelanta" al que ya
    estaba al día.
- Si una fila no trae `fecha_modificacion`, se usa la top-level como fallback; si
  tampoco hay, el servidor usa `NOW()`.
- **Formato obligatorio:** string ISO 8601 con zona horaria,
  ej. `2026-09-02T09:15:00Z` o `2026-09-02T09:15:00-04:00` (preferir UTC `Z`).

## 5. Ejemplos de uso por endpoint

### 5.1 `GET /localidades/{id_localidad}/documento` — descargar la localidad completa

Descarga cabecera + flags + **solo las secciones con datos** (las vacías se omiten),
cada una con su `fecha_modificacion` (LWW por fila) y la top-level.

```bash
# con id_edan_localidad (int)
curl -X GET -H "Authorization: Bearer <TOKEN>" \
  http://host:8000/api/v2/edan/localidades/340/documento

# con id_local (UUID offline)
curl -X GET -H "Authorization: Bearer <TOKEN>" \
  http://host:8000/api/v2/edan/localidades/SINAGER-340-ABC123/documento
```

Respuesta (resumida):

```json
{
  "ok": true,
  "data": {
    "id_local": "SINAGER-340-ABC123",
    "id_edan_localidad": 340,
    "localidad": "Salinas",
    "id_departamento": 2,
    "id_municipio": 20101,
    "id_usuario": 30,
    "imp_poblacion": true,
    "imp_impacto_poblacion": true,
    "imp_necesidad_salud": true,
    "fecha_modificacion": "2026-09-02T14:15:57-04:00",
    "impacto_poblacion": [
      {
        "id_seccion": "ip_doc_1",
        "id_grupo_etario": 1,
        "fallecidos": 0,
        "heridos": 5,
        "desaparecidos": 0,
        "fecha_modificacion": "2026-09-02T14:15:57-04:00"
      }
    ],
    "necesidad_salud": {
      "id_seccion": "ns_doc_1",
      "numero_personas": 21,
      "observaciones": "atencion basica",
      "fecha_modificacion": "2026-09-02T14:15:57-04:00"
    }
  }
}
```

### 5.2 `POST /localidades/documento` — crear una localidad nueva

Envía el documento completo. Si el `id_local` ya existe, **actualiza** en vez de
duplicar. Devuelve la localidad ya persistida con su `id_edan_localidad`.

```bash
curl -X POST -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  http://host:8000/api/v2/edan/localidades/documento \
  -d '{
    "id_local": "SINAGER-999-NUEVA",
    "localidad": "Comunidad Nueva",
    "id_departamento": 2, "id_municipio": 20101, "id_usuario": 30,
    "imp_poblacion": true,
    "imp_impacto_poblacion": true,
    "fecha_modificacion": "2026-09-02T10:00:00Z",
    "impacto_poblacion": [
      { "id_seccion": "ip_1", "id_grupo_etario": 1, "fallecidos": 1,
        "heridos": 3, "desaparecidos": 0,
        "fecha_modificacion": "2026-09-02T10:00:00Z" }
    ],
    "necesidad_salud": { "id_seccion": "ns_1", "numero_personas": 12,
        "fecha_modificacion": "2026-09-02T10:00:00Z" }
  }'
```

Respuesta:

```json
{
  "ok": true,
  "data": {
    "id_local": "SINAGER-999-NUEVA",
    "id_edan_localidad": 999,
    "localidad": "Comunidad Nueva",
    "imp_impacto_poblacion": true,
    "impacto_poblacion": [ { "id_seccion": "ip_1", "fallecidos": 1 } ],
    "necesidad_salud": { "id_seccion": "ns_1", "numero_personas": 12 }
  }
}
```

### 5.3 `PUT /localidades/{id_localidad}/documento` — actualizar una localidad existente

Actualiza la cabecera y **solo las secciones presentes** en el JSON. Las secciones
ausentes NO se borran. El servidor recalcula flags y aplica LWW (`GREATEST`).

```bash
# actualización parcial (solo impacto_poblacion)
curl -X PUT -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  http://host:8000/api/v2/edan/localidades/340/documento \
  -d '{
    "imp_impacto_poblacion": true,
    "fecha_modificacion": "2026-09-02T11:30:00Z",
    "impacto_poblacion": [
      { "id_seccion": "ip_doc_1", "id_grupo_etario": 1, "fallecidos": 0,
        "heridos": 8, "desaparecidos": 1,
        "fecha_modificacion": "2026-09-02T11:30:00Z" }
    ]
  }'
```

Comportamiento LWW observable:

- Enviar la fila con `fecha_modificacion: 2026-09-02T11:30:00Z` sobre una fila
  guardada a las `14:15` → **datos se actualizan**, pero la `fecha_modificacion`
  **se mantiene en 14:15** (no retrocede).
- Enviar con fecha **más nueva** → fecha y datos **se adoptan**.

### 5.4 `DELETE /localidades/{id_localidad}/documento` — eliminar la localidad completa

Elimina **físicamente** la localidad (cabecera + flags + **todas** sus secciones).
Acepta `id_edan_localidad` (int) o `id_local` (UUID).

```bash
curl -X DELETE -H "Authorization: Bearer <TOKEN>" \
  http://host:8000/api/v2/edan/localidades/340/documento

# también por id_local (UUID)
curl -X DELETE -H "Authorization: Bearer <TOKEN>" \
  http://host:8000/api/v2/edan/localidades/SINAGER-340-ABC123/documento
```

Respuesta (éxito):

```json
{ "message": "Localidad eliminada correctamente", "id": null }
```

**Regla de negocio (importante):** solo se borra si la localidad es **huérfana**
(`id_edan` NULL). Si está **consolidada** en un EDAN, la API responde **403**:

```json
{
  "detail": "La localidad está consolidada en un EDAN (id_edan) y no se puede eliminar desde el documento. Elimínela con `DELETE /edan/{id}/localidades/{id_localidad}`."
}
```

## 6. Errores (HTTP 400) ejemplo

Relaciones 1:1 enviadas como **array de >1** se rechazan con mensaje explicativo:

```bash
curl -X PUT -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  http://host:8000/api/v2/edan/localidades/340/documento \
  -d '{
    "necesidad_salud": [
      { "id_seccion": "ns_1", "numero_personas": 1 },
      { "id_seccion": "ns_2", "numero_personas": 2 }
    ]
  }'
```

```json
{
  "ok": false,
  "detail": "La seccion 'necesidad_salud' es de relacion 1:1 (un solo objeto); se recibieron 2 elementos. Envie un objeto unico o un array de un solo elemento."
}
```

## 7. Fotografías del carrete (NO van inline)

El documento es **JSON puro**; los binarios NO viajan en él.

1. La app sube las fotos primero: `POST /api/v2/edan/localidades/foto/subir`
   (multipart, una o varias) pasando `id_seccion`, y guarda el `path` devuelto.
2. En el documento, cada sección lleva `"fotografia": "/uploads/reports/..."`
   (el path del paso 1).
3. Al bajar el documento, la app reutiliza esos paths para mostrar imágenes.

> **Secciones que soportan `fotografia`** (+ `coordenada_lat`/`coordenada_lon`):
> `danos_viales`, `danos_infra_publica`, `danos_vivienda`, `danos_agricultura`,
> `danos_pecuario`, `infra_productiva`, `establecimientos_salud`,
> `servicios_basicos`, `unidades_educativas`.
>
> `impacto_poblacion` **no** tiene columna `fotografia`: la foto del carrete en
> ese rango etario se asocia vía el path en la tabla correspondiente o se omite.
> Las secciones 1:1 (`necesidad_*`) tampoco llevan `fotografia`.

```bash
# 1) subir la foto del carrete
curl -X POST -H "Authorization: Bearer <TOKEN>" \
  -F "file=@/ruta/foto.jpg" -F "id_seccion=ip_doc_1" \
  -F "id_local=SINAGER-340-ABC123" -F "id_edan_localidad=340" \
  http://host:8000/api/v2/edan/localidades/foto/subir
# → devuelve { "ok": true, "path": "/uploads/reports/340/foto.jpg" }

# 2) referenciar ese path dentro de la sección del documento
#    (curl análogo a 5.2/5.3 pero con "fotografia":"/uploads/reports/340/foto.jpg")
```

```typescript
// Subir carrete pendiente ANTES de subir el documento
for (const f of await db.foto_pendiente.where(subida = 0)) {
  const r = await post('/edan/localidades/foto/subir', {
    file: f.ruta_local_archivo, id_seccion: f.id_seccion,
    id_local: f.id_local, id_edan_localidad: f.id_edan_localidad,
    coordenada_lat, coordenada_lon,
  });
  await db.foto_pendiente.update(f.id_foto, { path_servidor: r.path, subida: 1 });
}
```

## 8. Filtros en el listado `mis-reportes`

El endpoint de listado acepta filtros opcionales por usuario, departamento y
municipio (según el rol y alcance del token):

```
GET /api/v2/edan/mis-reportes?modo=comprimido&id_departamento=2&id_municipio=20101
GET /api/v2/edan/mis-reportes?modo=comprimido&id_usuario=30
```

- `id_usuario`: filtra las localidades cargadas por ese usuario (rol con acceso amplio).
- `id_departamento` / `id_municipio`: filtran por ubicación geográfica.
- Roles con alcance propio (p. ej. rol 7) fuerzan su propio `id_usuario` independiente del filtro.

## 9. Flujo offline recomendado (push + pull con el documento)

```typescript
async function pushDocumento(loc) {
  // 1) carrete primero (secciones referencian el path)
  await pushCarrete(loc.id_local);
  // 2) armar el documento solo con lo pendiente/editado
  const doc = { ...loc, ...(await seccionDoc(loc.id_local)) };
  let r;
  if (loc.id_edan_localidad) {
    r = await put(`/edan/localidades/${loc.id_edan_localidad}/documento`, doc);
  } else {
    r = await post('/edan/localidades/documento', doc);
    await db.localidad.update(loc.id_local,
        { id_edan_localidad: r.data.id_edan_localidad, pendiente: 0 });
  }
  await marcarEnviadas(loc.id_local);   // editada=0, insertada_en_server=1
}

async function pullDocumento(idLocal) {
  const r = await get(`/edan/localidades/${idLocal}/documento`);
  await db.localidad.put(r.data);                       // cabecera + flags
  for (const [key, filas] of seccionesDe(r.data)) {
    await upsertSeccion(key, filas);                    // forma fija: array/objeto
  }
}
```

## 10. Recomendación de esquema SQLite para la app

Una sola tabla `seccion` genérica + una `localidad` con flags y fechas. La app
guarda las 14 secciones **dentro de** la localidad como JSON de la forma fija.

```sql
CREATE TABLE localidad (
  id_local              TEXT PRIMARY KEY,        -- UUID offline
  id_edan_localidad     INTEGER,                -- se llena tras el primer push
  localidad             TEXT,
  id_departamento INTEGER, id_provincia INTEGER, id_municipio INTEGER,
  fecha_llenado TEXT, fecha_evento TEXT, hora_evento TEXT,
  total_poblacion_afectada INTEGER DEFAULT 0,
  total_familias_afectadas INTEGER DEFAULT 0,
  total_familias_damnificadas INTEGER DEFAULT 0,
  -- 23 flags imp_* (9 legacy + 14 sección)
  imp_poblacion INTEGER DEFAULT 0, imp_salud INTEGER DEFAULT 0,
  imp_infraestructura INTEGER DEFAULT 0, imp_servicios INTEGER DEFAULT 0,
  imp_educacion INTEGER DEFAULT 0, imp_vivienda INTEGER DEFAULT 0,
  imp_agropecuario INTEGER DEFAULT 0, imp_proteccion INTEGER DEFAULT 0,
  imp_necesidades INTEGER DEFAULT 0,
  imp_impacto_poblacion INTEGER DEFAULT 0, imp_salud_establecimientos INTEGER DEFAULT 0,
  imp_danos_viales INTEGER DEFAULT 0, imp_danos_infra_publica INTEGER DEFAULT 0,
  imp_servicios_basicos INTEGER DEFAULT 0, imp_unidades_educativas INTEGER DEFAULT 0,
  imp_danos_vivienda INTEGER DEFAULT 0, imp_danos_agricultura INTEGER DEFAULT 0,
  imp_danos_pecuarios INTEGER DEFAULT 0, imp_infra_productiva INTEGER DEFAULT 0,
  imp_primera_respuesta INTEGER DEFAULT 0, imp_necesidad_salud INTEGER DEFAULT 0,
  imp_necesidad_humanitaria INTEGER DEFAULT 0,
  -- fechas
  fecha_modificacion TEXT,                  -- top-level (cabecera)
  pendiente INTEGER DEFAULT 0,              -- cabecera por enviar
  insertada_en_server INTEGER DEFAULT 0
);

-- Secciones de la forma fija como JSON (11 array / 3 objeto).
CREATE TABLE seccion (
  id_seccion   TEXT PRIMARY KEY,            -- id_seccion de la fila (solo 1:N)
  id_local     TEXT REFERENCES localidad(id_local),
  id_edan_localidad INTEGER,
  seccion      TEXT,                        -- "danos_viales", "necesidad_salud", ...
  json         TEXT,                        -- un objeto (1:1) o un elemento (1:N)
  fecha_modificacion TEXT,                  -- ISO 8601 (LWW)
  editada INTEGER DEFAULT 0,                -- 1 si cambió localmente (falta reenviar)
  insertada_en_server INTEGER DEFAULT 0,
  marcado_borrar INTEGER DEFAULT 0
);

CREATE TABLE foto_pendiente (
  id_foto TEXT PRIMARY KEY,
  id_local TEXT, id_edan_localidad INTEGER, id_seccion TEXT,
  ruta_local_archivo TEXT, path_servidor TEXT,
  coordenada_lat REAL, coordenada_lon REAL,
  subida INTEGER DEFAULT 0, observaciones TEXT
);
```

> La app arma el `json` del documento agrupando por `seccion`: las 11 1:N emiten
> `array`, las 3 1:1 emiten `objeto`, y el flag de cada una se recalcula al
> construir el documento. Así el payload sube **solo lo que tiene datos** y el
> servidor lo guarda tal cual (LWW por `fecha_modificacion`).