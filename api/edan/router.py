from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session
from ..database import get_db
from ..dependencies import get_current_user
from ..auth.permisos import module_permiso
from ..response import SuccessResponse, MessageResponse
from . import service
from .schemas import *

router = APIRouter(prefix="/edan", dependencies=[Depends(module_permiso("EDAN"))])

TAG_MAIN     = "EDAN > Formulario"
TAG_LOCAL    = "EDAN > Localidades"
TAG_REPORTES = "EDAN > Reportes"
TAG_CATALOG  = "EDAN > Catálogos"


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
    id_usuario: int | None = None,
    fecha_evento_desde: str | None = None,
    fecha_evento_hasta: str | None = None,
    fecha_creacion_desde: str | None = None,
    fecha_creacion_hasta: str | None = None,
    sincronizado: bool | None = None,
    es_borrador: bool | None = None,
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
        "id_estado": id_estado, "estado": estado, "id_usuario": id_usuario,
        "fecha_evento_desde": fecha_evento_desde,
        "fecha_evento_hasta": fecha_evento_hasta,
        "fecha_creacion_desde": fecha_creacion_desde,
        "fecha_creacion_hasta": fecha_creacion_hasta,
        "sincronizado": sincronizado, "es_borrador": es_borrador,
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
    id_usuario: int | None = Query(None),
    fecha_evento_desde: str | None = Query(None),
    fecha_evento_hasta: str | None = Query(None),
    fecha_creacion_desde: str | None = Query(None),
    fecha_creacion_hasta: str | None = Query(None),
    sincronizado: bool | None = Query(None),
    es_borrador: bool | None = Query(None),
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
        id_estado=id_estado, estado=estado, id_usuario=id_usuario,
        fecha_evento_desde=fecha_evento_desde, fecha_evento_hasta=fecha_evento_hasta,
        fecha_creacion_desde=fecha_creacion_desde, fecha_creacion_hasta=fecha_creacion_hasta,
        sincronizado=sincronizado, es_borrador=es_borrador,
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

@router.get("/reportes/resumen", tags=[TAG_REPORTES], responses={200: {"model": SuccessResponse}})
def reporte_resumen(
    f: dict = Depends(_filtros_dep),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    data = service.reporte_resumen(db, f)
    return SuccessResponse(message="Resumen EDAN generado correctamente", data=data)


@router.get("/reportes/geografico", tags=[TAG_REPORTES], responses={200: {"model": SuccessResponse}})
def reporte_geografico(
    f: dict = Depends(_filtros_dep),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    data = service.reporte_geografico(db, f)
    return SuccessResponse(message="Reporte geográfico generado correctamente", data=data, total=len(data))


@router.get("/reportes/agricultura", tags=[TAG_REPORTES], responses={200: {"model": SuccessResponse}})
def reporte_agricultura(
    f: dict = Depends(_filtros_dep),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    data = service.reporte_agricultura(db, f)
    return SuccessResponse(message="Reporte de agricultura generado correctamente", data=data, total=len(data))


@router.get("/reportes/pecuario", tags=[TAG_REPORTES], responses={200: {"model": SuccessResponse}})
def reporte_pecuario(
    f: dict = Depends(_filtros_dep),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    data = service.reporte_pecuario(db, f)
    return SuccessResponse(message="Reporte de pecuario generado correctamente", data=data, total=len(data))


@router.get("/reportes/localidades", tags=[TAG_REPORTES], responses={200: {"model": SuccessResponse}})
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
                     TipoEventoCreate, TipoEventoUpdate, "Tipo de evento", TAG_CATALOG)

_catalog_crud_routes(router, "estados", service.estado_edan_crud,
                     EstadoEdanCreate, EstadoEdanUpdate, "Estado EDAN", TAG_CATALOG)


# ============================================================================
#  EDAN PRINCIPAL
# ============================================================================

@router.get("/", tags=[TAG_MAIN], responses={200: {"model": SuccessResponse}})
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


@router.get("/{id}", tags=[TAG_MAIN], responses={200: {"model": SuccessResponse}})
def obtener_edan(id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    result = service.get_edan_completo(db, id)
    if not result:
        raise HTTPException(status_code=404, detail="EDAN no encontrado")
    return SuccessResponse(message="EDAN obtenido correctamente", data=result)


@router.post("/", status_code=201, tags=[TAG_MAIN], responses={201: {"model": SuccessResponse}})
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


@router.put("/{id}", tags=[TAG_MAIN], responses={200: {"model": SuccessResponse}})
def actualizar_edan(id: int, data: EdanUpdate, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    try:
        result = service.update_edan(db, id, data.model_dump())
    except Exception as e:
        raise _db_error(e)
    if not result:
        raise HTTPException(status_code=404, detail="EDAN no encontrado")
    return SuccessResponse(message="EDAN actualizado correctamente", data=result)


@router.delete("/{id}", tags=[TAG_MAIN], responses={200: {"model": MessageResponse}})
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

@router.get("/{id}/localidades", tags=[TAG_LOCAL], responses={200: {"model": SuccessResponse}})
def listar_localidades(id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    if not service.get_edan(db, id):
        raise HTTPException(status_code=404, detail="EDAN no encontrado")
    data = service._get_localidades(db, id)
    return SuccessResponse(message="Localidades listadas correctamente", data=data, total=len(data))


@router.post("/{id}/localidades", status_code=201, tags=[TAG_LOCAL], responses={201: {"model": SuccessResponse}})
def crear_localidad(id: int, data: LocalidadCreate, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    if not service.get_edan(db, id):
        raise HTTPException(status_code=404, detail="EDAN no encontrado")
    try:
        lid = service._insert_localidad(db, id, data.model_dump())
        db.commit()
        result = service._build_localidad(db, lid)
        return SuccessResponse(message="Localidad creada correctamente", data=result)
    except Exception as e:
        db.rollback()
        raise _db_error(e)


@router.put("/{id}/localidades/{id_localidad}", tags=[TAG_LOCAL], responses={200: {"model": SuccessResponse}})
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


@router.delete("/{id}/localidades/{id_localidad}", tags=[TAG_LOCAL], responses={200: {"model": MessageResponse}})
def eliminar_localidad(id: int, id_localidad: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    result = db.execute(
        text("DELETE FROM edan.edan_localidades WHERE id_edan_localidad = :id"),
        {"id": id_localidad},
    )
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Localidad no encontrada")
    return MessageResponse(message="Localidad eliminada correctamente")
