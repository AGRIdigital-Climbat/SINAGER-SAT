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
#  CATÁLOGOS - UNIDADES DE MEDIDA
# ============================================================================

class CatUnidadMedidaCreate(BaseModel):
    codigo: str | None = Field(None, max_length=20,
                               description="Minúscula; se autoderiva del nombre si no se envía")
    nombre: str = Field(..., min_length=1, max_length=50)
    activo: bool = True


class CatUnidadMedidaUpdate(BaseModel):
    codigo: str | None = Field(None, max_length=20)
    nombre: str | None = Field(None, min_length=1, max_length=50)
    activo: bool | None = None


class CatUnidadMedidaResponse(BaseModel):
    id_unidad_medida: int
    codigo: str
    nombre: str
    activo: bool
    n_articulos: int = 0


# ============================================================================
#  CATÁLOGOS - ARTÍCULOS
# ============================================================================

class CatArticuloBase(BaseModel):
    id_categoria_ayuda: int = Field(..., description="Categoría a la que pertenece")
    nombre: str = Field(..., min_length=1, max_length=150)
    unidad_de_medida: str | None = Field(None, max_length=20,
                                         description="Código de rida.cat_unidad_medida (default 'unidad')")
    peso_unitario_kg: Decimal | None = Field(None, ge=0)
    costo_referencia_bs: Decimal | None = Field(None, ge=0)
    activo: bool = True


class CatArticuloCreate(CatArticuloBase):
    codigo: str | None = Field(None, max_length=30, description="Se autogenera si no se envía")


class CatArticuloUpdate(BaseModel):
    id_categoria_ayuda: int | None = None
    nombre: str | None = Field(None, min_length=1, max_length=150)
    unidad_de_medida: str | None = Field(None, max_length=20,
                                         description="Código de rida.cat_unidad_medida")
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
    unidad_nombre: str | None = None
    peso_unitario_kg: Decimal | None
    costo_referencia_bs: Decimal | None
    activo: bool


# ============================================================================
#  NECESIDADES
# ============================================================================

class NecesidadBase(BaseModel):
    id_articulo: int | None = Field(None, description="Artículo requerido (opcional)")
    id_categoria_ayuda: int = Field(..., description="Categoría (obligatoria)")
    cantidad: Decimal | None = Field(None, ge=0, description="Cantidad requerida (opcional; NULL si no se registra)")
    prioridad: int = Field(3, ge=1, le=3, description="1=Alta, 2=Media, 3=Baja")
    estado: bool = Field(False, description="False=pendiente, True=completada")
    id_familia: int | None = Field(None, description="Familia beneficiaria (OBLIGATORIO: la necesidad pertenece a una familia; el formulario se deriva de ella)")

    @field_validator('prioridad')
    @classmethod
    def validar_prioridad(cls, v):
        if v not in (1, 2, 3):
            raise ValueError('La prioridad debe ser 1, 2 o 3')
        return v


class NecesidadCreate(NecesidadBase):
    id_necesidad_off: str | None = Field(None, description="ID único offline para sincronización")
    id_formulario: int | None = Field(None, description="Solo validación: si se envía, la familia debe pertenecer a este formulario (no se persiste)")


class NecesidadUpdate(BaseModel):
    id_articulo: int | None = None
    id_categoria_ayuda: int | None = None
    cantidad: Decimal | None = Field(None, ge=0)
    prioridad: int | None = Field(None, ge=1, le=3)
    estado: bool | None = None
    id_familia: int | None = None


class NecesidadResponse(BaseModel):
    id_necesidad: int
    id_familia: int | None
    id_formulario: int | None = Field(None, description="Derivado de familia.id_formulario (no es columna propia)")
    id_necesidad_off: str | None
    id_articulo: int | None = None
    articulo_nombre: str | None = None
    articulo_codigo: str | None = None
    id_categoria_ayuda: int
    categoria_nombre: str | None = None
    unidad_de_medida: str | None = None
    cantidad: Decimal | None = None
    prioridad: int
    estado: bool
    fuente: str = Field("manual", description="manual | motor")
    id_regla: int | None = Field(None, description="Regla de necesidad que la generó (motor)")
    id_edan_localidad: int | None = Field(None, description="Derivado de la familia: localidad de empadronamiento")
    localidad_nombre: str | None = None
    id_tipo_localidad: int | None = None
    tipo_localidad_nombre: str | None = None
    fecha_creacion: datetime | None
    fecha_modificacion: datetime | None


# ============================================================================
#  SYNC
# ============================================================================

class NecesidadSyncIn(BaseModel):
    id_necesidad_off: str | None = None
    id_formulario: int | None = None
    id_familia: int | None = None
    id_familia_off: str | None = None
    id_articulo: int | None = None
    id_categoria_ayuda: int | None = None
    cantidad: Decimal | None = Field(None, ge=0)
    prioridad: int | None = 3
    estado: bool | None = False


class SyncNecesidadesIn(BaseModel):
    necesidades: list[NecesidadSyncIn] = []


class SyncNecesidadesOut(BaseModel):
    necesidades: list[dict] = []
    errores: list[dict] = []


# ============================================================================
#  CATÁLOGOS - REHABILITACIÓN (NUEVO)
# ============================================================================

class CatTipoRehabilitacionBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=150)
    descripcion: str | None = None
    id_modalidad: int | None = Field(None, description="3=Rehabilitación-Insumos, 4=Rehabilitación-Reconstrucción")
    activo: bool = True


class CatTipoRehabilitacionCreate(CatTipoRehabilitacionBase):
    codigo: str | None = Field(None, max_length=50, description="Se autogenera si no se envía")


class CatTipoRehabilitacionUpdate(BaseModel):
    nombre: str | None = Field(None, min_length=1, max_length=150)
    descripcion: str | None = None
    id_modalidad: int | None = None
    activo: bool | None = None


class CatTipoRehabilitacionResponse(BaseModel):
    id_tipo_rehabilitacion: int
    codigo: str
    nombre: str
    descripcion: str | None
    id_modalidad: int | None
    modalidad_nombre: str | None
    activo: bool
    n_insumos: int = 0


class CatTipoRehabilitacionDetailResponse(CatTipoRehabilitacionResponse):
    insumos: list["CatInsumoRehabilitacionResponse"] = []


class CatInsumoRehabilitacionBase(BaseModel):
    id_tipo_rehabilitacion: int = Field(..., description="Tipo de rehabilitación al que pertenece")
    nombre: str = Field(..., min_length=1, max_length=150)
    unidad_de_medida: str = Field('unidad', max_length=20, description="unidad, m2, metro_lineal, dia, etc.")
    costo_referencia_bs: Decimal | None = Field(None, ge=0)
    activo: bool = True


class CatInsumoRehabilitacionCreate(CatInsumoRehabilitacionBase):
    codigo: str | None = Field(None, max_length=30, description="Se autogenera si no se envía")


class CatInsumoRehabilitacionUpdate(BaseModel):
    id_tipo_rehabilitacion: int | None = None
    nombre: str | None = Field(None, min_length=1, max_length=150)
    unidad_de_medida: str | None = None
    costo_referencia_bs: Decimal | None = Field(None, ge=0)
    activo: bool | None = None


class CatInsumoRehabilitacionResponse(BaseModel):
    id_insumo: int
    id_tipo_rehabilitacion: int
    tipo_nombre: str | None
    codigo: str
    nombre: str
    unidad_de_medida: str | None
    costo_referencia_bs: Decimal | None
    activo: bool


class NecesidadRehabilitacionCreate(BaseModel):
    """Crear necesidad de rehabilitación (en lugar de artículo de ayuda humanitaria)"""
    id_tipo_rehabilitacion: int = Field(..., description="Tipo de rehabilitación")
    id_insumo: int = Field(..., description="Insumo de rehabilitación requerido")
    cantidad: Decimal = Field(..., gt=0, description="Cantidad requerida")
    prioridad: int = Field(3, ge=1, le=3, description="1=Alta, 2=Media, 3=Baja")
    estado: bool = Field(False, description="False=pendiente, True=completada")
    id_familia: int | None = Field(None, description="Familia beneficiaria (OBLIGATORIO)")
    id_necesidad_off: str | None = Field(None, description="ID único offline")
    id_formulario: int | None = Field(None, description="Solo validación: si se envía, la familia debe pertenecer a este formulario (no se persiste)")
    
    @field_validator('prioridad')
    @classmethod
    def validar_prioridad(cls, v):
        if v not in (1, 2, 3):
            raise ValueError('La prioridad debe ser 1, 2 o 3')
        return v
