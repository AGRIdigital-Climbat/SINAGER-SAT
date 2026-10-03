from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator


# ============================================================================
#  CATÁLOGOS - CATEGORÍAS
# ============================================================================

class CatCategoriaAyudaBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)
    descripcion: str | None = None
    activo: bool = True


class CatCategoriaAyudaCreate(CatCategoriaAyudaBase):
    codigo: str | None = Field(None, max_length=30, description="Se autogenera si no se envía")


class CatCategoriaAyudaUpdate(BaseModel):
    nombre: str | None = Field(None, min_length=1, max_length=100)
    descripcion: str | None = None
    activo: bool | None = None


class CatCategoriaAyudaResponse(BaseModel):
    id_categoria_ayuda: int
    codigo: str
    nombre: str
    descripcion: str | None
    activo: bool
    n_articulos: int = 0


class CatCategoriaAyudaDetailResponse(CatCategoriaAyudaResponse):
    articulos: list["CatArticuloResponse"] = []


# ============================================================================
#  CATÁLOGOS - ARTÍCULOS
# ============================================================================

class CatArticuloBase(BaseModel):
    id_categoria_ayuda: int = Field(..., description="Categoría a la que pertenece")
    nombre: str = Field(..., min_length=1, max_length=150)
    peso_unitario_kg: Decimal | None = Field(None, ge=0)
    costo_referencia_bs: Decimal | None = Field(None, ge=0)
    activo: bool = True


class CatArticuloCreate(CatArticuloBase):
    codigo: str | None = Field(None, max_length=30, description="Se autogenera si no se envía")


class CatArticuloUpdate(BaseModel):
    id_categoria_ayuda: int | None = None
    nombre: str | None = Field(None, min_length=1, max_length=150)
    peso_unitario_kg: Decimal | None = Field(None, ge=0)
    costo_referencia_bs: Decimal | None = Field(None, ge=0)
    activo: bool | None = None


class CatArticuloResponse(BaseModel):
    id_articulo: int
    id_categoria_ayuda: int
    categoria_nombre: str | None
    codigo: str
    nombre: str
    unidad_de_medida: str | None
    peso_unitario_kg: Decimal | None
    costo_referencia_bs: Decimal | None
    activo: bool


# ============================================================================
#  NECESIDADES
# ============================================================================

class NecesidadBase(BaseModel):
    id_articulo: int = Field(..., description="Artículo requerido")
    id_categoria_ayuda: int = Field(..., description="Categoría (debe coincidir con el artículo)")
    cantidad: Decimal = Field(..., gt=0, description="Cantidad requerida (debe ser > 0)")
    prioridad: int = Field(3, ge=1, le=3, description="1=Alta, 2=Media, 3=Baja")
    estado: bool = Field(False, description="False=pendiente, True=completada")
    id_familia: int | None = Field(None, description="Familia beneficiaria (opcional si es del formulario)")

    @field_validator('prioridad')
    @classmethod
    def validar_prioridad(cls, v):
        if v not in (1, 2, 3):
            raise ValueError('La prioridad debe ser 1, 2 o 3')
        return v


class NecesidadCreate(NecesidadBase):
    id_necesidad_off: str | None = Field(None, description="ID único offline para sincronización")
    id_formulario: int | None = Field(None, description="Obligatorio si no viene en la ruta")


class NecesidadUpdate(BaseModel):
    id_articulo: int | None = None
    id_categoria_ayuda: int | None = None
    cantidad: Decimal | None = Field(None, gt=0)
    prioridad: int | None = Field(None, ge=1, le=3)
    estado: bool | None = None
    id_familia: int | None = None


class NecesidadResponse(BaseModel):
    id_necesidad: int
    id_familia: int | None
    id_formulario: int
    id_necesidad_off: str | None
    id_articulo: int
    articulo_nombre: str | None
    articulo_codigo: str | None
    id_categoria_ayuda: int
    categoria_nombre: str | None
    unidad_de_medida: str | None  # Se toma del artículo (solo lectura)
    cantidad: Decimal
    prioridad: int
    estado: bool
    fecha_creacion: datetime | None
    fecha_modificacion: datetime | None


# ============================================================================
#  SYNC
# ============================================================================

class NecesidadSyncIn(BaseModel):
    id_necesidad_off: str | None = None
    id_familia_off: str | None = None
    id_articulo: int | None = None
    id_categoria_ayuda: int | None = None
    cantidad: Decimal | None = None
    prioridad: int | None = 3
    estado: bool | None = False


class SyncNecesidadesIn(BaseModel):
    necesidades: list[NecesidadSyncIn] = []


class SyncNecesidadesOut(BaseModel):
    necesidades: list[dict] = []
    errores: list[dict] = []
