from pydantic import BaseModel
from typing import Any


class DepartamentoCreate(BaseModel):
    codigo_ine: str
    nombre: str


class DepartamentoUpdate(BaseModel):
    codigo_ine: str | None = None
    nombre: str | None = None


class DepartamentoResponse(BaseModel):
    id: int
    codigo_ine: str
    nombre: str

    class Config:
        from_attributes = True


class ProvinciaCreate(BaseModel):
    codigo_ine: str
    id_departamento: int
    nombre: str


class ProvinciaUpdate(BaseModel):
    codigo_ine: str | None = None
    id_departamento: int | None = None
    nombre: str | None = None


class ProvinciaResponse(BaseModel):
    id: int
    codigo_ine: str
    id_departamento: int
    nombre: str
    departamento: DepartamentoResponse | None = None

    class Config:
        from_attributes = True


class MunicipioCreate(BaseModel):
    codigo_ine: str
    id_departamento: int
    id_provincia: int
    nombre: str


class MunicipioUpdate(BaseModel):
    codigo_ine: str | None = None
    id_departamento: int | None = None
    id_provincia: int | None = None
    nombre: str | None = None


class MunicipioResponse(BaseModel):
    id: int
    codigo_ine: str
    id_departamento: int
    id_provincia: int
    nombre: str
    departamento: DepartamentoResponse | None = None
    provincia: ProvinciaResponse | None = None

    class Config:
        from_attributes = True


# ── GeoJSON schemas (RFC 7946) ──


class GeoJSONGeometry(BaseModel):
    type: str
    coordinates: Any


class GeoJSONProperties(BaseModel):
    id: int
    codigo_ine: str
    nombre: str
    departamento: DepartamentoResponse | None = None
    provincia: ProvinciaResponse | None = None
    area_km2: float | None = None


class GeoJSONFeature(BaseModel):
    type: str = "Feature"
    geometry: GeoJSONGeometry
    properties: GeoJSONProperties
    bbox: list[float] | None = None


class GeoJSONFeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    name: str = "municipios_bolivia"
    crs: dict[str, Any] = {
        "type": "name",
        "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}
    }
    features: list[GeoJSONFeature]
    total: int
    bbox: list[float] | None = None


# ── GEOM/WKT schemas ──


class MunicipioGeomItem(BaseModel):
    id: int
    codigo_ine: str
    nombre: str
    geom_wkt: str
    srid: int = 4326
    departamento: DepartamentoResponse | None = None
    provincia: ProvinciaResponse | None = None


class MunicipioGeomResponse(BaseModel):
    type: str = "GeometryCollection"
    geometries: list[MunicipioGeomItem]
    total: int


# ── Ubicación (punto-dentro-de-polígono) ──


class UbicacionResponse(BaseModel):
    lat: float
    lon: float
    municipio: dict[str, Any] | None = None
    provincia: dict[str, Any] | None = None
    departamento: dict[str, Any] | None = None
