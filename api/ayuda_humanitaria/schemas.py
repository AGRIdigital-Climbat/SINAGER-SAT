from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# ============================================================================
#  Catalogos
# ============================================================================

class EstadoRidaResponse(BaseModel):
    id_estado_rida: int
    codigo: str
    nombre: str
    tono: str
    orden: int
    activo: bool


# ============================================================================
#  Expedientes (Work Queue)
# ============================================================================

class ExpedienteResponse(BaseModel):
    id_solicitud: int
    id_evento_rida: int
    codigo_rida: str | None = None
    etapa: str | None = None
    id_modalidad: int
    nombre_modalidad: str | None = None
    id_municipio: int | None = None
    nombre_municipio: str | None = None
    id_departamento: int | None = None
    nombre_departamento: str | None = None
    tipo_evento: str | None = None
    fecha_solicitud: datetime | None = None
    # Derivados del motor (regla 3): NUNCA almacenados
    estado: dict | None = None
    badge: str | None = None
    dias_en_estado: int | None = None
    id_usuario_asignado: int | None = None
    nombre_tecnico: str | None = None
    tiene_motor: bool = False
    motor_iniciado: bool = False


class ExpedienteDetalleResponse(ExpedienteResponse):
    aprobacion: dict | None = None
    evaluacion: dict | None = None
    articulos: list[dict] = []
    orden_despacho: dict | None = None
    acta_recepcion: dict | None = None
    documentos: list[dict] = []


# ============================================================================
#  Motor de aprobaciones (secuencial, 7 niveles)
# ============================================================================

class AprobacionesAyudaResponse(BaseModel):
    id_solicitud: int
    id_modalidad: int
    etapa: str | None = None
    cadena: list[str] = []
    estado_global: str | None = None
    badge: dict | None = None
    mi_nivel: str | None = None
    niveles: dict = {}
    aprobaciones: list[dict] = []


class AprobacionAyudaRequest(BaseModel):
    aprobado: bool
    observacion: str | None = Field(
        None, description="Obligatoria al devolver (min 10 caracteres)")


class EvaluacionCreate(BaseModel):
    id_usuario_tecnico: int | None = Field(
        None, description="Tecnico VIDECI a cargo. Default: el usuario del token")
    observaciones: str | None = None


# ============================================================================
#  Acciones de paso
# ============================================================================

class MotorCalculoRequest(BaseModel):
    forzar: bool = Field(
        False, description="true = recalcular tambien sobre filas fuente='manual'")


class ArticuloUpdate(BaseModel):
    cantidad: float | None = None
    aprobado: bool | None = None
    observaciones: str | None = None


class OrdenDespachoItem(BaseModel):
    id_articulo: int
    cantidad: float


class OrdenDespachoCreate(BaseModel):
    id_almacen: int | None = None
    serie: list[OrdenDespachoItem] | None = Field(
        None, description="Articulos a despachar -> rida.entrega_detalle")
    observaciones: str | None = None


class PrepararRequest(BaseModel):
    estado: str = Field(
        "PREPARADA", description="EN_PREPARACION | PREPARADA")


class DespacharRequest(BaseModel):
    transporte: str | None = None
    placa: str | None = None
    observaciones: str | None = None


class FirmaActa(BaseModel):
    nombre: str | None = None
    ci: str | None = None
    cargo: str | None = None
    fecha: str | None = None


class ActaRecepcionCreate(BaseModel):
    id_documento: int | None = Field(
        None, description="PDF del acta en repositorio.documentos")
    firmas: list[FirmaActa] | None = None
    observaciones: str | None = None


class TransicionAyudaRequest(BaseModel):
    observaciones: str | None = None


# ============================================================================
#  Reglas del motor de calculo por KITS (CRUD, §2.6)
# ============================================================================

CriterioAplicacion = Literal["POR_FAMILIA", "POR_INTEGRANTE", "POR_CONDICION_ESPECIAL"]
RedondeoRegla = Literal["ninguno", "techo", "piso"]
SexoRegla = Literal["M", "F"]


class DetalleParametroKitBase(BaseModel):
    id_articulo: int = Field(..., description="Artículo del catálogo que compone el kit")
    cantidad_base_diaria: Decimal = Field(
        ..., ge=0, max_digits=8, decimal_places=3,
        description="Ración del artículo POR PERSONA al día")
    cantidad_min: Decimal | None = Field(None, ge=0, max_digits=12, decimal_places=2)
    cantidad_max: Decimal | None = Field(None, ge=0, max_digits=12, decimal_places=2)


class DetalleParametroKitResponse(DetalleParametroKitBase):
    id_detalle_regla: int
    articulo: str | None = None
    unidad: str | None = None


class ReglaCalculoKitCreate(BaseModel):
    nombre_regla: str = Field(..., min_length=1, max_length=100)
    criterio_aplicacion: CriterioAplicacion
    rango_edad_min_dias: int | None = Field(
        None, ge=0, description="Edad mínima del integrante en días (0-24 meses = 730 días)")
    rango_edad_max_dias: int | None = Field(None, ge=0)
    requiere_gestante: bool = False
    requiere_discapacidad: bool = False
    sexo: SexoRegla | None = None
    dias_duracion: int | None = Field(
        None, gt=0, description="Horizonte en días del kit; NULL = cálculo por día")
    redondeo: RedondeoRegla = "piso"
    prioridad: int = 100
    activo: bool = True
    orden: int = 0
    detalles: list[DetalleParametroKitBase] = Field(..., min_length=1)


class ReglaCalculoKitUpdate(BaseModel):
    nombre_regla: str | None = Field(None, min_length=1, max_length=100)
    criterio_aplicacion: CriterioAplicacion | None = None
    rango_edad_min_dias: int | None = Field(None, ge=0)
    rango_edad_max_dias: int | None = Field(None, ge=0)
    requiere_gestante: bool | None = None
    requiere_discapacidad: bool | None = None
    sexo: SexoRegla | None = None
    dias_duracion: int | None = Field(None, gt=0)
    redondeo: RedondeoRegla | None = None
    prioridad: int | None = None
    activo: bool | None = None
    orden: int | None = None
    detalles: list[DetalleParametroKitBase] | None = None


class ReglaCalculoKitResponse(ReglaCalculoKitCreate):
    id_regla: int
    estado: Literal["borrador", "publicada"] = "borrador"
    version_actual: int = 0
    fecha_creacion: datetime | None = None
    fecha_modificacion: datetime | None = None
    detalles: list[DetalleParametroKitResponse] = Field(default_factory=list)


# ============================================================================
#  Ciclo de vida de reglas + ejecuciones del motor (v2.58.0, contrato /calculos)
# ============================================================================

class ReglaValidacionResponse(BaseModel):
    valida: bool
    errores: list[str] = Field(default_factory=list)
    advertencias: list[str] = Field(default_factory=list)
    resumen: dict = Field(default_factory=dict)


class SimulacionReglaRequest(BaseModel):
    poblacion: int | None = Field(
        None, ge=1, description="Poblacion sintetica a aplicar (default 1)")
    dias_duracion: int | None = Field(
        None, gt=0, description="Sobrescribe los dias de duracion del kit")
    detalles: list[DetalleParametroKitBase] | None = Field(
        None, description="Sobrescribe los articulos/cantidades base del kit")


class SimulacionReglaResponse(BaseModel):
    simulacion: bool = True
    regla: dict
    resultado: list[dict]
    poblacion: int
    persistido_como_necesidad: bool = False


class PublicarReglaRequest(BaseModel):
    confirmar: bool = Field(
        ..., description="Debe ser true para publicar")


class ReglaVersionResponse(BaseModel):
    id_version: int
    id_regla: int
    numero_version: int
    configuracion_json: dict
    fecha_publicacion: datetime | None = None
    publicado_por: int | None = None


class ReglaCalculoEjecucion(BaseModel):
    id_regla: int
    numero_version: int | None = Field(
        None, description="Version publicada a ejecutar; por defecto la ultima")


class CalculoRequest(BaseModel):
    id_solicitud: int
    familias: list[int] | None = Field(
        None, description="id_familia a incluir; omitir = todas las del evento")
    reglas: list[ReglaCalculoEjecucion] | None = Field(
        None, description="Reglas a ejecutar; omitir = todas las publicadas y activas")
    modo: Literal["previsualizacion", "operativo"] = "previsualizacion"
    forzar: bool = Field(
        False, description="Solo operativo: recalcular tambien sobre filas fuente='manual'")


class CalculoResponse(BaseModel):
    calculo_id: str | None = None
    estado: str = "completado"
    modo: str
    id_solicitud: int
    resultados: list[dict] = Field(default_factory=list)
    inventario_consultado: bool = False
    necesidades_registradas: bool = False


class CalculoDetalleResponse(BaseModel):
    id_detalle: int
    id_calculo: str
    id_familia: int
    id_regla: int
    id_version: int
    id_articulo: int
    articulo: str | None = None
    cantidad_calculada: float
    unidad_medida: str | None = None


class CalculoCabeceraResponse(BaseModel):
    id_calculo: str
    id_solicitud: int
    modo: str
    estado: str
    fecha_ejecucion: datetime | None = None
    id_usuario: int | None = None
    total_detalles: int = 0
    total_familias: int = 0


# ============================================================================
#  Motor de NECESIDADES (v2.61.0)
# ============================================================================

class CondicionesNecesidad(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gestante: bool | None = Field(
        None, description="Solo integrantes gestantes (sexo F + semanas > 0)")
    discapacidad: bool | None = Field(
        None, description="Solo integrantes con discapacidad registrada")
    edad_min_dias: int | None = Field(None, ge=0)
    edad_max_dias: int | None = Field(None, ge=0)
    sexo: Literal["M", "F"] | None = None


class ReglaNecesidadBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)
    criterio_aplicacion: Literal[
        "POR_FAMILIA", "POR_INTEGRANTE", "POR_CONDICION_ESPECIAL"]
    id_categoria_ayuda: int = Field(..., description="Categoría del artículo")
    id_articulo: int = Field(..., description="Artículo que genera la necesidad")
    cantidad_base: Decimal = Field(
        ..., ge=0, max_digits=8, decimal_places=3,
        description="Cantidad base por familia/integrante (se multiplica por días)")
    dias_duracion: int | None = Field(
        None, gt=0, description="Horizonte en días; NULL = 1 día")
    condiciones: CondicionesNecesidad = Field(default_factory=CondicionesNecesidad)
    prioridad: int = 100
    orden: int = 0
    activo: bool = True


class ReglaNecesidadCreate(ReglaNecesidadBase):
    pass


class ReglaNecesidadUpdate(BaseModel):
    nombre: str | None = Field(None, min_length=1, max_length=100)
    criterio_aplicacion: Literal[
        "POR_FAMILIA", "POR_INTEGRANTE", "POR_CONDICION_ESPECIAL"] | None = None
    id_categoria_ayuda: int | None = None
    id_articulo: int | None = None
    cantidad_base: Decimal | None = Field(
        None, ge=0, max_digits=8, decimal_places=3)
    dias_duracion: int | None = Field(None, gt=0)
    condiciones: CondicionesNecesidad | None = None
    prioridad: int | None = None
    orden: int | None = None
    activo: bool | None = None


class ReglaNecesidadResponse(ReglaNecesidadBase):
    id_regla_necesidad: int
    categoria: str | None = None
    articulo: str | None = None
    unidad: str | None = None
    fecha_creacion: datetime | None = None
    fecha_modificacion: datetime | None = None


class NecesidadCalculada(BaseModel):
    id_familia: int
    id_localidad: int | None = None
    localidad: str | None = None
    id_articulo: int
    articulo: str | None = None
    categoria: str | None = None
    cantidad: int
    unidad: str | None = None
    fuente: Literal["motor"] = "motor"
    id_regla: int | None = None


class ResumenNecesidades(BaseModel):
    familias: int = 0
    articulos_distintos: int = 0
    unidades: int = 0
    manuales_reemplazadas: int = 0
    motoras_eliminadas: int = 0


class MotorNecesidadesRequest(BaseModel):
    forzar: bool = Field(
        False, description="Aceptado por contrato; el motor siempre manda")


class MotorNecesidadesResponse(BaseModel):
    id_solicitud: int
    persistido: bool
    necesidades: list[NecesidadCalculada] = Field(default_factory=list)
    resumen: ResumenNecesidades = Field(default_factory=ResumenNecesidades)
