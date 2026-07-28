from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..dependencies import get_current_user
from ..auth.permisos import module_permiso, permiso_required
from ..response import SuccessResponse, MessageResponse
from .schemas import *
from . import service

router = APIRouter(prefix="/usuarios", dependencies=[Depends(module_permiso("SISTEMA"))])

TAG_USR = "Usuarios > Cuentas"
TAG_ROL = "Usuarios > Roles"
TAG_APL = "Usuarios > Aplicaciones"
TAG_PER = "Usuarios > Permisos"
TAG_ACC = "Usuarios > Acciones"
TAG_SES = "Usuarios > Sesiones"
TAG_AUD = "Usuarios > Auditoría"


# ──────────────────────────────────────────────
#  ROLES
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
#  ACCIONES
# ──────────────────────────────────────────────

@router.get("/acciones", tags=[TAG_ACC], responses={200: {"model": SuccessResponse}})
def listar_acciones(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    items = service.get_acciones(db)
    return SuccessResponse(message="Acciones listadas correctamente", data=items, total=len(items))


@router.get("/acciones/{id}", tags=[TAG_ACC], responses={200: {"model": SuccessResponse}})
def obtener_accion(id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    result = service.get_accion(db, id)
    if not result:
        raise HTTPException(status_code=404, detail="Acción no encontrada")
    return SuccessResponse(message="Acción obtenida correctamente", data=result)


@router.post("/acciones", status_code=201, tags=[TAG_ACC], responses={201: {"model": SuccessResponse}})
def crear_accion(data: AccionCreate, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    id = service.create_accion(db, data.model_dump())
    result = service.get_accion(db, id)
    return SuccessResponse(message="Acción creada correctamente", data=result)


@router.put("/acciones/{id}", tags=[TAG_ACC], responses={200: {"model": SuccessResponse}})
def actualizar_accion(id: int, data: AccionUpdate, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    result = service.update_accion(db, id, data.model_dump(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="Acción no encontrada")
    return SuccessResponse(message="Acción actualizada correctamente", data=result)


@router.delete("/acciones/{id}", tags=[TAG_ACC], responses={200: {"model": MessageResponse}})
def eliminar_accion(id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    if not service.delete_accion(db, id):
        raise HTTPException(status_code=404, detail="Acción no encontrada")
    return MessageResponse(message="Acción eliminada correctamente")


# ──────────────────────────────────────────────
#  PERMISOS — endpoints intuitivos para frontend
# ──────────────────────────────────────────────

@router.get("/permisos/estructura", tags=[TAG_PER],
            summary="Estructura completa para montar UI de permisos")
def obtener_estructura_permisos(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    data = service.get_permisos_estructura(db)
    return SuccessResponse(message="Estructura de permisos obtenida", data=data)


@router.get("/permisos/rol/{id_rol}", tags=[TAG_PER],
            summary="Permisos de un rol agrupados por aplicación")
def obtener_permisos_rol(id_rol: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    result = service.get_rol_permisos_agrupados(db, id_rol)
    if not result:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    return SuccessResponse(message="Permisos del rol obtenidos", data=result)


@router.put("/roles/{id_rol}/permisos", tags=[TAG_PER],
            summary="Asignar permisos completos a un rol (reemplaza todos)")
def asignar_permisos_rol(id_rol: int, data: PermisoBatchRequest,
                         db: Session = Depends(get_db),
                         _ua=Depends(permiso_required("SISTEMA", "UPDATE"))):
    service.assign_permisos_batch(db, id_rol, data.permisos)
    result = service.get_rol_permisos_agrupados(db, id_rol)
    return SuccessResponse(message="Permisos actualizados correctamente", data=result)


# ── Permisos individuales (ajustes finos desde la UI) ──

@router.get("/permisos", tags=[TAG_PER], responses={200: {"model": SuccessResponse}})
def listar_permisos(id_rol: int | None = Query(None), db: Session = Depends(get_db), _user=Depends(get_current_user)):
    items = service.get_permisos(db, id_rol)
    return SuccessResponse(message="Permisos listados correctamente", data=items, total=len(items))


@router.post("/permisos/{id_rol}/{id_aplicacion}/{id_accion}", tags=[TAG_PER], responses={200: {"model": SuccessResponse}})
def asignar_permiso(id_rol: int, id_aplicacion: int, id_accion: int,
                    db: Session = Depends(get_db), _user=Depends(get_current_user)):
    service.assign_permiso(db, id_rol, id_aplicacion, id_accion)
    return SuccessResponse(message="Permiso asignado correctamente")


@router.delete("/permisos/{id_rol}/{id_aplicacion}/{id_accion}", tags=[TAG_PER], responses={200: {"model": MessageResponse}})
def remover_permiso(id_rol: int, id_aplicacion: int, id_accion: int,
                    db: Session = Depends(get_db), _user=Depends(get_current_user)):
    if not service.remove_permiso(db, id_rol, id_aplicacion, id_accion):
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
def listar_auditoria(
    id_usuario: int | None = Query(None, description="Filtrar por usuario"),
    id_aplicacion: int | None = Query(None, description="Filtrar por aplicación (1=EDAN, 4=REA, 9=SISTEMA)"),
    accion: str | None = Query(None, description="Filtrar por acción (CREATE, UPDATE, DELETE)"),
    fecha_desde: str | None = Query(None, description="Desde (ISO: YYYY-MM-DD o YYYY-MM-DD HH:MM:SS)"),
    fecha_hasta: str | None = Query(None, description="Hasta (ISO: YYYY-MM-DD o YYYY-MM-DD HH:MM:SS)"),
    id_rol: int | None = Query(None, description="Filtrar usuarios por rol"),
    id_municipio: int | None = Query(None, description="Filtrar usuarios por municipio"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db), _user=Depends(get_current_user)):
    items, total = service.get_auditoria(
        db, id_usuario, id_aplicacion, accion,
        fecha_desde, fecha_hasta, id_rol, id_municipio,
        skip, limit,
    )
    return SuccessResponse(message="Auditoría listada correctamente", data=items, total=total)


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
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{id}", tags=[TAG_USR], responses={200: {"model": SuccessResponse}})
def actualizar_usuario(id: int, data: UsuarioUpdate, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    try:
        result = service.update_usuario(db, id, data.model_dump(exclude_unset=True))
        if not result:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        return SuccessResponse(message="Usuario actualizado correctamente", data=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{id}", tags=[TAG_USR], responses={200: {"model": MessageResponse}})
def eliminar_usuario(id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    if not service.delete_usuario(db, id):
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return MessageResponse(message="Usuario desactivado correctamente")
