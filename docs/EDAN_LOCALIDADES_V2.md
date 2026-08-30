# EDAN Localidades — Sync por Secciones (V2)

> **Versión:** v1.5.0 · **Base URL:** `https://<host>` · **Prefijo V2:** `/api/v2`
> **Swagger interactivo:** `http://<host>:8000/docs/v2` · **OpenAPI JSON v2:** `GET http://<host>:8000/openapi.v2.json`
> (no requiere token; `openapi.json` = v1+v2, `openapi.v1.json` = solo v1).
> **Audiencia:** app móvil (Flutter/offline) y web — desarrolladores que sincronizan `edan_localidades`.
> **Relacionado:** [`SINCRONIZACION.md`](SINCRONIZACION.md) (modelo offline-first general) y
> [`SINCRONIZACION_SECCIONES_FOTOS.md`](SINCRONIZACION_SECCIONES_FOTOS.md) (fotos + coordenadas).
> **Documentación Swagger:** `http://<host>:8000/docs/v2`

---

## 1. ¿Qué es una `edan_localidades`?

`edan.edan_localidades` es una **localidad reportada** dentro del flujo EDAN: puede estar **huérfana** (`es_huerfana = true`, aún no consolidada en un EDAN cabecera) o asignada a un EDAN (`id_edan`). Cada localidad tiene:

- **Cabecera** (1 por localidad): geografía, evento, totales, banderas de impacto y estado.
- **Secciones (hasta 14):** daños, servicios y necesidades por área.

### Cabecera — campos principales

| Campo | Uso |
|---|---|
| `id_local` | UUID offline generado por el cliente (app/web). Clave de dedupe. Se genera UNA vez y se reusa. |
| `localidad`, `id_municipio`, `id_departamento`, `id_provincia` | Identificación y geografía. |
| `id_tipo_evento`, `id_tipo_localidad` | Catálogos. |
| `total_poblacion_afectada`, `total_familias_afectadas`, `total_familias_damnificadas` | Totales. |
| `imp_*` (poblacion, salud, infraestructura, servicios, educacion, vivienda, agropecuario, proteccion, necesidades) | Banderas de impacto (bool) — indican qué secciones aplican. |
| `id_edan_localidad_estado` | Estado. `2` = Enviado (visible para el UGR con data fresca). Solo se edita en web si es borrador (`1`). |
| `pendiente_actualizacion`, `pendiente_eliminacion` | Flags de sync interno (se mantienen solos). |

### Secciones — tabla

| # | Sección | Relación | Endpoint V2 | Detalles |
|---|---|---|---|---|
| 1 | Impacto en población | 1:N | `impacto-poblacion` | `rango`, `fallecidos`, `heridos`, `desaparecidos` |
| 2 | Salud — establecimientos | 1:N | `salud-establecimientos` | `nombre_establecimiento`, `nivel_atencion`, afectados por rol |
| 3 | Daños viales | 1:N | `danos-viales` | `via`, `puente`, `tramo`, `km_danio` |
| 4 | Daños a infraestructura pública | 1:N | `danos-infra-publica` | `comunidad`, `tipo_estructura` |
| 5 | Servicios básicos | 1:N | `servicios-basicos` | `tipo` **valores admitidos** (ver tabla abajo) |
| 6 | Unidades educativas | 1:N | `unidades-educativas` | `nombre_establecimiento`, estudiantes/profesores/administrativos |
| 7 | Daños a vivienda | 1:N | `danos-vivienda` | `comunidad`, `dano_parcial`, `dano_total` |
| 8 | Daños a agricultura | 1:N | `danos-agricultura` | `tipo_cultivo`, `id_cultivo` (FK catálogo), hectáreas |
| 9 | Daños pecuarios | 1:N | `danos-pecuarios` | `especie`, `raza`, `id_especie` (FK catálogo), animales | 
| 10 | Infraestructura productiva | 1:N | `infra-productiva` | `tipo` (ej. Qollqa, Apoyo, Almacén) |
| 11 | Protección (grupos vulnerables) | 1:N | `proteccion` | `id_grupo_vulnerable_catalogo` (**requerido**, FK catálogo) |
| 12 | Primera respuesta | 1:1 | `primera-respuesta` | `busqueda`, `salvamento`, `evacuacion` |
| 13 | Necesidades de salud | 1:1 | `necesidad-salud` | `numero_personas`, `otras_necesidades` |
| 14 | Necesidades humanitarias | 1:1 | `necesidad-humanitaria` | 9 necesidades (alimentos, refugio, ropa…) c/u con su `obs_*` |

**Secciones con FOTOS + GPS:** Daños viales, infra pública, vivienda, agricultura, pecuarios, salud, servicios básicos, unidades educativas, infra productiva. Cada una tiene **dos vías** de foto:
- **Vía A — `/con-foto` (multipart):** sube el archivo físico + campos en una llamada (**1 fila**). `file` es opcional.
- **Vía B — JSON de grupo (`POST …/<seccion>`):** la foto viaja como **path** en `fotografia` (+ `coordenada_lat/lon`) por cada fila; permite **grupos mixtos** (algunas filas con foto, otras sin) en una sola llamada.

Regla foto↔GPS: **foto exige coordenadas**; sin foto pueden ir sin coordenadas. Detalles y ejemplos (crear/editar/mezclar) en [`DESPLIEGUE_API_V2.md §6`](DESPLIEGUE_API_V2.md#6-secciones-con-foto).

---

## 2. Reglas del sync V2 (resumen)

1. **Orden:** primero la **cabecera** (`POST …/cabecera`), luego **cada sección** con su propio POST. No es necesario enviar todo: se sincroniza solo el cambio detectado.
2. **No destructivo:** solo se actualizan los campos que vienen en el payload. Los ausentes (`null`/omitidos) no se tocan en un UPDATE y toman el `DEFAULT` de la BD (`0`, `''`, `false`) en un INSERT.
3. **`id_seccion`:** se genera **en el origen de los datos (app o web)**, con las mismas características (UUID). Se genera UNA vez al crear el ítem y se REUSA en cada edición. El servidor solo lo usa como clave de UPSERT, nunca lo genera.
4. **Grupo por sección:** un solo POST puede llevar la sección completa como **objeto único o array**. Cada fila con su `id_seccion`.
5. **Aislamiento de errores:** si una fila del grupo falla (FK inválida, CHECK, obligatorio), las demás se guardan y la respuesta trae `errors[]` con el `index` de la fila y el motivo.
6. **1:1 nunca duplica:** `primera-respuesta`, `necesidad-salud`, `necesidad-humanitaria` hacen UPSERT por `id_seccion` con fallback por `id_edan_localidad` cuando no se envía `id_seccion`.
7. **Roles de escritura:** 6 (UGR municipio) y 7 (Responsable local). La lectura no exige rol local (basta autenticación EDAN).
8. **v1 intacta:** las APIs V1 con fotografía siguen funcionando; V2 es paralela.
9. **Modo offline (paralelo):** los endpoints de secciones aceptan `id_local` (UUID) en vez de `id_edan_localidad` (int). El servidor resuelve automáticamente. Si la cabecera aún no existe, responde `400` con `X-Retry-After: 2` para reintento automático.

### Modo Online vs Offline

| Modo | Cabecera | Secciones | Ejemplo path |
|---|---|---|---|
| **Online** | `POST /cabecera {id_local}` ← `id_edan_localidad` | `POST /localidades/{id_edan}/danos-viales {id_seccion}` | `/api/v2/edan/localidades/314/danos-viales` |
| **Offline (paralelo)** | `POST /cabecera {id_local}` ← mismo UUID | `POST /localidades/{id_local}/danos-viales {id_seccion}` | `/api/v2/edan/localidades/uuid-abc/danos-viales` |

**Ventaja del modo paralelo:** el móvil puede enviar cabecera + secciones al mismo tiempo (sin esperar respuesta). Si la sección llega antes, el servidor espera la cabecera (timeout 5s) y hace UPSERT.

---

## 3. Autenticación

```bash
# Obtener token (JWT)
curl -s -X POST $BASE/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"usuario":"7051296","contrasena":"12345678"}'
# → { "data": { "access_token": "eyJhbGci..." } }
```

```bash
# Usar en cada llamada:
H='Authorization: Bearer <token>'
CT='Content-Type: application/json'
```

---

## 4. Flujo paso a paso con ejemplos

Los `id_seccion` de los ejemplos (`imp_01`, `ag_001`, `pr_001`, …) representan UUIDs generados por el cliente; úsalo como patrón, no como valor literal.

### Paso 1 — Cabecera (SIEMPRE primero)

`POST /api/v2/edan/localidades/cabecera` crea o actualiza **solo la cabecera** usando `id_local` como dedupe. Devuelve el `id_edan_localidad` para las secciones.

```bash
curl -s -X POST $BASE/api/v2/edan/localidades/cabecera \
  -H "$H" -H "$CT" \
  -d '{
        "id_local": "3b2f9c1e-8a67-4d2e-9f01-c4d8a3b2e7f0",
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
        "imp_agropecuario": true
      }'
```

```json
{
  "success": true,
  "message": "Cabecera guardada correctamente",
  "data": {
    "id_edan_localidad": 312,
    "id_local": "3b2f9c1e-8a67-4d2e-9f01-c4d8a3b2e7f0",
    "localidad": "Comunidad Nuevo Amanecer",
    "es_huerfana": true,
    "pendiente_actualizacion": false
  }
}
```

> Re-enviar la **misma** `id_local` actualiza la cabecera sin duplicar la localidad.

### Paso 2 — Sección 1:N, grupo en array

`POST /api/v2/edan/localidades/{id_edan_localidad}/impacto-poblacion`

```bash
curl -s -X POST $BASE/api/v2/edan/localidades/312/impacto-poblacion \
  -H "$H" -H "$CT" \
  -d '[
        { "id_seccion": "imp_01", "rango": "0 a 5 anos",  "fallecidos": 1, "heridos": 10 },
        { "id_seccion": "imp_02", "rango": "6 a 12 anos", "fallecidos": 0, "heridos": 5  },
        { "id_seccion": "imp_03", "rango": "adultos",     "fallecidos": 3, "heridos": 20 }
      ]'
```

```json
{
  "success": true,
  "message": "Impacto en población sincronizados correctamente",
  "data": {
    "results": [
      { "id_impacto_poblacion": 187, "id_seccion": "imp_01" },
      { "id_impacto_poblacion": 188, "id_seccion": "imp_02" },
      { "id_impacto_poblacion": 189, "id_seccion": "imp_03" }
    ],
    "errors": []
  }
}
```

### Paso 3 — Sección 1:N, objeto único y casos con catálogos

Daños a agricultura (objeto único; `id_cultivo` es FK del catálogo `shared.cultivo`):

```bash
curl -s -X POST $BASE/api/v2/edan/localidades/312/danos-agricultura \
  -H "$H" -H "$CT" \
  -d '{ "id_seccion": "ag_001", "tipo_cultivo": "Arroz", "hectareas_afectadas": 12, "id_cultivo": 1 }'
```

Servicios básicos — `tipo` **solo admite** `energia_electrica`, `agua_potable`, `alcantarillado`, `gas_domiciliario`, `telecomunicaciones` (restricción CHECK):

```bash
curl -s -X POST $BASE/api/v2/edan/localidades/312/servicios-basicos \
  -H "$H" -H "$CT" \
  -d '{ "id_seccion": "sb_001", "tipo": "energia_electrica", "dano_parcial": true }'
```

Protección — `id_grupo_vulnerable_catalogo` es **requerido** (FK catálogo de grupos vulnerables):

```bash
curl -s -X POST $BASE/api/v2/edan/localidades/312/proteccion \
  -H "$H" -H "$CT" \
  -d '{ "id_seccion": "pr_001", "id_grupo_vulnerable_catalogo": 1, "mujeres": 4, "hombres": 6 }'
```

### Paso 4 — Secciones 1:1 (siempre un solo objeto)

```bash
# Con id_seccion (UPSERT por id_seccion)
curl -s -X POST $BASE/api/v2/edan/localidades/312/primera-respuesta \
  -H "$H" -H "$CT" \
  -d '{ "id_seccion": "prr_001", "busqueda": true, "evacuacion": true }'

# Sin id_seccion → fallback por id_edan_localidad (crea o actualiza la fila 1:1)
curl -s -X POST $BASE/api/v2/edan/localidades/312/necesidad-salud \
  -H "$H" -H "$CT" \
  -d '{ "numero_personas": 40, "otras_necesidades": "medicinas" }'

curl -s -X POST $BASE/api/v2/edan/localidades/312/necesidad-humanitaria \
  -H "$H" -H "$CT" \
  -d '{ "alimentos": true, "ropa_cama": true, "obs_alimentos": "racion diaria" }'
```

### Paso 5 — Editar un ítem (mismo `id_seccion`, solo los campos que cambian)

```bash
curl -s -X POST $BASE/api/v2/edan/localidades/312/impacto-poblacion \
  -H "$H" -H "$CT" \
  -d '{ "id_seccion": "imp_02", "heridos": 50 }'
# → heridos=50; fallecidos/desaparecidos del ítem se preservan
```

### Paso 6 — Eliminar ítem o vaciar sección

```bash
# Un ítem por id_seccion
curl -s -X DELETE $BASE/api/v2/edan/localidades/312/impacto-poblacion/seccion/imp_02 -H "$H"

# Toda la sección (1:N y 1:1)
curl -s -X DELETE $BASE/api/v2/edan/localidades/312/danos-agricultura -H "$H"
```

### Paso 7 — Verificar y mapear el `id_local`

```bash
curl -s "$BASE/api/v2/edan/localidades/por-id-local/3b2f9c1e-8a67-4d2e-9f01-c4d8a3b2e7f0" -H "$H"
```

```json
{
  "success": true,
  "data": {
    "id_edan_localidad": 312,
    "localidad": "Comunidad Nuevo Amanecer",
    "pendiente_actualizacion": true,
    "fecha_modificacion": "2026-08-28T14:39:14"
  }
}
```

`404` si el `id_local` no existe. `pendiente_actualizacion: true` indica cambios locales pendientes de consolidar.

---

## 5. Listado, resumen y estados — para la web

La web primero refresca la **lista ligera + badges de estado** y, al entrar a un ítem, carga **todo el contenido con la API de detalle de ese ítem**.

> ⚠️ **Dos catálogos de estado distintos,** no confundir:
>
> | Entidad | Catálogo | Endpoints resumen/estados | ID en respuestas |
> |---|---|---|---|
> | **Localidades** | `edan_localidades_estado` (1 Borrador · 6 En revisión UGR · 2 Enviado UGR · 3 Aprobado UGR · 4 Rechazado UGR · 5 Aprobado Ajuste UGR) | `…/localidades/mis-resumen`, `…/localidades/mis-estados` | `id_edan_localidad_estado` |
> | **EDAN cabecera** | `estado_edan` (1 Borrador · 2 Enviado · 3 Aprobado · 4 Rechazado · 5 Aprobado ajuste · 6 En revisión) | `…/edan/mis-resumen`, `…/edan/mis-estados` | `id_estado` |

Ambos respetan el mismo scope: el usuario ve **sus** registros (`id_usuario`); un rol 1/9 puede consultar otros usuarios con `?id_usuario=`.

### 5.1 Localidades — endpoints

| Endpoint | Uso | Peso |
|---|---|---|
| `GET …/localidades/mis-resumen` | Totales + `por_estado[]` (para badges) | Ligero |
| `GET …/localidades/mis-estados` | Lista ligera (cabecera + estado, **sin secciones**) | Muy ligero |
| `GET …/localidades/mis-reportes` | Lista **completa** (todas las secciones anidadas) | Pesado |
| `GET …/localidades/{id_localidad}` | **UNA** localidad completa (detalle al entrar al ítem) | Acepta `id_local` (UUID) o `id_edan_localidad` (int) |

```bash
# Badges de estado (refresh rápido)
curl -s "$BASE/api/v2/edan/localidades/mis-resumen" -H "$H"
curl -s "$BASE/api/v2/edan/localidades/mis-estados?limit=200" -H "$H"
```

```json
// mis-resumen → data.por_estado
{
  "success": true,
  "data": {
    "total_localidades": 4,
    "total_consolidadas": 0,
    "total_huerfanas": 4,
    "por_estado": [
      { "id_edan_localidad_estado": 1, "estado": "Borrador",        "cantidad": 2 },
      { "id_edan_localidad_estado": 6, "estado": "En revision UGR", "cantidad": 1 },
      { "id_edan_localidad_estado": 2, "estado": "Enviado UGR",     "cantidad": 1 }
    ]
  }
}
```

```bash
# Entrar a un ítem → cargar todo el contenido de ESA localidad
# (misma estructura que mis-reportes, pero de un solo ítem)
curl -s "$BASE/api/v2/edan/localidades/292" -H "$H"
curl -s "$BASE/api/v2/edan/localidades/1a042b1eac3-65a0486fd0d19" -H "$H"   # o por id_local
```

### 5.2 EDAN cabecera — endpoints

| Endpoint | Uso |
|---|---|
| `GET …/edan/mis-resumen` | Totales + `por_estado[]` (**estado_edan**) + `por_tipo_evento[]` |
| `GET …/edan/mis-estados` | Lista ligera de EDAN (cabecera + estado, **sin localidades** anidadas) |
| `GET …/edan/{id}` | EDAN completo (cabecera + localidades) al entrar al ítem |

```bash
# Badges de estado del EDAN (id_estado = estado_edan)
curl -s "$BASE/api/v2/edan/mis-resumen" -H "$H"
curl -s "$BASE/api/v2/edan/mis-estados?limit=200" -H "$H"

# Detalle completo al abrir el EDAN
curl -s "$BASE/api/v2/edan/45?modo=detallado" -H "$H"
```

```json
// mis-resumen edan → data
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

> **Flujo resumido:** login → `mis-resumen` (badges) + `mis-estados` (lista ligera con `id` + estado) → clic en ítem → `GET /localidades/{id}` o `/edan/{id}` carga el contenido → la edición se hace con los endpoints de **sección/cabecera** (nunca con el JSON anidado completo).

#### 5.3 Reportes agregados (solo totales)

Para "sacar un EDAN con solo los totales" usa los **reportes** (sin filas, agregados con filtros) o el **modo compacto** de un EDAN individual:

| Endpoint | Qué da |
|---|---|
| `GET …/edan/reportes/resumen` | `totales` + `por_estado[]` + `por_tipo_evento[]` (con filtros) |
| `GET …/edan/reportes/geografico` | EDANs por departamento/provincia/municipio |
| `GET …/edan/reportes/agricultura` | hectáreas por cultivo |
| `GET …/edan/reportes/pecuario` | animales por especie |
| `GET …/edan/reportes/localidades` | localidades consolidadas, paginado |
| `GET …/edan/{id}?modo=compacto` | **un** EDAN con `resumen_localidades` + `sumatorias` (no arrastra filas) |

Filtros (igual que v1): `q`, `id_departamento`, `id_provincia`, `id_municipio`, `id_tipo_evento`, `id_estado`, `estado`, `id_usuario_ugr`, `fecha_evento_desde/hasta`, `fecha_creacion_desde/hasta`, flags `pendiente_*`, `con_foto`, `sin_foto`, `imp_*`, `tiene_agricultura`, `tiene_pecuario`.

**Scope:** rol 1/9 ve todo; rol 2-8 ve solo sus EDAN (`id_usuario_ugr` propio) salvo filtro explícito. Ejemplos en [`DESPLIEGUE_API_V2.md §8.3`](DESPLIEGUE_API_V2.md#83-reportes-de-solo-totales-agregados-con-filtros).

---

## 6. Referencia de endpoints V2

| Recurso | GET | POST | DELETE |
|---|---|---|---|
| `localidades/cabecera` | — | crear/actualizar cabecera | — |
| `localidades/por-id-local/{id_local}` | mapear id_local | — | — |
| `localidades/{id_localidad}` | **localidad completa** | — | — |
| `localidades/mis-reportes` | listado completo | — | — |
| `localidades/mis-resumen` | totales + por estado | — | — |
| `localidades/mis-estados` | lista ligera (sin secciones) | — | — |
| `impacto-poblacion` | listar | grupo (objeto o array) | `…/seccion/{id_seccion}` o vaciar |
| `salud-establecimientos` | listar | grupo | `…/seccion/{id_seccion}` o vaciar |
| `danos-viales` | listar | grupo | `…/seccion/{id_seccion}` o vaciar |
| `danos-infra-publica` | listar | grupo | `…/seccion/{id_seccion}` o vaciar |
| `servicios-basicos` | listar | grupo | `…/seccion/{id_seccion}` o vaciar |
| `unidades-educativas` | listar | grupo | `…/seccion/{id_seccion}` o vaciar |
| `danos-vivienda` | listar | grupo | `…/seccion/{id_seccion}` o vaciar |
| `danos-agricultura` | listar | grupo | `…/seccion/{id_seccion}` o vaciar |
| `danos-pecuarios` | listar | grupo | `…/seccion/{id_seccion}` o vaciar |
| `infra-productiva` | listar | grupo | `…/seccion/{id_seccion}` o vaciar |
| `proteccion` | listar | grupo | `…/seccion/{id_seccion}` o vaciar |
| `primera-respuesta` (1:1) | obtener | objeto único | eliminar |
| `necesidad-salud` (1:1) | obtener | objeto único | eliminar |
| `necesidad-humanitaria` (1:1) | obtener | objeto único | eliminar |
| EDAN: `edan/mis-resumen` | totales + por estado_edan | — | — |
| EDAN: `edan/mis-estados` | lista ligera de EDAN | — | — |
| EDAN: `edan/{id}` | EDAN completo | — | — |

**Convención de rutas:** todos los grupos V2 son `POST /api/v2/edan/localidades/{id_edan_localidad}/{seccion}`.

---

## 7. Errores (aislados por fila)

Un grupo donde la fila `0` tiene `id_grupo_vulnerable_catalogo` inexistente devuelve `201` (finalizó) con la fila aparte:

```json
{
  "success": true,
  "message": "Grupos vulnerables (protección) sincronizados correctamente",
  "data": {
    "results": [ { "id_grupo_vulnerable": 42, "id_seccion": "pr_002" } ],
    "errors": [
      { "index": 0, "detail": "El registro referenciado no existe (violación de clave foránea)" }
    ]
  }
}
```

Si **ninguna** fila se guardó, la respuesta es `400` con `errors[]` por índice. Motivos típicos:

| Motivo | Cuándo ocurre |
|---|---|
| `El registro referenciado no existe (violación de clave foránea)` | FK inválida: `id_cultivo`, `id_especie`, `id_grupo_vulnerable_catalogo`, `id_municipio`… |
| `Valor no permitido (restricción CHECK)` | `tipo` de servicios básicos fuera del catálogo admitido |
| `Falta un campo obligatorio` | Columna `NOT NULL` sin default y sin valor |
| `Ya existe un registro con el mismo valor (violación de unicidad)` | Duplicado de clave |

---

## 8. Impacto en Población: `id_grupo_etario` (cambio v1.5.0)

La sección `impacto_poblacion` ahora usa `id_grupo_etario` (FK al catálogo `edan.grupo_etario`) en lugar del campo `rango` (string libre, eliminado de la BD).

### Catálogo `grupo_etario`

| id | código | nombre |
|---|---|---|
| 1 | ninas_ninos_0_5 | Niño (a) 0-5 años |
| 2 | escolar_6_18 | Escolar de 6-18 años |
| 3 | adulto_19_60 | Adulto de 19-60 años |
| 4 | adulto_mayor_60 | Adulto mayor de 60 años adelante |

### Envío v2 (recomendado)

```json
{
  "id_seccion": "im_1693012345_abc123",
  "id_grupo_etario": 3,
  "fallecidos": 2,
  "heridos": 8,
  "desaparecidos": 0
}
```

### Envío v1 (compatibilidad)

Si la app aún envía `rango` como string, la API lo resuelve automáticamente por nombre:

```json
{
  "id_seccion": "im_1693012345_abc123",
  "rango": "Adulto de 19-60 años",
  "fallecidos": 2,
  "heridos": 8
}
```

> **Nota:** si el string no coincide con ningún nombre del catálogo, se retorna error 400.

### Respuesta (lectura)

La respuesta **siempre** incluye:

```json
{
  "id_grupo_etario": 3,
  "grupo_etario": {
    "id": 3,
    "codigo": "adulto_19_60",
    "nombre": "Adulto de 19-60 años",
    "orden": 3,
    "activo": true
  },
  "rango": "Adulto de 19-60 años",
  "fallecidos": 2,
  "heridos": 8
}
```

- `id_grupo_etario`: fuente de verdad (usar este en escritura).
- `grupo_etario`: objeto anidado con datos del catálogo.
- `rango`: calculado (nombre del catálogo), mantenido por compatibilidad v1. **No usar en escritura.**

---

## 9. Swagger

En `/docs`, secciones V2 agrupadas como **tercer nivel** bajo `EDAN_LOCALIDADES` (tags `EDAN_LOCALIDADES > <Seccion>` vía `swagger-ui-plugin-hierarchical-tags`). Cada endpoint documenta schemas, errores y roles.

---

## 9. Checklist para el cliente

- [ ] Generar `id_local` una sola vez (UUID) y guardarlo.
- [ ] Generar cada `id_seccion` una sola vez por ítem y reusarlo al editar.
- [ ] Enviar **cabecera primero** y usar el `id_edan_localidad` devuelto.
- [ ] Enviar cada sección en su propio POST (objeto único o array), no el JSON completo de localidad.
- [ ] Los campos que no cambian: **no enviarlos** (o `null`) → no se alteran.
- [ ] Para borrar un ítem: `DELETE …/{seccion}/seccion/{id_seccion}`.
- [ ] Tras el POST de secciones, `pendiente_actualizacion` queda `true` (camino normal hasta consolidar).
- [ ] **Fotos:** subir con `POST /upload` → usar el `path` en `fotografia` (Vía B) para grupos mixtos; usar `/con-foto` (Vía A) para archivo+datos en una llamada. Foto siempre con `coordenada_lat/lon`.
- [ ] No usar las v1/foto para los datos sin foto; las v2 no resuelven foto.