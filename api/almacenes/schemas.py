from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


# === ALMACENES ===
class AlmacenBase(BaseModel):
    codigo: Optional[str] = None
    nombre: str
    descripcion: Optional[str] = None
    nivel: Literal["municipal", "departamental", "nacional"]
    id_municipio: Optional[int] = None
    id_departamento: Optional[int] = None
    direccion: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    capacidad_m2: Optional[float] = None
    estado: Literal["ACTIVO", "INACTIVO", "MANTENIMIENTO"] = "ACTIVO"
    id_responsable_operativo: Optional[int] = None


class AlmacenCreate(AlmacenBase):
    pass


class AlmacenUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    nivel: Optional[Literal["municipal", "departamental", "nacional"]] = None
    id_municipio: Optional[int] = None
    id_departamento: Optional[int] = None
    direccion: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    capacidad_m2: Optional[float] = None
    estado: Optional[Literal["ACTIVO", "INACTIVO", "MANTENIMIENTO"]] = None
    id_responsable_operativo: Optional[int] = None


class AlmacenResponse(AlmacenBase):
    id_almacen: int
    creado_por: Optional[int] = None
    fecha_creacion: Optional[datetime] = None
    fecha_modificacion: Optional[datetime] = None

    class Config:
        from_attributes = True


# === SOLICITUDES DE SALIDA ===
class AlmacenSolicitudDetalleCreate(BaseModel):
    id_articulo: int
    cantidad_solicitada: float = Field(gt=0)
    observaciones: Optional[str] = None


class AlmacenSolicitudCreate(BaseModel):
    id_solicitud: Optional[int] = None
    tipo: Literal["DESPACHO", "MERMA", "VENCIMIENTO", "OTRO"] = "DESPACHO"
    motivo: str
    id_municipio: Optional[int] = None
    id_departamento: Optional[int] = None
    observaciones: Optional[str] = None
    detalle: list[AlmacenSolicitudDetalleCreate]


class AlmacenSolicitudAprobar(BaseModel):
    motivo_justificacion: Optional[str] = None
    detalle_aprobado: Optional[list[dict]] = None


class AlmacenSolicitudRechazar(BaseModel):
    motivo_rechazo: str = Field(min_length=10)


# === NEA ===
class NEADetalleCreate(BaseModel):
    id_articulo: int
    cantidad: float = Field(gt=0)
    lote: Optional[str] = None
    fecha_vencimiento: Optional[date] = None
    valor_unitario_bs: Optional[float] = 0
    valor_total_bs: Optional[float] = 0


class NEACreate(BaseModel):
    tipo: Literal["CARGA_INICIAL", "DONACION", "COMPRA", "DEVOLUCION", "AJUSTE", "OTRO"]
    proveedor_donante: Optional[str] = None
    id_documento_soporte: Optional[int] = None
    fecha_entrada: date
    hora_entrada: Optional[str] = None
    observaciones: Optional[str] = None
    detalle: list[NEADetalleCreate]


# === PECOSA ===
class PECOSADetalleCreate(BaseModel):
    id_articulo: int
    cantidad: float = Field(gt=0)
    lote: Optional[str] = None
    fecha_vencimiento: Optional[date] = None


class PECOSACreate(BaseModel):
    id_solicitud: Optional[int] = None
    id_solicitud_salida: Optional[int] = None
    fecha_salida: date
    nombre_quien_recibe: str
    motivo: Optional[str] = None
    observaciones: Optional[str] = None
    detalle: list[PECOSADetalleCreate]


# === ENTREGA A BENEFICIARIOS ===
class EntregaBeneficiarioDetalleCreate(BaseModel):
    id_articulo: int
    cantidad: float = Field(gt=0)
    lote: Optional[str] = None
    fecha_vencimiento: Optional[date] = None


class EntregaBeneficiarioCreate(BaseModel):
    id_familia: int
    codigo_familia: str
    ci_jefe_familia: str
    nombre_jefe_familia: str
    metodo_verificacion: str
    id_usuario_entrega: Optional[int] = None
    fecha_hora_entrega: Optional[datetime] = None
    id_acta_entrega: int
    id_documento_lista_firmada: Optional[int] = None
    testigo_nombre: Optional[str] = None
    testigo_ci: Optional[str] = None
    parentesco: Optional[str] = None
    tipo_documento: str = "CI"
    observaciones: Optional[str] = None
    detalle: list[EntregaBeneficiarioDetalleCreate]
