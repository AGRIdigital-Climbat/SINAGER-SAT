from datetime import date, datetime
from pydantic import BaseModel, Field


# ============================================================================
#  CATÁLOGOS
# ============================================================================

class CatTipoAlbergueResponse(BaseModel):
    id_cat_tipo_albergue: int
    nombre: str


class CatEstadoFormularioResponse(BaseModel):
    id_estado_formulario: int
    codigo: str
    nombre: str
    descripcion: str | None = None
    orden: int | None = None
    activo: bool | None = True


class CatParentescoResponse(BaseModel):
    id_parentesco: int
    codigo: str
    nombre: str
    activo: bool | None = True


class CatTipoDiscapacidadResponse(BaseModel):
    id_discapacidad: int
    codigo: str
    nombre: str
    requiere_movilidad: bool | None = False
    activo: bool | None = True


# ============================================================================
#  INTEGRANTE
# ============================================================================

class IntegranteBase(BaseModel):
    id_integrante_off: str | None = Field(None, description="ID único offline (generado por dispositivo)")
    sexo: str | None = Field(None, description="M o F")
    fecha_nacimiento: date | None = None
    numero_documento: str | None = Field(None, max_length=20, description="Número de carnet o certificado")
    tipo_documento: str | None = Field("CARNET", description="CARNET o CERTIFICADO")
    id_parentesco: int | None = None
    es_jefe: bool | None = False
    gestante_semanas: int | None = Field(None, ge=0, le=45)
    lactante_meses: int | None = Field(None, ge=0, le=36)
    id_discapacidad: int | None = None
    id_enfermedad: int | None = None
    telefono: str | None = Field(None, max_length=20)
    nombre: str | None = Field(None, max_length=100)
    apellido: str | None = Field(None, max_length=100)


class IntegranteCreate(IntegranteBase):
    id_familia: int | None = Field(None, description="Obligatorio salvo en sync (se resuelve por id_familia_off)")


class IntegranteUpdate(IntegranteBase):
    pass


class IntegranteResponse(BaseModel):
    id_integrante: int
    id_familia: int
    id_integrante_off: str | None = None
    sexo: str | None = None
    fecha_nacimiento: date | None = None
    numero_documento: str | None = None
    tipo_documento: str | None = None
    id_parentesco: int | None = None
    parentesco_nombre: str | None = None
    es_jefe: bool | None = False
    gestante_semanas: int | None = None
    lactante_meses: int | None = None
    id_discapacidad: int | None = None
    discapacidad_nombre: str | None = None
    id_enfermedad: int | None = None
    enfermedad_nombre: str | None = None
    telefono: str | None = None
    nombre: str | None = None
    apellido: str | None = None
    fecha_creacion: datetime | None = None
    fecha_modificacion: datetime | None = None


# ============================================================================
#  UBICACIÓN FAMILIA
# ============================================================================

class UbicacionFamiliaBase(BaseModel):
    id_ubicacion_off: str | None = Field(None, description="ID único offline (generado por dispositivo)")
    coordenada_lat: float | None = Field(None, ge=-90, le=90)
    coordenada_lon: float | None = Field(None, ge=-180, le=180)
    id_cat_tipo_albergue: int | None = None


class UbicacionFamiliaNested(UbicacionFamiliaBase):
    """Ubicación dentro de un payload de sync/familia; el vínculo offline a la
    familia se expresa con id_familia_off."""
    id_familia_off: str | None = Field(None, description="Resuelve id_familia en sync offline")


class UbicacionFamiliaCreate(UbicacionFamiliaBase):
    id_familia: int | None = Field(None, description="Obligatorio salvo en sync (se resuelve por id_familia_off)")


class UbicacionFamiliaUpdate(UbicacionFamiliaBase):
    pass


class UbicacionFamiliaResponse(BaseModel):
    id_ubicacion_familia: int
    id_ubicacion_off: str | None = None
    coordenada_lat: float | None = None
    coordenada_lon: float | None = None
    id_familia: int
    id_cat_tipo_albergue: int | None = None
    tipo_albergue_nombre: str | None = None
    fecha_creacion: datetime | None = None
    fecha_modificacion: datetime | None = None


# ============================================================================
#  FAMILIA
# ============================================================================

class FamiliaBase(BaseModel):
    id_familia_off: str | None = Field(None, description="ID único offline (generado por dispositivo)")
    id_edan_localidad: int | None = None
    id_necesidad: int | None = None
    observacion: str | None = None


class FamiliaCreate(FamiliaBase):
    id_formulario: int | None = Field(None, description="Obligatorio salvo en sync (se resuelve por id_edan_localidad)")


class FamiliaUpdate(FamiliaBase):
    pass


class FamiliaResponse(BaseModel):
    id_familia: int
    id_familia_off: str | None = None
    id_formulario: int
    id_edan_localidad: int | None = None
    id_ubicacion_familia: int | None = None
    id_necesidad: int | None = None
    observacion: str | None = None
    localidad_nombre: str | None = None
    id_municipio: int | None = None
    id_departamento: int | None = None
    fecha_creacion: datetime | None = None
    fecha_modificacion: datetime | None = None
    integrantes: list[IntegranteResponse] = []
    ubicaciones: list[UbicacionFamiliaResponse] = []


# ============================================================================
#  FORMULARIO RIDA
# ============================================================================

class FormularioRidaCreate(BaseModel):
    id_edan_localidad: int = Field(..., description="FK a edan.edan_localidades (UNIQUE: un formulario por localidad)")
    id_edan: int | None = Field(None, description="FK a edan.edan aprobado (estado 3 ó 5). Si falta se usa el del EDAN de la localidad")
    id_estado: int | None = Field(1, description="FK a rida.cat_estado_formulario (default: PENDIENTE=1)")


class FormularioRidaUpdate(BaseModel):
    id_edan: int | None = None
    id_estado: int | None = None


class FormularioRidaResponse(BaseModel):
    id_formulario: int
    id_edan_localidad: int | None = None
    id_edan: int | None = None
    id_usuario: int | None = None
    id_estado: int | None = None
    id_evento_rida: int | None = None
    localidad_nombre: str | None = None
    id_municipio: int | None = None
    id_departamento: int | None = None
    municipio_nombre: str | None = None
    departamento_nombre: str | None = None
    codigo_edan: str | None = None
    edan_id_estado: int | None = None
    estado_codigo: str | None = None
    estado_nombre: str | None = None
    n_familias: int | None = None
    n_integrantes: int | None = None
    n_necesidades: int | None = None
    fecha_creacion: datetime | None = None
    fecha_modificacion: datetime | None = None
    familias: list[FamiliaResponse] = []


# ============================================================================
#  SYNC OFFLINE (batch)
# ============================================================================

class IntegranteNested(IntegranteBase):
    """Integrante dentro de un payload de sync; el vínculo offline a la familia
    se expresa con id_familia_off."""
    id_familia_off: str | None = Field(None, description="Resuelve id_familia en sync offline")


class EmpadronamientoSyncIn(BaseModel):
    formularios: list[FormularioRidaCreate] = Field(default_factory=list)
    familias: list[FamiliaCreate] = Field(default_factory=list)
    integrantes: list[IntegranteNested] = Field(default_factory=list)
    ubicaciones: list[UbicacionFamiliaNested] = Field(default_factory=list)


# ============================================================================
#  EVENTO RIDA (PADRE)
# ============================================================================

class CatEstadoEventoResponse(BaseModel):
    id_estado_evento: int
    codigo: str
    nombre: str


class LocalidadEventoResponse(BaseModel):
    """HIJO del evento RIDA: una localidad del EDAN con su formulario asociado."""
    id_formulario: int | None = None
    id_edan_localidad: int | None = None
    id_edan: int | None = None
    id_usuario: int | None = None
    id_estado: int | None = None
    id_evento_rida: int | None = None
    localidad: str | None = None
    id_departamento: int | None = None
    id_municipio: int | None = None
    departamento_nombre: str | None = None
    municipio_nombre: str | None = None
    estado_codigo: str | None = None
    estado_nombre: str | None = None
    n_familias: int | None = None
    n_integrantes: int | None = None
    n_necesidades: int | None = None


class EventoRidaResponse(BaseModel):
    """PADRE del RIDA con desglose del EDAN (tipo evento, geografía, usuarios)."""
    id_evento_rida: int
    id_edan: int | None = None
    id_estado: int | None = None
    estado: CatEstadoEventoResponse | None = None
    id_usuario_habilito: int | None = None
    fecha_habilitacion: datetime | None = None
    id_usuario_cierro: int | None = None
    fecha_cierre: datetime | None = None
    anulado: bool = False
    id_usuario_anulo: int | None = None
    fecha_anulacion: datetime | None = None
    fecha_creacion: datetime | None = None
    fecha_modificacion: datetime | None = None
    codigo_edan: str | None = None
    fecha_evento: date | None = None
    hora_evento: object | None = None
    tipo_evento: dict | None = None
    departamento: dict | None = None
    provincia: dict | None = None
    municipio: dict | None = None
    usuario_alcalde: dict | None = None
    usuario_ugr: dict | None = None
    n_familias: int = 0
    n_integrantes: int = 0
    n_necesidades: int = 0
    localidades: list[LocalidadEventoResponse] = []
    num_localidades: int = 0