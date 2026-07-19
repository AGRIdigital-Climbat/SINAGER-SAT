from sqlalchemy.orm import Session
from sqlalchemy import text
from .jwt import hash_password, verify_password, create_access_token
from .schemas import LoginRequest, RegisterRequest


def authenticate_user(db: Session, data: LoginRequest) -> dict | None:
    result = db.execute(
        text("""
            SELECT u.id_usuario, u.usuario, u.nombre, u.contrasena, u.activo, u.id_rol,
                   u.celular, u.carnet, u.comunidad,
                   u.id_departamento, u.id_provincia, u.id_municipio,
                   r.nombre as rol,
                   d.codigo_ine as d_codigo_ine, d.nombre as d_nombre,
                   prov.codigo_ine as prov_codigo_ine, prov.nombre as prov_nombre,
                   m.codigo_ine as m_codigo_ine, m.nombre as m_nombre
            FROM usuarios.usuario u
            LEFT JOIN usuarios.rol r ON u.id_rol = r.id_rol
            LEFT JOIN shared.departamento d ON u.id_departamento = d.id
            LEFT JOIN shared.provincia prov ON u.id_provincia = prov.id
            LEFT JOIN shared.municipio m ON u.id_municipio = m.id
            WHERE u.usuario = :u
        """),
        {"u": data.usuario},
    )
    user = result.mappings().first()
    if not user:
        return None
    if not user["activo"]:
        return None
    if not verify_password(data.contrasena, user["contrasena"]):
        return None
    token = create_access_token({"sub": str(user["id_usuario"]), "usuario": user["usuario"], "id_rol": user["id_rol"]})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user["id_usuario"],
        "usuario": user["usuario"],
        "nombre": user["nombre"],
        "celular": user["celular"],
        "carnet": user["carnet"],
        "comunidad": user["comunidad"],
        "departamento": {
            "id": user["id_departamento"],
            "codigo_ine": user["d_codigo_ine"],
            "nombre": user["d_nombre"],
        } if user["id_departamento"] else None,
        "provincia": {
            "id": user["id_provincia"],
            "codigo_ine": user["prov_codigo_ine"],
            "nombre": user["prov_nombre"],
        } if user["id_provincia"] else None,
        "municipio": {
            "id": user["id_municipio"],
            "codigo_ine": user["m_codigo_ine"],
            "nombre": user["m_nombre"],
        } if user["id_municipio"] else None,
        "id_rol": user["id_rol"],
        "rol": user["rol"],
        "activo": user["activo"],
    }


def register_user(db: Session, data: RegisterRequest) -> int:
    existing = db.execute(
        text("SELECT id_usuario FROM usuarios.usuario WHERE usuario = :u"),
        {"u": data.usuario},
    ).first()
    if existing:
        raise ValueError("El usuario ya existe")
    if data.carnet:
        existing_carnet = db.execute(
            text("SELECT id_usuario FROM usuarios.usuario WHERE carnet = :c"),
            {"c": data.carnet},
        ).first()
        if existing_carnet:
            raise ValueError("El número de carnet ya está registrado")
    hashed = hash_password(data.contrasena)
    result = db.execute(
        text("""
            INSERT INTO usuarios.usuario (usuario, contrasena, nombre, celular, carnet, comunidad,
                id_departamento, id_provincia, id_municipio, id_rol, activo)
            VALUES (:usuario, :contrasena, :nombre, :celular, :carnet, :comunidad,
                :id_departamento, :id_provincia, :id_municipio, :id_rol, true)
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
            "id_rol": data.id_rol,
        },
    )
    db.commit()
    return result.scalar()
