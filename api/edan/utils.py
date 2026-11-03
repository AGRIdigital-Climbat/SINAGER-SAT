from fastapi import Depends, HTTPException

from ..dependencies import get_current_user


def require_rol(*roles):
    def _checker(_user=Depends(get_current_user)):
        if _user.get("id_rol") not in roles:
            raise HTTPException(
                status_code=403,
                detail=f"Rol {_user.get('id_rol')} no autorizado. Roles permitidos: {roles}"
            )
        return _user
    return _checker


def db_error(exc: Exception) -> HTTPException:
    try:
        code = getattr(exc.orig, "sqlstate", None) or getattr(exc.orig, "pgcode", None)
    except AttributeError:
        code = None
    try:
        constraint = getattr(exc.orig.diag, "constraint_name", None)
    except AttributeError:
        constraint = None
    if code == "23503":
        return HTTPException(status_code=400, detail="El registro referenciado no existe (violación de clave foránea)"
                             + (f" [{constraint}]" if constraint else ""))
    if code == "23505":
        return HTTPException(status_code=400, detail="Ya existe un registro con el mismo valor (violación de unicidad)"
                             + (f" [{constraint}]" if constraint else ""))
    if code == "23502":
        return HTTPException(status_code=400, detail="Falta un campo obligatorio"
                             + (f" [{constraint}]" if constraint else ""))
    if code == "23514":
        return HTTPException(status_code=400, detail="Valor no permitido por una regla del campo (CHECK)"
                             + (f" [{constraint}]" if constraint else ""))
    return HTTPException(status_code=400, detail="Error al procesar la solicitud")
