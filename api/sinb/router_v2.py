from fastapi import APIRouter, Depends, HTTPException, Query, Body, Path
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Literal
from datetime import date
from uuid import UUID

from ..database import get_db
from ..dependencies import get_current_user
from ..response import SuccessResponse, DataListResponse, DataItemResponse
from . import service
from .schemas import (
    GrupoCreate, GrupoUpdate, GrupoResponse,
    IndicadorNaturalCreate, IndicadorNaturalUpdate, IndicadorNaturalResponse,
    CaracteristicaCreate, CaracteristicaUpdate, CaracteristicaResponse,
    ComportamientoCreate, ComportamientoUpdate, ComportamientoResponse,
    SignificadoCreate, SignificadoUpdate, SignificadoResponse,
    ZonaGeograficaCreate, ZonaGeograficaUpdate, ZonaGeograficaResponse,
    CampoPronosticoCreate, CampoPronosticoUpdate, CampoPronosticoResponse,
    EscenarioCreate, EscenarioUpdate, EscenarioResponse,
    CategoriaPronosticoTemporalCreate, CategoriaPronosticoTemporalUpdate,
    DimensionRecomendacionCreate, DimensionRecomendacionUpdate,
    CategoriaComportamientoCreate, CategoriaComportamientoUpdate,
    ObservacionCreate, ObservacionUpdate, ObservacionResponse,
    PronosticoEstacionalCreate, PronosticoEstacionalUpdate, PronosticoEstacionalResponse,
    PronosticoTemporalCreate, PronosticoTemporalUpdate, PronosticoTemporalResponse,
    VerificacionPronosticoCreate, CalculoVerificacionRequest, CalculoVerificacionResponse,
    RecomendacionLocalCreate, RecomendacionLocalUpdate,
    AvisoCreate, AvisoUpdate, AvisoResponse,
    ObservadorIndiceCreate, ObservadorIndiceResponse,
    PronosticoObservadorCreate, PronosticoObservadorResponse,
    MapaFiltros,
)
from .utils import require_rol, scope_geografico, ROLES_SINB_ADMIN, ROLES_SINB_PRONOSTICO, ROLES_SINB_OBSERVACION, ROLES_SINB_VALIDACION, ROLES_SINB_LOCAL


router = APIRouter(prefix="/sinb")


# ============================================================================
# TAGS METADATA PARA SWAGGER (organización jerárquica)
# ============================================================================

TAGS_CATALOGOS = "SINB > Catálogos Bioculturales"
TAGS_PREDICCIONES = "SINB > Predicciones"
TAGS_PREDICCIONES_LARGO = "SINB > Predicciones > Largo Plazo (Estacionales)"
TAGS_PREDICCIONES_CORTO = "SINB > Predicciones > Corto Plazo (Temporales)"
TAGS_PREDICCIONES_AVISOS = "SINB > Predicciones > Avisos (Alertas 24-48h)"
TAGS_PREDICCIONES_DIGITALES = "SINB > Predicciones > Pronósticos Digitales (Open-Meteo)"
TAGS_OBSERVACIONES = "SINB > Observaciones"
TAGS_VALIDACION = "SINB > Validación de Predicciones"
TAGS_RECOMENDACIONES = "SINB > Recomendaciones"
TAGS_MAPAS = "SINB > Mapas GeoJSON"
TAGS_REPORTES = "SINB > Reportes Enriquecidos"
TAGS_OBSERVADORES = "SINB > Observadores e Índices"


# ============================================================================
# CATÁLOGOS BIOCURALTURALES (sin paginación, siempre completos)
# ============================================================================

# --- Grupo ---

@router.get("/grupo", tags=[TAGS_CATALOGOS], response_model=DataListResponse[GrupoResponse],
            summary="Listar grupos bioculturales (completo, sin paginación)")
def listar_grupos(db: Session = Depends(get_db)):
    """Obtener todos los grupos bioculturales activos. Catálogo completo sin paginación."""
    data = service.get_grupos(db)
    return SuccessResponse(message="Grupos listados correctamente", data=data)


@router.post("/grupo", tags=[TAGS_CATALOGOS], status_code=201,
             dependencies=[Depends(require_rol(*ROLES_SINB_ADMIN))],
             summary="Crear grupo biocultural")
def crear_grupo(data: GrupoCreate, db: Session = Depends(get_db),
                user=Depends(get_current_user)):
    """Crear nuevo grupo biocultural. Requiere rol admin o superadmin."""
    result = service.create_grupo(db, data.model_dump())
    return SuccessResponse(message="Grupo creado correctamente", data=result)


@router.get("/grupo/{id}", tags=[TAGS_CATALOGOS], response_model=DataItemResponse[GrupoResponse])
def obtener_grupo(id: UUID, db: Session = Depends(get_db)):
    """Obtener grupo por ID."""
    result = service.get_grupo(db, id)
    if not result:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")
    return SuccessResponse(message="Grupo obtenido correctamente", data=result)


@router.put("/grupo/{id}", tags=[TAGS_CATALOGOS],
            dependencies=[Depends(require_rol(*ROLES_SINB_ADMIN))])
def actualizar_grupo(id: UUID, data: GrupoUpdate, db: Session = Depends(get_db)):
    """Actualizar grupo existente."""
    result = service.update_grupo(db, id, data.model_dump(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")
    return SuccessResponse(message="Grupo actualizado correctamente", data=result)


@router.delete("/grupo/{id}", tags=[TAGS_CATALOGOS],
               dependencies=[Depends(require_rol(*ROLES_SINB_ADMIN))])
def eliminar_grupo(id: UUID, db: Session = Depends(get_db)):
    """Eliminar lógico de grupo (cambia estado a ELIMINADO)."""
    service.delete_grupo(db, id)
    return {"message": "Grupo eliminado correctamente"}


# --- Indicador Natural ---

@router.get("/indicador-natural", tags=[TAGS_CATALOGOS],
            summary="Listar indicadores naturales (completo, con filtros)")
def listar_indicadores(
    id_grupo: UUID | None = Query(None, description="Filtrar por grupo"),
    codigo: str | None = Query(None, description="Buscar por código"),
    nombre_cientifico: str | None = Query(None, description="Buscar por nombre científico"),
    nombre_comun: str | None = Query(None, description="Buscar por nombre común"),
    db: Session = Depends(get_db)
):
    """Obtener indicadores naturales activos con filtros opcionales."""
    data = service.get_indicadores_naturales(db, id_grupo, codigo, nombre_cientifico, nombre_comun)
    return SuccessResponse(message="Indicadores listados correctamente", data=data)


@router.post("/indicador-natural", tags=[TAGS_CATALOGOS], status_code=201,
             dependencies=[Depends(require_rol(*ROLES_SINB_ADMIN))])
def crear_indicador(data: IndicadorNaturalCreate, db: Session = Depends(get_db),
                    user=Depends(get_current_user)):
    """Crear nuevo indicador natural."""
    result = service.create_indicador_natural(db, data.model_dump())
    return SuccessResponse(message="Indicador creado correctamente", data=result)


@router.get("/indicador-natural/{id}", tags=[TAGS_CATALOGOS])
def obtener_indicador(id: UUID, db: Session = Depends(get_db)):
    """Obtener indicador natural por ID con grupo anidado."""
    result = service.get_indicador_natural(db, id)
    if not result:
        raise HTTPException(status_code=404, detail="Indicador no encontrado")
    return SuccessResponse(message="Indicador obtenido correctamente", data=result)


@router.put("/indicador-natural/{id}", tags=[TAGS_CATALOGOS],
            dependencies=[Depends(require_rol(*ROLES_SINB_ADMIN))])
def actualizar_indicador(id: UUID, data: IndicadorNaturalUpdate, db: Session = Depends(get_db)):
    """Actualizar indicador natural."""
    result = service.update_indicador_natural(db, id, data.model_dump(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="Indicador no encontrado")
    return SuccessResponse(message="Indicador actualizado correctamente", data=result)


@router.delete("/indicador-natural/{id}", tags=[TAGS_CATALOGOS],
               dependencies=[Depends(require_rol(*ROLES_SINB_ADMIN))])
def eliminar_indicador(id: UUID, db: Session = Depends(get_db)):
    """Eliminar lógico de indicador natural."""
    service.delete_indicador_natural(db, id)
    return {"message": "Indicador eliminado correctamente"}


# --- Característica ---

@router.get("/caracteristica", tags=[TAGS_CATALOGOS],
            summary="Listar características (completo)")
def listar_caracteristicas(
    id_indicador_natural: UUID | None = Query(None, description="Filtrar por indicador"),
    db: Session = Depends(get_db)
):
    """Obtener características activas con filtro opcional por indicador."""
    data = service.get_caracteristicas(db, id_indicador_natural)
    return SuccessResponse(message="Características listadas correctamente", data=data)


@router.post("/caracteristica", tags=[TAGS_CATALOGOS], status_code=201,
             dependencies=[Depends(require_rol(*ROLES_SINB_ADMIN))])
def crear_caracteristica(data: CaracteristicaCreate, db: Session = Depends(get_db)):
    """Crear característica."""
    result = service.create_caracteristica(db, data.model_dump())
    return SuccessResponse(message="Característica creada correctamente", data=result)


@router.put("/caracteristica/{id}", tags=[TAGS_CATALOGOS],
            dependencies=[Depends(require_rol(*ROLES_SINB_ADMIN))])
def actualizar_caracteristica(id: UUID, data: CaracteristicaUpdate, db: Session = Depends(get_db)):
    """Actualizar característica."""
    result = service.update_caracteristica(db, id, data.model_dump(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="Característica no encontrada")
    return SuccessResponse(message="Característica actualizada correctamente", data=result)


@router.delete("/caracteristica/{id}", tags=[TAGS_CATALOGOS],
               dependencies=[Depends(require_rol(*ROLES_SINB_ADMIN))])
def eliminar_caracteristica(id: UUID, db: Session = Depends(get_db)):
    """Eliminar característica."""
    service.delete_caracteristica(db, id)
    return {"message": "Característica eliminada correctamente"}


# --- Comportamiento ---

@router.get("/comportamiento", tags=[TAGS_CATALOGOS],
            summary="Listar comportamientos (completo)")
def listar_comportamientos(
    id_grupo: UUID | None = Query(None, description="Filtrar por grupo"),
    id_caracteristica: UUID | None = Query(None, description="Filtrar por característica"),
    db: Session = Depends(get_db)
):
    """Obtener comportamientos activos con filtros."""
    data = service.get_comportamientos(db, id_grupo, id_caracteristica)
    return SuccessResponse(message="Comportamientos listados correctamente", data=data)


@router.post("/comportamiento", tags=[TAGS_CATALOGOS], status_code=201,
             dependencies=[Depends(require_rol(*ROLES_SINB_ADMIN))])
def crear_comportamiento(data: ComportamientoCreate, db: Session = Depends(get_db)):
    """Crear comportamiento."""
    result = service.create_comportamiento(db, data.model_dump())
    return SuccessResponse(message="Comportamiento creado correctamente", data=result)


@router.put("/comportamiento/{id}", tags=[TAGS_CATALOGOS],
            dependencies=[Depends(require_rol(*ROLES_SINB_ADMIN))])
def actualizar_comportamiento(id: UUID, data: ComportamientoUpdate, db: Session = Depends(get_db)):
    """Actualizar comportamiento."""
    result = service.update_comportamiento(db, id, data.model_dump(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="Comportamiento no encontrado")
    return SuccessResponse(message="Comportamiento actualizado correctamente", data=result)


@router.delete("/comportamiento/{id}", tags=[TAGS_CATALOGOS],
               dependencies=[Depends(require_rol(*ROLES_SINB_ADMIN))])
def eliminar_comportamiento(id: UUID, db: Session = Depends(get_db)):
    """Eliminar comportamiento."""
    service.delete_comportamiento(db, id)
    return {"message": "Comportamiento eliminado correctamente"}


# --- Significado ---

@router.get("/significado", tags=[TAGS_CATALOGOS],
            summary="Listar significados (completo)")
def listar_significados(
    id_grupo: UUID | None = Query(None, description="Filtrar por grupo"),
    id_comportamiento: UUID | None = Query(None, description="Filtrar por comportamiento"),
    categoria: str | None = Query(None, description="Filtrar por categoría"),
    db: Session = Depends(get_db)
):
    """Obtener significados activos con filtros."""
    data = service.get_significados(db, id_grupo, id_comportamiento, categoria)
    return SuccessResponse(message="Significados listados correctamente", data=data)


@router.post("/significado", tags=[TAGS_CATALOGOS], status_code=201,
             dependencies=[Depends(require_rol(*ROLES_SINB_ADMIN))])
def crear_significado(data: SignificadoCreate, db: Session = Depends(get_db)):
    """Crear significado."""
    result = service.create_significado(db, data.model_dump())
    return SuccessResponse(message="Significado creado correctamente", data=result)


@router.put("/significado/{id}", tags=[TAGS_CATALOGOS],
            dependencies=[Depends(require_rol(*ROLES_SINB_ADMIN))])
def actualizar_significado(id: UUID, data: SignificadoUpdate, db: Session = Depends(get_db)):
    """Actualizar significado."""
    result = service.update_significado(db, id, data.model_dump(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="Significado no encontrado")
    return SuccessResponse(message="Significado actualizado correctamente", data=result)


@router.delete("/significado/{id}", tags=[TAGS_CATALOGOS],
               dependencies=[Depends(require_rol(*ROLES_SINB_ADMIN))])
def eliminar_significado(id: UUID, db: Session = Depends(get_db)):
    """Eliminar significado."""
    service.delete_significado(db, id)
    return {"message": "Significado eliminado correctamente"}


# --- Zona Geográfica ---

@router.get("/zona-geografica", tags=[TAGS_CATALOGOS],
            summary="Listar zonas geográficas (completo)")
def listar_zonas_geograficas(db: Session = Depends(get_db)):
    """Obtener todas las zonas geográficas activas."""
    data = service.get_zonas_geograficas(db)
    return SuccessResponse(message="Zonas listadas correctamente", data=data)


@router.post("/zona-geografica", tags=[TAGS_CATALOGOS], status_code=201,
             dependencies=[Depends(require_rol(*ROLES_SINB_ADMIN))])
def crear_zona_geografica(data: ZonaGeograficaCreate, db: Session = Depends(get_db)):
    """Crear zona geográfica."""
    result = service.create_zona_geografica(db, data.model_dump())
    return SuccessResponse(message="Zona creada correctamente", data=result)


@router.put("/zona-geografica/{id}", tags=[TAGS_CATALOGOS],
            dependencies=[Depends(require_rol(*ROLES_SINB_ADMIN))])
def actualizar_zona_geografica(id: UUID, data: ZonaGeograficaUpdate, db: Session = Depends(get_db)):
    """Actualizar zona geográfica."""
    result = service.update_zona_geografica(db, id, data.model_dump(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="Zona no encontrada")
    return SuccessResponse(message="Zona actualizada correctamente", data=result)


@router.delete("/zona-geografica/{id}", tags=[TAGS_CATALOGOS],
               dependencies=[Depends(require_rol(*ROLES_SINB_ADMIN))])
def eliminar_zona_geografica(id: UUID, db: Session = Depends(get_db)):
    """Eliminar zona geográfica."""
    service.delete_zona_geografica(db, id)
    return {"message": "Zona eliminada correctamente"}


# --- Campo Pronóstico ---

@router.get("/campo-pronostico", tags=[TAGS_CATALOGOS],
            summary="Listar campos de pronóstico (completo)")
def listar_campos_pronostico(
    nombre: str | None = Query(None, description="Buscar por nombre"),
    tipo: str | None = Query(None, description="Filtrar por tipo"),
    db: Session = Depends(get_db)
):
    """Obtener campos de pronóstico activos."""
    data = service.get_campos_pronostico(db, nombre, tipo)
    return SuccessResponse(message="Campos listados correctamente", data=data)


@router.post("/campo-pronostico", tags=[TAGS_CATALOGOS], status_code=201,
             dependencies=[Depends(require_rol(*ROLES_SINB_ADMIN))])
def crear_campo_pronostico(data: CampoPronosticoCreate, db: Session = Depends(get_db)):
    """Crear campo de pronóstico."""
    result = service.create_campo_pronostico(db, data.model_dump())
    return SuccessResponse(message="Campo creado correctamente", data=result)


@router.put("/campo-pronostico/{id}", tags=[TAGS_CATALOGOS],
            dependencies=[Depends(require_rol(*ROLES_SINB_ADMIN))])
def actualizar_campo_pronostico(id: UUID, data: CampoPronosticoUpdate, db: Session = Depends(get_db)):
    """Actualizar campo de pronóstico."""
    result = service.update_campo_pronostico(db, id, data.model_dump(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="Campo no encontrado")
    return SuccessResponse(message="Campo actualizado correctamente", data=result)


@router.delete("/campo-pronostico/{id}", tags=[TAGS_CATALOGOS],
               dependencies=[Depends(require_rol(*ROLES_SINB_ADMIN))])
def eliminar_campo_pronostico(id: UUID, db: Session = Depends(get_db)):
    """Eliminar campo de pronóstico."""
    service.delete_campo_pronostico(db, id)
    return {"message": "Campo eliminado correctamente"}


# --- Escenario ---

@router.get("/escenario", tags=[TAGS_CATALOGOS],
            summary="Listar escenarios (completo)")
def listar_escenarios(
    id_campo_pronostico: UUID | None = Query(None, description="Filtrar por campo"),
    db: Session = Depends(get_db)
):
    """Obtener escenarios activos."""
    data = service.get_escenarios(db, id_campo_pronostico)
    return SuccessResponse(message="Escenarios listados correctamente", data=data)


@router.post("/escenario", tags=[TAGS_CATALOGOS], status_code=201,
             dependencies=[Depends(require_rol(*ROLES_SINB_ADMIN))])
def crear_escenario(data: EscenarioCreate, db: Session = Depends(get_db)):
    """Crear escenario."""
    result = service.create_escenario(db, data.model_dump())
    return SuccessResponse(message="Escenario creado correctamente", data=result)


@router.put("/escenario/{id}", tags=[TAGS_CATALOGOS],
            dependencies=[Depends(require_rol(*ROLES_SINB_ADMIN))])
def actualizar_escenario(id: UUID, data: EscenarioUpdate, db: Session = Depends(get_db)):
    """Actualizar escenario."""
    result = service.update_escenario(db, id, data.model_dump(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="Escenario no encontrado")
    return SuccessResponse(message="Escenario actualizado correctamente", data=result)


@router.delete("/escenario/{id}", tags=[TAGS_CATALOGOS],
               dependencies=[Depends(require_rol(*ROLES_SINB_ADMIN))])
def eliminar_escenario(id: UUID, db: Session = Depends(get_db)):
    """Eliminar escenario."""
    service.delete_escenario(db, id)
    return {"message": "Escenario eliminado correctamente"}


# --- Dimensión Recomendación ---

@router.get("/dimension-recomendacion", tags=[TAGS_CATALOGOS],
            summary="Listar dimensiones de recomendación (completo)")
def listar_dimensiones(db: Session = Depends(get_db)):
    """Obtener dimensiones de recomendación activas."""
    data = service.get_dimensiones_recomendacion(db)
    return SuccessResponse(message="Dimensiones listadas correctamente", data=data)


@router.post("/dimension-recomendacion", tags=[TAGS_CATALOGOS], status_code=201,
             dependencies=[Depends(require_rol(*ROLES_SINB_ADMIN))])
def crear_dimension(data: DimensionRecomendacionCreate, db: Session = Depends(get_db)):
    """Crear dimensión de recomendación."""
    result = service.create_dimension_recomendacion(db, data.model_dump())
    return SuccessResponse(message="Dimensión creada correctamente", data=result)


@router.put("/dimension-recomendacion/{id}", tags=[TAGS_CATALOGOS],
            dependencies=[Depends(require_rol(*ROLES_SINB_ADMIN))])
def actualizar_dimension(id: UUID, data: DimensionRecomendacionUpdate, db: Session = Depends(get_db)):
    """Actualizar dimensión."""
    result = service.update_dimension_recomendacion(db, id, data.model_dump(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="Dimensión no encontrada")
    return SuccessResponse(message="Dimensión actualizada correctamente", data=result)


@router.delete("/dimension-recomendacion/{id}", tags=[TAGS_CATALOGOS],
               dependencies=[Depends(require_rol(*ROLES_SINB_ADMIN))])
def eliminar_dimension(id: UUID, db: Session = Depends(get_db)):
    """Eliminar dimensión."""
    service.delete_dimension_recomendacion(db, id)
    return {"message": "Dimensión eliminada correctamente"}


# --- Categoría Comportamiento ---

@router.get("/categoria-comportamiento", tags=[TAGS_CATALOGOS],
            summary="Listar categorías de comportamiento (completo)")
def listar_categorias(
    id_dimension: UUID | None = Query(None, description="Filtrar por dimensión"),
    db: Session = Depends(get_db)
):
    """Obtener categorías de comportamiento activas."""
    data = service.get_categorias_comportamiento(db, id_dimension)
    return SuccessResponse(message="Categorías listadas correctamente", data=data)


@router.post("/categoria-comportamiento", tags=[TAGS_CATALOGOS], status_code=201,
             dependencies=[Depends(require_rol(*ROLES_SINB_ADMIN))])
def crear_categoria(data: CategoriaComportamientoCreate, db: Session = Depends(get_db)):
    """Crear categoría de comportamiento."""
    result = service.create_categoria_comportamiento(db, data.model_dump())
    return SuccessResponse(message="Categoría creada correctamente", data=result)


@router.put("/categoria-comportamiento/{id}", tags=[TAGS_CATALOGOS],
            dependencies=[Depends(require_rol(*ROLES_SINB_ADMIN))])
def actualizar_categoria(id: UUID, data: CategoriaComportamientoUpdate, db: Session = Depends(get_db)):
    """Actualizar categoría."""
    result = service.update_categoria_comportamiento(db, id, data.model_dump(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    return SuccessResponse(message="Categoría actualizada correctamente", data=result)


@router.delete("/categoria-comportamiento/{id}", tags=[TAGS_CATALOGOS],
               dependencies=[Depends(require_rol(*ROLES_SINB_ADMIN))])
def eliminar_categoria(id: UUID, db: Session = Depends(get_db)):
    """Eliminar categoría."""
    service.delete_categoria_comportamiento(db, id)
    return {"message": "Categoría eliminada correctamente"}


# ============================================================================
# OBSERVACIONES (últimos 15, paginación, filtros geográficos)
# ============================================================================

@router.get("/observacion", tags=[TAGS_OBSERVACIONES],
            summary="Listar observaciones (últimos 15, con filtros)")
def listar_observaciones(
    skip: int = Query(0, ge=0, description="Saltar para paginación"),
    limit: int = Query(15, ge=1, le=100, description="Límite de registros (default 15, max 100)"),
    id_municipio: int | None = Query(None, description="Filtrar por municipio"),
    id_departamento: int | None = Query(None, description="Filtrar por departamento"),
    codigo_comunidad: str | None = Query(None, description="Filtrar por comunidad"),
    id_usuario_responsable: int | None = Query(None, description="Filtrar por responsable"),
    fecha_inicio_desde: date | None = Query(None, description="Fecha inicio desde"),
    fecha_inicio_hasta: date | None = Query(None, description="Fecha inicio hasta"),
    es_validada: bool | None = Query(None, description="Filtrar por validación"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """
    Listar observaciones con paginación (default últimos 15) y filtros opcionales.
    
    - **Filtros geográficos**: se aplican automáticamente según el rol del usuario
    - **Roles locales** (UGR, Responsable, Alcalde): ven solo su municipio
    - **Roles nacionales** (admin, VIDECI): ven todos o filtran por parámetros
    """
    # Aplicar scope geográfico según rol
    scope = scope_geografico(user, id_departamento, None, id_municipio)
    filters = {
        **scope,
        "codigo_comunidad": codigo_comunidad,
        "id_usuario_responsable": id_usuario_responsable,
        "fecha_inicio_desde": fecha_inicio_desde,
        "fecha_inicio_hasta": fecha_inicio_hasta,
        "es_validada": es_validada,
    }
    
    data, total = service.get_observaciones(db, skip=skip, limit=limit, filters=filters)
    return SuccessResponse(message="Observaciones listadas correctamente", data=data, total=total)


@router.get("/observacion/{id}", tags=[TAGS_OBSERVACIONES],
            summary="Obtener observación completa con registros")
def obtener_observacion(id: UUID, db: Session = Depends(get_db),
                        user=Depends(get_current_user)):
    """Obtener observación con todos sus registros anidados."""
    result = service.get_observacion(db, id)
    if not result:
        raise HTTPException(status_code=404, detail="Observación no encontrada")
    return SuccessResponse(message="Observación obtenida correctamente", data=result)


@router.post("/observacion", tags=[TAGS_OBSERVACIONES], status_code=201,
             dependencies=[Depends(require_rol(*ROLES_SINB_OBSERVACION))],
             summary="Crear observación con registros opcionales")
def crear_observacion(data: ObservacionCreate, db: Session = Depends(get_db),
                      user=Depends(get_current_user)):
    """
    Crear observación con registros opcionales.
    
    - **codigo_corto**: se genera automáticamente
    - **id_usuario_responsable**: si no se envía, usa el usuario actual
    - **observacion_registro**: lista opcional de registros anidados
    """
    result = service.create_observacion(db, data.model_dump(), user["id_usuario"])
    return SuccessResponse(message="Observación creada correctamente", data=result)


@router.put("/observacion/{id}", tags=[TAGS_OBSERVACIONES],
            dependencies=[Depends(require_rol(*ROLES_SINB_OBSERVACION))])
def actualizar_observacion(id: UUID, data: ObservacionUpdate, db: Session = Depends(get_db)):
    """Actualizar observación existente."""
    result = service.update_observacion(db, id, data.model_dump(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="Observación no encontrada")
    return SuccessResponse(message="Observación actualizada correctamente", data=result)


@router.delete("/observacion/{id}", tags=[TAGS_OBSERVACIONES],
               dependencies=[Depends(require_rol(*ROLES_SINB_ADMIN))])
def eliminar_observacion(id: UUID, db: Session = Depends(get_db)):
    """Eliminar lógico de observación."""
    service.delete_observacion(db, id)
    return {"message": "Observación eliminada correctamente"}


# ============================================================================
# PRONÓSTICOS ESTACIONALES Y TEMPORALES
# ============================================================================

@router.get("/pronostico-estacional", tags=[TAGS_PREDICCIONES_LARGO],
            summary="Listar pronósticos estacionales (últimos 15)")
def listar_pronosticos_estacionales(
    skip: int = Query(0, ge=0),
    limit: int = Query(15, ge=1, le=100),
    id_campo_pronostico: UUID | None = Query(None, description="Filtrar por campo"),
    fecha_emision_desde: date | None = Query(None, description="Fecha emisión desde"),
    fecha_emision_hasta: date | None = Query(None, description="Fecha emisión hasta"),
    estado: str | None = Query(None, description="Filtrar por estado"),
    id_usuario_elabora: int | None = Query(None, description="Filtrar por elaborador"),
    db: Session = Depends(get_db)
):
    """Listar pronósticos estacionales con paginación y filtros."""
    data, total = service.get_pronosticos_estacionales(
        db, skip=skip, limit=limit,
        id_campo=id_campo_pronostico,
        fecha_emision_desde=fecha_emision_desde,
        fecha_emision_hasta=fecha_emision_hasta,
        estado=estado,
        id_usuario_elabora=id_usuario_elabora
    )
    return SuccessResponse(message="Pronósticos estacionales listados", data=data, total=total)


@router.get("/pronostico-estacional/{id}", tags=[TAGS_PREDICCIONES_LARGO],
            summary="Obtener pronóstico estacional completo")
def obtener_pronostico_estacional(id: UUID, db: Session = Depends(get_db)):
    """Obtener pronóstico estacional con escenarios y observadores asignados."""
    result = service.get_pronostico_estacional(db, id)
    if not result:
        raise HTTPException(status_code=404, detail="Pronóstico no encontrado")
    return SuccessResponse(message="Pronóstico obtenido correctamente", data=result)


@router.post("/pronostico-estacional", tags=[TAGS_PREDICCIONES_LARGO], status_code=201,
             dependencies=[Depends(require_rol(*ROLES_SINB_PRONOSTICO))],
             summary="Crear pronóstico estacional con escenarios y observadores")
def crear_pronostico_estacional(data: PronosticoEstacionalCreate, db: Session = Depends(get_db),
                                 user=Depends(get_current_user)):
    """
    Crear pronóstico estacional.
    
    - **escenarios**: lista opcional de escenarios con probabilidad
    - **observadores**: lista opcional de observadores asignados
    - **id_usuario_elabora**: si no se envía, usa el usuario actual
    """
    result = service.create_pronostico_estacional(db, data.model_dump(), user["id_usuario"])
    return SuccessResponse(message="Pronóstico creado correctamente", data=result)


@router.put("/pronostico-estacional/{id}", tags=[TAGS_PREDICCIONES_LARGO],
            dependencies=[Depends(require_rol(*ROLES_SINB_PRONOSTICO))])
def actualizar_pronostico_estacional(id: UUID, data: PronosticoEstacionalUpdate,
                                      db: Session = Depends(get_db)):
    """Actualizar pronóstico estacional."""
    result = service.update_pronostico_estacional(db, id, data.model_dump(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="Pronóstico no encontrado")
    return SuccessResponse(message="Pronóstico actualizado correctamente", data=result)


@router.delete("/pronostico-estacional/{id}", tags=[TAGS_PREDICCIONES_LARGO],
               dependencies=[Depends(require_rol(*ROLES_SINB_PRONOSTICO))])
def eliminar_pronostico_estacional(id: UUID, db: Session = Depends(get_db)):
    """Eliminar pronóstico estacional."""
    service.delete_pronostico_estacional(db, id)
    return {"message": "Pronóstico eliminado correctamente"}


@router.post("/pronostico-estacional/{id}/escenario", tags=[TAGS_PREDICCIONES_LARGO],
             dependencies=[Depends(require_rol(*ROLES_SINB_PRONOSTICO))],
             summary="Agregar escenario a pronóstico")
def agregar_escenario(id: UUID, id_escenario: UUID = Query(...),
                      probabilidad: float = Query(..., ge=0, le=100),
                      db: Session = Depends(get_db)):
    """Agregar o actualizar escenario de pronóstico estacional."""
    result = service.add_escenario_a_pronostico(db, id, id_escenario, probabilidad)
    return SuccessResponse(message="Escenario agregado correctamente", data=result)


@router.delete("/pronostico-estacional/{id}/escenario/{id_escenario}",
               tags=[TAGS_PREDICCIONES_LARGO],
               dependencies=[Depends(require_rol(*ROLES_SINB_PRONOSTICO))])
def remover_escenario(id: UUID, id_escenario: UUID, db: Session = Depends(get_db)):
    """Remover escenario de pronóstico estacional."""
    service.remove_escenario_de_pronostico(db, id, id_escenario)
    return {"message": "Escenario removido correctamente"}


# --- Pronósticos Temporales (Corto Plazo) ---

@router.get("/pronostico-temporal", tags=[TAGS_PREDICCIONES_CORTO],
            summary="Listar pronósticos temporales (últimos 15)")
def listar_pronosticos_temporales(
    skip: int = Query(0, ge=0),
    limit: int = Query(15, ge=1, le=100),
    id_categoria: UUID | None = Query(None, description="Filtrar por categoría"),
    id_campo_pronostico: UUID | None = Query(None, description="Filtrar por campo"),
    fecha_emision_desde: date | None = Query(None, description="Fecha emisión desde"),
    confianza: str | None = Query(None, description="Filtrar por confianza"),
    estado: str | None = Query(None, description="Filtrar por estado"),
    db: Session = Depends(get_db)
):
    """Listar pronósticos temporales con paginación."""
    data, total = service.get_pronosticos_temporales(
        db, skip=skip, limit=limit,
        id_categoria=id_categoria,
        id_campo=id_campo_pronostico,
        fecha_emision_desde=fecha_emision_desde,
        confianza=confianza,
        estado=estado
    )
    return SuccessResponse(message="Pronósticos temporales listados", data=data, total=total)


@router.post("/pronostico-temporal", tags=[TAGS_PREDICCIONES_CORTO], status_code=201,
             dependencies=[Depends(require_rol(*ROLES_SINB_PRONOSTICO))])
def crear_pronostico_temporal(data: PronosticoTemporalCreate, db: Session = Depends(get_db)):
    """Crear pronóstico temporal."""
    result = service.create_pronostico_temporal(db, data.model_dump())
    return SuccessResponse(message="Pronóstico temporal creado correctamente", data=result)


@router.put("/pronostico-temporal/{id}", tags=[TAGS_PREDICCIONES_CORTO],
            dependencies=[Depends(require_rol(*ROLES_SINB_PRONOSTICO))])
def actualizar_pronostico_temporal(id: UUID, data: PronosticoTemporalUpdate,
                                    db: Session = Depends(get_db)):
    """Actualizar pronóstico temporal."""
    result = service.update_pronostico_temporal(db, id, data.model_dump(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="Pronóstico no encontrado")
    return SuccessResponse(message="Pronóstico actualizado correctamente", data=result)


@router.delete("/pronostico-temporal/{id}", tags=[TAGS_PREDICCIONES_CORTO],
               dependencies=[Depends(require_rol(*ROLES_SINB_PRONOSTICO))])
def eliminar_pronostico_temporal(id: UUID, db: Session = Depends(get_db)):
    """Eliminar pronóstico temporal."""
    service.delete_pronostico_temporal(db, id)
    return {"message": "Pronóstico eliminado correctamente"}


# ============================================================================
# ASIGNACIÓN DE OBSERVADORES A PRONÓSTICOS
# ============================================================================

@router.post("/pronostico/{id}/observadores", tags=[TAGS_OBSERVADORES],
             dependencies=[Depends(require_rol(6, 7, 8, 12, 13))],  # Roles locales
             summary="Asignar observadores a pronóstico (recolector → observadores)")
def asignar_observadores(
    id: UUID,
    data: PronosticoObservadorCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """
    Asignar 1..N observadores a un pronóstico.
    
    **Requiere que todos los observadores sean del mismo municipio.**
    El recolector menciona y destaca los nombres de los observadores locales.
    """
    result = service.asignar_observadores_a_pronostico(
        db, id, data.tipo_pronostico, data.id_observadores, data.confianza,
        user["id_usuario"]
    )
    return SuccessResponse(message="Observadores asignados correctamente", data=result)


@router.delete("/pronostico/{id}/observador/{id_usuario}", tags=[TAGS_OBSERVADORES],
               dependencies=[Depends(require_rol(6, 7, 8, 12, 13))])
def remover_observador(
    id: UUID,
    id_usuario: int,
    tipo_pronostico: Literal["estacional", "temporal"] = Query(...),
    db: Session = Depends(get_db)
):
    """Remover asignación de observador de un pronóstico."""
    service.remover_observador_de_pronostico(db, id, tipo_pronostico, id_usuario)
    return {"message": "Observador removido correctamente"}


# ============================================================================
# VALIDACIÓN DE PRONÓSTICOS (Automática y Manual)
# ============================================================================

@router.post("/verificacion/calcular", tags=[TAGS_VALIDACION],
             dependencies=[Depends(require_rol(*ROLES_SINB_ADMIN))],
             summary="Calcular verificación AUTOMÁTICA de pronósticos vencidos")
def calcular_verificacion_automatica(
    data: CalculoVerificacionRequest,
    db: Session = Depends(get_db)
):
    """
    **Validación Automática:** Ejecuta tarea de verificación de pronósticos vencidos.
    
    **Reglas automáticas:**
    1. Pronóstico vencido (fecha_fin < NOW()) → marca PENDIENTE_VERIFICACION
    2. Si hay observaciones en ventana → EN_VERIFICACION (requiere manual)
    3. Si coincide evento → COINCIDE
    4. Sin datos → SIN_DATOS
    
    Retorna lista de verificaciones calculadas.
    """
    resultados = service.calcular_verificacion_automatica(db, data.id_pronostico, data.tipo)
    return SuccessResponse(message="Verificación automática calculada", data=resultados)


@router.get("/verificacion/pendientes", tags=[TAGS_VALIDACION],
            summary="Listar pronósticos pendientes de verificación")
def listar_verificaciones_pendientes(db: Session = Depends(get_db)):
    """Obtener lista de pronósticos vencidos pendientes de verificación."""
    data = service.get_verificaciones_pendientes(db)
    return SuccessResponse(message="Verificaciones pendientes listadas", data=data)


@router.put("/verificacion/{id_pronostico}", tags=[TAGS_VALIDACION],
            dependencies=[Depends(require_rol(*ROLES_SINB_VALIDACION))],
            summary="Validación MANUAL de pronóstico (experto)")
def validar_pronostico_manual(
    id_pronostico: UUID,
    tipo: Literal["estacional", "temporal"] = Query(...),
    estado: Literal["COINCIDE", "NO_COINCIDE"] = Query(...),
    observacion: str = Query(..., description="Observación cualitativa del validador"),
    calificacion: float | None = Query(None, ge=0, le=100, description="Calificación 0-100"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """
    **Validación Manual:** Usuario experto valida manualmente el pronóstico.
    
    **Requerimientos:**
    - Rol: admin (2) o VIDECI Departamental (9)
    - Estado: COINCIDE o NO_COINCIDE
    - Observación: texto explicativo obligatorio
    
    Sobrescribe validación automática si existe.
    """
    result = service.validar_pronostico_manual(
        db, id_pronostico, tipo, estado, observacion, calificacion,
        user["id_usuario"]
    )
    return SuccessResponse(message="Validación manual registrada", data=result)


# ============================================================================
# RECOMENDACIONES LOCALES
# ============================================================================

@router.get("/recomendacion-local", tags=[TAGS_RECOMENDACIONES],
            summary="Listar recomendaciones locales (últimos 15)")
def listar_recomendaciones(
    skip: int = Query(0, ge=0),
    limit: int = Query(15, ge=1, le=100),
    id_dimension: UUID | None = Query(None, description="Filtrar por dimensión"),
    id_categoria: UUID | None = Query(None, description="Filtrar por categoría"),
    id_municipio: int | None = Query(None, description="Filtrar por municipio"),
    db: Session = Depends(get_db)
):
    """Listar recomendaciones locales con paginación."""
    from sqlalchemy import text
    params = {"limit": limit, "skip": skip}
    where = ["rl.estado = 'ACTIVO'"]
    
    if id_dimension:
        where.append("rl.id_dimension = :id_dimension")
        params["id_dimension"] = id_dimension
    if id_categoria:
        where.append("rl.id_categoria = :id_categoria")
        params["id_categoria"] = id_categoria
    if id_municipio:
        where.append("rl.id_municipio = :id_municipio")
        params["id_municipio"] = id_municipio
    
    where_clause = " AND ".join(where)
    
    data = service._rows(db, f"""
        SELECT rl.*, d.nombre as dimension_nombre, c.nombre as categoria_nombre,
               m.nombre as municipio_nombre
        FROM sinb.recomendacion_local rl
        JOIN sinb.dimension_recomendacion d ON d.id = rl.id_dimension
        JOIN sinb.categoria_comportamiento c ON c.id = rl.id_categoria
        LEFT JOIN shared.municipio m ON m.id = rl.id_municipio
        WHERE {where_clause}
        ORDER BY rl.creado_en DESC
        LIMIT :limit OFFSET :skip
    """, params)
    
    return SuccessResponse(message="Recomendaciones listadas", data=data)


@router.post("/recomendacion-local", tags=[TAGS_RECOMENDACIONES], status_code=201,
             dependencies=[Depends(require_rol(*ROLES_SINB_LOCAL))])
def crear_recomendacion(data: RecomendacionLocalCreate, db: Session = Depends(get_db),
                        user=Depends(get_current_user)):
    """Crear recomendación local."""
    payload = data.model_dump()
    if not payload.get("id_usuario_elabora"):
        payload["id_usuario_elabora"] = user["id_usuario"]
    
    result = service._row(db, """
        INSERT INTO sinb.recomendacion_local 
        (texto, id_dimension, id_categoria, codigo_comunidad, id_municipio, 
         id_usuario_elabora, estado)
        VALUES (:texto, :id_dimension, :id_categoria, :codigo_comunidad, :id_municipio,
                :id_usuario_elabora, 'ACTIVO')
        RETURNING *
    """, payload)
    db.commit()
    return SuccessResponse(message="Recomendación creada correctamente", data=result)


@router.delete("/recomendacion-local/{id}", tags=[TAGS_RECOMENDACIONES],
               dependencies=[Depends(require_rol(*ROLES_SINB_LOCAL))])
def eliminar_recomendacion(id: UUID, db: Session = Depends(get_db)):
    """Eliminar recomendación local."""
    service._execute(db, """
        UPDATE sinb.recomendacion_local SET estado = 'ELIMINADO' WHERE id = :id
    """, {"id": id})
    db.commit()
    return {"message": "Recomendación eliminada correctamente"}


# ============================================================================
# AVISOS DE CORTO PLAZO
# ============================================================================

@router.get("/aviso", tags=[TAGS_PREDICCIONES_AVISOS],
            summary="Listar avisos de corto plazo (últimos 15)")
def listar_avisos(
    skip: int = Query(0, ge=0),
    limit: int = Query(15, ge=1, le=100),
    id_municipio: int | None = Query(None, description="Filtrar por municipio"),
    codigo_comunidad: str | None = Query(None, description="Filtrar por comunidad"),
    vigente: bool | None = Query(None, description="Solo vigentes"),
    db: Session = Depends(get_db)
):
    """Listar avisos de corto plazo con paginación y filtros."""
    params = {"limit": limit, "skip": skip}
    where = ["a.estado = 'ACTIVO'"]
    
    if id_municipio:
        where.append("a.id_municipio = :id_municipio")
        params["id_municipio"] = id_municipio
    if codigo_comunidad:
        where.append("a.codigo_comunidad = :codigo_comunidad")
        params["codigo_comunidad"] = codigo_comunidad
    if vigente is True:
        where.append("a.fecha_vencimiento > NOW()")
    
    where_clause = " AND ".join(where)
    
    data = service._rows(db, f"""
        SELECT a.*, cp.nombre as campo_nombre, m.nombre as municipio_nombre,
               u.nombre as emisor_nombre
        FROM sinb.aviso a
        LEFT JOIN sinb.campo_pronostico cp ON cp.id = a.id_campo_pronostico
        LEFT JOIN shared.municipio m ON m.id = a.id_municipio
        LEFT JOIN usuarios.usuario u ON u.id_usuario = a.id_usuario_emite
        WHERE {where_clause}
        ORDER BY a.fecha_emision DESC
        LIMIT :limit OFFSET :skip
    """, params)
    
    return SuccessResponse(message="Avisos listados", data=data)


@router.post("/aviso", tags=[TAGS_PREDICCIONES_AVISOS], status_code=201,
             dependencies=[Depends(require_rol(*ROLES_SINB_LOCAL))])
def crear_aviso(data: AvisoCreate, db: Session = Depends(get_db),
                user=Depends(get_current_user)):
    """
    Crear aviso de corto plazo.
    
    **Flujo:** El productor dicta el aviso («va a granizar») → se asigna a comunidad →
    vence en 24-48h → se verifica si cumplió.
    """
    payload = data.model_dump()
    payload["codigo"] = f"AV-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    payload["id_usuario_emite"] = user["id_usuario"]
    payload["fecha_vencimiento"] = f"NOW() + INTERVAL '{data.vigencia_horas} HOURS'"
    
    result = service._row(db, """
        INSERT INTO sinb.aviso 
        (codigo, id_campo_pronostico, codigo_comunidad, id_municipio, mensaje,
         fecha_emision, vigencia_horas, fecha_vencimiento, id_usuario_emite, estado)
        VALUES (:codigo, :id_campo_pronostico, :codigo_comunidad, :id_municipio, :mensaje,
                NOW(), :vigencia_horas, NOW() + INTERVAL ':vigencia_horas HOURS',
                :id_usuario_emite, 'ACTIVO')
        RETURNING *
    """, payload)
    db.commit()
    return SuccessResponse(message="Aviso creado correctamente", data=result)


@router.delete("/aviso/{id}", tags=[TAGS_PREDICCIONES_AVISOS],
               dependencies=[Depends(require_rol(*ROLES_SINB_LOCAL))])
def eliminar_aviso(id: UUID, db: Session = Depends(get_db)):
    """Eliminar aviso."""
    service._execute(db, """
        UPDATE sinb.aviso SET estado = 'ELIMINADO' WHERE id = :id
    """, {"id": id})
    db.commit()
    return {"message": "Aviso eliminado correctamente"}


# ============================================================================
# OBSERVADOR ÍNDICE (aciertos por usuario)
# ============================================================================

@router.get("/observador-indice", tags=[TAGS_OBSERVADORES],
            summary="Listar índices de observadores (aciertos)")
def listar_observadores_indice(
    skip: int = Query(0, ge=0),
    limit: int = Query(15, ge=1, le=100),
    id_usuario: int | None = Query(None, description="Filtrar por usuario"),
    tipo: str | None = Query(None, description="CORTO o LARGO"),
    db: Session = Depends(get_db)
):
    """
    Listar observador_indice: mide aciertos de cada observador.
    
    - **tipo CORTO**: viene de avisos (§6A)
    - **tipo LARGO**: viene de pronósticos estacionales (§6.4)
    """
    params = {"limit": limit, "skip": skip}
    where = ["estado = 'ACTIVO'"]
    
    if id_usuario:
        where.append("oi.id_usuario = :id_usuario")
        params["id_usuario"] = id_usuario
    if tipo:
        where.append("oi.tipo = :tipo::sinb.tipo_pronostico")
        params["tipo"] = tipo
    
    where_clause = " AND ".join(where)
    
    data = service._rows(db, f"""
        SELECT oi.*, u.nombre as usuario_nombre, i.nombre_cientifico as indicador_nombre
        FROM sinb.observador_indice oi
        JOIN usuarios.usuario u ON u.id_usuario = oi.id_usuario
        LEFT JOIN sinb.indicador_natural i ON i.id = oi.id_indicador_natural
        WHERE {where_clause}
        ORDER BY oi.fecha_calculo DESC
        LIMIT :limit OFFSET :skip
    """, params)
    
    return SuccessResponse(message="Índices listados", data=data)


@router.post("/observador-indice", tags=[TAGS_OBSERVADORES], status_code=201,
             dependencies=[Depends(require_rol(*ROLES_SINB_LOCAL))])
def crear_observador_indice(data: ObservadorIndiceCreate, db: Session = Depends(get_db)):
    """Crear registro de observador índice."""
    result = service._row(db, """
        INSERT INTO sinb.observador_indice 
        (id_usuario, id_indicador_natural, tipo, valor, fecha_calculo)
        VALUES (:id_usuario, :id_indicador_natural, :tipo::sinb.tipo_pronostico,
                :valor, :fecha_calculo)
        ON CONFLICT (id_usuario, id_indicador_natural, tipo)
        DO UPDATE SET valor = :valor, fecha_calculo = :fecha_calculo
        RETURNING *
    """, data.model_dump())
    db.commit()
    return SuccessResponse(message="Índice creado correctamente", data=result)


# ============================================================================
# REPORTES ENRIQUECIDOS
# ============================================================================

@router.get("/reporte/observaciones", tags=[TAGS_REPORTES],
            summary="Reporte enriquecido de observaciones")
def reporte_observaciones(
    id_municipio: int | None = Query(None, description="Filtrar por municipio"),
    db: Session = Depends(get_db)
):
    """
    Reporte enriquecido de observaciones:
    - Totales
    - Por comunidad (top 20)
    - Por indicador (top 20)
    - Por estado de validación
    """
    filters = {"id_municipio": id_municipio} if id_municipio else {}
    data = service.get_reporte_observaciones_resumen(db, filters)
    return SuccessResponse(message="Reporte generado", data=data)


@router.get("/reporte/pronosticos", tags=[TAGS_REPORTES],
            summary="Reporte de pronósticos con verificación")
def reporte_pronosticos(db: Session = Depends(get_db)):
    """
    Reporte de pronósticos con estado de verificación:
    - Totales por tipo
    - Por estado
    - Verificaciones: coinciden, no coinciden, pendientes
    """
    data = service.get_reporte_pronosticos_resumen(db)
    return SuccessResponse(message="Reporte generado", data=data)


@router.get("/reporte/calendario-siembra", tags=[TAGS_REPORTES],
            summary="Calendario de siembra por municipio")
def reporte_calendario_siembra(
    id_municipio: int | None = Query(None, description="Filtrar por municipio"),
    fecha_desde: date | None = Query(None, description="Fecha desde"),
    fecha_hasta: date | None = Query(None, description="Fecha hasta"),
    db: Session = Depends(get_db)
):
    """
    Obtener calendario de siembra consolidado por municipio.
    Muestra épocas de siembra recomendadas por cultivo.
    """
    data = service.get_calendario_siembra(db, id_municipio, fecha_desde, fecha_hasta)
    return SuccessResponse(message="Calendario obtenido", data=data)


# ============================================================================
# MAPAS GEOJSON
# ============================================================================

@router.get("/mapa/observaciones/geojson", tags=[TAGS_MAPAS],
            summary="GeoJSON de observaciones por filtros geográficos")
def mapa_observaciones_geojson(
    id_departamento: int | None = Query(None, description="Filtrar por departamento"),
    id_provincia: int | None = Query(None, description="Filtrar por provincia"),
    id_municipio: int | None = Query(None, description="Filtrar por municipio"),
    codigo_comunidad: str | None = Query(None, description="Filtrar por comunidad"),
    fecha_inicio: date | None = Query(None, description="Fecha inicio"),
    fecha_fin: date | None = Query(None, description="Fecha fin"),
    db: Session = Depends(get_db)
):
    """
    **Mapa de observaciones en GeoJSON** para Leaflet/Mapbox.
    
    **Filtros geográficos:** departamento, provincia, municipio, comunidad
    **Propiedades:** comunidad, municipio, provincia, departamento, total_observaciones, indicadores
    
    Retorna FeatureCollection RFC 7946, EPSG:4326.
    """
    params = {}
    where = ["o.estado = 'ACTIVO'"]
    
    if id_departamento:
        where.append("d.id = :id_departamento")
        params["id_departamento"] = id_departamento
    if id_provincia:
        where.append("p.id = :id_provincia")
        params["id_provincia"] = id_provincia
    if id_municipio:
        where.append("m.id = :id_municipio")
        params["id_municipio"] = id_municipio
    if codigo_comunidad:
        where.append("o.codigo_comunidad = :codigo_comunidad")
        params["codigo_comunidad"] = codigo_comunidad
    if fecha_inicio:
        where.append("o.fecha_inicio >= :fecha_inicio")
        params["fecha_inicio"] = fecha_inicio
    if fecha_fin:
        where.append("o.fecha_inicio <= :fecha_fin")
        params["fecha_fin"] = fecha_fin
    
    where_clause = " AND ".join(where)
    
    features = service._rows(db, f"""
        SELECT 
            jsonb_build_object(
                'type', 'Feature',
                'id', o.codigo_comunidad,
                'geometry', ST_AsGeoJSON(c.geom)::jsonb,
                'properties', jsonb_build_object(
                    'codigo_comunidad', o.codigo_comunidad,
                    'comunidad', c.nombre,
                    'municipio', m.nombre,
                    'provincia', p.nombre,
                    'departamento', d.nombre,
                    'total_observaciones', COUNT(o.id),
                    'ultimo_registro', MAX(o.fecha_inicio)
                )
            ) as feature
        FROM sinb.observacion o
        JOIN shared.comunidades c ON c.codigo_ine = o.codigo_comunidad
        JOIN shared.municipio m ON m.id = c.id_municipio
        JOIN shared.provincia p ON p.id = m.id_provincia
        JOIN shared.departamento d ON d.id = p.id_departamento
        WHERE {where_clause}
        GROUP BY o.codigo_comunidad, c.geom, c.nombre, m.nombre, p.nombre, d.nombre
    """, params)
    
    return {
        "type": "FeatureCollection",
        "features": [f["feature"] for f in features]
    }


@router.get("/mapa/comunidades/geojson", tags=[TAGS_MAPAS],
            summary="GeoJSON de comunidades por municipio/departamento")
def mapa_comunidades_geojson(
    id_departamento: int | None = Query(None, description="Filtrar por departamento"),
    id_municipio: int | None = Query(None, description="Filtrar por municipio"),
    db: Session = Depends(get_db)
):
    """
    **GeoJSON de comunidades** (puntos) para mapa.
    
    **Propiedades:** nombre, codigo_ine, municipio, provincia, departamento
    """
    params = {}
    where = ["TRUE"]
    
    if id_departamento:
        where.append("d.id = :id_departamento")
        params["id_departamento"] = id_departamento
    if id_municipio:
        where.append("m.id = :id_municipio")
        params["id_municipio"] = id_municipio
    
    where_clause = " AND ".join(where)
    
    features = service._rows(db, f"""
        SELECT 
            jsonb_build_object(
                'type', 'Feature',
                'id', c.codigo_ine,
                'geometry', ST_AsGeoJSON(c.geom)::jsonb,
                'properties', jsonb_build_object(
                    'codigo_ine', c.codigo_ine,
                    'nombre', c.nombre,
                    'municipio', m.nombre,
                    'provincia', p.nombre,
                    'departamento', d.nombre
                )
            ) as feature
        FROM shared.comunidades c
        JOIN shared.municipio m ON m.id = c.id_municipio
        JOIN shared.provincia p ON p.id = m.id_provincia
        JOIN shared.departamento d ON d.id = p.id_departamento
        WHERE {where_clause}
    """, params)
    
    return {
        "type": "FeatureCollection",
        "features": [f["feature"] for f in features]
    }


@router.get("/mapa/municipios/geojson", tags=[TAGS_MAPAS],
            summary="GeoJSON de municipios por departamento")
def mapa_municipios_geojson(
    id_departamento: int | None = Query(None, description="Filtrar por departamento"),
    db: Session = Depends(get_db)
):
    """
    **GeoJSON de municipios** (polígonos) para mapa.
    
    **Propiedades:** nombre, codigo_ine, provincia, departamento
    """
    params = {}
    where = ["TRUE"]
    
    if id_departamento:
        where.append("d.id = :id_departamento")
        params["id_departamento"] = id_departamento
    
    where_clause = " AND ".join(where)
    
    features = service._rows(db, f"""
        SELECT 
            jsonb_build_object(
                'type', 'Feature',
                'id', m.id,
                'geometry', ST_AsGeoJSON(m.geom)::jsonb,
                'properties', jsonb_build_object(
                    'id', m.id,
                    'codigo_ine', m.codigo_ine,
                    'nombre', m.nombre,
                    'provincia', p.nombre,
                    'departamento', d.nombre
                )
            ) as feature
        FROM shared.municipio m
        JOIN shared.provincia p ON p.id = m.id_provincia
        JOIN shared.departamento d ON d.id = p.id_departamento
        WHERE {where_clause}
    """, params)
    
    return {
        "type": "FeatureCollection",
        "features": [f["feature"] for f in features]
    }


@router.get("/mapa/manzanos/geojson", tags=[TAGS_MAPAS],
            summary="GeoJSON de manzanos censales")
def mapa_manzanos_geojson(
    id_municipio: int | None = Query(None, description="Filtrar por municipio"),
    db: Session = Depends(get_db)
):
    """
    **GeoJSON de manzanos censales** (polígonos) del Censo 2024.
    
    **Propiedades:** codigo_ine, municipio, departamento
    """
    params = {}
    where = ["TRUE"]
    
    if id_municipio:
        where.append("id_municipio = :id_municipio")
        params["id_municipio"] = id_municipio
    
    where_clause = " AND ".join(where)
    
    features = service._rows(db, f"""
        SELECT 
            jsonb_build_object(
                'type', 'Feature',
                'id', m.codigo_ine,
                'geometry', ST_AsGeoJSON(m.geom)::jsonb,
                'properties', jsonb_build_object(
                    'codigo_ine', m.codigo_ine,
                    'nombre', m.nombre,
                    'id_municipio', m.id_municipio
                )
            ) as feature
        FROM shared.manzanos m
        WHERE {where_clause}
    """, params)
    
    return {
        "type": "FeatureCollection",
        "features": [f["feature"] for f in features]
    }


@router.get("/mapa/pronosticos/geojson", tags=[TAGS_MAPAS],
            summary="GeoJSON de pronósticos estacionales por municipio")
def mapa_pronosticos_geojson(
    id_departamento: int | None = Query(None, description="Filtrar por departamento"),
    db: Session = Depends(get_db)
):
    """
    **Mapa de pronósticos estacionales** agregados por municipio.
    
    **Propiedades:** municipio, total_pronosticos, ultima_emision, campos
    """
    params = {}
    where = ["pe.estado IN ('EMITIDO', 'ACEPTADO')"]
    
    if id_departamento:
        where.append("d.id = :id_departamento")
        params["id_departamento"] = id_departamento
    
    where_clause = " AND ".join(where)
    
    features = service._rows(db, f"""
        SELECT 
            jsonb_build_object(
                'type', 'Feature',
                'id', m.id,
                'geometry', ST_AsGeoJSON(m.geom)::jsonb,
                'properties', jsonb_build_object(
                    'municipio', m.nombre,
                    'total_pronosticos', COUNT(pe.id),
                    'ultima_emision', MAX(pe.fecha_emision),
                    'campos', ARRAY_AGG(DISTINCT cp.nombre)
                )
            ) as feature
        FROM sinb.pronostico_estacional pe
        JOIN shared.municipio m ON m.id = pe.id_municipio
        JOIN shared.provincia p ON p.id = m.id_provincia
        JOIN shared.departamento d ON d.id = p.id_departamento
        JOIN sinb.campo_pronostico cp ON cp.id = pe.id_campo_pronostico
        WHERE {where_clause}
        GROUP BY m.id, m.nombre, m.geom
    """, params)
    
    return {
        "type": "FeatureCollection",
        "features": [f["feature"] for f in features]
    }


# ============================================================================
# PRONÓSTICOS DIGITALES (Open-Meteo Integration)
# ============================================================================

@router.get("/pronostico-digital/diario", 
            tags=[TAGS_PREDICCIONES_DIGITALES],
            summary="Obtener pronósticos diarios con filtros geográficos")
def get_pronosticos_diarios(
    id_departamento: int = Query(None, description="Filtrar por departamento (ej: 2=La Paz)"),
    id_provincia: int = Query(None, description="Filtrar por provincia (ej: 24=Murillo)"),
    id_municipio: int = Query(None, description="Filtrar por municipio (ej: 2401=La Paz)"),
    fecha_desde: date = Query(None, description="Fecha desde (default: hoy)"),
    fecha_hasta: date = Query(None, description="Fecha hasta"),
    skip: int = Query(0, ge=0, description="Saltar registros para paginación"),
    limit: int = Query(100, ge=1, le=500, description="Límite de registros (default: 100, max: 500)"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """
    Obtener pronósticos diarios con filtros geográficos completos.
    
    **Horario de referencia:**
    - Los datos son del día COMPLETO (0:00 a 23:59 hora local America/La_Paz, UTC-4)
    - `temp_max`: máxima del día (ocurre típicamente entre 12:00-15:00)
    - `temp_min`: mínima del día (ocurre típicamente entre 03:00-06:00)
    - `sunrise`: salida del sol (~06:00-06:30, inicio del día solar)
    - `sunset`: puesta del sol (~18:00-19:00, fin del día solar)
    
    **Filtros geográficos:**
    - `id_departamento`: Filtrar por departamento
    - `id_provincia`: Filtrar por provincia  
    - `id_municipio`: Filtrar por municipio específico
    
    **Notas:**
    - Los datos se actualizan automáticamente 2 veces al día (06:00 y 18:00)
    - Horizonte: 7 días
    - Filtros se aplican según el rol del usuario (scope geográfico)
    - Paginación: skip/limit (default 100 registros)
    """
    # Aplicar scope geográfico según rol del usuario
    from .utils import scope_geografico
    scope = scope_geografico(user, id_departamento, id_provincia, id_municipio)
    
    # Si el usuario tiene restricciones geográficas, aplicarlas
    if scope.get("id_departamento") and not id_departamento:
        id_departamento = scope["id_departamento"]
    if scope.get("id_municipio") and not id_municipio:
        id_municipio = scope["id_municipio"]
    
    data, total = service.get_pronosticos_diarios_filtrados(
        db, 
        id_departamento=id_departamento,
        id_provincia=id_provincia,
        id_municipio=id_municipio,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        skip=skip,
        limit=limit
    )
    
    return SuccessResponse(
        message=f"Pronósticos obtenidos ({len(data)} de {total})",
        data=data,
        total=total
    )


@router.get("/pronostico-digital/diario/{id_municipio}", 
            tags=[TAGS_PREDICCIONES_DIGITALES],
            summary="Obtener pronóstico diario por municipio específico")
def get_pronostico_diario_municipio(
    id_municipio: int = Path(..., description="ID del municipio"),
    fecha_desde: date = Query(None, description="Fecha desde"),
    fecha_hasta: date = Query(None, description="Fecha hasta"),
    db: Session = Depends(get_db)
):
    """
    Obtener pronóstico diario almacenado para un municipio específico.
    
    Datos actualizados automáticamente 2 veces al día (06:00 y 18:00).
    Horizonte: 7 días.
    """
    data = service.get_pronostico_diario_municipal(db, id_municipio, fecha_desde, fecha_hasta)
    return SuccessResponse(message="Pronóstico diario obtenido", data=data)


@router.get("/pronostico-digital/consultar",
            tags=[TAGS_PREDICCIONES_DIGITALES],
            summary="Consultar pronóstico digital en tiempo real (Open-Meteo)")
def consultar_pronostico(
    latitud: float = Query(..., ge=-90, le=90, description="Latitud"),
    longitud: float = Query(..., ge=-180, le=180, description="Longitud"),
    tipo: Literal["daily", "hourly", "minutely_15"] = Query("daily", description="Tipo de pronóstico"),
    variables: str = Query(None, description="Variables (separadas por coma)"),
    horizonte_dias: int = Query(7, ge=1, le=16, description="Días de horizonte (1-16)"),
    guardar_cache: bool = Query(False, description="¿Guardar en caché? (24h hourly, 1h minutely)"),
    db: Session = Depends(get_db)
):
    """
    Consultar directamente a Open-Meteo (sin autenticación requerida).
    
    **Tipos de pronóstico:**
    
    1. **daily** (7-16 días, 1 valor/día):
       - Datos del día COMPLETO (0:00-23:59 hora local)
       - Variables: temp_max (~12:00-15:00), temp_min (~03:00-06:00), precipitación
       - sunrise/sunset incluidos
    
    2. **hourly** (24-168 horas, 1 valor/hora):
       - Datos hora por hora
       - Variables: temperatura, humedad, prob. precipitación, viento
       - Ideal para eventos específicos
    
    3. **minutely_15** (48 horas, 1 valor/15min):
       - Nowcast de muy corto plazo
       - Variables: precipitación, temperatura
       - Ideal para alertas inmediatas
    
    **Horarios de referencia:**
    - Open-Meteo usa hora local (America/La_Paz, UTC-4)
    - daily: día completo 0:00-23:59
    - hourly: cada hora desde el momento actual
    - minutely_15: cada 15 minutos desde el momento actual
    
    **Opcional:** Guardar en caché (24h para hourly, 1h para minutely)
    """
    vars_list = variables.split(",") if variables else None
    
    # Consultar Open-Meteo
    datos = service.consultar_open_meteo(latitud, longitud, tipo, vars_list, horizonte_dias)
    
    # Guardar en caché si se solicita
    if guardar_cache and tipo == "hourly":
        # Obtener municipio por coordenadas (aproximado)
        municipio_result = _row(db, """
            SELECT id FROM shared.municipio 
            WHERE ST_Contains(geom, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326))
        """, {"lon": longitud, "lat": latitud})
        
        id_municipio = municipio_result["id"] if municipio_result else None
        service.guardar_pronostico_hourly_cache(db, latitud, longitud, datos, id_municipio)
    
    return SuccessResponse(message="Pronóstico consultado", data=datos)


@router.get("/pronostico-digital/hourly/{lat}/{lon}",
            tags=[TAGS_PREDICCIONES_DIGITALES],
            summary="Obtener pronóstico hourly almacenado (caché 24h)")
def get_pronostico_hourly(
    lat: float = Path(..., description="Latitud"),
    lon: float = Path(..., description="Longitud"),
    horas: int = Query(48, ge=1, le=168, description="Horas a obtener"),
    db: Session = Depends(get_db)
):
    """
    Obtener pronóstico hourly desde caché (24 horas).
    
    Si no hay datos en caché, consultar primero el endpoint /consultar con guardar_cache=true.
    """
    from datetime import datetime, timedelta
    fecha_desde = datetime.now()
    fecha_hasta = fecha_desde + timedelta(hours=horas)
    
    data = service.get_pronostico_hourly_punto(db, lat, lon, fecha_desde, fecha_hasta)
    return SuccessResponse(
        message=f"Pronóstico hourly obtenido ({len(data)} registros)",
        data=data
    )


@router.post("/pronostico-digital/actualizar-municipio/{id_municipio}",
             tags=[TAGS_PREDICCIONES_DIGITALES],
             dependencies=[Depends(require_rol(*ROLES_SINB_ADMIN))],
             summary="Actualizar pronóstico diario de municipio (uso cron)")
def actualizar_pronostico_municipio(
    id_municipio: int = Path(..., description="ID del municipio"),
    latitud: float = Query(..., description="Latitud del centroide"),
    longitud: float = Query(..., description="Longitud del centroide"),
    db: Session = Depends(get_db)
):
    """
    Actualizar pronóstico diario para un municipio.
    
    Usado por tarea cron (06:00 y 18:00).
    Requiere rol admin.
    """
    from datetime import date
    resultado = service.guardar_pronostico_diario_municipal(
        db, id_municipio, latitud, longitud, date.today()
    )
    return SuccessResponse(message="Pronóstico actualizado", data=resultado)


    db: Session = Depends(get_db)
# ============================================================================
# GALERÍA DE EVIDENCIAS (Fotos/Audio de Bioindicadores)
# ============================================================================

@router.get("/galeria/evidencias", 
            tags=["SINB > Galería de Evidencias"],
            summary="Obtener galería de evidencias con filtros")
def get_galeria_evidencias(
    id_indicador_natural: UUID = Query(None, description="Filtrar por indicador natural"),
    id_grupo: UUID = Query(None, description="Filtrar por grupo biocultural"),
    id_municipio: int = Query(None, description="Filtrar por municipio"),
    codigo_comunidad: str = Query(None, description="Filtrar por comunidad"),
    id_usuario_subio: int = Query(None, description="Filtrar por usuario que subió"),
    formato: str = Query(None, description="Filtrar por formato (JPG, PNG, MP3)"),
    fecha_desde: date = Query(None, description="Fecha desde"),
    fecha_hasta: date = Query(None, description="Fecha hasta"),
    con_gps: bool = Query(None, description="Solo evidencias con coordenadas GPS"),
    skip: int = Query(0, ge=0, description="Saltar registros"),
    limit: int = Query(100, ge=1, le=500, description="Límite de registros"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """
    **Galería de evidencias** con filtros completos y anidados JSON.
    
    **Filtros disponibles:**
    - `id_indicador_natural`: Filtrar por bioindicador específico
    - `id_grupo`: Filtrar por grupo biocultural (Animales, Plantas, etc.)
    - `id_municipio`: Filtrar por municipio
    - `codigo_comunidad`: Filtrar por comunidad
    - `id_usuario_subio`: Filtrar por usuario que subió la evidencia
    - `formato`: Filtrar por formato (JPG, PNG, MP3, WAV)
    - `fecha_desde`: Fecha mínima de carga
    - `fecha_hasta`: Fecha máxima de carga
    - `con_gps`: Solo evidencias con coordenadas GPS
    
    **Respuesta incluye:**
    - Indicador natural anidado (con grupo)
    - Observación registro anidada
    - Usuario que subió anidado
    - Metadata (tamaño, formato, GPS si disponible)
    - Paginación: skip/limit
    """
    filtros = {
        "id_indicador_natural": id_indicador_natural,
        "id_grupo": id_grupo,
        "id_municipio": id_municipio,
        "codigo_comunidad": codigo_comunidad,
        "id_usuario_subio": id_usuario_subio,
        "formato": formato,
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,
        "con_gps": con_gps
    }
    
    # Filtrar campos None
    filtros = {k: v for k, v in filtros.items() if v is not None}
    
    data, total = service.get_evidencias_galeria(db, filtros, skip, limit)
    
    return SuccessResponse(
        message=f"Galería obtenida ({len(data)} de {total} evidencias)",
        data=data,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/galeria/indicadores-destacados",
            tags=["SINB > Galería de Evidencias"],
            summary="Obtener indicadores con más evidencias (top fotos)")
def get_indicadores_destacados(
    id_grupo: UUID = Query(None, description="Filtrar por grupo biocultural"),
    limit: int = Query(10, ge=1, le=50, description="Cantidad de indicadores a retornar"),
    db: Session = Depends(get_db)
):
    """
    **Ranking de indicadores** con más evidencias (fotos) en la galería.
    
    **Útil para:**
    - Ver qué bioindicadores tienen más documentación fotográfica
    - Identificar indicadores populares o bien documentados
    - Explorar la galería por indicador más fotografiado
    
    **Respuesta incluye:**
    - Información completa del indicador
    - Grupo biocultural anidado
    - Cantidad total de evidencias
    - Últimas fotos subidas (URLs, descripciones)
    """
    data = service.get_indicadores_destacados_galeria(db, id_grupo, limit)
    return SuccessResponse(
        message=f"Indicadores destacados obtenidos ({len(data)} indicadores)",
        data=data
    )


@router.get("/galeria/municipio/{id_municipio}",
            tags=["SINB > Galería de Evidencias"],
            summary="Obtener galería de evidencias por municipio")
def get_galeria_municipal(
    id_municipio: int = Path(..., description="ID del municipio"),
    limit: int = Query(50, ge=1, le=500, description="Límite de evidencias"),
    db: Session = Depends(get_db)
):
    """
    **Galería de evidencias filtrada por municipio**.
    
    Muestra todas las fotos/evidencias de bioindicadores documentadas en ese municipio.
    
    **Respuesta incluye:**
    - Evidencias con indicador anidado
    - Municipio y comunidad anidados
    - Total de evidencias en el municipio
    - Ordenadas por fecha de carga (más recientes primero)
    """
    data = service.get_galeria_por_municipio(db, id_municipio, limit)
    total_comunal = data[0]["total_comunal"] if data else 0
    
    return SuccessResponse(
        message=f"Galería municipal obtenida ({len(data)} de {total_comunal} evidencias)",
        data=data
    )


@router.get("/galeria/indicator/{id_indicador}",
            tags=["SINB > Galería de Evidencias"],
            summary="Obtener galería de un bioindicador específico")
def get_galeria_indicador(
    id_indicador: UUID = Path(..., description="ID del indicador natural"),
    skip: int = Query(0, ge=0, description="Saltar registros"),
    limit: int = Query(100, ge=1, le=500, description="Límite de evidencias"),
    db: Session = Depends(get_db)
):
    """
    **Galería completa de un bioindicador específico**.
    
    Muestra todas las fotos/evidencias documentadas para ese indicador.
    
    **Útil para:**
    - Ver toda la documentación fotográfica de un indicador
    - Explorar variaciones geográficas del mismo indicador
    - Validar identificación del bioindicador
    
    **Respuesta incluye:**
    - Todas las evidencias del indicador
    - Usuario que subió cada evidencia
    - Ubicación (municipio, comunidad) de cada foto
    - Metadata de cada archivo
    """
    filtros = {"id_indicador_natural": id_indicador}
    data, total = service.get_evidencias_galeria(db, filtros, skip, limit)
    
    return SuccessResponse(
        message=f"Galería del indicador obtenida ({len(data)} de {total} evidencias)",
        data=data,
        total=total,
        skip=skip,
        limit=limit
    )
