from pydantic import BaseModel, Field, ConfigDict
from typing import Literal

from ..response import SuccessResponse


# ============================================================================
#  MODELOS ANIDADOS DEL FORMULARIO EDAN
#  Reflejan EXACTAMENTE el esquema de las tablas edan.edan_localidades_*
#  Los IDs (id_edan_localidad, id_establecimiento_salud, etc.) los asigna
#  el servicio al insertar — el cliente NO los envía.
# ============================================================================

class ImpactoPoblacion(BaseModel):
    """→ edan.edan_localidades_impacto_poblacion (1:N por grupo etario).
    La fuente de verdad es id_grupo_etario (FK a edan.grupo_etario).
    El campo rango se mantiene solo por compatibilidad de lectura en v1 (calculado)."""
    id_seccion: str | None = Field(None, description="ID único offline (generado por cliente). Ej: '1a0357323cb-659d0c9c3d415'")
    fecha_modificacion: str | None = Field(None, description="ISO timestamp UTC de la última edición local de la fila (LWW). Formato ISO 8601, ej: '2026-09-02T09:15:00Z'")
    id_grupo_etario: int | None = Field(None, description="FK a edan.grupo_etario (recomendado). Si falta, se resuelve por rango/codigo.")
    rango: str | None = Field(None, description="DEPRECATED: usar id_grupo_etario. Solo se acepta para compatibilidad v1 (resolución por nombre).")
    fallecidos: int = Field(0, ge=0)
    heridos: int = Field(0, ge=0)
    desaparecidos: int = Field(0, ge=0)
    observaciones: str = ''


class PrimeraRespuesta(BaseModel):
    """→ edan.edan_localidades_primera_respuesta (1:1 por localidad)."""
    id_seccion: str | None = Field(None, description="ID único offline (generado por cliente)")
    fecha_modificacion: str | None = Field(None, description="ISO timestamp UTC de la última edición local de la fila (LWW). Formato ISO 8601, ej: '2026-09-02T09:15:00Z'")
    busqueda: bool = False
    salvamento: bool = False
    evacuacion: bool = False
    observaciones: str = ''


class EstablecimientoSalud(BaseModel):
    """→ edan.edan_localidades_salud_establecimientos (1:N)."""
    id_seccion: str | None = Field(None, description="ID único offline (generado por cliente). Ej: '1a0357323cb-659d0c9c3d415'")
    fecha_modificacion: str | None = Field(None, description="ISO timestamp UTC de la última edición local de la fila (LWW). Formato ISO 8601, ej: '2026-09-02T09:15:00Z'")
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
    fecha_modificacion: str | None = Field(None, description="ISO timestamp UTC de la última edición local de la fila (LWW). Formato ISO 8601, ej: '2026-09-02T09:15:00Z'")
    numero_personas: int = Field(0, ge=0)
    otras_necesidades: str = ''
    observaciones: str = ''


class DanoVial(BaseModel):
    """→ edan.edan_localidades_danos_viales (1:N)."""
    id_seccion: str | None = Field(None, description="ID único offline (generado por cliente). Ej: '1a0357323cb-659d0c9c3d415'")
    fecha_modificacion: str | None = Field(None, description="ISO timestamp UTC de la última edición local de la fila (LWW). Formato ISO 8601, ej: '2026-09-02T09:15:00Z'")
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
    fecha_modificacion: str | None = Field(None, description="ISO timestamp UTC de la última edición local de la fila (LWW). Formato ISO 8601, ej: '2026-09-02T09:15:00Z'")
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
    fecha_modificacion: str | None = Field(None, description="ISO timestamp UTC de la última edición local de la fila (LWW). Formato ISO 8601, ej: '2026-09-02T09:15:00Z'")
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
    fecha_modificacion: str | None = Field(None, description="ISO timestamp UTC de la última edición local de la fila (LWW). Formato ISO 8601, ej: '2026-09-02T09:15:00Z'")
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
    fecha_modificacion: str | None = Field(None, description="ISO timestamp UTC de la última edición local de la fila (LWW). Formato ISO 8601, ej: '2026-09-02T09:15:00Z'")
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
    fecha_modificacion: str | None = Field(None, description="ISO timestamp UTC de la última edición local de la fila (LWW). Formato ISO 8601, ej: '2026-09-02T09:15:00Z'")
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
    fecha_modificacion: str | None = Field(None, description="ISO timestamp UTC de la última edición local de la fila (LWW). Formato ISO 8601, ej: '2026-09-02T09:15:00Z'")
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
    fecha_modificacion: str | None = Field(None, description="ISO timestamp UTC de la última edición local de la fila (LWW). Formato ISO 8601, ej: '2026-09-02T09:15:00Z'")
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
    fecha_modificacion: str | None = Field(None, description="ISO timestamp UTC de la última edición local de la fila (LWW). Formato ISO 8601, ej: '2026-09-02T09:15:00Z'")
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
    fecha_modificacion: str | None = Field(None, description="ISO timestamp UTC de la última edición local de la fila (LWW). Formato ISO 8601, ej: '2026-09-02T09:15:00Z'")
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


# ============================================================================
#  MODELOS DEL DOCUMENTO TODO-EN-UNO v2 (edan_local_completo / /documento).
#  Iguales a las secciones compartidas (v1) pero con `id_seccion` REQUERIDO:
#  en el flujo v2 el único identificador es `id_seccion` (UUID offline generado
#  por el cliente). El backend NUNCA lo genera; si la app no lo envía, 400.
#  Estos modelos solo se usan en POST/PUT/GET /documento y el response.
#  NO tocan los modelos compartidos v1 (id_seccion sigue opcional ahí).
# ============================================================================

class ImpactoPoblacionDoc(ImpactoPoblacion):
    id_seccion: str = Field(..., description="REQUERIDO v2: ID único offline (UUID generado por el cliente). El backend no lo genera.")

class PrimeraRespuestaDoc(PrimeraRespuesta):
    id_seccion: str = Field(..., description="REQUERIDO v2: ID único offline (UUID generado por el cliente). El backend no lo genera.")

class EstablecimientoSaludDoc(EstablecimientoSalud):
    id_seccion: str = Field(..., description="REQUERIDO v2: ID único offline (UUID generado por el cliente). El backend no lo genera.")

class NecesidadSaludDoc(NecesidadSalud):
    id_seccion: str = Field(..., description="REQUERIDO v2: ID único offline (UUID generado por el cliente). El backend no lo genera.")

class DanoVialDoc(DanoVial):
    id_seccion: str = Field(..., description="REQUERIDO v2: ID único offline (UUID generado por el cliente). El backend no lo genera.")

class DanoInfraPublicaDoc(DanoInfraPublica):
    id_seccion: str = Field(..., description="REQUERIDO v2: ID único offline (UUID generado por el cliente). El backend no lo genera.")

class ServicioBasicoDetalleDoc(ServicioBasicoDetalle):
    id_seccion: str = Field(..., description="REQUERIDO v2: ID único offline (UUID generado por el cliente). El backend no lo genera.")

class UnidadEducativaDoc(UnidadEducativa):
    id_seccion: str = Field(..., description="REQUERIDO v2: ID único offline (UUID generado por el cliente). El backend no lo genera.")

class DanoViviendaDoc(DanoVivienda):
    id_seccion: str = Field(..., description="REQUERIDO v2: ID único offline (UUID generado por el cliente). El backend no lo genera.")

class DanoAgriculturaDoc(DanoAgricultura):
    id_seccion: str = Field(..., description="REQUERIDO v2: ID único offline (UUID generado por el cliente). El backend no lo genera.")

class DanoPecuarioDoc(DanoPecuario):
    id_seccion: str = Field(..., description="REQUERIDO v2: ID único offline (UUID generado por el cliente). El backend no lo genera.")

class InfraProductivaDoc(InfraProductiva):
    id_seccion: str = Field(..., description="REQUERIDO v2: ID único offline (UUID generado por el cliente). El backend no lo genera.")

class GrupoVulnerableDoc(BaseModel):
    """→ edan.edan_localidades_proteccion (1:N por grupo vulnerable) — v2 documento.
    Definido sin herencia para NO exponer la PK interna `id_grupo_vulnerable`."""
    id_seccion: str = Field(..., description="REQUERIDO v2: ID único offline (UUID generado por el cliente). El backend no lo genera.")
    fecha_modificacion: str | None = Field(None, description="ISO timestamp UTC de la última edición local de la fila (LWW). Formato ISO 8601, ej: '2026-09-02T09:15:00Z'")
    id_grupo_vulnerable_catalogo: int | None = None  # FK a edan.grupo_vulnerable
    grupo: dict | None = None  # { id, codigo, nombre, orden } (catálogo anidado)
    mujeres: int = Field(0, ge=0)
    hombres: int = Field(0, ge=0)
    total: int = Field(0, ge=0, description="Calculado: mujeres + hombres")
    apoyo_psicologico: bool | None = None
    reposicion_documentos: bool | None = None
    observaciones: str = ''

class NecesidadHumanitariaDoc(NecesidadHumanitaria):
    id_seccion: str = Field(..., description="REQUERIDO v2: ID único offline (UUID generado por el cliente). El backend no lo genera.")


class LocalidadDocumentoCreate(BaseModel):
    """Entrada POST/PUT /documento v2 (todo-en-uno, SIEMPRE COMPACTO).

    Igual que el `LocalidadCreate` compartido (v1) pero aquí CADA sección usa su
    modelo Doc con `id_seccion` REQUERIDO. La forma es la misma que la salida
    (`LocalidadDocumentoResponse`), por eso es un JSON simétrico ready-to-send.
    El único identificador de sección es `id_seccion` (UUID offline del cliente).
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
    fecha_modificacion: str | None = Field(None, description="ISO timestamp (LWW top-level)")
    pendiente_actualizacion: bool = False
    pendiente_eliminacion: bool = False
    localidad: str = Field('', description="Nombre de la comunidad/barrio/ciudad")
    imp_poblacion: bool = Field(False, description="legacy agrupado")
    imp_salud: bool = Field(False, description="legacy agrupado")
    imp_infraestructura: bool = Field(False, description="legacy agrupado")
    imp_servicios: bool = Field(False, description="legacy agrupado")
    imp_educacion: bool = Field(False, description="legacy agrupado")
    imp_vivienda: bool = Field(False, description="legacy agrupado")
    imp_agropecuario: bool = Field(False, description="legacy agrupado")
    imp_proteccion: bool = Field(False, description="¿impacto en protección?")
    imp_necesidades: bool = Field(False, description="legacy agrupado")
    imp_impacto_poblacion: bool = Field(False, description="1:1 impacto-poblacion")
    imp_salud_establecimientos: bool = Field(False, description="1:1 salud-establecimientos")
    imp_danos_viales: bool = Field(False, description="1:1 danos-viales")
    imp_danos_infra_publica: bool = Field(False, description="1:1 danos-infra-publica")
    imp_servicios_basicos: bool = Field(False, description="1:1 servicios-basicos")
    imp_unidades_educativas: bool = Field(False, description="1:1 unidades-educativas")
    imp_danos_vivienda: bool = Field(False, description="1:1 danos-vivienda")
    imp_danos_agricultura: bool = Field(False, description="1:1 danos-agricultura")
    imp_danos_pecuarios: bool = Field(False, description="1:1 danos-pecuarios")
    imp_infra_productiva: bool = Field(False, description="1:1 infra-productiva")
    imp_primera_respuesta: bool = Field(False, description="1:1 primera-respuesta")
    imp_necesidad_salud: bool = Field(False, description="1:1 necesidad-salud")
    imp_necesidad_humanitaria: bool = Field(False, description="1:1 necesidad-humanitaria")
    # 1:N y 1:1 — forma fija (11 array / 3 objeto), cada sección con id_seccion REQUERIDO.
    impacto_poblacion: list[ImpactoPoblacionDoc] | dict | None = None
    necesidad_primera_respuesta: PrimeraRespuestaDoc | list[dict] | None = None
    establecimientos_salud: list[EstablecimientoSaludDoc] | dict | None = None
    necesidad_salud: NecesidadSaludDoc | list[dict] | None = None
    danos_viales: list[DanoVialDoc] | dict | None = None
    danos_infra_publica: list[DanoInfraPublicaDoc] | dict | None = None
    servicios_basicos: list[ServicioBasicoDetalleDoc] | dict | None = None
    unidades_educativas: list[UnidadEducativaDoc] | dict | None = None
    danos_vivienda: list[DanoViviendaDoc] | dict | None = None
    danos_agricultura: list[DanoAgriculturaDoc] | dict | None = None
    danos_pecuarios: list[DanoPecuarioDoc] | dict | None = None
    infra_productiva: list[InfraProductivaDoc] | dict | None = None
    proteccion: list[GrupoVulnerableDoc] | dict | None = None
    necesidad_humanitaria: NecesidadHumanitariaDoc | list[dict] | None = None


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
    imp_poblacion: bool = Field(False, description="¿Hubo impacto en población? (legacy agrupado)")
    imp_salud: bool = Field(False, description="legacy agrupado")
    imp_infraestructura: bool = Field(False, description="legacy agrupado")
    imp_servicios: bool = Field(False, description="legacy agrupado")
    imp_educacion: bool = Field(False, description="legacy agrupado")
    imp_vivienda: bool = Field(False, description="legacy agrupado")
    imp_agropecuario: bool = Field(False, description="legacy agrupado")
    imp_proteccion: bool = Field(False, description="¿impacto en protección?")
    imp_necesidades: bool = Field(False, description="legacy agrupado")
    imp_impacto_poblacion: bool = Field(False, description="1:1 impacto-poblacion")
    imp_salud_establecimientos: bool = Field(False, description="1:1 salud-establecimientos")
    imp_danos_viales: bool = Field(False, description="1:1 danos-viales")
    imp_danos_infra_publica: bool = Field(False, description="1:1 danos-infra-publica")
    imp_servicios_basicos: bool = Field(False, description="1:1 servicios-basicos")
    imp_unidades_educativas: bool = Field(False, description="1:1 unidades-educativas")
    imp_danos_vivienda: bool = Field(False, description="1:1 danos-vivienda")
    imp_danos_agricultura: bool = Field(False, description="1:1 danos-agricultura")
    imp_danos_pecuarios: bool = Field(False, description="1:1 danos-pecuarios")
    imp_infra_productiva: bool = Field(False, description="1:1 infra-productiva")
    imp_primera_respuesta: bool = Field(False, description="1:1 primera-respuesta")
    imp_necesidad_salud: bool = Field(False, description="1:1 necesidad-salud")
    imp_necesidad_humanitaria: bool = Field(False, description="1:1 necesidad-humanitaria")
    # 1:N y 1:1 — entrada LAXA (aceptan objeto o array según lo que mande la app).
    # service.normalize_seccion_doc impone la FORMA FIJA (11 array / 3 objeto),
    # y rechaza (HTTP 400 con mensaje) o acepta según el contrato.
    impacto_poblacion: list[ImpactoPoblacion] | dict | None = None
    necesidad_primera_respuesta: PrimeraRespuesta | list[dict] | None = None
    establecimientos_salud: list[EstablecimientoSalud] | dict | None = None
    necesidad_salud: NecesidadSalud | list[dict] | None = None
    danos_viales: list[DanoVial] | dict | None = None
    danos_infra_publica: list[DanoInfraPublica] | dict | None = None
    servicios_basicos: list[ServicioBasicoDetalle] | dict | None = None
    unidades_educativas: list[UnidadEducativa] | dict | None = None
    danos_vivienda: list[DanoVivienda] | dict | None = None
    danos_agricultura: list[DanoAgricultura] | dict | None = None
    danos_pecuarios: list[DanoPecuario] | dict | None = None
    infra_productiva: list[InfraProductiva] | dict | None = None
    proteccion: list[GrupoVulnerable] | dict | None = None
    necesidad_humanitaria: NecesidadHumanitaria | list[dict] | None = None


# ----------------------------------------------------------------------------
#  DOCUMENTO COMPLETO (grupo exclusivo v2).
#  JSON simétrico: GET /documento devuelve lo que POST/PUT /documento aceptan.
#  - Secciones SOLO presentes si su flag imp_* = true (o hay datos).
#  - Forma fija: 11 secciones array (aunque venga 1 solo), 3 secciones objeto.
#  - En la SALIDA (modo comprimido) las secciones sin datos se omiten (None).
# ----------------------------------------------------------------------------

class LocalidadDocumentoResponse(BaseModel):
    """Documento completo de una localidad (salida del GET /documento).

    Es como LocalidadCreate pero con las secciones OPCIONALES (None si no hay
    datos / flag false): refleja el `modo=comprimido` usado por el sync.
    La cabecera trae los 23 flags imp_* y `fecha_modificacion` top-level; cada
    sección presente lleva su propia `fecha_modificacion` (LWW por fila).
    """
    id_edan_localidad: int | None = None
    id_edan: int | None = None
    es_huerfana: bool = True
    id_tipo_localidad: int | None = None
    id_edan_localidad_estado: int | None = None
    tipo_localidad: dict | None = None
    id_tipo_evento: int | None = None
    tipo_evento: dict | None = None
    id_departamento: int | None = None
    id_provincia: int | None = None
    id_municipio: int | None = None
    departamento: dict | None = None
    provincia: dict | None = None
    municipio: dict | None = None
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
    edan: dict | None = None
    # 23 flags imp_* (9 legacy + 14 1:1)
    imp_poblacion: bool = False
    imp_salud: bool = False
    imp_infraestructura: bool = False
    imp_servicios: bool = False
    imp_educacion: bool = False
    imp_vivienda: bool = False
    imp_agropecuario: bool = False
    imp_proteccion: bool = False
    imp_necesidades: bool = False
    imp_impacto_poblacion: bool = False
    imp_salud_establecimientos: bool = False
    imp_danos_viales: bool = False
    imp_danos_infra_publica: bool = False
    imp_servicios_basicos: bool = False
    imp_unidades_educativas: bool = False
    imp_danos_vivienda: bool = False
    imp_danos_agricultura: bool = False
    imp_danos_pecuarios: bool = False
    imp_infra_productiva: bool = False
    imp_primera_respuesta: bool = False
    imp_necesidad_salud: bool = False
    imp_necesidad_humanitaria: bool = False
    # Secciones (forma fija): 11 array + 3 objeto; None si sin datos (comprimido).
    # Solo `id_seccion` (UUID offline) las identifica; sin IDs internos del backend.
    impacto_poblacion: list[ImpactoPoblacionDoc] | None = None
    establecimientos_salud: list[EstablecimientoSaludDoc] | None = None
    danos_viales: list[DanoVialDoc] | None = None
    danos_infra_publica: list[DanoInfraPublicaDoc] | None = None
    servicios_basicos: list[ServicioBasicoDetalleDoc] | None = None
    unidades_educativas: list[UnidadEducativaDoc] | None = None
    danos_vivienda: list[DanoViviendaDoc] | None = None
    danos_agricultura: list[DanoAgriculturaDoc] | None = None
    danos_pecuarios: list[DanoPecuarioDoc] | None = None
    infra_productiva: list[InfraProductivaDoc] | None = None
    proteccion: list[GrupoVulnerableDoc] | None = None
    necesidad_primera_respuesta: PrimeraRespuestaDoc | None = None
    necesidad_salud: NecesidadSaludDoc | None = None
    necesidad_humanitaria: NecesidadHumanitariaDoc | None = None


class LocalidadCabeceraCreate(BaseModel):
    """Schema para el sync incremental POR SECCIONES: crea o actualiza SOLO la
    cabecera del edan_localidades. Nunca toca secciones.

    Es la 1ra escritura del flujo móvil: devuelve `id_edan_localidad` para
    poder enviar las secciones después. `id_local` (UUID offline) es la clave
    de dedupe: si ya existe, se actualiza la cabecera; si no, se crea.

    Ejemplo offline (1er sync sin conexión):
    {
      "id_local": "3b2f9c1e-8a67-4d2e-9f01-c4d8a3b2e7f0",
      "localidad": "Comunidad Nuevo Amanecer",
      "id_municipio": 70101,
      "id_departamento": 7,
      "id_provincia": 701,
      "id_tipo_evento": 7,
      "id_tipo_localidad": 2,
      "total_poblacion_afectada": 255,
      "total_familias_afectadas": 60,
      "total_familias_damnificadas": 30,
      "imp_poblacion": true,
      "imp_agropecuario": true
    }
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
    localidad: str = Field('', description="Nombre de la comunidad/barrio/ciudad")
    imp_poblacion: bool = Field(False, description="¿Hubo impacto en población? (legacy agrupado)")
    imp_salud: bool = Field(False, description="legacy agrupado")
    imp_infraestructura: bool = Field(False, description="legacy agrupado")
    imp_servicios: bool = Field(False, description="legacy agrupado")
    imp_educacion: bool = Field(False, description="legacy agrupado")
    imp_vivienda: bool = Field(False, description="legacy agrupado")
    imp_agropecuario: bool = Field(False, description="legacy agrupado")
    imp_proteccion: bool = Field(False, description="¿impacto en protección?")
    imp_necesidades: bool = Field(False, description="legacy agrupado")
    imp_impacto_poblacion: bool = Field(False, description="1:1 impacto-poblacion")
    imp_salud_establecimientos: bool = Field(False, description="1:1 salud-establecimientos")
    imp_danos_viales: bool = Field(False, description="1:1 danos-viales")
    imp_danos_infra_publica: bool = Field(False, description="1:1 danos-infra-publica")
    imp_servicios_basicos: bool = Field(False, description="1:1 servicios-basicos")
    imp_unidades_educativas: bool = Field(False, description="1:1 unidades-educativas")
    imp_danos_vivienda: bool = Field(False, description="1:1 danos-vivienda")
    imp_danos_agricultura: bool = Field(False, description="1:1 danos-agricultura")
    imp_danos_pecuarios: bool = Field(False, description="1:1 danos-pecuarios")
    imp_infra_productiva: bool = Field(False, description="1:1 infra-productiva")
    imp_primera_respuesta: bool = Field(False, description="1:1 primera-respuesta")
    imp_necesidad_salud: bool = Field(False, description="1:1 necesidad-salud")
    imp_necesidad_humanitaria: bool = Field(False, description="1:1 necesidad-humanitaria")


class LocalidadEstadoUpdateV2(BaseModel):
    """Schema para cambiar el estado de una localidad en V2 usando id_local.

    Ejemplo (móvil envía estado tras revisión):
    {
      "id_local": "3b2f9c1e-8a67-4d2e-9f01-c4d8a3b2e7f0",
      "id_edan_localidad_estado": 2
    }
    """
    id_local: str = Field(..., description="UUID del móvil (clave offline)",
                          json_schema_extra={"example": "3b2f9c1e-8a67-4d2e-9f01-c4d8a3b2e7f0"})
    id_edan_localidad_estado: int = Field(..., ge=1, le=6,
        description="Estado: 1=Borrador, 2=Enviado UGR, 3=Aprobado UGR, 4=Rechazado UGR, 5=Aprobado Ajuste UGR, 6=En revisión UGR",
        json_schema_extra={"example": 2})


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
    imp_impacto_poblacion: bool = False
    imp_salud_establecimientos: bool = False
    imp_danos_viales: bool = False
    imp_danos_infra_publica: bool = False
    imp_servicios_basicos: bool = False
    imp_unidades_educativas: bool = False
    imp_danos_vivienda: bool = False
    imp_danos_agricultura: bool = False
    imp_danos_pecuarios: bool = False
    imp_infra_productiva: bool = False
    imp_primera_respuesta: bool = False
    imp_necesidad_salud: bool = False
    imp_necesidad_humanitaria: bool = False
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
    pendiente_actualizacion: bool | None = None,
    responsable: Responsable | None = None


class EdanUpdateV2(BaseModel):
    """Actualización de un EDAN consolidado (v2) — SOLO columnas reales de
    `edan.edan` (las mismas 17 que escribe `service.update_edan`).

    PUT parcial: todos los campos son opcionales (`exclude_unset`).
    - `id_usuario_alcalde`: int (FK a `usuarios.usuario`) asigna el alcalde.
    - No incluye `estado` (string), `responsable` ni `fecha_modificacion`:
      no son columnas de la tabla; `fecha_modificacion` la genera el servicio
      con `NOW()` en cada UPDATE.
    - `extra="forbid"`: campos desconocidos (p.ej. `nombre_alcalde`,
      `fono_alcalde`, `responsable`) devuelven 422 en vez de ignorarse.
    """
    model_config = ConfigDict(extra="forbid")

    id_local: str | None = None
    codigo_edan: str | None = None
    id_usuario_ugr: int | None = None
    id_usuario_alcalde: int | None = None
    id_departamento: int | None = None
    id_provincia: int | None = None
    id_municipio: int | None = None
    id_tipo_evento: int | None = None
    fecha_llenado: str | None = None
    fecha_evento: str | None = None
    hora_evento: str | None = None
    total_poblacion_afectada: int | None = None
    total_familias_afectadas: int | None = None
    total_familias_damnificadas: int | None = None
    id_estado: int | None = None
    pendiente_eliminacion: bool | None = None
    pendiente_actualizacion: bool | None = None,


class AprobacionEdan(BaseModel):
    """Modelo para las APIs de aprobación independientes (sin restricciones de rol).

    - `aprobado=true`  → aprueba el nivel.
    - `aprobado=false` → devuelve al nivel anterior (`observacion` obligatoria).
    """
    aprobado: bool
    observacion: str | None = None
    model_config = ConfigDict()


# --- Respuestas de la máquina de aprobaciones (v2.17.4) ----------------------
# El GET es una vista informativa: por cada nivel dice en qué estado está,
# quién lo aprobó y cuándo, y quién lo devolvió y cuándo. Los usuarios van
# embebidos (no solo el id) para que el frontend no haga llamadas extra.
# Estos modelos existen para documentar la respuesta en Swagger; el service
# arma el dict con la misma forma a mano.


class UsuarioAprobacionResponse(BaseModel):
    """Usuario de la cadena de aprobaciones, embebido junto al id."""
    id_usuario: int
    usuario: str
    nombre: str
    carnet: str | None = None
    celular: str | None = None
    correo: str | None = None
    cargo: str | None = None
    id_rol: int | None = None
    activo: bool | None = None


class RolAprobadorResponse(BaseModel):
    """Rol que corresponde a un nivel. Informativo: el servidor no restringe."""
    id_rol: int
    nombre: str
    descripcion: str | None = None


class NivelAprobacionEdan(BaseModel):
    nivel: Literal["ugr", "alcalde", "dgr", "videcid"]
    estado: Literal["pendiente", "aprobado", "observado", "espera_correccion"]
    observacion: str | None = None
    rol_aprobador: RolAprobadorResponse | None = None
    # Quién aprobó y cuándo. Se conserva aunque el nivel luego sea devuelto.
    id_usuario_aprobacion: int | None = None
    usuario_aprobacion: UsuarioAprobacionResponse | None = None
    fecha_aprobacion: str | None = None
    # Quién devolvió y cuándo. Se limpia al aprobar de nuevo o resolverse.
    id_usuario_devolucion: int | None = None
    usuario_devolucion: UsuarioAprobacionResponse | None = None
    fecha_devolucion: str | None = None


class AprobacionesEdanResponse(BaseModel):
    """`data` del GET /api/v2/edan/{id}/aprobacion y de los PUT."""
    id_edan: int
    estado_global: str
    aprobaciones: dict[str, NivelAprobacionEdan]


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
    imp_impacto_poblacion: bool = False
    imp_salud_establecimientos: bool = False
    imp_danos_viales: bool = False
    imp_danos_infra_publica: bool = False
    imp_servicios_basicos: bool = False
    imp_unidades_educativas: bool = False
    imp_danos_vivienda: bool = False
    imp_danos_agricultura: bool = False
    imp_danos_pecuarios: bool = False
    imp_infra_productiva: bool = False
    imp_primera_respuesta: bool = False
    imp_necesidad_salud: bool = False
    imp_necesidad_humanitaria: bool = False
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
    grupo: str | None = None
    categoria: str | None = None


class TipoEventoUpdate(BaseModel):
    nombre: str | None = None
    descripcion: str | None = None
    grupo: str | None = None
    categoria: str | None = None


class TipoEventoResponse(BaseModel):
    id_tipo_evento: int
    nombre: str
    descripcion: str | None = None
    grupo: str | None = None
    categoria: str | None = None

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


class TipoLocalidadResponse(BaseModel):
    id_tipo_localidad: int
    nombre: str
    descripcion: str | None = None
    orden: int = 0

    class Config:
        from_attributes = True


class EdanLocalidadEstadoCreate(BaseModel):
    nombre: str
    descripcion: str | None = None
    orden: int = 0


class EdanLocalidadEstadoUpdate(BaseModel):
    nombre: str | None = None
    descripcion: str | None = None
    orden: int | None = None


class EdanLocalidadEstadoResponse(BaseModel):
    id_edan_localidad_estado: int
    nombre: str
    descripcion: str | None = None
    orden: int = 0

    class Config:
        from_attributes = True


class ProteccionCreate(BaseModel):
    """Schema de entrada para crear/actualizar un grupo vulnerable en una localidad (sin foto)."""
    id_seccion: str | None = Field(None, description="ID único offline (generado por cliente). Ej: 'po_1693012345_abc12345'")
    id_grupo_vulnerable_catalogo: int
    mujeres: int = Field(0, ge=0)
    hombres: int = Field(0, ge=0)
    total: int = Field(0, ge=0)
    apoyo_psicologico: bool | None = None
    reposicion_documentos: bool | None = None
    observaciones: str = ''


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


class GrupoVulnerableResponse(BaseModel):
    id_grupo_vulnerable: int
    codigo: str
    nombre: str
    descripcion: str | None = None
    orden: int = 0
    activo: bool = True

    class Config:
        from_attributes = True


class GrupoEtarioCreate(BaseModel):
    codigo: str
    nombre: str
    descripcion: str | None = None
    orden: int = 0
    activo: bool = True


class GrupoEtarioUpdate(BaseModel):
    codigo: str | None = None
    nombre: str | None = None
    descripcion: str | None = None
    orden: int | None = None
    activo: bool | None = None


class GrupoEtarioResponse(BaseModel):
    id_grupo_etario: int
    codigo: str
    nombre: str
    descripcion: str | None = None
    orden: int = 0
    activo: bool = True

    class Config:
        from_attributes = True


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


# ============================================================================
#  MODELOS DE RESPUESTA — REPORTES AGREGADOS v2 (swagger completo)
#  Reportes sobre TODAS las localidades (huérfanas + consolidadas).
# ============================================================================

class PorEstadoLocalidadItem(BaseModel):
    id_edan_localidad_estado: int | None = None
    estado: str | None = None
    cantidad: int = 0


class PorTipoEventoItem(BaseModel):
    id_tipo_evento: int | None = None
    tipo_evento: str = ''
    cantidad: int = 0


class TotalesResumen(BaseModel):
    total_localidades: int = 0
    total_huerfanas: int = 0
    total_consolidadas: int = 0
    total_poblacion_afectada: float = 0
    total_familias_afectadas: float = 0
    total_familias_damnificadas: float = 0


class ResumenReporteData(BaseModel):
    totales: TotalesResumen
    por_estado: list[PorEstadoLocalidadItem] = []
    por_tipo_evento: list[PorTipoEventoItem] = []


class ReporteGeografiaItem(BaseModel):
    id_departamento: int | None = None
    departamento: str | None = None
    id_provincia: int | None = None
    provincia: str | None = None
    id_municipio: int | None = None
    municipio: str | None = None
    total_localidades: int = 0
    total_huerfanas: int = 0
    total_consolidadas: int = 0
    poblacion_afectada: float = 0
    familias_afectadas: float = 0
    familias_damnificadas: float = 0


class ReporteAgriculturaItem(BaseModel):
    tipo_cultivo: str | None = None
    id_cultivo: int | None = None
    cultivo_nombre: str | None = None
    cultivo_grupo: str | None = None
    total_registros: int = 0
    hectareas_afectadas: float = 0
    hectareas_perdidas: float = 0


class ReportePecuarioItem(BaseModel):
    especie: str | None = None
    id_especie: int | None = None
    especie_catalogo: str | None = None
    especie_grupo: str | None = None
    total_registros: int = 0
    animales_afectados: float = 0
    animales_muertos: float = 0


class PorEstadoEdanItem(BaseModel):
    id_estado: int | None = None
    estado: str | None = None
    cantidad: int = 0


class MisResumenData(BaseModel):
    total_edans: int = 0
    # Los nombres de total_borrador / total_enviado son legacy: no coinciden con
    # los estados que cuentan y se conservan para no romper el contrato. La
    # verdad del desglose es 'por_estado', que sale del catalogo.
    total_borrador: int = 0
    total_enviado: int = 0
    total_aprobado: int = 0
    total_observado: int = 0
    total_poblacion_afectada: float = 0
    total_familias_afectadas: float = 0
    total_familias_damnificadas: float = 0
    total_localidades: int = 0
    por_estado: list[PorEstadoEdanItem] = []
    por_tipo_evento: list[PorTipoEventoItem] = []


class ResumenReporteResponse(SuccessResponse):
    data: ResumenReporteData


class ReporteGeografiaResponse(SuccessResponse):
    data: list[ReporteGeografiaItem]
    total: int | None = None


class ReporteAgriculturaResponse(SuccessResponse):
    data: list[ReporteAgriculturaItem]
    total: int | None = None


class ReportePecuarioResponse(SuccessResponse):
    data: list[ReportePecuarioItem]
    total: int | None = None


class MisResumenResponse(SuccessResponse):
    data: MisResumenData

