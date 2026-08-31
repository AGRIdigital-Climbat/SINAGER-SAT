from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..dependencies import get_current_user
from ..database import get_db
from ..response import SuccessResponse, MessageResponse
from . import service
from .schemas import EdanCreate, EdanUpdate, ConsolidarIn, EdanSyncIn, CambiarEstadoEdanIn, LocalidadEstadoUpdate
from .utils import require_rol, db_error
from ..auth.permisos import module_permiso

router = APIRouter(prefix="/edan", dependencies=[Depends(module_permiso("EDAN"))])

TAG_EDAN = "EDAN"
TAG_EDAN_LOCALIDADES = "EDAN_LOCALIDADES"

ROLES_EDAN_CREA = (1, 2, 3, 4, 5, 9)
ROLES_ESTADO_EDAN = (1, 2, 3, 4, 5, 9)
ROLES_LOCALES = (6, 7)


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
    user=Depends(get_current_user),
):
    f = service._filters_from_query(
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
    if user["id_rol"] not in (1, 9) and f.get("id_usuario_ugr") is None:
        f["id_usuario_ugr"] = user["id_usuario"]
    return f


# ----------------------------------------------------------------------------
#  REPORTES (solo totales/agregados) — antes de /{id} para no capturar rutas
#  Mismos filtros que v1. Scope: rol 1/9 ve todo (filtro libre); otros roles
#  ven solo sus EDAN (id_usuario_ugr = propio) salvo filtro explícito.
# ----------------------------------------------------------------------------

@router.get("/reportes/mis-resumen", tags=[TAG_EDAN],
            summary="Resumen de mis EDAN (totales + por estado_edan)",
            description="Totales agregados de EDAN del usuario: `totales`, `por_estado[]` "
                        "y `por_tipo_evento[]`. Scope: rol 6/7 ve lo propio; otro rol usa `?id_usuario=`.")
def reportes_mis_resumen_edan(
    id_usuario: int | None = Query(None),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    uid = _user["id_usuario"] if _user["id_rol"] not in (1, 9) else (id_usuario or _user["id_usuario"])
    data = service.get_mis_resumen_edan(db, uid)
    return SuccessResponse(message="Resumen de mis EDAN generado correctamente", data=data or {})


@router.get("/reportes/mis-reportes", tags=[TAG_EDAN],
            summary="Listar mis EDAN (cabecera + localidades)",
            description="Lista los EDAN del usuario con su estructura completa (cabecera + localidades). "
                        "Scope: rol 6/7 ve lo propio; otro rol usa `?id_usuario=`.")
def reportes_mis_reportes_edan(
    id_usuario: int | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    uid = _user["id_usuario"] if _user["id_rol"] not in (1, 9) else (id_usuario or _user["id_usuario"])
    data, total = service.get_mis_edans(db, uid, skip=skip, limit=limit)
    return SuccessResponse(message="Reportes EDAN del usuario listados correctamente", data=data, total=total)


@router.get("/reportes/resumen", tags=[TAG_EDAN],
            summary="Reporte resumen de EDAN (totales agregados con filtros)",
            description="Totales agregados de EDAN con filtros (geografía, tipo_evento, estado, fechas, flags): "
                        "`totales`, `por_estado[]`, `por_tipo_evento[]`.")
def reportes_resumen_edan(
    f: dict = Depends(_filtros_dep),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    data = service.reporte_resumen(db, f) or {}
    return SuccessResponse(message="Resumen EDAN generado correctamente", data=data)


@router.get("/reportes/geografico", tags=[TAG_EDAN],
            summary="Reporte geográfico de EDAN (agrupado por d/p/m)",
            description="EDANs agrupados por departamento/provincia/municipio con totales acumulados.")
def reportes_geografico_edan(
    f: dict = Depends(_filtros_dep),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    data = service.reporte_geografico(db, f) or []
    return SuccessResponse(message="Reporte geográfico generado correctamente", data=data, total=len(data))


@router.get("/reportes/agricultura", tags=[TAG_EDAN],
            summary="Reporte de daños a agricultura (agregado)",
            description="Hectáreas afectadas/perdidas por cultivo, con filtros de EDAN.")
def reportes_agricultura_edan(
    f: dict = Depends(_filtros_dep),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    data = service.reporte_agricultura(db, f) or []
    return SuccessResponse(message="Reporte de agricultura generado correctamente", data=data, total=len(data))


@router.get("/reportes/pecuario", tags=[TAG_EDAN],
            summary="Reporte de daños pecuarios (agregado)",
            description="Animales afectados/muertos por especie, con filtros de EDAN.")
def reportes_pecuario_edan(
    f: dict = Depends(_filtros_dep),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    data = service.reporte_pecuario(db, f) or []
    return SuccessResponse(message="Reporte de pecuario generado correctamente", data=data, total=len(data))


@router.get("/reportes/localidades", tags=[TAG_EDAN],
            summary="Reporte de localidades consolidadas (paginado)",
            description="Listado de localidades consolidadas en EDAN con sus banderas de impacto, "
                        "con filtros de EDAN. Paginado con `skip`/`limit`.")
def reportes_localidades_edan(
    f: dict = Depends(_filtros_dep),
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    data, total = service.reporte_localidades(db, f, skip=skip, limit=limit)
    return SuccessResponse(message="Reporte de localidades generado correctamente", data=data, total=total)


@router.get("/", tags=[TAG_EDAN], summary="Listar EDANs con filtros")
def listar_edans(f: dict = Depends(_filtros_dep), skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=500),
                 db: Session = Depends(get_db), _user=Depends(get_current_user)):
    data, total = service.get_edans(db, dict(f), skip=skip, limit=limit)
    return SuccessResponse(message="EDANs listados correctamente", data=data, total=total)


@router.get("/mis-resumen", tags=[TAG_EDAN],
            summary="Resumen de mis EDAN (totales + por estado_edan)",
            description="Totales agregados de EDAN del usuario y desglose `por_estado[]` "
                        "con `id_estado` + `nombre` + `cantidad` para refrescar badges.")
def mis_resumen_edan(
    id_usuario: int | None = Query(None),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    uid = _user["id_usuario"] if _user["id_rol"] not in (1, 9) else (id_usuario or _user["id_usuario"])
    data = service.get_mis_resumen_edan(db, uid)
    return SuccessResponse(message="Resumen de mis EDAN generado correctamente", data=data or {})


@router.get("/mis-estados", tags=[TAG_EDAN],
            summary="Listado ligero de mis EDAN (solo estado, sin localidades)",
            description="Lista ligera para refrescar badges de `id_estado` (estado_edan): "
                        "cabecera + estado + tipo_evento, SIN localidades anidadas.")
def mis_estados_edan(
    id_usuario: int | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    uid = _user["id_usuario"] if _user["id_rol"] not in (1, 9) else (id_usuario or _user["id_usuario"])
    data, total = service.list_mis_edans_estados(db, uid, skip=skip, limit=limit)
    return SuccessResponse(message="Estados de mis EDAN listados correctamente", data=data, total=total)


# ============================================================================
#  SYNC EDAN + CONSOLIDAR PENDIENTES
# ============================================================================

@router.get("/consolidar/pendientes", tags=[TAG_EDAN_LOCALIDADES],
            responses={200: {"model": SuccessResponse}},
            summary="Listar EDAN localidades listas para consolidar",
            description="Devuelve las EDAN localidades huérfanas (id_edan IS NULL) agrupadas por\n"
                        "(municipio, tipo_evento), con conteos y totales agregados.\n\n"
                        "Por defecto muestra TODOS los estados. Use `estado` para filtrar\n"
                        "(ILIKE: 'aprobado' matchea 'Aprobado UGR' y 'Aprobado Ajuste UGR')\n"
                        "o `id_estado` para un estado específico.\n\n"
                        "El UGR municipio usa esto para decidir cuáles agrupar en un nuevo EDAN.")
def consolidar_pendientes(
    id_municipio: int | None = Query(None, description="Municipio del UGR (opcional)"),
    estado: str | None = Query(None, description="Estado de localidad (ILIKE, ej: 'aprobado')"),
    id_estado: int | None = Query(None, description="ID de estado específico"),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    data = service.listar_consolidables(db, id_municipio=id_municipio,
                                         estado_nombre=estado, id_estado=id_estado)
    return SuccessResponse(message="EDAN localidades consolidadas listadas correctamente",
                           data=data, total=len(data))


@router.post("/sync", tags=[TAG_EDAN],
             responses={200: {"model": SuccessResponse}},
             summary="Sincronizar EDANs (push desde móvil)",
             description="Recibe un lote de EDANs desde la app móvil. Por cada EDAN ejecuta un upsert.\n\n"
                         "La respuesta devuelve por fila: `aplicado`, `id_local`, `id_edan`, `conflicto`, "
                         "`tombstone`, `data`, `error`.")
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
                "error": db_error(exc).detail,
            })
    return SuccessResponse(message="EDANs sincronizados correctamente", data=results)


@router.get("/sync/pull", tags=[TAG_EDAN],
            responses={200: {"model": SuccessResponse}},
            summary="Descargar EDANs para móvil (pull)",
            description="Devuelve los EDANs del usuario. El móvil usa esto para convergencia offline-first.\n\n"
                        "Query `fecha_desde` (ISO timestamp) filtra por `fecha_modificacion >= fecha_desde`\n"
                        "para sincronización incremental.")
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


@router.get("/{id}", tags=[TAG_EDAN], summary="Obtener EDAN completo")
def obtener_edan(id: int, modo: str = Query("detallado"), db: Session = Depends(get_db), _user=Depends(get_current_user)):
    result = service.get_edan_completo(db, id, modo=modo)
    if not result:
        raise HTTPException(status_code=404, detail="EDAN no encontrado")
    return SuccessResponse(message="EDAN obtenido correctamente", data=result)


@router.post("/", status_code=201, tags=[TAG_EDAN], dependencies=[Depends(require_rol(*ROLES_EDAN_CREA))],
             summary="Crear un EDAN")
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
        raise db_error(e)


@router.put("/{id}", tags=[TAG_EDAN], dependencies=[Depends(require_rol(*ROLES_EDAN_CREA))],
            summary="Actualizar un EDAN")
def actualizar_edan(id: int, data: EdanUpdate, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    try:
        result = service.update_edan(db, id, data.model_dump(exclude_unset=True))
    except HTTPException:
        raise
    except Exception as e:
        raise db_error(e)
    if not result:
        raise HTTPException(status_code=404, detail="EDAN no encontrado")
    return SuccessResponse(message="EDAN actualizado correctamente", data=result)


@router.put("/{id}/estado", tags=[TAG_EDAN], dependencies=[Depends(require_rol(*ROLES_ESTADO_EDAN))],
            summary="Cambiar estado de EDAN")
def cambiar_estado_edan_endpoint(id: int, data: CambiarEstadoEdanIn, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    try:
        result = service.cambiar_estado_edan(db, id, data.id_estado)
    except HTTPException:
        raise
    except Exception as e:
        raise db_error(e)
    if not result:
        raise HTTPException(status_code=404, detail="EDAN no encontrado")
    return SuccessResponse(message="Estado de EDAN actualizado correctamente", data=result)


@router.delete("/{id}", tags=[TAG_EDAN], dependencies=[Depends(require_rol(*ROLES_EDAN_CREA))],
               summary="Eliminar un EDAN (lógico o permanente)")
def eliminar_edan(id: int, permanente: bool = Query(False), db: Session = Depends(get_db), _user=Depends(get_current_user)):
    if permanente:
        if not service.delete_edan(db, id):
            raise HTTPException(status_code=404, detail="EDAN no encontrado")
        return MessageResponse(message="EDAN eliminado permanentemente")
    result = service.soft_delete_edan(db, id)
    if not result:
        raise HTTPException(status_code=404, detail="EDAN no encontrado")
    return SuccessResponse(message="EDAN marcado para eliminación", data=result)


@router.put("/{id}/deshacer", tags=[TAG_EDAN], dependencies=[Depends(require_rol(*ROLES_LOCALES))],
            summary="Deshacer consolidación de un EDAN")
def deshacer_edan(id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    try:
        result = service.deshacer_consolidacion(db, id, _user["id_usuario"])
    except HTTPException:
        raise
    except Exception as e:
        raise db_error(e)
    return SuccessResponse(message="EDAN deshecho correctamente", data=result)


@router.post("/consolidar", tags=[TAG_EDAN_LOCALIDADES], dependencies=[Depends(require_rol(*ROLES_LOCALES))],
             summary="Consolidar EDAN localidades en un nuevo EDAN")
def consolidar(data: ConsolidarIn, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    try:
        result = service.consolidar(db, data.id_municipio, data.id_tipo_evento, data.localidad_ids, _user["id_usuario"])
    except HTTPException:
        raise
    except Exception as e:
        raise db_error(e)
    return SuccessResponse(message="EDAN consolidado correctamente", data=result)


@router.post("/consolidar/auto", tags=[TAG_EDAN_LOCALIDADES], dependencies=[Depends(require_rol(*ROLES_LOCALES))],
             summary="Consolidación automática de localidades")
def consolidar_auto_endpoint(id_municipio: int = Query(...), id_tipo_evento: int = Query(...),
                             db: Session = Depends(get_db), _user=Depends(get_current_user)):
    try:
        result = service.consolidar_auto(db, id_municipio, id_tipo_evento, _user["id_usuario"])
    except HTTPException:
        raise
    except Exception as e:
        raise db_error(e)
    return SuccessResponse(message="EDAN consolidado automáticamente", data=result)


@router.put("/localidades/{id_localidad}/desconsolidar", tags=[TAG_EDAN_LOCALIDADES],
            dependencies=[Depends(require_rol(*ROLES_LOCALES))], summary="Desconsolidar una localidad")
def desconsolidar_endpoint(id_localidad: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    try:
        result = service.desconsolidar(db, id_localidad)
    except HTTPException:
        raise
    except Exception as e:
        raise db_error(e)
    return SuccessResponse(message="Localidad desconsolidada correctamente", data=result)


@router.put("/localidades/{id_localidad}/estado", tags=[TAG_EDAN_LOCALIDADES],
            dependencies=[Depends(require_rol(*ROLES_LOCALES))], summary="Cambiar estado de localidad (por id_edan_localidad)")
def cambiar_estado_localidad_endpoint(id_localidad: int, data: LocalidadEstadoUpdate,
                                       db: Session = Depends(get_db), _user=Depends(get_current_user)):
    try:
        result = service.cambiar_estado_localidad(db, id_localidad, data.id_edan_localidad_estado)
    except HTTPException:
        raise
    except Exception as e:
        raise db_error(e)
    if not result:
        raise HTTPException(status_code=404, detail="Localidad no encontrada")
    return SuccessResponse(message="Estado de localidad actualizado correctamente", data=result)
