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
    id_tipo_localidad: int | None = Field(None, description="FK a edan.tipo_localidad (rastreo)")
    tipo_localidad_nombre: str | None = None
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
    id_edan_localidad: int | None = Field(None, description="FK a edan.edan_localidades (rastreo del empadronamiento)")
    id_edan: int | None = None
    id_usuario: int | None = None
    id_estado: int | None = None
    id_evento_rida: int | None = None
    localidad_nombre: str | None = None
    id_tipo_localidad: int | None = Field(None, description="FK a edan.tipo_localidad")
    tipo_localidad_nombre: str | None = None
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
    id_tipo_localidad: int | None = Field(None, description="FK a edan.tipo_localidad (rastreo)")
    tipo_localidad_nombre: str | None = None
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
    codigo: str | None = Field(None, description="Código del evento RIDA: "
                                                 "<codigo_edan>-R (v2.46.0)")
    estado: CatEstadoEventoResponse | None = None
    id_usuario_habilito: int | None = None
    fecha_habilitacion: datetime | None = None
    id_usuario_cierro: int | None = None
    fecha_cierre: datetime | None = None
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


# ============================================================================
#  REPORTE DE EVENTO RIDA (empadronamiento consolidado)
# ============================================================================

class ReporteUsuario(BaseModel):
    id_usuario: int
    nombre: str | None = None
    usuario: str | None = None


class ReporteGrupoEtario(BaseModel):
    grupo: str = Field(description="codigo del grupo (edan.grupo_etario): "
                                   "ninas_ninos_0_5 | escolar_6_18 | adulto_19_60 | "
                                   "adulto_mayor_60 | sin_fecha")
    nombre: str
    orden: int
    total: int = 0
    m: int = 0
    f: int = 0


class ReporteTipoConteo(BaseModel):
    id: int
    codigo: str | None = None
    nombre: str | None = None
    total: int = 0


class ReporteCapacidadDetalle(BaseModel):
    total: int = 0
    por_tipo: list[ReporteTipoConteo] = []


class ReporteCapacidadesGrupo(BaseModel):
    grupo: str
    nombre: str
    orden: int
    gestantes: int = 0
    lactantes: int = 0
    discapacidad: ReporteCapacidadDetalle = Field(default_factory=ReporteCapacidadDetalle)
    enfermedad: ReporteCapacidadDetalle = Field(default_factory=ReporteCapacidadDetalle)


class ReporteNecesidadCategoria(BaseModel):
    id_categoria: int
    codigo: str | None = None
    nombre: str | None = None
    n_necesidades: int = 0
    completadas: int = 0


class ReporteNecesidadFamilia(BaseModel):
    id_familia: int
    id_formulario: int | None = None
    integrantes: int = 0
    n_necesidades: int = 0
    por_categoria: list[ReporteNecesidadCategoria] = []


class ReporteNecesidadesTotales(BaseModel):
    total: int = 0
    completadas: int = 0
    pendientes: int = 0


class ReportePromMinMax(BaseModel):
    promedio: float = 0
    minimo: int = 0
    maximo: int = 0


class ReporteSeccion(BaseModel):
    """Las 3 secciones del reporte, idénticas para `resumen` (total del evento)
    y para cada `formulario`: población por grupo etario, capacidades especiales
    por grupo etario y necesidades por familia."""
    familias: int = 0
    integrantes: int = 0
    integrantes_por_familia: ReportePromMinMax = Field(default_factory=ReportePromMinMax)
    poblacion_por_grupo_etario: list[ReporteGrupoEtario] = []
    capacidades_especiales_por_grupo_etario: list[ReporteCapacidadesGrupo] = []
    necesidades_por_familia: list[ReporteNecesidadFamilia] = []
    necesidades: ReporteNecesidadesTotales = Field(default_factory=ReporteNecesidadesTotales)


class ReporteLocalidad(BaseModel):
    """Identificadores de rastreo de la localidad (id al inicio)."""
    id_edan_localidad: int | None = None
    id_tipo_localidad: int | None = None
    localidad: str | None = None
    tipo_localidad: str | None = None
    estado_localidad: str | None = None


class ReporteFormulario(BaseModel):
    """Un formulario (localidad) del reporte: identificadores de rastreo al
    inicio (id_edan_localidad, id_tipo_localidad, localidad, id_formulario)
    y después las mismas 3 secciones que `resumen`. No hereda de
    ReporteSeccion para conservar ese orden de campos en la serialización."""
    id_edan_localidad: int | None = Field(None, description="Identificador de rastreo del empadronamiento")
    id_tipo_localidad: int | None = Field(None, description="FK a edan.tipo_localidad")
    localidad: ReporteLocalidad | None = None
    id_formulario: int | None = None
    estado_formulario: dict | None = None
    fecha_creacion: datetime | None = None
    levantado_por: ReporteUsuario | None = None
    familias: int = 0
    integrantes: int = 0
    integrantes_por_familia: ReportePromMinMax = Field(default_factory=ReportePromMinMax)
    poblacion_por_grupo_etario: list[ReporteGrupoEtario] = []
    capacidades_especiales_por_grupo_etario: list[ReporteCapacidadesGrupo] = []
    necesidades_por_familia: list[ReporteNecesidadFamilia] = []
    necesidades: ReporteNecesidadesTotales = Field(default_factory=ReporteNecesidadesTotales)


class ReportePoblacionDeclarada(BaseModel):
    poblacion_afectada: int | None = None
    familias_afectadas: int | None = None
    familias_damnificadas: int | None = None


class ReporteEdan(BaseModel):
    id_edan: int
    codigo_edan: str | None = None
    procedencia: str | None = None
    fecha_evento: date | None = None
    hora_evento: object | None = None
    fecha_llenado: date | None = None
    tipo_evento: dict | None = None
    departamento: dict | None = None
    provincia: dict | None = None
    municipio: dict | None = None
    levantaron: list[ReporteUsuario] = Field(
        default_factory=list,
        description="Quiénes levantaron la información: creadores de las localidades "
                    "del EDAN + importador (si el EDAN viene de importación)")
    ugr: ReporteUsuario | None = None
    alcalde: ReporteUsuario | None = None
    poblacion_declarada: ReportePoblacionDeclarada = Field(
        default_factory=ReportePoblacionDeclarada)
    n_localidades: int = 0


class ReporteEvento(BaseModel):
    id_evento_rida: int
    codigo: str | None = None
    estado: dict | None = None
    fecha_habilitacion: datetime | None = None
    fecha_cierre: datetime | None = None
    fecha_creacion: datetime | None = None


class EventoReporteResponse(BaseModel):
    """`data` de GET /rida/evento/{identificador}/reporte.

    Orden: evento → edan → `resumen` (total del evento con las 3 secciones) →
    `formularios` (cada uno con sus datos y las mismas 3 secciones). Edades
    calculadas a la fecha del empadronamiento."""
    evento: ReporteEvento
    edan: ReporteEdan
    resumen: ReporteSeccion = Field(default_factory=ReporteSeccion)
    formularios: list[ReporteFormulario] = []


# ============================================================================
#  REPORTE DE INTEGRANTES POR LUGAR (listado de personas del evento)
# ============================================================================

class IntegranteReporteItem(BaseModel):
    """Una persona (integrante) dentro del listado por lugar. Rastreo de la
    persona solo con datos propios (documento/nombre); el lugar se da en el
    bloque `localidad` padre. Edad y grupo calculados a la fecha de
    empadronamiento (`fecha_creacion` del integrante, fallback la del
    formulario)."""
    numero_documento: str | None = Field(None, description="Nro. de documento (Carnet/DNI/otro)")
    tipo_documento: str | None = Field(None, description="Tipo de documento (CARNET, CI, ...)")
    nombre: str | None = None
    apellido: str | None = None
    nombre_completo: str | None = Field(None, description="apellido + nombre")
    sexo: str | None = Field(None, description="M o F")
    sexo_nombre: str | None = Field(None, description="Masculino / Femenino / None")
    fecha_nacimiento: date | None = None
    edad: int | None = Field(None, description="Años completados a la fecha de empadronamiento")
    grupo_etario: str | None = Field(None, description="codigo de edan.grupo_etario")
    grupo_etario_nombre: str | None = None
    id_parentesco: int | None = None
    parentesco_nombre: str | None = None
    es_jefe: bool | None = Field(False, description="Jefe(a) de hogar")
    id_discapacidad: int | None = None
    discapacidad_nombre: str | None = None
    id_enfermedad: int | None = None
    enfermedad_nombre: str | None = None
    gestante_semanas: int | None = None
    lactante_meses: int | None = None


class LocalidadIntegrantes(BaseModel):
    """Un lugar (localidad) del evento con sus integrantes ordenados por
    apellido. Los ids de rastreo van al inicio; `personas: []` si aún no se
    empadronó (consistente con el reporte de secciones)."""
    id_edan_localidad: int | None = Field(None, description="Identificador de rastreo del empadronamiento")
    id_tipo_localidad: int | None = Field(None, description="FK a edan.tipo_localidad")
    tipo_localidad: str | None = None
    localidad: str | None = None
    estado_localidad: str | None = None
    id_formulario: int | None = None
    familias: int = 0
    integrantes: int = 0
    personas: list[IntegranteReporteItem] = []


class ReporteIntegrantesResumen(BaseModel):
    """Totales de todo el evento. `sin_sexo` cubre integrantes con sexo NULL o
    fuera de {M, F}."""
    n_localidades: int = 0
    familias: int = 0
    integrantes: int = 0
    masculino: int = 0
    femenino: int = 0
    sin_sexo: int = 0
    por_grupo_etario: list[ReporteGrupoEtario] = []
    con_discapacidad: int = 0
    con_enfermedad: int = 0
    gestantes: int = 0
    lactantes: int = 0


class EventoIntegrantesResponse(BaseModel):
    """`data` de GET /rida/evento/{identificador}/integrantes (y su variante
    `GET /rida/evento/integrantes?codigo=`).

    Orden: evento → edan → `resumen` (totales) → `localidades` (un bloque por
    lugar, con `personas` ordenadas por apellido)."""
    evento: ReporteEvento
    edan: ReporteEdan
    resumen: ReporteIntegrantesResumen = Field(default_factory=ReporteIntegrantesResumen)
    localidades: list[LocalidadIntegrantes] = []


class DeshabilitarEventoResponse(BaseModel):
    """Resultado de deshabilitar (borrado físico del evento y sus hijos vacíos)."""
    id_evento_rida: int
    id_edan: int | None = None
    formularios_eliminados: int = 0