from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import text
from .jwt import hash_password, verify_password, create_access_token
from .schemas import LoginRequest, RegisterRequest, VerificarIdentidadRequest, CambiarContrasenaRequest


TOKEN_LARGO = datetime(2099, 12, 31, 23, 59, 59)


def _calcular_expiracion(id_rol: int) -> tuple[datetime, timedelta | None]:
    if id_rol in (6, 7):
        return TOKEN_LARGO, None
    return datetime.now() + timedelta(hours=72), timedelta(hours=72)


PERMISOS_POR_ROL = """
    SELECT a.codigo as app, ac.codigo as accion
    FROM usuarios.permiso p
    JOIN usuarios.aplicacion a ON a.id_aplicacion = p.id_aplicacion
    JOIN usuarios.accion ac ON ac.id_accion = p.id_accion
    WHERE p.id_rol = :r
"""


def _agrupar_permisos(db: Session, id_rol: int) -> dict[str, list[str]]:
    rows = db.execute(text(PERMISOS_POR_ROL), {"r": id_rol}).mappings().all()
    result = {}
    for r in rows:
        app = r["app"]
        accion = r["accion"]
        if app not in result:
            result[app] = []
        result[app].append(accion)
    return result


def _get_permisos_response(id_rol: int, db: Session) -> dict | str:
    if id_rol == 1:
        return "full_access"
    return _agrupar_permisos(db, id_rol)


def authenticate_user(db: Session, data: LoginRequest) -> dict | None:
    result = db.execute(
        text("""
            SELECT u.id_usuario, u.usuario, u.nombre, u.contrasena, u.activo, u.id_rol,
                   u.celular, u.carnet, u.comunidad, u.correo, u.cargo,
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

    # Buscar sesión activa existente - reutilizar token (solo si no expiró)
    sesion = db.execute(
        text("SELECT token FROM usuarios.sesion WHERE id_usuario = :uid AND activo = true AND fecha_expiracion > NOW()"),
        {"uid": user["id_usuario"]}
    ).mappings().first()

    fecha_exp, delta = _calcular_expiracion(user["id_rol"])

    if sesion:
        token = sesion["token"]
    else:
        token = create_access_token(
            {"sub": str(user["id_usuario"]), "usuario": user["usuario"], "id_rol": user["id_rol"]},
            expires_delta=delta,
        )
        db.execute(
            text("INSERT INTO usuarios.sesion (id_usuario, token, activo, fecha_expiracion) VALUES (:uid, :token, true, :fecha_exp)"),
            {"uid": user["id_usuario"], "token": token, "fecha_exp": fecha_exp},
        )
        db.commit()

    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user["id_usuario"],
        "usuario": user["usuario"],
        "nombre": user["nombre"],
        "celular": user["celular"],
        "carnet": user["carnet"],
        "comunidad": user["comunidad"],
        "correo": user["correo"],
        "cargo": user["cargo"],
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
        "permisos": _get_permisos_response(user["id_rol"], db),
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
                correo, cargo,
                id_departamento, id_provincia, id_municipio, id_rol, activo)
            VALUES (:usuario, :contrasena, :nombre, :celular, :carnet, :comunidad,
                :correo, :cargo,
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
            "correo": data.correo,
            "cargo": data.cargo,
            "id_departamento": data.id_departamento,
            "id_provincia": data.id_provincia,
            "id_municipio": data.id_municipio,
            "id_rol": data.id_rol,
        },
    )
    db.commit()
    return result.scalar()


def verificar_identidad(db: Session, data: VerificarIdentidadRequest) -> dict | None:
    result = db.execute(
        text("""
            SELECT id_usuario FROM usuarios.usuario
            WHERE carnet = :carnet
              AND celular = :celular
              AND id_departamento = :dep
              AND id_provincia = :prov
              AND id_municipio = :muni
              AND comunidad = :comunidad
              AND activo = true
        """),
        {"carnet": data.carnet, "celular": data.celular, "dep": data.id_departamento,
         "prov": data.id_provincia, "muni": data.id_municipio, "comunidad": data.comunidad},
    ).mappings().first()
    return {"id_usuario": result["id_usuario"]} if result else None


def cambiar_contrasena(db: Session, data: CambiarContrasenaRequest) -> bool:
    user = db.execute(
        text("SELECT id_usuario FROM usuarios.usuario WHERE id_usuario = :id AND activo = true"),
        {"id": data.id_usuario},
    ).first()
    if not user:
        return False
    hashed = hash_password(data.nueva_contrasena)
    db.execute(
        text("UPDATE usuarios.usuario SET contrasena = :contrasena WHERE id_usuario = :id"),
        {"contrasena": hashed, "id": data.id_usuario},
    )
    db.commit()
    return True
