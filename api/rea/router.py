from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..database import get_db
from ..dependencies import get_current_user
from ..response import SuccessResponse, MessageResponse
from .schemas import *
from . import service

router = APIRouter(prefix="/rea")

TAG_REP = "REA > Reportes"
TAG_EST = "REA > Estados"
TAG_CAT = "REA > Categorías"


@router.get("/reportes", tags=[TAG_REP], responses={200: {"model": SuccessResponse}})
def listar_reportes(
    id_estado: int | None = Query(None),
    id_municipio: int | None = Query(None),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    data = service.get_reportes(db, id_estado, id_municipio, skip, limit)
    return SuccessResponse(message="Reportes listados correctamente", data=data, total=len(data))


@router.get("/reportes/{id}", tags=[TAG_REP], responses={200: {"model": SuccessResponse}})
def obtener_reporte(id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    result = service.get_reporte_completo(db, id)
    if not result:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")
    return SuccessResponse(message="Reporte obtenido correctamente", data=result)


@router.post("/reportes", status_code=201, tags=[TAG_REP], responses={201: {"model": SuccessResponse}})
def crear_reporte(data: ReporteEventoCreate, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    try:
        reporte_id = service.create_reporte(db, data.model_dump())
        result = service.get_reporte_completo(db, reporte_id)
        return SuccessResponse(message="Reporte creado correctamente", data=result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/reportes/{id}", tags=[TAG_REP], responses={200: {"model": SuccessResponse}})
def actualizar_reporte(id: int, data: ReporteEventoUpdate, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    result = service.update_reporte(db, id, data.model_dump(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")
    return SuccessResponse(message="Reporte actualizado correctamente", data=result)


@router.put("/reportes/{id}/estado", tags=[TAG_REP], responses={200: {"model": SuccessResponse}})
def cambiar_estado(id: int, data: CambiarEstadoRequest, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    result = service.change_estado(db, id, data.id_estado)
    if not result:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")
    return SuccessResponse(message="Estado del reporte actualizado correctamente", data=result)


@router.delete("/reportes/{id}", tags=[TAG_REP], responses={200: {"model": MessageResponse}})
def eliminar_reporte(id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
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
