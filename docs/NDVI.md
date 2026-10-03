# NDVI Satelital - Documentación Técnica

## Resumen

Módulo de series históricas de NDVI calculado desde imágenes Sentinel-2 (EarthSearch STAC API).

**Estado:** ✅ IMPLEMENTADO (v2.28.0)

---

## Arquitectura

```
┌─────────────────────────────────────────────────────────┐
│  EarthSearch STAC API (sentinel-2-l2a)                  │
│  - Bandas: B08 (nir), B04 (red), SCL                    │
│  - Revisita: 5 días                                     │
│  - Resolución: 10m                                      │
│  - Sin API key requerida                                │
└────────────────────┬────────────────────────────────────┘
                     │ POST /search (bbox, fecha, nubes)
                     ↓
┌─────────────────────────────────────────────────────────┐
│  SINAGERSAT - Ingesta NDVI                              │
│  1. Consultar EarthSearch                               │
│  2. Filtrar por cobertura de nubes (<20%)               │
│  3. Calcular NDVI = (NIR - Red) / (NIR + Red)           │
│  4. Aplicar máscara de nubes (SCL)                      │
│  5. Agregar por comunidad (promedio espacial)           │
│  6. Guardar en BD                                       │
└────────────────────┬────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────┐
│  PostgreSQL - Esquema sinb                              │
│  - escena_satelital (1 fila por escena)                 │
│  - agregado_satelital (1 fila por comunidad×escena)     │
│  - serie_ndvi_comunidad (serie temporal)                │
│  - vw_ultimo_ndvi_comunidad (vista)                     │
│  - vw_evolucion_mensual_ndvi (vista)                    │
│  - vw_alertas_ndvi (vista)                              │
└────────────────────┬────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────┐
│  FastAPI - Endpoints v2                                 │
│  GET  /api/v2/ndvi/comunidad                            │
│  GET  /api/v2/ndvi/comunidad/{codigo}/evolucion         │
│  GET  /api/v2/ndvi/comunidad/{codigo}/serie             │
│  GET  /api/v2/ndvi/alertas                              │
│  GET  /api/v2/ndvi/geojson/mapa-calor                   │
│  GET  /api/v2/ndvi/geojson/bbox                         │
│  POST /api/v2/ndvi/ingestar                             │
└─────────────────────────────────────────────────────────┘
```

---

## Endpoints API

### 1. `GET /api/v2/ndvi/comunidad`

**Último NDVI disponible por comunidad.**

**Parámetros:**
- `codigo_comunidad` (opcional): Filtrar por código de comunidad

**Respuesta:**
```json
{
  "success": true,
  "data": [
    {
      "codigo_ine": "0201001",
      "nombre": "Comunidad A",
      "fecha": "2026-10-01",
      "ndvi_promedio": 0.52,
      "ndvi_anomalia": 0.08,
      "estado_vegetacion": "normal",
      "estado_alerta": "muy_bien"
    }
  ],
  "total": 343
}
```

---

### 2. `GET /api/v2/ndvi/comunidad/{codigo_comunidad}/evolucion`

**Evolución mensual de NDVI.**

**Parámetros:**
- `codigo_comunidad` (requerido): Código de comunidad
- `meses` (opcional, default=12): Meses hacia atrás (1-60)

**Respuesta:**
```json
{
  "success": true,
  "data": [
    {
      "codigo_ine": "0201001",
      "nombre": "Comunidad A",
      "mes": "2026-10-01T00:00:00",
      "ndvi_promedio_mes": 0.52,
      "anomalia_promedio_mes": 0.08,
      "n_dias_con_datos": 8
    }
  ]
}
```

---

### 3. `GET /api/v2/ndvi/comunidad/{codigo_comunidad}/serie`

**Serie temporal completa de NDVI.**

**Parámetros:**
- `codigo_comunidad` (requerido)
- `fecha_desde` (opcional)
- `fecha_hasta` (opcional)
- `limit` (opcional, default=365, max=1000)

**Respuesta:**
```json
{
  "success": true,
  "data": [
    {
      "fecha": "2026-10-01",
      "ndvi_promedio": 0.52,
      "ndvi_anomalia": 0.08,
      "estado_vegetacion": "normal",
      "n_escenas": 3
    }
  ]
}
```

---

### 4. `GET /api/v2/ndvi/alertas`

**Alertas activas de NDVI bajo.**

**Parámetros:**
- `departamento` (opcional)
- `provincia` (opcional)
- `municipio` (opcional)

**Niveles de alerta:**
1. `sequia_extrema` (NDVI < 0.2)
2. `sequia_moderada` (NDVI < 0.3)
3. `anomalia_negativa_fuerte` (< -0.15)
4. `anomalia_negativa_leve` (< -0.05)

**Respuesta:**
```json
{
  "success": true,
  "data": [
    {
      "codigo_ine": "0502003",
      "nombre": "Comunidad B",
      "fecha": "2026-10-02",
      "ndvi_promedio": 0.18,
      "ndvi_anomalia": -0.22,
      "estado_vegetacion": "seco",
      "tipo_alerta": "sequia_extrema",
      "nivel_prioridad": 1
    }
  ]
}
```

---

### 5. `GET /api/v2/ndvi/geojson/mapa-calor`

**GeoJSON para mapa de calor de NDVI.**

**Parámetros:**
- `departamento` (opcional): Filtrar por departamento
- `provincia` (opcional): Filtrar por provincia
- `municipio` (opcional): Filtrar por municipio
- `nivel` (opcional, default="comunidad"): "comunidad" o "municipio"

**Respuesta:** FeatureCollection GeoJSON

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {"type": "Polygon", "coordinates": [...]},
      "properties": {
        "codigo_ine": "0201001",
        "nombre": "Comunidad A",
        "ndvi_promedio": 0.52,
        "ndvi_anomalia": 0.08,
        "estado_vegetacion": "normal",
        "estado_alerta": "muy_bien",
        "color": "#32CD32"
      }
    }
  ]
}
```

**Colores por NDVI:**
- `< 0.1`: `#8B4513` (suelo desnudo, marrón)
- `< 0.2`: `#DAA520` (seco, dorado)
- `< 0.3`: `#FFD700` (bajo, amarillo)
- `< 0.5`: `#9ACD32` (normal, verde claro)
- `< 0.7`: `#32CD32` (alto, verde)
- `>= 0.7`: `#006400` (muy alto, verde oscuro)

**Uso en frontend (Leaflet):**
```javascript
fetch('/api/v2/ndvi/geojson/mapa-calor?departamento=La%20Paz')
  .then(r => r.json())
  .then(geojson => {
    L.geoJSON(geojson.data, {
      style: feature => ({
        fillColor: feature.properties.color,
        weight: 1,
        opacity: 1,
        fillOpacity: 0.7
      })
    }).addTo(map);
  });
```

---

### 6. `GET /api/v2/ndvi/geojson/bbox`

**GeoJSON filtrado por bounding box.**

**Parámetros (requeridos):**
- `min_lon`: Lon mínimo
- `min_lat`: Lat mínima
- `max_lon`: Lon máximo
- `max_lat`: Lat máximo

**Útil para:** Zoom a región específica en mapas interactivos.

---

### 7. `POST /api/v2/ndvi/ingestar`

**Ingestar NDVI desde EarthSearch.**

**Requiere:** Rol admin

**Body:**
```json
{
  "codigos_comunidades": ["0201001", "0201002"],  // null = todas
  "max_nubes": 20.0
}
```

**Respuesta:**
```json
{
  "success": true,
  "data": {
    "escenas_consultadas": 50,
    "escenas_procesadas": 35,
    "comunidades_procesadas": 10,
    "errores": []
  }
}
```

---

### 8. `GET /api/v2/ndvi/escenas`

**Listar escenas satelitales procesadas.**

**Parámetros:**
- `fecha_desde` (opcional)
- `fecha_hasta` (opcional)
- `cobertura_nubes_max` (opcional, default=20.0)
- `skip` (opcional, default=0)
- `limit` (opcional, default=100, max=500)

---

### 9. `GET /api/v2/ndvi/escenas/consultar`

**Consultar EarthSearch STAC API en tiempo real.**

**Parámetros:**
- `min_lon`, `min_lat`, `max_lon`, `max_lat` (bbox)
- `fecha_desde`, `fecha_hasta`
- `max_nubes` (default=20.0)

**Respuesta:** Features brutos de EarthSearch.

---

### 10. `GET /api/v2/ndvi/estadisticas/resumen`

**Resumen estadístico de la base de datos NDVI.**

**Respuesta:**
```json
{
  "success": true,
  "data": {
    "escenas_procesadas": 150,
    "comunidades_con_datos": 343,
    "fecha_minima": "2026-01-01",
    "fecha_maxima": "2026-10-03",
    "ndvi_promedio_30dias": 0.48,
    "alertas_activas": 12
  }
}
```

---

### 11. `GET /api/v2/ndvi/procesamiento/log`

**Log de procesamiento de ingestión.**

**Parámetros:**
- `fecha_desde` (opcional)
- `limit` (opcional, default=30)

---

## Tarea CRON

### Instalación

```bash
crontab -e
```

Agregar línea:
```
0 6 * * * cd /home/prosuco/SINAGERSAT/BaseData && venv/bin/python scripts/cron_ndvi_ingest.py >> /var/log/sinb/ndvi_cron.log 2>&1
```

### Ejecución manual (testing)

```bash
cd /home/prosuco/SINAGERSAT/BaseData
venv/bin/python scripts/cron_ndvi_ingest.py
```

### Logs

- Logs de CRON: `/var/log/sinb/ndvi_cron.log`
- Logs de la API: `/tmp/uvicorn.log`

---

## Esquema de Base de Datos

### Tablas principales

```sql
-- Escenas satelitales
sinb.escena_satelital
├─ id uuid
├─ escena_id varchar(100)  -- ID EarthSearch
├─ fecha_adquisicion date
├─ cobertura_nubes numeric(5,2)
├─ huella geometry(MULTIPOLYGON)
├─ metadata jsonb
└─ creado_en timestamptz

-- Agregados por comunidad
sinb.agregado_satelital
├─ id uuid
├─ id_escena_satelital uuid (FK)
├─ codigo_comunidad text (FK)
├─ ndvi_promedio numeric(5,4)
├─ ndvi_min numeric(5,4)
├─ ndvi_max numeric(5,4)
├─ pixeles_validos integer
└─ fecha_proceso timestamptz

-- Serie temporal (para consultas rápidas)
sinb.serie_ndvi_comunidad
├─ id uuid
├─ codigo_comunidad text (FK)
├─ fecha date
├─ ndvi_promedio numeric(5,4)
├─ ndvi_anomalia numeric(5,4)  -- vs. histórico 5 años
├─ estado_vegetacion varchar(20)
└─ actualizado_en timestamptz
```

### Vistas

```sql
-- Último NDVI por comunidad
sinb.vw_ultimo_ndvi_comunidad

-- Evolución mensual (últimos 12 meses)
sinb.vw_evolucion_mensual_ndvi

-- Alertas activas (últimos 7 días)
sinb.vw_alertas_ndvi
```

---

## Migración

```bash
# Ejecutar migración v2.28.0
PGPASSWORD=12345678 psql -h 127.0.0.1 -U sinagersat -d db_sinagersat \
  -f database/migrations/v2.28.0_ndvi_satelital.sql
```

---

## Ejemplos de Uso

### 1. Verificar estado de vegetación en un municipio

```bash
curl -s "http://localhost:8000/api/v2/ndvi/comunidad?codigo_comunidad=0201001" \
  | python3 -m json.tool
```

### 2. Obtener alertas de sequía por departamento

```bash
curl -s "http://localhost:8000/api/v2/ndvi/alertas?departamento=Oruro" \
  | python3 -m json.tool
```

### 3. Generar mapa de calor para todo el país

```bash
curl -s "http://localhost:8000/api/v2/ndvi/geojson/mapa-calor" \
  -o ndvi_bolivia.geojson
```

### 4. Exportar serie temporal para análisis

```bash
curl -s "http://localhost:8000/api/v2/ndvi/comunidad/0201001/serie?fecha_desde=2026-01-01&limit=365" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('fecha,ndvi,anomalia,estado')
for row in d['data']:
    print(f\"{row['fecha']},{row['ndvi_promedio']},{row['ndvi_anomalia']},{row['estado_vegetacion']}\")
" > serie_ndvi_0201001.csv
```

### 5. Consultar EarthSearch manualmente

```bash
curl -s "http://localhost:8000/api/v2/ndvi/escenas/consultar?min_lon=-70&min_lat=-20&max_lon=-65&max_lat=-15&max_nubes=10" \
  | python3 -m json.tool
```

---

## Validación Científica

### Comparación con observaciones de campo

```sql
-- Correlación NDVI vs. observaciones de bioindicadores
SELECT 
    date_trunc('month', o.fecha_ocurrencia) as mes,
    avg(s.ndvi_promedio) as ndvi_promedio,
    count(o.id) as n_observaciones
FROM sinb.observacion o
JOIN sinb.serie_ndvi_comunidad s 
  ON o.codigo_comunidad = s.codigo_comunidad
  AND date_trunc('month', o.fecha_ocurrencia) = date_trunc('month', s.fecha)
WHERE o.fecha_ocurrencia >= '2026-01-01'
GROUP BY mes
ORDER BY mes;
```

### Detección de anomalías

```sql
-- Comunidades con NDVI más bajo que el histórico
SELECT 
    c.nombre,
    s.fecha,
    s.ndvi_promedio,
    s.ndvi_anomalia,
    s.estado_vegetacion
FROM sinb.serie_ndvi_comunidad s
JOIN shared.comunidades c ON s.codigo_comunidad = c.codigo_ine
WHERE s.fecha >= (CURRENT_DATE - INTERVAL '7 days')
  AND s.ndvi_anomalia < -0.15
ORDER BY s.ndvi_anomalia ASC;
```

---

## Solución de Problemas

### Error: "EarthSearch timeout"

**Causa:** La API de EarthSearch puede ser lenta.

**Solución:** Aumentar timeout en `service_ndvi.py:consultar_earthsearch()`:
```python
response = requests.post(url, json=query, headers=headers, timeout=60)
```

### Error: "No hay escenas disponibles"

**Causa:** Cobertura de nubes muy alta en la región.

**Solución:** Aumentar `max_nubes` en la consulta:
```bash
curl "http://localhost:8000/api/v2/ndvi/escenas/consultar?...&max_nubes=40"
```

### Error: "NDVI NULL para todas las comunidades"

**Causa:** No se ejecutó la ingesta.

**Solución:** Ejecutar manualmente:
```bash
python scripts/cron_ndvi_ingest.py
```

---

## Referencias

- **EarthSearch STAC API:** https://earth-search.aws.element84.com/v1/docs
- **Sentinel-2:** https://sentinel.esa.int/web/sentinel/user-guides/sentinel-2-msi
- **Fórmula NDVI:** Rouse et al. (1974)
- **Open-Meteo NDVI:** NO disponible (requiere cálculo propio)

---

## Estado de Implementación

| Componente | Estado | Archivo |
|---|---|---|
| Migración SQL | ✅ Completado | `database/migrations/v2.28.0_ndvi_satelital.sql` |
| Tablas | ✅ Creadas | PostgreSQL (sinb.escena_satelital, sinb.agregado_satelital, sinb.serie_ndvi_comunidad) |
| Vistas | ✅ Creadas | vw_ultimo_ndvi_comunidad, vw_evolucion_mensual_ndvi, vw_alertas_ndvi |
| Funciones SQL | ✅ Creadas | clasificar_estado_vegetacion(), calcular_anomalia_ndvi(), actualizar_serie_ndvi_comunidad() |
| Service (Python) | ✅ Completado | `api/sinb/service_ndvi.py` |
| Router (API) | ✅ Completado | `api/sinb/router_ndvi.py` |
| Schemas (Pydantic) | ✅ Completado | `api/sinb/schemas.py` |
| Endpoints | ✅ 11 endpoints | `/api/v2/ndvi/*` |
| GeoJSON | ✅ 2 endpoints | mapa-calor, bbox |
| Script CRON | ✅ Completado | `scripts/cron_ndvi_ingest.py` |
| Documentación | ✅ Completado | `docs/NDVI.md` |

**Versión:** v2.28.0  
**Fecha:** 2026-10-03  
**Autor:** SINAGERSAT
