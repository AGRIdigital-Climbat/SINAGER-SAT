from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..database import get_db
from ..dependencies import get_current_user
from .schemas import *
from . import service

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


# ── USUARIOS ──

@router.get("/", response_model=list[UsuarioResponse])
def listar_usuarios(skip: int = 0, limit: int = 50, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    return service.get_usuarios(db, skip, limit)


@router.get("/{id}", response_model=UsuarioResponse)
def obtener_usuario(id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    result = service.get_usuario(db, id)
    if not result:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return result


@router.post("/", response_model=UsuarioResponse, status_code=201)
def crear_usuario(data: UsuarioCreate, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    try:
        id = service.create_usuario(db, data.model_dump())
        return service.get_usuario(db, id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{id}", response_model=UsuarioResponse)
def actualizar_usuario(id: int, data: UsuarioUpdate, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    result = service.update_usuario(db, id, data.model_dump(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return result


@router.delete("/{id}")
def eliminar_usuario(id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    if not service.delete_usuario(db, id):
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return MessageResponse(message="Usuario desactivado")


# ── ROLES ──

@router.get("/roles/", response_model=list[RolResponse])
def listar_roles(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    return service.get_roles(db)


@router.get("/roles/{id}", response_model=RolResponse)
def obtener_rol(id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    result = service.get_rol(db, id)
    if not result:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    return result


@router.post("/roles/", response_model=RolResponse, status_code=201)
def crear_rol(data: RolCreate, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    id = service.create_rol(db, data.model_dump())
    return service.get_rol(db, id)


@router.put("/roles/{id}", response_model=RolResponse)
def actualizar_rol(id: int, data: RolUpdate, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    result = service.update_rol(db, id, data.model_dump(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    return result


@router.delete("/roles/{id}")
def eliminar_rol(id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    if not service.delete_rol(db, id):
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    return MessageResponse(message="Rol eliminado")


# ── USUARIO_ROL ──

@router.get("/{id_usuario}/roles", response_model=list[UsuarioRolResponse])
def listar_usuario_roles(id_usuario: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    return service.get_usuario_roles(db, id_usuario)


@router.post("/{id_usuario}/roles/{id_rol}")
def asignar_rol(id_usuario: int, id_rol: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    service.assign_rol(db, id_usuario, id_rol)
    return MessageResponse(message="Rol asignado")


@router.delete("/{id_usuario}/roles/{id_rol}")
def remover_rol(id_usuario: int, id_rol: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    if not service.remove_rol(db, id_usuario, id_rol):
        raise HTTPException(status_code=404, detail="Asignación no encontrada")
    return MessageResponse(message="Rol removido")


# ── APLICACIONES ──

@router.get("/aplicaciones/", response_model=list[AplicacionResponse])
def listar_aplicaciones(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    return service.get_aplicaciones(db)


@router.get("/aplicaciones/{id}", response_model=AplicacionResponse)
def obtener_aplicacion(id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    result = service.get_aplicacion(db, id)
    if not result:
        raise HTTPException(status_code=404, detail="Aplicación no encontrada")
    return result


@router.post("/aplicaciones/", response_model=AplicacionResponse, status_code=201)
def crear_aplicacion(data: AplicacionCreate, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    id = service.create_aplicacion(db, data.model_dump())
    return service.get_aplicacion(db, id)


@router.put("/aplicaciones/{id}", response_model=AplicacionResponse)
def actualizar_aplicacion(id: int, data: AplicacionUpdate, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    result = service.update_aplicacion(db, id, data.model_dump(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="Aplicación no encontrada")
    return result


@router.delete("/aplicaciones/{id}")
def eliminar_aplicacion(id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    if not service.delete_aplicacion(db, id):
        raise HTTPException(status_code=404, detail="Aplicación no encontrada")
    return MessageResponse(message="Aplicación eliminada")


# ── PERMISOS ──

@router.get("/permisos/", response_model=list[PermisoAplicacionResponse])
def listar_permisos(id_rol: int | None = Query(None), db: Session = Depends(get_db), _user=Depends(get_current_user)):
    return service.get_permisos(db, id_rol)


@router.post("/permisos/{id_rol}/{id_aplicacion}")
def asignar_permiso(id_rol: int, id_aplicacion: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    service.assign_permiso(db, id_rol, id_aplicacion)
    return MessageResponse(message="Permiso asignado")


@router.delete("/permisos/{id_rol}/{id_aplicacion}")
def remover_permiso(id_rol: int, id_aplicacion: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    if not service.remove_permiso(db, id_rol, id_aplicacion):
        raise HTTPException(status_code=404, detail="Permiso no encontrado")
    return MessageResponse(message="Permiso removido")


# ── SESIONES ──

@router.get("/sesiones/")
def listar_sesiones(id_usuario: int | None = Query(None), db: Session = Depends(get_db), _user=Depends(get_current_user)):
    return [dict(s) for s in service.get_sesiones(db, id_usuario)]


# ── AUDITORIA ──

@router.get("/auditoria/")
def listar_auditoria(id_usuario: int | None = Query(None), skip: int = 0, limit: int = 100, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    return [dict(a) for a in service.get_auditoria(db, id_usuario, skip, limit)]


# ── RESET CONTRASEÑA ──

@router.get("/resets/")
def listar_resets(id_usuario: int | None = Query(None), db: Session = Depends(get_db), _user=Depends(get_current_user)):
    return [dict(r) for r in service.get_resets(db, id_usuario)]
