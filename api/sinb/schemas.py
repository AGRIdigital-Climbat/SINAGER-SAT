from pydantic import BaseModel, Field, ConfigDict, field_validator
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
    estado: Literal["ACTIVO", "INACTIVO", "ELIMINADO"] | None = Field(None, description="Estado del registro (INACTIVO = retirado, sigue en BD)")


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
    id_grupo: UUID = Field(..., description="FK a grupo (NOT NULL en BD)")
    descripcion: str | None = None
    requiere_consentimiento: bool = Field(False, description="¿Requiere consentimiento de comunidad?")


class IndicadorNaturalUpdate(SinbBaseResponse):
    codigo: str | None = Field(None, max_length=20)
    nombre_cientifico: str | None = None
    nombre_comun: str | None = None
    id_grupo: UUID | None = None
    descripcion: str | None = None
    requiere_consentimiento: bool | None = None
    estado: Literal["ACTIVO", "INACTIVO", "ELIMINADO"] | None = Field(None, description="Estado del registro (INACTIVO = retirado, sigue en BD)")


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
    fotos: list[dict] | None = None
    creado_en: datetime
    actualizado_en: datetime


# --- Característica ---

class CaracteristicaCreate(SinbBaseResponse):
    id_indicador_natural: UUID = Field(..., description="FK a indicador natural")
    caracteristica: str = Field(..., description="Descripción de la característica")


class CaracteristicaUpdate(SinbBaseResponse):
    id_indicador_natural: UUID | None = None
    caracteristica: str | None = None
    estado: Literal["ACTIVO", "INACTIVO", "ELIMINADO"] | None = Field(None, description="Estado del registro (INACTIVO = retirado, sigue en BD)")


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
    estado: Literal["ACTIVO", "INACTIVO", "ELIMINADO"] | None = Field(None, description="Estado del registro (INACTIVO = retirado, sigue en BD)")


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
    estado: Literal["ACTIVO", "INACTIVO", "ELIMINADO"] | None = Field(None, description="Estado del registro (INACTIVO = retirado, sigue en BD)")


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
    estado: Literal["ACTIVO", "INACTIVO", "ELIMINADO"] | None = Field(None, description="Estado del registro (INACTIVO = retirado, sigue en BD)")


class ZonaGeograficaResponse(SinbBaseResponse):
    id: UUID
    codigo: str
    nombre: str
    descripcion: str | None
    estado: Literal["ACTIVO", "INACTIVO", "ELIMINADO"]


# ============================================================================
# PRONÓSTICOS - CAMPOS Y ESCENARIOS
# ============================================================================

class CategoriaPronosticoCreate(SinbBaseResponse):
    nombre: str = Field(..., max_length=100, description="Nombre de la categoría")
    descripcion: str | None = Field(None, description="Descripción opcional")


class CategoriaPronosticoUpdate(SinbBaseResponse):
    nombre: str | None = Field(None, max_length=100)
    descripcion: str | None = None
    estado: Literal["ACTIVO", "INACTIVO", "ELIMINADO"] | None = Field(None, description="Estado del registro (INACTIVO = retirado, sigue en BD)")


class CategoriaPronosticoResponse(SinbBaseResponse):
    id: UUID
    nombre: str
    descripcion: str | None
    estado: Literal["ACTIVO", "INACTIVO", "ELIMINADO"]


# --- Escenario ---

class EscenarioCreate(SinbBaseResponse):
    id_categoria: UUID = Field(..., description="FK a categoría de pronóstico")
    nombre: str = Field(..., max_length=100, description="Nombre del escenario")
    descripcion: str | None = None
    valor_min: float | None = Field(None, description="Valor mínimo del rango")
    valor_max: float | None = Field(None, description="Valor máximo del rango")


class EscenarioUpdate(SinbBaseResponse):
    id_categoria: UUID | None = None
    nombre: str | None = Field(None, max_length=100)
    descripcion: str | None = None
    valor_min: float | None = None
    valor_max: float | None = None
    estado: Literal["ACTIVO", "INACTIVO", "ELIMINADO"] | None = Field(None, description="Estado del registro (INACTIVO = retirado, sigue en BD)")


class EscenarioResponse(SinbBaseResponse):
    id: UUID
    id_categoria: UUID
    nombre: str
    descripcion: str | None
    valor_min: float | None
    valor_max: float | None
    estado: Literal["ACTIVO", "INACTIVO", "ELIMINADO"]


# ============================================================================
# PRONÓSTICOS
# ============================================================================

class EscenarioEstacionalCreate(SinbBaseResponse):
    id_escenario_off: str | None = Field(None, max_length=36, description="ID offline del escenario (generado por dispositivo)")
    id_escenario: UUID = Field(..., description="FK a escenario")
    confianza: Literal["ALTA", "MEDIA", "BAJA"] | None = Field(
        None, description="Confianza inicial del escenario: ALTA | MEDIA | BAJA (opcional, igual que pronóstico de corto plazo)"
    )


class CadenaBioculturalCreate(SinbBaseResponse):
    """Cadena obligatoria: grupo → indicador → característica → comportamiento."""
    id_grupo: UUID = Field(..., description="FK a sinb.grupo")
    id_indicador_natural: UUID = Field(..., description="FK a sinb.indicador_natural (debe pertenecer al grupo)")
    id_caracteristica: UUID = Field(..., description="FK a sinb.caracteristica (debe pertenecer al indicador)")
    id_comportamiento: UUID = Field(..., description="FK a sinb.comportamiento (debe pertenecer a la característica)")


class PeriodoCreate(SinbBaseResponse):
    """Período del pronóstico: fin debe ser >= inicio."""
    inicio: date = Field(..., description="Inicio del período")
    fin: date = Field(..., description="Fin del período")


class ContextoCreate(SinbBaseResponse):
    """Contexto geográfico/notas del registro (todo opcional)."""
    latitud: float | None = Field(None, ge=-90, le=90, description="Latitud -90..90")
    longitud: float | None = Field(None, ge=-180, le=180, description="Longitud -180..180")
    altitud: float | None = Field(None, description="Altitud en metros")
    notas: str | None = Field(None, description="Notas de contexto")


class PronosticoLargoItemCreate(SinbBaseResponse):
    """Un bloque de pronóstico: una categoría (campo) con sus escenarios."""
    id_item_off: str | None = Field(None, max_length=36, description="ID offline del item (generado por dispositivo)")
    id_categoria: UUID = Field(..., description="FK a sinb.categoria_pronostico")
    metodo_validacion: str | None = Field(None, max_length=50, description="Método de validación (texto libre, sin FK)")
    id_regla_pronostica: int | None = Field(None, description="Regla pronóstica aplicada (sin FK)")
    ejecutar_en: datetime | None = Field(None, description="Momento de aplicación de la validación")
    fuente: str | None = Field(None, max_length=200, description="Fuente del dato")
    orden: int = Field(0, ge=0, description="Orden de presentación")
    id_escenarios: list[UUID | EscenarioEstacionalCreate] = Field(
        default_factory=list,
        description="Escenarios: acepta uuid plano o {id_escenario, confianza}"
    )

    @field_validator("id_escenarios", mode="before")
    @classmethod
    def _normalizar_escenarios(cls, v):
        return [{"id_escenario": e} if not isinstance(e, dict) else e for e in (v or [])]


class RecomendacionLargoCreate(SinbBaseResponse):
    """Recomendación en texto libre: lo que el productor recomienda hacer."""
    id_recomendacion: UUID | None = Field(
        None, description="ID de la recomendación (lo fija el servidor si no viene; los dispositivos offline lo generan)"
    )
    id_recomendacion_off: str | None = Field(
        None, max_length=36, description="ID offline de la recomendación (generado por dispositivo)"
    )
    nombre: str = Field(
        ..., min_length=1,
        description="Texto libre de la recomendación (lo que el productor nos recomienda hacer)"
    )

    @field_validator("nombre")
    @classmethod
    def _nombre_no_vacio(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("La recomendación no puede estar vacía")
        return v


class ObservadorLargoCreate(SinbBaseResponse):
    id_observador_off: str | None = Field(None, max_length=36, description="ID offline del observador (generado por dispositivo)")
    id_usuario: int = Field(..., description="FK a usuarios.usuario")


class PronosticoLargoCreate(SinbBaseResponse):
    """POST /pronostico-largo — contrato anidado (MD 15)."""
    fecha_emision: date | None = Field(None, description="Fecha de emisión (default: hoy)")
    texto_observador: str | None = Field(None, description="Texto literal del observador")
    id_municipio: int = Field(..., description="FK a shared.municipio")
    codigo_comunidad: str = Field(..., description="Código INE de comunidad")
    id_pe_off: str | None = Field(None, max_length=36, description="ID offline generado por dispositivo")
    cadena_biocultural: CadenaBioculturalCreate = Field(..., description="Cadena de 4 niveles obligatoria")
    periodo: PeriodoCreate = Field(..., description="Período del pronóstico")
    contexto: ContextoCreate | None = Field(None, description="Coordenadas y notas")
    pronosticos: list[PronosticoLargoItemCreate] = Field(
        ..., min_length=1, description="Al menos un bloque de pronóstico"
    )
    recomendaciones: list[RecomendacionLargoCreate] | None = Field(
        None, description="Recomendaciones en texto libre (lo que el productor recomienda hacer), con su id y su id offline"
    )
    observadores: list[ObservadorLargoCreate] = Field(
        ..., min_length=1,
        description="1..N observadores obligatorios: auto-registro (el observador sube) "
                    "o en representación (el recolector menciona a uno o más observadores)"
    )


class PronosticoLargoUpdate(SinbBaseResponse):
    """PUT /pronostico-largo/{id} — campos opcionales; si vienen pronosticos/recomendaciones reemplazan a los hijos."""
    fecha_emision: date | None = None
    texto_observador: str | None = None
    id_municipio: int | None = None
    codigo_comunidad: str | None = None
    estado: Literal["EMITIDO", "ACEPTADO", "RECHAZADO", "EN_REVISION"] | None = None
    cadena_biocultural: CadenaBioculturalCreate | None = None
    periodo: PeriodoCreate | None = None
    contexto: ContextoCreate | None = None
    pronosticos: list[PronosticoLargoItemCreate] | None = Field(
        None, description="Si se envía, reemplaza todos los bloques hijos"
    )
    recomendaciones: list[RecomendacionLargoCreate] | None = Field(
        None, description="Si se envía, reemplaza todas las recomendaciones hijas (texto libre)"
    )


class PronosticoLargoResponse(SinbBaseResponse):
    id: UUID
    codigo: str
    fecha_emision: date
    periodo_inicio: date
    periodo_fin: date
    estado: str
    id_usuario_subio: int | None = None
    id_municipio: int | None = None
    codigo_comunidad: str | None = None
    texto_observador: str | None = None
    cadena_biocultural: dict | None = None
    contexto: dict | None = None
    pronosticos: list[dict] = Field(default_factory=list, description="Bloques con sus escenarios")
    recomendaciones: list[dict] = Field(default_factory=list, description="Recomendaciones en texto libre (id, id_recomendacion_off, nombre)")
    observadores: list[dict] = Field(default_factory=list)
    tipo_registro: Literal["INDIVIDUAL", "COLECTIVO"] | None = Field(
        None, description="Derivado: INDIVIDUAL con 1 observador, COLECTIVO con 2+ (07 §4.5)"
    )
    creado_en: datetime
    actualizado_en: datetime | None = None


class PronosticoCortoCreate(SinbBaseResponse):
    id_pt_off: str | None = Field(None, max_length=36, description="ID offline generado por dispositivo")
    id_categoria: UUID = Field(..., description="FK a categoría de pronóstico")
    fecha_emision: date = Field(..., description="Fecha de emisión")
    fecha_inicio: date = Field(..., description="Inicio de vigencia")
    fecha_fin: date = Field(..., description="Fin de vigencia")
    texto_observador: str | None = Field(None, description="Texto literal del observador")
    confianza: Literal["ALTA", "MEDIA", "BAJA"] | None = Field(None, description="Nivel de confianza")
    id_usuario_subio: int | None = Field(None, description="Usuario que subió")
    id_municipio: int | None = Field(None, description="FK a municipio (opcional, se infiere desde coordenadas si no viene)")
    codigo_comunidad: str | None = Field(None, description="Código INE de comunidad (opcional, se infiere desde coordenadas si no viene)")
    contexto: dict | None = Field(None, description="Coordenadas GPS: {latitud, longitud} (opcional, para inferir municipio/comunidad)")


class PronosticoCortoUpdate(SinbBaseResponse):
    id_categoria: UUID | None = None
    fecha_emision: date | None = None
    fecha_inicio: date | None = None
    fecha_fin: date | None = None
    texto_observador: str | None = None
    confianza: Literal["ALTA", "MEDIA", "BAJA"] | None = None
    codigo_comunidad: str | None = None


class PronosticoCortoResponse(SinbBaseResponse):
    id: UUID
    id_pt_off: str | None = None
    codigo: str
    id_categoria: UUID
    categoria: dict | None = None
    codigo_comunidad: str | None = None
    id_municipio: int | None = None
    fecha_emision: date
    fecha_inicio: date
    fecha_fin: date
    texto_observador: str | None = None
    confianza: Literal["ALTA", "MEDIA", "BAJA"] | None = None
    id_usuario_subio: int | None = None
    creado_en: datetime


# ============================================================================
# VALIDACIÓN DE PRONÓSTICOS
# ============================================================================

class VerificacionPronosticoCreate(SinbBaseResponse):
    """Validación MANUAL de pronóstico."""
    id_pronostico_largo: UUID | None = Field(None, description="FK a pronóstico estacional")
    id_pronostico_corto: UUID | None = Field(None, description="FK a pronóstico temporal")
    id_municipio: int | None = Field(None, description="FK a municipio")
    estado: Literal["COINCIDE", "NO_COINCIDE"] = Field(..., description="Resultado de validación")
    notas: str | None = Field(None, description="Observación cualitativa")
    acierto_categoria: bool | None = Field(None, description="¿Coincidió la categoría?")


class VerificacionPronosticoResponse(SinbBaseResponse):
    id: UUID
    id_pronostico_largo: UUID | None
    id_pronostico_corto: UUID | None
    id_variable_climatica: UUID | None
    codigo_comunidad: str | None
    id_municipio: int | None
    acierto_categoria: bool | None
    error_absoluto: float | None
    sesgo: float | None
    estado: Literal["COINCIDE", "NO_COINCIDE", "PENDIENTE", "EN_VERIFICACION", "SIN_DATOS", "NO_VERIFICABLE"]
    notas: str | None
    es_autoevaluada: bool
    verificado_por: int | None
    verificador: dict | None = None
    fecha_verificacion: datetime | None
    creado_en: datetime


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
# AVISOS
# ============================================================================

class AvisoCreate(SinbBaseResponse):
    id_aviso_off: str | None = Field(None, max_length=36, description="ID offline generado por dispositivo")
    id_categoria: UUID = Field(..., description="FK a categoría de pronóstico")
    codigo_comunidad: str = Field(..., description="Código INE de comunidad")
    id_municipio: int = Field(..., description="FK a municipio")
    mensaje: str = Field(..., description="Mensaje del aviso")
    vigencia_horas: int = Field(24, ge=1, le=168, description="Vigencia en horas (1-168)")
    id_usuario_subio: int | None = Field(None, description="Usuario que subió (recolector u observador)")


class AvisoUpdate(SinbBaseResponse):
    mensaje: str | None = None
    vigencia_horas: int | None = None
    estado: Literal["ACTIVO", "INACTIVO", "ELIMINADO"] | None = None


class AvisoResponse(SinbBaseResponse):
    id: UUID
    id_aviso_off: str | None
    codigo: str
    id_categoria: UUID
    categoria: dict | None = None
    codigo_comunidad: str
    id_municipio: int
    mensaje: str
    fecha_emision: datetime
    vigencia_horas: int
    fecha_vencimiento: datetime
    estado: Literal["ACTIVO", "INACTIVO", "ELIMINADO"]
    id_usuario_subio: int | None
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


class ObservadorIndiceUpdate(SinbBaseResponse):
    valor: float | None = Field(None, description="Valor calculado del índice")
    fecha_calculo: date | None = Field(None, description="Fecha de cálculo del índice")


class ObservadorIndiceResponse(SinbBaseResponse):
    id: UUID
    id_usuario: int
    usuario: dict | None = None
    id_indicador_natural: UUID
    indicador: dict | None = None
    tipo: Literal["ESTACIONAL", "TEMPORAL"]
    valor: float | None
    fecha_calculo: date
    creado_en: datetime | None = None


# ============================================================================
# ASIGNACIÓN DE OBSERVADORES A PRONÓSTICOS
# ============================================================================

class PronosticoObservadorCreate(SinbBaseResponse):
    """Asignar observador(es) a un pronóstico (recolector → observadores del mismo municipio)."""
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
# REPORTES
# ============================================================================

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
    """Solicitud de consulta de pronóstico digital (16 días desde hoy)."""
    id_municipio: int = Field(..., description="ID del municipio")
    tipo: Literal["daily", "hourly"] = Field(
        "daily", 
        description="Tipo de pronóstico: daily (16 días), hourly (168 horas)"
    )


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
# PRONÓSTICO DIARIO (HISTÓRICO Y CONSULTA)
# ============================================================================

class PronosticoDiarioHistoricoRequest(SinbBaseResponse):
    """Filtros para consultar histórico de pronóstico diario."""
    id_municipio: int | None = Field(None, description="Filtrar por municipio")
    codigo_comunidad: str | None = Field(None, description="Filtrar por código de comunidad")
    fecha_desde: date | None = Field(None, description="Fecha desde")
    fecha_hasta: date | None = Field(None, description="Fecha hasta")
    temp_max_min: float | None = Field(None, ge=-50, le=50, description="Temperatura máxima mínima")
    temp_max_max: float | None = Field(None, ge=-50, le=50, description="Temperatura máxima máxima")
    precipitacion_min: float | None = Field(None, ge=0, description="Precipitación mínima")
    precipitacion_max: float | None = Field(None, ge=0, description="Precipitación máxima")
    pagina: int = Field(1, ge=1, description="Número de página")
    por_pagina: int = Field(50, ge=1, le=500, description="Registros por página")


class PronosticoDiarioResponse(SinbBaseResponse):
    """Respuesta de pronóstico diario individual."""
    id: UUID
    id_municipio: int
    municipio: str | None = None
    fecha: date
    temp_max: float | None = None
    temp_min: float | None = None
    precipitacion_suma: float | None = None
    precipitacion_prob_max: int | None = None
    humedad_relativa_max: int | None = None
    humedad_relativa_min: int | None = None
    evapotranspiracion: float | None = None
    viento_velocidad_max: float | None = None
    viento_direccion: int | None = None
    radiacion_solar: float | None = None
    uv_index_max: float | None = None
    sunrise: datetime | None = None
    sunset: datetime | None = None
    fuente: str | None = None


class PronosticoDiarioHistoricoResponse(SinbBaseResponse):
    """Respuesta paginada de histórico de pronóstico diario."""
    data: list[PronosticoDiarioResponse]
    total: int
    pagina: int
    por_pagina: int
    total_paginas: int


class PronosticoDigitalConsultarRequest(SinbBaseResponse):
    """Solicitud para consultar pronóstico digital almacenado (16 días)."""
    id_municipio: int = Field(..., description="ID del municipio")
    tipo: Literal["daily", "hourly"] = Field(
        "daily", 
        description="Tipo de pronóstico: daily (16 días desde hoy), hourly (168 horas)"
    )


class PronosticoDigitalConsultarResponse(SinbBaseResponse):
    """Respuesta de pronóstico digital (16 días desde hoy)."""
    id_municipio: int
    municipio: str | None = None
    tipo: str
    registros: list[PronosticoDiarioResponse]
    fecha_consulta: date
    dias_disponibles: int


# ============================================================================
# FOTOS DE INDICADOR NATURAL
# ============================================================================

class IndicadorFotoUpdate(SinbBaseResponse):
    """Actualizar datos de una foto de indicador natural (autor o admin)."""
    descripcion: str = Field(..., max_length=500, description="Descripción de la foto")


class IndicadorFotoResponse(SinbBaseResponse):
    """Foto de un indicador natural."""
    id: UUID
    id_indicador_natural: UUID
    path_foto: str
    url_descarga: str | None = None
    descripcion: str
    id_usuario_subio: int
    usuario: dict | None = None
    creado_en: datetime
    actualizado_en: datetime


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


# ============================================================================
# SCHEMAS DE RESPUESTA PARA ENDPOINTS GET (2026-10-03)
# ============================================================================

class PronosticoLargoListItemResponse(SinbBaseResponse):
    """Respuesta simplificada para lista de pronósticos estacionales."""
    id: UUID
    codigo: str
    fecha_emision: date
    periodo_inicio: date
    periodo_fin: date
    estado: str
    id_usuario_subio: int | None
    id_municipio: int | None
    cadena_biocultural: dict | None = None
    creado_en: datetime


class PronosticoCortoListItemResponse(SinbBaseResponse):
    """Respuesta simplificada para lista de pronósticos temporales."""
    id: UUID
    codigo: str
    fecha_emision: date
    periodo_inicio: date
    periodo_fin: date
    estado: str
    categoria: str | None
    confianza: int | None
    id_usuario_subio: int | None = None
    creado_en: datetime


class AvisoListItemResponse(SinbBaseResponse):
    """Respuesta simplificada para lista de avisos."""
    id: UUID
    codigo: str
    fecha_emision: date
    vigencia_horas: int
    mensaje: str
    estado: str
    verificado: bool | None
    creado_en: datetime


class IndicadorNaturalListItemResponse(SinbBaseResponse):
    """Respuesta simplificada para lista de indicadores."""
    id: UUID
    codigo: str
    nombre_cientifico: str
    nombre_comun: str | None
    id_grupo: UUID | None
    grupo: dict | None
    estado: str


class CaracteristicaListItemResponse(SinbBaseResponse):
    """Respuesta simplificada para lista de características."""
    id: UUID
    id_indicador_natural: UUID
    caracteristica: str
    estado: str
    indicador: dict | None


class ComportamientoListItemResponse(SinbBaseResponse):
    """Respuesta simplificada para lista de comportamientos."""
    id: UUID
    id_grupo: UUID | None
    id_caracteristica: UUID
    comportamiento: str
    estado: str
    grupo: dict | None
    caracteristica: dict | None


class SignificadoListItemResponse(SinbBaseResponse):
    """Respuesta simplificada para lista de significados."""
    id: UUID
    id_grupo: UUID | None
    id_comportamiento: UUID
    significado: str
    estado: str
    grupo: dict | None
    comportamiento: dict | None


class EscenarioListItemResponse(SinbBaseResponse):
    """Respuesta simplificada para lista de escenarios."""
    id: UUID
    id_categoria: UUID
    id_municipio: int | None
    nombre_escenario: str
    confianza: str | None
    categoria: dict | None
    estado: str
