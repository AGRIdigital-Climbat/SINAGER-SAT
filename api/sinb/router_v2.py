from fastapi import APIRouter, Depends, HTTPException, Query, Body, Path, File, Form, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Literal
from datetime import date, datetime, timedelta
from uuid import UUID

from ..database import get_db
from ..dependencies import get_current_user
from ..response import SuccessResponse, DataListResponse, DataItemResponse
from ..pagination import pagina_limit_offset
from ..upload import save_upload_file, delete_file_from_server
from . import service
from .service import _row, _rows
from .schemas import (
    GrupoCreate, GrupoUpdate, GrupoResponse,
    IndicadorNaturalCreate, IndicadorNaturalUpdate, IndicadorNaturalResponse,
    CaracteristicaCreate, CaracteristicaUpdate, CaracteristicaResponse,
    ComportamientoCreate, ComportamientoUpdate, ComportamientoResponse,
    SignificadoCreate, SignificadoUpdate, SignificadoResponse,
    ZonaGeograficaCreate, ZonaGeograficaUpdate, ZonaGeograficaResponse,
    CategoriaPronosticoCreate, CategoriaPronosticoUpdate, CategoriaPronosticoResponse,
    EscenarioCreate, EscenarioUpdate, EscenarioResponse,
    PronosticoLargoCreate, PronosticoLargoUpdate, PronosticoLargoResponse,
    PronosticoCortoCreate, PronosticoCortoUpdate, PronosticoCortoResponse,
    VerificacionPronosticoCreate, CalculoVerificacionRequest, CalculoVerificacionResponse,
    AvisoCreate, AvisoUpdate, AvisoResponse,
    ObservadorIndiceCreate, ObservadorIndiceUpdate, ObservadorIndiceResponse,
    PronosticoObservadorCreate, PronosticoObservadorResponse,
    MapaFiltros,
    IndicadorFotoUpdate, IndicadorFotoResponse,
    PronosticoDiarioHistoricoRequest, PronosticoDiarioResponse, PronosticoDiarioHistoricoResponse,
    PronosticoDigitalConsultarRequest, PronosticoDigitalConsultarResponse,
)
from .utils import require_rol, scope_geografico, autorizar_propietario, ROLES_SINB_ADMIN, ROLES_SINB_VALIDACION


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
TAGS_VALIDACION = "SINB > Validación de Predicciones"
TAGS_MAPAS = "SINB > Mapas GeoJSON"
TAGS_REPORTES = "SINB > Reportes"
TAGS_OBSERVADORES = "SINB > Observadores"


# ============================================================================
# CONTROL DE AUTORÍA (editar/borrar: solo el usuario que creó el registro)
# ============================================================================

def _exigir_autor(db: Session, sql: str, id_, user: dict, campo: str = "id_usuario_subio"):
    """Carga la fila y exige que el usuario sea su autor.

    404 si el registro no existe, 403 si existe pero no es del usuario.
    No hay excepción para superadmin/admin: la regla es estricta.
    """
    autorizar_propietario(_row(db, sql, {"id": id_}), user, campo)


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
             summary="Crear grupo biocultural")
def crear_grupo(data: GrupoCreate, db: Session = Depends(get_db),
                user=Depends(get_current_user)):
    """Crear nuevo grupo biocultural. Cualquier usuario autenticado."""
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
def eliminar_grupo(id: UUID, db: Session = Depends(get_db),
                   user=Depends(get_current_user)):
    """Eliminar grupo **definitivamente** (borrado físico).

    Deja registro en `sinb.registro_borrado` para que la app offline la retire de su caché.
    Si el grupo aún tiene indicadores, comportamientos, significados o pronósticos arriba,
    responde 409 con el detalle: retírelo con `estado: INACTIVO` o borre antes lo que lo usa."""
    service.delete_grupo(db, id, user["id_usuario"])
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


@router.post("/indicador-natural", tags=[TAGS_CATALOGOS], status_code=201)
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
def eliminar_indicador(id: UUID, db: Session = Depends(get_db),
                   user=Depends(get_current_user)):
    """Eliminar indicador natural **definitivamente** (borrado físico).

    Deja registro en `sinb.registro_borrado`. Responde 409 si todavía tiene características,
    fotos, índices de observador o pronósticos: así ninguna foto de campo se pierde."""
    service.delete_indicador_natural(db, id, user["id_usuario"])
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


@router.get("/caracteristica/{id}", tags=[TAGS_CATALOGOS],
            response_model=DataItemResponse[CaracteristicaResponse],
            summary="Obtener característica por ID")
def obtener_caracteristica(id: UUID, db: Session = Depends(get_db)):
    """Obtener característica por su ID."""
    result = service.get_caracteristica(db, id)
    if not result:
        raise HTTPException(status_code=404, detail="Característica no encontrado")
    return SuccessResponse(message="Característica obtenida correctamente", data=result)


@router.post("/caracteristica", tags=[TAGS_CATALOGOS], status_code=201)
def crear_caracteristica(data: CaracteristicaCreate, db: Session = Depends(get_db),
                         user=Depends(get_current_user)):
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
def eliminar_caracteristica(id: UUID, db: Session = Depends(get_db),
                   user=Depends(get_current_user)):
    """Eliminar característica **definitivamente** (borrado físico + registro de borrado).
    Responde 409 si tiene comportamientos o pronósticos arriba."""
    service.delete_caracteristica(db, id, user["id_usuario"])
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


@router.get("/comportamiento/{id}", tags=[TAGS_CATALOGOS],
            response_model=DataItemResponse[ComportamientoResponse],
            summary="Obtener comportamiento por ID")
def obtener_comportamiento(id: UUID, db: Session = Depends(get_db)):
    """Obtener comportamiento por su ID."""
    result = service.get_comportamiento(db, id)
    if not result:
        raise HTTPException(status_code=404, detail="Comportamiento no encontrado")
    return SuccessResponse(message="Comportamiento obtenido correctamente", data=result)


@router.post("/comportamiento", tags=[TAGS_CATALOGOS], status_code=201)
def crear_comportamiento(data: ComportamientoCreate, db: Session = Depends(get_db),
                         user=Depends(get_current_user)):
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
def eliminar_comportamiento(id: UUID, db: Session = Depends(get_db),
                   user=Depends(get_current_user)):
    """Eliminar comportamiento **definitivamente** (borrado físico + registro de borrado).
    Responde 409 si tiene significados o pronósticos arriba."""
    service.delete_comportamiento(db, id, user["id_usuario"])
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


@router.get("/significado/{id}", tags=[TAGS_CATALOGOS],
            response_model=DataItemResponse[SignificadoResponse],
            summary="Obtener significado por ID")
def obtener_significado(id: UUID, db: Session = Depends(get_db)):
    """Obtener significado por su ID."""
    result = service.get_significado(db, id)
    if not result:
        raise HTTPException(status_code=404, detail="Significado no encontrado")
    return SuccessResponse(message="Significado obtenido correctamente", data=result)


@router.post("/significado", tags=[TAGS_CATALOGOS], status_code=201)
def crear_significado(data: SignificadoCreate, db: Session = Depends(get_db),
                      user=Depends(get_current_user)):
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
def eliminar_significado(id: UUID, db: Session = Depends(get_db),
                   user=Depends(get_current_user)):
    """Eliminar significado **definitivamente** (borrado físico + registro de borrado)."""
    service.delete_significado(db, id, user["id_usuario"])
    return {"message": "Significado eliminado correctamente"}


# --- Zona Geográfica ---

@router.get("/zona-geografica", tags=[TAGS_CATALOGOS],
            summary="Listar zonas geográficas (completo)")
def listar_zonas_geograficas(db: Session = Depends(get_db)):
    """Obtener todas las zonas geográficas activas."""
    data = service.get_zonas_geograficas(db)
    return SuccessResponse(message="Zonas listadas correctamente", data=data)


@router.get("/zona-geografica/{id}", tags=[TAGS_CATALOGOS],
            response_model=DataItemResponse[ZonaGeograficaResponse],
            summary="Obtener zona geográfica por ID")
def obtener_zona_geografica(id: UUID, db: Session = Depends(get_db)):
    """Obtener zona geográfica por su ID."""
    result = service.get_zona_geografica(db, id)
    if not result:
        raise HTTPException(status_code=404, detail="Zona geográfica no encontrado")
    return SuccessResponse(message="Zona geográfica obtenida correctamente", data=result)


@router.post("/zona-geografica", tags=[TAGS_CATALOGOS], status_code=201)
def crear_zona_geografica(data: ZonaGeograficaCreate, db: Session = Depends(get_db),
                          user=Depends(get_current_user)):
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
def eliminar_zona_geografica(id: UUID, db: Session = Depends(get_db),
                   user=Depends(get_current_user)):
    """Eliminar zona geográfica **definitivamente** (borrado físico + registro de borrado)."""
    service.delete_zona_geografica(db, id, user["id_usuario"])
    return {"message": "Zona eliminada correctamente"}


# --- Categoría Pronóstico ---

@router.get("/categoria-pronostico", tags=[TAGS_CATALOGOS],
            summary="Listar categorías de pronóstico (completo)")
def listar_categorias_pronostico(
    nombre: str | None = Query(None, description="Buscar por nombre"),
    db: Session = Depends(get_db)
):
    """Obtener categorías de pronóstico activas."""
    data = service.get_categorias_pronostico(db, nombre)
    return SuccessResponse(message="Categorías listadas correctamente", data=data)


@router.get("/categoria-pronostico/{id}", tags=[TAGS_CATALOGOS],
            response_model=DataItemResponse[CategoriaPronosticoResponse],
            summary="Obtener categoría de pronóstico por ID")
def obtener_categoria_pronostico(id: UUID, db: Session = Depends(get_db)):
    """Obtener categoría de pronóstico por su ID."""
    result = service.get_categoria_pronostico(db, id)
    if not result:
        raise HTTPException(status_code=404, detail="Categoría de pronóstico no encontrado")
    return SuccessResponse(message="Categoría de pronóstico obtenido correctamente", data=result)


@router.post("/categoria-pronostico", tags=[TAGS_CATALOGOS], status_code=201)
def crear_categoria_pronostico(data: CategoriaPronosticoCreate, db: Session = Depends(get_db),
                               user=Depends(get_current_user)):
    """Crear categoría de pronóstico."""
    result = service.create_categoria_pronostico(db, data.model_dump())
    return SuccessResponse(message="Categoría creada correctamente", data=result)


@router.put("/categoria-pronostico/{id}", tags=[TAGS_CATALOGOS],
            dependencies=[Depends(require_rol(*ROLES_SINB_ADMIN))])
def actualizar_categoria_pronostico(id: UUID, data: CategoriaPronosticoUpdate, db: Session = Depends(get_db)):
    """Actualizar categoría de pronóstico."""
    result = service.update_categoria_pronostico(db, id, data.model_dump(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    return SuccessResponse(message="Categoría actualizada correctamente", data=result)


@router.delete("/categoria-pronostico/{id}", tags=[TAGS_CATALOGOS],
               dependencies=[Depends(require_rol(*ROLES_SINB_ADMIN))])
def eliminar_categoria_pronostico(id: UUID, db: Session = Depends(get_db),
                   user=Depends(get_current_user)):
    """Eliminar categoría de pronóstico **definitivamente** (borrado físico + registro de borrado).
    Responde 409 si tiene escenarios, bloques de pronóstico, pronósticos cortos o avisos."""
    service.delete_categoria_pronostico(db, id, user["id_usuario"])
    return {"message": "Categoría eliminada correctamente"}


# --- Escenario ---

@router.get("/escenario", tags=[TAGS_CATALOGOS],
            response_model=DataListResponse[EscenarioResponse],
            summary="Listar escenarios (completo)")
def listar_escenarios(
    id_categoria: UUID | None = Query(None, description="Filtrar por categoría"),
    db: Session = Depends(get_db)
):
    """Obtener escenarios activos."""
    data = service.get_escenarios(db, id_categoria)
    return SuccessResponse(message="Escenarios listados correctamente", data=data)


@router.get("/escenario/{id}", tags=[TAGS_CATALOGOS],
            response_model=DataItemResponse[EscenarioResponse],
            summary="Obtener escenario por ID")
def obtener_escenario(id: UUID, db: Session = Depends(get_db)):
    """Obtener escenario por su ID."""
    result = service.get_escenario(db, id)
    if not result:
        raise HTTPException(status_code=404, detail="Escenario no encontrado")
    return SuccessResponse(message="Escenario obtenido correctamente", data=result)


@router.post("/escenario", tags=[TAGS_CATALOGOS], status_code=201,
             response_model=DataItemResponse[EscenarioResponse])
def crear_escenario(data: EscenarioCreate, db: Session = Depends(get_db),
                    user=Depends(get_current_user)):
    """Crear escenario."""
    result = service.create_escenario(db, data.model_dump())
    return SuccessResponse(message="Escenario creado correctamente", data=result)


@router.put("/escenario/{id}", tags=[TAGS_CATALOGOS],
            dependencies=[Depends(require_rol(*ROLES_SINB_ADMIN))],
            response_model=DataItemResponse[EscenarioResponse])
def actualizar_escenario(id: UUID, data: EscenarioUpdate, db: Session = Depends(get_db)):
    """Actualizar escenario."""
    result = service.update_escenario(db, id, data.model_dump(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="Escenario no encontrado")
    return SuccessResponse(message="Escenario actualizado correctamente", data=result)


@router.delete("/escenario/{id}", tags=[TAGS_CATALOGOS],
               dependencies=[Depends(require_rol(*ROLES_SINB_ADMIN))])
def eliminar_escenario(id: UUID, db: Session = Depends(get_db),
                   user=Depends(get_current_user)):
    """Eliminar escenario **definitivamente** (borrado físico + registro de borrado).
    Responde 409 si está asignado a algún bloque de pronóstico."""
    service.delete_escenario(db, id, user["id_usuario"])
    return {"message": "Escenario eliminado correctamente"}


# ============================================================================
# CONTROL DE BORRADOS (sincronización offline)
# ============================================================================

@router.get("/catalogo/borrados", tags=[TAGS_CATALOGOS],
            summary="Listar borrados físicos desde una fecha (sync offline)")
def listar_borrados(
    desde: datetime | None = Query(None, description="Only borrados a partir de este instante (ISO 8601). Sin valor: todos"),
    tabla: Literal["grupo", "indicador_natural", "caracteristica", "comportamiento",
                   "significado", "zona_geografica", "categoria_pronostico", "escenario",
                   "avisos", "indicador_foto", "observador_indice",
                   "pronostico_largo", "pronostico_corto"] | None = Query(
        None, description="Filtrar por tabla borrada"),
    limit: int | None = Query(None, ge=1, description="Registros por página. Sin valor: sin límite"),
    skip: int = Query(0, ge=0, description="Registros a saltar"),
    todos: bool = Query(False, description="true = devolver todos sin LIMIT/OFFSET"),
    db: Session = Depends(get_db)
):
    """
    Borrar por API es físico, así que la fila desaparece sin dejar rastro en su tabla.
    Este listado es el registro aparte (`sinb.registro_borrado`) para que la app offline
    sepa qué retirar de su caché desde su última descarga.

    Pública, igual que los catálogos. `codigo` es el código o nombre que tenía la fila y
    `id_off` el identificador del dispositivo, cuando existía.
    """
    data, total = service.get_borrados(db, desde, tabla, limit=limit, skip=skip, todos=todos)
    return SuccessResponse(message="Borrados listados correctamente", data=data, total=total)


# --- Dimensión Recomendación ---



# ============================================================================
# PRONÓSTICOS ESTACIONALES Y TEMPORALES
# ============================================================================

@router.get("/pronostico-largo", tags=[TAGS_PREDICCIONES_LARGO],
            response_model=DataListResponse[PronosticoLargoResponse],
            summary="Listar pronósticos estacionales (últimos 15)")
def listar_pronosticos_estacionales(
    skip: int = Query(0, ge=0),
    limit: int = Query(15, ge=1, le=100),
    todos: bool = Query(False, description="true = devolver todos sin LIMIT/OFFSET"),
    id_categoria: UUID | None = Query(None, description="Filtrar por categoría"),
    fecha_emision_desde: date | None = Query(None, description="Fecha emisión desde"),
    fecha_emision_hasta: date | None = Query(None, description="Fecha emisión hasta"),
    estado: Literal["EMITIDO", "ACEPTADO", "RECHAZADO", "EN_REVISION"] | None = Query(
        None, description="Filtrar por estado de validación"),
    id_usuario_subio: int | None = Query(None, description="Filtrar por elaborador"),
    id_municipio: int | None = Query(None, description="Filtrar por municipio"),
    codigo_comunidad: str | None = Query(None, description="Filtrar por comunidad"),
    db: Session = Depends(get_db)
):
    """Listar pronósticos estacionales con paginación y filtros.

    - `limit`: cantidad (los más recientes primero); `skip`: offset.
    - `todos=true`: ignora `limit`/`skip` y devuelve el conjunto completo.

    Cada elemento viene con sus hijos anidados: `pronosticos[].escenarios[]` (donde vive la
    `confianza` ALTA | MEDIA | BAJA), `recomendaciones[]` (texto libre) y `observadores[]`
    (solo `id_usuario`, `nombre`, `usuario`, `fecha_asignacion`, `id_observador_off`).
    """
    data, total = service.get_pronosticos_estacionales(
        db, skip=skip, limit=limit, todos=todos,
        id_categoria=id_categoria,
        fecha_emision_desde=fecha_emision_desde,
        fecha_emision_hasta=fecha_emision_hasta,
        estado=estado,
        id_usuario_subio=id_usuario_subio,
        id_municipio=id_municipio,
        codigo_comunidad=codigo_comunidad
    )
    return SuccessResponse(message="Pronósticos estacionales listados", data=data, total=total)


@router.get("/pronostico-largo/{id}", tags=[TAGS_PREDICCIONES_LARGO],
            response_model=DataItemResponse[PronosticoLargoResponse],
            summary="Obtener pronóstico estacional completo")
def obtener_pronostico_estacional(id: UUID, db: Session = Depends(get_db)):
    """Obtener un pronóstico estacional completo.

    Devuelve la cabecera, `periodo`, `cadena_biocultural`, `contexto`, los bloques
    `pronosticos[]` con sus `escenarios[]` (cada uno con `confianza` ALTA | MEDIA | BAJA o
    null), las `recomendaciones[]` en texto libre y los `observadores[]` asignados.
    La confianza **solo** está en los escenarios: los observadores no llevan confianza.
    `tipo_registro` es INDIVIDUAL (1 observador) o COLECTIVO (2+).
    """
    result = service.get_pronostico_largo(db, id)
    if not result:
        raise HTTPException(status_code=404, detail="Pronóstico no encontrado")
    return SuccessResponse(message="Pronóstico obtenido correctamente", data=result)


@router.post("/pronostico-largo", tags=[TAGS_PREDICCIONES_LARGO], status_code=201,
             response_model=DataItemResponse[PronosticoLargoResponse],
             summary="Crear pronóstico estacional con escenarios y observadores")
def crear_pronostico_estacional(data: PronosticoLargoCreate, db: Session = Depends(get_db),
                                 user=Depends(get_current_user)):
    """
    Crear pronóstico largo plazo con contrato anidado (MD 15).

    - **cadena_biocultural**: grupo → indicador → característica → comportamiento (obligatoria y coherente)
    - **periodo**: inicio y fin (fin >= inicio)
    - **pronosticos**: 1..N bloques por categoría con sus escenarios
    - **recomendaciones**: texto libre — cada una con `id_recomendacion` (opcional, lo genera el
      servidor si no viene), `id_recomendacion_off` y `nombre` (el texto de la recomendación)
    - **escenarios**: `{id_escenario, confianza}` donde `confianza` es ALTA, MEDIA o BAJA (opcional)
    - **observadores**: 1..N obligatorios — auto-registro o en representación (recolector).
      Solo llevan `id_usuario` (y `id_observador_off` opcional): la confianza no aplica al
      observador, va en los **escenarios** del bloque
    - **id_usuario_subio**: lo fija siempre el servidor (usuario actual)

    **Permisos:** cualquier usuario autenticado puede crear; editar/eliminar es
    exclusivo del autor del pronóstico (sin excepción, tampoco superadmin/admin).

    Ejemplo:
    ```json
    {
      "texto_observador": "Aullido ronco a finales de septiembre",
      "id_municipio": 20302,
      "codigo_comunidad": "05507675566-D",
      "cadena_biocultural": {
        "id_grupo": "a97a54ca-a4d2-4c73-81b5-18184c88a592",
        "id_indicador_natural": "94fa9644-9b49-4b98-8a24-3d54dff31d23",
        "id_caracteristica": "57fe3a82-c3db-4679-9267-954579061513",
        "id_comportamiento": "ea9c032f-c37c-489b-a7f8-5fc53d25b8d4"
      },
      "periodo": {"inicio": "2026-09-01", "fin": "2026-12-15"},
      "contexto": {"latitud": -17.5, "longitud": -66.1, "altitud": 3800},
      "pronosticos": [
        {
          "id_categoria": "01f7aa3d-5736-44b5-8004-d9b56becd265",
          "id_escenarios": [
            {"id_escenario": "5f028719-7f55-488b-a4f3-be413e0e1173", "confianza": "ALTA"},
            {"id_escenario": "9dd808be-49b1-4394-962f-dc5ab4cf7d24", "confianza": "MEDIA"},
            {"id_escenario": "e67decf3-ffa2-46ea-b05e-d4a3e7419b8d", "confianza": "BAJA"}
          ]
        },
        {
          "id_categoria": "a714e69f-3d73-4090-95cb-513f3b13af11",
          "id_escenarios": [{"id_escenario": "4acceb80-2150-4d94-9306-c5889c1c578e"}]
        }
      ],
      "recomendaciones": [
        {
          "id_recomendacion_off": "rec-off-001",
          "nombre": "Sembrar variedades de ciclo corto antes del 15 de octubre"
        },
        {
          "id_recomendacion_off": "rec-off-002",
          "nombre": "Aplicar cobertura mortera en suelos con humedad deficitaria"
        }
      ],
      "observadores": [{"id_usuario": 810}]
    }
    ```
    """
    result = service.create_pronostico_largo(db, data.model_dump(), user["id_usuario"])
    return SuccessResponse(message="Pronóstico creado correctamente", data=result)


@router.put("/pronostico-largo/{id}", tags=[TAGS_PREDICCIONES_LARGO],
            response_model=DataItemResponse[PronosticoLargoResponse])
def actualizar_pronostico_estacional(id: UUID, data: PronosticoLargoUpdate,
                                     db: Session = Depends(get_db),
                                     user=Depends(get_current_user)):
    """Actualizar pronóstico estacional (parcial: solo se modifican los campos enviados).
    Solo el autor del pronóstico.

    - `pronosticos`: si se envía, **reemplaza** todos los bloques y sus escenarios; cada
      escenario acepta uuid plano o `{id_escenario, confianza}` con confianza ALTA | MEDIA | BAJA
    - `recomendaciones`: si se envía, **reemplaza** todas las recomendaciones en texto libre
    - `periodo`, `contexto`, `cadena_biocultural`: se actualiza campo a campo; los que no
      se envían conservan su valor anterior (no hay forma de ponerlos a NULL con este PUT)
    - `estado`: EMITIDO | ACEPTADO | RECHAZADO | EN_REVISION
    - `observadores`: **no se editan aquí** (se ignoran); se gestionan con
      `POST /pronostico/{id}/observadores` y `DELETE /pronostico/{id}/observador/{id_usuario}`

    La respuesta trae el pronóstico completo releyendo los hijos, con la confianza solo en
    `pronosticos[].escenarios[]`.
    """
    _exigir_autor(db, "SELECT id_usuario_subio FROM sinb.pronostico_largo WHERE id = :id", id, user)
    result = service.update_pronostico_largo(db, id, data.model_dump(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="Pronóstico no encontrado")
    return SuccessResponse(message="Pronóstico actualizado correctamente", data=result)


@router.delete("/pronostico-largo/{id}", tags=[TAGS_PREDICCIONES_LARGO])
def eliminar_pronostico_estacional(id: UUID, db: Session = Depends(get_db),
                                   user=Depends(get_current_user)):
    """Eliminar pronóstico estacional. Solo el autor del pronóstico.

    Borrado físico: elimina en cascada sus bloques con escenarios, sus recomendaciones y
    sus observadores, y deja el tombstone para la sincronización offline.
    """
    _exigir_autor(db, "SELECT id_usuario_subio FROM sinb.pronostico_largo WHERE id = :id", id, user)
    service.delete_pronostico_largo(db, id, user["id_usuario"])
    return {"message": "Pronóstico eliminado correctamente"}



@router.post("/pronostico-largo/{id}/item/{id_item}/escenario",
             tags=[TAGS_PREDICCIONES_LARGO],
             summary="Agregar escenario a un bloque del pronóstico")
def agregar_escenario(id: UUID, id_item: UUID, id_escenario: UUID = Query(...),
                      confianza: Literal["ALTA", "MEDIA", "BAJA"] | None = Query(
                          None, description="Confianza del escenario (opcional)"),
                      db: Session = Depends(get_db),
                      user=Depends(get_current_user)):
    """Agregar o actualizar un escenario dentro de un bloque (categoría) del pronóstico.

    Solo el autor. El escenario debe existir y pertenecer a la categoría del bloque
    (`id_categoria`); si ya estaba asignado, se actualiza su `confianza`.
    `confianza`: ALTA | MEDIA | BAJA, opcional. Otros valores devuelven 422.
    """
    _exigir_autor(db, "SELECT id_usuario_subio FROM sinb.pronostico_largo WHERE id = :id", id, user)
    result = service.add_escenario_a_pronostico(db, id, id_item, id_escenario, confianza)
    return SuccessResponse(message="Escenario agregado correctamente", data=result)


@router.put("/pronostico-largo/{id}/item/{id_item}/escenario/{id_escenario}",
            tags=[TAGS_PREDICCIONES_LARGO],
            summary="Actualizar confianza de un escenario de un bloque")
def actualizar_escenario(id: UUID, id_item: UUID, id_escenario: UUID,
                         confianza: Literal["ALTA", "MEDIA", "BAJA"] | None = Query(
                             None, description="Confianza del escenario; sin parámetro = dejarla vacía"),
                         db: Session = Depends(get_db),
                         user=Depends(get_current_user)):
    """Actualizar la confianza (ALTA|MEDIA|BAJA) de un escenario ya asignado en un bloque. Solo el autor."""
    _exigir_autor(db, "SELECT id_usuario_subio FROM sinb.pronostico_largo WHERE id = :id", id, user)
    result = service.update_escenario_en_pronostico(db, id, id_item, id_escenario, confianza)
    if not result:
        raise HTTPException(status_code=404, detail="Escenario no encontrado en el bloque")
    return SuccessResponse(message="Escenario actualizado correctamente", data=result)


@router.delete("/pronostico-largo/{id}/item/{id_item}/escenario/{id_escenario}",
               tags=[TAGS_PREDICCIONES_LARGO])
def remover_escenario(id: UUID, id_item: UUID, id_escenario: UUID,
                      db: Session = Depends(get_db),
                      user=Depends(get_current_user)):
    """Remover un escenario de un bloque del pronóstico. Solo el autor."""
    _exigir_autor(db, "SELECT id_usuario_subio FROM sinb.pronostico_largo WHERE id = :id", id, user)
    service.remove_escenario_de_pronostico(db, id, id_item, id_escenario)
    return {"message": "Escenario removido correctamente"}


# --- Pronósticos Temporales (Corto Plazo) ---

@router.get("/pronostico-corto", tags=[TAGS_PREDICCIONES_CORTO], response_model=SuccessResponse,
            summary="Listar pronósticos temporales (últimos 15)")
def listar_pronosticos_temporales(
    skip: int = Query(0, ge=0),
    limit: int = Query(15, ge=1, le=100),
    todos: bool = Query(False, description="true = devolver todos sin LIMIT/OFFSET"),
    id_categoria: UUID | None = Query(None, description="Filtrar por categoría"),
    fecha_emision_desde: date | None = Query(None, description="Fecha emisión desde"),
    confianza: Literal["ALTA", "MEDIA", "BAJA"] | None = Query(
        None, description="Filtrar por confianza del pronóstico"),
    estado: Literal["EMITIDO", "ACEPTADO", "RECHAZADO", "EN_REVISION"] | None = Query(
        None, description="Filtrar por estado de validación"),
    codigo_comunidad: str | None = Query(None, description="Filtrar por comunidad"),
    db: Session = Depends(get_db)
):
    """Listar pronósticos temporales con paginación.

    `limit`/`skip` paginan (los más recientes primero); `todos=true` devuelve todo.
    """
    data, total = service.get_pronosticos_temporales(
        db, skip=skip, limit=limit, todos=todos,
        id_categoria=id_categoria,
        fecha_emision_desde=fecha_emision_desde,
        confianza=confianza,
        estado=estado,
        codigo_comunidad=codigo_comunidad
    )
    return SuccessResponse(message="Pronósticos temporales listados", data=data, total=total)


@router.get("/pronostico-corto/{id}", tags=[TAGS_PREDICCIONES_CORTO], response_model=SuccessResponse)
def obtener_pronostico_corto(id: UUID, db: Session = Depends(get_db),
                         current_user: dict = Depends(get_current_user)):
    """Obtener pronóstico de corto plazo completo."""
    result = service.get_pronostico_corto_by_id(db, id)
    if not result:
        raise HTTPException(status_code=404, detail="Pronóstico no encontrado")
    return SuccessResponse(message="Pronóstico de corto plazo", data=result)


@router.post("/pronostico-corto", tags=[TAGS_PREDICCIONES_CORTO], status_code=201)
def crear_pronostico_temporal(data: PronosticoCortoCreate, db: Session = Depends(get_db),
                              user=Depends(get_current_user)):
    """Crear pronóstico temporal. Cualquier usuario autenticado."""
    result = service.create_pronostico_corto(db, data.model_dump(), user["id_usuario"])
    return SuccessResponse(message="Pronóstico temporal creado correctamente", data=result)


@router.put("/pronostico-corto/{id}", tags=[TAGS_PREDICCIONES_CORTO])
def actualizar_pronostico_temporal(id: UUID, data: PronosticoCortoUpdate,
                                   db: Session = Depends(get_db),
                                   user=Depends(get_current_user)):
    """Actualizar pronóstico temporal. Solo el autor."""
    _exigir_autor(db, "SELECT id_usuario_subio FROM sinb.pronostico_corto WHERE id = :id", id, user)
    result = service.update_pronostico_corto(db, id, data.model_dump(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="Pronóstico no encontrado")
    return SuccessResponse(message="Pronóstico actualizado correctamente", data=result)


@router.delete("/pronostico-corto/{id}", tags=[TAGS_PREDICCIONES_CORTO])
def eliminar_pronostico_temporal(id: UUID, db: Session = Depends(get_db),
                                 user=Depends(get_current_user)):
    """Eliminar pronóstico temporal. Solo el autor."""
    _exigir_autor(db, "SELECT id_usuario_subio FROM sinb.pronostico_corto WHERE id = :id", id, user)
    service.delete_pronostico_corto(db, id, user["id_usuario"])
    return {"message": "Pronóstico eliminado correctamente"}


# ============================================================================
# ASIGNACIÓN DE OBSERVADORES A PRONÓSTICOS
# ============================================================================

@router.post("/pronostico/{id}/observadores", tags=[TAGS_OBSERVADORES],
             dependencies=[Depends(require_rol(1, 6, 7, 8, 12, 13))],
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
    
    `confianza` solo aplica a pronósticos **temporales**; en los estacionales (largo) se
    ignora, porque la confianza de esos va en los escenarios de cada bloque.
    """
    result = service.asignar_observadores_a_pronostico(
        db, id, data.tipo_pronostico, data.id_observadores, data.confianza,
        user["id_usuario"]
    )
    return SuccessResponse(message="Observadores asignados correctamente", data=result)


@router.delete("/pronostico/{id}/observador/{id_usuario}", tags=[TAGS_OBSERVADORES],
               dependencies=[Depends(require_rol(1, 6, 7, 8, 12, 13))])
def remover_observador(
    id: UUID,
    id_usuario: int,
    tipo_pronostico: Literal["estacional", "temporal"] = Query(...),
    db: Session = Depends(get_db)
):
    """Remover asignación de observador de un pronóstico."""
    service.remover_observador_de_pronostico(db, id, tipo_pronostico, id_usuario)
    return {"message": "Observador removido correctamente"}


@router.get("/pronostico/{id}/observadores", tags=[TAGS_OBSERVADORES],
            summary="Listar observadores asignados a un pronóstico")
def listar_observadores_de_pronostico(
    id: UUID,
    tipo_pronostico: Literal["estacional", "temporal"] = Query(...),
    limit: int | None = Query(None, ge=1, description="Registros por página. Sin valor: sin límite"),
    skip: int = Query(0, ge=0, description="Registros a saltar"),
    todos: bool = Query(False, description="true = devolver todos sin LIMIT/OFFSET"),
    db: Session = Depends(get_db)
):
    """Observadores asignados a un pronóstico estacional o temporal.

    `confianza` solo tiene valor en los pronósticos **temporales**; en los estacionales
    siempre devuelve null porque en largo plazo la confianza vive en los escenarios.
    """
    data, total = service.get_observadores_de_pronostico(
        db, id, tipo_pronostico, limit=limit, skip=skip, todos=todos)
    return SuccessResponse(message="Observadores asignados listados", data=data, total=total)


# ============================================================================
# VALIDACIÓN DE PRONÓSTICOS (Automática y Manual)
# ============================================================================

@router.post("/verificacion/calcular", tags=[TAGS_VALIDACION],
             summary="Calcular verificación AUTOMÁTICA de pronósticos vencidos (cron)")
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
def listar_verificaciones_pendientes(
    limit: int | None = Query(None, ge=1, description="Registros por página. Sin valor: sin límite"),
    skip: int = Query(0, ge=0, description="Registros a saltar"),
    todos: bool = Query(False, description="true = devolver todos sin LIMIT/OFFSET"),
    db: Session = Depends(get_db),
):
    """Obtener lista de pronósticos vencidos pendientes de verificación."""
    data = service.get_verificaciones_pendientes(db, limit=limit, skip=skip, todos=todos)
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
# RANKING DE OBSERVADORES Y RECOLECTORES
# ============================================================================

@router.get("/observadores/ranking", tags=[TAGS_OBSERVADORES],
            summary="Ranking de observadores por aportes")
def ranking_observadores(
    rol: int | None = Query(None, description="Filtrar por rol (12=recolector, 13=observador)"),
    id_municipio: int | None = Query(None, description="Filtrar por municipio"),
    desde: date | None = Query(None, description="Fecha desde"),
    hasta: date | None = Query(None, description="Fecha hasta"),
    limite: int = Query(20, ge=1, le=100, description="Top N"),
    skip: int = Query(0, ge=0, description="Registros a saltar"),
    todos: bool = Query(False, description="true = devolver todos sin LIMIT (omite también `limite`)"),
    db: Session = Depends(get_db)
):
    """
    Ranking de usuarios por cantidad de reportes:
    - Pronósticos largo plazo
    - Pronósticos corto plazo  
    - Avisos
    - Fotos de indicadores naturales
    
    Retorna posición, id_usuario, nombre, rol, conteos por tipo y total.
    """
    where = ["u.activo = true"]
    params = {"limite": limite}
    
    if rol:
        where.append("u.id_rol = :rol")
        params["rol"] = rol
    if id_municipio:
        where.append("u.id_municipio = :id_municipio")
        params["id_municipio"] = id_municipio
    
    where_clause = " AND ".join(where)
    page, page_params = pagina_limit_offset(None if todos else limite, skip, todos)
    params.update(page_params)
    
    data = service._rows(db, f"""
        WITH conteos AS (
            SELECT id_usuario_subio as id_usuario, 
                   'pronostico_largo' as tipo, COUNT(*) as cantidad
            FROM sinb.pronostico_largo WHERE id_usuario_subio IS NOT NULL
            GROUP BY id_usuario_subio
            UNION ALL
            SELECT id_usuario_subio, 'pronostico_corto', COUNT(*)
            FROM sinb.pronostico_corto WHERE id_usuario_subio IS NOT NULL
            GROUP BY id_usuario_subio
            UNION ALL
            SELECT id_usuario_subio, 'avisos', COUNT(*)
            FROM sinb.avisos WHERE id_usuario_subio IS NOT NULL
            GROUP BY id_usuario_subio
            UNION ALL
            SELECT id_usuario_subio, 'fotos', COUNT(*)
            FROM sinb.indicador_foto
            GROUP BY id_usuario_subio
        ),
        total_por_usuario AS (
            SELECT id_usuario, SUM(cantidad) as total
            FROM conteos
            GROUP BY id_usuario
        )
        SELECT 
            ROW_NUMBER() OVER (ORDER BY t.total DESC) as posicion,
            u.id_usuario,
            u.usuario,
            u.nombre,
            u.id_rol,
            r.nombre as rol_nombre,
            COALESCE((SELECT cantidad FROM conteos WHERE id_usuario = u.id_usuario AND tipo = 'pronostico_largo'), 0) as pronosticos_largo,
            COALESCE((SELECT cantidad FROM conteos WHERE id_usuario = u.id_usuario AND tipo = 'pronostico_corto'), 0) as pronosticos_corto,
            COALESCE((SELECT cantidad FROM conteos WHERE id_usuario = u.id_usuario AND tipo = 'avisos'), 0) as avisos,
            COALESCE((SELECT cantidad FROM conteos WHERE id_usuario = u.id_usuario AND tipo = 'fotos'), 0) as fotos,
            t.total
        FROM total_por_usuario t
        JOIN usuarios.usuario u ON u.id_usuario = t.id_usuario
        JOIN usuarios.rol r ON r.id_rol = u.id_rol
        WHERE {where_clause}
        ORDER BY t.total DESC
        {page}
    """, params)
    
    return SuccessResponse(message="Ranking obtenido", data=data)


# ============================================================================

@router.get("/avisos", tags=[TAGS_PREDICCIONES_AVISOS],
            summary="Listar avisos de corto plazo (últimos 15)")
def listar_avisos(
    skip: int = Query(0, ge=0),
    limit: int = Query(15, ge=1, le=100),
    todos: bool = Query(False, description="true = devolver todos sin LIMIT/OFFSET"),
    id_municipio: int | None = Query(None, description="Filtrar por municipio"),
    codigo_comunidad: str | None = Query(None, description="Filtrar por comunidad"),
    vigente: bool | None = Query(None, description="Solo vigentes"),
    db: Session = Depends(get_db)
):
    """Listar avisos de corto plazo con paginación y filtros.

    `limit`/`skip` paginan (los más recientes primero); `todos=true` devuelve todo.
    """
    params = {}
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
    
    # cantidad → paginación; todos=True → sin LIMIT/OFFSET
    page = "" if todos else " LIMIT :limit OFFSET :skip"
    if not todos:
        params.update({"limit": limit, "skip": skip})

    data = service._rows(db, f"""
        SELECT a.*, cp.nombre as categoria_nombre, m.nombre as municipio_nombre,
               u.nombre as emisor_nombre
        FROM sinb.avisos a
        LEFT JOIN sinb.categoria_pronostico cp ON cp.id = a.id_categoria
        LEFT JOIN shared.municipio m ON m.id = a.id_municipio
        LEFT JOIN usuarios.usuario u ON u.id_usuario = a.id_usuario_subio
        WHERE {where_clause}
        ORDER BY a.fecha_emision DESC
        {page}
    """, params)
    
    return SuccessResponse(message="Avisos listados", data=data)


@router.get("/avisos/{id}", tags=[TAGS_PREDICCIONES_AVISOS],
            response_model=DataItemResponse[AvisoResponse],
            summary="Obtener aviso por ID")
def obtener_aviso(id: UUID, db: Session = Depends(get_db)):
    """Obtener un aviso por su ID."""
    result = service.get_aviso(db, id)
    if not result:
        raise HTTPException(status_code=404, detail="Aviso no encontrado")
    return SuccessResponse(message="Aviso obtenido correctamente", data=result)


@router.post("/avisos", tags=[TAGS_PREDICCIONES_AVISOS], status_code=201)
def crear_aviso(data: AvisoCreate, db: Session = Depends(get_db),
                user=Depends(get_current_user)):
    """
    Crear aviso de corto plazo. Cualquier usuario autenticado.

    **Flujo:** El productor dicta el aviso («va a granizar») → se asigna a comunidad →
    vence en 24-48h → se verifica si cumplió.
    """
    payload = data.model_dump()
    payload["codigo"] = f"AV-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    payload["id_usuario_subio"] = user["id_usuario"]
    from datetime import timedelta
    payload["fecha_vencimiento"] = datetime.now() + timedelta(hours=data.vigencia_horas)
    
    result = service._crear_unico(db, """
        INSERT INTO sinb.avisos 
        (codigo, id_categoria, codigo_comunidad, id_municipio, mensaje,
         fecha_emision, vigencia_horas, fecha_vencimiento, id_usuario_subio, estado)
        VALUES (:codigo, :id_categoria, :codigo_comunidad, :id_municipio, :mensaje,
                NOW(), :vigencia_horas, :fecha_vencimiento,
                :id_usuario_subio, 'ACTIVO')
        RETURNING *
    """, payload, f"El aviso '{payload['codigo']}'")
    return SuccessResponse(message="Aviso creado correctamente", data=result)


@router.put("/avisos/{id}", tags=[TAGS_PREDICCIONES_AVISOS],
            response_model=DataItemResponse[AvisoResponse],
            summary="Actualizar aviso de corto plazo")
def actualizar_aviso(id: UUID, data: AvisoUpdate, db: Session = Depends(get_db),
                     user=Depends(get_current_user)):
    """Actualizar mensaje/vigencia/estado de un aviso. Solo el autor."""
    _exigir_autor(db, "SELECT id_usuario_subio FROM sinb.avisos WHERE id = :id", id, user)
    result = service.update_aviso(db, id, data.model_dump(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="Aviso no encontrado")
    return SuccessResponse(message="Aviso actualizado correctamente", data=result)


@router.delete("/avisos/{id}", tags=[TAGS_PREDICCIONES_AVISOS])
def eliminar_aviso(id: UUID, db: Session = Depends(get_db),
                   user=Depends(get_current_user)):
    """Eliminar aviso **definitivamente** (borrado físico + registro de borrado). Solo el autor."""
    _exigir_autor(db, "SELECT id_usuario_subio FROM sinb.avisos WHERE id = :id", id, user)
    service.delete_aviso(db, id, user["id_usuario"])
    return {"message": "Aviso eliminado correctamente"}


# ============================================================================
# OBSERVADOR ÍNDICE (aciertos por usuario)
# ============================================================================

@router.get("/observador-indice", tags=[TAGS_OBSERVADORES],
            summary="Listar índices de observadores (aciertos)")
def listar_observadores_indice(
    skip: int = Query(0, ge=0),
    limit: int = Query(15, ge=1, le=100),
    todos: bool = Query(False, description="true = devolver todos sin LIMIT/OFFSET"),
    id_usuario: int | None = Query(None, description="Filtrar por usuario"),
    tipo: Literal["ESTACIONAL", "TEMPORAL"] | None = Query(
        None, description="Tipo de pronóstico: ESTACIONAL (largo plazo) o TEMPORAL (corto plazo)"),
    db: Session = Depends(get_db)
):
    """
    Listar observador_indice: mide aciertos de cada observador.
    
    - **tipo TEMPORAL**: índice del pronóstico de corto plazo (avisos, §6A)
    - **tipo ESTACIONAL**: índice del pronóstico de largo plazo (§6.4)
    - `limit`/`skip` paginan (los más recientes primero); `todos=true` devuelve todo.
    """
    params = {}
    # sinb.observador_indice no tiene columna `estado`: no se filtra por ella
    where = ["1 = 1"]

    if id_usuario:
        where.append("oi.id_usuario = :id_usuario")
        params["id_usuario"] = id_usuario
    if tipo:
        where.append("oi.tipo = CAST(:tipo AS sinb.tipo_pronostico)")
        params["tipo"] = tipo
    
    where_clause = " AND ".join(where)
    
    # cantidad → paginación; todos=True → sin LIMIT/OFFSET
    page = "" if todos else " LIMIT :limit OFFSET :skip"
    if not todos:
        params.update({"limit": limit, "skip": skip})

    data = service._rows(db, f"""
        SELECT oi.*, u.nombre as usuario_nombre, i.nombre_cientifico as indicador_nombre
        FROM sinb.observador_indice oi
        JOIN usuarios.usuario u ON u.id_usuario = oi.id_usuario
        LEFT JOIN sinb.indicador_natural i ON i.id = oi.id_indicador_natural
        WHERE {where_clause}
        ORDER BY oi.fecha_calculo DESC
        {page}
    """, params)
    
    return SuccessResponse(message="Índices listados", data=data)


@router.get("/observador-indice/{id}", tags=[TAGS_OBSERVADORES],
            response_model=DataItemResponse[ObservadorIndiceResponse],
            summary="Obtener índice de un observador por ID")
def obtener_observador_indice(id: UUID, db: Session = Depends(get_db)):
    """Obtener un registro de observador índice por su ID."""
    result = service.get_observador_indice(db, id)
    if not result:
        raise HTTPException(status_code=404, detail="Índice no encontrado")
    return SuccessResponse(message="Índice obtenido correctamente", data=result)


@router.post("/observador-indice", tags=[TAGS_OBSERVADORES], status_code=201)
def crear_observador_indice(data: ObservadorIndiceCreate, db: Session = Depends(get_db),
                            user=Depends(get_current_user)):
    """Crear registro de observador índice. Cualquier usuario autenticado.

    **id_usuario siempre se fuerza al usuario actual**: nadie puede registrar
    un índice en nombre de otra persona.
    """
    payload = data.model_dump()
    payload["id_usuario"] = user["id_usuario"]
    result = service._row(db, """
        INSERT INTO sinb.observador_indice 
        (id_usuario, id_indicador_natural, tipo, valor, fecha_calculo)
        VALUES (:id_usuario, :id_indicador_natural, CAST(:tipo AS sinb.tipo_pronostico),
                :valor, :fecha_calculo)
        ON CONFLICT (id_usuario, id_indicador_natural, tipo)
        DO UPDATE SET valor = :valor, fecha_calculo = :fecha_calculo
        RETURNING *
    """, payload)
    db.commit()
    return SuccessResponse(message="Índice creado correctamente",
                           data=service.get_observador_indice(db, result["id"]))


@router.put("/observador-indice/{id}", tags=[TAGS_OBSERVADORES],
            response_model=DataItemResponse[ObservadorIndiceResponse],
            summary="Actualizar índice de un observador")
def actualizar_observador_indice(id: UUID, data: ObservadorIndiceUpdate,
                                 db: Session = Depends(get_db),
                                 user=Depends(get_current_user)):
    """Actualizar valor/fecha de un índice. Solo el dueño del índice."""
    _exigir_autor(db, "SELECT id_usuario FROM sinb.observador_indice WHERE id = :id",
                  id, user, campo="id_usuario")
    result = service.update_observador_indice(db, id, data.model_dump(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="Índice no encontrado")
    return SuccessResponse(message="Índice actualizado correctamente", data=result)


@router.delete("/observador-indice/{id}", tags=[TAGS_OBSERVADORES])
def eliminar_observador_indice(id: UUID, db: Session = Depends(get_db),
                               user=Depends(get_current_user)):
    """Eliminar un índice. Solo el dueño del índice."""
    _exigir_autor(db, "SELECT id_usuario FROM sinb.observador_indice WHERE id = :id",
                  id, user, campo="id_usuario")
    service.delete_observador_indice(db, id, user["id_usuario"])
    return {"message": "Índice eliminado correctamente"}


# ============================================================================
# REPORTES ENRIQUECIDOS
# ============================================================================


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


# ============================================================================
# MAPAS GEOJSON
# ============================================================================

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
                    'total_pronosticos', COUNT(DISTINCT pe.id),
                    'ultima_emision', MAX(pe.fecha_emision),
                    'campos', ARRAY_AGG(DISTINCT cp.nombre)
                )
            ) as feature
        FROM sinb.pronostico_largo pe
        JOIN sinb.pronostico_largo_item pei ON pei.id_pronostico_largo = pe.id
        JOIN shared.municipio m ON m.id = pe.id_municipio
        JOIN shared.provincia p ON p.id = m.id_provincia
        JOIN shared.departamento d ON d.id = p.id_departamento
        JOIN sinb.categoria_pronostico cp ON cp.id = pei.id_categoria
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
    todos: bool = Query(False, description="true = devolver todos sin LIMIT/OFFSET"),
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
    - Los datos se actualizan automáticamente 2 veces al día (06:00 y 18:00 hora de Bolivia)
    - Horizonte: 16 días (hoy inclusive); sin `fecha_hasta` se devuelve exactamente ese tramo
    - Filtros se aplican según el rol del usuario (scope geográfico)
    - Paginación: skip/limit (default 100 registros); `todos=true` devuelve todo
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
        limit=limit,
        todos=todos
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
    
    **Variables disponibles:**
    - Temperatura: máx, mín
    - Precipitación: suma, probabilidad máx
    - Humedad relativa: máx, mín
    - Evapotranspiración FAO ET₀
    - Viento: velocidad máx, dirección dominante
    - Radiación solar
    - Índice UV máx
    - Amanecer/atardecer
    
    **Actualización:** 2 veces al día (06:00 y 18:00) desde Open-Meteo.
    **Horizonte:** 16 días desde hoy.
    """
    # Usar el método de histórico con filtros
    filtros = {"id_municipio": id_municipio}
    if fecha_desde:
        filtros["fecha_desde"] = fecha_desde
    if fecha_hasta:
        filtros["fecha_hasta"] = fecha_hasta
    if not fecha_desde and not fecha_hasta:
        # Sin fechas: ventana exacta de pronóstico (hoy..hoy+15). Para ver la
        # evidencia de días pasados usar /pronostico-diario/historico con fechas.
        hoy = service._hoy_bolivia()
        filtros["fecha_desde"] = hoy
        filtros["fecha_hasta"] = hoy + timedelta(days=service.HORIZONTE_DIAS - 1)
    
    data, total = service.get_pronostico_diario_historico(db, filtros, pagina=1, por_pagina=100)
    
    return SuccessResponse(
        message=f"Pronóstico obtenido ({len(data)} registros)",
        data=data
    )


@router.get("/pronostico-diario/historico",
             tags=[TAGS_PREDICCIONES_DIGITALES],
             summary="Consultar histórico de pronóstico diario con filtros")
def get_pronostico_diario_historico(
    id_municipio: int = Query(None, description="Filtrar por municipio"),
    codigo_comunidad: str = Query(None, description="Filtrar por código de comunidad"),
    fecha_desde: date = Query(None, description="Fecha desde"),
    fecha_hasta: date = Query(None, description="Fecha hasta"),
    temp_max_min: float = Query(None, ge=-50, le=50, description="Temperatura máxima mínima"),
    temp_max_max: float = Query(None, ge=-50, le=50, description="Temperatura máxima máxima"),
    precipitacion_min: float = Query(None, ge=0, description="Precipitación mínima"),
    precipitacion_max: float = Query(None, ge=0, description="Precipitación máxima"),
    pagina: int = Query(1, ge=1, description="Número de página"),
    por_pagina: int = Query(50, ge=1, le=500, description="Registros por página"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """
    Consultar histórico de pronóstico diario almacenado en BD.
    
    **Filtros disponibles:**
    - Geográficos: municipio, comunidad
    - Fecha: fecha_desde, fecha_hasta
    - Datos meteorológicos: temp_max, precipitación
    
    **Paginación:**
    - pagina: Número de página (default 1)
    - por_pagina: Registros por página (default 50, max 500)
    
    **Sin filtros:** Retorna últimos 16 días de todos los municipios.
    
    **Nota:** Datos actualizados 2 veces al día (06:00 y 18:00) desde Open-Meteo.
    """
    filtros = {
        "id_municipio": id_municipio,
        "codigo_comunidad": codigo_comunidad,
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,
        "temp_max_min": temp_max_min,
        "temp_max_max": temp_max_max,
        "precipitacion_min": precipitacion_min,
        "precipitacion_max": precipitacion_max
    }
    
    # Filtrar campos None
    filtros = {k: v for k, v in filtros.items() if v is not None}
    
    data, total = service.get_pronostico_diario_historico(
        db, filtros, pagina, por_pagina
    )
    
    total_paginas = (total + por_pagina - 1) // por_pagina if total > 0 else 0
    
    return SuccessResponse(
        message=f"Histórico obtenido ({len(data)} de {total} registros)",
        data=data,
        total=total,
        pagina=pagina,
        por_pagina=por_pagina,
        total_paginas=total_paginas
    )


@router.get("/pronostico-digital/consultar",
             tags=[TAGS_PREDICCIONES_DIGITALES],
             summary="Consultar pronóstico digital (1 municipio × 16 días o TODOS × 16 días)")
def consultar_pronostico_digital(
    id_municipio: int | None = Query(None, description="ID del municipio (omitir para TODOS)"),
    tipo: Literal["daily", "hourly"] = Query("daily", description="Tipo de pronóstico"),
    todos_los_dias: bool = Query(True, description="¿Traer 16 días o solo hoy? (default: True)"),
    db: Session = Depends(get_db)
):
    """
    Consultar pronóstico digital almacenado en BD.
    
    **Tres modos de uso:**
    
    1. **UN municipio × 16 días:** `?id_municipio=41503`
       - Retorna 16 días desde hoy para ese municipio
       - Ideal para vista de detalle
    
    2. **TODOS × 16 días:** (omitir id_municipio, todos_los_dias=True)
       - Retorna 343 municipios × 16 días = 5,488 registros
       - Ideal para mapas con línea de tiempo
       - Incluye coordenadas para geolocalización
    
    3. **TODOS × solo hoy:** `?todos_los_dias=False`
       - Retorna 343 municipios × 1 día (hoy)
       - Ideal para mapa estático rápido
    
    **Importante:**
    - Datos actualizados 2 veces/día (06:00 y 18:00)
    - Fuente: Open-Meteo (almacenado en BD local)
    """
    from datetime import date as date_type
    
    if id_municipio is None:
        # Modo TODOS LOS MUNICIPIOS
        if todos_los_dias:
            # TODOS × 16 DÍAS
            data = service.get_pronostico_todos_municipios_16dias(db)
            return SuccessResponse(
                message=f"Pronóstico completo obtenido ({len(data)} registros = 343 municipios × 16 días)",
                data=data,
                total_registros=len(data),
                total_municipios=343,
                dias_por_municipio=16,
                tipo="mapa_completo"
            )
        else:
            # TODOS × SOLO HOY
            fecha_consulta = service._hoy_bolivia()
            data = service.get_pronostico_todos_municipios(db, fecha_consulta)
            
            return SuccessResponse(
                message=f"Pronóstico de mapa obtenido ({len(data)} municipios)",
                data=data,
                total_municipios=len(data),
                fecha_consulta=fecha_consulta,
                tipo="mapa_hoy"
            )
    else:
        # Modo UN MUNICIPIO × 16 DÍAS
        data, municipio_nombre, fecha_hoy = service.get_pronostico_diario_consultar(
            db, id_municipio, tipo
        )
        
        if not data:
            return SuccessResponse(
                message="No hay datos disponibles para este municipio",
                data=[],
                id_municipio=id_municipio,
                tipo=tipo,
                fecha_consulta=fecha_hoy,
                dias_disponibles=0
            )
        
        return SuccessResponse(
            message=f"Pronóstico obtenido ({len(data)} días desde {fecha_hoy})",
            data=data,
            id_municipio=id_municipio,
            municipio=municipio_nombre,
            tipo=tipo,
            fecha_consulta=fecha_hoy,
            dias_disponibles=len(data)
        )

@router.get("/pronostico-comunidad/{codigo_ine}",
             tags=[TAGS_PREDICCIONES_DIGITALES],
             summary="Consultar pronóstico para una comunidad por su código INE")
def get_pronostico_comunidad(
    codigo_ine: str = Path(..., description="Código INE de la comunidad"),
    db: Session = Depends(get_db)
):
    """
    Consultar pronóstico para una comunidad específica.
    
    **Parámetros:**
    - `codigo_ine`: Código INE de la comunidad (ej: '02417371843-M')
    
    **Retorna:**
    - 16 días de pronóstico desde hoy
    - Mismo formato que endpoint de municipio
    - Incluye coordenadas y nombre de la comunidad
    
    **Flujo:**
    1. Validar que el código INE existe en `shared.comunidades`
    2. Obtener lat/lon y id_municipio de la comunidad
    3. Consultar pronóstico usando las coordenadas
    4. Retornar 16 días con todas las variables agrícolas
    """
    from datetime import date as date_type
    
    # 1. Validar que la comunidad existe
    comunidad = _row(db, """
        SELECT codigo_ine, nombre, lat, lon, id_municipio
        FROM shared.comunidades
        WHERE codigo_ine = :codigo_ine
    """, {"codigo_ine": codigo_ine})
    
    if not comunidad:
        raise HTTPException(
            status_code=404,
            detail=f"Comunidad con código INE '{codigo_ine}' no encontrada"
        )
    
    # 2. Obtener datos de la comunidad
    cod_ine = comunidad['codigo_ine']
    nombre_comunidad = comunidad['nombre']
    lat_comunidad = comunidad['lat']
    lon_comunidad = comunidad['lon']
    id_municipio = comunidad['id_municipio']
    
    # 3. Consultar pronóstico DIRECTO de Open-Meteo (NO guarda en BD)
    # Las comunidades no están en el cron, así que consultamos directamente
    data, municipio_nombre, fecha_hoy = service.get_pronostico_comunidad_directo(
        db, lat_comunidad, lon_comunidad, id_municipio
    )
    
    # Agregar metadatos de comunidad a cada registro (misma estructura que municipio)
    for item in data:
        item["comunidad_nombre"] = nombre_comunidad
        item["codigo_ine"] = cod_ine
    
    return SuccessResponse(
        message=f"Pronóstico para comunidad '{nombre_comunidad}' (16 días desde {fecha_hoy})",
        data=data
    )


@router.get("/pronostico-comunidad",
             tags=[TAGS_PREDICCIONES_DIGITALES],
             summary="Consultar pronóstico para comunidad por coordenadas")
def get_pronostico_comunidad_coordenadas(
    latitud: float = Query(..., ge=-90, le=90, description="Latitud de la comunidad"),
    longitud: float = Query(..., ge=-180, le=180, description="Longitud de la comunidad"),
    db: Session = Depends(get_db)
):
    """
    Consultar pronóstico para una comunidad usando coordenadas geográficas.
    
    **Parámetros:**
    - `latitud`: Latitud decimal (ej: -18.5)
    - `longitud`: Longitud decimal (ej: -68.5)
    
    **Flujo:**
    1. Validar que las coordenadas están en Bolivia
    2. Buscar comunidad más cercana en `shared.comunidades`
    3. Obtener id_municipio de la comunidad más cercana
    4. Consultar pronóstico usando las coordenadas
    5. Retornar 16 días con todas las variables
    """
    from datetime import date as date_type
    from sqlalchemy import text
    
    # 1. Buscar comunidad más cercana a las coordenadas
    comunidad = _row(db, """
        SELECT codigo_ine, nombre, lat, lon, id_municipio,
               ST_Distance(
                   ST_SetSRID(ST_MakePoint(:lon, :lat), 4326),
                   geom
               ) as distancia
        FROM shared.comunidades
        ORDER BY distancia
        LIMIT 1
    """, {"lon": longitud, "lat": latitud})
    
    if not comunidad:
        raise HTTPException(
            status_code=404,
            detail="No se encontró comunidad cercana a las coordenadas proporcionadas"
        )
    
    # 2. Obtener datos de la comunidad
    cod_ine = comunidad['codigo_ine']
    nombre_comunidad = comunidad['nombre']
    lat_comunidad = comunidad['lat']
    lon_comunidad = comunidad['lon']
    id_municipio = comunidad['id_municipio']
    
    # 3. Consultar pronóstico DIRECTO de Open-Meteo (NO guarda en BD)
    data, municipio_nombre, fecha_hoy = service.get_pronostico_comunidad_directo(
        db, latitud, longitud, id_municipio
    )
    
    # Agregar metadatos de comunidad a cada registro (misma estructura que municipio)
    for item in data:
        item["comunidad_nombre"] = nombre_comunidad
        item["codigo_ine"] = cod_ine
    
    return SuccessResponse(
        message=f"Pronóstico para comunidad '{nombre_comunidad}' (16 días desde {fecha_hoy})",
        data=data
    )


# ============================================================================
# MAPA DE PRONÓSTICOS (TODOS LOS MUNICIPIOS)
# ============================================================================

@router.get("/pronostico-digital/mapa",
             tags=[TAGS_PREDICCIONES_DIGITALES],
             summary="Obtener pronóstico de TODOS los municipios para mapa (16 días)")
def get_pronostico_mapa(
    fecha: date = Query(None, description="Fecha inicial (hoy por defecto)"),
    todos_los_dias: bool = Query(True, description="¿Traer 16 días o solo 1 día?"),
    db: Session = Depends(get_db)
):
    """
    Obtener pronóstico de TODOS los 343 municipios para visualizar en mapa.
    
    **Dos modos:**
    
    1. **16 días:** `?todos_los_dias=true` (default)
       - 343 municipios × 16 días = 5,488 registros
       - Ideal para mapa con línea de tiempo
    
    2. **Solo 1 día:** `?todos_los_dias=false&fecha=2026-10-05`
       - 343 municipios × 1 día = 343 registros
       - Ideal para mapa estático rápido
    
    **Variables incluidas:**
    - Temperatura máx/mín
    - Precipitación
    - Humedad (máx/mín)
    - Evapotranspiración
    - Viento (velocidad y dirección)
    - Radiación solar
    - UV index
    - Coordenadas (latitud, longitud)
    """
    from datetime import date as date_type
    
    if todos_los_dias:
        data = service.get_pronostico_todos_municipios_16dias(db)
        
        return SuccessResponse(
            message=f"Pronóstico de mapa completo ({len(data)} registros)",
            data=data,
            total_registros=len(data),
            total_municipios=343,
            dias_por_municipio=16,
            tipo="mapa_completo"
        )
    else:
        fecha_consulta = fecha if fecha else service._hoy_bolivia()
        data = service.get_pronostico_todos_municipios(db, fecha_consulta)
        
        return SuccessResponse(
            message=f"Pronóstico de mapa ({len(data)} municipios)",
            data=data,
            total_municipios=len(data),
            fecha_consulta=fecha_consulta,
            tipo="mapa_hoy"
        )


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
             summary="Actualizar pronóstico diario de municipio (uso cron)")
def actualizar_pronostico_municipio(
    id_municipio: int = Path(..., description="ID del municipio"),
    latitud: float = Query(..., description="Latitud del centroide"),
    longitud: float = Query(..., description="Longitud del centroide"),
    db: Session = Depends(get_db)
):
    """
    Actualizar pronóstico diario para un municipio (16 días).
    
    **Endpoint sin autenticación para uso desde cron** (06:00 y 18:00 hora de Bolivia).
    
    **Reintentos:** 3 intentos con espera exponencial (2/4/8 s) sobre la consulta a
    Open-Meteo, dentro de `guardar_pronostico_diario_municipal`.
    """
    try:
        resultado = service.guardar_pronostico_diario_municipal(
            db, id_municipio, latitud, longitud, service._hoy_bolivia()
        )
    except HTTPException as e:
        if e.status_code == 503:
            raise HTTPException(status_code=503,
                                detail=f"Error después de 3 reintentos: {e.detail}")
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Error después de 3 reintentos: {str(e)}")

    return SuccessResponse(
        message=f"Pronóstico actualizado ({resultado['registros_guardados']} días)",
        data=resultado
    )



# ============================================================================
# FOTOS DE INDICADOR NATURAL (1:N con sinb.indicador_natural)
# ============================================================================

def _autorizar_foto(foto: dict, user: dict):
    """Estricto: solo el autor de la foto puede modificarla o eliminarla."""
    autorizar_propietario(foto, user, "id_usuario_subio")


@router.get("/indicador-natural/{id}/fotos", tags=[TAGS_CATALOGOS],
            response_model=DataListResponse[IndicadorFotoResponse],
            summary="Listar fotos de un indicador natural")
def listar_fotos_indicador(
    id: UUID,
    limit: int | None = Query(None, ge=1, description="Registros por página. Sin valor: sin límite"),
    skip: int = Query(0, ge=0, description="Registros a saltar"),
    todos: bool = Query(False, description="true = devolver todos sin LIMIT/OFFSET"),
    db: Session = Depends(get_db),
):
    """Fotos del indicador natural, más recientes primero."""
    if not service.get_indicador_natural(db, id):
        raise HTTPException(status_code=404, detail="Indicador no encontrado")
    data, total = service.get_fotos_indicador(db, id, limit=limit, skip=skip, todos=todos)
    return SuccessResponse(message="Fotos listadas correctamente", data=data, total=total)


@router.post("/indicador-natural/{id}/fotos", tags=[TAGS_CATALOGOS],
             status_code=201,
             response_model=DataItemResponse[IndicadorFotoResponse],
             summary="Subir foto a un indicador natural")
async def crear_foto_indicador(
    id: UUID,
    file: UploadFile = File(..., description="Imagen JPG, PNG, WEBP, GIF, BMP, TIFF o HEIC (máx. 10 MB)"),
    descripcion: str = Form(..., max_length=500, description="Descripción de la foto"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Sube una foto y la asocia al indicador. Cualquier usuario autenticado."""
    if not service.get_indicador_natural(db, id):
        raise HTTPException(status_code=404, detail="Indicador no encontrado")

    path = await save_upload_file(file, db, user.get("id_municipio"), user.get("id_usuario"))
    try:
        foto = service.create_foto_indicador(db, id, path, descripcion, user["id_usuario"])
    except Exception:
        delete_file_from_server(path)
        raise

    return SuccessResponse(message="Foto subida correctamente",
                           data=service.get_foto_indicador(db, foto["id"]))


@router.put("/indicador-natural/{id}/fotos/{id_foto}", tags=[TAGS_CATALOGOS],
            response_model=DataItemResponse[IndicadorFotoResponse],
            summary="Actualizar descripción de una foto")
def actualizar_foto_indicador(
    id: UUID,
    id_foto: UUID,
    data: IndicadorFotoUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Solo el autor de la foto puede editarla."""
    foto = service.get_foto_indicador(db, id_foto)
    if not foto or foto["id_indicador_natural"] != id:
        raise HTTPException(status_code=404, detail="Foto no encontrada")
    _autorizar_foto(foto, user)

    service.update_foto_indicador(db, id_foto, data.descripcion)
    return SuccessResponse(message="Foto actualizada correctamente",
                           data=service.get_foto_indicador(db, id_foto))


@router.delete("/indicador-natural/{id}/fotos/{id_foto}", tags=[TAGS_CATALOGOS],
               summary="Eliminar una foto (fila y archivo físico)")
def eliminar_foto_indicador(
    id: UUID,
    id_foto: UUID,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Solo el autor de la foto puede eliminarla."""
    foto = service.get_foto_indicador(db, id_foto)
    if not foto or foto["id_indicador_natural"] != id:
        raise HTTPException(status_code=404, detail="Foto no encontrada")
    _autorizar_foto(foto, user)

    service.delete_foto_indicador(db, id_foto, user["id_usuario"])
    delete_file_from_server(foto["path_foto"])
    return SuccessResponse(message="Foto eliminada correctamente")
