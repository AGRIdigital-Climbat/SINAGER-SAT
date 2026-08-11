from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date


# ============================================================================
#  CATÁLOGO: repositorio.tipo_documento
# ============================================================================

class TipoDocumentoCreate(BaseModel):
    codigo: str = Field(..., max_length=50)
    nombre: str = Field(..., max_length=100)
    descripcion: Optional[str] = None
    orden: int = 0
    activo: bool = True


class TipoDocumentoUpdate(BaseModel):
    codigo: Optional[str] = None
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    orden: Optional[int] = None
    activo: Optional[bool] = None


class TipoDocumentoResponse(BaseModel):
    id_tipo_documento: int
    codigo: str
    nombre: str
    descripcion: Optional[str] = None
    orden: int
    activo: bool

    class Config:
        from_attributes = True


# ============================================================================
#  DOCUMENTOS: repositorio.documentos
# ============================================================================

class DocumentoCreate(BaseModel):
    id_tipo_documento: int
    id_departamento: int
    id_provincia: int
    id_municipio: int
    fecha_documento: date
    nombre_documento: str = Field(..., max_length=255)
    observaciones: Optional[str] = None


class DocumentoUpdate(BaseModel):
    observaciones: Optional[str] = None
    activo: Optional[bool] = None


class DocumentoResponse(BaseModel):
    id_documento: int
    id_edan: int
    id_tipo_documento: int
    nombre_original: str
    path_archivo: str
    tamano_bytes: int
    hash_sha256: Optional[str] = None
    id_usuario_subio: int
    id_municipio: Optional[int] = None
    id_departamento: Optional[int] = None
    id_provincia: Optional[int] = None
    fecha_documento: Optional[date] = None
    nombre_documento: Optional[str] = None
    fecha_subida: datetime
    activo: bool
    observaciones: Optional[str] = None

    class Config:
        from_attributes = True
