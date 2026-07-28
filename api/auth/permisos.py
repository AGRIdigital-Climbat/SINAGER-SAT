from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.orm import Session
from ..dependencies import get_current_user, get_db


def module_permiso(modulo: str):
    def check(
        request: Request,
        usuario: dict = Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        method_map = {"GET": "READ", "POST": "CREATE", "PUT": "UPDATE", "DELETE": "DELETE"}
        accion = method_map.get(request.method, "READ")
        if usuario["id_rol"] == 1:
            return usuario
        result = db.execute(
            text("""
                SELECT 1 FROM usuarios.permiso p
                JOIN usuarios.aplicacion a ON a.id_aplicacion = p.id_aplicacion
                JOIN usuarios.accion ac ON ac.id_accion = p.id_accion
                WHERE p.id_rol = :rol AND a.codigo = :mod AND ac.codigo = :acc
            """),
            {"rol": usuario["id_rol"], "mod": modulo, "acc": accion},
        ).scalar()
        if not result:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Sin permiso: {accion} en {modulo}",
            )
        return usuario
    return check


def permiso_required(modulo: str, accion: str):
    def check(
        usuario: dict = Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        if usuario["id_rol"] == 1:
            return usuario
        result = db.execute(
            text("""
                SELECT 1 FROM usuarios.permiso p
                JOIN usuarios.aplicacion a ON a.id_aplicacion = p.id_aplicacion
                JOIN usuarios.accion ac ON ac.id_accion = p.id_accion
                WHERE p.id_rol = :rol AND a.codigo = :mod AND ac.codigo = :acc
            """),
            {"rol": usuario["id_rol"], "mod": modulo, "acc": accion},
        ).scalar()
        if not result:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Sin permiso: {accion} en {modulo}",
            )
        return usuario
    return check
