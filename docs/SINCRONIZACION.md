# Sincronización EDAN — Modelo en PostgreSQL (offline-first)

Documenta la **lógica de sincronización tal como quedó definida en la base de
datos** (migraciones `v1.8.0` y `v1.9.0`), preparada para el flujo
**AppSheet (móvil) ↔ servidor ↔ PC (web)**. No documenta endpoints: la capa
API se ajustará al modelo en una etapa posterior.

## Objetivo

Un formulario EDAN se captura en campo con la app (sin conexión), se sube al
servidor y se completa/visualiza en la PC. El mismo documento debe poder
editarse **desde cualquier extremo** y converger sin duplicados ni pérdidas,
usando la regla simple **last-write-wins (LWW)**.

## Modelo de datos

### Campos de sync en `edan.edan`

| Campo | Tipo | Rol en la sincronización |
|---|---|---|
| `id_edan` | BIGSERIAL PK | Identidad del documento **en el servidor** |
| `id_local` | VARCHAR(64) UNIQUE | UUID generado en el dispositivo (AppSheet). **Identidad estable del documento entre dispositivos**; el servidor lo mapea a `id_edan` |
| `fecha_creacion` | TIMESTAMP | Auditoría, `NOW()` del servidor (no participa en sync) |
| `fecha_modificacion` | TIMESTAMP | **Autoridad de tiempo**. `NOW()` al escribir. Soporta pull incremental y LWW |
| `pendiente_actualizacion` | BOOLEAN (FALSE) | Flag "dirty": cambios locales sin subir |
| `pendiente_eliminacion` | BOOLEAN (FALSE) | Tombstone de borrado |
| `id_usuario_ugr` | INTEGER FK | **Dueño del pull** del EDAN (rol 6, UGR Municipio). Índice `idx_edan_sync_pull` |
| `id_usuario_alcalde` | INTEGER FK | Alcalde (rol 8) que registró/edita desde la app |
| `id_estado` | INTEGER FK (1) | Ciclo de vida (`borrador`, `enviado`, `aprobado`, `rechazado`, `cerrado`). `borrador` = id_estado 1 |

### Campos de sync en `edan.edan_localidades`

| Campo | Tipo | Rol en la sincronización |
|---|---|---|
| `id_edan_localidad` | SERIAL PK | Identidad **en el servidor** |
| `id_local` | VARCHAR(64) UNIQUE | UUID del dispositivo. Identidad estable de la localidad |
| `id_edan` | BIGINT FK (SET NULL) | EDAN padre |
| `id_usuario` | INTEGER FK | **Dueño del pull** de la localidad. Índice `idx_edan_localidades_sync_pull` |
| `fecha_modificacion` | TIMESTAMP | Autoridad de tiempo (mismo uso que en la cabecera) |
| `pendiente_actualizacion` | BOOLEAN (FALSE) | Flag "dirty" |
| `pendiente_eliminacion` | BOOLEAN (FALSE) | Tombstone de borrado |

### Columnas eliminadas (no se usan)

| Columna | Motivo |
|---|---|
| `sincronizado` (ambas tablas) | Redundante: el flag de "no subido" es `pendiente_actualizacion` |
| `es_borrador` (edan) | Derivable: `id_estado = 1` |
| `id_server` (ambas tablas) | El id del servidor es `id_edan` / `id_edan_localidad` |
| `intentos_sync`, `ultimo_error` (edan) | La cola/reintentos se manejan en el cliente |
| `id_usuario` (edan.edan) | Sustituido por `id_usuario_ugr` + `id_usuario_alcalde` |

## Reglas de la sincronización

### 1. Identidad: el `id_local` manda

- El dispositivo genera `id_local = UUID` al crear el documento y nunca lo cambia.
- **Dedupe** por `id_local`: si el servidor ya tiene una fila con ese `id_local`,
  es el mismo documento (aunque el dispositivo aún no conozca su `id_edan`).
- El `id_edan` asignado por el servidor se le devuelve al dispositivo como
  referencia, pero **nunca** se usa como clave de comparación para sync.
- El índice único **parcial** `edan_id_local_key` (`WHERE id_local IS NOT NULL`)
  garantiza que un `id_local` no pueda existir dos veces.

### 2. Autoridad de tiempo: `fecha_modificacion`

- El **servidor es la autoridad de tiempo**: cada escritura fija
  `fecha_modificacion = NOW()`.
- La `fecha_modificacion` que envía el cliente solo sirve para saber **qué
  versión conoce** y detectar versiones atrasadas.
- **LWW**: si dos extremos editan el mismo documento, gana la versión con
  `fecha_modificacion` más reciente.

### 3. Flags de estado

- `pendiente_actualizacion = TRUE` → "tengo cambios que aún no subí" (dirty).
  Se limpia al aplicar el push.
- `pendiente_eliminacion = TRUE` → **tombstone**: borrado local que debe
  propagarse al otro extremo. El pull devuelve el documento con este flag y el
  otro extremo lo marca/oculta.
- Para no retroceder el reloj al marcar un borrado, se usa
  `fecha_modificacion = GREATEST(fecha_modificacion, NOW())`.

### 4. Dueño del pull

| Unidad | Dueño | Criterio |
|---|---|---|
| EDAN (cabecera) | `id_usuario_ugr` (rol 6) | El UGR ve/descarga todos los EDANs de su municipio |
| Localidad | `id_usuario` | La localidad viaja con su dueño |

Índices que soportan el pull incremental por dueño:

- `idx_edan_sync_pull (id_usuario_ugr, fecha_modificacion)`
- `idx_edan_localidades_sync_pull (id_usuario, fecha_modificacion)`

### 5. Push (subida) de un EDAN

1. Buscar por `id_local`.
2. **No existe** → INSERT (la cabecera conserva el `id_local` y la
   `fecha_modificacion` del cliente como referencia). Se limpian los flags.
3. **Existe** → comparar la `fecha_modificacion` que envía el cliente con la
   del servidor:
   - cliente más nuevo → UPDATE (LWW) y se devuelve el documento convergido;
   - cliente más viejo → **no se aplica** (conflicto): se devuelve la versión
     vigente para que el dispositivo la adopte.
4. **Tombstone** (`pendiente_eliminacion`) → marcar el registro en el servidor
   (no eliminación física), manteniendo la fecha con `GREATEST`.
5. El resultado siempre devuelve el documento **convergido** que el dispositivo
   debe guardar como su versión local.

### 6. Localidades dentro del EDAN

- El push de un EDAN reemplaza **el set completo de localidades** de la cabecera
  (delete + reinsert) preservando la identidad de sync de las que ya existían:
  `id_local`, `id_usuario`, `fecha_modificacion`, estado.
- De esta forma re-sincronizar el mismo EDAN **no duplica** localidades y no
  pierde el estado de las existentes.
- Toda escritura sobre una localidad de un EDAN **bump** la cabecera
  (`fecha_modificacion = NOW()`, `pendiente_actualizacion = TRUE`) para que el
  pull la detecte como modificada.

## Vínculo REA ↔ EDAN

- `edan.edan` ya no guarda `id_reporte_rea`: el vínculo vive en
  `rea.reporte_evento.id_edan` (FK inversa → `edan.edan.id_edan`, `ON DELETE
  SET NULL`, índice `idx_reporte_id_edan`).
- Un REA solo puede generar **un** EDAN; un EDAN puede agrupar varios REAs.
- Al crear/actualizar/borrar un EDAN la capa API mantiene ese vínculo en
  sincronía (el REA anterior se desvincula a NULL si el origen cambia).

## Escenarios de sincronización

### A. Solo app (el PC no participa)

```
app crea EDAN offline (id_local = UUID)
  → con conexión: push → servidor INSERT + asigna id_edan
  → app guarda el documento convergido (id_local + id_edan + flags limpios)
```

- El documento vive solo en el móvil y el servidor; el pull posterior de la app
  devuelve el mismo documento sin duplicados.

### B. Solo web (la app no participa)

```
PC crea/edita EDAN en el servidor (web, con conexión)
  → servidor genera id_local (UUID) para el documento
  → pull incremental por id_usuario_ugr devuelve el documento
```

- La web nunca ve flags de sync: `pendiente_actualizacion/eliminacion` quedan
  en FALSE. El `id_local` generado por el servidor asegura que el documento
  pueda adoptarse después desde la app.

### C. App → Web → App (captura en campo, cierre en PC)

```
1. app crea EDAN offline (id_local = X)
2. push → servidor crea id_edan, devuelve convergido (X → id_edan)
3. PC hace pull incremental → recibe el EDAN X y lo completa (PUT)
4. app hace pull → recibe la versión del PC (misma X, ahora actualizada)
5. app intenta re-push con su versión vieja → LWW: gana el PC, la app
   recibe la versión vigente y la adopta
```

### D. Web → App → Web (carga en web, edición en campo)

```
1. PC crea EDAN (servidor genera id_local = Y)
2. app hace pull → recibe el EDAN Y y lo edita offline
3. app push → LWW: si la app es más nueva, gana; si es más vieja, la app
   adopta la versión del servidor
4. PC hace pull → recibe la versión de la app
```

### E. Borrado propagado (tombstone)

```
app borra EDAN offline → pendiente_eliminacion = TRUE
  → push → servidor marca el registro (fecha con GREATEST)
  → PC hace pull → ve el documento con pendiente_eliminacion = TRUE
    y lo oculta/marca como eliminado
```

## Consultas útiles (PostgreSQL)

```sql
-- Documentos sucios (cambios locales sin subir)
SELECT id_edan, id_local, pendiente_actualizacion, fecha_modificacion
FROM edan.edan
WHERE pendiente_actualizacion = TRUE;

-- Tombsones (borrados pendientes de propagar)
SELECT id_edan, id_local, pendiente_eliminacion
FROM edan.edan
WHERE pendiente_eliminacion = TRUE;

-- Pull incremental de un UGR (marca de último sync = fecha_desde)
SELECT e.*
FROM edan.edan e
WHERE e.id_usuario_ugr = :id_ugr
  AND e.fecha_modificacion >= :fecha_desde
ORDER BY e.fecha_modificacion DESC;

-- Detectar duplicados de id_local (no debería haber: índice único parcial)
SELECT id_local, COUNT(*) FROM edan.edan
WHERE id_local IS NOT NULL GROUP BY id_local HAVING COUNT(*) > 1;

-- EDANs que provienen de un reporte REA (vínculo inverso)
SELECT r.id_reporte, r.comunidad, e.id_edan, e.id_local
FROM rea.reporte_evento r
LEFT JOIN edan.edan e ON e.id_edan = r.id_edan;
```

## Resumen de reglas

| Regla | Decisión |
|---|---|
| Dedupe | `id_local` (UUID), nunca `id_edan` |
| Conflictos | **LWW** por `fecha_modificacion`; el servidor es autoridad de tiempo |
| Push atrasado | No aplica; responde el documento vigente para que el cliente lo adopte |
| Borrado | Tombstone (`pendiente_eliminacion`), nunca DELETE físico |
| Dueño del pull | EDAN → `id_usuario_ugr`; Localidad → `id_usuario` |
| Re-sync | Idempotente (no duplica) y preserva identidad/estado de localidades |
| Subir | `pendiente_actualizacion` = TRUE hasta aplicar el push |

---

## Contrato HTTP de los endpoints de sincronización

### Endpoints de sincronización

| Método | Path | Rol | Función |
|--------|------|-----|---------|
| POST | `/api/v1/edan/localidades/sync` | 6, 7 | Push: subir localidades desde la app móvil |
| GET | `/api/v1/edan/localidades/sync/pull` | 6, 7 | Pull: descargar localidades del servidor |
| POST | `/api/v1/edan/sync` | 6, 7 | Push: subir EDANs (cabeceras) desde la app |
| GET | `/api/v1/edan/sync/pull` | 6, 7 | Pull: descargar EDANs del servidor |

---

### POST `/api/v1/edan/localidades/sync`

**Push offline → online.** Recibe un lote de localidades y las aplica al servidor.

- **Auth:** Bearer token (JWT)
- **Roles:** 6 (UGR Municipio), 7 (Responsable Local)
- **Content-Type:** `application/json`

#### Body (request)

```json
{
  "localidades": [ <LocalidadCreate>, ... ]
}
```

Cada item del array es un `LocalidadCreate`. El servidor procesa cada item independientemente:
si uno falla, los demás continúan (nunca falla el lote completo).

##### Campos obligatorios de LocalidadCreate

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id_local` | string | UUID generado por la app (offline-first dedup). **Obligatorio para identidad.** |

##### Campos del encabezado de la localidad

| Campo | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `localidad` | string | `""` | Nombre de la comunidad/barrio/ciudad |
| `id_tipo_localidad` | int \| null | null | FK a `edan.tipo_localidad` (ej: 2=Comunidad, 9=OTB) |
| `tipo_localidad` | string \| null | null | Nombre libre (alternativa al id, para compatibilidad con la app) |
| `id_edan_localidad_estado` | int \| null | null | FK a `edan.edan_localidades_estado` (1=Borrador, 2=Enviado UGR, 3=Aprobado UGR, 4=Rechazado UGR, 5=Aprobado Ajuste UGR, 6=En revision UGR) |
| `id_tipo_evento` | int \| null | null | FK a `edan.tipo_evento` (1=Inundación, 2=Riada, 3=Deslizamiento, 4=Helada, 5=Granizada, 6=Sequía, 7=Incendios, 8=Otros) |
| `id_departamento` | int \| null | null | FK a `shared.departamento` (ej: 7=Santa Cruz) |
| `id_provincia` | int \| null | null | FK a `shared.provincia` (ej: 701=Andrés Ibáñez) |
| `id_municipio` | int \| null | null | FK a `shared.municipio` (ej: 70101=Santa Cruz de la Sierra) |
| `id_usuario` | int \| null | null | FK a `usuarios.usuario`. El servidor lo asigna si no se envía |
| `fecha_llenado` | string \| null | null | Fecha ISO `YYYY-MM-DD` |
| `fecha_evento` | string \| null | null | Fecha ISO `YYYY-MM-DD` del evento |
| `hora_evento` | string \| null | null | Hora `HH:MM:SS` del evento |
| `total_poblacion_afectada` | int | 0 | Total de personas afectadas |
| `total_familias_afectadas` | int | 0 | Total de familias afectadas |
| `total_familias_damnificadas` | int | 0 | Total de familias damnificadas |

##### Campos de flags de sincronización

| Campo | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `id_local` | string \| null | null | UUID del dispositivo. **Clave de dedup** |
| `fecha_modificacion` | string \| null | null | Timestamp ISO. Usado para LWW (last-write-wins) |
| `pendiente_actualizacion` | bool | false | Flag "dirty": cambios locales sin subir |
| `pendiente_eliminacion` | bool | false | **Tombstone**: si `true`, elimina la localidad del servidor |

##### Flags de impacto (booleanos)

| Campo | Default | Descripción |
|-------|---------|-------------|
| `imp_poblacion` | false | ¿Hubo impacto en población? |
| `imp_salud` | false | ¿Hubo impacto en salud? |
| `imp_infraestructura` | false | ¿Hubo impacto en infraestructura? |
| `imp_servicios` | false | ¿Hubo impacto en servicios básicos? |
| `imp_educacion` | false | ¿Hubo impacto en educación? |
| `imp_vivienda` | false | ¿Hubo impacto en vivienda? |
| `imp_agropecuario` | false | ¿Hubo impacto agropecuario? |
| `imp_proteccion` | false | ¿Hubo impacto en grupos vulnerables? |
| `imp_necesidades` | false | ¿Hay necesidades humanitarias? |

##### Secciones opcionales (arrays — se envían vacíos o no se envían si no aplica)

Todas las secciones son OPCIONALES. Si una sección no se envía, simplemente no se crea.
Al actualizar una localidad existente, las secciones se **reemplazan completamente** (DELETE + INSERT).

**Secciones 1:N (listas de objetos):**

| Sección | Campos por item | Descripción |
|---------|-----------------|-------------|
| `impacto_poblacion` | `rango`, `fallecidos`, `heridos`, `desaparecidos`, `observaciones` | Impacto por rango etario |
| `establecimientos_salud` | `nombre_establecimiento`, `comunidad`, `nivel_atencion`, `dano_parcial`, `dano_total`, `medicos_afectados`, `enfermeras_afectadas`, `otros_afectados`, `fotografia`, `coordenada_lat`, `coordenada_lon` | Establecimientos de salud afectados |
| `danos_viales` | `via`, `puente`, `tramo`, `dano_parcial`, `dano_total`, `km_danio`, `necesidades_inmediatas`, `observaciones`, `fotografia`, `coordenada_lat`, `coordenada_lon` | Daños en vías/carreteras |
| `danos_infra_publica` | `comunidad`, `tipo_estructura`, `dano_parcial`, `dano_total`, `observaciones`, `fotografia`, `coordenada_lat`, `coordenada_lon` | Daños en infraestructura pública |
| `danos_vivienda` | `comunidad`, `dano_parcial` (int), `dano_total` (int), `necesidades_inmediatas`, `observaciones`, `fotografia`, `coordenada_lat`, `coordenada_lon` | Daños en viviendas (cantidades) |
| `danos_agricultura` | `tipo_cultivo`, `id_cultivo` (FK opcional a `shared.cultivo`), `hectareas_afectadas`, `hectareas_perdidas`, `necesidades_inmediatas`, `observaciones`, `fotografia`, `coordenada_lat`, `coordenada_lon` | Daños en agricultura |
| `danos_pecuarios` | `especie`, `id_especie` (FK opcional a `shared.pecuario`), `raza`, `animales_afectados`, `animales_muertos`, `necesidades_inmediatas`, `fotografia`, `coordenada_lat`, `coordenada_lon` | Daños en pecuarios |
| `servicios_basicos` | `tipo` (CHECK: `energia_electrica`, `agua_potable`, `alcantarillado`, `gas_domiciliario`, `telecomunicaciones`), `dano_parcial`, `dano_total`, `necesidades_inmediatas`, `observaciones`, `fotografia`, `coordenada_lat`, `coordenada_lon` | Daños en servicios básicos |
| `unidades_educativas` | `nombre_establecimiento`, `comunidad`, `dano_parcial`, `dano_total`, `suspension_clases`, `perdida_material`, `funciona_albergue`, `estudiantes`, `profesores`, `administrativos`, `observaciones`, `fotografia`, `coordenada_lat`, `coordenada_lon` | Daños en unidades educativas |
| `infra_productiva` | `tipo`, `dano_parcial` (int), `dano_total` (int), `fotografia`, `coordenada_lat`, `coordenada_lon` | Daños en infraestructura productiva |
| `proteccion` | `id_grupo_vulnerable_catalogo` (FK a `edan.grupo_vulnerable`), `grupo` (objeto anidado: `{id, codigo, nombre, orden}`), `mujeres`, `hombres`, `total`, `apoyo_psicologico`, `reposicion_documentos`, `observaciones` | Grupos vulnerables protegidos |

**Secciones 1:1 (objetos únicos):**

| Sección | Campos | Descripción |
|---------|--------|-------------|
| `necesidad_primera_respuesta` | `busqueda`, `salvamento`, `evacuacion`, `observaciones` | Necesidades de primera respuesta |
| `necesidad_salud` | `numero_personas`, `otras_necesidades`, `observaciones` | Necesidades de salud |
| `necesidad_humanitaria` | `alimentos`, `refugio_vivienda`, `ropa_cama`, `articulos_higiene`, `articulos_cocina`, `prendas_vestir`, `herramientas`, `almacenamiento_agua`, `banos`, `obs_*` (texto libre para cada uno) | Necesidades humanitarias |

#### Respuestas del endpoint

El endpoint devuelve una lista de resultados, uno por cada localidad enviada.

##### 1. INSERT exitoso (localidad nueva)

```json
{
  "success": true,
  "message": "EDAN localidades sincronizadas correctamente",
  "data": [
    {
      "id_local": "abc123-uuid-001",
      "id_edan_localidad": 48,
      "aplicado": true,
      "conflicto": false,
      "data": {
        "id_edan_localidad": 48,
        "id_edan": null,
        "es_huerfana": true,
        "id_tipo_evento": 5,
        "tipo_evento": { "id_tipo_evento": 5, "nombre": "Granizada" },
        "localidad": "Barrio Nuevo",
        "departamento": { "id": 7, "codigo_ine": "07", "nombre": "Santa Cruz" },
        "provincia": { "id": 701, "codigo_ine": "0701", "nombre": "Andrés Ibáñez" },
        "municipio": { "id": 70101, "codigo_ine": "070101", "nombre": "Santa Cruz de la Sierra" },
        "usuario": { "id_usuario": 30, "usuario": "7051296", "nombre": "Luis Miguel Quenta Herrera" },
        "pendiente_actualizacion": false,
        "pendiente_eliminacion": false,
        "impacto_poblacion": [],
        "danos_vivienda": [],
        "...": "... todas las secciones vacías ..."
      }
    }
  ]
}
```

##### 2. UPDATE exitoso (localidad existente, mismo `id_local`)

```json
{
  "data": [
    {
      "id_local": "abc123-uuid-001",
      "id_edan_localidad": 48,
      "aplicado": true,
      "conflicto": false,
      "data": { "... localidad convergida con todos los campos actualizados ..." }
    }
  ]
}
```

##### 3. Conflicto LWW (`fecha_modificacion` del payload es más antigua que la del servidor)

```json
{
  "data": [
    {
      "id_local": "abc123-uuid-001",
      "id_edan_localidad": 48,
      "aplicado": false,
      "conflicto": true,
      "data": { "... versión vigente del servidor (NO se aplicó el cambio) ..." }
    }
  ]
}
```

El cliente debe adoptar la versión del servidor (reemplazar su copia local).

##### 4. Tombstone (eliminación)

```json
{
  "data": [
    {
      "id_local": "abc123-uuid-001",
      "id_edan_localidad": null,
      "aplicado": true,
      "tombstone": true,
      "data": null
    }
  ]
}
```

El servidor elimina físicamente la localidad. El cliente debe borrarla de su SQLite local.

##### 5. Error por item

```json
{
  "data": [
    {
      "id_local": "abc123-uuid-001",
      "id_edan_localidad": null,
      "sincronizado": false,
      "aplicado": false,
      "error": "Error al procesar la solicitud"
    }
  ]
}
```

El item falló pero los demás continúan procesándose.

#### Comportamiento del servidor

1. Para cada localidad en el array:
   - **`pendiente_eliminacion = true`** → DELETE físico y respuesta tombstone
   - **`id_local` no existe** → INSERT nuevo con `pendiente_actualizacion = false`
   - **`id_local` existe** → comparar `fecha_modificacion`:
     - Payload más nuevo o igual → UPDATE (LWW)
     - Payload más viejo → conflicto (no se aplica)
   - Si la localidad tiene `id_edan` (consolidada), los campos de encabezado (`id_tipo_evento`, `id_departamento`, etc.) se heredan del EDAN padre **solo si el payload no los trae** (no sobreescribe valores existentes)

2. Al actualizar: las secciones 1:N y 1:1 se **reemplazan completamente** (DELETE + INSERT). El cliente debe enviar siempre el set completo de secciones.

3. El servidor establece `fecha_modificacion = NOW()` en cada escritura.

#### Curl example — Crear localidad

```bash
# 1. Login
TOKEN=$(curl -s -X POST 'http://localhost:8000/api/v1/auth/login' \
  -H 'Content-Type: application/json' \
  -d '{"usuario":"7051296","contrasena":"12345678"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['access_token'])")

# 2. Crear localidad via sync
curl -s -X POST 'http://localhost:8000/api/v1/edan/localidades/sync' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "localidades": [{
      "id_local": "mi-uuid-local-001",
      "tipo_localidad": "Municipio",
      "id_tipo_evento": 5,
      "id_departamento": 7,
      "id_provincia": 701,
      "id_municipio": 70101,
      "localidad": "Barrio Ejemplo",
      "fecha_llenado": "2026-08-19",
      "fecha_evento": "2026-08-19",
      "hora_evento": "10:30:00",
      "total_poblacion_afectada": 150,
      "total_familias_afectadas": 30,
      "total_familias_damnificadas": 10,
      "imp_poblacion": true,
      "imp_salud": true,
      "impacto_poblacion": [
        {"rango": "0-5", "fallecidos": 0, "heridos": 2, "desaparecidos": 0}
      ],
      "establecimientos_salud": [
        {"nombre_establecimiento": "Centro Salud", "comunidad": "Barrio", "nivel_atencion": "1er Nivel"}
      ],
      "danos_vivienda": [
        {"comunidad": "Barrio", "dano_parcial": 15, "dano_total": 3}
      ],
      "proteccion": [
        {"grupo": "mujeres_embarazadas", "mujeres": 5, "hombres": 0, "total": 5}
      ]
    }]
  }' | python3 -m json.tool
```

#### Curl example — Editar tipo_evento (cambiar de 5→3)

```bash
curl -s -X POST 'http://localhost:8000/api/v1/edan/localidades/sync' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "localidades": [{
      "id_local": "mi-uuid-local-001",
      "tipo_localidad": "Municipio",
      "id_tipo_evento": 3,
      "id_departamento": 7,
      "id_provincia": 701,
      "id_municipio": 70101,
      "localidad": "Barrio Ejemplo",
      "fecha_modificacion": "2099-12-31T23:59:59"
    }]
  }' | python3 -c "
import sys, json
d = json.load(sys.stdin)
item = d['data'][0]
print(f'aplicado: {item[\"aplicado\"]}')
print(f'id_tipo_evento: {item[\"data\"][\"id_tipo_evento\"]}')
print(f'tipo_evento: {item[\"data\"][\"tipo_evento\"]}')
"
# Salida esperada:
# aplicado: True
# id_tipo_evento: 3
# tipo_evento: {'id_tipo_evento': 3, 'nombre': 'Deslizamiento'}
```

> **Nota:** `fecha_modificacion` debe ser mayor o igual al timestamp del servidor.
> Si el payload envía una fecha anterior, el servidor responde `conflicto: true`
> y NO aplica el cambio (LWW: last-write-wins).

#### Curl example — Eliminar localidad (tombstone)

```bash
curl -s -X POST 'http://localhost:8000/api/v1/edan/localidades/sync' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "localidades": [{
      "id_local": "mi-uuid-local-001",
      "pendiente_eliminacion": true
    }]
  }' | python3 -m json.tool
# Salida: { "aplicado": true, "tombstone": true, "data": null }
```

---

### GET `/api/v1/edan/localidades/sync/pull`

**Pull online → offline.** Devuelve las localidades del usuario autenticado.

- **Auth:** Bearer token (JWT)
- **Roles:** 6 (UGR Municipio), 7 (Responsable Local)

#### Parámetros query

| Param | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `fecha_desde` | string \| null | null | Timestamp ISO. Filtra `fecha_modificacion >= fecha_desde` |
| `skip` | int | 0 | Offset para paginación |
| `limit` | int | 50 | Máximo de resultados por página (1-1000) |

#### Respuesta

```json
{
  "success": true,
  "message": "EDAN localidades para sincronización listadas correctamente",
  "data": [
    {
      "id_edan_localidad": 43,
      "id_local": "1a00d220dd5-659334d060b00",
      "id_edan": null,
      "es_huerfana": true,
      "id_tipo_evento": null,
      "tipo_evento": null,
      "localidad": "Las Lomas",
      "departamento": { "id": 7, "codigo_ine": "07", "nombre": "Santa Cruz" },
      "provincia": { "id": 701, "codigo_ine": "0701", "nombre": "Andrés Ibáñez" },
      "municipio": { "id": 70101, "codigo_ine": "070101", "nombre": "Santa Cruz de la Sierra" },
      "usuario": { "id_usuario": 30, "usuario": "7051296", "nombre": "Luis Miguel Quenta Herrera" },
      "pendiente_actualizacion": false,
      "pendiente_eliminacion": false,
      "...": "... todas las secciones anidadas ..."
    }
  ],
  "total": 1
}
```

El pull devuelve la estructura completa de `_build_localidad` (la misma que el push response).

#### Curl example — Pull incremental

```bash
# Pull de todas las localidades del usuario
curl -s "http://localhost:8000/api/v1/edan/localidades/sync/pull" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# Pull incremental: solo localidades modificadas desde una fecha
curl -s "http://localhost:8000/api/v1/edan/localidades/sync/pull?fecha_desde=2026-08-19T00:00:00" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# Pull con paginación
curl -s "http://localhost:8000/api/v1/edan/localidades/sync/pull?skip=0&limit=10" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

---

### Errores comunes de sincronización

| Situación | Código HTTP | Comportamiento | Solución del cliente |
|-----------|-------------|----------------|---------------------|
| Token inválido/expirado | 401 | Rechazo | Re-login |
| Sin rol adecuado | 403 | Rechazo | Verificar rol del usuario |
| `id_local` duplicado en el payload | 200 | Procesa cada item; el segundo INSERT falla con error en ese item | Evitar duplicados en el mismo lote |
| `fecha_modificacion` más vieja que servidor | 200 | `aplicado: false, conflicto: true` | Adoptar la versión del servidor |
| Campo CHECK inválido (ej: `grupo` en `proteccion`) | 200 | Error en ese item | Usar valores válidos del CHECK constraint |
| Sección con campos requeridos faltantes | 200 | Error en ese item | Verificar campos requeridos de cada sección |
| `pendiente_eliminacion = true` | 200 | DELETE físico + tombstone | Borrar de SQLite local |

---

## 13. Limitaciones conocidas

### Tombstones de localidades (DELETE físico)

Cuando la app móvil elimina una localidad (`pendiente_eliminacion = true`), el servidor realiza un **DELETE físico** de la fila. Esto significa que:

- Otro dispositivo que haga pull posterior **no recibirá** un "tombstone" indicando que la localidad fue eliminada.
- La localidad simplemente desaparecerá del pull (no estará en la respuesta).

**Impacto:** En un escenario multi-dispositivo, si el Dispositivo A elimina una localidad y el Dispositivo B hace pull después, B simplemente no verá la localidad (no sabrá que fue eliminada explícitamente).

**Para la app actual (single-user por dispositivo):** esta limitación no afecta. Cada usuario maneja sus propias localidades en su dispositivo.

### Campos legacy aceptados en EdanCreate

El schema `EdanCreate` aún acepta campos que ya no existen en la tabla `edan.edan` (ej: `estado`, `departamento_nombre`, `tipo_evento_nombre`). Estos campos se ignoran silenciosamente al hacer INSERT/UPDATE.

### `_replace_localidades` en sync push de EDAN

Al hacer push de un EDAN con localidades anidadas, el servidor **elimina** todas las localidades existentes del EDAN que no estén en el payload y reinserta las que sí están. Esto es intencional (replace completo), pero puede ser destructivo si se mezcla con ediciones web-side concurrentes.

---

**Última actualización:** rama `v1.3.0` — fix sync: update_edan con columnas eliminadas, uid assignment, get_edan_por_reporte.
