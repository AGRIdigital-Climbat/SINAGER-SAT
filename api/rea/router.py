from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..database import get_db
from ..dependencies import get_current_user
from .schemas import *
from . import service

router = APIRouter(prefix="/rea", tags=["REA - Reportes Eventos Adversos"])


# ── REPORTES ──

@router.get("/reportes", response_model=list[ReporteEventoResponse])
def listar_reportes(
    id_estado: int | None = Query(None),
    id_municipio: int | None = Query(None),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    return service.get_reportes(db, id_estado, id_municipio, skip, limit)


@router.get("/reportes/{id}")
def obtener_reporte(id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    result = service.get_reporte_completo(db, id)
    if not result:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")
    return result


@router.post("/reportes", status_code=201)
def crear_reporte(data: ReporteEventoCreate, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    try:
        reporte_id = service.create_reporte(db, data.model_dump())
        return service.get_reporte_completo(db, reporte_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/reportes/{id}")
def actualizar_reporte(id: int, data: ReporteEventoUpdate, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    result = service.update_reporte(db, id, data.model_dump(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")
    return result


@router.put("/reportes/{id}/estado")
def cambiar_estado(id: int, data: CambiarEstadoRequest, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    result = service.change_estado(db, id, data.id_estado)
    if not result:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")
    return result


@router.delete("/reportes/{id}")
def eliminar_reporte(id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    if not service.delete_reporte(db, id):
        raise HTTPException(status_code=404, detail="Reporte no encontrado")
    return MessageResponse(message="Reporte eliminado")


# ── ESTADOS ──

@router.get("/estados", response_model=list[EstadoReporteResponse])
def listar_estados(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    return service.get_estados(db)


@router.get("/estados/{id}", response_model=EstadoReporteResponse)
def obtener_estado(id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    result = service.get_estado(db, id)
    if not result:
        raise HTTPException(status_code=404, detail="Estado no encontrado")
    return result


@router.post("/estados", response_model=EstadoReporteResponse, status_code=201)
def crear_estado(data: EstadoReporteCreate, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    id = service.create_estado(db, data.model_dump())
    return service.get_estado(db, id)


@router.put("/estados/{id}", response_model=EstadoReporteResponse)
def actualizar_estado(id: int, data: EstadoReporteUpdate, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    result = service.update_estado(db, id, data.model_dump(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="Estado no encontrado")
    return result


@router.delete("/estados/{id}")
def eliminar_estado(id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    if not service.delete_estado(db, id):
        raise HTTPException(status_code=404, detail="Estado no encontrado")
    return MessageResponse(message="Estado eliminado")


# ── CATEGORIAS AFECTACION ──

@router.get("/categorias", response_model=list[AfectacionCategoriaResponse])
def listar_categorias(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    return service.get_categorias(db)


@router.get("/categorias/{id}", response_model=AfectacionCategoriaResponse)
def obtener_categoria(id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    result = service.get_categoria(db, id)
    if not result:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    return result


@router.post("/categorias", response_model=AfectacionCategoriaResponse, status_code=201)
def crear_categoria(data: AfectacionCategoriaCreate, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    id = service.create_categoria(db, data.model_dump())
    return service.get_categoria(db, id)


@router.put("/categorias/{id}", response_model=AfectacionCategoriaResponse)
def actualizar_categoria(id: int, data: AfectacionCategoriaUpdate, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    result = service.update_categoria(db, id, data.model_dump(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    return result


@router.delete("/categorias/{id}")
def eliminar_categoria(id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    if not service.delete_categoria(db, id):
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    return MessageResponse(message="Categoría eliminada")
