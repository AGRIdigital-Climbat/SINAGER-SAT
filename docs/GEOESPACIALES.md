# Geoespaciales — GeoJSON, WKT y Ubicación

Guía de los endpoints geoespaciales de SINAGERSAT (v1.2.5) para uso con herramientas de mapas y GPS.

## Requisitos

- PostgreSQL 16+ con extensión **PostGIS** (incluida en el backup `backup_2026_07_26.sql`)
- 340 municipios con geometrías `MULTIPOLYGON` en SRID 4326 (WGS 84)

## Endpoints

| Método | URL | Descripción |
|--------|-----|-------------|
| GET | `/api/v1/shared/municipios/geojson` | Todos los municipios como GeoJSON FeatureCollection |
| GET | `/api/v1/shared/municipios/geojson?id_departamento=2` | Filtrar por departamento |
| GET | `/api/v1/shared/municipios/geojson?id_provincia=201` | Filtrar por provincia |
| GET | `/api/v1/shared/municipios/{id}/geojson` | Un municipio como GeoJSON Feature |
| GET | `/api/v1/shared/municipios/geom` | Todos los municipios con geometría WKT |
| GET | `/api/v1/shared/municipios/{id}/geom` | Un municipio con geometría WKT |
| GET | `/api/v1/shared/municipios/ubicacion?lat=-16.49&lon=-68.12` | Identificar municipio por coordenada |

---

## 1. GeoJSON (RFC 7946)

Formato estándar para datos geoespaciales en la web. Compatible con todas las herramientas de mapas.

### Respuesta completa (FeatureCollection)

```bash
curl http://localhost:8000/api/v1/shared/municipios/geojson
```

```json
{
  "type": "FeatureCollection",
  "name": "municipios_bolivia",
  "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "MultiPolygon",
        "coordinates": [[[[-68.12, -16.49], [-68.11, -16.48], ...]]]
      },
      "properties": {
        "id": 20101,
        "codigo_ine": "020101",
        "nombre": "La Paz",
        "departamento": {"id": 2, "codigo_ine": "02", "nombre": "La Paz"},
        "provincia": {"id": 201, "codigo_ine": "0201", "nombre": "Murillo"},
        "area_km2": 263.17
      },
      "bbox": [-68.36, -16.62, -68.04, -16.35]
    }
  ],
  "total": 340,
  "bbox": [-69.65, -22.90, -57.17, -9.68]
}
```

### Un municipio (Feature)

```bash
curl http://localhost:8000/api/v1/shared/municipios/20101/geojson
```

---

## 2. WKT (Well-Known Text)

Formato de texto para geometrías. Útil para debug y consultas SQL directas.

```bash
curl http://localhost:8000/api/v1/shared/municipios/geom
```

```json
{
  "type": "GeometryCollection",
  "geometries": [
    {
      "id": 20101,
      "codigo_ine": "020101",
      "nombre": "La Paz",
      "geom_wkt": "MULTIPOLYGON(((-68.12 -16.49, -68.11 -16.48, ...)))",
      "srid": 4326,
      "departamento": {"id": 2, "codigo_ine": "02", "nombre": "La Paz"},
      "provincia": {"id": 201, "codigo_ine": "0201", "nombre": "Murillo"}
    }
  ],
  "total": 340
}
```

---

## 3. Ubicación (punto-dentro-de-polígono)

Dada una coordenada GPS, identifica a qué municipio, provincia y departamento pertenece.

```bash
curl "http://localhost:8000/api/v1/shared/municipios/ubicacion?lat=-16.4897&lon=-68.1193"
```

```json
{
  "lat": -16.4897,
  "lon": -68.1193,
  "municipio": {"id": 20101, "codigo_ine": "020101", "nombre": "La Paz"},
  "provincia": {"id": 201, "codigo_ine": "0201", "nombre": "Murillo"},
  "departamento": {"id": 2, "codigo_ine": "02", "nombre": "La Paz"}
}
```

Si la coordenada no cae dentro de ningún municipio:
```json
{
  "lat": 0.0,
  "lon": 0.0,
  "municipio": null,
  "provincia": null,
  "departamento": null,
  "message": "No se encontró municipio para estas coordenadas"
}
```

---

## Uso con herramientas de mapas

### Leaflet (JavaScript)

```javascript
// Cargar todos los municipios
fetch('/api/v1/shared/municipios/geojson')
  .then(r => r.json())
  .then(data => {
    L.geoJSON(data, {
      style: { color: '#3388ff', weight: 1, fillOpacity: 0.3 },
      onEachFeature: (feature, layer) => {
        layer.bindPopup(feature.properties.nombre);
      }
    }).addTo(map);
  });
```

### OpenLayers (JavaScript)

```javascript
const vectorSource = new ol.source.Vector({
  url: '/api/v1/shared/municipios/geojson',
  format: new ol.format.GeoJSON()
});
const vectorLayer = new ol.layer.Vector({
  source: vectorSource,
  style: new ol.style.Style({
    stroke: new ol.style.Stroke({ color: '#3388ff', width: 1 }),
    fill: new ol.style.Fill({ color: 'rgba(51, 136, 255, 0.3)' })
  })
});
map.addLayer(vectorLayer);
```

### Google Maps (JavaScript)

```javascript
fetch('/api/v1/shared/municipios/geojson')
  .then(r => r.json())
  .then(data => {
    data.features.forEach(feature => {
      const dataLayer = new google.maps.Data();
      dataLayer.addGeoJson(feature);
      dataLayer.setStyle({ fillColor: '#3388ff', fillOpacity: 0.3 });
      dataLayer.setMap(map);
    });
  });
```

### Mapbox GL JS

```javascript
map.addSource('municipios', {
  type: 'geojson',
  data: '/api/v1/shared/municipios/geojson'
});
map.addLayer({
  id: 'municipios-fill',
  type: 'fill',
  source: 'municipios',
  paint: { 'fill-color': '#3388ff', 'fill-opacity': 0.3 }
});
```

### QGIS

1. Capa > Añadir capa > Añadir capa vectorial
2. Tipo: `Protocolo`
3. Tipo de protocolo: `GeoJSON`
4. URL: `http://localhost:8000/api/v1/shared/municipios/geojson`

### kepler.gl

1. Arrastrar y soltar el JSON de la respuesta sobre el mapa
2. O usar la URL del endpoint directamente

### Python (Shapely / GeoPandas)

```python
import requests
import geopandas as gpd
from shapely import wkt

# Cargar como GeoDataFrame
r = requests.get('http://localhost:8000/api/v1/shared/municipios/geojson')
gdf = gpd.GeoDataFrame.from_features(r.json()['features'])

# Consulta espacial
punto = gpd.GeoSeries([Point(-68.12, -16.49)], crs='EPSG:4326')
municipio = gdf[gdf.contains(punto.iloc[0])]
```

### SQL directo con PostGIS

```sql
-- Buscar municipio por coordenada
SELECT m.codigo_ine, m.nombre
FROM shared.municipio m
WHERE ST_Contains(m.geom, ST_SetSRID(ST_Point(-68.1193, -16.4897), 4326));

-- Distancia entre dos municipios (en metros)
SELECT ST_Distance(
  (SELECT geom FROM shared.municipio WHERE id = 20101)::geography,
  (SELECT geom FROM shared.municipio WHERE id = 70201)::geography
);

-- Área de un municipio (en km²)
SELECT ST_Area(geom::geography) / 1000000 as area_km2
FROM shared.municipio WHERE id = 20101;
```
