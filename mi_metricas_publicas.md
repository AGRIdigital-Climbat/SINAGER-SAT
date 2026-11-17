# Métricas públicas — guía para la página principal (sin token)

Todas son `GET`, **públicas** (no envían `Authorization`), **sin filtros**, formato
uniforme:

```json
{ "success": true, "message": "...", "data": [ ... | { ... } ], "total": N }
```

Servidor: `http://10.10.0.24:8000` (ajusta host). Base del grupo: `/api/v2/publico`.
Los datos EDAN distinguen `ambito`: `"consolidado"` (formulario del municipio,
`edan.edan`) vs `"local"` (una fila por localidad, `edan.edan_localidades`).
Las series anuales/mensuales vienen **completas desde el primer dato** (años/meses
sin eventos incluyen `total: 0`) — listas para gráfico de línea sin huecos.

## Tarjetas de portada (una sola llamada)
```bash
curl "$API/api/v2/publico/resumen"
# data.edan_consolidado_total, data.edan_local_total, data.edan_poblacion_afectada,
# data.edan_local_aprobados, data.repo_documentos, data.repo_doc_precedentes,
# data.usuarios_activos, data.geo_departamentos/provincias/municipios/manzanos/comunidades,
# data.censo_poblacion, data.censo_hogares_ine, data.motoria_documentos/chunks,
# data.edan_primera_fecha, data.edan_ultima_fecha
```

## EDAN
```bash
curl "$API/api/v2/publico/edan/resumen"            # totales por ambito (incl. sin_fecha)
curl "$API/api/v2/publico/edan/serie-anios"        # [{ambito, anio, total}]      -> linea "eventos por ano desde sus inicios"
curl "$API/api/v2/publico/edan/serie-anios-por-tipo"  # [{ambito, anio, id_tipo_evento, tipo, total}] -> barras apiladas por tipo
curl "$API/api/v2/publico/edan/serie-meses"        # [{ambito, mes "YYYY-MM", total}] -> estacionalidad
curl "$API/api/v2/publico/edan/tipos-evento"       # [{ambito, tipo, total}] DESC     -> "mas recurrentes" (top N con slice)
curl "$API/api/v2/publico/edan/estados"            # [{ambito, orden, estado, total}] -> workflow (consolidado 1-4, local 1-6)
curl "$API/api/v2/publico/edan/departamentos"      # [{ambito, id_departamento, departamento, eventos, poblacion_afectada}] top 15
curl "$API/api/v2/publico/edan/sectores"           # [{sector, total}] 14 sectores (flags de localidades)
```

## Repositorio de documentos
```bash
curl "$API/api/v2/publico/repositorio/serie-anios"          # [{origen, anio, total}]  origen: EDAN|RIDA|DOC_PRECEDENTE
curl "$API/api/v2/publico/repositorio/serie-anios-por-tipo" # [{id_tipo_documento, tipo, anio, total}]
curl "$API/api/v2/publico/repositorio/resumen"              # [{dimension, llave, total}]  (total/origen/tipo/firma/expedientes)
```
Nota: una `dimension='origen'` solo incluye orígenes con documentos; `DOC_PRECEDENTE`
aparecerá cuando el primer municipio suba un respaldo.

`dimension='expedientes'` (3 filas): cantidad de grupos de documentos por origen —
EDAN = `distinct id_edan`, RIDA = `distinct id_evento_rida`, DOC_PRECEDENTE =
`distinct codigo_documento` (clave de rastreo de la 3ª subida; ver
`mi_repositorio.md`). Solo conteos: nunca se exponen los códigos. Sirve para la
tarjeta "expedientes abiertos" o barras comparativas.

## Usuarios (solo cantidades — nunca datos personales)
```bash
curl "$API/api/v2/publico/usuarios/resumen"
# data.totales:        [{llave: total|activos|inactivos|con_municipio, cantidad}]
# data.por_rol:        [{rol, cantidad}]        (todos los roles, incl. 0)
# data.por_cargo:      [{cargo, cantidad}]      ("sin_especificar" agrupa vacios)
# data.por_geografia:  [{nivel: departamento|provincia|municipio, id, nombre, cantidad}]
```

## Censo 2024 (población y personas por hogar)
```bash
curl "$API/api/v2/publico/censo/nacional"        # 1 fila
curl "$API/api/v2/publico/censo/departamentos"   # 9 filas
curl "$API/api/v2/publico/censo/provincias"      # 113 filas
curl "$API/api/v2/publico/censo/municipios"      # 343 filas
# columnas: nivel, id_departamento, id_provincia, id_municipio, codigo_ine, nombre,
#           poblacion, viviendas, hogares, unidades_con_hogares, hogares_ine,
#           personas_por_hogar (numero entero o null)
```
`personas_por_hogar` = promedio oficial municipal `poblacion / hogares_ine` (tabulado
INE) con redondeo normal (3,5→4); si un municipio no tiene `hogares_ine`, se calcula
con las unidades que sí tienen ficha (`unidades_con_hogares`). `null` = sin dato.

## MotorIA y geografía
```bash
curl "$API/api/v2/publico/motor-ia/resumen"   # [{llave, cantidad}] docs/chunks/uso
curl "$API/api/v2/publico/geo/resumen"        # [{llave, cantidad}] dptos/prov/mun/manz/com
```

## Mapa (ya públicos, por si los necesitas junto a esto)
```bash
curl "$API/api/v2/shared/departamentos"                  # 9
curl "$API/api/v2/shared/provincias"                     # 113
curl "$API/api/v2/shared/municipios"                     # 343
curl "$API/api/v2/shared/municipios/geojson"             # todo el pais (mapbox)
curl "$API/api/v2/shared/municipios/{id}/geojson"        # uno
curl "$API/api/v2/shared/censo/poblacion/departamentos"  # equivalente censal con filtros propios
```

## Detalles útiles para el front
- **Caché 60 s** por servidor: los números no cambian más rápido que eso.
- No enviar `Authorization`: tampoco es necesario y ahorra CORS preflight raro.
- `total` en las listas = número de filas devueltas (no hay paginación a propósito:
  son conjuntos acotados: 9/113/343 municipios, años, meses, 14 sectores…).
- EDAN local con `fecha_evento IS NULL` (6 registros hoy) **no** entra en las series
  pero sí en los totales; el hueco se ve en `/edan/resumen.sin_fecha`.
- Series vacías: si el servidor gemelo aún no tiene datos, `data` puede venir `[]` o
  con un solo año — la app debe tolerar lista vacía.
- Documentación completa del backend (vistas SQL y replicación):
  `cambios_replicacion/PUBLICO_metricas_v266.md`.
