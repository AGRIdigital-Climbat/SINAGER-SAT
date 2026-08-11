from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import text
from sqlalchemy.orm import Session
from ..database import get_db
from ..dependencies import get_current_user
from ..auth.permisos import module_permiso
from ..response import SuccessResponse, MessageResponse
from ..upload import save_upload_file
from . import service
from .schemas import *

router = APIRouter(prefix="/edan", dependencies=[Depends(module_permiso("EDAN"))])

TAG_EDAN            = "EDAN"
TAG_EDAN_LOCALIDADES = "EDAN_LOCALIDADES"

# Roles que solo acceden a sus propios registros (patrón REA)
ROLES_LOCALES = (6, 7)          # CRUD localidades (UGR municipio + Responsable local)
ROLES_EDAN_CREA = (6,)          # Solo UGR municipio crea EDAN consolidado
ROLES_LECTURA = (6, 7, 8)       # Lectura (incluye alcalde)
ROLES_ESTADO_EDAN = (1, 2, 3, 4, 5, 9)  # Editar estado_edan (todos EXCEPTO 6, 7, 8)


def _require_rol(*roles):
    """Helper para validar roles. Lanza 403 si el rol no está permitido."""
    def _checker(_user=Depends(get_current_user)):
        if _user.get("id_rol") not in roles:
            raise HTTPException(
                status_code=403,
                detail=f"Rol {_user.get('id_rol')} no autorizado. Roles permitidos: {roles}"
            )
        return _user
    return _checker


def _db_error(exc: Exception) -> HTTPException:
    """Traduce errores de BD a mensajes limpios sin filtrar el SQL."""
    try:
        code = getattr(exc.orig, "sqlstate", None) or getattr(exc.orig, "pgcode", None)
    except AttributeError:
        code = None
    if code == "23503":
        return HTTPException(status_code=400, detail="El registro referenciado no existe (violación de clave foránea)")
    if code == "23505":
        return HTTPException(status_code=400, detail="Ya existe un registro con el mismo valor (violación de unicidad)")
    if code == "23502":
        return HTTPException(status_code=400, detail="Falta un campo obligatorio")
    return HTTPException(status_code=400, detail="Error al procesar la solicitud")


def _filters_from_query(
    q: str | None = None,
    id_departamento: int | None = None,
    id_provincia: int | None = None,
    id_municipio: int | None = None,
    id_tipo_evento: int | None = None,
    id_estado: int | None = None,
    estado: str | None = None,
    id_usuario_ugr: int | None = None,
    fecha_evento_desde: str | None = None,
    fecha_evento_hasta: str | None = None,
    fecha_creacion_desde: str | None = None,
    fecha_creacion_hasta: str | None = None,
    pendiente_eliminacion: bool | None = None,
    pendiente_actualizacion: bool | None = None,
    con_foto: bool | None = None,
    sin_foto: bool | None = None,
    imp_poblacion: bool | None = None,
    imp_salud: bool | None = None,
    imp_infraestructura: bool | None = None,
    imp_servicios: bool | None = None,
    imp_educacion: bool | None = None,
    imp_vivienda: bool | None = None,
    imp_agropecuario: bool | None = None,
    imp_proteccion: bool | None = None,
    imp_necesidades: bool | None = None,
    tiene_agricultura: bool | None = None,
    tiene_pecuario: bool | None = None,
) -> dict:
    return {
        "q": q, "id_departamento": id_departamento, "id_provincia": id_provincia,
        "id_municipio": id_municipio, "id_tipo_evento": id_tipo_evento,
        "id_estado": id_estado, "estado": estado, "id_usuario_ugr": id_usuario_ugr,
        "fecha_evento_desde": fecha_evento_desde,
        "fecha_evento_hasta": fecha_evento_hasta,
        "fecha_creacion_desde": fecha_creacion_desde,
        "fecha_creacion_hasta": fecha_creacion_hasta,
        "pendiente_eliminacion": pendiente_eliminacion,
        "pendiente_actualizacion": pendiente_actualizacion,
        "con_foto": con_foto, "sin_foto": sin_foto,
        "imp_poblacion": imp_poblacion, "imp_salud": imp_salud,
        "imp_infraestructura": imp_infraestructura, "imp_servicios": imp_servicios,
        "imp_educacion": imp_educacion, "imp_vivienda": imp_vivienda,
        "imp_agropecuario": imp_agropecuario, "imp_proteccion": imp_proteccion,
        "imp_necesidades": imp_necesidades,
        "tiene_agricultura": tiene_agricultura, "tiene_pecuario": tiene_pecuario,
    }


def _filtros_dep(
    q: str | None = Query(None),
    id_departamento: int | None = Query(None),
    id_provincia: int | None = Query(None),
    id_municipio: int | None = Query(None),
    id_tipo_evento: int | None = Query(None),
    id_estado: int | None = Query(None),
    estado: str | None = Query(None),
    id_usuario_ugr: int | None = Query(None),
    fecha_evento_desde: str | None = Query(None),
    fecha_evento_hasta: str | None = Query(None),
    fecha_creacion_desde: str | None = Query(None),
    fecha_creacion_hasta: str | None = Query(None),
    pendiente_eliminacion: bool | None = Query(None),
    pendiente_actualizacion: bool | None = Query(None),
    con_foto: bool | None = Query(None),
    sin_foto: bool | None = Query(None),
    imp_poblacion: bool | None = Query(None),
    imp_salud: bool | None = Query(None),
    imp_infraestructura: bool | None = Query(None),
    imp_servicios: bool | None = Query(None),
    imp_educacion: bool | None = Query(None),
    imp_vivienda: bool | None = Query(None),
    imp_agropecuario: bool | None = Query(None),
    imp_proteccion: bool | None = Query(None),
    imp_necesidades: bool | None = Query(None),
    tiene_agricultura: bool | None = Query(None),
    tiene_pecuario: bool | None = Query(None),
):
    return _filters_from_query(
        q=q, id_departamento=id_departamento, id_provincia=id_provincia,
        id_municipio=id_municipio, id_tipo_evento=id_tipo_evento,
        id_estado=id_estado, estado=estado, id_usuario_ugr=id_usuario_ugr,
        fecha_evento_desde=fecha_evento_desde, fecha_evento_hasta=fecha_evento_hasta,
        fecha_creacion_desde=fecha_creacion_desde, fecha_creacion_hasta=fecha_creacion_hasta,
        pendiente_eliminacion=pendiente_eliminacion, pendiente_actualizacion=pendiente_actualizacion,
        con_foto=con_foto, sin_foto=sin_foto,
        imp_poblacion=imp_poblacion, imp_salud=imp_salud,
        imp_infraestructura=imp_infraestructura, imp_servicios=imp_servicios,
        imp_educacion=imp_educacion, imp_vivienda=imp_vivienda,
        imp_agropecuario=imp_agropecuario, imp_proteccion=imp_proteccion,
        imp_necesidades=imp_necesidades,
        tiene_agricultura=tiene_agricultura, tiene_pecuario=tiene_pecuario,
    )


# ============================================================================
#  REPORTES (antes de /{id} para no capturar rutas)
# ============================================================================

@router.get("/reportes/mis-resumen", tags=[TAG_EDAN], responses={200: {"model": SuccessResponse}})
def mis_resumen(
    id_usuario: int | None = Query(None),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    uid = _user["id_usuario"] if _user["id_rol"] in ROLES_LOCALES else (id_usuario or _user["id_usuario"])
    data = service.get_mis_resumen_edan(db, uid)
    return SuccessResponse(message="Resumen EDAN del usuario generado correctamente", data=data)


@router.get("/reportes/mis-reportes", tags=[TAG_EDAN], responses={200: {"model": SuccessResponse}})
def mis_reportes(
    id_usuario: int | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    uid = _user["id_usuario"] if _user["id_rol"] in ROLES_LOCALES else (id_usuario or _user["id_usuario"])
    data, total = service.get_mis_edans(db, uid, skip=skip, limit=limit)
    return SuccessResponse(message="Reportes EDAN del usuario listados correctamente", data=data, total=total)


@router.get("/localidades/mis-resumen", tags=[TAG_EDAN_LOCALIDADES], responses={200: {"model": SuccessResponse}})
def mis_localidades_resumen(
    id_usuario: int | None = Query(None),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Resumen de localidades HUÉRFANAS (id_edan IS NULL) del usuario."""
    uid = _user["id_usuario"] if _user["id_rol"] in ROLES_LOCALES else (id_usuario or _user["id_usuario"])
    data = service.get_mis_localidades_resumen(db, uid)
    return SuccessResponse(message="Resumen de localidades listado correctamente", data=data or {})


@router.get("/localidades/mis-reportes", tags=[TAG_EDAN_LOCALIDADES], responses={200: {"model": SuccessResponse}})
def mis_localidades_reportes(
    id_usuario: int | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Lista localidades HUÉRFANAS (id_edan IS NULL) del usuario."""
    uid = _user["id_usuario"] if _user["id_rol"] in ROLES_LOCALES else (id_usuario or _user["id_usuario"])
    data, total = service.get_mis_localidades(db, uid, skip=skip, limit=limit)
    return SuccessResponse(message="Localidades listadas correctamente", data=data, total=total)


@router.get("/reportes/resumen", tags=[TAG_EDAN], responses={200: {"model": SuccessResponse}})
def reporte_resumen(
    f: dict = Depends(_filtros_dep),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    data = service.reporte_resumen(db, f)
    return SuccessResponse(message="Resumen EDAN generado correctamente", data=data)


@router.get("/reportes/geografico", tags=[TAG_EDAN], responses={200: {"model": SuccessResponse}})
def reporte_geografico(
    f: dict = Depends(_filtros_dep),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    data = service.reporte_geografico(db, f)
    return SuccessResponse(message="Reporte geográfico generado correctamente", data=data, total=len(data))


@router.get("/reportes/agricultura", tags=[TAG_EDAN], responses={200: {"model": SuccessResponse}})
def reporte_agricultura(
    f: dict = Depends(_filtros_dep),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    data = service.reporte_agricultura(db, f)
    return SuccessResponse(message="Reporte de agricultura generado correctamente", data=data, total=len(data))


@router.get("/reportes/pecuario", tags=[TAG_EDAN], responses={200: {"model": SuccessResponse}})
def reporte_pecuario(
    f: dict = Depends(_filtros_dep),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    data = service.reporte_pecuario(db, f)
    return SuccessResponse(message="Reporte de pecuario generado correctamente", data=data, total=len(data))


@router.get("/reportes/localidades", tags=[TAG_EDAN], responses={200: {"model": SuccessResponse}})
def reporte_localidades(
    f: dict = Depends(_filtros_dep),
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    data, total = service.reporte_localidades(db, f, skip=skip, limit=limit)
    return SuccessResponse(message="Reporte de localidades generado correctamente", data=data, total=total)


# ============================================================================
#  CATÁLOGOS (antes de /{id} para no capturar rutas)
# ============================================================================

def _catalog_crud_routes(parent, path, crud, Create, Update, label, tag):
    get_all, get_one, create, update, delete = crud
    s = path.replace("-", "_")

    @parent.get(f"/{path}", name=f"listar_{s}", tags=[tag], responses={200: {"model": SuccessResponse}})
    def _list(db: Session = Depends(get_db), _user=Depends(get_current_user)):
        data = get_all(db)
        return SuccessResponse(message=f"{label} listados correctamente", data=data, total=len(data))

    @parent.get(f"/{path}/{{id}}", name=f"obtener_{s}", tags=[tag], responses={200: {"model": SuccessResponse}})
    def _get(id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
        result = get_one(db, id)
        if not result:
            raise HTTPException(status_code=404, detail=f"{label} no encontrado")
        return SuccessResponse(message=f"{label} obtenido correctamente", data=result)

    @parent.post(f"/{path}", name=f"crear_{s}", status_code=201, tags=[tag], responses={201: {"model": SuccessResponse}})
    def _create(data: Create, db: Session = Depends(get_db), _user=Depends(get_current_user)):
        try:
            id = create(db, data.model_dump())
            result = get_one(db, id)
            return SuccessResponse(message=f"{label} creado correctamente", data=result)
        except Exception as e:
            raise _db_error(e)

    @parent.put(f"/{path}/{{id}}", name=f"actualizar_{s}", tags=[tag], responses={200: {"model": SuccessResponse}})
    def _update(id: int, data: Update, db: Session = Depends(get_db), _user=Depends(get_current_user)):
        result = update(db, id, data.model_dump())
        if not result:
            raise HTTPException(status_code=404, detail=f"{label} no encontrado")
        return SuccessResponse(message=f"{label} actualizado correctamente", data=result)

    @parent.delete(f"/{path}/{{id}}", name=f"eliminar_{s}", tags=[tag], responses={200: {"model": MessageResponse}})
    def _delete(id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
        if not delete(db, id):
            raise HTTPException(status_code=404, detail=f"{label} no encontrado")
        return MessageResponse(message=f"{label} eliminado correctamente")


_catalog_crud_routes(router, "tipo-evento", service.tipo_evento_crud,
                     TipoEventoCreate, TipoEventoUpdate, "Tipo de evento", TAG_EDAN)

_catalog_crud_routes(router, "estados", service.estado_edan_crud,
                     EstadoEdanCreate, EstadoEdanUpdate, "Estado EDAN", TAG_EDAN)

_catalog_crud_routes(router, "tipo-localidad", service.tipo_localidad_crud,
                     TipoLocalidadCreate, TipoLocalidadUpdate, "Tipo de localidad", TAG_EDAN)

_catalog_crud_routes(router, "localidades-estado", service.edan_localidades_estado_crud,
                     EdanLocalidadEstadoCreate, EdanLocalidadEstadoUpdate, "Estado de localidad", TAG_EDAN)


# ============================================================================
#  SINCRONIZACIÓN OFFLINE-FIRST (móvil <-> servidor <-> PC)
# ============================================================================

@router.post("/sync", tags=[TAG_EDAN], responses={200: {"model": SuccessResponse}})
def sync_push(data: EdanSyncIn, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    uid = _user["id_usuario"]
    results = []
    for e in data.edans:
        try:
            results.append(service.sync_upsert(db, e.model_dump(), uid))
        except Exception as exc:
            db.rollback()
            results.append({
                "id_local": e.id_local, "sincronizado": False, "aplicado": False,
                "error": _db_error(exc).detail,
            })
    return SuccessResponse(message="EDANs sincronizados correctamente", data=results)


@router.get("/sync/pull", tags=[TAG_EDAN], responses={200: {"model": SuccessResponse}})
def sync_pull(
    id_usuario: int | None = Query(None),
    fecha_desde: str | None = Query(None, description="Solo EDANs modificados después de esta fecha"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    uid = _user["id_usuario"] if _user["id_rol"] in ROLES_LOCALES else (id_usuario or _user["id_usuario"])
    data, total = service.list_edans_sync(db, uid, fecha_desde=fecha_desde, skip=skip, limit=limit)
    return SuccessResponse(message="EDANs sincronizados correctamente", data=data, total=total)


# ============================================================================
#  SINCRONIZACIÓN DE LOCALIDADES (unidad de reporte) + CONSOLIDACIÓN
# ============================================================================

@router.post("/localidades/sync", tags=[TAG_EDAN_LOCALIDADES], responses={200: {"model": SuccessResponse}})
def localidad_sync_push(data: LocalidadSyncIn, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    uid = _user["id_usuario"]
    results = []
    for loc in data.localidades:
        try:
            results.append(service.localidad_sync_upsert(db, loc.model_dump(), uid))
        except Exception as exc:
            db.rollback()
            results.append({
                "id_local": loc.id_local, "id_edan_localidad": None,
                "sincronizado": False, "aplicado": False,
                "error": _db_error(exc).detail,
            })
    return SuccessResponse(message="Localidades sincronizadas correctamente", data=results)


@router.get("/localidades/sync/pull", tags=[TAG_EDAN_LOCALIDADES], responses={200: {"model": SuccessResponse}})
def localidad_sync_pull(
    id_usuario: int | None = Query(None),
    fecha_desde: str | None = Query(None, description="Solo localidades modificadas después de esta fecha"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    uid = _user["id_usuario"] if _user["id_rol"] in ROLES_LOCALES else (id_usuario or _user["id_usuario"])
    data, total = service.list_localidades_sync(db, uid, fecha_desde=fecha_desde, skip=skip, limit=limit)
    return SuccessResponse(message="Localidades sincronizadas correctamente", data=data, total=total)


@router.get("/consolidar/pendientes", tags=[TAG_EDAN_LOCALIDADES], responses={200: {"model": SuccessResponse}})
def consolidar_pendientes(
    id_municipio: int | None = Query(None, description="Municipio del UGR (opcional)"),
    estado: str = Query("aprobado", description="Estado de localidad a agrupar"),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    data = service.listar_consolidables(db, id_municipio=id_municipio, estado_nombre=estado)
    return SuccessResponse(message="Localidades consolidadas listadas correctamente",
                           data=data, total=len(data))


@router.post("/consolidar", tags=[TAG_EDAN_LOCALIDADES], responses={200: {"model": SuccessResponse}})
def consolidar(data: ConsolidarIn, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    try:
        result = service.consolidar(db, data.id_municipio, data.id_tipo_evento,
                                    data.localidad_ids, _user["id_usuario"])
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise _db_error(e)
    return SuccessResponse(message="EDAN consolidado correctamente", data=result)


@router.put("/localidades/{id_localidad}/estado", tags=[TAG_EDAN_LOCALIDADES], responses={200: {"model": SuccessResponse}})
def cambiar_estado_localidad(id_localidad: int, data: LocalidadEstadoUpdate,
                             db: Session = Depends(get_db), _user=Depends(get_current_user)):
    try:
        result = service.cambiar_estado_localidad(db, id_localidad, data.id_edan_localidad_estado)
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise _db_error(e)
    if not result:
        raise HTTPException(status_code=404, detail="Localidad no encontrada")
    return SuccessResponse(message="Estado de localidad actualizado correctamente", data=result)


@router.delete("/localidades/{id_localidad}", tags=[TAG_EDAN_LOCALIDADES], responses={200: {"model": MessageResponse}})
def eliminar_localidad_standalone(id_localidad: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    if not service.delete_localidad(db, id_localidad):
        raise HTTPException(status_code=404, detail="Localidad no encontrada")
    return MessageResponse(message="Localidad eliminada correctamente")


# ============================================================================
#  EDAN PRINCIPAL
# ============================================================================

@router.get("/", tags=[TAG_EDAN], responses={200: {"model": SuccessResponse}})
def listar_edans(
    f: dict = Depends(_filtros_dep),
    order_by: str = Query("id_edan", description="Campo de orden (id_edan, fecha_evento, estado, ...)"),
    order: str = Query("desc", description="Dirección: asc | desc"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    f = dict(f)
    f["order_by"] = order_by
    f["order"] = order
    data, total = service.get_edans(db, f, skip=skip, limit=limit)
    return SuccessResponse(message="EDANs listados correctamente", data=data, total=total)


@router.get("/{id}", tags=[TAG_EDAN], responses={200: {"model": SuccessResponse}})
def obtener_edan(id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    result = service.get_edan_completo(db, id)
    if not result:
        raise HTTPException(status_code=404, detail="EDAN no encontrado")
    return SuccessResponse(message="EDAN obtenido correctamente", data=result)


@router.post("/", status_code=201, tags=[TAG_EDAN], responses={201: {"model": SuccessResponse}},
             dependencies=[Depends(_require_rol(*ROLES_EDAN_CREA))])
def crear_edan(data: EdanCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    try:
        payload = data.model_dump(exclude_none=False)
        if payload.get("id_usuario") is None:
            payload["id_usuario"] = user["id_usuario"]
        id = service.create_edan(db, payload)
        result = service.get_edan_completo(db, id)
        return SuccessResponse(message="EDAN creado correctamente", data=result)
    except HTTPException:
        raise
    except Exception as e:
        raise _db_error(e)


@router.put("/{id}", tags=[TAG_EDAN], responses={200: {"model": SuccessResponse}},
            dependencies=[Depends(_require_rol(*ROLES_EDAN_CREA))])
def actualizar_edan(id: int, data: EdanUpdate, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    try:
        result = service.update_edan(db, id, data.model_dump(exclude_unset=True))
    except HTTPException:
        raise
    except Exception as e:
        raise _db_error(e)
    if not result:
        raise HTTPException(status_code=404, detail="EDAN no encontrado")
    return SuccessResponse(message="EDAN actualizado correctamente", data=result)


@router.put("/{id}/estado", tags=[TAG_EDAN], responses={200: {"model": SuccessResponse}},
            dependencies=[Depends(_require_rol(*ROLES_ESTADO_EDAN))])
def cambiar_estado_edan_endpoint(id: int, data: EstadoEdanUpdate,
                                  db: Session = Depends(get_db), _user=Depends(get_current_user)):
    """Cambia solo el campo id_estado de un EDAN consolidado.
    Acceso abierto para roles 1-5, 9 (admin, VIDECI, UGR Sectores, DGR, VIDECI Departamental).
    Roles 6, 7, 8 NO pueden editar estado_edan."""
    try:
        result = service.cambiar_estado_edan(db, id, data.id_estado)
    except HTTPException:
        raise
    except Exception as e:
        raise _db_error(e)
    if not result:
        raise HTTPException(status_code=404, detail="EDAN no encontrado")
    return SuccessResponse(message="Estado de EDAN actualizado correctamente", data=result)


@router.delete("/{id}", tags=[TAG_EDAN], responses={200: {"model": MessageResponse}},
               dependencies=[Depends(_require_rol(*ROLES_EDAN_CREA))])
def eliminar_edan(id: int, permanente: bool = Query(False, description="Eliminación física (cascada)"),
                  db: Session = Depends(get_db), _user=Depends(get_current_user)):
    if permanente:
        if not service.delete_edan(db, id):
            raise HTTPException(status_code=404, detail="EDAN no encontrado")
        return MessageResponse(message="EDAN eliminado permanentemente")
    result = service.soft_delete_edan(db, id)
    if not result:
        raise HTTPException(status_code=404, detail="EDAN no encontrado")
    return SuccessResponse(message="EDAN marcado para eliminación", data=result)


# ============================================================================
#  LOCALIDADES (CRUD anidado)
# ============================================================================

@router.get("/{id}/localidades", tags=[TAG_EDAN_LOCALIDADES], responses={200: {"model": SuccessResponse}})
def listar_localidades(id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    if not service.get_edan(db, id):
        raise HTTPException(status_code=404, detail="EDAN no encontrado")
    data = service._get_localidades(db, id)
    return SuccessResponse(message="Localidades listadas correctamente", data=data, total=len(data))


@router.post("/{id}/localidades", status_code=201, tags=[TAG_EDAN_LOCALIDADES], responses={201: {"model": SuccessResponse}},
                  dependencies=[Depends(_require_rol(*ROLES_LOCALES))])
def crear_localidad(id: int, data: LocalidadCreate, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    if not service.get_edan(db, id):
        raise HTTPException(status_code=404, detail="EDAN no encontrado")
    try:
        lid = service._insert_localidad(db, id, data.model_dump())
        service._bump_edan_fecha(db, id)
        db.commit()
        result = service._build_localidad(db, lid)
        return SuccessResponse(message="Localidad creada correctamente", data=result)
    except Exception as e:
        db.rollback()
        raise _db_error(e)


@router.put("/{id}/localidades/{id_localidad}", tags=[TAG_EDAN_LOCALIDADES], responses={200: {"model": SuccessResponse}},
             dependencies=[Depends(_require_rol(*ROLES_LOCALES))])
def actualizar_localidad(id: int, id_localidad: int, data: LocalidadUpdate,
                         db: Session = Depends(get_db), _user=Depends(get_current_user)):
    try:
        result = service.update_localidad(db, id_localidad, data.model_dump())
    except Exception as e:
        db.rollback()
        raise _db_error(e)
    if not result:
        raise HTTPException(status_code=404, detail="Localidad no encontrada")
    return SuccessResponse(message="Localidad actualizada correctamente", data=result)


@router.delete("/{id}/localidades/{id_localidad}", tags=[TAG_EDAN_LOCALIDADES], responses={200: {"model": MessageResponse}},
                dependencies=[Depends(_require_rol(*ROLES_LOCALES))])
def eliminar_localidad(id: int, id_localidad: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    if not service.delete_localidad(db, id_localidad):
        raise HTTPException(status_code=404, detail="Localidad no encontrada")
    return MessageResponse(message="Localidad eliminada correctamente")


# ============================================================================
#  CREAR ITEMS DE DAÑO/SERVICIO CON FOTO (estilo REA /reportes/con-foto)
#  Patrón de archivo: uploads/reports/{codigo_ine}/{codigo_ine}_{id_usuario}_{ts}.{ext}
#  Solo difieren en los Form fields de cada tabla. Si el cliente prefiere subir
#  primero y luego mandar el path, también puede usar /upload (api/upload.py).
# ============================================================================

async def _upload_to_localidad(file: UploadFile, db: Session, id_localidad: int, _user: dict) -> str:
    """Sube un archivo y devuelve el path. Usa id_municipio de la localidad."""
    row = service._row(db, "SELECT id_municipio FROM edan.edan_localidades WHERE id_edan_localidad = :id",
                       {"id": id_localidad})
    if not row:
        raise HTTPException(status_code=404, detail=f"Localidad {id_localidad} no encontrada")
    return await save_upload_file(file, db, row["id_municipio"], _user.get("id_usuario"))


@router.post("/localidades/{id_localidad}/danos-viales/con-foto", status_code=201, tags=[TAG_EDAN_LOCALIDADES])
async def crear_danos_viales_con_foto(
    id_localidad: int,
    file: UploadFile = File(...),
    via: bool = Form(False),
    puente: bool = Form(False),
    tramo: str = Form(""),
    dano_parcial: bool = Form(False),
    dano_total: bool = Form(False),
    km_danio: float | None = Form(None),
    necesidades_inmediatas: str = Form(""),
    observaciones: str = Form(""),
    coordenada_lat: float | None = Form(None),
    coordenada_lon: float | None = Form(None),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        fotografia = await _upload_to_localidad(file, db, id_localidad, _user)
        result = service.create_dano_vial(db, id_localidad, {
            "via": via, "puente": puente, "tramo": tramo,
            "dano_parcial": dano_parcial, "dano_total": dano_total,
            "km_danio": km_danio,
            "necesidades_inmediatas": necesidades_inmediatas,
            "observaciones": observaciones,
            "fotografia": fotografia,
            "coordenada_lat": coordenada_lat,
            "coordenada_lon": coordenada_lon,
        })
        return SuccessResponse(message="Daño vial creado con foto", data=result)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise _db_error(e)


@router.post("/localidades/{id_localidad}/danos-infra-publica/con-foto", status_code=201, tags=[TAG_EDAN_LOCALIDADES])
async def crear_danos_infra_publica_con_foto(
    id_localidad: int,
    file: UploadFile = File(...),
    comunidad: str = Form(""),
    tipo_estructura: str = Form(""),
    dano_parcial: bool = Form(False),
    dano_total: bool = Form(False),
    observaciones: str = Form(""),
    coordenada_lat: float | None = Form(None),
    coordenada_lon: float | None = Form(None),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        fotografia = await _upload_to_localidad(file, db, id_localidad, _user)
        result = service.create_dano_infra_publica(db, id_localidad, {
            "comunidad": comunidad, "tipo_estructura": tipo_estructura,
            "dano_parcial": dano_parcial, "dano_total": dano_total,
            "observaciones": observaciones,
            "fotografia": fotografia,
            "coordenada_lat": coordenada_lat,
            "coordenada_lon": coordenada_lon,
        })
        return SuccessResponse(message="Daño infraestructura pública creado con foto", data=result)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise _db_error(e)


@router.post("/localidades/{id_localidad}/danos-vivienda/con-foto", status_code=201, tags=[TAG_EDAN_LOCALIDADES])
async def crear_danos_vivienda_con_foto(
    id_localidad: int,
    file: UploadFile = File(...),
    comunidad: str = Form(""),
    dano_parcial: int = Form(0),
    dano_total: int = Form(0),
    necesidades_inmediatas: str = Form(""),
    observaciones: str = Form(""),
    coordenada_lat: float | None = Form(None),
    coordenada_lon: float | None = Form(None),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        fotografia = await _upload_to_localidad(file, db, id_localidad, _user)
        result = service.create_dano_vivienda(db, id_localidad, {
            "comunidad": comunidad, "dano_parcial": dano_parcial, "dano_total": dano_total,
            "necesidades_inmediatas": necesidades_inmediatas,
            "observaciones": observaciones,
            "fotografia": fotografia,
            "coordenada_lat": coordenada_lat,
            "coordenada_lon": coordenada_lon,
        })
        return SuccessResponse(message="Daño vivienda creado con foto", data=result)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise _db_error(e)


@router.post("/localidades/{id_localidad}/danos-agricultura/con-foto", status_code=201, tags=[TAG_EDAN_LOCALIDADES])
async def crear_danos_agricultura_con_foto(
    id_localidad: int,
    file: UploadFile = File(...),
    tipo_cultivo: str = Form(""),
    id_cultivo: int | None = Form(None),
    hectareas_afectadas: int = Form(0),
    hectareas_perdidas: int = Form(0),
    necesidades_inmediatas: str = Form(""),
    observaciones: str = Form(""),
    coordenada_lat: float | None = Form(None),
    coordenada_lon: float | None = Form(None),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        fotografia = await _upload_to_localidad(file, db, id_localidad, _user)
        result = service.create_dano_agricultura(db, id_localidad, {
            "tipo_cultivo": tipo_cultivo, "id_cultivo": id_cultivo,
            "hectareas_afectadas": hectareas_afectadas,
            "hectareas_perdidas": hectareas_perdidas,
            "necesidades_inmediatas": necesidades_inmediatas,
            "observaciones": observaciones,
            "fotografia": fotografia,
            "coordenada_lat": coordenada_lat,
            "coordenada_lon": coordenada_lon,
        })
        return SuccessResponse(message="Daño agricultura creado con foto", data=result)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise _db_error(e)


@router.post("/localidades/{id_localidad}/danos-pecuarios/con-foto", status_code=201, tags=[TAG_EDAN_LOCALIDADES])
async def crear_danos_pecuarios_con_foto(
    id_localidad: int,
    file: UploadFile = File(...),
    especie: str = Form(""),
    id_especie: int | None = Form(None),
    raza: str = Form(""),
    animales_afectados: int = Form(0),
    animales_muertos: int = Form(0),
    necesidades_inmediatas: str = Form(""),
    coordenada_lat: float | None = Form(None),
    coordenada_lon: float | None = Form(None),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        fotografia = await _upload_to_localidad(file, db, id_localidad, _user)
        result = service.create_dano_pecuario(db, id_localidad, {
            "especie": especie, "id_especie": id_especie, "raza": raza,
            "animales_afectados": animales_afectados,
            "animales_muertos": animales_muertos,
            "necesidades_inmediatas": necesidades_inmediatas,
            "fotografia": fotografia,
            "coordenada_lat": coordenada_lat,
            "coordenada_lon": coordenada_lon,
        })
        return SuccessResponse(message="Daño pecuario creado con foto", data=result)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise _db_error(e)


@router.post("/localidades/{id_localidad}/salud-establecimientos/con-foto", status_code=201, tags=[TAG_EDAN_LOCALIDADES])
async def crear_salud_establecimiento_con_foto(
    id_localidad: int,
    file: UploadFile = File(...),
    nombre_establecimiento: str = Form(""),
    comunidad: str = Form(""),
    nivel_atencion: str = Form(""),
    dano_parcial: bool = Form(False),
    dano_total: bool = Form(False),
    medicos_afectados: int = Form(0),
    enfermeras_afectados: int = Form(0),
    otros_afectados: int = Form(0),
    coordenada_lat: float | None = Form(None),
    coordenada_lon: float | None = Form(None),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        fotografia = await _upload_to_localidad(file, db, id_localidad, _user)
        result = service.create_establecimiento_salud(db, id_localidad, {
            "nombre_establecimiento": nombre_establecimiento, "comunidad": comunidad,
            "nivel_atencion": nivel_atencion,
            "dano_parcial": dano_parcial, "dano_total": dano_total,
            "medicos_afectados": medicos_afectados,
            "enfermeras_afectados": enfermeras_afectados,
            "otros_afectados": otros_afectados,
            "fotografia": fotografia,
            "coordenada_lat": coordenada_lat,
            "coordenada_lon": coordenada_lon,
        })
        return SuccessResponse(message="Establecimiento de salud creado con foto", data=result)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise _db_error(e)


@router.post("/localidades/{id_localidad}/servicios-basicos/con-foto", status_code=201, tags=[TAG_EDAN_LOCALIDADES])
async def crear_servicio_basico_con_foto(
    id_localidad: int,
    file: UploadFile = File(...),
    tipo: str = Form(""),
    dano_parcial: bool = Form(False),
    dano_total: bool = Form(False),
    necesidades_inmediatas: str = Form(""),
    observaciones: str = Form(""),
    coordenada_lat: float | None = Form(None),
    coordenada_lon: float | None = Form(None),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        fotografia = await _upload_to_localidad(file, db, id_localidad, _user)
        result = service.create_servicio_basico(db, id_localidad, {
            "tipo": tipo,
            "dano_parcial": dano_parcial, "dano_total": dano_total,
            "necesidades_inmediatas": necesidades_inmediatas,
            "observaciones": observaciones,
            "fotografia": fotografia,
            "coordenada_lat": coordenada_lat,
            "coordenada_lon": coordenada_lon,
        })
        return SuccessResponse(message="Servicio básico creado con foto", data=result)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise _db_error(e)


@router.post("/localidades/{id_localidad}/unidades-educativas/con-foto", status_code=201, tags=[TAG_EDAN_LOCALIDADES])
async def crear_unidad_educativa_con_foto(
    id_localidad: int,
    file: UploadFile = File(...),
    nombre_establecimiento: str = Form(""),
    comunidad: str = Form(""),
    dano_parcial: bool = Form(False),
    dano_total: bool = Form(False),
    suspension_clases: bool | None = Form(None),
    perdida_material: bool | None = Form(None),
    funciona_albergue: bool | None = Form(None),
    estudiantes: int = Form(0),
    profesores: int = Form(0),
    administrativos: int = Form(0),
    observaciones: str = Form(""),
    coordenada_lat: float | None = Form(None),
    coordenada_lon: float | None = Form(None),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        fotografia = await _upload_to_localidad(file, db, id_localidad, _user)
        result = service.create_unidad_educativa(db, id_localidad, {
            "nombre_establecimiento": nombre_establecimiento, "comunidad": comunidad,
            "dano_parcial": dano_parcial, "dano_total": dano_total,
            "suspension_clases": suspension_clases,
            "perdida_material": perdida_material,
            "funciona_albergue": funciona_albergue,
            "estudiantes": estudiantes, "profesores": profesores,
            "administrativos": administrativos,
            "observaciones": observaciones,
            "fotografia": fotografia,
            "coordenada_lat": coordenada_lat,
            "coordenada_lon": coordenada_lon,
        })
        return SuccessResponse(message="Unidad educativa creada con foto", data=result)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise _db_error(e)


# ============================================================================
#  GET: listar items con foto por municipio / filtros
#  Cada endpoint devuelve el item completo (incluye path de la foto).
# ============================================================================

@router.get("/localidades/{id_localidad}/danos-viales", tags=[TAG_EDAN_LOCALIDADES])
def listar_danos_viales(
    id_localidad: int,
    con_foto: bool | None = Query(None),
    skip: int = 0, limit: int = 100,
    db: Session = Depends(get_db), _user=Depends(get_current_user),
):
    conds = ["id_edan_localidad = :id"]
    params: dict = {"id": id_localidad}
    if con_foto is True:
        conds.append("fotografia IS NOT NULL AND fotografia <> ''")
    elif con_foto is False:
        conds.append("(fotografia IS NULL OR fotografia = '')")
    rows = service._rows(db, f"""
        SELECT * FROM edan.edan_localidades_danos_viales
        WHERE {' AND '.join(conds)}
        ORDER BY id_dano_vial DESC LIMIT :limit OFFSET :skip
    """, {**params, "limit": limit, "skip": skip})
    total = service._row(db, f"""
        SELECT COUNT(*) AS c FROM edan.edan_localidades_danos_viales
        WHERE {' AND '.join(conds)}
    """, params)["c"]
    return SuccessResponse(message="Daños viales listados", data=[dict(r) for r in rows], total=total)


@router.get("/localidades/{id_localidad}/danos-infra-publica", tags=[TAG_EDAN_LOCALIDADES])
def listar_danos_infra_publica(
    id_localidad: int,
    con_foto: bool | None = Query(None),
    skip: int = 0, limit: int = 100,
    db: Session = Depends(get_db), _user=Depends(get_current_user),
):
    conds = ["id_edan_localidad = :id"]
    params: dict = {"id": id_localidad}
    if con_foto is True:
        conds.append("fotografia IS NOT NULL AND fotografia <> ''")
    elif con_foto is False:
        conds.append("(fotografia IS NULL OR fotografia = '')")
    rows = service._rows(db, f"""
        SELECT * FROM edan.edan_localidades_danos_infra_publica
        WHERE {' AND '.join(conds)}
        ORDER BY id_dano_infra DESC LIMIT :limit OFFSET :skip
    """, {**params, "limit": limit, "skip": skip})
    total = service._row(db, f"""
        SELECT COUNT(*) AS c FROM edan.edan_localidades_danos_infra_publica
        WHERE {' AND '.join(conds)}
    """, params)["c"]
    return SuccessResponse(message="Daños infraestructura pública listados", data=[dict(r) for r in rows], total=total)


@router.get("/localidades/{id_localidad}/danos-vivienda", tags=[TAG_EDAN_LOCALIDADES])
def listar_danos_vivienda(
    id_localidad: int,
    con_foto: bool | None = Query(None),
    skip: int = 0, limit: int = 100,
    db: Session = Depends(get_db), _user=Depends(get_current_user),
):
    conds = ["id_edan_localidad = :id"]
    params: dict = {"id": id_localidad}
    if con_foto is True:
        conds.append("fotografia IS NOT NULL AND fotografia <> ''")
    elif con_foto is False:
        conds.append("(fotografia IS NULL OR fotografia = '')")
    rows = service._rows(db, f"""
        SELECT * FROM edan.edan_localidades_danos_vivienda
        WHERE {' AND '.join(conds)}
        ORDER BY id_dano_vivienda DESC LIMIT :limit OFFSET :skip
    """, {**params, "limit": limit, "skip": skip})
    total = service._row(db, f"""
        SELECT COUNT(*) AS c FROM edan.edan_localidades_danos_vivienda
        WHERE {' AND '.join(conds)}
    """, params)["c"]
    return SuccessResponse(message="Daños vivienda listados", data=[dict(r) for r in rows], total=total)


@router.get("/localidades/{id_localidad}/danos-agricultura", tags=[TAG_EDAN_LOCALIDADES])
def listar_danos_agricultura(
    id_localidad: int,
    con_foto: bool | None = Query(None),
    skip: int = 0, limit: int = 100,
    db: Session = Depends(get_db), _user=Depends(get_current_user),
):
    conds = ["id_edan_localidad = :id"]
    params: dict = {"id": id_localidad}
    if con_foto is True:
        conds.append("fotografia IS NOT NULL AND fotografia <> ''")
    elif con_foto is False:
        conds.append("(fotografia IS NULL OR fotografia = '')")
    rows = service._rows(db, f"""
        SELECT * FROM edan.edan_localidades_danos_agricultura
        WHERE {' AND '.join(conds)}
        ORDER BY id_dano_agricola DESC LIMIT :limit OFFSET :skip
    """, {**params, "limit": limit, "skip": skip})
    total = service._row(db, f"""
        SELECT COUNT(*) AS c FROM edan.edan_localidades_danos_agricultura
        WHERE {' AND '.join(conds)}
    """, params)["c"]
    return SuccessResponse(message="Daños agricultura listados", data=[dict(r) for r in rows], total=total)


@router.get("/localidades/{id_localidad}/danos-pecuarios", tags=[TAG_EDAN_LOCALIDADES])
def listar_danos_pecuarios(
    id_localidad: int,
    con_foto: bool | None = Query(None),
    skip: int = 0, limit: int = 100,
    db: Session = Depends(get_db), _user=Depends(get_current_user),
):
    conds = ["id_edan_localidad = :id"]
    params: dict = {"id": id_localidad}
    if con_foto is True:
        conds.append("fotografia IS NOT NULL AND fotografia <> ''")
    elif con_foto is False:
        conds.append("(fotografia IS NULL OR fotografia = '')")
    rows = service._rows(db, f"""
        SELECT * FROM edan.edan_localidades_danos_pecuario
        WHERE {' AND '.join(conds)}
        ORDER BY id_dano_pecuario DESC LIMIT :limit OFFSET :skip
    """, {**params, "limit": limit, "skip": skip})
    total = service._row(db, f"""
        SELECT COUNT(*) AS c FROM edan.edan_localidades_danos_pecuario
        WHERE {' AND '.join(conds)}
    """, params)["c"]
    return SuccessResponse(message="Daños pecuarios listados", data=[dict(r) for r in rows], total=total)


@router.get("/localidades/{id_localidad}/salud-establecimientos", tags=[TAG_EDAN_LOCALIDADES])
def listar_salud_establecimientos(
    id_localidad: int,
    con_foto: bool | None = Query(None),
    skip: int = 0, limit: int = 100,
    db: Session = Depends(get_db), _user=Depends(get_current_user),
):
    conds = ["id_edan_localidad = :id"]
    params: dict = {"id": id_localidad}
    if con_foto is True:
        conds.append("fotografia IS NOT NULL AND fotografia <> ''")
    elif con_foto is False:
        conds.append("(fotografia IS NULL OR fotografia = '')")
    rows = service._rows(db, f"""
        SELECT * FROM edan.edan_localidades_salud_establecimientos
        WHERE {' AND '.join(conds)}
        ORDER BY id_establecimiento_salud DESC LIMIT :limit OFFSET :skip
    """, {**params, "limit": limit, "skip": skip})
    total = service._row(db, f"""
        SELECT COUNT(*) AS c FROM edan.edan_localidades_salud_establecimientos
        WHERE {' AND '.join(conds)}
    """, params)["c"]
    return SuccessResponse(message="Establecimientos de salud listados", data=[dict(r) for r in rows], total=total)


@router.get("/localidades/{id_localidad}/servicios-basicos", tags=[TAG_EDAN_LOCALIDADES])
def listar_servicios_basicos(
    id_localidad: int,
    con_foto: bool | None = Query(None),
    skip: int = 0, limit: int = 100,
    db: Session = Depends(get_db), _user=Depends(get_current_user),
):
    conds = ["id_edan_localidad = :id"]
    params: dict = {"id": id_localidad}
    if con_foto is True:
        conds.append("fotografia IS NOT NULL AND fotografia <> ''")
    elif con_foto is False:
        conds.append("(fotografia IS NULL OR fotografia = '')")
    rows = service._rows(db, f"""
        SELECT * FROM edan.edan_localidades_servicios_basicos
        WHERE {' AND '.join(conds)}
        ORDER BY id_servicio_basico DESC LIMIT :limit OFFSET :skip
    """, {**params, "limit": limit, "skip": skip})
    total = service._row(db, f"""
        SELECT COUNT(*) AS c FROM edan.edan_localidades_servicios_basicos
        WHERE {' AND '.join(conds)}
    """, params)["c"]
    return SuccessResponse(message="Servicios básicos listados", data=[dict(r) for r in rows], total=total)


@router.get("/localidades/{id_localidad}/unidades-educativas", tags=[TAG_EDAN_LOCALIDADES])
def listar_unidades_educativas(
    id_localidad: int,
    con_foto: bool | None = Query(None),
    skip: int = 0, limit: int = 100,
    db: Session = Depends(get_db), _user=Depends(get_current_user),
):
    conds = ["id_edan_localidad = :id"]
    params: dict = {"id": id_localidad}
    if con_foto is True:
        conds.append("fotografia IS NOT NULL AND fotografia <> ''")
    elif con_foto is False:
        conds.append("(fotografia IS NULL OR fotografia = '')")
    rows = service._rows(db, f"""
        SELECT * FROM edan.edan_localidades_unidades_educativas
        WHERE {' AND '.join(conds)}
        ORDER BY id_unidad_educativa DESC LIMIT :limit OFFSET :skip
    """, {**params, "limit": limit, "skip": skip})
    total = service._row(db, f"""
        SELECT COUNT(*) AS c FROM edan.edan_localidades_unidades_educativas
        WHERE {' AND '.join(conds)}
    """, params)["c"]
    return SuccessResponse(message="Unidades educativas listadas", data=[dict(r) for r in rows], total=total)


# ============================================================================
#  GET: todas las fotos de un municipio (para galería de evidencia)
#  Agrupa por id_localidad y retorna cada item con su foto, geolocalización
#  y nombre de comunidad para renderizar en un mapa o galería.
# ============================================================================

TABLAS_CON_FOTO = {
    "danos_viales": ("edan_localidades_danos_viales", "id_dano_vial"),
    "danos_infra_publica": ("edan_localidades_danos_infra_publica", "id_dano_infra"),
    "danos_vivienda": ("edan_localidades_danos_vivienda", "id_dano_vivienda"),
    "danos_agricultura": ("edan_localidades_danos_agricultura", "id_dano_agricola"),
    "danos_pecuarios": ("edan.edan_localidades_danos_pecuario", "id_dano_pecuario"),
    "salud_establecimientos": ("edan_localidades_salud_establecimientos", "id_establecimiento_salud"),
    "servicios_basicos": ("edan_localidades_servicios_basicos", "id_servicio_basico"),
    "unidades_educativas": ("edan_localidades_unidades_educativas", "id_unidad_educativa"),
}


@router.get("/municipios/{id_municipio}/fotos", tags=[TAG_EDAN])
def listar_fotos_por_municipio(
    id_municipio: int,
    tipo: str | None = Query(None, description="Filtrar por tipo de daño/servicio (claves de TABLAS_CON_FOTO). Si None, devuelve todos."),
    con_coordenadas: bool | None = Query(None, description="Solo items con coordenada_lat Y coordenada_lon no nulos."),
    skip: int = 0, limit: int = 200,
    db: Session = Depends(get_db), _user=Depends(get_current_user),
):
    """Devuelve todas las evidencias fotográficas del municipio, agrupadas por
    tabla. Cada item incluye: id, tipo (nombre lógico), id_localidad, comunidad,
    fotografia (path), coordenada_lat, coordenada_lon."""
    tablas = {tipo: TABLAS_CON_FOTO[tipo]} if tipo and tipo in TABLAS_CON_FOTO else TABLAS_CON_FOTO
    conds = ["l.id_municipio = :m", "t.fotografia IS NOT NULL", "t.fotografia <> ''"]
    if con_coordenadas is True:
        conds.append("t.coordenada_lat IS NOT NULL AND t.coordenada_lon IS NOT NULL")
    where = " AND ".join(conds)

    resultados: list[dict] = []
    for tipo_nombre, (tabla, pk) in tablas.items():
        tabla_q = tabla.replace("edan.", "edan.")
        rows = service._rows(db, f"""
            SELECT t.{pk} AS id_item, '{tipo_nombre}' AS tipo, l.id_edan_localidad,
                   l.localidad, l.comunidad_id, t.fotografia,
                   t.coordenada_lat, t.coordenada_lon
            FROM edan.{tabla_q} t
            JOIN edan.edan_localidades l ON l.id_edan_localidad = t.id_edan_localidad
            WHERE {where}
            ORDER BY t.{pk} DESC LIMIT :limit OFFSET :skip
        """, {"m": id_municipio, "limit": limit, "skip": skip})
        resultados.extend(dict(r) for r in rows)

    resultados.sort(key=lambda x: x["id_item"], reverse=True)
    return SuccessResponse(
        message=f"Evidencias fotográficas del municipio {id_municipio}",
        data=resultados,
        total=len(resultados),
    )
