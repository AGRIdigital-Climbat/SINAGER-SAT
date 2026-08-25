from pydantic import BaseModel, Field


# ============================================================================
#  MODELOS ANIDADOS DEL FORMULARIO EDAN
#  Reflejan EXACTAMENTE el esquema de las tablas edan.edan_localidades_*
#  Los IDs (id_edan_localidad, id_establecimiento_salud, etc.) los asigna
#  el servicio al insertar — el cliente NO los envía.
# ============================================================================

class ImpactoPoblacion(BaseModel):
    """→ edan.edan_localidades_impacto_poblacion (1:N por rango etario)."""
    id_seccion: str | None = Field(None, description="ID único offline (generado por cliente). Ej: '1a0357323cb-659d0c9c3d415'")
    rango: str = Field('', description="Ej: 'Niño 0-5', 'Adulto 19-60', 'Adulto mayor 60+'")
    fallecidos: int = Field(0, ge=0)
    heridos: int = Field(0, ge=0)
    desaparecidos: int = Field(0, ge=0)
    observaciones: str = ''


class PrimeraRespuesta(BaseModel):
    """→ edan.edan_localidades_primera_respuesta (1:1 por localidad)."""
    id_seccion: str | None = Field(None, description="ID único offline (generado por cliente)")
    busqueda: bool = False
    salvamento: bool = False
    evacuacion: bool = False
    observaciones: str = ''


class EstablecimientoSalud(BaseModel):
    """→ edan.edan_localidades_salud_establecimientos (1:N)."""
    id_seccion: str | None = Field(None, description="ID único offline (generado por cliente). Ej: '1a0357323cb-659d0c9c3d415'")
    nombre_establecimiento: str = ''
    comunidad: str = ''
    nivel_atencion: str = Field('', description="Ej: '1er Nivel', '2do Nivel', '3er Nivel'")
    dano_parcial: bool = False
    dano_total: bool = False
    medicos_afectados: int = Field(0, ge=0)
    enfermeras_afectadas: int = Field(0, ge=0, description="Columna BD: enfermeras_afectadas")
    otros_afectados: int = Field(0, ge=0)
    fotografia: str | None = Field(None, description="Path: /uploads/reports/{codigo_ine}/...")
    coordenada_lat: float | None = None
    coordenada_lon: float | None = None


class NecesidadSalud(BaseModel):
    """→ edan.edan_localidades_salud_necesidades (1:1)."""
    id_seccion: str | None = Field(None, description="ID único offline (generado por cliente)")
    numero_personas: int = Field(0, ge=0)
    otras_necesidades: str = ''
    observaciones: str = ''


class DanoVial(BaseModel):
    """→ edan.edan_localidades_danos_viales (1:N)."""
    id_seccion: str | None = Field(None, description="ID único offline (generado por cliente). Ej: '1a0357323cb-659d0c9c3d415'")
    via: bool = Field(False, description="Daño en vía/carretera")
    puente: bool = Field(False, description="Daño en puente")
    tramo: str = ''
    dano_parcial: bool = False
    dano_total: bool = False
    km_danio: float = Field(0, ge=0, description="Kilómetros de daño")
    necesidades_inmediatas: str = ''
    observaciones: str = ''
    fotografia: str | None = None
    coordenada_lat: float | None = None
    coordenada_lon: float | None = None


class DanoInfraPublica(BaseModel):
    """→ edan.edan_localidades_danos_infra_publica (1:N)."""
    id_seccion: str | None = Field(None, description="ID único offline (generado por cliente). Ej: '1a0357323cb-659d0c9c3d415'")
    comunidad: str = ''
    tipo_estructura: str = Field('', description="Ej: 'Alcaldía', 'Iglesia', 'Plaza'")
    dano_parcial: bool = False
    dano_total: bool = False
    observaciones: str = ''
    fotografia: str | None = None
    coordenada_lat: float | None = None
    coordenada_lon: float | None = None


class ServicioBasicoDetalle(BaseModel):
    """→ edan.edan_localidades_servicios_basicos (1:N).
    Valores válidos de tipo (CHECK constraint):
    'energia_electrica', 'agua_potable', 'alcantarillado', 'gas_domiciliario', 'telecomunicaciones'
    """
    id_seccion: str | None = Field(None, description="ID único offline (generado por cliente). Ej: '1a0357323cb-659d0c9c3d415'")
    tipo: str = Field('', description="energia_electrica|agua_potable|alcantarillado|gas_domiciliario|telecomunicaciones")
    dano_parcial: bool = False
    dano_total: bool = False
    necesidades_inmediatas: str = ''
    observaciones: str = ''
    fotografia: str | None = None
    coordenada_lat: float | None = None
    coordenada_lon: float | None = None


class UnidadEducativa(BaseModel):
    """→ edan.edan_localidades_unidades_educativas (1:N)."""
    id_seccion: str | None = Field(None, description="ID único offline (generado por cliente). Ej: '1a0357323cb-659d0c9c3d415'")
    nombre_establecimiento: str = ''
    comunidad: str = ''
    dano_parcial: bool = False
    dano_total: bool = False
    suspension_clases: bool | None = None
    perdida_material: bool | None = None
    funciona_albergue: bool | None = None
    estudiantes: int = Field(0, ge=0)
    profesores: int = Field(0, ge=0)
    administrativos: int = Field(0, ge=0)
    observaciones: str = ''
    fotografia: str | None = None
    coordenada_lat: float | None = None
    coordenada_lon: float | None = None


class DanoVivienda(BaseModel):
    """→ edan.edan_localidades_danos_vivienda (1:N).
    Cantidades de viviendas con daño parcial/total.
    """
    id_seccion: str | None = Field(None, description="ID único offline (generado por cliente). Ej: '1a0357323cb-659d0c9c3d415'")
    comunidad: str = ''
    dano_parcial: int = Field(0, ge=0)
    dano_total: int = Field(0, ge=0)
    necesidades_inmediatas: str = ''
    observaciones: str = ''
    fotografia: str | None = None
    coordenada_lat: float | None = None
    coordenada_lon: float | None = None


class DanoAgricultura(BaseModel):
    """→ edan.edan_localidades_danos_agricultura (1:N).
    Si id_cultivo está presente, se vincula al catálogo shared.cultivo.
    """
    id_seccion: str | None = Field(None, description="ID único offline (generado por cliente). Ej: '1a0357323cb-659d0c9c3d415'")
    tipo_cultivo: str = ''
    id_cultivo: int | None = Field(None, description="FK a shared.cultivo (opcional)")
    hectareas_afectadas: int = Field(0, ge=0)
    hectareas_perdidas: int = Field(0, ge=0)
    necesidades_inmediatas: str = ''
    observaciones: str = ''
    fotografia: str | None = None
    coordenada_lat: float | None = None
    coordenada_lon: float | None = None


class DanoPecuario(BaseModel):
    """→ edan.edan_localidades_danos_pecuario (1:N).
    Si id_especie está presente, se vincula al catálogo shared.pecuario.
    """
    id_seccion: str | None = Field(None, description="ID único offline (generado por cliente). Ej: '1a0357323cb-659d0c9c3d415'")
    especie: str = ''
    id_especie: int | None = Field(None, description="FK a shared.pecuario (opcional)")
    raza: str = ''
    animales_afectados: int = Field(0, ge=0)
    animales_muertos: int = Field(0, ge=0)
    necesidades_inmediatas: str = ''
    fotografia: str | None = None
    coordenada_lat: float | None = None
    coordenada_lon: float | None = None


class InfraProductiva(BaseModel):
    """→ edan.edan_localidades_infra_productiva (1:N)."""
    id_seccion: str | None = Field(None, description="ID único offline (generado por cliente). Ej: '1a0357323cb-659d0c9c3d415'")
    tipo: str = Field('', description="Ej: 'Molino', 'Almacén', 'Tienda comunitaria'")
    dano_parcial: int = Field(0, ge=0)
    dano_total: int = Field(0, ge=0)
    fotografia: str | None = None
    coordenada_lat: float | None = None
    coordenada_lon: float | None = None


class GrupoVulnerable(BaseModel):
    """→ edan.edan_localidades_proteccion (1:N por grupo vulnerable).
    Ahora vinculado a catálogo edan.grupo_vulnerable via FK.
    """
    id_seccion: str | None = Field(None, description="ID único offline (generado por cliente). Ej: '1a0357323cb-659d0c9c3d415'")
    id_grupo_vulnerable: int | None = None  # PK técnica (serial)
    id_grupo_vulnerable_catalogo: int | None = None  # FK a edan.grupo_vulnerable
    grupo: dict | None = None  # { id, codigo, nombre, orden } (catálogo anidado)
    mujeres: int = Field(0, ge=0)
    hombres: int = Field(0, ge=0)
    total: int = Field(0, ge=0, description="Calculado: mujeres + hombres")
    apoyo_psicologico: bool | None = None
    reposicion_documentos: bool | None = None
    observaciones: str = ''


class NecesidadHumanitaria(BaseModel):
    """→ edan.edan_localidades_necesidades_humanitarias (1:1).
    Cada bool indica si se requiere esa ayuda. Cada obs_* es texto libre.
    """
    id_seccion: str | None = Field(None, description="ID único offline (generado por cliente)")
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
    """Datos del responsable del EDAN (cabecera del formulario)."""
    nombre: str = ''
    cargo: str = ''
    fono: str = ''
    correo: str = ''


class LocalidadCreate(BaseModel):
    """Schema para CREAR una EDAN localidad.
    → edan.edan_localidades (cabecera) + secciones 1:N / 1:1 opcionales.

    IDs locales (id_edan_localidad, id_local, id_usuario) los asigna el servicio.
    Las secciones son OPCIONALES: una granizada puede afectar solo agricultura
    y no daños_vivienda. Si una sección no se envía, simplemente no se crea.
    """
    id_tipo_localidad: int | None = Field(None, description="FK a edan.tipo_localidad")
    id_edan_localidad_estado: int | None = Field(None, description="FK a edan.edan_localidades_estado")
    tipo_localidad: str | None = Field(None, description="Nombre libre (alternativa al id)")
    id_tipo_evento: int | None = Field(None, description="FK a edan.tipo_evento")
    id_departamento: int | None = Field(None, description="FK a shared.departamento")
    id_provincia: int | None = Field(None, description="FK a shared.provincia")
    id_municipio: int | None = Field(None, description="FK a shared.municipio")
    fecha_llenado: str | None = Field(None, description="ISO date YYYY-MM-DD")
    fecha_evento: str | None = Field(None, description="ISO date YYYY-MM-DD")
    hora_evento: str | None = Field(None, description="HH:MM:SS")
    total_poblacion_afectada: int = Field(0, ge=0)
    total_familias_afectadas: int = Field(0, ge=0)
    total_familias_damnificadas: int = Field(0, ge=0)
    id_local: str | None = Field(None, description="UUID del móvil (offline-first dedupe)")
    id_usuario: int | None = Field(None, description="Asignado por el servidor si no se envía")
    fecha_modificacion: str | None = Field(None, description="ISO timestamp")
    pendiente_actualizacion: bool = False
    pendiente_eliminacion: bool = False
    localidad: str = Field('', description="Nombre de la comunidad/barrio/ciudad")
    imp_poblacion: bool = Field(False, description="¿Hubo impacto en población?")
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


class GrupoVulnerableCreate(BaseModel):
    codigo: str
    nombre: str
    descripcion: str | None = None
    orden: int = 0
    activo: bool = True


class GrupoVulnerableUpdate(BaseModel):
    codigo: str | None = None
    nombre: str | None = None
    descripcion: str | None = None
    orden: int | None = None
    activo: bool | None = None


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

