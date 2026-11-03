from datetime import date, datetime
from pydantic import BaseModel, Field, model_validator


class CatModalidadResponse(BaseModel):
    id_modalidad: int
    nombre: str
    descripcion: str | None = None
    activo: bool | None = True


class CatRequisitoResponse(BaseModel):
    id_requisito: int
    id_modalidad: int
    orden: int
    nombre_paso: str
    id_tipo_documento: int | None = None
    instancia: int
    es_documento: bool | None = True
    es_hito_aprobacion: bool | None = False
    activo: bool | None = True


class RequisitoConEstado(CatRequisitoResponse):
    completado: bool = False
    id_solicitud_documento: int | None = None
    id_documento: int | None = None
    fecha_subida: datetime | None = None
    valido: bool | None = None
    observaciones_doc: str | None = None


class SolicitudCreate(BaseModel):
    id_evento_rida: int
    id_modalidad: int
    observaciones: str | None = None


class SolicitudUpdate(BaseModel):
    id_modalidad: int | None = None
    observaciones: str | None = None


class SolicitudDocumentoCreate(BaseModel):
    id_requisito: int
    observaciones: str | None = None


class AprobacionNivelDerivada(BaseModel):
    """Un eslabon de la cadena, derivado de rida.aprobaciones_solicitud
    (fase 2, v2.45.0). Para `puede_aprobar` y el resto del detalle usar
    GET /{id_solicitud}/aprobacion."""
    nivel: str
    estado: str
    observacion: str | None = None
    por: int | None = None
    fecha: datetime | None = None


class SolicitudResponse(BaseModel):
    id_solicitud: int
    id_evento_rida: int
    id_modalidad: int
    nombre_modalidad: str | None = None
    etapa: str
    codigo_edan: str | None = None
    evento_codigo: str | None = None
    id_municipio: int | None = None
    nombre_municipio: str | None = None
    id_departamento: int | None = None
    nombre_departamento: str | None = None
    fecha_inicio: datetime | None = None
    # Derivado de rida.aprobaciones_solicitud en cada lectura: la bandeja y el
    # detalle ven la cadena activa sin un GET de la maquina por fila. La
    # columna derivada de 15 campos se retiro en la v2.45.0 (fase 2).
    # estado_global es un RESUMEN (regla 3), no un turno: para saber quien
    # puede actuar usar GET /{id_solicitud}/aprobacion (puede_aprobar).
    aprobaciones: list[AprobacionNivelDerivada] = []
    estado_global: str | None = None
    observaciones: str | None = None
    fecha_cierre: datetime | None = None
    id_usuario_crea: int | None = None


class CatEtapaSolicitudResponse(BaseModel):
    id_etapa: int
    codigo: str
    nombre: str
    orden: int
    activo: bool | None = True


class BitacoraItemResponse(BaseModel):
    id_bitacora: int
    id_solicitud: int
    # Nullable en BD: las filas previas a la maquina de aprobaciones lo tienen
    # NULL, y declararlo obligatorio las hacia fallar la respuesta entera.
    paso_orden: int | None = None
    paso_nombre: str | None = None
    accion: str | None = None
    estado_resultante: str | None = None
    observaciones: str | None = None
    id_usuario: int | None = None
    fecha: datetime | None = None


class TransicionRequest(BaseModel):
    observaciones: str | None = None


OBS_MIN = 10


class AprobacionRequest(BaseModel):
    """Cuerpo de PUT /{id_solicitud}/aprobacion/{nivel}.

    Acepta los dos pares de nombres durante la transicion: el canonico
    (aprobado / observacion) y el legado que hoy manda el frontend
    (aprobar / observaciones). Si llegan los dos, gana el canonico; los
    nombres legados quedan obsoletos cuando el frontend lea la maquina
    (GET /{id_solicitud}/aprobacion).
    """
    model_config = {"extra": "forbid"}

    aprobado: bool | None = None
    observacion: str | None = None
    aprobar: bool | None = None
    observaciones: str | None = None

    @model_validator(mode="after")
    def _resolver(self) -> "AprobacionRequest":
        self.aprobado = self.aprobado if self.aprobado is not None else self.aprobar
        if self.observacion is None:
            self.observacion = self.observaciones
        if self.aprobado is None:
            raise ValueError("Debe enviar 'aprobado' (o 'aprobar')")
        return self

    @property
    def es_devolver(self) -> bool:
        return self.aprobado is False

    @property
    def motivo(self) -> str:
        return (self.observacion or "").strip()


class NivelAprobacionSolicitudResponse(BaseModel):
    """Un eslabon de la cadena. `puede_aprobar` lo calcula el servidor con el
    rol y el alcance del token: el frontend no debe deducirlo de estado_global."""
    nivel: str
    orden: int
    estado: str
    observacion: str | None = None
    por: int | None = None
    fecha: datetime | None = None
    roles: list[int] = []
    alcance: str
    puede_aprobar: bool = False
    puede_devolver: bool = False
    es_mio: bool = False


class AprobacionesSolicitudResponse(BaseModel):
    """`data` de GET /{id_solicitud}/aprobacion y de los PUT."""
    id_solicitud: int
    id_modalidad: int
    etapa: str
    cadena: list[str] = []
    # None sin cadena (Ayuda Humanitaria / sin configurar); en otro caso es el
    # badge del primer nivel no aprobado (v2.60.0).
    estado_global: str | None = None
    mi_nivel: str | None = None
    aprobaciones: dict[str, NivelAprobacionSolicitudResponse] = {}


class NivelCatalogoAprobacionResponse(BaseModel):
    codigo: str
    label: str
    roles: list[int] = []
    nom_roles: list[str] = []
    alcance: str
    orden: int


class CadenaAprobacionResponse(BaseModel):
    """`data` de GET /rida/solicitudes/cat-cadena-aprobacion.

    Se consume una vez y se cachea: el listado de solicitudes no hace un GET de
    la maquina por fila, asi que el frontend necesita la cadena aqui."""
    niveles: list[NivelCatalogoAprobacionResponse] = []
    default: list[str] = []
    por_modalidad: dict[str, list[str]] = {}


class CadenaAprobacionUpdateRequest(BaseModel):
    """Reemplaza la cadena de una modalidad. `id_modalidad = None` no se acepta
    por ruta porque la cadena por defecto se edita por la misma via con el
    identificador de la modalidad."""
    niveles: list[str]
