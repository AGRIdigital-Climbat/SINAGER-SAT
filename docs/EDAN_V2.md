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
| PUT | `/api/v2/edan/{id}` | Actualizar **responsable/alcalde** de la cabecera |
| PUT | `/api/v2/edan/{id}/estado` | Cambiar estado del EDAN (`estado_edan`) |
| DELETE | `/api/v2/edan/{id}?permanente=false` | Baja lógica (sync) |
| GET | `/api/v2/edan/mis-resumen` | Totales de mis EDAN + `por_estado` |
| GET | `/api/v2/edan/mis-reportes` | Mis EDAN con localidades |
| GET | `/api/v2/edan/mis-estados` | Lista ligera (solo estado) para badges |
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