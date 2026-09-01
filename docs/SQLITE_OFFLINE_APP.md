# Especificación — SQLite offline-first para la app EDAN

Documento de **sugerencia técnica** del backend (Modelo A, por secciones, `/api/v2`)
para que la app móvil implemente una caché local en **SQLite** compatible 1:1 con
el servidor. Define la estructura de tablas y el flujo de sincronización
(offline → push → pull).

> No incluye código de la app: es la especificación para que el equipo móvil
> replique el modelo.

---

## 1. Principios de diseño

1. **SQLite duplica las tablas del backend** (mismas columnas) más columnas de
   sincronización local. Así el push es directo: se lee la fila local y se manda
   al endpoint correcto.
2. **La app es la fuente de verdad de los identificadores.** Genera `id_local`
   (UUID, identidad estable de la localidad) y `id_seccion` (UUID, identidad
   estable de cada fila de sección). El servidor **nunca** genera `id_seccion`;
   solo lo usa como clave de UPSERT. El `id_local` lo mapea a `id_edan_localidad`.
3. **`id_seccion` es la clave de deduplicación global** (el backend tiene un
   índice único por tabla, ej. `idx_seccion_danos_viales UNIQUE (id_seccion)`).
   Por eso debe ser **único entre todos los dispositivos** → usar UUID, no un
   contador por localidad.
4. **Modelo A (por secciones):** se sincroniza por sección, no el JSON completo
   de la localidad. Cabecera primero, luego secciones, luego borrados.

### Reglas de oro de `id_seccion` (para la app)
- **Generarlo una sola vez** por fila y **reusarlo en cada edición**. Si al
  editar se manda un `id_seccion` nuevo, el servidor crea una fila adicional
  (UPSERT por el nuevo id) → duplicado.
- **Secciones 1:1** (`primera-respuesta`, `necesidad-salud`,
  `necesidad-humanitaria`): hay **un solo registro por localidad**. Para
  actualizar hay que **reenviar el MISMO `id_seccion`**; si se manda otro, el
  servidor responde **400 "violación de unicidad"**.

### Sincronización de cabecera
- `id_local` (UUID) es la identidad estable del documento. El endpoint
  `POST /localidades/cabecera` crea la localidad y puede responder
  `es_huerfana: true` (aún sin consolidar). Tras el primer push la app guarda el
  `id_edan_localidad` devuelto.

---

## 2. Estructura SQLite propuesta (DDL)

### 2.1 Tabla `localidad` (cabecera)
```sql
CREATE TABLE localidad (
  id_local          TEXT PRIMARY KEY,   -- UUID generado en el dispositivo (se manda a /cabecera)
  id_edan_localidad INTEGER,            -- se completa tras el 1er push
  es_huerfana       INTEGER DEFAULT 1,  -- 1 mientras id_edan_localidad IS NULL
  id_tipo_localidad   INTEGER,
  id_edan_localidad_estado INTEGER,
  id_tipo_evento      INTEGER,
  id_departamento     INTEGER,
  id_provincia        INTEGER,
  id_municipio        INTEGER,
  localidad           TEXT,
  fecha_llenado       TEXT,
  fecha_evento        TEXT,
  hora_evento         TEXT,
  total_poblacion_afectada  INTEGER DEFAULT 0,
  total_familias_afectadas  INTEGER DEFAULT 0,
  total_familias_damnificadas INTEGER DEFAULT 0,

  -- sincronización local (NO se envían al servidor)
  creada_offset INTEGER DEFAULT 0,      -- timestamp local para ordenar
  pendiente     INTEGER DEFAULT 1       -- 1 = falta push de cabecera / 0 = sincronizada
);
```

### 2.2 Patrón de tablas de sección
Cada sección repite las columnas del backend más:
- `id_seccion` como **PK local** (clave de dedup).
- `id_local` (FK a la localidad dueña).
- Banderas: `insertada_en_server` (1 = ya existe en el server, aplicar UPDATE;
  0 = no existe, aplicar INSERT) y `marcado_borrar` (1 = imprimir DELETE).

**Sección 1:N con foto** — ejemplo `seccion_danos_viales`:
```sql
CREATE TABLE seccion_danos_viales (
  id_seccion   TEXT PRIMARY KEY,        -- UUID, clave de dedup del server
  id_local     TEXT REFERENCES localidad(id_local),
  id_edan_localidad INTEGER,            -- caché para el push
  via           INTEGER,                -- bool
  puente        INTEGER,                -- bool
  tramo         TEXT,
  dano_parcial  INTEGER,                -- bool
  dano_total    INTEGER,                -- bool
  km_danio      REAL,
  necesidades_inmediatas TEXT,
  observaciones TEXT,
  fotografia    TEXT,                   -- path servidor: /uploads/reports/...
  coordenada_lat REAL,
  coordenada_lon REAL,

  insertada_en_server INTEGER DEFAULT 0,
  marcado_borrar      INTEGER DEFAULT 0
);
```

**Sección 1:N sin foto** — ejemplo `seccion_impacto_poblacion`:
```sql
CREATE TABLE seccion_impacto_poblacion (
  id_seccion   TEXT PRIMARY KEY,
  id_local     TEXT REFERENCES localidad(id_local),
  id_edan_localidad INTEGER,
  id_grupo_etario INTEGER,
  fallecidos    INTEGER,
  heridos       INTEGER,
  desaparecidos INTEGER,
  observaciones TEXT,
  insertada_en_server INTEGER DEFAULT 0,
  marcado_borrar      INTEGER DEFAULT 0
);
```

**Sección 1:1** — ejemplo `seccion_primera_respuesta` (un solo registro por
localidad):
```sql
CREATE TABLE seccion_primera_respuesta (
  id_seccion   TEXT PRIMARY KEY,
  id_local     TEXT,
  id_edan_localidad INTEGER,
  busqueda     INTEGER,
  salvamento   INTEGER,
  evacuacion   INTEGER,
  observaciones TEXT,
  insertada_en_server INTEGER DEFAULT 0,
  marcado_borrar      INTEGER DEFAULT 0
);
```

### 2.3 Tabla `foto_pendiente` (carrete)
Desacopla la subida de binarios del guardado de la sección. La app sube las
fotos ni bien hay red y guarda el `path` devuelto; después reenvía ese path en
el campo `fotografia` de la sección.
```sql
CREATE TABLE foto_pendiente (
  id_foto           TEXT PRIMARY KEY,   -- UUID local
  id_local          TEXT,               -- localidad dueña (puede ser NULL pre-cabecera)
  id_edan_localidad INTEGER,
  id_seccion        TEXT,               -- vinculo con la sección (vacío hasta saber)
  ruta_local_archivo TEXT,              -- path del binario en el dispositivo
  coordenada_lat    REAL,
  coordenada_lon    REAL,
  subida            INTEGER DEFAULT 0,  -- 1 = ya subida, path_servidor disponible
  path_servidor     TEXT,               -- path devuelto por /foto/subir
  observaciones     TEXT
);
```

### 2.4 Cómo se conectan las secciones con la cabecera offline (puente hacia el servidor)

**El problema.** En línea, cada sección cuelga de la cabecera por
`id_edan_localidad` (int que asigna el servidor):
```
edan_localidades (id_edan_localidad=337)
   ├── edan_localidades_danos_viales          (id_edan_localidad=337)
   └── edan_localidades_unidades_educativas   (id_edan_localidad=337)
```
Pero **offline** ese id aún **no existe** (el servidor no ha respondido). No se
puede usar como llave de relación local.

**Cadena de identidad local por UUID.** El SQLite usa dos claves que **la propia
app genera y no dependen del servidor**:
- `id_local` (UUID) → identidad estable de la **cabecera**.
- `id_seccion` (UUID) → identidad estable de **cada fila de sección**.

Cada fila de sección local guarda `id_local` como **FK puente** a su cabecera, y
un `id_edan_localidad` que empieza en **NULL**:
```
localidad (id_local='aaa...')
   ├── seccion_danos_viales       (id_seccion='x1', id_local='aaa...', id_edan_localidad=NULL)
   └── seccion_unidades_educativas(id_seccion='x2', id_local='aaa...', id_edan_localidad=NULL)
```
La relación local es `seccion.id_local → localidad.id_local`. Así, sin red, se
sabe qué secciones pertenecen a qué formulario.

**El puente (acople único).** Al subir la cabecera:
```
POST /localidades/cabecera  { id_local:'aaa...', ... }
   → el servidor crea la localidad y responde  id_edan_localidad: 337
```
La app entonces:
1. Guarda `id_edan_localidad=337` en la fila `localidad`.
2. **Propaga el mismo valor a todas sus secciones** por `id_local`:
   ```sql
   UPDATE seccion_danos_viales        SET id_edan_localidad = 337 WHERE id_local = 'aaa...';
   UPDATE seccion_unidades_educativas SET id_edan_localidad = 337 WHERE id_local = 'aaa...';
   -- ... repetir para las 14 tablas de sección
   ```
3. Marca `pendiente = 0` en la cabecera.

A partir de ahí, **local y servidor quedan idénticos**: cada sección lleva el
mismo `id_edan_localidad`, y `id_seccion` es la misma clave en ambos lados.

**Por qué el servidor acepta ambas referencias.** El backend (`_resolve_localidad_id`)
permite subir secciones con `id_edan_localidad` (int) **o** con `id_local` (UUID),
resolviendo él mismo la correspondencia. Por eso el **orden del push importa**:
cabecera primero (para obtener y propagar el id), secciones después.

**Diagrama del puente.**
```
OFFLINE (SQLite local)
 id_local='aaa...' (UUID, genera la app)
   ├─ seccion x1 (id_seccion='x1', id_local='aaa...', id_edan_localidad=NULL)
   ├─ seccion x2 (id_seccion='x2', id_local='aaa...', id_edan_localidad=NULL)
   └─ ...14
      │
      │  PUSH (ordenado)
      ▼
 1. POST /cabecera {id_local:'aaa...'}  ──►  servidor responde id_edan_localidad=337
      │
      │  "nodo de puente": UPDATE todas las secciones
      │  SET id_edan_localidad=337 WHERE id_local='aaa...'
      ▼
 2. POST /foto/subir  (carrete)         ──►  path_servidor
 3. POST /337/{seccion} ×14             ──►  cada una sube con id_edan_localidad=337
      │
      ▼
ONLINE (servidor)
 edan_localidades (id_edan_localidad=337)
   ├── danos_viales       (id_edan_localidad=337)
   └── unidades_educativas(id_edan_localidad=337)
```

**Reglas del diseño.**
- La unión local es por `id_local` (UUID); `id_edan_localidad` es el relleno final.
- El puente se hace **una sola vez**, cuando la cabecera responde el id, y se
  propaga a todas las secciones hijas.
- `id_seccion` **no cambia** entre offline y online: es la misma clave, por eso el
  UPSERT del servidor coincide (INSERT nuevo vs UPDATE del mismo).
- `id_local` es **estable para siempre** (se genera al crear y nunca se modifica);
  sirve de llave de reconciliación entre dispositivos.

---

## 3. Mapa de tablas de sección (backend real)

| Tabla backend (`edan.*`) | Endpoint carrete/sección | 1:N / 1:1 | Foto |
|---|---|---|---|
| `edan_localidades_impacto_poblacion` | impacto-poblacion | 1:N | no |
| `edan_localidades_salud_establecimientos` | salud-establecimientos | 1:N | sí |
| `edan_localidades_danos_viales` | danos-viales | 1:N | sí |
| `edan_localidades_danos_infra_publica` | danos-infra-publica | 1:N | sí |
| `edan_localidades_servicios_basicos` | servicios-basicos | 1:N | sí |
| `edan_localidades_unidades_educativas` | unidades-educativas | 1:N | sí |
| `edan_localidades_danos_vivienda` | danos-vivienda | 1:N | sí |
| `edan_localidades_danos_agricultura` | danos-agricultura | 1:N | sí |
| `edan_localidades_danos_pecuario` | danos-pecuarios | 1:N | sí |
| `edan_localidades_infra_productiva` | infra-productiva | 1:N | sí |
| `edan_localidades_proteccion` | proteccion | 1:N | no |
| `edan_localidades_primera_respuesta` | primera-respuesta | 1:1 | no |
| `edan_localidades_salud_necesidades` | necesidad-salud | 1:1 | no |
| `edan_localidades_necesidades_humanitarias` | necesidad-humanitaria | 1:1 | no |

Columnas con foto (a replicar tal cual en el DDL de cada sección con foto):
`fotografia`, `coordenada_lat`, `coordenada_lon`.

---

## 4. Flujo offline (sin red)

1. Crear localidad → `INSERT localidad` con `id_local=UUID`, `pendiente=1`.
2. Agregar/editar secciones → INSERT/UPDATE en su tabla manteniendo siempre el
   mismo `id_seccion`.
3. Tomar fotos → `INSERT foto_pendiente` (binario en disco, `subida=0`).
4. Nada toca la red. Toda la identidad se sustenta en `id_local` + `id_seccion`
   estables.

---

## 5. Flujo de push (online) — orden recomendado

El orden importa porque la cabecera resuelve el municipio para la ruta de las
fotos, y las secciones necesitan `id_edan_localidad`.

1. **Fase 1 — Cabecera**
   `POST /api/v2/edan/localidades/cabecera`
   → guardar `id_edan_localidad` de la respuesta; `pendiente=0`.

2. **Fase 2 — Carrete de fotos**
   `POST /api/v2/edan/localidades/foto/subir` (multipart)
   - `file` (una o varias, repetir campo) + `id_seccion` (paralelo) +
     `id_edan_localidad`/`id_local` + GPS opcional.
   - → guardar `path_servidor`, `subida=1`.

3. **Fase 3 — Secciones**
   `POST /api/v2/edan/localidades/{id}/{seccion}`
   - Body: **objeto único o array directo** de la misma sección. (NO envolver en
     `{"items": [...]}`: eso genera la fila con campos vacíos.)
   - Pasar `fotografia=path_servidor` y GPS en el item.
   - `insertada_en_server=0` → id_seccion nuevo (server hace INSERT).
   - `insertada_en_server=1` → reenviar el **mismo id_seccion** (server hace
     UPDATE, no duplica). Marcar `insertada_en_server=1` tras el 2xx.

4. **Fase 4 — Borrados**
   `DELETE /api/v2/edan/localidades/{id}/{seccion}/seccion/{id_seccion}`
   solo si `marcado_borrar=1`.

---

## 6. Flujo de pull / reconciliación

`GET /api/v2/edan/localidades/{id}` devuelve todas las secciones anidadas.
La app compara por `id_seccion` (y `id_local`) y aplica los cambios venidos del
servidor (ej. consolidación de UGR u otras PC). Última escritura gana.

---

## 7. Pseudocódigo de la app (push ordenado)

```typescript
async function sync() {
  // Fase 1: cabeceras pendientes
  for (const loc of await db.localidad.where(pendiente=1)) {
    const r = await post('/edan/localidades/cabecera', loc);
    // PUENTE offline → online: guardar el id y PROPAGARLO a todas sus secciones
    await db.localidad.update(loc.id_local, { id_edan_localidad: r.id_edan_localidad, pendiente: 0 });
    for (const [tabla] of SECCIONES) {
      await db[tabla].where({ id_local: loc.id_local })
                      .update({ id_edan_localidad: r.id_edan_localidad });
    }
    loc.id_edan_localidad = r.id_edan_localidad;
  }

  // Fase 2: carrete
  const fotos = await db.foto_pendiente.where(subida=0);
  for (const item of fotos) {
    const r = await post('/edan/localidades/foto/subir', {
      file: item.ruta_local_archivo,          // una o varias
      id_seccion: item.id_seccion,
      id_edan_localidad: item.id_edan_localidad,
      coordenada_lat, coordenada_lon,
    });
    await db.foto_pendiente.update(item.id_foto, { path_servidor: r.path, subida: 1 });
  }

  // Fase 3: secciones
  for (const [tabla, nombreSeccion] of SECCIONES) {
    const filas = await db[tabla].where(marcado_borrar=0);
    for (const item of filas) {
      const payload = armarPayload(item);      // poner fotografia=path_servidor y GPS
      await post(`/edan/localidades/${item.id_edan_localidad}/${nombreSeccion}`,
                 payload.length===1 ? payload[0] : payload);
      await db[tabla].update(item.id_seccion, { insertada_en_server: 1 });
    }
  }

  // Fase 4: borrados
  for (const item of await db.todasSecciones.where(marcado_borrar=1)) {
    await del(`/edan/localidades/${item.id_edan_localidad}/${item.nombreSeccion}/seccion/${item.id_seccion}`);
    await db[item.tabla].delete(item.id_seccion);
  }
}
```

---

## 8. Notas transversales

- **Coherencia de ids en el carrete:** si la app envía `id_local` e
  `id_edan_localidad` y la cabecera ya existe, el servidor valida que apunten a
  la misma localidad (400 si no). Si la cabecera aún no existe (offline), la foto
  se guarda igual (carpeta `reports/general`) y se asocia al guardar la sección.
- **GPS de la foto es opcional** en el carrete (el GPS corresponde a la sección,
  no a la foto). En los endpoints `con-foto` antiguos el GPS sí es obligatorio.
- Todo este modelo asume el **Modelo A (por secciones)**; el Modelo B (`/sync`)
  fue eliminado del v2.
