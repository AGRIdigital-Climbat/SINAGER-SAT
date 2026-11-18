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
    observaciones: Optional[str] = Field(None, description="Texto libre (opcional)")
    activo: Optional[bool] = None
    codigo_documento: Optional[str] = Field(
        None, max_length=64,
        description="Clave de agrupación/expediente (DOC_PRECEDENTE). Se normaliza a MAYÚSCULAS.")


class DocumentoResponse(BaseModel):
    id_documento: int
    # Vínculos según origen: EDAN/RIDA pueden tener id_edan/id_evento_rida;
    # DOC_PRECEDENTE (respaldo municipal) no tiene ninguno.
    id_edan: Optional[int] = None
    id_evento_rida: Optional[int] = None
    # Origen explícito (asignado por la ruta de subida): EDAN, RIDA, DOC_PRECEDENTE.
    origen: Optional[str] = None
    # Clave de agrupación/rastreo de DOC_PRECEDENTE (null en EDAN/RIDA).
    codigo_documento: Optional[str] = None
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


# ============================================================================
#  GRUPOS / EXPEDIENTES (GET /repositorio/documentos, modo=agrupado)
# ============================================================================

class DocumentoCopiaResponse(BaseModel):
    """Documento gemelo (mismo hash_sha256) localizado en otro grupo."""
    id_documento: int
    nombre_documento: Optional[str] = None
    hash_sha256: Optional[str] = Field(
        None, description="Primeros 16 caracteres del SHA-256 (coincidencia exacta)")

    class Config:
        from_attributes = True


class GrupoCoincidenciaResponse(BaseModel):
    """Grupo hermano con el que se comparten documentos idénticos por hash."""
    tipo: str = Field(..., description="EDAN | RIDA | DOC_PRECEDENTE")
    clave: str = Field(..., description="Codigo real del grupo: codigo_edan, "
                       "codigo de evento RIDA o codigo_documento")
    documentos_comunes: int
    documentos: list[DocumentoCopiaResponse] = []

    class Config:
        from_attributes = True


class DocumentoGrupoResponse(BaseModel):
    """Fila de GET /repositorio/documentos?modo=agrupado (un grupo/expediente)."""
    tipo: str = Field(..., description="EDAN (por id_edan) | RIDA (por id_evento_rida, "
                        "aunque herede id_edan) | DOC_PRECEDENTE (por codigo_documento)")
    clave: str = Field(..., description="Codigo real del grupo: `codigo_edan` "
                       "(EDAN), `rida.evento_rida.codigo` (RIDA, p. ej. "
                       "070101/2026/003-R) o `codigo_documento` (DOC_PRECEDENTE, "
                       "tal cual se puso). Fallback ED-<id>/EV-<id>/DOC-<id> solo "
                       "si el padre no tuviera codigo")
    id_edan: Optional[int] = Field(None, description="EDAN del grupo (EDAN y, heredado, RIDA)")
    id_evento_rida: Optional[int] = None
    codigo_documento: Optional[str] = None
    id_departamento: Optional[int] = None
    id_provincia: Optional[int] = None
    id_municipio: Optional[int] = None
    total_documentos: int
    fecha_documento_max: Optional[date] = None
    fecha_subida_max: Optional[datetime] = None
    documentos_compartidos: int = Field(
        0, description="Docs del grupo cuyo hash exacto aparece en OTRO grupo "
        "(copias dentro del mismo grupo no cuentan)")
    comparte_con: list[GrupoCoincidenciaResponse] = Field(
        default_factory=list, description="Grupos hermanos con copia identica por hash")

    class Config:
        from_attributes = True
