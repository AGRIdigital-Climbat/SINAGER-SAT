from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user
from ..response import SuccessResponse, DataListResponse, DataItemResponse
from ..auth.permisos import module_permiso
from ..edan.utils import require_rol, db_error
from . import service
from .schemas import EventoRidaResponse, LocalidadEventoResponse, CatEstadoEventoResponse

router = APIRouter(
    prefix="/rida",
    dependencies=[Depends(module_permiso("RIDA"))],
)

TAG_PADRES = "RIDA > Padres"
TAG_HIJOS = "RIDA > Hijos"
TAG_EMPADRONAMIENTO = "RIDA > Empadronamiento"
TAG_BUSQUEDA = "RIDA > Búsqueda"

# Habilitan/cierran el evento: Admin (1-2) y DGR/VIDECI departamental (5/9).
ROLES_GESTION_EVENTO = (1, 2, 5, 6, 9)


@router.get("/evento/cat-estado-evento", tags=[TAG_EMPADRONAMIENTO],
            response_model=DataListResponse[CatEstadoEventoResponse],
            summary="Estados de evento RIDA",
            description="Catálogo rida.cat_estado_evento: HABILITADO(1), CERRADO(2).")
def listar_cat_estado_evento(db: Session = Depends(get_db)):
    rows = service._rows(
        db,
        "SELECT id_estado_evento, codigo, nombre FROM rida.cat_estado_evento ORDER BY orden, id_estado_evento",
        {},
    )
    return SuccessResponse(message="Estados de evento listados correctamente", data=[dict(r) for r in rows],
                           total=len(rows))


@router.get("/eventos", tags=[TAG_PADRES], response_model=DataListResponse[EventoRidaResponse],
            summary="Listar eventos RIDA (padres)",
            description="Lista paginada de eventos RIDA con desglose del EDAN padre:\n"
                        "- tipo de evento, fecha y hora del evento,\n"
                        "- geografía hasta municipio,\n"
                        "- número y nombres de las localidades,\n"
                        "- usuario alcalde y usuario UGR.\n"
                        "Scope: 5/8/9 restringidos a su departamento/municipio; 6/7 a su geografía; 1-4 todo.")
def listar_eventos(
    id_edan: int | None = Query(None, description="Filtrar por EDAN"),
    id_estado: int | None = Query(None, description="1=HABILITADO, 2=CERRADO"),
    id_departamento: int | None = Query(None, description="Filtrar por departamento"),
    id_provincia: int | None = Query(None, description="Filtrar por provincia"),
    id_municipio: int | None = Query(None, description="Filtrar por municipio"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    todos: bool = Query(False, description="Devolver todos los eventos sin paginar"),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        data, total = service.listar_eventos(db, _user, {
            "id_edan": id_edan, "id_estado": id_estado,
            "id_departamento": id_departamento, "id_provincia": id_provincia,
            "id_municipio": id_municipio,
        }, skip=skip, limit=limit, todos=todos)
        return SuccessResponse(message="Eventos RIDA listados correctamente", data=data, total=total)
    except Exception as e:
        raise db_error(e)


@router.get("/edan-aprobados", tags=[TAG_PADRES],
            response_model=DataListResponse[dict],
            summary="Listar EDAN aprobados para habilitar RIDA",
            description="Lista EDAN con estado APROBADO (3 ó 5) con filtros geográficos jerárquicos.\n\n"
                        "Cada EDAN viene **marcado** con:\n"
                        "- `rida_habilitado`: true si ya tiene un evento RIDA activo.\n"
                        "- `puede_habilitar`: true si aún no tiene RIDA o su evento fue anulado.\n"
                        "- `evento_estado_codigo` / `evento_estado_nombre`: HABILITADO/CERRADO.\n"
                        "- `id_evento_rida`, `fecha_habilitacion`, `fecha_cierre`.\n\n"
                        "Los EDAN con RIDA habilitado se ordenan primero.\n"
                        "Scope geográfico aplica según rol del usuario.")
def listar_edan_aprobados(
    id_edan: int | None = Query(None, description="Filtrar por EDAN"),
    id_departamento: int | None = Query(None, description="Filtrar por departamento"),
    id_provincia: int | None = Query(None, description="Filtrar por provincia"),
    id_municipio: int | None = Query(None, description="Filtrar por municipio"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    todos: bool = Query(False, description="Devolver todos los EDAN sin paginar"),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        data, total = service.listar_edan_aprobados(db, _user, {
            "id_edan": id_edan,
            "id_departamento": id_departamento,
            "id_provincia": id_provincia,
            "id_municipio": id_municipio,
        }, skip=skip, limit=limit, todos=todos)
        return SuccessResponse(message="EDAN aprobados listados correctamente", data=data, total=total)
    except Exception as e:
        raise db_error(e)


@router.get("/evento/{id_evento_rida}", tags=[TAG_PADRES], response_model=DataItemResponse[EventoRidaResponse],
            summary="Evento RIDA (padre) con localidades",
            description="Detalle del evento con su EDAN padre desglosado y sus localidades (hijos).")
def obtener_evento(
    id_evento_rida: int,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    service._validar_scope_evento(db, _user, id_evento_rida)
    result = service.get_evento(db, id_evento_rida)
    if not result:
        raise HTTPException(status_code=404, detail="Evento RIDA no encontrado")
    return SuccessResponse(message="Evento RIDA obtenido correctamente", data=result)


@router.get("/evento/{id_evento_rida}/localidades", tags=[TAG_HIJOS],
            response_model=DataListResponse[LocalidadEventoResponse],
            summary="Localidades de un evento RIDA (hijos)",
            description="Lista las localidades del EDAN del evento con su formulario de empadronamiento "
                        "(si existe), nombre de localidad, geografía, estado y conteos consolidados de "
                        "familias/integrantes/necesidades. Paginada; `todos=true` devuelve todas.")
def obtener_evento_localidades(
    id_evento_rida: int,
    id_departamento: int | None = Query(None, description="Filtrar por departamento"),
    id_provincia: int | None = Query(None, description="Filtrar por provincia"),
    id_municipio: int | None = Query(None, description="Filtrar por municipio"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    todos: bool = Query(False, description="Devolver todas las localidades sin paginar"),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    service._validar_scope_evento(db, _user, id_evento_rida)
    if not service.get_evento(db, id_evento_rida):
        raise HTTPException(status_code=404, detail="Evento RIDA no encontrado")
    geo_filtros = {
        "id_departamento": id_departamento,
        "id_provincia": id_provincia,
        "id_municipio": id_municipio,
    }
    data, total = service.localidades_evento_paginado(db, id_evento_rida, geo_filtros=geo_filtros, skip=skip, limit=limit, todos=todos)
    return SuccessResponse(message="Localidades listadas correctamente", data=data, total=total)


@router.post("/evento/{id_edan}/habilitar", tags=[TAG_PADRES], status_code=201,
             response_model=DataItemResponse[EventoRidaResponse],
             dependencies=[Depends(require_rol(*ROLES_GESTION_EVENTO))],
             summary="Habilitar evento RIDA (padre)",
             description="Crea el evento RIDA (padre) a partir del EDAN aprobado y auto-crea los HIJO:\n"
                         "un formulario de empadronamiento por cada localidad del EDAN (estado PENDIENTE).\n"
                         "Error 400 si el EDAN no está aprobado o ya tiene evento RIDA.")
def habilitar_evento(
    id_edan: int,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        service._validar_geo_edan(db, _user, id_edan)
        result = service.habilitar_evento(db, id_edan, _user["id_usuario"])
        return SuccessResponse(message="Evento RIDA habilitado correctamente", data=result)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise db_error(e)


@router.post("/evento/{id_evento_rida}/cerrar", tags=[TAG_PADRES], status_code=200,
             response_model=DataItemResponse[EventoRidaResponse],
             dependencies=[Depends(require_rol(*ROLES_GESTION_EVENTO))],
             summary="Cerrar evento RIDA",
             description="Marca el evento RIDA como CERRADO con auditoría (quién/cuándo).")
def cerrar_evento(
    id_evento_rida: int,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        service._validar_scope_evento(db, _user, id_evento_rida)
        result = service.cerrar_evento(db, id_evento_rida, _user["id_usuario"])
        return SuccessResponse(message="Evento RIDA cerrado correctamente", data=result)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise db_error(e)


@router.post("/evento/{id_evento_rida}/anular", tags=[TAG_PADRES], status_code=200,
             response_model=DataItemResponse[EventoRidaResponse],
             dependencies=[Depends(require_rol(*ROLES_GESTION_EVENTO))],
             summary="Anular evento RIDA (habilitado por error)",
             description="Anula un evento RIDA que fue habilitado por error. "
                        "Solo se pueden anular eventos en estado HABILITADO.")
def anular_evento(
    id_evento_rida: int,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        service._validar_scope_evento(db, _user, id_evento_rida)
        result = service.anular_evento(db, id_evento_rida, _user["id_usuario"])
        return SuccessResponse(message="Evento RIDA anulado correctamente", data=result)
    except HTTPException:
        raise
    except Exception as e:
        raise db_error(e)
