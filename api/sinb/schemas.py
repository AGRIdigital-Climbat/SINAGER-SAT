from pydantic import BaseModel, Field, ConfigDict
from typing import Literal, Optional
from datetime import date, datetime
from uuid import UUID


# ============================================================================
# SCHEMAS BASE
# ============================================================================

class SinbBaseResponse(BaseModel):
    """Respuesta base con formato estándar SINB."""
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# CATÁLOGOS BIOCURALTURALES
# ============================================================================

class GrupoCreate(SinbBaseResponse):
    codigo: str = Field(..., max_length=20, description="Código único del grupo")
    nombre: str = Field(..., description="Nombre del grupo")
    descripcion: str | None = Field(None, description="Descripción opcional")


class GrupoUpdate(SinbBaseResponse):
    codigo: str | None = Field(None, max_length=20)
    nombre: str | None = None
    descripcion: str | None = None


class GrupoResponse(SinbBaseResponse):
    id: UUID
    codigo: str
    nombre: str
    descripcion: str | None
    estado: Literal["ACTIVO", "INACTIVO", "ELIMINADO"]
    creado_en: datetime
    actualizado_en: datetime


# --- Indicador Natural ---

class IndicadorNaturalCreate(SinbBaseResponse):
    codigo: str = Field(..., max_length=20, description="Código único del indicador")
    nombre_cientifico: str = Field(..., description="Nombre científico")
    nombre_comun: str | None = Field(None, description="Nombre común")
    id_grupo: UUID | None = Field(None, description="FK a grupo")
    descripcion: str | None = None
    requiere_consentimiento: bool = Field(False, description="¿Requiere consentimiento de comunidad?")


class IndicadorNaturalUpdate(SinbBaseResponse):
    codigo: str | None = Field(None, max_length=20)
    nombre_cientifico: str | None = None
    nombre_comun: str | None = None
    id_grupo: UUID | None = None
    descripcion: str | None = None
    requiere_consentimiento: bool | None = None


class IndicadorNaturalResponse(SinbBaseResponse):
    id: UUID
    codigo: str
    nombre_cientifico: str
    nombre_comun: str | None
    id_grupo: UUID | None
    grupo: dict | None = None
    descripcion: str | None
    requiere_consentimiento: bool
    estado: Literal["ACTIVO", "INACTIVO", "ELIMINADO"]
    creado_en: datetime
    actualizado_en: datetime


# --- Característica ---

class CaracteristicaCreate(SinbBaseResponse):
    id_indicador_natural: UUID = Field(..., description="FK a indicador natural")
    caracteristica: str = Field(..., description="Descripción de la característica")


class CaracteristicaUpdate(SinbBaseResponse):
    id_indicador_natural: UUID | None = None
    caracteristica: str | None = None


class CaracteristicaResponse(SinbBaseResponse):
    id: UUID
    id_indicador_natural: UUID
    caracteristica: str
    estado: Literal["ACTIVO", "INACTIVO", "ELIMINADO"]
    creado_en: datetime


# --- Comportamiento ---

class ComportamientoCreate(SinbBaseResponse):
    id_grupo: UUID | None = Field(None, description="FK a grupo")
    id_caracteristica: UUID = Field(..., description="FK a característica")
    comportamiento: str = Field(..., description="Descripción del comportamiento")


class ComportamientoUpdate(SinbBaseResponse):
    id_grupo: UUID | None = None
    id_caracteristica: UUID | None = None
    comportamiento: str | None = None


class ComportamientoResponse(SinbBaseResponse):
    id: UUID
    id_grupo: UUID | None
    id_caracteristica: UUID
    comportamiento: str
    estado: Literal["ACTIVO", "INACTIVO", "ELIMINADO"]
    creado_en: datetime


# --- Significado ---

class SignificadoCreate(SinbBaseResponse):
    id_grupo: UUID | None = Field(None, description="FK a grupo")
    id_comportamiento: UUID = Field(..., description="FK a comportamiento")
    significado: str = Field(..., description="Significado del comportamiento")
    categoria: str | None = Field(None, description="Categoría opcional")


class SignificadoUpdate(SinbBaseResponse):
    id_grupo: UUID | None = None
    id_comportamiento: UUID | None = None
    significado: str | None = None
    categoria: str | None = None


class SignificadoResponse(SinbBaseResponse):
    id: UUID
    id_grupo: UUID | None
    id_comportamiento: UUID
    significado: str
    categoria: str | None
    estado: Literal["ACTIVO", "INACTIVO", "ELIMINADO"]
    creado_en: datetime


# ============================================================================
# ZONA GEOGRÁFICA
# ============================================================================

class ZonaGeograficaCreate(SinbBaseResponse):
    codigo: str = Field(..., max_length=10, description="Código único de zona")
    nombre: str = Field(..., max_length=100, description="Nombre de la zona")
    descripcion: str | None = None


class ZonaGeograficaUpdate(SinbBaseResponse):
    codigo: str | None = Field(None, max_length=10)
    nombre: str | None = None
    descripcion: str | None = None


class ZonaGeograficaResponse(SinbBaseResponse):
    id: UUID
    codigo: str
    nombre: str
    descripcion: str | None
    estado: Literal["ACTIVO", "INACTIVO", "ELIMINADO"]


# ============================================================================
# PRONÓSTICOS - CAMPOS Y ESCENARIOS
# ============================================================================

class CampoPronosticoCreate(SinbBaseResponse):
    nombre: str = Field(..., max_length=100, description="Nombre del campo")
    unidad: str | None = Field(None, description="Unidad de medida")
    tipo: str = Field(..., description="Tipo: numerico, categorico, texto")


class CampoPronosticoUpdate(SinbBaseResponse):
    nombre: str | None = Field(None, max_length=100)
    unidad: str | None = None
    tipo: str | None = None


class CampoPronosticoResponse(SinbBaseResponse):
    id: UUID
    nombre: str
    unidad: str | None
    tipo: str
    estado: Literal["ACTIVO", "INACTIVO", "ELIMINADO"]


# --- Escenario ---

class EscenarioCreate(SinbBaseResponse):
    id_campo_pronostico: UUID = Field(..., description="FK a campo pronóstico")
    nombre: str = Field(..., max_length=100, description="Nombre del escenario")
    descripcion: str | None = None
    valor_min: float | None = Field(None, description="Valor mínimo del rango")
    valor_max: float | None = Field(None, description="Valor máximo del rango")


class EscenarioUpdate(SinbBaseResponse):
    id_campo_pronostico: UUID | None = None
    nombre: str | None = Field(None, max_length=100)
    descripcion: str | None = None
    valor_min: float | None = None
    valor_max: float | None = None


class EscenarioResponse(SinbBaseResponse):
    id: UUID
    id_campo_pronostico: UUID
    nombre: str
    descripcion: str | None
    valor_min: float | None
    valor_max: float | None
    estado: Literal["ACTIVO", "INACTIVO", "ELIMINADO"]


# --- Categoría Pronóstico Temporal ---

class CategoriaPronosticoTemporalCreate(SinbBaseResponse):
    nombre: str = Field(..., max_length=100, description="Nombre de la categoría")
    descripcion: str | None = None


class CategoriaPronosticoTemporalUpdate(SinbBaseResponse):
    nombre: str | None = Field(None, max_length=100)
    descripcion: str | None = None


class CategoriaPronosticoTemporalResponse(SinbBaseResponse):
    id: UUID
    nombre: str
    descripcion: str | None
    estado: Literal["ACTIVO", "INACTIVO", "ELIMINADO"]


# ============================================================================
# DIMENSIONES Y CATEGORÍAS DE RECOMENDACIÓN
# ============================================================================

class DimensionRecomendacionCreate(SinbBaseResponse):
    codigo: str = Field(..., max_length=20, description="Código único")
    nombre: str = Field(..., max_length=100, description="Nombre de la dimensión")
    descripcion: str | None = None


class DimensionRecomendacionUpdate(SinbBaseResponse):
    codigo: str | None = Field(None, max_length=20)
    nombre: str | None = None
    descripcion: str | None = None


class DimensionRecomendacionResponse(SinbBaseResponse):
    id: UUID
    codigo: str
    nombre: str
    descripcion: str | None
    estado: Literal["ACTIVO", "INACTIVO", "ELIMINADO"]


class CategoriaComportamientoCreate(SinbBaseResponse):
    id_dimension: UUID = Field(..., description="FK a dimensión recomendación")
    nombre: str = Field(..., max_length=100, description="Nombre de la categoría")
    descripcion: str | None = None


class CategoriaComportamientoUpdate(SinbBaseResponse):
    id_dimension: UUID | None = None
    nombre: str | None = Field(None, max_length=100)
    descripcion: str | None = None


class CategoriaComportamientoResponse(SinbBaseResponse):
    id: UUID
    id_dimension: UUID
    nombre: str
    descripcion: str | None
    estado: Literal["ACTIVO", "INACTIVO", "ELIMINADO"]


# ============================================================================
# OBSERVACIONES
# ============================================================================

class ObservacionRegistroCreate(SinbBaseResponse):
    """Registro individual dentro de una observación."""
    id_reg_off: str | None = Field(None, max_length=36, description="ID offline generado por dispositivo")
    id_caracteristica: UUID | None = Field(None, description="FK a característica")
    id_comportamiento: UUID | None = Field(None, description="FK a comportamiento")
    id_significado: UUID | None = Field(None, description="FK a significado")
    id_indicador_natural: UUID | None = Field(None, description="FK a indicador natural")
    valor_observado: str | None = Field(None, description="Valor observado")
    unidad: str | None = Field(None, description="Unidad de medida")


class ObservacionRegistroResponse(SinbBaseResponse):
    id: UUID
    id_reg_off: str | None
    id_observacion: UUID
    id_caracteristica: UUID | None
    id_comportamiento: UUID | None
    id_significado: UUID | None
    id_indicador_natural: UUID | None
    valor_observado: str | None
    unidad: str | None
    creado_en: datetime


class ObservacionCreate(SinbBaseResponse):
    id_obs_off: str | None = Field(None, max_length=36, description="ID offline generado por dispositivo")
    codigo_comunidad: str = Field(..., description="Código INE de comunidad")
    id_municipio: int = Field(..., description="FK a municipio")
    id_usuario_responsable: int | None = Field(None, description="Usuario responsable (se asigna auto si None)")
    fecha_inicio: date = Field(..., description="Fecha de inicio de observación")
    fecha_fin: date = Field(..., description="Fecha de fin de observación")
    hora_inicio: str | None = Field(None, description="Hora inicio (HH:MM)")
    hora_fin: str | None = Field(None, description="Hora fin (HH:MM)")
    fecha_registro: date = Field(..., description="Fecha de registro")
    clima_observado: str | None = Field(None, description="Descripción del clima")
    observacion_registro: list[ObservacionRegistroCreate] | None = Field(None, description="Registros anidados")


class ObservacionUpdate(SinbBaseResponse):
    codigo_comunidad: str | None = None
    id_municipio: int | None = None
    fecha_inicio: date | None = None
    fecha_fin: date | None = None
    hora_inicio: str | None = None
    hora_fin: str | None = None
    fecha_registro: date | None = None
    clima_observado: str | None = None
    es_validada: bool | None = None
    observacion_rechazada_motivo: str | None = None


class ObservacionResponse(SinbBaseResponse):
    id: UUID
    id_obs_off: str | None
    codigo_corto: str
    codigo_comunidad: str
    id_municipio: int
    id_usuario_responsable: int
    usuario_responsable: dict | None = None
    fecha_inicio: date
    fecha_fin: date
    hora_inicio: str | None
    hora_fin: str | None
    fecha_registro: date
    clima_observado: str | None
    es_validada: bool
    validada_por: int | None
    validada_en: datetime | None
    observacion_rechazada_motivo: str | None
    estado: Literal["ACTIVO", "INACTIVO", "ELIMINADO"]
    creado_en: datetime
    actualizado_en: datetime
    version_registro: int
    observacion_registro: list[ObservacionRegistroResponse] | None = None


# ============================================================================
# PRONÓSTICOS
# ============================================================================

class EscenarioEstacionalCreate(SinbBaseResponse):
    id_escenario: UUID = Field(..., description="FK a escenario")
    probabilidad: float = Field(..., ge=0, le=100, description="Probabilidad 0-100%")


class PronosticoEstacionalCreate(SinbBaseResponse):
    id_pe_off: str | None = Field(None, max_length=36, description="ID offline generado por dispositivo")
    id_campo_pronostico: UUID = Field(..., description="FK a campo pronóstico")
    fecha_emision: date = Field(..., description="Fecha de emisión")
    periodo_inicio: date = Field(..., description="Inicio del período")
    periodo_fin: date = Field(..., description="Fin del período")
    id_usuario_elabora: int | None = Field(None, description="Usuario que elabora")
    notas: str | None = None
    escenarios: list[EscenarioEstacionalCreate] | None = Field(None, description="Escenarios anidados")


class PronosticoEstacionalUpdate(SinbBaseResponse):
    id_campo_pronostico: UUID | None = None
    fecha_emision: date | None = None
    periodo_inicio: date | None = None
    periodo_fin: date | None = None
    estado: Literal["EMITIDO", "ACEPTADO", "RECHAZADO", "EN_REVISION"] | None = None
    id_usuario_elabora: int | None = None
    notas: str | None = None


class PronosticoEstacionalResponse(SinbBaseResponse):
    id: UUID
    id_pe_off: str | None
    codigo: str
    id_campo_pronostico: UUID
    campo_pronostico: dict | None = None
    fecha_emision: date
    periodo_inicio: date
    periodo_fin: date
    estado: Literal["EMITIDO", "ACEPTADO", "RECHAZADO", "EN_REVISION"]
    id_usuario_elabora: int | None
    notas: str | None
    creado_en: datetime
    escenarios: list[dict] | None = None


class PronosticoTemporalCreate(SinbBaseResponse):
    id_pt_off: str | None = Field(None, max_length=36, description="ID offline generado por dispositivo")
    id_categoria: UUID = Field(..., description="FK a categoría pronóstico temporal")
    id_campo_pronostico: UUID = Field(..., description="FK a campo pronóstico")
    fecha_emision: date = Field(..., description="Fecha de emisión")
    fecha_inicio: date = Field(..., description="Inicio de vigencia")
    fecha_fin: date = Field(..., description="Fin de vigencia")
    valor_esperado: str | None = Field(None, description="Valor esperado")
    confianza: Literal["ALTA", "MEDIA", "BAJA"] | None = Field(None, description="Nivel de confianza")


class PronosticoTemporalUpdate(SinbBaseResponse):
    id_categoria: UUID | None = None
    id_campo_pronostico: UUID | None = None
    fecha_emision: date | None = None
    fecha_inicio: date | None = None
    fecha_fin: date | None = None
    valor_esperado: str | None = None
    confianza: Literal["ALTA", "MEDIA", "BAJA"] | None = None
    estado: Literal["EMITIDO", "ACEPTADO", "RECHAZADO", "EN_REVISION"] | None = None


class PronosticoTemporalResponse(SinbBaseResponse):
    id: UUID
    id_pt_off: str | None
    codigo: str
    id_categoria: UUID
    categoria: dict | None = None
    id_campo_pronostico: UUID
    campo_pronostico: dict | None = None
    fecha_emision: date
    fecha_inicio: date
    fecha_fin: date
    valor_esperado: str | None
    confianza: Literal["ALTA", "MEDIA", "BAJA"] | None
    estado: Literal["EMITIDO", "ACEPTADO", "RECHAZADO", "EN_REVISION"]
    creado_en: datetime


# ============================================================================
# VALIDACIÓN DE PRONÓSTICOS
# ============================================================================

class VerificacionPronosticoCreate(SinbBaseResponse):
    """Validación MANUAL de pronóstico."""
    id_pronostico_estacional: UUID | None = Field(None, description="FK a pronóstico estacional")
    id_pronostico_temporal: UUID | None = Field(None, description="FK a pronóstico temporal")
    id_variable_climatica: UUID | None = Field(None, description="FK a variable climática")
    codigo_comunidad: str | None = Field(None, description="Código INE de comunidad")
    id_municipio: int | None = Field(None, description="FK a municipio")
    estado: Literal["COINCIDE", "NO_COINCIDE"] = Field(..., description="Resultado de validación")
    calificacion: float | None = Field(None, ge=0, le=100, description="Calificación 0-100")
    observacion: str | None = Field(None, description="Observación cualitativa")


class VerificacionPronosticoResponse(SinbBaseResponse):
    id: UUID
    id_pronostico_estacional: UUID | None
    id_pronostico_temporal: UUID | None
    id_variable_climatica: UUID | None
    codigo_comunidad: str | None
    id_municipio: int | None
    estado: Literal["COINCIDE", "NO_COINCIDE"]
    calificacion: float | None
    observacion: str | None
    es_automatico: bool
    id_usuario_verifica: int | None
    usuario_verifica: dict | None = None
    fecha_verificacion: datetime


class CalculoVerificacionRequest(SinbBaseResponse):
    """Request para cálculo AUTOMÁTICO de verificación."""
    id_pronostico: UUID | None = Field(None, description="ID de pronóstico específico (opcional)")
    tipo: Literal["estacional", "temporal", "todos"] = Field("todos", description="Tipo de pronóstico a verificar")


class CalculoVerificacionResponse(SinbBaseResponse):
    id_pronostico: UUID
    tipo: str
    estado_calculo: Literal["COINCIDE", "NO_COINCIDE", "SIN_DATOS", "EN_VERIFICACION"]
    calificacion: float | None
    es_automatico: bool
    mensaje: str


# ============================================================================
# RECOMENDACIONES
# ============================================================================

class RecomendacionLocalCreate(SinbBaseResponse):
    id_rec_off: str | None = Field(None, max_length=36, description="ID offline generado por dispositivo")
    texto: str = Field(..., description="Texto de la recomendación")
    id_dimension: UUID = Field(..., description="FK a dimensión")
    id_categoria: UUID = Field(..., description="FK a categoría")
    codigo_comunidad: str | None = Field(None, description="Código INE de comunidad (opcional)")
    id_municipio: int | None = Field(None, description="FK a municipio (opcional)")
    id_usuario_elabora: int | None = Field(None, description="Usuario que elabora")


class RecomendacionLocalUpdate(SinbBaseResponse):
    texto: str | None = None
    id_dimension: UUID | None = None
    id_categoria: UUID | None = None
    codigo_comunidad: str | None = None
    id_municipio: int | None = None
    estado: Literal["ACTIVO", "INACTIVO", "ELIMINADO"] | None = None


class RecomendacionLocalResponse(SinbBaseResponse):
    id: UUID
    id_rec_off: str | None
    texto: str
    id_dimension: UUID
    dimension: dict | None = None
    id_categoria: UUID
    categoria: dict | None = None
    codigo_comunidad: str | None
    id_municipio: int | None
    id_usuario_elabora: int | None
    usuario_elabora: dict | None = None
    estado: Literal["ACTIVO", "INACTIVO", "ELIMINADO"]
    creado_en: datetime


class VarianteLocalCreate(SinbBaseResponse):
    id_recomendacion: UUID = Field(..., description="FK a recomendación")
    variante: str = Field(..., description="Texto de la variante")
    ambito: str | None = Field(None, description="Ámbito de aplicación")


class VarianteLocalResponse(SinbBaseResponse):
    id: UUID
    id_recomendacion: UUID
    variante: str
    ambito: str | None
    estado: Literal["ACTIVO", "INACTIVO", "ELIMINADO"]
    creado_en: datetime


# ============================================================================
# AVISOS
# ============================================================================

class AvisoCreate(SinbBaseResponse):
    id_aviso_off: str | None = Field(None, max_length=36, description="ID offline generado por dispositivo")
    id_campo_pronostico: UUID = Field(..., description="FK a campo pronóstico")
    codigo_comunidad: str = Field(..., description="Código INE de comunidad")
    id_municipio: int = Field(..., description="FK a municipio")
    mensaje: str = Field(..., description="Mensaje del aviso")
    vigencia_horas: int = Field(24, ge=1, le=168, description="Vigencia en horas (1-168)")
    id_usuario_emite: int | None = Field(None, description="Usuario que emite")


class AvisoUpdate(SinbBaseResponse):
    mensaje: str | None = None
    vigencia_horas: int | None = None
    estado: Literal["ACTIVO", "INACTIVO", "ELIMINADO"] | None = None


class AvisoResponse(SinbBaseResponse):
    id: UUID
    id_aviso_off: str | None
    codigo: str
    id_campo_pronostico: UUID
    campo_pronostico: dict | None = None
    codigo_comunidad: str
    id_municipio: int
    mensaje: str
    fecha_emision: datetime
    vigencia_horas: int
    fecha_vencimiento: datetime
    estado: Literal["ACTIVO", "INACTIVO", "ELIMINADO"]
    id_usuario_emite: int | None
    usuario_emite: dict | None = None


# ============================================================================
# OBSERVADOR ÍNDICE
# ============================================================================

class ObservadorIndiceCreate(SinbBaseResponse):
    id_usuario: int = Field(..., description="FK a usuario observador")
    id_indicador_natural: UUID = Field(..., description="FK a indicador natural")
    tipo: Literal["ESTACIONAL", "TEMPORAL"] = Field(..., description="Tipo de pronóstico")
    valor: float | None = Field(None, description="Valor calculado del índice")
    fecha_calculo: date | None = None


class ObservadorIndiceResponse(SinbBaseResponse):
    id: UUID
    id_usuario: int
    usuario: dict | None = None
    id_indicador_natural: UUID
    indicador: dict | None = None
    tipo: Literal["ESTACIONAL", "TEMPORAL"]
    valor: float | None
    fecha_calculo: date
    creado_en: datetime


# ============================================================================
# ASIGNACIÓN DE OBSERVADORES A PRONÓSTICOS
# ============================================================================

class PronosticoObservadorCreate(SinbBaseResponse):
    """Asignar observador(es) a un pronóstico (recolector → observadores del mismo municipio)."""
    id_pronostico: UUID = Field(..., description="ID del pronóstico (estacional o temporal)")
    tipo_pronostico: Literal["estacional", "temporal"] = Field(..., description="Tipo de pronóstico")
    id_observadores: list[int] = Field(..., description="Lista de IDs de usuarios observadores (mismo municipio)")
    confianza: Literal["ALTA", "MEDIA", "BAJA"] | None = Field(None, description="Nivel de confianza asignado")


class PronosticoObservadorResponse(SinbBaseResponse):
    id_pronostico: UUID
    tipo_pronostico: str
    id_usuario: int
    usuario: dict | None = None
    confianza: Literal["ALTA", "MEDIA", "BAJA"] | None
    fecha_asignacion: datetime


# ============================================================================
# MAPAS - GEOJSON
# ============================================================================

class MapaFiltros(SinbBaseResponse):
    """Filtros geográficos para endpoints de mapa."""
    id_departamento: int | None = Field(None, description="Filtrar por departamento")
    id_provincia: int | None = Field(None, description="Filtrar por provincia")
    id_municipio: int | None = Field(None, description="Filtrar por municipio")
    codigo_comunidad: str | None = Field(None, description="Filtrar por comunidad (código INE)")
    codigo_manzano: str | None = Field(None, description="Filtrar por manzano (código INE)")
    fecha_inicio: date | None = Field(None, description="Filtrar observaciones desde fecha")
    fecha_fin: date | None = Field(None, description="Filtrar observaciones hasta fecha")
    id_indicador_natural: UUID | None = Field(None, description="Filtrar por indicador natural")
    id_grupo: UUID | None = Field(None, description="Filtrar por grupo biocultural")


# ============================================================================
# REPORTES ENRIQUECIDOS
# ============================================================================

class ReporteObservacionesResumen(SinbBaseResponse):
    """Resumen de observaciones por período."""
    total_observaciones: int
    total_registros: int
    por_comunidad: list[dict]
    por_indicador: list[dict]
    por_estado_validacion: list[dict]


class ReportePronosticosResumen(SinbBaseResponse):
    """Resumen de pronósticos con estado de verificación."""
    total_pronosticos: int
    por_estado: list[dict]
    por_tipo: list[dict]
    verificaciones_pendientes: int
    verificaciones_coinciden: int
    verificaciones_no_coinciden: int


# ============================================================================
# PRONÓSTICOS DIGITALES (Open-Meteo)
# ============================================================================

class PronosticoDiarioMunicipalResponse(SinbBaseResponse):
    """
    Pronóstico diario por municipio (automático, 2x/día).
    
    **Horario de referencia:**
    - Los datos son del día COMPLETO (0:00 a 23:59 hora local America/La_Paz, UTC-4)
    - temp_max: máxima del día (ocurre típicamente 12:00-15:00)
    - temp_min: mínima del día (ocurre típicamente 03:00-06:00)
    - sunrise: salida del sol (~06:00-06:30, inicio del día solar)
    - sunset: puesta del sol (~18:00-19:00, fin del día solar)
    """
    id: UUID
    id_municipio: int
    municipio: dict | None = None
    fecha: date
    temp_max: float | None = Field(None, description="Temperatura máxima del día (°C), ocurre ~12:00-15:00")
    temp_min: float | None = Field(None, description="Temperatura mínima del día (°C), ocurre ~03:00-06:00")
    precipitacion_suma: float | None = Field(None, description="Suma total de precipitación del día (mm)")
    precipitacion_prob_max: int | None = Field(None, description="Probabilidad máxima de precipitación (%)")
    sunrise: datetime | None = Field(None, description="Hora de salida del sol (inicio del día solar)")
    sunset: datetime | None = Field(None, description="Hora de puesta del sol (fin del día solar)")
    fuente: str
    creado_en: datetime


class PronosticoHourlyPuntoResponse(SinbBaseResponse):
    """Pronóstico por hora para punto específico (on-demand, caché 24h)."""
    id: UUID
    latitud: float
    longitud: float
    fecha_hora: datetime
    id_variable_climatica: UUID | None
    variable: dict | None = None
    valor: float | None
    unidad: str | None
    id_municipio: int | None
    creado_en: datetime
    expira_en: datetime


class PronosticoMinutelyCacheResponse(SinbBaseResponse):
    """Nowcast cada 15 minutos (caché 1h)."""
    id: UUID
    latitud: float
    longitud: float
    fecha_hora: datetime
    precipitacion: float | None
    temperatura: float | None
    id_municipio: int | None
    creado_en: datetime
    expira_en: datetime


class PronosticoDigitalConsultaRequest(SinbBaseResponse):
    """Solicitud de consulta de pronóstico digital."""
    latitud: float = Field(..., ge=-90, le=90, description="Latitud del punto")
    longitud: float = Field(..., ge=-180, le=180, description="Longitud del punto")
    tipo: Literal["daily", "hourly", "minutely_15"] = Field(
        "daily", 
        description="Tipo de pronóstico: daily (7-16 días), hourly (24-168h), minutely_15 (48h)"
    )
    variables: str = Field(
        "temperature_2m_max,temperature_2m_min,precipitation_sum",
        description="Variables separadas por coma"
    )
    horizonte_dias: int = Field(7, ge=1, le=16, description="Días de horizonte (1-16)")


class OpenMeteoResponse(SinbBaseResponse):
    """Respuesta directa de Open-Meteo (sin almacenamiento)."""
    latitude: float
    longitude: float
    elevation: float
    timezone: str
    timezone_abbreviation: str
    generationtime_ms: float
    data: dict  # Datos crudos de Open-Meteo


# ============================================================================
# GALERÍA DE EVIDENCIAS (Fotos/Audio de Bioindicadores)
# ============================================================================

class EvidenciaCreate(SinbBaseResponse):
    """Crear evidencia (foto/audio) de bioindicador."""
    id_indicador_natural: UUID | None = Field(None, description="FK a indicador natural (galería)")
    id_observacion_registro: UUID | None = Field(None, description="FK a registro de observación")
    descripcion: str = Field(..., max_length=500, description="Descripción de la evidencia")
    formato: str = Field(..., max_length=20, description="Formato del archivo (JPG, PNG, MP3, etc)")
    tamano_bytes: int | None = Field(None, description="Tamaño del archivo en bytes")
    hash_sha256: str | None = Field(None, max_length=64, description="Hash SHA256 del archivo")
    latitud: float | None = Field(None, ge=-90, le=90, description="Coordenada GPS (latitud)")
    longitud: float | None = Field(None, ge=-180, le=180, description="Coordenada GPS (longitud)")


class EvidenciaResponse(SinbBaseResponse):
    """Respuesta de evidencia con anidados completos."""
    id: UUID
    id_indicador_natural: UUID | None
    indicador: dict | None = None  # Anidado: indicador completo
    id_observacion_registro: UUID | None
    observacion_registro: dict | None = None  # Anidado: registro completo
    id_usuario_subio: int
    usuario: dict | None = None  # Anidado: usuario completo
    path_archivo: str
    url_descarga: str | None = None  # URL temporal de descarga
    descripcion: str
    formato: str
    tamano_bytes: int | None
    hash_sha256: str | None
    fecha_carga: datetime
    activo: bool
    metadata: dict | None = None  # GPS, cámara, etc.


class GaleriaFiltros(SinbBaseResponse):
    """Filtros para galería de evidencias."""
    id_indicador_natural: UUID | None = Field(None, description="Filtrar por indicador")
    id_grupo: UUID | None = Field(None, description="Filtrar por grupo biocultural")
    id_municipio: int | None = Field(None, description="Filtrar por municipio")
    codigo_comunidad: str | None = Field(None, description="Filtrar por comunidad")
    id_usuario_subio: int | None = Field(None, description="Filtrar por usuario que subió")
    formato: str | None = Field(None, description="Filtrar por formato (JPG, PNG, MP3)")
    fecha_desde: date | None = Field(None, description="Fecha desde")
    fecha_hasta: date | None = Field(None, description="Fecha hasta")
    con_gps: bool | None = Field(None, description="Solo evidencias con coordenadas GPS")


class GaleriaResponse(SinbBaseResponse):
    """Respuesta de galería con paginación."""
    total: int
    skip: int
    limit: int
    filtros_aplicados: dict
    evidencias: list[EvidenciaResponse]
    grupos_disponibles: list[dict] | None = None  # Para filtros
    indicadores_destacados: list[dict] | None = None  # Más fotos


# ============================================================================
# NDVI SATELITAL
# ============================================================================

class NDVIComunidadResponse(SinbBaseResponse):
    """NDVI actual por comunidad."""
    codigo_ine: str
    nombre: str
    fecha: date | None
    ndvi_promedio: float | None
    ndvi_anomalia: float | None
    estado_vegetacion: str | None
    estado_alerta: str | None


class NDVIEvolucionResponse(SinbBaseResponse):
    """Evolución mensual de NDVI."""
    codigo_ine: str
    nombre: str
    mes: datetime
    ndvi_promedio_mes: float | None
    anomalia_promedio_mes: float | None
    n_dias_con_datos: int


class NDVIAlertaResponse(SinbBaseResponse):
    """Alerta de NDVI bajo."""
    codigo_ine: str
    nombre: str
    fecha: date
    ndvi_promedio: float | None
    ndvi_anomalia: float | None
    estado_vegetacion: str | None
    tipo_alerta: str
    nivel_prioridad: int


class NDTVITemporalResponse(SinbBaseResponse):
    """Serie temporal de NDVI."""
    fecha: date
    ndvi_promedio: float | None
    ndvi_anomalia: float | None
    estado_vegetacion: str | None
    n_escenas: int | None


class EscenaSatelitalResponse(SinbBaseResponse):
    """Escena satelital procesada."""
    id: UUID
    producto: str
    escena_id: str
    fecha_adquisicion: date
    fecha_proceso: datetime
    cobertura_nubes: float | None
    huella: dict | None  # GeoJSON
    metadata: dict | None


class NDVIProcesamientoLogResponse(SinbBaseResponse):
    """Log de procesamiento NDVI."""
    fecha_proceso: date
    hora_inicio: datetime
    hora_fin: datetime | None
    estado: str
    escenas_consultadas: int | None
    escenas_descargadas: int | None
    comunidades_procesadas: int | None
    error_mensaje: str | None


class NDVIIngestarRequest(SinbBaseResponse):
    """Request para ingestar NDVI."""
    codigos_comunidades: list[str] | None = Field(None, description="Lista de comunidades (None = todas)")
    max_nubes: float = Field(20.0, ge=0, le=100, description="Máxima cobertura de nubes (%)")


class NDVIIngestarResponse(SinbBaseResponse):
    """Respuesta de ingestión NDVI."""
    escenas_consultadas: int
    escenas_procesadas: int
    comunidades_procesadas: int
    errores: list[str]
