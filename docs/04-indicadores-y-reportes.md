# 04 · Indicadores y reportes

> Verificado contra `GET /openapi.v2.json` y el código de los módulos en octubre de 2026.

## 1. Estado general

| Tipo | ¿Existe? | Formato de salida |
|---|---|---|
| Indicadores / KPIs agregados | **Sí** | JSON dentro del envoltorio `{success, message, data, total}` |
| Consultas geográficas para mapas | **Sí** | GeoJSON (RFC 7946) |
| Reportes descargables (PDF, Excel, CSV) | **No** | — |
| Generación automática de reportes (cron) | **No** | — |
| Dashboard web con gráficas | **No** (el frontend está fuera del repo) | — |

> Todos los "reportes" del sistema son **consultas agregadas en JSON** que un frontend (web o móvil) debe representar. La generación de ficheros descargables queda registrada como **pendiente** en [INFORME_ENTREGA.md](INFORME_ENTREGA.md).

## 2. Indicadores EDAN

| Endpoint | Fichero | Qué calcula |
|---|---|---|
| `GET /api/v2/edan/reportes/resumen` | `api/edan/router_v2_edan.py:118` | Totales, huérfanas vs consolidadas, población/familias/damnificadas, desglose por estado (`api/edan/service.py:4083-4127`) |
| `GET /api/v2/edan/reportes/geografico` | `router_v2_edan.py:132` | Agrupado por departamento / provincia / municipio (`service.py:4130-4152`) |
| `GET /api/v2/edan/reportes/agricultura` | `router_v2_edan.py:146` | Daños agrícolas agregados |
| `GET /api/v2/edan/reportes/pecuario` | `router_v2_edan.py:160` | Daños pecuarios agregados |
| `GET /api/v2/edan/reportes/mis-reportes` | `router_v2_edan.py:101` | Reportes del usuario autenticado |
| `GET /api/v2/edan/mis-resumen`, `/mis-estados` | `router_v2_edan.py:181,197` | Resumen personal y estados |
| `GET /api/v2/edan/localidades/mis-resumen` | `router_v2.py:154` | Resumen de localidades propias |
| `GET /api/v2/edan/localidades/municipio/{id}/resumen` | `router_v2_localidades.py:553` | Resumen ejecutivo por municipio |
| `GET /api/v2/edan/localidades/filtrar` | `router_v2.py:105` | Listado con filtros de cabecera (respuesta comprimida) |

Filtros comunes: geografía (`id_departamento`, `id_provincia`, `id_municipio`), fechas y paginación. El alcance por rol se aplica en el servicio (`_filtros_dep_factory`, `api/edan/router_v2_edan.py:25`).

## 3. Indicadores SINB

| Endpoint | Fichero:línea | Qué calcula |
|---|---|---|
| `GET /api/v2/sinb/reporte/pronosticos` | `api/sinb/router_v2.py:1243` | Totales por tipo y estado de pronóstico; verificaciones (coinciden / no coinciden / pendientes) |
| `GET /api/v2/sinb/observadores/ranking` | `router_v2.py:974` | Ranking de aportes de observadores |
| `GET /api/v2/sinb/galeria/indicadores-destacados` | `router_v2.py:1905` | Indicadores con más evidencias |
| `GET /api/v2/sinb/galeria/evidencias` | `router_v2.py:1840` | Evidencias geolocalizadas |
| `GET /api/v2/sinb/verificacion/pendientes` | `router_v2.py:664` | Pronósticos pendientes de verificación |
| `GET /api/v2/sinb/indicador-natural` | `router_v2.py:111` | Catálogo de indicadores bioculturales (CRUD) |

Catálogo SINB: `grupo`, `indicador_natural`, `caracteristica`, `comportamiento`, `significado`, `zona_geografica` (cada uno con GET/POST/PUT/DELETE).

## 4. Indicadores NDVI (satélite)

| Endpoint | Fichero:línea | Qué calcula |
|---|---|---|
| `GET /api/v2/ndvi/estadisticas/resumen` | `api/sinb/router_ndvi.py:544` | Escenas procesadas, comunidades con datos, rango de fechas, promedio NDVI 30 días, alertas activas |
| `GET /api/v2/ndvi/alertas` | `router_ndvi.py:132` | Alertas desde `sinb.vw_alertas_ndvi` |
| `GET /api/v2/ndvi/geojson/mapa-calor` | `router_ndvi.py:246` | Mapa de calor NDVI |
| `GET /api/v2/ndvi/comunidad/{codigo}/evolucion` | `router_ndvi.py:78` | Serie temporal por comunidad |

## 5. Indicadores de población y geografía (censo 2024)

| Endpoint | Contenido |
|---|---|
| `GET /api/v2/shared/censo/poblacion/nacional` | Totales nacionales |
| `GET /api/v2/shared/censo/poblacion/departamentos` | Por los 9 departamentos |
| `GET /api/v2/shared/censo/poblacion/provincias` | Por las 113 provincias |
| `GET /api/v2/shared/censo/poblacion/municipios` | Por los 343 municipios |
| `GET /api/v2/shared/censo/poblacion/{departamento\|provincia\|municipio}/{id}` | Detalle jerárquico |
| `GET /api/v2/shared/municipios/geojson` / `/geom` / `/ubicacion` | Límites GeoJSON, WKT y coordenada → municipio |

Fuentes: `shared.manzanos` y `shared.comunidades` (Censo 2024, migraciones `v2.15.0` y `v2.16.0`).

## 6. Indicadores RIDA

**Hoy no existe un endpoint de KPIs de RIDA.** Los datos se pueden derivar de los listados operativos:

| Dato | Fuente |
|---|---|
| Formularios por estado | `GET /api/v2/rida/empadronamiento/formularios` (+ filtros) |
| Familias / integrantes de un formulario | `GET /api/v2/rida/empadronamiento/formularios/{id}` (árbol completo) |
| Mis formularios | `GET /api/v2/rida/empadronamiento/formularios/mis` |
| Búsqueda de personas | `GET /api/v2/rida/empadronamiento/personas/buscar` |
| Necesidades por formulario o familia | `GET /api/v2/rida/necesidades/formularios/{id}/necesidades`, `.../familias/{id}/necesidades` |
| Solicitudes por etapa/modalidad | `GET /api/v2/rida/solicitudes` (filtros) |
| Eventos y localidades | `GET /api/v2/rida/eventos`, `GET /api/v2/rida/evento/{id}/localidades` |

> La creación de `GET /api/v2/rida/indicadores` (KPIs agregados) estaba prevista en el alcance inicial pero **no se ha implementado** en esta entrega; ver [INFORME_ENTREGA.md](INFORME_ENTREGA.md).

## 7. Auditoría como fuente de indicadores

`GET /api/v2/usuarios/auditoria` (`api/usuarios/router.py:215-256`) permite construir indicadores de uso: escrituras por usuario, por módulo y por rango de fechas.

## 8. Cómo consumir un indicador

```bash
# 1. Autenticar
TOKEN=$(curl -s -X POST http://localhost:8000/api/v2/auth/login \
  -H "Content-Type: application/json" \
  -d '{"usuario":"...","contrasena":"..."}' | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['access_token'])")

# 2. Consultar un indicador
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v2/edan/reportes/resumen" | python3 -m json.tool

# 3. Indicador con filtros geográficos
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v2/shared/censo/poblacion/municipios?id_departamento=1"
```

**Formato de respuesta siempre envuelto** (`api/response.py`):

```json
{ "success": true, "message": "...", "data": [ ... ], "total": 123 }
```

## 9. Trabajo pendiente relacionado

| Pendiente | Detalle |
|---|---|
| Endpoint `GET /api/v2/rida/indicadores` | KPIs agregados de RIDA en una sola respuesta |
| Exportación a Excel/PDF | Al menos 3 reportes descargables (empadronamiento, necesidades, eventos) |
| Generación automática por cron | Tras la exportación, publicación periódica en `uploads/reports/` |

---

**Anterior:** [03 · Offline y sincronización](03-offline-y-sincronizacion.md) · Índice: [README](README.md)
