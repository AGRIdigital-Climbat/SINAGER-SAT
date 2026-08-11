from pydantic import BaseModel, Field


# ============================================================================
#  MODELOS ANIDADOS DEL FORMULARIO EDAN
#  Espejo de lib/models/edan.dart (nombres JSON exactos de la app).
# ============================================================================

class ImpactoPoblacion(BaseModel):
    rango: str = ''
    fallecidos: int = 0
    heridos: int = 0
    desaparecidos: int = 0
    observaciones: str = ''


class PrimeraRespuesta(BaseModel):
    busqueda: bool = False
    salvamento: bool = False
    evacuacion: bool = False
    observaciones: str = ''


class EstablecimientoSalud(BaseModel):
    nombre_establecimiento: str = ''
    comunidad: str = ''
    nivel_atencion: str = ''
    dano_parcial: bool = False
    dano_total: bool = False
    medicos_afectados: int = 0
    enfermeras_afectados: int = 0
    otros_afectados: int = 0
    fotografia: str | None = None
    coordenada_lat: float | None = None
    coordenada_lon: float | None = None


class NecesidadSalud(BaseModel):
    numero_personas: int = 0
    otras_necesidades: str = ''
    observaciones: str = ''


class DanoVial(BaseModel):
    via: bool = False
    puente: bool = False
    tramo: str = ''
    dano_parcial: bool = False
    dano_total: bool = False
    km_danio: float | None = 0
    necesidades_inmediatas: str = ''
    observaciones: str = ''
    fotografia: str | None = None
    coordenada_lat: float | None = None
    coordenada_lon: float | None = None


class DanoInfraPublica(BaseModel):
    comunidad: str = ''
    tipo_estructura: str = ''
    dano_parcial: bool = False
    dano_total: bool = False
    observaciones: str = ''
    fotografia: str | None = None
    coordenada_lat: float | None = None
    coordenada_lon: float | None = None


class ServicioBasicoDetalle(BaseModel):
    tipo: str = ''
    dano_parcial: bool = False
    dano_total: bool = False
    necesidades_inmediatas: str = ''
    observaciones: str = ''
    fotografia: str | None = None
    coordenada_lat: float | None = None
    coordenada_lon: float | None = None


class UnidadEducativa(BaseModel):
    nombre_establecimiento: str = ''
    comunidad: str = ''
    dano_parcial: bool = False
    dano_total: bool = False
    suspension_clases: bool | None = None
    perdida_material: bool | None = None
    funciona_albergue: bool | None = None
    estudiantes: int = 0
    profesores: int = 0
    administrativos: int = 0
    observaciones: str = ''
    fotografia: str | None = None
    coordenada_lat: float | None = None
    coordenada_lon: float | None = None


class DanoVivienda(BaseModel):
    comunidad: str = ''
    dano_parcial: int = 0
    dano_total: int = 0
    necesidades_inmediatas: str = ''
    observaciones: str = ''
    fotografia: str | None = None
    coordenada_lat: float | None = None
    coordenada_lon: float | None = None


class DanoAgricultura(BaseModel):
    tipo_cultivo: str = ''
    id_cultivo: int | None = None
    hectareas_afectadas: int = 0
    hectareas_perdidas: int = 0
    necesidades_inmediatas: str = ''
    observaciones: str = ''
    fotografia: str | None = None
    coordenada_lat: float | None = None
    coordenada_lon: float | None = None


class DanoPecuario(BaseModel):
    especie: str = ''
    id_especie: int | None = None
    raza: str = ''
    animales_afectados: int = 0
    animales_muertos: int = 0
    necesidades_inmediatas: str = ''
    fotografia: str | None = None
    coordenada_lat: float | None = None
    coordenada_lon: float | None = None


class InfraProductiva(BaseModel):
    tipo: str = ''
    dano_parcial: int = 0
    dano_total: int = 0


class GrupoVulnerable(BaseModel):
    grupo: str = ''
    mujeres: int = 0
    hombres: int = 0
    total: int = 0
    apoyo_psicologico: bool | None = None
    reposicion_documentos: bool | None = None
    observaciones: str = ''


class Proteccion(BaseModel):
    proteccion: list[GrupoVulnerable] = []


class NecesidadHumanitaria(BaseModel):
    alimentos: bool = False
    refugio_vivienda: bool = False
    ropa_cama: bool = False
    articulos_higiene: bool = False
    articulos_cocina: bool = False
    prendas_vestir: bool = False
    herramientas: bool = False
    almacenamiento_agua: bool = False
    banos: bool = False
    obs_alimentos: str = ''
    obs_refugio_vivienda: str = ''
    obs_ropa_cama: str = ''
    obs_articulos_higiene: str = ''
    obs_articulos_cocina: str = ''
    obs_prendas_vestir: str = ''
    obs_herramientas: str = ''
    obs_almacenamiento_agua: str = ''
    obs_banos: str = ''


class Responsable(BaseModel):
    nombre: str = ''
    cargo: str = ''
    fono: str = ''
    correo: str = ''


class LocalidadCreate(BaseModel):
    id_tipo_localidad: int | None = None
    id_edan_localidad_estado: int | None = None
    tipo_localidad: str | None = None
    id_tipo_evento: int | None = None
    id_departamento: int | None = None
    id_provincia: int | None = None
    id_municipio: int | None = None
    fecha_llenado: str | None = None
    fecha_evento: str | None = None
    hora_evento: str | None = None
    total_poblacion_afectada: int = 0
    total_familias_afectadas: int = 0
    total_familias_damnificadas: int = 0
    id_local: str | None = None
    id_usuario: int | None = None
    fecha_modificacion: str | None = None
    pendiente_actualizacion: bool = False
    pendiente_eliminacion: bool = False
    localidad: str = ''
    imp_poblacion: bool = False
    imp_salud: bool = False
    imp_infraestructura: bool = False
    imp_servicios: bool = False
    imp_educacion: bool = False
    imp_vivienda: bool = False
    imp_agropecuario: bool = False
    imp_proteccion: bool = False
    imp_necesidades: bool = False
    impacto_poblacion: list[ImpactoPoblacion] = []
    necesidad_primera_respuesta: PrimeraRespuesta | None = None
    establecimientos_salud: list[EstablecimientoSalud] = []
    necesidad_salud: NecesidadSalud | None = None
    danos_viales: list[DanoVial] = []
    danos_infra_publica: list[DanoInfraPublica] = []
    servicios_basicos: list[ServicioBasicoDetalle] = []
    unidades_educativas: list[UnidadEducativa] = []
    danos_vivienda: list[DanoVivienda] = []
    danos_agricultura: list[DanoAgricultura] = []
    danos_pecuarios: list[DanoPecuario] = []
    infra_productiva: list[InfraProductiva] = []
    proteccion: list[GrupoVulnerable] = []
    necesidad_humanitaria: NecesidadHumanitaria | None = None


class LocalidadNestedResponse(BaseModel):
    """Estructura completa anidada de una localidad (respuesta de GET).

    Las secciones (impacto_poblacion, establecimientos_salud, danos_viales, etc.)
    son OPCIONALES: si no hay datos para esa sección, devuelve una lista vacía []
    o un dict con valores por defecto. Ejemplo: una granizada puede afectar
    agricultura pero no daños_vivienda.

    Todos los IDs vienen DESAGREGADOS en forma anidada:
    - id_departamento + departamento: { id, codigo_ine, nombre }
    - id_provincia + provincia: { id, codigo_ine, nombre }
    - id_municipio + municipio: { id, codigo_ine, nombre }
    - id_tipo_evento + tipo_evento: { id_tipo_evento, nombre }
    - id_tipo_localidad + tipo_localidad: { id_tipo_localidad, nombre, ... }
    - id_edan_localidad_estado + estado_localidad: { id, nombre, ... }
    - id_edan + edan: { id_edan, codigo_edan, estado, ... }
    - id_cultivo + cultivo (dentro de danos_agricultura[i])
    - id_especie + especie (dentro de danos_pecuarios[i])
    """
    id_edan_localidad: int
    id_edan: int | None = None
    es_huerfana: bool = True
    id_tipo_localidad: int | None = None
    id_edan_localidad_estado: int | None = None
    id_tipo_evento: int | None = None
    id_departamento: int | None = None
    id_provincia: int | None = None
    id_municipio: int | None = None
    fecha_llenado: str | None = None
    fecha_evento: str | None = None
    hora_evento: str | None = None
    total_poblacion_afectada: int = 0
    total_familias_afectadas: int = 0
    total_familias_damnificadas: int = 0
    id_local: str | None = None
    id_usuario: int | None = None
    fecha_modificacion: str | None = None
    pendiente_actualizacion: bool = False
    pendiente_eliminacion: bool = False
    localidad: str = ''
    imp_poblacion: bool = False
    imp_salud: bool = False
    imp_infraestructura: bool = False
    imp_servicios: bool = False
    imp_educacion: bool = False
    imp_vivienda: bool = False
    imp_agropecuario: bool = False
    imp_proteccion: bool = False
    imp_necesidades: bool = False
    tipo_localidad: dict | None = None
    estado_localidad: dict | None = None
    tipo_evento: dict | None = None
    departamento: dict | None = None
    provincia: dict | None = None
    municipio: dict | None = None
    edan: dict | None = None
    impacto_poblacion: list[dict] = []
    necesidad_primera_respuesta: dict = {}
    establecimientos_salud: list[dict] = []
    necesidad_salud: dict = {}
    danos_viales: list[dict] = []
    danos_infra_publica: list[dict] = []
    servicios_basicos: list[dict] = []
    unidades_educativas: list[dict] = []
    danos_vivienda: list[dict] = []
    danos_agricultura: list[dict] = []
    danos_pecuarios: list[dict] = []
    infra_productiva: list[dict] = []
    proteccion: list[dict] = []
    necesidad_humanitaria: dict = {}


class EdanCreate(BaseModel):
    id_local: str | None = None
    fecha_modificacion: str | None = None
    codigo_edan: str | None = None
    id_usuario_ugr: int | None = None
    id_usuario_alcalde: int | None = None
    id_departamento: int | None = None
    id_provincia: int | None = None
    id_municipio: int | None = None
    departamento_nombre: str | None = None
    provincia_nombre: str | None = None
    municipio_nombre: str | None = None
    fecha_llenado: str | None = None
    fecha_evento: str | None = None
    hora_evento: str | None = None
    total_poblacion_afectada: int = 0
    total_familias_afectadas: int = 0
    total_familias_damnificadas: int = 0
    id_tipo_evento: int | None = None
    tipo_evento_nombre: str | None = None
    localidades: list[LocalidadCreate] = []
    responsable: Responsable | None = None
    id_estado: int = 1
    estado: str = 'borrador'
    pendiente_eliminacion: bool = False
    pendiente_actualizacion: bool = False


class EdanUpdate(BaseModel):
    id_local: str | None = None
    fecha_modificacion: str | None = None
    codigo_edan: str | None = None
    id_usuario_ugr: int | None = None
    id_usuario_alcalde: int | None = None
    id_departamento: int | None = None
    id_provincia: int | None = None
    id_municipio: int | None = None
    fecha_llenado: str | None = None
    fecha_evento: str | None = None
    hora_evento: str | None = None
    total_poblacion_afectada: int | None = None
    total_familias_afectadas: int | None = None
    total_familias_damnificadas: int | None = None
    id_tipo_evento: int | None = None
    id_estado: int | None = None
    estado: str | None = None
    pendiente_eliminacion: bool | None = None
    pendiente_actualizacion: bool | None = None
    responsable: Responsable | None = None


class LocalidadUpdate(BaseModel):
    id_tipo_localidad: int | None = None
    id_edan_localidad_estado: int | None = None
    tipo_localidad: str | None = None
    id_tipo_evento: int | None = None
    id_departamento: int | None = None
    id_provincia: int | None = None
    id_municipio: int | None = None
    fecha_llenado: str | None = None
    fecha_evento: str | None = None
    hora_evento: str | None = None
    total_poblacion_afectada: int | None = None
    total_familias_afectadas: int | None = None
    total_familias_damnificadas: int | None = None
    localidad: str = ''
    imp_poblacion: bool = False
    imp_salud: bool = False
    imp_infraestructura: bool = False
    imp_servicios: bool = False
    imp_educacion: bool = False
    imp_vivienda: bool = False
    imp_agropecuario: bool = False
    imp_proteccion: bool = False
    imp_necesidades: bool = False
    impacto_poblacion: list[ImpactoPoblacion] = []
    necesidad_primera_respuesta: PrimeraRespuesta | None = None
    establecimientos_salud: list[EstablecimientoSalud] | None = None
    necesidad_salud: NecesidadSalud | None = None
    danos_viales: list[DanoVial] | None = None
    danos_infra_publica: list[DanoInfraPublica] | None = None
    servicios_basicos: list[ServicioBasicoDetalle] | None = None
    unidades_educativas: list[UnidadEducativa] | None = None
    danos_vivienda: list[DanoVivienda] | None = None
    danos_agricultura: list[DanoAgricultura] | None = None
    danos_pecuarios: list[DanoPecuario] | None = None
    infra_productiva: list[InfraProductiva] | None = None
    proteccion: list[GrupoVulnerable] = []
    necesidad_humanitaria: NecesidadHumanitaria | None = None


# ============================================================================
#  CATÁLOGOS
# ============================================================================

class TipoEventoCreate(BaseModel):
    nombre: str
    descripcion: str | None = None


class TipoEventoUpdate(BaseModel):
    nombre: str | None = None
    descripcion: str | None = None


class TipoEventoResponse(BaseModel):
    id_tipo_evento: int
    nombre: str
    descripcion: str | None = None

    class Config:
        from_attributes = True


class EstadoEdanCreate(BaseModel):
    nombre: str
    descripcion: str | None = None
    orden: int = 0


class EstadoEdanUpdate(BaseModel):
    nombre: str | None = None
    descripcion: str | None = None
    orden: int | None = None


class EstadoEdanResponse(BaseModel):
    id_estado: int
    nombre: str
    descripcion: str | None = None
    orden: int = 0

    class Config:
        from_attributes = True


class TipoLocalidadCreate(BaseModel):
    nombre: str
    descripcion: str | None = None
    orden: int = 0


class TipoLocalidadUpdate(BaseModel):
    nombre: str | None = None
    descripcion: str | None = None
    orden: int | None = None


class EdanLocalidadEstadoCreate(BaseModel):
    nombre: str
    descripcion: str | None = None
    orden: int = 0


class EdanLocalidadEstadoUpdate(BaseModel):
    nombre: str | None = None
    descripcion: str | None = None
    orden: int | None = None


class EdanSyncIn(BaseModel):
    edans: list[EdanCreate] = []


# ============================================================================
#  CONSOLIDACIÓN Y CAMBIO DE ESTADO DE LOCALIDAD
# ============================================================================

class LocalidadEstadoUpdate(BaseModel):
    id_edan_localidad_estado: int


class ConsolidarIn(BaseModel):
    id_municipio: int
    id_tipo_evento: int
    localidad_ids: list[int] = []


class LocalidadSyncIn(BaseModel):
    localidades: list[LocalidadCreate] = []

