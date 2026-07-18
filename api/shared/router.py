from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from ..database import get_db
from .schemas import (
    DepartamentoCreate, DepartamentoUpdate, DepartamentoResponse,
    ProvinciaCreate, ProvinciaUpdate, ProvinciaResponse,
    MunicipioCreate, MunicipioUpdate, MunicipioResponse,
    MessageResponse,
)
from . import service

router = APIRouter(prefix="/shared")

TAG = "Geografía > Departamentos"


@router.get("/departamentos", response_model=list[DepartamentoResponse], tags=[TAG])
def listar_departamentos(db: Session = Depends(get_db)):
    return service.get_departamentos(db)


@router.get("/departamentos/{id}", response_model=DepartamentoResponse, tags=[TAG])
def obtener_departamento(id: int, db: Session = Depends(get_db)):
    result = service.get_departamento(db, id)
    if not result:
        raise HTTPException(status_code=404, detail="Departamento no encontrado")
    return result


@router.post("/departamentos", response_model=DepartamentoResponse, status_code=201, tags=[TAG])
def crear_departamento(data: DepartamentoCreate, db: Session = Depends(get_db)):
    try:
        id = service.create_departamento(db, data)
        return service.get_departamento(db, id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/departamentos/{id}", response_model=DepartamentoResponse, tags=[TAG])
def actualizar_departamento(id: int, data: DepartamentoUpdate, db: Session = Depends(get_db)):
    result = service.update_departamento(db, id, data)
    if not result:
        raise HTTPException(status_code=404, detail="Departamento no encontrado")
    return result


@router.delete("/departamentos/{id}", response_model=MessageResponse, tags=[TAG])
def eliminar_departamento(id: int, db: Session = Depends(get_db)):
    if not service.delete_departamento(db, id):
        raise HTTPException(status_code=404, detail="Departamento no encontrado")
    return MessageResponse(message="Departamento eliminado")


TAG = "Geografía > Provincias"


@router.get("/provincias", response_model=list[ProvinciaResponse], tags=[TAG])
def listar_provincias(
    id_departamento: int | None = Query(None),
    db: Session = Depends(get_db),
):
    return service.get_provincias(db, id_departamento)


@router.get("/provincias/{id}", response_model=ProvinciaResponse, tags=[TAG])
def obtener_provincia(id: int, db: Session = Depends(get_db)):
    result = service.get_provincia(db, id)
    if not result:
        raise HTTPException(status_code=404, detail="Provincia no encontrada")
    return result


@router.post("/provincias", response_model=ProvinciaResponse, status_code=201, tags=[TAG])
def crear_provincia(data: ProvinciaCreate, db: Session = Depends(get_db)):
    try:
        id = service.create_provincia(db, data)
        return service.get_provincia(db, id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/provincias/{id}", response_model=ProvinciaResponse, tags=[TAG])
def actualizar_provincia(id: int, data: ProvinciaUpdate, db: Session = Depends(get_db)):
    result = service.update_provincia(db, id, data)
    if not result:
        raise HTTPException(status_code=404, detail="Provincia no encontrada")
    return result


@router.delete("/provincias/{id}", response_model=MessageResponse, tags=[TAG])
def eliminar_provincia(id: int, db: Session = Depends(get_db)):
    if not service.delete_provincia(db, id):
        raise HTTPException(status_code=404, detail="Provincia no encontrada")
    return MessageResponse(message="Provincia eliminada")


TAG = "Geografía > Municipios"


@router.get("/municipios", response_model=list[MunicipioResponse], tags=[TAG])
def listar_municipios(
    id_provincia: int | None = Query(None),
    id_departamento: int | None = Query(None),
    db: Session = Depends(get_db),
):
    return service.get_municipios(db, id_provincia, id_departamento)


@router.get("/municipios/{id}", response_model=MunicipioResponse, tags=[TAG])
def obtener_municipio(id: int, db: Session = Depends(get_db)):
    result = service.get_municipio(db, id)
    if not result:
        raise HTTPException(status_code=404, detail="Municipio no encontrado")
    return result


@router.post("/municipios", response_model=MunicipioResponse, status_code=201, tags=[TAG])
def crear_municipio(data: MunicipioCreate, db: Session = Depends(get_db)):
    try:
        id = service.create_municipio(db, data)
        return service.get_municipio(db, id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/municipios/{id}", response_model=MunicipioResponse, tags=[TAG])
def actualizar_municipio(id: int, data: MunicipioUpdate, db: Session = Depends(get_db)):
    result = service.update_municipio(db, id, data)
    if not result:
        raise HTTPException(status_code=404, detail="Municipio no encontrado")
    return result


@router.delete("/municipios/{id}", response_model=MessageResponse, tags=[TAG])
def eliminar_municipio(id: int, db: Session = Depends(get_db)):
    if not service.delete_municipio(db, id):
        raise HTTPException(status_code=404, detail="Municipio no encontrado")
    return MessageResponse(message="Municipio eliminado")
