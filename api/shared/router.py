from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from ..database import get_db
from ..auth.permisos import permiso_required
from ..response import SuccessResponse, MessageResponse
from .schemas import (
    DepartamentoCreate, DepartamentoUpdate, DepartamentoResponse,
    ProvinciaCreate, ProvinciaUpdate, ProvinciaResponse,
    MunicipioCreate, MunicipioUpdate, MunicipioResponse,
)
from . import service

router = APIRouter(prefix="/shared")

TAG = "Geografía > Departamentos"


@router.get("/departamentos", response_model=SuccessResponse, tags=[TAG])
def listar_departamentos(db: Session = Depends(get_db)):
    items = service.get_departamentos(db)
    return SuccessResponse(message="Operación exitosa", data=items, total=len(items))


@router.get("/departamentos/{id}", response_model=SuccessResponse, tags=[TAG])
def obtener_departamento(id: int, db: Session = Depends(get_db)):
    result = service.get_departamento(db, id)
    if not result:
        raise HTTPException(status_code=404, detail="Departamento no encontrado")
    return SuccessResponse(message="Operación exitosa", data=result)


@router.post("/departamentos", response_model=SuccessResponse, status_code=201, tags=[TAG])
def crear_departamento(data: DepartamentoCreate, db: Session = Depends(get_db), _ua=Depends(permiso_required("SISTEMA", "CREATE"))):
    try:
        id = service.create_departamento(db, data)
        result = service.get_departamento(db, id)
        return SuccessResponse(message="Departamento creado exitosamente", data=result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/departamentos/{id}", response_model=SuccessResponse, tags=[TAG])
def actualizar_departamento(id: int, data: DepartamentoUpdate, db: Session = Depends(get_db), _ua=Depends(permiso_required("SISTEMA", "UPDATE"))):
    result = service.update_departamento(db, id, data)
    if not result:
        raise HTTPException(status_code=404, detail="Departamento no encontrado")
    return SuccessResponse(message="Departamento actualizado exitosamente", data=result)


@router.delete("/departamentos/{id}", response_model=SuccessResponse, tags=[TAG])
def eliminar_departamento(id: int, db: Session = Depends(get_db), _ua=Depends(permiso_required("SISTEMA", "DELETE"))):
    if not service.delete_departamento(db, id):
        raise HTTPException(status_code=404, detail="Departamento no encontrado")
    return SuccessResponse(message="Departamento eliminado")


TAG = "Geografía > Provincias"


@router.get("/provincias", response_model=SuccessResponse, tags=[TAG])
def listar_provincias(
    id_departamento: int | None = Query(None),
    db: Session = Depends(get_db),
):
    items = service.get_provincias(db, id_departamento)
    return SuccessResponse(message="Operación exitosa", data=items, total=len(items))


@router.get("/provincias/{id}", response_model=SuccessResponse, tags=[TAG])
def obtener_provincia(id: int, db: Session = Depends(get_db)):
    result = service.get_provincia(db, id)
    if not result:
        raise HTTPException(status_code=404, detail="Provincia no encontrada")
    return SuccessResponse(message="Operación exitosa", data=result)


@router.post("/provincias", response_model=SuccessResponse, status_code=201, tags=[TAG])
def crear_provincia(data: ProvinciaCreate, db: Session = Depends(get_db), _ua=Depends(permiso_required("SISTEMA", "CREATE"))):
    try:
        id = service.create_provincia(db, data)
        result = service.get_provincia(db, id)
        return SuccessResponse(message="Provincia creada exitosamente", data=result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/provincias/{id}", response_model=SuccessResponse, tags=[TAG])
def actualizar_provincia(id: int, data: ProvinciaUpdate, db: Session = Depends(get_db), _ua=Depends(permiso_required("SISTEMA", "UPDATE"))):
    result = service.update_provincia(db, id, data)
    if not result:
        raise HTTPException(status_code=404, detail="Provincia no encontrada")
    return SuccessResponse(message="Provincia actualizada exitosamente", data=result)


@router.delete("/provincias/{id}", response_model=SuccessResponse, tags=[TAG])
def eliminar_provincia(id: int, db: Session = Depends(get_db), _ua=Depends(permiso_required("SISTEMA", "DELETE"))):
    if not service.delete_provincia(db, id):
        raise HTTPException(status_code=404, detail="Provincia no encontrada")
    return SuccessResponse(message="Provincia eliminada")


TAG = "Geografía > Municipios"

# ── IMPORTANTE: Rutas estáticas ANTES de /{id} para evitar conflicto de routing ──

TAG_GEOJSON = "Geografía > GeoJSON"
TAG_GEOM = "Geografía > GEOM/WKT"
TAG_UBICACION = "Geografía > Ubicación"


# ── GEOJSON (RFC 7946) ── compatible con Leaflet, OpenLayers, Google Maps, QGIS, Mapbox, kepler.gl

@router.get("/municipios/geojson", tags=[TAG_GEOJSON],
            summary="Municipios en formato GeoJSON (FeatureCollection)",
            response_class=JSONResponse)
def listar_municipios_geojson(
    id_provincia: int | None = Query(None, description="Filtrar por provincia"),
    id_departamento: int | None = Query(None, description="Filtrar por departamento"),
    db: Session = Depends(get_db),
):
    """
    Retorna todos los municipios en formato **GeoJSON FeatureCollection** (RFC 7946).

    Compatible con: **Leaflet**, **OpenLayers**, **Google Maps**, **Mapbox GL JS**,
    **QGIS**, **ArcGIS**, **kepler.gl**, **deck.gl**, **GeoServer**, **MapProxy**.

    Ejemplos de uso:
    - Leaflet: `L.geoJSON(data).addTo(map)`
    - OpenLayers: `new ol.layer.Vector({source: new ol.source.Vector({format: new ol.format.GeoJSON(), url: '...'})})`
    - QGIS: Capa > Añadir capa > Vector > Protocolo: GeoJSON > URL del endpoint
    - Google Maps: `data.features.forEach(f => new google.maps.Data().addGeoJson(f))`
    - Mapbox: `map.addSource('municipios', {type: 'geojson', data: url})`
    """
    data = service.get_municipios_geojson(db, id_provincia, id_departamento)
    return JSONResponse(content=data)


@router.get("/municipios/geom", tags=[TAG_GEOM],
            summary="Municipios con geometría en formato WKT (Well-Known Text)",
            response_class=JSONResponse)
def listar_municipios_geom(
    id_provincia: int | None = Query(None, description="Filtrar por provincia"),
    id_departamento: int | None = Query(None, description="Filtrar por departamento"),
    db: Session = Depends(get_db),
):
    """
    Retorna municipios con geometría en formato **WKT (Well-Known Text)**.

    Útil para: debug, consultas SQL directas, sistemas internos,
    herramientas que parsean WKT (PostGIS, Shapely, GEOS).

    Ejemplo WKT: `MULTIPOLYGON(((-68.12 -16.49, -68.11 -16.48, ...)))`
    """
    items = service.get_municipios_geom(db, id_provincia, id_departamento)
    return JSONResponse(content={
        "type": "GeometryCollection",
        "geometries": items,
        "total": len(items),
    })


@router.get("/municipios/ubicacion", tags=[TAG_UBICACION],
            summary="Identificar municipio para un punto (lat, lon)",
            response_class=JSONResponse)
def obtener_ubicacion(
    lat: float = Query(..., description="Latitud (ej: -16.4897)"),
    lon: float = Query(..., description="Longitud (ej: -68.1193)"),
    db: Session = Depends(get_db),
):
    """
    Dada una coordenada **(lat, lon)**, retorna el municipio, provincia y departamento
    que contienen ese punto usando `ST_Contains`.

    Compatible con GPS, formularios REA/EDAN, geolocalización de reportes.

    Ejemplo: `GET /api/v1/shared/municipios/ubicacion?lat=-16.4897&lon=-68.1193`
    """
    result = service.obtener_ubicacion(db, lat, lon)
    if not result:
        return JSONResponse(
            status_code=404,
            content={
                "lat": lat,
                "lon": lon,
                "municipio": None,
                "provincia": None,
                "departamento": None,
                "message": "No se encontró municipio para estas coordenadas",
            },
        )
    return JSONResponse(content=result)


# ── CRUD Municipios (rutas con /{id} DEBEN ir DESPUÉS de las rutas estáticas) ──

@router.get("/municipios", response_model=SuccessResponse, tags=[TAG])
def listar_municipios(
    id_provincia: int | None = Query(None),
    id_departamento: int | None = Query(None),
    db: Session = Depends(get_db),
):
    items = service.get_municipios(db, id_provincia, id_departamento)
    return SuccessResponse(message="Operación exitosa", data=items, total=len(items))


@router.get("/municipios/{id}", response_model=SuccessResponse, tags=[TAG])
def obtener_municipio(id: int, db: Session = Depends(get_db)):
    result = service.get_municipio(db, id)
    if not result:
        raise HTTPException(status_code=404, detail="Municipio no encontrado")
    return SuccessResponse(message="Operación exitosa", data=result)


@router.post("/municipios", response_model=SuccessResponse, status_code=201, tags=[TAG])
def crear_municipio(data: MunicipioCreate, db: Session = Depends(get_db), _ua=Depends(permiso_required("SISTEMA", "CREATE"))):
    try:
        id = service.create_municipio(db, data)
        result = service.get_municipio(db, id)
        return SuccessResponse(message="Municipio creado exitosamente", data=result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/municipios/{id}", response_model=SuccessResponse, tags=[TAG])
def actualizar_municipio(id: int, data: MunicipioUpdate, db: Session = Depends(get_db), _ua=Depends(permiso_required("SISTEMA", "UPDATE"))):
    result = service.update_municipio(db, id, data)
    if not result:
        raise HTTPException(status_code=404, detail="Municipio no encontrado")
    return SuccessResponse(message="Municipio actualizado exitosamente", data=result)


@router.delete("/municipios/{id}", response_model=SuccessResponse, tags=[TAG])
def eliminar_municipio(id: int, db: Session = Depends(get_db), _ua=Depends(permiso_required("SISTEMA", "DELETE"))):
    if not service.delete_municipio(db, id):
        raise HTTPException(status_code=404, detail="Municipio no encontrado")
    return SuccessResponse(message="Municipio eliminado")


# ── GEOJSON por ID (después de /{id} porque incluye geojson en el path) ──

@router.get("/municipios/{id}/geojson", tags=[TAG_GEOJSON],
            summary="Un municipio en formato GeoJSON (Feature)",
            response_class=JSONResponse)
def obtener_municipio_geojson(id: int, db: Session = Depends(get_db)):
    """
    Retorna un municipio individual en formato **GeoJSON Feature** (RFC 7946).
    Incluye bounding box para facilitar el zoom en el mapa.
    """
    result = service.get_municipio_geojson(db, id)
    if not result:
        raise HTTPException(status_code=404, detail="Municipio no encontrado")
    return JSONResponse(content=result)


@router.get("/municipios/{id}/geom", tags=[TAG_GEOM],
            summary="Un municipio con geometría en formato WKT",
            response_class=JSONResponse)
def obtener_municipio_geom(id: int, db: Session = Depends(get_db)):
    """
    Retorna un municipio individual con geometría en formato **WKT**.
    """
    result = service.get_municipio_geom(db, id)
    if not result:
        raise HTTPException(status_code=404, detail="Municipio no encontrado")
    return JSONResponse(content=result)
