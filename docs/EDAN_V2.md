# EDAN — API v2 (grupo consolidado)

> Documentación exclusiva del endpoint `/api/v2/edan/*` (tabla `edan.edan`).
> Fecha: 2026-09-08. Basada en datos reales de la base `db_sinagersat`.

## Modelo de datos

- **`edan.edan_localidades` es la fuente de verdad**: cada registro es un
  formulario EDAN por localidad (huérfanas cuando `id_edan IS NULL`).
- **`edan.edan` es SOLO el grupo consolidado**: se crea única y exclusivamente
  con `POST /api/v2/edan/consolidar` (o `/consolidar/auto`) a partir de
  localidades aprobadas del mismo municipio/tipo de evento. No existe
  creación manual de EDAN.
- Los datos detallados (14 secciones) viven en las tablas
  `edan.edan_localidades_*`; la cabecera `edan.edan` guarda un snapshot de
  totales.

Reversa de la consolidación:

- `PUT /api/v2/edan/{id}/deshacer` — revierte todo el grupo (las localidades
  quedan huérfanas).
- `PUT /api/v2/edan/localidades/{id_localidad}/desconsolidar` — saca UNA
  localidad del grupo (deja las demás).

## Endpoints activos

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/v2/edan/` | Lista de EDAN (con filtros) |
| GET | `/api/v2/edan/{id}` | EDAN completo (cabecera + secciones + `resumen_secciones`) |
| PUT | `/api/v2/edan/{id}` | Actualizar cabecera (solo columnas reales de `edan.edan`) |
| PUT | `/api/v2/edan/{id}/estado` | Cambiar estado del EDAN (`estado_edan`) |
| DELETE | `/api/v2/edan/{id}?permanente=false` | Baja lógica (sync) |
| GET | `/api/v2/edan/mis-resumen` | Totales de mis EDAN + `por_estado` |
| GET | `/api/v2/edan/mis-estados` | Lista ligera (solo estado) para badges |
| GET | `/api/v2/edan/mis-reportes` | Mis EDAN con localidades (raíz) |
| GET | `/api/v2/edan/reportes/resumen` | Totales agregados de localidades |
| GET | `/api/v2/edan/reportes/geografico` | Agrupado por depto/prov/municipio |
| GET | `/api/v2/edan/reportes/agricultura` | Daños por cultivo |
| GET | `/api/v2/edan/reportes/pecuario` | Daños por especie |
| GET | `/api/v2/edan/consolidar/pendientes` | Localidades listas para consolidar |
| POST | `/api/v2/edan/consolidar` | Consolidar localidades en un EDAN |
| POST | `/api/v2/edan/consolidar/auto` | Consolidación automática |
| PUT | `/api/v2/edan/localidades/{id}/estado` | Estado de localidad (UGR) |

Retirados (mayo–sep 2026): `POST /api/v2/edan/` (crear EDAN manual),
`GET /api/v2/edan/reportes/localidades` (lo reemplaza
`GET /api/v2/edan/localidades/filtrar`),
`GET /api/v2/edan/reportes/mis-resumen` (duplicado de `/mis-resumen`).

> `GET /filtrar` y todo `/api/v2/edan/localidades/*` son módulo aparte
> (`router_v2.py`) y no se describen aquí.

### Orden de rutas (importante)

FastAPI resuelve las rutas en el orden en que se declaran. `GET /{id}`
(`id: int`) captura cualquier segmento y, si no es entero, devuelve
`422 Input should be a valid integer`. Por eso TODAS las rutas estáticas del
grupo EDAN (`/mis-resumen`, `/mis-estados`, `/mis-reportes`, `/reportes/*`,
`/consolidar/pendientes`) se declaran **antes** de `GET /{id}`.
`/reportes/mis-reportes` y `/mis-reportes` son equivalentes (misma lógica:
`service.get_mis_edans`); la variante raíz existe para no ser atrapada por
`GET /{id}`.

## Actualizar cabecera EDAN — `PUT /api/v2/edan/{id}`

El body acepta **solo las 17 columnas reales de `edan.edan`** que escribe
`service.update_edan`. PUT parcial: basta enviar los campos a cambiar
(`model_dump(exclude_unset=True)`); un body vacío `{}` retorna el EDAN sin
escribir nada.

NO acepta estos campos (no son columnas de la tabla, se eliminaron del
schema `EdanUpdateV2` en 2026-09-08):

- `estado` (string) → el estado va por `id_estado` (cambiar con
  `PUT /api/v2/edan/{id}/estado`, body `{"id_estado": N}`).
- `responsable` {nombre, cargo, fono, correo} → el contacto del alcalde se
  **lee** por JOIN con `usuarios.usuario`; no se escribe.
- `fecha_modificacion` → la genera el servicio con `NOW()` en cada UPDATE.

> **Estricto desde 2026-09-08:** `EdanUpdateV2` usa `extra="forbid"`. Cualquier
> campo desconocido (`nombre_alcalde`, `fono_alcalde`, `responsable`, typo del
> campo correcto) devuelve **422** ("Extra inputs are not permitted") — no se
> ignora silenciosamente.

### Matriz de roles del `PUT /api/v2/edan/{id}`

| Rol | Puede modificar |
|---|---|
| 1 (superadmin), 2 (admin), 3 (VIDECI Regional), 4 (UGR Sectores), 5 (DGR), 9 (VIDECI Departamental) | Todas las 17 columnas |
| 6 (UGR Municipio), 7 (Responsable Local) | **Solo `id_usuario_alcalde`** — asignar el alcalde. Cualquier otro campo → **403** |
| 8 (Alcalde) | Sin acceso (403, permiso de módulo) |

`id_usuario_alcalde` debe ser un `usuarios.usuario` con **rol 8 (Alcalde)**;
si el usuario no existe → 404, si tiene otro rol → **400**.

### Campos aceptados (17)

`id_local`, `codigo_edan`, `id_usuario_ugr`, `id_usuario_alcalde`,
`id_departamento`, `id_provincia`, `id_municipio`, `id_tipo_evento`,
`fecha_llenado` (date), `fecha_evento` (date), `hora_evento` (time),
`total_poblacion_afectada`, `total_familias_afectadas`,
`total_familias_damnificadas` (int), `id_estado`,
`pendiente_eliminacion`, `pendiente_actualizacion` (bool).

### Ejemplos reales

Asignar el alcalde — hecho por un **UGR Municipio (rol 6)** sobre un EDAN ya
consolidado (EDAN 76, `070101/2026/002`; el usuario 25 es rol Alcalde):

```json
{
  "id_usuario_alcalde": 25
}
```

- `id_usuario_alcalde` se guarda en `edan.edan`; el desglose `responsable_*`
  (nombre, cargo, fono, correo) sale del JOIN `usuarios.usuario` en la
  respuesta `GET /api/v2/edan/76`.
- Validación (rol 6 probado en 2026-09-08): `id_usuario_alcalde: 25` → `200`;
  `id_usuario_alcalde: 28` (usuario rol 6, no alcalde) →
  `400 {"detail": "id_usuario_alcalde debe ser un usuario con rol Alcalde (8)"}`.

Intentos prohibidos para rol 6 (verificados):

```text
PUT /api/v2/edan/76  {"id_estado": 2}     -> 403 "Rol 6 solo puede modificar id_usuario_alcalde. Campos no permitidos: id_estado"
PUT /api/v2/edan/76  {"nombre_alcalde": "X"}  -> 422 (extra_forbidden)
PUT /api/v2/edan/76  {"id_usuario_alcalde": "abc"} -> 422 (debe ser int)
```

Ajustar localización y un total (rol 1-5 / 9; si se manda `id_municipio` y
faltan depto/provincia, el servicio los deduce de `shared.municipio`):

```json
{
  "id_municipio": 70101,
  "total_poblacion_afectada": 1200
}
```

Respuesta real de `PUT {}` (no-op → `GET /api/v2/edan/76`), tras actualizar:

```json
{
  "success": true,
  "message": "EDAN actualizado correctamente",
  "data": {
    "id_edan": 76,
    "codigo_edan": "070101/2026/002",
    "id_departamento": 7,
    "id_provincia": 701,
    "id_municipio": 70101,
    "fecha_llenado": "2026-08-27",
    "fecha_evento": "2026-08-27",
    "hora_evento": "07:00:00",
    "total_poblacion_afectada": 100,
    "total_familias_afectadas": 5,
    "total_familias_damnificadas": 2
  }
}
```

> En `openapi.json`: el PUT v2 usa el componente `EdanUpdateV2`; el PUT v1
> (`/api/v1/edan/{id}`) sigue usando `EdanUpdate` (con `estado`/`responsable`)
> y NO se modifica en esta documentación.

### Usuarios en la respuesta de todos los GET de EDAN (2026-09-08)

Todo GET de EDAN devuelve los ids planos **y** el usuario anidado **completo**
(9 campos), tanto para el UGR (`usuario_ugr`) como para el alcalde
(`usuario_alcalde`). Ejemplo real del EDAN 76:

```json
{
  "id_usuario_ugr": 28,
  "usuario_ugr": {
    "id_usuario": 28,
    "usuario": "UGRSCZ",
    "nombre": "Andres Calamardo",
    "carnet": "12345678",
    "celular": "67023648",
    "correo": null,
    "cargo": "UGR",
    "id_rol": 6,
    "activo": true
  },
  "id_usuario_alcalde": 26,
  "usuario_alcalde": {
    "id_usuario": 26,
    "usuario": "AlcaldeSCZ",
    "nombre": "Mamen Saavedra",
    "carnet": "7894561",
    "celular": "78851166",
    "correo": null,
    "cargo": null,
    "id_rol": 8,
    "activo": true
  }
}
```

Si no hay alcalde asignado (`id_usuario_alcalde` null), `usuario_alcalde` es
`null`. Este formato aplica a `GET /`, `GET /{id}`, `/mis-reportes`,
`/reportes/mis-reportes` y a las respuestas que reusan el builder en v1. El
resto de campos de la cabecera no cambia.

## Reportes agregados (ABIERTOS)

Los 4 reportes agregan sobre **todas las localidades** (huérfanas +
consolidadas, tabla `edan.edan_localidades`). No aplican scope por rol y el
filtro `id_usuario_ugr` se ignora. Filtros soportados (query params):
`id_departamento`, `id_provincia`, `id_municipio`, `id_tipo_evento`,
`id_estado`/`estado` (estado **de localidad**), `fecha_llenado_*`,
`fecha_evento_*`, `imp_*`, `tiene_agricultura`, `tiene_pecuario`.

### `GET /reportes/resumen` — respuesta real

```json
{
  "success": true,
  "message": "Resumen de localidades generado correctamente",
  "data": {
    "totales": {
      "total_localidades": 39,
      "total_huerfanas": 38,
      "total_consolidadas": 1,
      "total_poblacion_afectada": 23592.0,
      "total_familias_afectadas": 5325.0,
      "total_familias_damnificadas": 1689.0
    },
    "por_estado": [
      {"id_edan_localidad_estado": 2, "estado": "Enviado UGR", "cantidad": 17},
      {"id_edan_localidad_estado": 6, "estado": "En revision UGR", "cantidad": 8},
      {"id_edan_localidad_estado": null, "estado": null, "cantidad": 7},
      {"id_edan_localidad_estado": 1, "estado": "Borrador", "cantidad": 4},
      {"id_edan_localidad_estado": 3, "estado": "Aprobado UGR", "cantidad": 3}
    ],
    "por_tipo_evento": [
      {"id_tipo_evento": 1, "tipo_evento": "Inundación", "cantidad": 12},
      {"id_tipo_evento": 5, "tipo_evento": "Granizada", "cantidad": 10},
      {"id_tipo_evento": 7, "tipo_evento": "Incendios", "cantidad": 5},
      {"id_tipo_evento": 4, "tipo_evento": "Helada", "cantidad": 4},
      {"id_tipo_evento": null, "tipo_evento": "Sin tipo", "cantidad": 2},
      {"id_tipo_evento": 2, "tipo_evento": "Riada", "cantidad": 2},
      {"id_tipo_evento": 6, "tipo_evento": "Sequía", "cantidad": 2},
      {"id_tipo_evento": 22, "tipo_evento": "Fallas estructurales", "cantidad": 1},
      {"id_tipo_evento": 8, "tipo_evento": "Tormenta", "cantidad": 1}
    ]
  }
}
```

### `GET /reportes/geografico` — primera fila real

```json
{
  "success": true,
  "message": "Reporte geográfico generado correctamente",
  "data": [
    {
      "id_departamento": 2,
      "departamento": "La Paz",
      "id_provincia": 201,
      "provincia": "Murillo",
      "id_municipio": 20101,
      "municipio": "Nuestra Señora de La Paz",
      "total_localidades": 2,
      "total_huerfanas": 2,
      "total_consolidadas": 0,
      "poblacion_afectada": 2250.0,
      "familias_afectadas": 450.0,
      "familias_damnificadas": 34.0
    }
  ],
  "total": 10
}
```

### `GET /reportes/agricultura` — respuesta real

```json
{
  "success": true,
  "message": "Reporte de agricultura generado correctamente",
  "data": [
    {"tipo_cultivo": "Maiz en grano", "id_cultivo": 6, "cultivo_nombre": "Maiz en grano",
     "cultivo_grupo": "Cereales", "total_registros": 1,
     "hectareas_afectadas": 100.0, "hectareas_perdidas": 20.0},
    {"tipo_cultivo": "Lechuga", "id_cultivo": 45, "cultivo_nombre": "Lechuga",
     "cultivo_grupo": "Hortalizas", "total_registros": 1,
     "hectareas_afectadas": 50.0, "hectareas_perdidas": 50.0},
    {"tipo_cultivo": "Banano", "id_cultivo": 13, "cultivo_nombre": "Banano",
     "cultivo_grupo": "Frutales", "total_registros": 2,
     "hectareas_afectadas": 27.0, "hectareas_perdidas": 30.0}
  ],
  "total": 4
}
```

### `GET /reportes/pecuario` — respuesta real

```json
{
  "success": true,
  "message": "Reporte de pecuario generado correctamente",
  "data": [
    {"especie": "Bovino", "id_especie": 44, "especie_catalogo": "Bovinos",
     "especie_grupo": "Ganado mayor", "total_registros": 2,
     "animales_afectados": 30.0, "animales_muertos": 4.0}
  ],
  "total": 1
}
```

## `GET /api/v2/edan/{id}` — EDAN completo

- `modo=detallado` (default): cabecera + `localidades[]` (cada una con sus 14
  secciones) + `resumen_secciones`.
- `modo=compacto`: cabecera + `resumen_localidades[]` + `sumatorias` +
  `resumen_secciones`.

### `resumen_secciones` (nuevo)

Agrega las 14 secciones del grupo desde las tablas `edan.edan_localidades_*`
(si el EDAN no tiene localidades devuelve `{}`):

`impacto_poblacion`, `primera_respuesta`, `salud_establecimientos`,
`necesidad_salud`, `danos_viales`, `danos_infra_publica`,
`servicios_basicos`, `unidades_educativas`, `danos_vivienda`,
`danos_agricultura`, `danos_pecuarios`, `infra_productiva`, `proteccion`,
`necesidad_humanitaria`.

Ejemplo real para el EDAN **76** (`070101/2026/002`, UGRSCZ, municipio 70101,
evento Sequía, 1 localidad):

```json
{
  "id_edan": 76,
  "codigo_edan": "070101/2026/002",
  "id_estado": 1,
  "estado": "Borrador",
  "id_usuario_ugr": 28,
  "localidades": [ "…(formulario completo de la localidad)…" ],
  "resumen_secciones": {
    "impacto_poblacion": {
      "por_grupo_etario": [
        {"id_grupo_etario": 1, "grupo_etario": "Niño (a) 0-5 años",
         "fallecidos": 5, "heridos": 8, "desaparecidos": 0},
        {"id_grupo_etario": 2, "grupo_etario": "Escolar de 6-18 años", "…": "…"}
      ],
      "totales": {"fallecidos": 5, "heridos": 8, "desaparecidos": 0, "localidades": 1}
    },
    "necesidad_salud": {"localidades": 1, "numero_personas": 0},
    "danos_agricultura": {
      "por_cultivo": [
        {"id_cultivo": 2, "cultivo": "Avena", "tipo_cultivo": "Avena",
         "hectareas_afectadas": 5, "hectareas_perdidas": 3},
        {"id_cultivo": 13, "cultivo": "Banano", "tipo_cultivo": "Banano",
         "hectareas_afectadas": 2, "hectareas_perdidas": 0}
      ],
      "hectareas_afectadas": 7,
      "hectareas_perdidas": 3,
      "total_registros": 2
    },
    "infra_productiva": {
      "por_tipo": [{"tipo": "Bebedero", "dano_parcial": 0, "dano_total": 2}],
      "dano_parcial": 0,
      "dano_total": 2,
      "total_registros": 1
    },
    "proteccion": {
      "por_grupo": [{"grupo": "", "mujeres": 7, "hombres": 6, "total": 13,
                     "apoyo_psicologico": 0, "reposicion_documentos": 0}],
      "mujeres": 7,
      "hombres": 6,
      "total": 13,
      "total_registros": 1
    }
  }
}
```

> Nota: en `salud_establecimientos`, `danos_viales`, `danos_infra_publica`,
> `servicios_basicos` y `unidades_educativas` las columnas `dano_parcial` /
> `dano_total` son **booleanos**; en el resumen se cuentan sus `TRUE`
> (`(col)::int`). En `danos_vivienda` e `infra_productiva` son enteros y se
> suman.

## `GET /api/v2/edan/mis-resumen` — respuesta real (rol 6, usuario 28)

Totales de los EDAN del UGR según `estado_edan`:

```json
{
  "success": true,
  "message": "Resumen de mis EDAN generado correctamente",
  "data": {
    "total_edans": 1,
    "total_borrador": 1,
    "total_enviado": 0,
    "total_aprobado": 0,
    "total_poblacion_afectada": 100.0,
    "total_familias_afectadas": 5.0,
    "total_familias_damnificadas": 2.0,
    "total_localidades": 1,
    "por_estado": [{"id_estado": 1, "estado": "Borrador", "cantidad": 1}],
    "por_tipo_evento": [{"id_tipo_evento": 6, "tipo_evento": "Sequía", "cantidad": 1}]
  }
}
```

## Swagger / OpenAPI

Todos los endpoints de reportes y `mis-resumen` tienen `response_model`
tipado (`ResumenReporteResponse`, `ReporteGeografiaResponse`,
`ReporteAgriculturaResponse`, `ReportePecuarioResponse`, `MisResumenResponse`)
visible en `/docs`.