from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..database import get_db
from ..dependencies import get_current_user
from ..response import SuccessResponse, MessageResponse
from .schemas import *
from . import service

router = APIRouter(prefix="/usuarios")

TAG_USR = "Usuarios > Cuentas"
TAG_ROL = "Usuarios > Roles"
TAG_APL = "Usuarios > Aplicaciones"
TAG_PER = "Usuarios > Permisos"
TAG_SES = "Usuarios > Sesiones"
TAG_AUD = "Usuarios > Auditoría"


# ──────────────────────────────────────────────
#  ROLES (antes de /{id} para evitar conflicto)
# ──────────────────────────────────────────────

@router.get("/roles", tags=[TAG_ROL], responses={200: {"model": SuccessResponse}})
def listar_roles(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    items = service.get_roles(db)
    return SuccessResponse(message="Roles listados correctamente", data=items, total=len(items))


@router.get("/roles/{id}", tags=[TAG_ROL], responses={200: {"model": SuccessResponse}})
def obtener_rol(id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    result = service.get_rol(db, id)
    if not result:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    return SuccessResponse(message="Rol obtenido correctamente", data=result)


@router.post("/roles", status_code=201, tags=[TAG_ROL], responses={201: {"model": SuccessResponse}})
def crear_rol(data: RolCreate, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    id = service.create_rol(db, data.model_dump())
    result = service.get_rol(db, id)
    return SuccessResponse(message="Rol creado correctamente", data=result)


@router.put("/roles/{id}", tags=[TAG_ROL], responses={200: {"model": SuccessResponse}})
def actualizar_rol(id: int, data: RolUpdate, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    result = service.update_rol(db, id, data.model_dump(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    return SuccessResponse(message="Rol actualizado correctamente", data=result)


@router.delete("/roles/{id}", tags=[TAG_ROL], responses={200: {"model": MessageResponse}})
def eliminar_rol(id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    if not service.delete_rol(db, id):
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    return MessageResponse(message="Rol eliminado correctamente")


@router.get("/{id_usuario}/roles", tags=[TAG_ROL], responses={200: {"model": SuccessResponse}})
def listar_usuario_roles(id_usuario: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    items = service.get_usuario_roles(db, id_usuario)
    return SuccessResponse(message="Roles del usuario listados correctamente", data=items, total=len(items))


@router.post("/{id_usuario}/roles/{id_rol}", tags=[TAG_ROL], responses={200: {"model": SuccessResponse}})
def asignar_rol(id_usuario: int, id_rol: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    service.assign_rol(db, id_usuario, id_rol)
    return SuccessResponse(message="Rol asignado correctamente")


@router.delete("/{id_usuario}/roles/{id_rol}", tags=[TAG_ROL], responses={200: {"model": MessageResponse}})
def remover_rol(id_usuario: int, id_rol: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    if not service.remove_rol(db, id_usuario, id_rol):
        raise HTTPException(status_code=404, detail="Asignación no encontrada")
    return MessageResponse(message="Rol removido correctamente")


# ──────────────────────────────────────────────
#  APLICACIONES
# ──────────────────────────────────────────────

@router.get("/aplicaciones", tags=[TAG_APL], responses={200: {"model": SuccessResponse}})
def listar_aplicaciones(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    items = service.get_aplicaciones(db)
    return SuccessResponse(message="Aplicaciones listadas correctamente", data=items, total=len(items))


@router.get("/aplicaciones/{id}", tags=[TAG_APL], responses={200: {"model": SuccessResponse}})
def obtener_aplicacion(id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    result = service.get_aplicacion(db, id)
    if not result:
        raise HTTPException(status_code=404, detail="Aplicación no encontrada")
    return SuccessResponse(message="Aplicación obtenida correctamente", data=result)


@router.post("/aplicaciones", status_code=201, tags=[TAG_APL], responses={201: {"model": SuccessResponse}})
def crear_aplicacion(data: AplicacionCreate, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    id = service.create_aplicacion(db, data.model_dump())
    result = service.get_aplicacion(db, id)
    return SuccessResponse(message="Aplicación creada correctamente", data=result)


@router.put("/aplicaciones/{id}", tags=[TAG_APL], responses={200: {"model": SuccessResponse}})
def actualizar_aplicacion(id: int, data: AplicacionUpdate, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    result = service.update_aplicacion(db, id, data.model_dump(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="Aplicación no encontrada")
    return SuccessResponse(message="Aplicación actualizada correctamente", data=result)


@router.delete("/aplicaciones/{id}", tags=[TAG_APL], responses={200: {"model": MessageResponse}})
def eliminar_aplicacion(id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    if not service.delete_aplicacion(db, id):
        raise HTTPException(status_code=404, detail="Aplicación no encontrada")
    return MessageResponse(message="Aplicación eliminada correctamente")


# ──────────────────────────────────────────────
#  PERMISOS
# ──────────────────────────────────────────────

@router.get("/permisos", tags=[TAG_PER], responses={200: {"model": SuccessResponse}})
def listar_permisos(id_rol: int | None = Query(None), db: Session = Depends(get_db), _user=Depends(get_current_user)):
    items = service.get_permisos(db, id_rol)
    return SuccessResponse(message="Permisos listados correctamente", data=items, total=len(items))


@router.post("/permisos/{id_rol}/{id_aplicacion}", tags=[TAG_PER], responses={200: {"model": SuccessResponse}})
def asignar_permiso(id_rol: int, id_aplicacion: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    service.assign_permiso(db, id_rol, id_aplicacion)
    return SuccessResponse(message="Permiso asignado correctamente")


@router.delete("/permisos/{id_rol}/{id_aplicacion}", tags=[TAG_PER], responses={200: {"model": MessageResponse}})
def remover_permiso(id_rol: int, id_aplicacion: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    if not service.remove_permiso(db, id_rol, id_aplicacion):
        raise HTTPException(status_code=404, detail="Permiso no encontrado")
    return MessageResponse(message="Permiso removido correctamente")


# ──────────────────────────────────────────────
#  SESIONES Y AUDITORÍA
# ──────────────────────────────────────────────

@router.get("/sesiones", tags=[TAG_SES], responses={200: {"model": SuccessResponse}})
def listar_sesiones(id_usuario: int | None = Query(None), db: Session = Depends(get_db), _user=Depends(get_current_user)):
    items = service.get_sesiones(db, id_usuario)
    return SuccessResponse(message="Sesiones listadas correctamente", data=items, total=len(items))


@router.get("/auditoria", tags=[TAG_AUD], responses={200: {"model": SuccessResponse}})
def listar_auditoria(id_usuario: int | None = Query(None), skip: int = 0, limit: int = 100, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    items = service.get_auditoria(db, id_usuario, skip, limit)
    return SuccessResponse(message="Auditoría listada correctamente", data=items, total=len(items))


@router.get("/resets", tags=[TAG_AUD], responses={200: {"model": SuccessResponse}})
def listar_resets(id_usuario: int | None = Query(None), db: Session = Depends(get_db), _user=Depends(get_current_user)):
    items = service.get_resets(db, id_usuario)
    return SuccessResponse(message="Resets listados correctamente", data=items, total=len(items))


# ──────────────────────────────────────────────
#  USUARIOS PRINCIPAL (al final para no capturar /{id})
# ──────────────────────────────────────────────

@router.get("/", tags=[TAG_USR], responses={200: {"model": SuccessResponse}})
def listar_usuarios(skip: int = 0, limit: int = 50, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    items = service.get_usuarios(db, skip, limit)
    return SuccessResponse(message="Usuarios listados correctamente", data=items, total=len(items))


@router.get("/{id}", tags=[TAG_USR], responses={200: {"model": SuccessResponse}})
def obtener_usuario(id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    result = service.get_usuario(db, id)
    if not result:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return SuccessResponse(message="Usuario obtenido correctamente", data=result)


@router.post("/", status_code=201, tags=[TAG_USR], responses={201: {"model": SuccessResponse}})
def crear_usuario(data: UsuarioCreate, db: Session = Depends(get_db)):
    try:
        id = service.create_usuario(db, data.model_dump())
        result = service.get_usuario(db, id)
        return SuccessResponse(message="Usuario creado correctamente", data=result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{id}", tags=[TAG_USR], responses={200: {"model": SuccessResponse}})
def actualizar_usuario(id: int, data: UsuarioUpdate, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    result = service.update_usuario(db, id, data.model_dump(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return SuccessResponse(message="Usuario actualizado correctamente", data=result)


@router.delete("/{id}", tags=[TAG_USR], responses={200: {"model": MessageResponse}})
def eliminar_usuario(id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    if not service.delete_usuario(db, id):
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return MessageResponse(message="Usuario desactivado correctamente")
