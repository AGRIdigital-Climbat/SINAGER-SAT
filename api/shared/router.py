from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..response import SuccessResponse, MessageResponse
from .schemas import (
    DepartamentoCreate, DepartamentoUpdate, DepartamentoResponse,
    ProvinciaCreate, ProvinciaUpdate, ProvinciaResponse,
    MunicipioCreate, MunicipioUpdate, MunicipioResponse,
)
from . import service

router = APIRouter(prefix="/shared")

TAG = "Geografía > Departamentos"


@router.get("/departamentos", response_model=SuccessResponse, tags=[TAG])
def listar_departamentos(db: Session = Depends(get_db)):
    items = service.get_departamentos(db)
    return SuccessResponse(message="Operación exitosa", data=items, total=len(items))


@router.get("/departamentos/{id}", response_model=SuccessResponse, tags=[TAG])
def obtener_departamento(id: int, db: Session = Depends(get_db)):
    result = service.get_departamento(db, id)
    if not result:
        raise HTTPException(status_code=404, detail="Departamento no encontrado")
    return SuccessResponse(message="Operación exitosa", data=result)


@router.post("/departamentos", response_model=SuccessResponse, status_code=201, tags=[TAG])
def crear_departamento(data: DepartamentoCreate, db: Session = Depends(get_db)):
    try:
        id = service.create_departamento(db, data)
        result = service.get_departamento(db, id)
        return SuccessResponse(message="Departamento creado exitosamente", data=result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/departamentos/{id}", response_model=SuccessResponse, tags=[TAG])
def actualizar_departamento(id: int, data: DepartamentoUpdate, db: Session = Depends(get_db)):
    result = service.update_departamento(db, id, data)
    if not result:
        raise HTTPException(status_code=404, detail="Departamento no encontrado")
    return SuccessResponse(message="Departamento actualizado exitosamente", data=result)


@router.delete("/departamentos/{id}", response_model=SuccessResponse, tags=[TAG])
def eliminar_departamento(id: int, db: Session = Depends(get_db)):
    if not service.delete_departamento(db, id):
        raise HTTPException(status_code=404, detail="Departamento no encontrado")
    return SuccessResponse(message="Departamento eliminado")


TAG = "Geografía > Provincias"


@router.get("/provincias", response_model=SuccessResponse, tags=[TAG])
def listar_provincias(
    id_departamento: int | None = Query(None),
    db: Session = Depends(get_db),
):
    items = service.get_provincias(db, id_departamento)
    return SuccessResponse(message="Operación exitosa", data=items, total=len(items))


@router.get("/provincias/{id}", response_model=SuccessResponse, tags=[TAG])
def obtener_provincia(id: int, db: Session = Depends(get_db)):
    result = service.get_provincia(db, id)
    if not result:
        raise HTTPException(status_code=404, detail="Provincia no encontrada")
    return SuccessResponse(message="Operación exitosa", data=result)


@router.post("/provincias", response_model=SuccessResponse, status_code=201, tags=[TAG])
def crear_provincia(data: ProvinciaCreate, db: Session = Depends(get_db)):
    try:
        id = service.create_provincia(db, data)
        result = service.get_provincia(db, id)
        return SuccessResponse(message="Provincia creada exitosamente", data=result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/provincias/{id}", response_model=SuccessResponse, tags=[TAG])
def actualizar_provincia(id: int, data: ProvinciaUpdate, db: Session = Depends(get_db)):
    result = service.update_provincia(db, id, data)
    if not result:
        raise HTTPException(status_code=404, detail="Provincia no encontrada")
    return SuccessResponse(message="Provincia actualizada exitosamente", data=result)


@router.delete("/provincias/{id}", response_model=SuccessResponse, tags=[TAG])
def eliminar_provincia(id: int, db: Session = Depends(get_db)):
    if not service.delete_provincia(db, id):
        raise HTTPException(status_code=404, detail="Provincia no encontrada")
    return SuccessResponse(message="Provincia eliminada")


TAG = "Geografía > Municipios"


@router.get("/municipios", response_model=SuccessResponse, tags=[TAG])
def listar_municipios(
    id_provincia: int | None = Query(None),
    id_departamento: int | None = Query(None),
    db: Session = Depends(get_db),
):
    items = service.get_municipios(db, id_provincia, id_departamento)
    return SuccessResponse(message="Operación exitosa", data=items, total=len(items))


@router.get("/municipios/{id}", response_model=SuccessResponse, tags=[TAG])
def obtener_municipio(id: int, db: Session = Depends(get_db)):
    result = service.get_municipio(db, id)
    if not result:
        raise HTTPException(status_code=404, detail="Municipio no encontrado")
    return SuccessResponse(message="Operación exitosa", data=result)


@router.post("/municipios", response_model=SuccessResponse, status_code=201, tags=[TAG])
def crear_municipio(data: MunicipioCreate, db: Session = Depends(get_db)):
    try:
        id = service.create_municipio(db, data)
        result = service.get_municipio(db, id)
        return SuccessResponse(message="Municipio creado exitosamente", data=result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/municipios/{id}", response_model=SuccessResponse, tags=[TAG])
def actualizar_municipio(id: int, data: MunicipioUpdate, db: Session = Depends(get_db)):
    result = service.update_municipio(db, id, data)
    if not result:
        raise HTTPException(status_code=404, detail="Municipio no encontrado")
    return SuccessResponse(message="Municipio actualizado exitosamente", data=result)


@router.delete("/municipios/{id}", response_model=SuccessResponse, tags=[TAG])
def eliminar_municipio(id: int, db: Session = Depends(get_db)):
    if not service.delete_municipio(db, id):
        raise HTTPException(status_code=404, detail="Municipio no encontrado")
    return SuccessResponse(message="Municipio eliminado")
