from sqlalchemy.orm import Session
from sqlalchemy import text
from .jwt import hash_password, verify_password, create_access_token
from .schemas import LoginRequest, RegisterRequest


def authenticate_user(db: Session, data: LoginRequest) -> dict | None:
    result = db.execute(
        text("SELECT id_usuario, usuario, nombre, contrasena, activo FROM usuarios.usuario WHERE usuario = :u"),
        {"u": data.usuario},
    )
    user = result.mappings().first()
    if not user:
        return None
    if not user["activo"]:
        return None
    if not verify_password(data.contrasena, user["contrasena"]):
        return None
    token = create_access_token({"sub": str(user["id_usuario"]), "usuario": user["usuario"]})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user["id_usuario"],
        "usuario": user["usuario"],
        "nombre": user["nombre"],
    }


def register_user(db: Session, data: RegisterRequest) -> int:
    existing = db.execute(
        text("SELECT id_usuario FROM usuarios.usuario WHERE usuario = :u"),
        {"u": data.usuario},
    ).first()
    if existing:
        raise ValueError("El usuario ya existe")
    hashed = hash_password(data.contrasena)
    result = db.execute(
        text("""
            INSERT INTO usuarios.usuario (usuario, contrasena, nombre, celular, carnet, comunidad,
                id_departamento, id_provincia, id_municipio, activo)
            VALUES (:usuario, :contrasena, :nombre, :celular, :carnet, :comunidad,
                :id_departamento, :id_provincia, :id_municipio, true)
            RETURNING id_usuario
        """),
        {
            "usuario": data.usuario,
            "contrasena": hashed,
            "nombre": data.nombre,
            "celular": data.celular,
            "carnet": data.carnet,
            "comunidad": data.comunidad,
            "id_departamento": data.id_departamento,
            "id_provincia": data.id_provincia,
            "id_municipio": data.id_municipio,
        },
    )
    db.commit()
    return result.scalar()
