from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user
from ..response import SuccessResponse, DataListResponse, DataItemResponse
from ..auth.permisos import module_permiso
from ..edan.utils import require_rol, db_error
from . import service
from .schemas import (EventoRidaResponse, LocalidadEventoResponse,
                      CatEstadoEventoResponse, DeshabilitarEventoResponse,
                      EventoReporteResponse, EventoIntegrantesResponse)

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
            description="Catálogo rida.cat_estado_evento: HABILITADO(1), HABILITAR(2), "
                        "EN PROCESO(3), ATENDIDO(4), CERRADO(5).")
def listar_cat_estado_evento(db: Session = Depends(get_db)):
    rows = service._rows(
        db,
        "SELECT id_estado_evento, codigo, nombre FROM rida.cat_estado_evento ORDER BY orden, id_estado_evento",
        {},
    )
    return SuccessResponse(message="Estados de evento listados correctamente", data=[dict(r) for r in rows],
                           total=len(rows))


@router.get("/evento/reporte", tags=[TAG_PADRES],
            response_model=DataItemResponse[EventoReporteResponse],
            summary="Reporte consolidado por código RIDA (query param)",
            description="Mismo reporte que `GET /evento/{identificador}/reporte` pero el código "
                        "RIDA se pasa como query param `?codigo=` — el código contiene `/` "
                        "(ej. `070101/2026/002-R`) que no puede viajar limpio en el path. "
                        "También acepta `?id=` numérico. Sin coincidencia → 404.")
def obtener_evento_reporte_por_codigo(
    codigo: str | None = Query(None, description="Código RIDA (ej. 070101/2026/002-R)"),
    id: int | None = Query(None, description="id numérico del evento"),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    identificador = codigo if codigo else id
    if identificador is None:
        raise HTTPException(status_code=422, detail="Se requiere ?codigo= o ?id=")
    data = service.get_evento_reporte(db, identificador, user=_user)
    if not data:
        raise HTTPException(status_code=404,
                            detail="Evento RIDA no encontrado (id o código inválido)")
    return SuccessResponse(message="Reporte de evento RIDA generado correctamente", data=data)


@router.get("/evento/integrantes", tags=[TAG_PADRES],
            response_model=DataItemResponse[EventoIntegrantesResponse],
            summary="Listado de integrantes por lugar (query param)",
            description="Mismo listado que `GET /evento/{identificador}/integrantes` pero el "
                        "código RIDA se pasa como query param `?codigo=` — el código contiene "
                        "`/` (ej. `070101/2026/002-R`) que no puede viajar limpio en el path. "
                        "También acepta `?id=` numérico. Sin coincidencia → 404. "
                        "Consulta puntual: no pagina.")
def obtener_evento_integrantes_por_codigo(
    codigo: str | None = Query(None, description="Código RIDA (ej. 070101/2026/002-R)"),
    id: int | None = Query(None, description="id numérico del evento"),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    identificador = codigo if codigo else id
    if identificador is None:
        raise HTTPException(status_code=422, detail="Se requiere ?codigo= o ?id=")
    data = service.get_evento_integrantes(db, identificador, user=_user)
    if not data:
        raise HTTPException(status_code=404,
                            detail="Evento RIDA no encontrado (id o código inválido)")
    return SuccessResponse(message="Listado de integrantes generado correctamente", data=data)


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
    codigo: str | None = Query(None, description="Filtrar por código RIDA (ej. 070101/2026/002-R, "
                                                 "sin distinguir mayúsculas)"),
    id_estado: int | None = Query(None, description="id del catálogo: 1=HABILITADO, …, 5=CERRADO"),
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
            "id_edan": id_edan, "codigo": codigo, "id_estado": id_estado,
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
                        "- `puede_habilitar`: true si aún no tiene evento RIDA (deshabilitar borra el registro y libera el EDAN).\n"
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


@router.get("/evento/{identificador}/reporte", tags=[TAG_PADRES],
            response_model=DataItemResponse[EventoReporteResponse],
            summary="Reporte consolidado de un evento RIDA",
            description="Empadronamiento consolidado del evento, localizable por **id** "
                        "numérico o por **código RIDA** (ej. `070101/2026/002-R`, sin "
                        "distinguir mayúsculas). Sin coincidencia → 404.\n\n"
                        "Orden del JSON:\n"
                        "1. `evento` — datos del evento RIDA (código, estado, fechas).\n"
                        "2. `edan` — EDAN padre: código, fecha/tipo de evento, geografía, "
                        "**`levantaron`** (quién creó las localidades + importador si aplica), "
                        "**`ugr`**, **`alcalde`** y población declarada.\n"
                        "3. `resumen` — **total del evento** con las 3 secciones:\n"
                        "   `poblacion_por_grupo_etario`, "
                        "`capacidades_especiales_por_grupo_etario` (gestantes, lactantes, "
                        "discapacidad y enfermedad por grupo, con desglose por tipo) y "
                        "`necesidades_por_familia` (agrupadas por categoría de ayuda, sin "
                        "costos), más `familias`, `integrantes` e "
                        "`integrantes_por_familia` (promedio/mínimo/máximo) y totales de "
                        "necesidades.\n"
                        "4. `formularios` — cada `formulario_rida` (= localidad del EDAN) "
                        "con sus datos de cabecera y **las mismas 3 secciones** para esa "
                        "localidad.\n\n"
                        "Las edades se calculan **a la fecha del empadronamiento** "
                        "(fecha de alta del integrante). Consulta puntual: no pagina.")
def obtener_evento_reporte(
    identificador: str = Path(..., description="id del evento (numérico) o código RIDA"),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    data = service.get_evento_reporte(db, identificador, user=_user)
    if not data:
        raise HTTPException(status_code=404,
                            detail="Evento RIDA no encontrado (id o código inválido)")
    return SuccessResponse(message="Reporte de evento RIDA generado correctamente", data=data)


@router.get("/evento/{identificador}/integrantes", tags=[TAG_PADRES],
            response_model=DataItemResponse[EventoIntegrantesResponse],
            summary="Listado de integrantes del evento por lugar",
            description="Devuelve TODOS los integrantes (personas) del evento RIDA agrupados "
                        "por lugar (localidad del EDAN), sin paginar.\n\n"
                        "1. `evento` / `edan` — cabecera igual que el reporte consolidado.\n"
                        "2. `resumen` — totales: localidades, familias, integrantes, "
                        "masculino/femenino/sin_sexo, población por grupo etario, "
                        "discapacidades, enfermedades, gestantes y lactantes.\n"
                        "3. `localidades` — un bloque por lugar con sus ids de rastreo "
                        "(`id_edan_localidad`, `id_tipo_localidad`, `localidad`, "
                        "`id_formulario`) y sus `personas` **ordenadas por apellido**.\n\n"
                        "Por cada persona: documento (nro. y tipo), nombre y apellido, sexo "
                        "(M/F con etiqueta), fecha de nacimiento y edad, grupo etario, "
                        "parentesco y si es jefe de hogar, y condición especial "
                        "(discapacidad, enfermedad crónica, semanas de gestante y meses de "
                        "lactante).\n\n"
                        "Las edades se calculan **a la fecha del empadronamiento** (mismos "
                        "criterios que el reporte). Consulta puntual: no pagina. "
                        "Si no se ha empadronado una localidad viene con `personas: []`.")
def obtener_evento_integrantes(
    identificador: str = Path(..., description="id del evento (numérico) o código RIDA"),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    data = service.get_evento_integrantes(db, identificador, user=_user)
    if not data:
        raise HTTPException(status_code=404,
                            detail="Evento RIDA no encontrado (id o código inválido)")
    return SuccessResponse(message="Listado de integrantes generado correctamente", data=data)


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


@router.post("/evento/{id_evento_rida}/atender", tags=[TAG_PADRES], status_code=200,
             response_model=DataItemResponse[EventoRidaResponse],
             dependencies=[Depends(require_rol(*ROLES_GESTION_EVENTO))],
             summary="Marcar evento RIDA como ATENDIDO",
             description="Ciclo de vida del evento: HABILITADO → (primer registro de empadronamiento) "
                         "→ EN PROCESO (automático) → **ATENDIDO** (solo vía esta API) → CERRADO "
                         "(solo vía la API cerrar). Error 400 si no está EN PROCESO o si ya está CERRADO.")
def atender_evento(
    id_evento_rida: int,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        service._validar_scope_evento(db, _user, id_evento_rida)
        result = service.atender_evento(db, id_evento_rida, _user["id_usuario"])
        return SuccessResponse(message="Evento RIDA marcado como ATENDIDO", data=result)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise db_error(e)


@router.post("/evento/{id_evento_rida}/cerrar", tags=[TAG_PADRES], status_code=200,
             response_model=DataItemResponse[EventoRidaResponse],
             dependencies=[Depends(require_rol(*ROLES_GESTION_EVENTO))],
             summary="Cerrar evento RIDA",
             description="Marca el evento RIDA como CERRADO (terminal): llena `id_usuario_cierro` y "
                         "`fecha_cierre` con la **hora automática del sistema de Bolivia** "
                         "(America/La_Paz). Solo desde EN PROCESO o ATENDIDO (un evento HABILITADO "
                         "sin registros no se cierra). Sin body. Error 400 si ya está cerrado.")
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


@router.post("/evento/{id_evento_rida}/deshabilitar", tags=[TAG_PADRES], status_code=200,
             response_model=DataItemResponse[DeshabilitarEventoResponse],
             dependencies=[Depends(require_rol(*ROLES_GESTION_EVENTO))],
             summary="Deshabilitar evento RIDA (habilitado por error)",
             description="Lo contrario de habilitar: borra físicamente el evento y sus formularios "
                         "auto-creados, dejando el EDAN libre para volver a habilitar.\n"
                         "Error 400 si el evento está CERRADO o si algún formulario ya tiene datos "
                         "(familias, necesidades o solicitudes).")
def deshabilitar_evento(
    id_evento_rida: int,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        service._validar_scope_evento(db, _user, id_evento_rida)
        result = service.deshabilitar_evento(db, id_evento_rida)
        return SuccessResponse(message="Evento RIDA deshabilitado correctamente", data=result)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise db_error(e)
