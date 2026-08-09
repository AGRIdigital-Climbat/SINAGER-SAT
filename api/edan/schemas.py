from pydantic import BaseModel, Field


# ============================================================================
#  MODELOS ANIDADOS DEL FORMULARIO EDAN
#  Espejo de lib/models/edan.dart (nombres JSON exactos de la app).
# ============================================================================

class GrupoEtarioDetalle(BaseModel):
    rango: str = ''
    fallecidos: int = 0
    heridos: int = 0
    desaparecidos: int = 0
    observaciones: str = ''


class ImpactoPoblacion(BaseModel):
    grupo_etario: str = ''
    fallecidos: int = 0
    heridos: int = 0
    desaparecidos: int = 0
    observaciones: str = ''
    grupos_etarios: list[GrupoEtarioDetalle] = []


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


class NecesidadSalud(BaseModel):
    botiquines: bool = False
    numero_personas: int = 0
    otras_necesidades: str = ''
    observaciones: str = ''


class DanoVial(BaseModel):
    via_puente: str = ''
    tramo: str = ''
    dano_parcial: bool = False
    dano_total: bool = False
    km_danio: float | None = 0
    necesidades_inmediatas: str = ''
    observaciones: str = ''


class DanoInfraPublica(BaseModel):
    comunidad: str = ''
    tipo_estructura: str = ''
    dano_parcial: bool = False
    dano_total: bool = False
    observaciones: str = ''


class ServicioBasicoDetalle(BaseModel):
    tipo: str = ''
    afectado: bool = False
    dano_parcial: bool = False
    dano_total: bool = False
    necesidades_inmediatas: str = ''
    observaciones: str = ''


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


class DanoVivienda(BaseModel):
    comunidad: str = ''
    dano_parcial: int = 0
    dano_total: int = 0
    necesidades_inmediatas: str = ''
    observaciones: str = ''


class DanoAgricultura(BaseModel):
    tipo_cultivo: str = ''
    id_cultivo: int | None = None
    hectareas_afectadas: int = 0
    hectareas_perdidas: int = 0
    necesidades_inmediatas: str = ''
    observaciones: str = ''


class DanoPecuario(BaseModel):
    especie: str = ''
    id_especie: int | None = None
    raza: str = ''
    animales_afectados: int = 0
    animales_muertos: int = 0
    necesidades_inmediatas: str = ''


class InfraProductiva(BaseModel):
    tipo: str = ''
    dano_parcial: int = 0
    dano_total: int = 0


class GrupoVulnerable(BaseModel):
    mujeres: int = 0
    hombres: int = 0
    apoyo_psicologico: bool | None = None
    reposicion_documentos: bool | None = None
    observaciones: str = ''


class Vulnerables(BaseModel):
    ninos: GrupoVulnerable = GrupoVulnerable()
    adolescentes: GrupoVulnerable = GrupoVulnerable()
    mujeres_lactantes: GrupoVulnerable = GrupoVulnerable()
    mujeres_embarazadas: GrupoVulnerable = GrupoVulnerable()
    adultos_mayores: GrupoVulnerable = GrupoVulnerable()
    personas_discapacidad: GrupoVulnerable = GrupoVulnerable()
    personas_enfermedad: GrupoVulnerable = GrupoVulnerable()


class Proteccion(BaseModel):
    vulnerables: Vulnerables = Vulnerables()


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
    tipo_localidad: str = ''
    nombre: str = ''
    imp_poblacion: bool = False
    imp_salud: bool = False
    imp_infraestructura: bool = False
    imp_servicios: bool = False
    imp_educacion: bool = False
    imp_vivienda: bool = False
    imp_agropecuario: bool = False
    imp_proteccion: bool = False
    imp_necesidades: bool = False
    impacto_poblacion: ImpactoPoblacion | None = None
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
    proteccion: Proteccion | None = None
    necesidad_humanitaria: NecesidadHumanitaria | None = None


class EdanCreate(BaseModel):
    id_local: str | None = None
    id_server: int | None = None
    fecha_modificacion: str | None = None
    codigo_edan: str | None = None
    id_usuario: int | None = None
    id_departamento: int | None = None
    id_provincia: int | None = None
    id_municipio: int | None = None
    departamento_nombre: str | None = None
    provincia_nombre: str | None = None
    municipio_nombre: str | None = None
    nombre_alcalde: str = ''
    fono_alcalde: str = ''
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
    sincronizado: bool = False
    pendiente_eliminacion: bool = False
    pendiente_actualizacion: bool = False
    es_borrador: bool = False
    id_reporte_rea: int | None = None
    fotografia: str | None = None


class EdanUpdate(BaseModel):
    id_local: str | None = None
    id_server: int | None = None
    fecha_modificacion: str | None = None
    codigo_edan: str | None = None
    id_usuario: int | None = None
    id_departamento: int | None = None
    id_provincia: int | None = None
    id_municipio: int | None = None
    nombre_alcalde: str | None = None
    fono_alcalde: str | None = None
    fecha_llenado: str | None = None
    fecha_evento: str | None = None
    hora_evento: str | None = None
    total_poblacion_afectada: int | None = None
    total_familias_afectadas: int | None = None
    total_familias_damnificadas: int | None = None
    id_tipo_evento: int | None = None
    id_estado: int | None = None
    estado: str | None = None
    sincronizado: bool | None = None
    pendiente_eliminacion: bool | None = None
    pendiente_actualizacion: bool | None = None
    es_borrador: bool | None = None
    responsable: Responsable | None = None
    id_reporte_rea: int | None = None
    fotografia: str | None = None


class LocalidadUpdate(BaseModel):
    tipo_localidad: str = ''
    nombre: str = ''
    imp_poblacion: bool = False
    imp_salud: bool = False
    imp_infraestructura: bool = False
    imp_servicios: bool = False
    imp_educacion: bool = False
    imp_vivienda: bool = False
    imp_agropecuario: bool = False
    imp_proteccion: bool = False
    imp_necesidades: bool = False
    impacto_poblacion: ImpactoPoblacion | None = None
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
    proteccion: Proteccion | None = None
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


class EdanSyncIn(BaseModel):
    edans: list[EdanCreate] = []
