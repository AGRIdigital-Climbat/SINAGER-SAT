# Geoespaciales — GeoJSON, WKT y Ubicación

Guía de los endpoints geoespaciales de SINAGERSAT (v1.5.0) para uso con herramientas de mapas y GPS.

## Requisitos

- PostgreSQL 16+ con extensión **PostGIS**
- 340 municipios con geometrías `MULTIPOLYGON` en SRID 4326 (WGS 84)

### ⚠️ PostGIS y la columna `geom`

La extensión **PostGIS** y la columna `shared.municipio.geom` son **indispensables**
para estos endpoints (todos los SQL usan `ST_Transform`/`ST_AsGeoJSON`/`ST_Contains`).
Si la BD se restauró desde un **dump parcial** (`backup_pre_*.sql`, `crear_edan_db.sql`,
`edan_db_backup.sql`) o muy antiguo, la geometría se pierde y los endpoints devuelven
`500` con `column m.geom does not exist`.

**Instalar / reparar:**

```bash
# 1. Paquete PostGIS (deploy/instalar_postgresql.sh lo hace automáticamente)
sudo apt-get install -y postgresql-16-postgis-3

# 2. Extensión + columna + índice (idempotente)
sudo -u postgres psql -d db_sinagersat -f database/migration_v1.5.0.sql

# 3. Restaurar los 340 polígonos desde un backup completo SIN tocar otras tablas
bash database/restaurar_geom.sh            # usa backup_v1.3.0.sql por defecto
bash database/restaurar_geom.sh database/backup_v1.5.0.sql
```

**Verificar:**

```sql
SELECT count(*) FROM shared.municipio WHERE geom IS NOT NULL;   -- → 340
SELECT ST_SRID(geom) FROM shared.municipio WHERE id = 70101;    -- → 4326
SELECT extname FROM pg_extension WHERE extname = 'postgis';     -- → postgis
```

> **Regla para backups**: siempre restaurar desde el backup **completo más reciente**
> (`database/backup_*.sql` completo, p. ej. `backup_v1.5.0.sql`). Nunca usar un dump
> parcial como base. `database/hacer_backup.sh` (cron diario 03:00) genera los backups
> completos con PostGIS incluido.

## Endpoints

| Método | URL | Descripción |
|--------|-----|-------------|
| GET | `/api/v1/shared/municipios/geojson` | Todos los municipios como GeoJSON FeatureCollection |
| GET | `/api/v1/shared/municipios/geojson?id_departamento=2` | Filtrar por departamento |
| GET | `/api/v1/shared/municipios/geojson?id_provincia=201` | Filtrar por provincia |
| GET | `/api/v1/shared/municipios/{id}/geojson` | Un municipio como GeoJSON Feature |
| GET | `/api/v1/shared/municipios/geom` | Todos con geometría WKT |
| GET | `/api/v1/shared/municipios/{id}/geom` | Un municipio con geometría WKT |
| GET | `/api/v1/shared/municipios/ubicacion?lat=-16.49&lon=-68.12` | Identificar municipio por coordenada |

---

## 1. GeoJSON (RFC 7946)

```bash
curl http://localhost:8000/api/v1/shared/municipios/geojson
```

Respuesta:

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

---

## 2. WKT (Well-Known Text)

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

Si no encuentra municipio:

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

### Leaflet

```javascript
fetch('/api/v1/shared/municipios/geojson')
  .then(r => r.json())
  .then(data => {
    L.geoJSON(data, {
      style: { color: '#3388ff', weight: 1, fillOpacity: 0.3 },
      onEachFeature: (feature, layer) => layer.bindPopup(feature.properties.nombre)
    }).addTo(map);
  });
```

### OpenLayers

```javascript
const vectorSource = new ol.source.Vector({
  url: '/api/v1/shared/municipios/geojson',
  format: new ol.format.GeoJSON()
});
```

### Google Maps

```javascript
fetch('/api/v1/shared/municipios/geojson')
  .then(r => r.json())
  .then(data => {
    data.features.forEach(feature => {
      const dataLayer = new google.maps.Data();
      dataLayer.addGeoJson(feature);
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
```

### QGIS

Capa > Añadir capa > Añadir capa vectorial > Protocolo > GeoJSON  
URL: `http://localhost:8000/api/v1/shared/municipios/geojson`

### Python (GeoPandas)

```python
import geopandas as gpd
gdf = gpd.read_file('http://localhost:8000/api/v1/shared/municipios/geojson')
```

### SQL directo con PostGIS

```sql
-- Municipio por coordenada
SELECT m.codigo_ine, m.nombre
FROM shared.municipio m
WHERE ST_Contains(m.geom, ST_SetSRID(ST_Point(-68.1193, -16.4897), 4326));

-- Distancia entre municipios (metros)
SELECT ST_Distance(
  (SELECT geom FROM shared.municipio WHERE id = 20101)::geography,
  (SELECT geom FROM shared.municipio WHERE id = 70201)::geography
);

-- Área (km²)
SELECT ST_Area(geom::geography) / 1000000 as area_km2
FROM shared.municipio WHERE id = 20101;
```
