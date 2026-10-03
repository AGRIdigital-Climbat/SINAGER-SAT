from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..dependencies import get_current_user


# Roles permitidos para operaciones SINB
ROLES_SINB_ADMIN = (1, 2)  # superadmin, admin
ROLES_SINB_PRONOSTICO = (1, 2, 9)  # superadmin, admin, VIDECI Departamental
ROLES_SINB_OBSERVACION = (1, 2, 6, 7, 8, 9, 12, 13)  # todos los roles SINB
ROLES_SINB_VALIDACION = (1, 2, 9)  # validación manual
ROLES_SINB_LOCAL = (6, 7, 8, 12, 13)  # roles locales (UGR, Responsable, Alcalde, Recolector, Observador)


def require_rol(*roles_allowed):
    """Dependency para restringir endpoints por rol."""
    def dependency(user=Depends(get_current_user)):
        if user.get("id_rol") not in roles_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Rol {user.get('id_rol')} no permitido. Roles requeridos: {roles_allowed}"
            )
        return user
    return dependency


def scope_geografico(user: dict, id_departamento=None, id_provincia=None, id_municipio=None):
    """
    Aplica filtros geográficos según rol del usuario.
    
    Retorna dict con filtros a aplicar en consultas SQL.
    """
    id_rol = user.get("id_rol")
    id_dept_user = user.get("id_departamento")
    id_prov_user = user.get("id_provincia")
    id_mun_user = user.get("id_municipio")
    
    # Roles 1, 2: sin filtros (superadmin, admin)
    if id_rol in (1, 2):
        return {
            "id_departamento": id_departamento,
            "id_provincia": id_provincia,
            "id_municipio": id_municipio
        }
    
    # Rol 9 (VIDECI Departamental): filtra por departamento del usuario
    if id_rol == 9 and id_dept_user:
        return {
            "id_departamento": id_departamento if id_departamento else id_dept_user,
            "id_provincia": id_provincia,
            "id_municipio": id_municipio
        }
    
    # Roles 6, 8 (UGR Municipio, Alcalde): filtra por municipio del usuario
    if id_rol in (6, 8) and id_mun_user:
        return {
            "id_departamento": id_departamento,
            "id_provincia": id_provincia,
            "id_municipio": id_mun_user
        }
    
    # Rol 7 (Responsable Local): puede tener filtro por comunidad específica
    if id_rol == 7:
        return {
            "id_departamento": id_departamento,
            "id_provincia": id_provincia,
            "id_municipio": id_mun_user
        }
    
    # Roles 12, 13 (Usuario recolector, Observador local): sin filtro por defecto
    # (pueden ver todas las observaciones de su área)
    return {
        "id_departamento": id_departamento,
        "id_provincia": id_provincia,
        "id_municipio": id_municipio
    }


def validar_scope_localidad(db: Session, user: dict, id_localidad: int):
    """
    Valida que el usuario tenga acceso a una localidad específica.
    Lanza HTTPException 403 si no tiene acceso.
    """
    from sqlalchemy import text
    id_rol = user.get("id_rol")
    
    # Roles 1, 2: acceso total
    if id_rol in (1, 2):
        return True
    
    # Verificar existencia
    result = db.execute(
        text("""
            SELECT id_departamento, id_provincia, id_municipio, id_usuario
            FROM edan.edan_localidades
            WHERE id_edan_localidad = :id
        """),
        {"id": id_localidad}
    )
    loc = result.mappings().first()
    if not loc:
        raise HTTPException(status_code=404, detail="Localidad no encontrada")
    
    # Rol 9: verifica departamento
    if id_rol == 9 and user.get("id_departamento"):
        if loc["id_departamento"] != user["id_departamento"]:
            raise HTTPException(status_code=403, detail="No tiene acceso a esta localidad")
        return True
    
    # Roles 6, 8: verifica municipio
    if id_rol in (6, 8) and user.get("id_municipio"):
        if loc["id_municipio"] != user["id_municipio"]:
            raise HTTPException(status_code=403, detail="No tiene acceso a esta localidad")
        return True
    
    # Rol 7: verifica municipio o usuario propietario
    if id_rol == 7:
        if loc["id_usuario"] == user["id_usuario"]:
            return True
        if loc["id_municipio"] != user.get("id_municipio"):
            raise HTTPException(status_code=403, detail="No tiene acceso a esta localidad")
        return True
    
    # Roles 12, 13: solo propietario
    if id_rol in (12, 13):
        if loc["id_usuario"] != user["id_usuario"]:
            raise HTTPException(status_code=403, detail="No tiene acceso a esta localidad")
        return True
    
    return True
