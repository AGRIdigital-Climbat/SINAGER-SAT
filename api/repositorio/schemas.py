from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date


# ============================================================================
#  CATÁLOGO: repositorio.tipo_documento
# ============================================================================

class TipoDocumentoCreate(BaseModel):
    """→ repositorio.tipo_documento."""
    codigo: str = Field(..., max_length=50, description="Código único. Ej: 'informe_legal', 'resolucion_alcaldicia'")
    nombre: str = Field(..., max_length=100, description="Nombre legible. Ej: 'Informe Legal'")
    descripcion: Optional[str] = Field(None, description="Descripción larga del tipo de documento")
    orden: int = Field(0, ge=0, description="Orden de presentación en listados")
    activo: bool = Field(True, description="Si FALSE, no aparece en catálogos activos")
    requiere_versionado: bool = Field(False, description="Si TRUE, cada nueva versión genera una fila (futuro)")
    extensiones_permitidas: Optional[str] = Field('pdf', description="CSV extensiones permitidas. Default: 'pdf'")
    tamano_maximo_bytes: Optional[int] = Field(52428800, ge=1, description="Tamaño máximo en bytes. Default: 50MB")


class TipoDocumentoUpdate(BaseModel):
    codigo: Optional[str] = Field(None, max_length=50)
    nombre: Optional[str] = Field(None, max_length=100)
    descripcion: Optional[str] = None
    orden: Optional[int] = Field(None, ge=0)
    activo: Optional[bool] = None
    requiere_versionado: Optional[bool] = None
    extensiones_permitidas: Optional[str] = None
    tamano_maximo_bytes: Optional[int] = Field(None, ge=1)


class TipoDocumentoResponse(BaseModel):
    """→ repositorio.tipo_documento (catálogo completo)."""
    id_tipo_documento: int
    codigo: str
    nombre: str
    descripcion: Optional[str] = None
    orden: int
    activo: bool
    requiere_versionado: Optional[bool] = None
    extensiones_permitidas: Optional[str] = None
    tamano_maximo_bytes: Optional[int] = None

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
    # Ambos pueden venir NULL segun el origen: un documento de EDAN no tiene
    # evento RIDA, y uno de RIDA siempre hereda su EDAN del evento.
    id_edan: Optional[int] = None
    id_evento_rida: Optional[int] = None
    # Derivado en SQL: 'edan' si id_evento_rida es NULL, 'rida' si no.
    origen: Optional[str] = None
    # Derivados de resultado_firma: cuantas firmas tiene y si se pudo validar.
    cantidad_firmas: int = 0
    firma_validada: bool = False
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
    tiene_firma_digital: Optional[bool] = False
    resultado_firma: Optional[dict] = None
    fecha_validacion_firma: Optional[datetime] = None
    tipo_codigo: Optional[str] = None
    tipo_nombre: Optional[str] = None

    class Config:
        from_attributes = True
