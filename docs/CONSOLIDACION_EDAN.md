# Consolidación EDAN: cómo se vincula `edan_localidades` → `edan`

> **Nota (v1.3.2):** la V2 de sync por secciones (`/api/v2`, no destructiva) **no modifica el flujo de consolidación**: `consolidar`/`desconsolidar` siguen operando sobre la cabecera (`id_edan`, `id_edan_localidad_estado`). Ver [SINCRONIZACION.md](SINCRONIZACION.md#sincronización-incremental-por-secciones-v2--apiv2).

> **Audiencia:** developers de app móvil y web que consumen la API BaseData.
> **Objetivo:** entender cómo varias "EDAN localidades" (ítems) se agrupan en un
> solo "EDAN" (cabecera) mediante el proceso de consolidación, y cómo se
> calculan los totales.

---

## 1. Modelo de datos (resumen)

```
┌────────────────────────┐                  ┌───────────────────────┐
│      edan.edan         │                  │ edan.edan_localidades │
│   (CABECERA EDAN)      │                  │      (ÍTEMS)          │
├────────────────────────┤                  ├───────────────────────┤
│  id_edan (PK)          │◄──── 1:N ────────►│  id_edan_localidad PK │
│  codigo_edan           │                  │  id_edan (FK nullable)│
│  id_departamento       │                  │  localidad            │
│  id_provincia          │                  │  id_municipio         │
│  id_municipio          │                  │  id_tipo_evento       │
│  id_tipo_evento        │                  │  id_tipo_localidad    │
│  fecha_evento / hora   │                  │  id_edan_localidad_   │
│  total_poblacion_      │                  │     estado            │
│     afectada (SUM)     │                  │  total_poblacion_     │
│  total_familias_       │                  │     afectada          │
│     afectadas (SUM)    │                  │  total_familias_      │
│  total_familias_       │                  │     afectadas         │
│     damnificadas (SUM) │                  │  total_familias_      │
│  id_estado / estado    │                  │     damnificadas      │
│  id_usuario_ugr        │                  │  fecha_evento/hora    │
│  id_usuario_alcalde    │                  │  fecha_modificacion   │
│  fecha_creacion        │                  │  pendiente_*          │
│  fecha_modificacion    │                  │                       │
└────────────────────────┘                  │  + secciones 1:N:     │
                                            │   - impacto_poblacion │
                                            │   - establecimientos_ │
                                            │     salud             │
                                            │   - danos_viales      │
                                            │   - danos_vivienda    │
                                            │   - danos_agricultura │
                                            │   - danos_pecuario    │
                                            │   - servicios_basicos │
                                            │   - unidades_         │
                                            │     educativas        │
                                            │   - danos_infra_      │
                                            │     publica           │
                                            │   - infra_productiva  │
                                            │   - proteccion        │
                                            │  + secciones 1:1:     │
                                            │   - primera_respuesta │
                                            │   - salud_necesidades │
                                            │   - necesidades_      │
                                            │     humanitarias      │
                                            └───────────────────────┘
```

### Estados

**Estado de LOCALIDAD** (`edan.edan_localidades_estado.nombre`):

| id | nombre | orden | significado |
|----|--------|-------|-------------|
| 1 | `borrador` | 1 | Creada por Responsable Local, aún editable |
| 2 | `enviado_ugr` | 2 | Enviada al UGR municipio para revisión |
| 3 | `aprobado` | 3 | UGR la aprobó → lista para consolidar |
| 4 | `rechazado_ugr` | 4 | UGR la rechazó → vuelve a editable |
| 5 | `aprobado_ajuste_ugr` | 5 | Aprobada con ajustes pendientes |

**Estado de EDAN** (`edan.estado_edan.nombre`):

| id | nombre | orden | significado |
|----|--------|-------|-------------|
| 6 | `en_revision` | 0 | Antes de consolidarse (no usado por ahora) |
| 1 | `borrador` | 1 | Recién consolidado, editable por UGR |
| 2 | `enviado` | 2 | UGR lo envió al Ministerio |
| 3 | `aprobado` | 3 | Ministerio aprobó |
| 4 | `rechazado` | 4 | Ministerio rechazó |
| 5 | `cerrado` | 5 | Cerrado / finalizado |

---

## 2. Conceptos clave

### 2.1. Localidad HUÉRFANA vs CONSOLIDADA

```
es_huerfana = (id_edan IS NULL)
```

- **Huérfana** (`id_edan = NULL`): creada por Responsable Local pero aún no
  consolidada. Vive sola en `edan_localidades`.
- **Consolidada** (`id_edan = <algo>`): ya fue agrupada en un EDAN cabecera.

El campo `es_huerfana` en las respuestas es **calculado por el servidor**
(id_edan IS NULL). NO lo envía el cliente.

### 2.2. Cuándo se consolida

Una localidad es **consolidable** cuando cumple TODAS estas condiciones:

```
✓ id_edan IS NULL                (huérfana)
✓ id_edan_localidad_estado = 'aprobado'  (UGR la aprobó)
✓ Mismo id_municipio
✓ Mismo id_tipo_evento
```

El UGR municipio puede agrupar N localidades en 1 EDAN cabecera.

### 2.3. Totales

#### Totales de LOCALIDAD

Cada `edan_localidades` tiene 3 totales propios:

```sql
edan_localidades.total_poblacion_afectada      INT NOT NULL DEFAULT 0
edan_localidades.total_familias_afectadas      INT NOT NULL DEFAULT 0
edan_localidades.total_familias_damnificadas   INT NOT NULL DEFAULT 0
```

Estos totales los **asigna el usuario (Responsable Local)** al llenar el
formulario. NO se calculan automáticamente desde las secciones 1:N
(`impacto_poblacion`, etc.) — son resumen agregado que el oficial reporta.

#### Totales de EDAN (cabecera)

Los totales del EDAN cabecera son **SIEMPRE la SUMA de los totales de todas las
localidades vinculadas**:

```sql
edan.total_poblacion_afectada =
    SUM(edan_localidades.total_poblacion_afectada)
    WHERE id_edan = <este EDAN>

edan.total_familias_afectadas =
    SUM(edan_localidades.total_familias_afectadas)
    WHERE id_edan = <este EDAN>

edan.total_familias_damnificadas =
    SUM(edan_localidades.total_familias_damnificadas)
    WHERE id_edan = <este EDAN>
```

> ⚠️ **IMPORTANTE:** los totales del EDAN cabecera NO se actualizan
> automáticamente si después cambias los totales de una localidad. La
> consolidación hace un **snapshot** de los totales al momento de consolidar.
> Si modificas localidades después, debes re-consolidar (o el UGR ajusta
> manualmente el EDAN cabecera).

#### Totales de SECCIONES 1:N

Cada sección (`danos_viales`, `establecimientos_salud`, etc.) tiene sus
propios conteos internos. Ejemplo:

```
danos_vivienda:
  dano_parcial INT   → # viviendas con daño parcial
  dano_total   INT   → # viviendas con daño total

impacto_poblacion:
  rango           VARCHAR
  fallecidos      INT
  heridos         INT
  desaparecidos   INT

proteccion:
  grupo  VARCHAR
  mujeres INT
  hombres INT
  total   INT   ← calculado por el servicio: mujeres + hombres
```

El servicio **calcula `proteccion.total = mujeres + hombres`** al insertar
cada grupo vulnerable.

---

## 3. APIs del flujo (end-to-end)

### 3.1. FLUJO COMPLETO con endpoints

```
┌──────────────────────────────────────────────────────────────────┐
│ RESPONSABLE LOCAL (rol 7)                                        │
└──────────────────────────────────────────────────────────────────┘

1. Crear localidad huérfana (estado='borrador'):
   POST /api/v1/edan/{id_edan}/localidades  → id_edan_localidad

   NOTA: {id_edan} en URL es el EDAN **padre** lógico (departamento/provincia/
   municipio). Como la localidad es huérfana, el server la guarda con id_edan=NULL.
   En realidad este endpoint corresponde a crear una EDAN_localidad sin padre
   consolidado. Ver 3.1.1.

2. Llenar las secciones (1:N):
   POST /api/v1/edan/localidades/{id}/danos-viales
   POST /api/v1/edan/localidades/{id}/salud-establecimientos
   POST /api/v1/edan/localidades/{id}/danos-agricultura
   ...etc.

3. Subir fotos por sección (multipart):
   POST /api/v1/edan/localidades/{id}/danos-viales/con-foto
   ...etc.

4. Ver TODAS sus localidades (huérfanas + consolidadas):
   GET  /api/v1/edan/localidades/mis-reportes?solo_huerfanas=true
   GET  /api/v1/edan/localidades/mis-resumen

5. Sincronizar offline → online (push):
   POST /api/v1/edan/localidades/sync

6. Cambiar estado de localidad (borrador → enviado_ugr):
   PUT  /api/v1/edan/localidades/{id}/estado  body: {id_edan_localidad_estado: 2}

   ┌──────────────────────────────────────────────────────────────┐
   │ UGR MUNICIPIO (rol 6)                                        │
   └──────────────────────────────────────────────────────────────┘

7. Aprobar la localidad (enviado_ugr → aprobado):
   PUT  /api/v1/edan/localidades/{id}/estado  body: {id_edan_localidad_estado: 3}

8. Ver qué hay listo para consolidar (filtrado por estado='aprobado'):
   GET  /api/v1/edan/consolidar/pendientes?id_municipio=20101
   → retorna grupos por (municipio, tipo_evento) con array de localidad_ids

9. CONSOLIDAR — crear EDAN cabecera:
   POST /api/v1/edan/consolidar
   body: {
     "id_municipio": 20101,
     "id_tipo_evento": 3,
     "localidad_ids": [14, 15, 16, 17]
   }
   → crea fila en `edan.edan` con totales = SUM de las 4 localidades
   → UPDATE edan_localidades SET id_edan = <nuevo> WHERE id_edan_localidad IN (...)
   → retorna EDAN completo con todas las secciones

10. Modificar EDAN cabecera (opcional):
    PUT  /api/v1/edan/{id_edan}
    PUT  /api/v1/edan/{id_edan}/estado  body: {id_estado: 2}  # enviado

11. Subir PDFs al repositorio del EDAN:
    POST /api/v1/repositorio/edan/{id_edan}/documentos  (multipart PDF)

12. Ver documentos:
    GET  /api/v1/repositorio/edan/{id_edan}/documentos
    GET  /api/v1/repositorio/documentos/filtrar?id_edan={id_edan}

    ┌──────────────────────────────────────────────────────────────┐
    │ MINISTERIO / LECTURA (rol 8)                                 │
    └──────────────────────────────────────────────────────────────┘

13. Listar EDANs (con filtros):
    GET  /api/v1/edan?estado=aprobado&id_municipio=20101

14. Ver EDAN completo:
    GET  /api/v1/edan/{id_edan}

15. Cambiar estado a aprobado/cerrado:
    PUT  /api/v1/edan/{id_edan}/estado
```

### 3.2. Endpoints clave

#### `POST /api/v1/edan/consolidar` (tag EDAN_LOCALIDADES)

**Input** (`ConsolidarIn`):

```json
{
  "id_municipio": 20101,
  "id_tipo_evento": 3,
  "localidad_ids": [14, 15, 16]
}
```

**Validaciones del server:**
1. `localidad_ids` no vacío.
2. Todas las localidades existen, están en estado `aprobado`, tienen `id_edan=NULL`,
   pertenecen al mismo municipio y al mismo tipo de evento.
3. Agrupa geografía común (departamento/provincia) y suma totales.

**Output**: EDAN completo con todas las localidades + secciones anidadas.

#### `GET /api/v1/edan/consolidar/pendientes` (tag EDAN_LOCALIDADES)

Lista las localidades que están listas para consolidar, agrupadas por
(municipio, tipo_evento).

**Query params:**
- `id_municipio` (opcional): filtrar por municipio
- `estado` (default=`aprobado`): nombre del estado de localidad

**Output:**

```json
{
  "status": "success",
  "total": 3,
  "data": [
    {
      "id_municipio": 20101,
      "municipio_nombre": "La Paz",
      "id_departamento": 2,
      "departamento_nombre": "La Paz",
      "id_provincia": 2,
      "provincia_nombre": "Murillo",
      "id_tipo_evento": 3,
      "tipo_evento_nombre": "Granizada",
      "cantidad_localidades": 4,
      "localidad_ids": [14, 15, 16, 17],
      "total_poblacion_afectada": 1240,
      "total_familias_afectadas": 320,
      "total_familias_damnificadas": 45,
      "fecha_evento": "2026-07-15"
    },
    ...
  ]
}
```

Esto es lo que el UGR ve para decidir qué consolidar.

#### `GET /api/v1/edan/localidades/mis-reportes` (tag EDAN_LOCALIDADES)

Lista las localidades del usuario actual (el que está autenticado).

**Query params:**
- `solo_huerfanas`: `true` → solo huérfanas, `false` → solo consolidadas,
  `null` → todas (default).

**Output** (cada localidad con todas sus secciones):

```json
{
  "id_edan_localidad": 14,
  "id_edan": null,            ← null = huérfana
  "es_huerfana": true,        ← calculado
  "id_municipio": 20101,
  "municipio": {"id": 20101, "codigo_ine": "020101", "nombre": "La Paz", ...},
  "id_tipo_evento": 3,
  "tipo_evento": {"id_tipo_evento": 3, "nombre": "Granizada"},
  "localidad": "Comunidad A",
  "total_poblacion_afectada": 320,
  "danos_viales": [...],
  "danos_agricultura": [...],
  "establecimientos_salud": [...],
  ...
}
```

#### `GET /api/v1/edan/localidades/mis-resumen` (tag EDAN_LOCALIDADES)

Resumen agregado del usuario (para dashboard).

**Output:**

```json
{
  "id_usuario": 2,
  "total_localidades": 4,
  "total_huerfanas": 2,
  "total_consolidadas": 2,
  "total_huerfanas_con_estado": 1,
  "total_consolidadas_con_estado": 2,
  "por_estado": {
    "borrador": 1,
    "aprobado": 1,
    "enviado_ugr": 0,
    "rechazado_ugr": 0
  },
  "por_tipo_evento": [
    {"id_tipo_evento": 3, "nombre": "Granizada", "cantidad": 4}
  ]
}
```

---

## 4. Ejemplo completo paso a paso

### Escenario

> Una granizada afecta 4 comunidades del municipio de La Paz (20101). El
> Responsable Local (rol 7) crea 4 localidades huérfanas, las llena, las envía
> al UGR. El UGR (rol 6) aprueba las 4 y las consolida en un solo EDAN.

### Paso 1: Responsable Local crea 4 localidades (todas huérfanas)

```bash
curl -X POST $BASE/api/v1/edan/0/localidades \
  -H "Authorization: Bearer $TOKEN_LOCAL" \
  -H "Content-Type: application/json" \
  -d '{
    "id_tipo_localidad": 1,
    "id_departamento": 2,
    "id_provincia": 2,
    "id_municipio": 20101,
    "id_tipo_evento": 3,
    "localidad": "Comunidad A",
    "fecha_evento": "2026-07-15",
    "total_poblacion_afectada": 80,
    "total_familias_afectadas": 20,
    "total_familias_damnificadas": 3,
    "imp_agropecuario": true,
    "imp_vivienda": true
  }'
# → id_edan_localidad: 14, id_edan=null, es_huerfana=true
```

Repetir para B, C, D → ids 15, 16, 17.

### Paso 2: Llenar secciones

```bash
# Daños agricultura para localidad 14
curl -X POST $BASE/api/v1/edan/localidades/14/danos-agricultura \
  -H "Authorization: Bearer $TOKEN_LOCAL" \
  -H "Content-Type: application/json" \
  -d '[{
    "tipo_cultivo": "Papa",
    "id_cultivo": 4,
    "hectareas_afectadas": 12,
    "hectareas_perdidas": 5,
    "necesidades_inmediatas": "Semillas"
  }]'

# Daños vivienda
curl -X POST $BASE/api/v1/edan/localidades/14/danos-vivienda \
  -H "Authorization: Bearer $TOKEN_LOCAL" \
  -H "Content-Type: application/json" \
  -d '[{
    "comunidad": "Comunidad A",
    "dano_parcial": 5,
    "dano_total": 2
  }]'
```

### Paso 3: Enviar al UGR

```bash
curl -X PUT $BASE/api/v1/edan/localidades/14/estado \
  -H "Authorization: Bearer $TOKEN_LOCAL" \
  -H "Content-Type: application/json" \
  -d '{"id_edan_localidad_estado": 2}'  # enviado_ugr
```

### Paso 4: UGR aprueba

```bash
curl -X PUT $BASE/api/v1/edan/localidades/14/estado \
  -H "Authorization: Bearer $TOKEN_UGR" \
  -H "Content-Type: application/json" \
  -d '{"id_edan_localidad_estado": 3}'  # aprobado
```

### Paso 5: UGR ve qué consolidar

```bash
curl -X GET "$BASE/api/v1/edan/consolidar/pendientes?id_municipio=20101" \
  -H "Authorization: Bearer $TOKEN_UGR"
```

```json
{
  "status": "success",
  "total": 1,
  "data": [{
    "id_municipio": 20101,
    "municipio_nombre": "La Paz",
    "id_tipo_evento": 3,
    "tipo_evento_nombre": "Granizada",
    "cantidad_localidades": 4,
    "localidad_ids": [14, 15, 16, 17],
    "total_poblacion_afectada": 320,
    "total_familias_afectadas": 80,
    "total_familias_damnificadas": 12
  }]
}
```

### Paso 6: UGR consolida

```bash
curl -X POST $BASE/api/v1/edan/consolidar \
  -H "Authorization: Bearer $TOKEN_UGR" \
  -H "Content-Type: application/json" \
  -d '{
    "id_municipio": 20101,
    "id_tipo_evento": 3,
    "localidad_ids": [14, 15, 16, 17]
  }'
```

**Server ejecuta (transacción atómica):**

```sql
-- 1) INSERT cabecera (SOLO id_estado, NO columna 'estado')
INSERT INTO edan.edan (
  codigo_edan, id_departamento, id_provincia, id_municipio,
  id_tipo_evento, fecha_llenado, fecha_evento, hora_evento,
  total_poblacion_afectada, total_familias_afectadas,
  total_familias_damnificadas, id_usuario_ugr, id_estado
) VALUES (
  '020101/2026/001',     ← generado por _next_codigo_edan
  2, 2, 20101,           ← geografía común (de la primera localidad)
  3,                     ← tipo evento
  CURRENT_DATE,          ← fecha_llenado = hoy
  '2026-07-15',          ← MIN(fecha_evento) entre las 4 localidades
  '14:30:00',            ← MIN(hora_evento)
  320, 80, 12,           ← SUM de totales de las 4 localidades
  6,                     ← id_usuario_ugr (del JWT)
  1                      ← id_estado = 1 (borrador)
) RETURNING id_edan;     → id_edan = 50

-- 2) UPDATE localidades → todas con id_edan = 50
UPDATE edan.edan_localidades
   SET id_edan = 50,
       fecha_modificacion = NOW(),
       pendiente_actualizacion = TRUE
 WHERE id_edan_localidad IN (14, 15, 16, 17);
```

**Output**: EDAN completo (cabecera + 4 localidades + todas sus secciones).

### Paso 7: Verificar

```bash
# Antes: localidad 14 era huérfana (id_edan=null, es_huerfana=true)
# Después:
curl $BASE/api/v1/edan/localidades/mis-reportes | jq '.data[0] | {id_edan_localidad, id_edan, es_huerfana}'
# { "id_edan_localidad": 14, "id_edan": 50, "es_huerfana": false }

# Cabecera del EDAN (modo detallado — default):
curl $BASE/api/v1/edan/50 | jq '.data | {id_edan, codigo_edan, total_poblacion_afectada, localidades: .localidades | length}'
# { "id_edan": 50, "codigo_edan": "020101/2026/001",
#   "total_poblacion_afectada": 320, "localidades": 4 }

# Cabecera del EDAN (modo compacto — solo sumatorias, sin secciones):
curl "$BASE/api/v1/edan/50?modo=compacto" | jq '.data | {id_edan, sumatorias}'
# { "id_edan": 50, "sumatorias": {
#     "total_poblacion_afectada": 320,
#     "total_familias_afectadas": 80,
#     "total_familias_damnificadas": 12,
#     "danos_agricultura": {"hectareas_afectadas": 42, "hectareas_perdidas": 18},
#     "danos_pecuarios": {"total_animales_afectados": 80, "total_animales_muertos": 13},
#     "proteccion": {"mujeres": 25, "hombres": 15, "total": 40},
#     "establecimientos_salud": {"total_medicos": 5, "total_enfermeras": 8},
#     "necesidad_salud": {"total_personas": 150}
# }}
```

### Paso 7b: Desconsolidar (si es necesario)

Si el UGR necesita quitar una localidad del EDAN:

```bash
curl -X PUT $BASE/api/v1/edan/localidades/14/desconsolidar \
  -H "Authorization: Bearer $TOKEN_UGR"
```

**Qué hace el server:**
1. Desvincula la localidad (`id_edan = NULL`)
2. Recalcula los totales del EDAN (resta los valores de la localidad removida)
3. Si el EDAN queda sin localidades → lo elimina (retorna 404)
4. Si quedan localidades → retorna el EDAN con totales actualizados

### Paso 7c: Consolidar automático

El UGR puede consolidar TODAS las localidades pendientes de un grupo de una sola vez:

```bash
curl -X POST $BASE/api/v1/edan/consolidar/auto \
  -H "Authorization: Bearer $TOKEN_UGR" \
  -H "Content-Type: application/json" \
  -d '{
    "id_municipio": 20101,
    "id_tipo_evento": 3
  }'
```

**Qué hace el server:**
1. Busca todas las localidades aprobadas huérfanas del municipio+tipo_evento
2. Si hay 0 → error 400
3. Si hay 1 o más → consolida todas en un solo EDAN

### Paso 7d: Deshacer consolidación

Si el UGR consolidó por error o necesita reorganizar, puede deshacer todo el EDAN:

```bash
curl -X PUT $BASE/api/v1/edan/{id_edan}/deshacer \
  -H "Authorization: Bearer $TOKEN_UGR"
```

**Qué hace el server (transacción atómica):**
1. Verifica que el EDAN existe (404 si no)
2. Verifica que está en estado **Borrador** (`id_estado = 1`) — si fue enviado al Ministerio, no se puede deshacer (400)
3. Verifica que el usuario es el UGR que lo consolidó (403 si no)
4. Verifica que no tenga documentos en el repositorio (400 si tiene)
5. Libera TODAS las localidades: `SET id_edan = NULL` (vuelven a ser huérfanas)
6. Elimina el EDAN cabecera
7. Retorna `{"edan_deshecho": id, "localidades_liberadas": N}`

**Restricciones:**
- Solo **rol 6** (UGR Municipio)
- Solo EDANs en estado **Borrador** (`id_estado = 1`)
- No debe tener documentos en repositorio

**Las localidades conservan su estado** "Aprobado UGR" (`id_estado = 3`), por lo que quedan listas para re-consolidarse inmediatamente.

```json
{
  "status": "success",
  "message": "EDAN deshecho correctamente",
  "data": {
    "edan_deshecho": 65,
    "localidades_liberadas": 2
  }
}
```

---

## 5. Modo compacto vs detallado

El endpoint `GET /api/v1/edan/{id}` acepta el query parameter `modo`:

| Modo | Descripción | Uso recomendado |
|------|-------------|-----------------|
| `detallado` (default) | Devuelve TODAS las localidades con TODAS sus secciones anidadas | Vista completa del EDAN |
| `compacto` | Solo cabecera del EDAN + `sumatorias` calculadas desde las secciones | Dashboard, reportes, listados |

### Ejemplo de respuesta compacta

```json
{
  "status": "success",
  "data": {
    "id_edan": 50,
    "codigo_edan": "020101/2026/001",
    "total_poblacion_afectada": 320,
    "total_familias_afectadas": 80,
    "total_familias_damnificadas": 12,
    "estado": "borrador",
    "municipio": {"id": 20101, "nombre": "La Paz"},
    "tipo_evento": {"id_tipo_evento": 3, "nombre": "Granizada"},
    "sumatorias": {
      "localidades_count": 4,
      "danos_agricultura": {
        "hectareas_afectadas": 42.0,
        "hectareas_perdidas": 18.0
      },
      "danos_pecuarios": {
        "total_animales_afectados": 80,
        "total_animales_muertos": 13
      },
      "proteccion": {
        "mujeres": 25,
        "hombres": 15,
        "total": 40
      },
      "establecimientos_salud": {
        "total_medicos": 5,
        "total_enfermeras": 8,
        "total_otro": 3
      },
      "necesidad_salud": {
        "total_personas": 150
      }
    }
  }
}
```

Las sumatorias se calculan haciendo **SUM** de los valores de todas las localidades vinculadas al EDAN.

---

## 5. Permisos por rol

| Rol | Descripción | Puede |
|-----|-------------|-------|
| 6 | UGR Municipio | ✅ Crear localidad huérfana<br>✅ Aprobar/rechazar localidad<br>✅ **Consolidar**<br>✅ Modificar EDAN cabecera<br>✅ Subir PDFs al repositorio |
| 7 | Responsable Local | ✅ Crear localidad huérfana<br>✅ Llenar secciones + subir fotos<br>✅ Enviar al UGR (`estado=enviado_ugr`) |
| 8 | Alcalde / Ministerio | ✅ Lectura de todo |

Variables en código:

```python
ROLES_LOCALES = (6, 7)         # Crear/editar localidades
ROLES_EDAN_CREA = (6,)         # Solo UGR puede consolidar
ROLES_LECTURA = (6, 7, 8)      # Lectura
```

---

## 6. Resumen de endpoints (tag `EDAN_LOCALIDADES`)

| Método | Path | Rol | Función |
|--------|------|-----|---------|
| GET | `/edan/localidades/mis-resumen` | 6,7 | Dashboard agregado del usuario |
| GET | `/edan/localidades/mis-reportes` | 6,7 | Lista de mis localidades (`?solo_huerfanas=true/false`) |
| POST | `/edan/{id_edan}/localidades` | 6,7 | Crear localidad huérfana |
| PUT | `/edan/{id_edan}/localidades/{id}` | 6,7 | Editar localidad |
| DELETE | `/edan/{id_edan}/localidades/{id}` | 6,7 | Borrar localidad (soft) |
| DELETE | `/edan/localidades/{id}` | 6,7 | Borrar localidad standalone |
| POST | `/edan/localidades/sync` | 6,7 | Push offline → online |
| GET | `/edan/localidades/sync/pull` | 6,7 | Pull online → offline |
| GET | `/edan/consolidar/pendientes` | 6 | Lista pendientes de consolidar |
| POST | `/edan/consolidar` | 6 | **Consolidar N localidades → 1 EDAN** |
| POST | `/edan/consolidar/auto` | 6 | **Consolidar automático (todas las pendientes de un grupo)** |
| PUT | `/edan/localidades/{id}/desconsolidar` | 6 | **Quitar 1 localidad del EDAN (recalcula totales)** |
| PUT | `/edan/{id}/deshacer` | 6 | **Deshacer consolidación completa (solo borrador)** |
| PUT | `/edan/localidades/{id}/estado` | 6,7 | Cambiar estado de localidad |
| GET | `/edan/{id}?modo=compacto` | 6,7,8 | **EDAN solo con sumatorias (sin secciones)** |
| GET | `/edan/{id}` | 6,7,8 | EDAN completo con todas las localidades y secciones |
| GET | `/edan/localidades/{id}/<seccion>` | 6,7 | Leer una sección (1:N) |
| POST | `/edan/localidades/{id}/<seccion>` | 6,7 | Agregar item a sección |
| PUT | `/edan/localidades/{id}/<seccion>/{item_id}` | 6,7 | Editar item de sección |
| DELETE | `/edan/localidades/{id}/<seccion>/{item_id}` | 6,7 | Borrar item de sección |
| POST | `/edan/localidades/{id}/<seccion>/con-foto` | 6,7 | Crear item + subir foto (multipart) |

Secciones (`<seccion>`): `danos-viales`, `danos-infra-publica`, `danos-vivienda`,
`danos-agricultura`, `danos-pecuarios`, `salud-establecimientos`,
`servicios-basicos`, `unidades-educativas`, `impacto-poblacion`,
`infra-productiva`, `proteccion`.

---

## 7. Sincronización offline (app móvil)

### Endpoints de sincronización

| Método | Path | Rol | Función |
|--------|------|-----|---------|
| POST | `/api/v1/edan/localidades/sync` | 6, 7 | Push: subir localidades desde la app móvil |
| GET | `/api/v1/edan/localidades/sync/pull` | 6, 7 | Pull: descargar localidades del servidor |
| POST | `/api/v1/edan/sync` | 6, 7 | Push: subir EDANs (cabeceras) desde la app |
| GET | `/api/v1/edan/sync/pull` | 6, 7 | Pull: descargar EDANs del servidor |

> **Documentación completa** del contrato HTTP (request, response, curl examples, valores
> permitidos de cada campo, CHECK constraints): ver `docs/SINCRONIZACION.md` sección
> "Contrato HTTP de los endpoints de sincronización".

### Flujo offline-first

1. App móvil crea localidad con `id_local = UUID` (generado en cliente).
2. App guarda en SQLite local + cola de sincronización.
3. Cuando hay conectividad:
   ```
   POST /api/v1/edan/localidades/sync
   body: { "localidades": [LocalidadCreate, ...] }
   ```
4. Server:
   - Si `pendiente_eliminacion=true` → DELETE físico + tombstone
   - Si `id_local` no existe → INSERT con `pendiente_actualizacion=false`
   - Si `id_local` existe → UPDATE por LWW (last-write-wins)
   - Si `fecha_modificacion` del payload es más vieja → conflicto (no aplica)
   - Devuelve las localidades convergidas con `id_edan_localidad` real
5. Las secciones se reemplazan completamente en cada UPDATE (DELETE + INSERT).
   El cliente debe enviar siempre el set completo de secciones.

### Pull (caché inicial e incremental)

```
GET /api/v1/edan/localidades/sync/pull
GET /api/v1/edan/localidades/sync/pull?fecha_desde=2026-08-01T00:00:00
GET /api/v1/edan/localidades/sync/pull?skip=0&limit=50
```

Parámetros: `fecha_desde` (ISO timestamp), `skip` (offset), `limit` (1-1000, default 50).
Retorna las localidades del usuario modificadas después de `fecha_desde`, con paginación.

---

## 8. Errores comunes

| HTTP | Causa | Solución |
|------|-------|----------|
| 400 | Consolidar sin localidad_ids | Enviar al menos 1 |
| 400 | Algunas localidades no consolidables | Verificar estado=`aprobado`, id_edan=null, mismo municipio/tipo evento |
| 403 | Sin rol para consolidar | Solo rol 6 (UGR) puede |
| 404 | EDAN o localidad no existe | Verificar id |
| 409 | Conflicto al consolidar | Otra transacción consolidó antes; refrescar pendientes |

---

## 9. Diagrama de transición de estados

```
LOCALIDAD (edan_localidades):
  borrador (1) ──► enviado_ugr (2) ──► aprobado (3) ──► (CONSOLIDADA)
       ▲                  │                  │
       │                  ▼                  ▼
       │            rechazado_ugr (4)    aprobado_ajuste_ugr (5)
       └────────── desde cualquiera ─────┘

EDAN (edan.edan):
  borrador (1) ──► enviado (2) ──► aprobado (3) ──► cerrado (5)
                          │
                          └──► rechazado (4)
```

---

## 10. Pruebas exhaustivas (16/16 PASS)

Suite de pruebas con datos aleatorios ejecutada en `v1.3.0`:

### Grupo 1 — Consolidación básica
| Test | Descripción | Resultado |
|------|-------------|-----------|
| T1 | Consolidar 2+ localidades → SUM totales | PASS |
| T2 | `GET /edan/{id}?modo=detallado` → secciones completas | PASS |
| T3 | `GET /edan/{id}?modo=compacto` → sumatorias correctas | PASS |
| T4 | Consolidar 1 sola localidad | PASS |
| T5 | Consolidar localidad en estado borrador → 400 | PASS |
| T6 | Consolidar localidades de diferentes municipios → 400 | PASS |

### Grupo 2 — Desconsolidar
| Test | Descripción | Resultado |
|------|-------------|-----------|
| T7 | Quitar 1 localidad → totales recalculados | PASS |
| T8 | Quitar todas menos 1 → EDAN persiste con totals de la última | PASS |
| T9 | Quitar última localidad → EDAN eliminado (404) | PASS |

### Grupo 3 — Consolidar automático
| Test | Descripción | Resultado |
|------|-------------|-----------|
| T10 | `POST /consolidar/auto` → consolida todas las pendientes del grupo | PASS |
| T11 | Repetir cuando no hay pendientes → 404 | PASS |

### Grupo 4 — Reportes
| Test | Descripción | Resultado |
|------|-------------|-----------|
| T12 | `GET /reportes/mis-resumen` → counts consistentes | PASS |
| T13 | `GET /reportes/mis-reportes` → lista incluye EDANs creados | PASS |

### Grupo 5 — Casos borde
| Test | Descripción | Resultado |
|------|-------------|-----------|
| T14 | Consolidar localidades con secciones vacías → sumatorias = 0 | PASS |
| T15 | Mezclar localidades vacías y con datos → suma solo las con datos | PASS |
| T16 | `modo=compacto` con secciones vacías → sin errores | PASS |

**Datos de prueba:** 8-10 localidades aleatorias (municipios 70101/70102, tipo_evento 1/2/3, poblaciones 50-500), secciones con datos random (agricultura, pecuario, protección, salud). Limpieza completa al finalizar.

### Grupo 6 — Deshacer consolidación
| Test | Descripción | Resultado |
|------|-------------|-----------|
| T1 | Deshacer EDAN borrador con 2 localidades → EDAN eliminado, localidades huérfanas con estado Aprobado UGR | PASS |
| T1b | Verificar localidades huérfanas conservan estado "Aprobado UGR" (3) | PASS |
| T1c | Verificar EDAN eliminado (GET → 404) | PASS |
| T2 | Deshacer EDAN enviado (estado 2) → 400 "Solo borrador" | PASS |
| T3 | Deshacer EDAN inexistente → 404 | PASS |
| T4 | Deshacer con rol incorrecto (Responsable Local) → 403 | PASS |

**Total: 22/22 tests PASS**

---

**Última actualización:** rama `v1.3.0` — consolidación EDAN, modo compacto, desconsolidar, consolidar automático, deshacer consolidación, fix sync API, 22/22 tests PASS.
