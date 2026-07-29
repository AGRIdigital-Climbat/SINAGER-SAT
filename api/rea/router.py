import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import text
from sqlalchemy.orm import Session
from ..database import get_db
from ..dependencies import get_current_user
from ..auth.permisos import module_permiso
from ..response import SuccessResponse, MessageResponse
from ..upload import save_upload_file
from .schemas import *
from . import service

router = APIRouter(prefix="/rea", dependencies=[Depends(module_permiso("REA"))])

TAG_REP = "REA > Reportes"
TAG_EST = "REA > Estados"
TAG_CAT = "REA > Categorías"

ROLES_BAJOS = (6, 7)


@router.get("/reportes", tags=[TAG_REP], responses={200: {"model": SuccessResponse}})
def listar_reportes(
    id_estado: int | None = Query(None),
    id_municipio: int | None = Query(None),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    data, total = service.get_reportes(db, id_estado, id_municipio, skip, limit)
    return SuccessResponse(message="Reportes listados correctamente", data=data, total=total)


@router.get("/reportes/mis-resumen", tags=[TAG_REP], responses={200: {"model": SuccessResponse}})
def mis_resumen(
    id_usuario: int | None = Query(None),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    uid = _user["id_usuario"] if _user["id_rol"] in ROLES_BAJOS else (id_usuario or _user["id_usuario"])
    data, total = service.get_mis_resumen(db, uid, skip, limit)
    return SuccessResponse(message="Resumen de reportes del usuario listado correctamente", data=data, total=total)


@router.get("/reportes/mis-reportes", tags=[TAG_REP], responses={200: {"model": SuccessResponse}})
def mis_reportes(
    id_usuario: int | None = Query(None),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    uid = _user["id_usuario"] if _user["id_rol"] in ROLES_BAJOS else (id_usuario or _user["id_usuario"])
    data, total = service.get_mis_reportes(db, uid, skip, limit)
    return SuccessResponse(message="Reportes del usuario listados correctamente", data=data, total=total)


@router.get("/reportes/{id}", tags=[TAG_REP], responses={200: {"model": SuccessResponse}})
def obtener_reporte(id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    result = service.get_reporte_completo(db, id)
    if not result:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")
    return SuccessResponse(message="Reporte obtenido correctamente", data=result)


@router.post("/reportes", status_code=201, tags=[TAG_REP], responses={201: {"model": SuccessResponse}})
def crear_reporte(data: ReporteEventoCreate, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    try:
        if _user["id_rol"] in ROLES_BAJOS:
            data.id_usuario = _user["id_usuario"]
        reporte_id = service.create_reporte(db, data.model_dump())
        result = service.get_reporte_completo(db, reporte_id)
        return SuccessResponse(message="Reporte creado correctamente", data=result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/reportes/con-foto", status_code=201, tags=[TAG_REP], responses={201: {"model": SuccessResponse}})
async def crear_reporte_con_foto(
    file: UploadFile = File(...),
    id_usuario: int = Form(...),
    id_departamento: int = Form(...),
    id_provincia: int = Form(...),
    id_municipio: int = Form(...),
    comunidad: str = Form(...),
    fecha_evento: str = Form(...),
    hora_evento: str | None = Form(None),
    id_tipo_evento: int = Form(...),
    coordenada_lat: float | None = Form(None),
    coordenada_lon: float | None = Form(None),
    descripcion: str | None = Form(None),
    id_estado: int = Form(1),
    categorias: str | None = Form(None),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        fotografia = await save_upload_file(file, db, id_municipio, comunidad)

        cat_list = json.loads(categorias) if categorias else None

        uid = _user["id_usuario"] if _user["id_rol"] in ROLES_BAJOS else id_usuario

        data = {
            "id_usuario": uid,
            "id_departamento": id_departamento,
            "id_provincia": id_provincia,
            "id_municipio": id_municipio,
            "comunidad": comunidad,
            "fecha_evento": fecha_evento,
            "hora_evento": hora_evento,
            "id_tipo_evento": id_tipo_evento,
            "coordenada_lat": coordenada_lat,
            "coordenada_lon": coordenada_lon,
            "fotografia": fotografia,
            "descripcion": descripcion,
            "id_estado": id_estado,
            "categorias": cat_list,
        }

        reporte_id = service.create_reporte(db, data)
        result = service.get_reporte_completo(db, reporte_id)
        return SuccessResponse(message="Reporte creado correctamente", data=result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/reportes/{id}", tags=[TAG_REP], responses={200: {"model": SuccessResponse}})
def actualizar_reporte(id: int, data: ReporteEventoUpdate, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    if _user["id_rol"] in ROLES_BAJOS:
        reporte = service.get_reporte(db, id)
        if not reporte or reporte["id_usuario"] != _user["id_usuario"]:
            raise HTTPException(status_code=403, detail="No puedes modificar un reporte que no te pertenece")
    result = service.update_reporte(db, id, data.model_dump(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")
    return SuccessResponse(message="Reporte actualizado correctamente", data=result)


@router.put("/reportes/{id}/estado", tags=[TAG_REP], responses={200: {"model": SuccessResponse}})
def cambiar_estado(id: int, data: CambiarEstadoRequest, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    if _user["id_rol"] <= 5:
        result = service.change_estado(db, id, data.id_estado)
        if not result:
            raise HTTPException(status_code=404, detail="Reporte no encontrado")
        return SuccessResponse(message="Estado del reporte actualizado correctamente", data=result)

    reporte = service.get_reporte(db, id)
    if not reporte:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")

    if _user["id_rol"] == 7:
        if reporte["id_usuario"] != _user["id_usuario"]:
            raise HTTPException(status_code=403, detail="No puedes cambiar el estado de un reporte que no te pertenece")

    if _user["id_rol"] == 6:
        creador = db.execute(
            text("SELECT id_rol FROM usuarios.usuario WHERE id_usuario = :id"),
            {"id": reporte["id_usuario"]},
        ).mappings().first()
        if not creador or creador["id_rol"] != 7:
            raise HTTPException(status_code=403, detail="Solo puedes cambiar estado de reportes de Responsables Locales")
        if reporte["id_municipio"] != _user["id_municipio"]:
            raise HTTPException(status_code=403, detail="No puedes cambiar estado de reportes de otro municipio")

    result = service.change_estado(db, id, data.id_estado)
    if not result:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")
    return SuccessResponse(message="Estado del reporte actualizado correctamente", data=result)


@router.delete("/reportes/{id}", tags=[TAG_REP], responses={200: {"model": MessageResponse}})
def eliminar_reporte(id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    if _user["id_rol"] in ROLES_BAJOS:
        reporte = service.get_reporte(db, id)
        if not reporte or reporte["id_usuario"] != _user["id_usuario"]:
            raise HTTPException(status_code=403, detail="No puedes eliminar un reporte que no te pertenece")
    if not service.delete_reporte(db, id):
        raise HTTPException(status_code=404, detail="Reporte no encontrado")
    return MessageResponse(message="Reporte eliminado correctamente")


@router.get("/estados", tags=[TAG_EST], responses={200: {"model": SuccessResponse}})
def listar_estados(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    data = service.get_estados(db)
    return SuccessResponse(message="Estados listados correctamente", data=data, total=len(data))


@router.get("/estados/{id}", tags=[TAG_EST], responses={200: {"model": SuccessResponse}})
def obtener_estado(id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    result = service.get_estado(db, id)
    if not result:
        raise HTTPException(status_code=404, detail="Estado no encontrado")
    return SuccessResponse(message="Estado obtenido correctamente", data=result)


@router.post("/estados", status_code=201, tags=[TAG_EST], responses={201: {"model": SuccessResponse}})
def crear_estado(data: EstadoReporteCreate, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    id = service.create_estado(db, data.model_dump())
    result = service.get_estado(db, id)
    return SuccessResponse(message="Estado creado correctamente", data=result)


@router.put("/estados/{id}", tags=[TAG_EST], responses={200: {"model": SuccessResponse}})
def actualizar_estado(id: int, data: EstadoReporteUpdate, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    result = service.update_estado(db, id, data.model_dump(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="Estado no encontrado")
    return SuccessResponse(message="Estado actualizado correctamente", data=result)


@router.delete("/estados/{id}", tags=[TAG_EST], responses={200: {"model": MessageResponse}})
def eliminar_estado(id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    if not service.delete_estado(db, id):
        raise HTTPException(status_code=404, detail="Estado no encontrado")
    return MessageResponse(message="Estado eliminado correctamente")


@router.get("/categorias", tags=[TAG_CAT], responses={200: {"model": SuccessResponse}})
def listar_categorias(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    data = service.get_categorias(db)
    return SuccessResponse(message="Categorías listadas correctamente", data=data, total=len(data))


@router.get("/categorias/{id}", tags=[TAG_CAT], responses={200: {"model": SuccessResponse}})
def obtener_categoria(id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    result = service.get_categoria(db, id)
    if not result:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    return SuccessResponse(message="Categoría obtenida correctamente", data=result)


@router.post("/categorias", status_code=201, tags=[TAG_CAT], responses={201: {"model": SuccessResponse}})
def crear_categoria(data: AfectacionCategoriaCreate, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    id = service.create_categoria(db, data.model_dump())
    result = service.get_categoria(db, id)
    return SuccessResponse(message="Categoría creada correctamente", data=result)


@router.put("/categorias/{id}", tags=[TAG_CAT], responses={200: {"model": SuccessResponse}})
def actualizar_categoria(id: int, data: AfectacionCategoriaUpdate, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    result = service.update_categoria(db, id, data.model_dump(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    return SuccessResponse(message="Categoría actualizada correctamente", data=result)


@router.delete("/categorias/{id}", tags=[TAG_CAT], responses={200: {"model": MessageResponse}})
def eliminar_categoria(id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    if not service.delete_categoria(db, id):
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    return MessageResponse(message="Categoría eliminada correctamente")
