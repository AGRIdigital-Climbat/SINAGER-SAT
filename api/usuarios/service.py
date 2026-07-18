from sqlalchemy.orm import Session
from sqlalchemy import text
from ..auth.jwt import hash_password


SELECT_USUARIO = """
    SELECT u.id_usuario, u.usuario, u.nombre, u.celular, u.carnet, u.comunidad,
           u.id_departamento, u.id_provincia, u.id_municipio, u.id_rol,
           r.nombre as rol, u.activo
    FROM usuarios.usuario u
    LEFT JOIN usuarios.rol r ON u.id_rol = r.id_rol
"""


# ── USUARIOS ──

def get_usuarios(db: Session, skip: int = 0, limit: int = 50):
    return db.execute(
        text(f"{SELECT_USUARIO} ORDER BY u.id_usuario LIMIT :limit OFFSET :skip"),
        {"limit": limit, "skip": skip},
    ).mappings().all()


def get_usuario(db: Session, id: int):
    return db.execute(
        text(f"{SELECT_USUARIO} WHERE u.id_usuario = :id"),
        {"id": id},
    ).mappings().first()


def create_usuario(db: Session, data: dict) -> int:
    hashed = hash_password(data["contrasena"])
    result = db.execute(
        text("""
            INSERT INTO usuarios.usuario (usuario, contrasena, nombre, celular, carnet, comunidad,
                id_departamento, id_provincia, id_municipio, id_rol, activo)
            VALUES (:usuario, :contrasena, :nombre, :celular, :carnet, :comunidad,
                :id_departamento, :id_provincia, :id_municipio, :id_rol, :activo)
            RETURNING id_usuario
        """),
        {**data, "contrasena": hashed},
    )
    db.commit()
    return result.scalar()


def update_usuario(db: Session, id: int, data: dict) -> dict | None:
    if "contrasena" in data and data["contrasena"]:
        data["contrasena"] = hash_password(data["contrasena"])
    fields = {k: v for k, v in data.items() if v is not None}
    if not fields:
        return get_usuario(db, id)
    fields["id_usuario"] = id
    set_clause = ", ".join(f"{k} = :{k}" for k in fields)
    db.execute(text(f"UPDATE usuarios.usuario SET {set_clause} WHERE id_usuario = :id_usuario"), fields)
    db.commit()
    return get_usuario(db, id)


def delete_usuario(db: Session, id: int) -> bool:
    result = db.execute(text("UPDATE usuarios.usuario SET activo = false WHERE id_usuario = :id"), {"id": id})
    db.commit()
    return result.rowcount > 0


# ── ROLES ──

def get_roles(db: Session):
    return db.execute(text("SELECT * FROM usuarios.rol ORDER BY jerarquia DESC")).mappings().all()


def get_rol(db: Session, id: int):
    return db.execute(text("SELECT * FROM usuarios.rol WHERE id_rol = :id"), {"id": id}).mappings().first()


def create_rol(db: Session, data: dict) -> int:
    result = db.execute(
        text("INSERT INTO usuarios.rol (nombre, descripcion, jerarquia) VALUES (:n, :d, :j) RETURNING id_rol"),
        data,
    )
    db.commit()
    return result.scalar()


def update_rol(db: Session, id: int, data: dict) -> dict | None:
    fields = {k: v for k, v in data.items() if v is not None}
    if not fields:
        return get_rol(db, id)
    fields["id_rol"] = id
    set_clause = ", ".join(f"{k} = :{k}" for k in fields)
    db.execute(text(f"UPDATE usuarios.rol SET {set_clause} WHERE id_rol = :id_rol"), fields)
    db.commit()
    return get_rol(db, id)


def delete_rol(db: Session, id: int) -> bool:
    result = db.execute(text("DELETE FROM usuarios.rol WHERE id_rol = :id"), {"id": id})
    db.commit()
    return result.rowcount > 0


# ── USUARIO_ROL ──

def get_usuario_roles(db: Session, id_usuario: int):
    return db.execute(
        text("SELECT id_usuario, id_rol FROM usuarios.usuario_rol WHERE id_usuario = :id"),
        {"id": id_usuario},
    ).mappings().all()


def assign_rol(db: Session, id_usuario: int, id_rol: int):
    db.execute(
        text("INSERT INTO usuarios.usuario_rol (id_usuario, id_rol) VALUES (:u, :r) ON CONFLICT DO NOTHING"),
        {"u": id_usuario, "r": id_rol},
    )
    db.commit()


def remove_rol(db: Session, id_usuario: int, id_rol: int) -> bool:
    result = db.execute(
        text("DELETE FROM usuarios.usuario_rol WHERE id_usuario = :u AND id_rol = :r"),
        {"u": id_usuario, "r": id_rol},
    )
    db.commit()
    return result.rowcount > 0


# ── APLICACIONES ──

def get_aplicaciones(db: Session):
    return db.execute(text("SELECT * FROM usuarios.aplicacion ORDER BY id_aplicacion")).mappings().all()


def get_aplicacion(db: Session, id: int):
    return db.execute(text("SELECT * FROM usuarios.aplicacion WHERE id_aplicacion = :id"), {"id": id}).mappings().first()


def create_aplicacion(db: Session, data: dict) -> int:
    result = db.execute(
        text("INSERT INTO usuarios.aplicacion (codigo, nombre, descripcion, activo) VALUES (:c, :n, :d, :a) RETURNING id_aplicacion"),
        data,
    )
    db.commit()
    return result.scalar()


def update_aplicacion(db: Session, id: int, data: dict) -> dict | None:
    fields = {k: v for k, v in data.items() if v is not None}
    if not fields:
        return get_aplicacion(db, id)
    fields["id_aplicacion"] = id
    set_clause = ", ".join(f"{k} = :{k}" for k in fields)
    db.execute(text(f"UPDATE usuarios.aplicacion SET {set_clause} WHERE id_aplicacion = :id_aplicacion"), fields)
    db.commit()
    return get_aplicacion(db, id)


def delete_aplicacion(db: Session, id: int) -> bool:
    result = db.execute(text("DELETE FROM usuarios.aplicacion WHERE id_aplicacion = :id"), {"id": id})
    db.commit()
    return result.rowcount > 0


# ── PERMISOS ──

def get_permisos(db: Session, id_rol: int | None = None):
    if id_rol:
        return db.execute(
            text("SELECT id_rol, id_aplicacion FROM usuarios.permiso_aplicacion WHERE id_rol = :r"),
            {"r": id_rol},
        ).mappings().all()
    return db.execute(text("SELECT id_rol, id_aplicacion FROM usuarios.permiso_aplicacion")).mappings().all()


def assign_permiso(db: Session, id_rol: int, id_aplicacion: int):
    db.execute(
        text("INSERT INTO usuarios.permiso_aplicacion (id_rol, id_aplicacion) VALUES (:r, :a) ON CONFLICT DO NOTHING"),
        {"r": id_rol, "a": id_aplicacion},
    )
    db.commit()


def remove_permiso(db: Session, id_rol: int, id_aplicacion: int) -> bool:
    result = db.execute(
        text("DELETE FROM usuarios.permiso_aplicacion WHERE id_rol = :r AND id_aplicacion = :a"),
        {"r": id_rol, "a": id_aplicacion},
    )
    db.commit()
    return result.rowcount > 0


# ── SESIONES ──

def get_sesiones(db: Session, id_usuario: int | None = None):
    if id_usuario:
        return db.execute(
            text("SELECT * FROM usuarios.sesion WHERE id_usuario = :id ORDER BY fecha_inicio DESC"),
            {"id": id_usuario},
        ).mappings().all()
    return db.execute(text("SELECT * FROM usuarios.sesion ORDER BY fecha_inicio DESC LIMIT 100")).mappings().all()


# ── AUDITORIA ──

def get_auditoria(db: Session, id_usuario: int | None = None, skip: int = 0, limit: int = 100):
    if id_usuario:
        return db.execute(
            text("SELECT * FROM usuarios.auditoria WHERE id_usuario = :id ORDER BY fecha DESC LIMIT :limit OFFSET :skip"),
            {"id": id_usuario, "limit": limit, "skip": skip},
        ).mappings().all()
    return db.execute(
        text("SELECT * FROM usuarios.auditoria ORDER BY fecha DESC LIMIT :limit OFFSET :skip"),
        {"limit": limit, "skip": skip},
    ).mappings().all()


# ── RESET CONTRASEÑA ──

def get_resets(db: Session, id_usuario: int | None = None):
    if id_usuario:
        return db.execute(
            text("SELECT * FROM usuarios.reset_contrasena WHERE id_usuario = :id ORDER BY fecha_solicitud DESC"),
            {"id": id_usuario},
        ).mappings().all()
    return db.execute(text("SELECT * FROM usuarios.reset_contrasena ORDER BY fecha_solicitud DESC LIMIT 100")).mappings().all()
