from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..dependencies import get_current_user
from ..database import get_db
from ..response import SuccessResponse, MessageResponse
from . import service
from .schemas import (
    EdanUpdateV2, ConsolidarIn, CambiarEstadoEdanIn, LocalidadEstadoUpdate,
    ResumenReporteResponse, ReporteGeografiaResponse, ReporteAgriculturaResponse,
    ReportePecuarioResponse, MisResumenResponse,
)
from .utils import require_rol, db_error
from ..auth.permisos import module_permiso

router = APIRouter(prefix="/edan", dependencies=[Depends(module_permiso("EDAN"))])

TAG_EDAN = "EDAN"
TAG_EDAN_LOCALIDADES = "EDAN_LOCALIDADES"

ROLES_EDAN_CREA = (1, 2, 3, 4, 5, 9)
ROLES_ESTADO_EDAN = (1, 2, 3, 4, 5, 9)
ROLES_LOCALES = (6, 7)
ROLES_ASIGNA_ALCALDE = (6, 7)
PU_ALCALDE_ONLY_FIELDS = {"id_usuario_alcalde"}


def _filtros_dep_factory(forzar_scope: bool = True):
    """Dependencia de filtros de EDAN. Con `forzar_scope=True` los roles
    6/7 ven SOLO sus EDAN (id_usuario_ugr propio); con `False` los reportes
    agregados quedan ABIERTOS (todas las localidades de todos)."""
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
        if forzar_scope and user["id_rol"] not in (1, 9) and f.get("id_usuario_ugr") is None:
            f["id_usuario_ugr"] = user["id_usuario"]
        return f

    return _filtros_dep


_filtros_dep = _filtros_dep_factory(forzar_scope=True)
_filtros_dep_abierto = _filtros_dep_factory(forzar_scope=False)


# ----------------------------------------------------------------------------
#  REPORTES (solo totales/agregados) — antes de /{id} para no capturar rutas
#  Filtros ABIERTOS: reportes sobre TODAS las localidades (huérfanas +
#  consolidadas), sin scope por rol. Filtrar por geografía con ?id_departamento=,
#  ?id_provincia=, ?id_municipio=.
# ----------------------------------------------------------------------------

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
            response_model=ResumenReporteResponse,
            summary="Reporte resumen de localidades (totales agregados con filtros)",
            description="Totales agregados sobre TODAS las localidades (huérfanas + consolidadas) con "
                        "filtros (geografía, tipo_evento, estado de localidad, fechas, flags): "
                        "`totales`, `por_estado[]`, `por_tipo_evento[]`. Reportes abiertos: sin scope por rol.")
def reportes_resumen_edan(
    f: dict = Depends(_filtros_dep_abierto),
    db: Session = Depends(get_db),
):
    data = service.reporte_resumen(db, f) or {}
    return ResumenReporteResponse(message="Resumen de localidades generado correctamente", data=data)


@router.get("/reportes/geografico", tags=[TAG_EDAN],
            response_model=ReporteGeografiaResponse,
            summary="Reporte geográfico de localidades (agrupado por d/p/m)",
            description="Localidades agrupadas por departamento/provincia/municipio con totales "
                        "acumulados, desglose de huérfanas/consolidadas. Reportes abiertos.")
def reportes_geografico_edan(
    f: dict = Depends(_filtros_dep_abierto),
    db: Session = Depends(get_db),
):
    data = service.reporte_geografico(db, f) or []
    return ReporteGeografiaResponse(message="Reporte geográfico generado correctamente",
                                    data=data, total=len(data))


@router.get("/reportes/agricultura", tags=[TAG_EDAN],
            response_model=ReporteAgriculturaResponse,
            summary="Reporte de daños a agricultura (agregado)",
            description="Hectáreas afectadas/perdidas por cultivo, sobre TODAS las localidades. "
                        "Reportes abiertos.")
def reportes_agricultura_edan(
    f: dict = Depends(_filtros_dep_abierto),
    db: Session = Depends(get_db),
):
    data = service.reporte_agricultura(db, f) or []
    return ReporteAgriculturaResponse(message="Reporte de agricultura generado correctamente",
                                      data=data, total=len(data))


@router.get("/reportes/pecuario", tags=[TAG_EDAN],
            response_model=ReportePecuarioResponse,
            summary="Reporte de daños pecuarios (agregado)",
            description="Animales afectados/muertos por especie, sobre TODAS las localidades. "
                        "Reportes abiertos.")
def reportes_pecuario_edan(
    f: dict = Depends(_filtros_dep_abierto),
    db: Session = Depends(get_db),
):
    data = service.reporte_pecuario(db, f) or []
    return ReportePecuarioResponse(message="Reporte de pecuario generado correctamente",
                                   data=data, total=len(data))


@router.get("/", tags=[TAG_EDAN], summary="Listar EDANs con filtros")
def listar_edans(f: dict = Depends(_filtros_dep), skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=500),
                 db: Session = Depends(get_db), _user=Depends(get_current_user)):
    data, total = service.get_edans(db, dict(f), skip=skip, limit=limit)
    return SuccessResponse(message="EDANs listados correctamente", data=data, total=total)


@router.get("/mis-resumen", tags=[TAG_EDAN], response_model=MisResumenResponse,
            summary="Resumen de mis EDAN (totales + por estado_edan)",
            description="Totales agregados de los EDAN del usuario (grupos consolidados) y desglose "
                        "`por_estado[]` con `id_estado` + `nombre` + `cantidad` para refrescar badges, "
                        "según `estado_edan`. Scope: rol 6/7 ve lo propio; otro rol usa `?id_usuario=`.")
def mis_resumen_edan(
    id_usuario: int | None = Query(None),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    uid = _user["id_usuario"] if _user["id_rol"] not in (1, 9) else (id_usuario or _user["id_usuario"])
    data = service.get_mis_resumen_edan(db, uid)
    return MisResumenResponse(message="Resumen de mis EDAN generado correctamente", data=data or {})


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


@router.get("/mis-reportes", tags=[TAG_EDAN],
            summary="Listar mis EDAN (cabecera + localidades)",
            description="Lista los EDAN del usuario con su estructura completa (cabecera + localidades). "
                        "Ruta a nivel raíz para no ser capturada por `GET /{id}`. "
                        "Scope: rol 6/7 ve lo propio; otro rol usa `?id_usuario=`.")
def mis_reportes_edan(
    id_usuario: int | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    uid = _user["id_usuario"] if _user["id_rol"] not in (1, 9) else (id_usuario or _user["id_usuario"])
    data, total = service.get_mis_edans(db, uid, skip=skip, limit=limit)
    return SuccessResponse(message="Reportes EDAN del usuario listados correctamente", data=data, total=total)


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




@router.get("/{id}", tags=[TAG_EDAN],
            summary="Obtener EDAN completo (detallado o compacto)",
            description="Devuelve la cabecera del EDAN + localidades + resumen por secciones.\n\n"
                        "**`modo=detallado`** (default): cabecera + `localidades[]` completas (las 14\n"
                        "secciones, tengan datos o no) + `resumen_secciones` + `reportes_rea`.\n"
                        "**`modo=compacto`**: cabecera + `localidades[]` en formato **comprimido**\n"
                        "(los 22 flags `imp_*` + SOLO las secciones con datos, igual que localidad v2)\n"
                        "+ `sumatorias` (totales por sección del EDAN) + `resumen_secciones` + `reportes_rea`.")
def obtener_edan(id: int, modo: Literal["detallado", "compacto"] = Query(
        "detallado", description="detallado=localidades con las 14 secciones; "
                                 "compacto=localidades solo con secciones con datos + sumatorias"),
        db: Session = Depends(get_db), _user=Depends(get_current_user)):
    result = service.get_edan_completo(db, id, modo=modo)
    if not result:
        raise HTTPException(status_code=404, detail="EDAN no encontrado")
    return SuccessResponse(message="EDAN obtenido correctamente", data=result)


@router.put("/{id}", tags=[TAG_EDAN],
            summary="Actualizar un EDAN",
            description="Actualiza las columnas reales de `edan.edan`. PUT parcial: basta enviar\n"
                        "solo los campos a cambiar. `id_usuario_alcalde` (int) asigna el alcalde;\n"
                        "los datos de contacto del responsable se leen por JOIN con `usuarios.usuario`.\n\n"
                        "**Roles 6 y 7 (UGR Municipio / Responsable Local):** solo pueden enviar\n"
                        "`id_usuario_alcalde`; cualquier otro campo devuelve 403. Roles 1-5 y 9\n"
                        "pueden editar todas las columnas.")
def actualizar_edan(id: int, data: EdanUpdateV2, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    rol = _user.get("id_rol")
    if rol not in ROLES_EDAN_CREA and rol not in ROLES_ASIGNA_ALCALDE:
        raise HTTPException(
            status_code=403,
            detail=f"Rol {rol} no autorizado para actualizar EDAN. Roles permitidos: "
                   f"{ROLES_EDAN_CREA} o {ROLES_ASIGNA_ALCALDE} (solo id_usuario_alcalde)",
        )
    payload = data.model_dump(exclude_unset=True)
    if rol not in ROLES_EDAN_CREA:
        no_permitidos = set(payload) - PU_ALCALDE_ONLY_FIELDS
        if no_permitidos:
            raise HTTPException(
                status_code=403,
                detail=f"Rol {rol} solo puede modificar id_usuario_alcalde. "
                       f"Campos no permitidos: {', '.join(sorted(no_permitidos))}",
            )
    try:
        result = service.update_edan(db, id, payload)
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
