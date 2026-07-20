from sqlalchemy.orm import Session
from sqlalchemy import text
from ..auth.jwt import hash_password


SELECT_USUARIO = """
    SELECT u.id_usuario, u.usuario, u.nombre, u.celular, u.carnet, u.comunidad,
           u.id_departamento, u.id_provincia, u.id_municipio, u.id_rol, u.activo,
           d.id as d_id, d.codigo_ine as d_codigo_ine, d.nombre as d_nombre,
           p.id as p_id, p.codigo_ine as p_codigo_ine, p.nombre as p_nombre,
           m.id as m_id, m.codigo_ine as m_codigo_ine, m.nombre as m_nombre,
           r.id_rol as r_id, r.nombre as r_nombre, r.descripcion as r_descripcion, r.jerarquia as r_jerarquia
    FROM usuarios.usuario u
    LEFT JOIN shared.departamento d ON u.id_departamento = d.id
    LEFT JOIN shared.provincia p ON u.id_provincia = p.id
    LEFT JOIN shared.municipio m ON u.id_municipio = m.id
    LEFT JOIN usuarios.rol r ON u.id_rol = r.id_rol
"""


def _build_usuario(row):
    data = dict(row)
    data["departamento"] = {
        "id": data.pop("d_id"),
        "codigo_ine": data.pop("d_codigo_ine"),
        "nombre": data.pop("d_nombre"),
    } if data.get("d_id") else None
    data["provincia"] = {
        "id": data.pop("p_id"),
        "codigo_ine": data.pop("p_codigo_ine"),
        "nombre": data.pop("p_nombre"),
    } if data.get("p_id") else None
    data["municipio"] = {
        "id": data.pop("m_id"),
        "codigo_ine": data.pop("m_codigo_ine"),
        "nombre": data.pop("m_nombre"),
    } if data.get("m_id") else None
    data["rol"] = {
        "id_rol": data.pop("r_id"),
        "nombre": data.pop("r_nombre"),
        "descripcion": data.pop("r_descripcion"),
        "jerarquia": data.pop("r_jerarquia"),
    } if data.get("r_id") else None
    return data


# ── USUARIOS ──

def get_usuarios(db: Session, skip: int = 0, limit: int = 50):
    rows = db.execute(
        text(f"{SELECT_USUARIO} ORDER BY u.id_usuario LIMIT :limit OFFSET :skip"),
        {"limit": limit, "skip": skip},
    ).mappings().all()
    return [_build_usuario(r) for r in rows]


def get_usuario(db: Session, id: int):
    row = db.execute(
        text(f"{SELECT_USUARIO} WHERE u.id_usuario = :id"),
        {"id": id},
    ).mappings().first()
    return _build_usuario(row) if row else None


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
    rows = db.execute(text("SELECT * FROM usuarios.rol ORDER BY jerarquia DESC")).mappings().all()
    return [dict(r) for r in rows]


def get_rol(db: Session, id: int):
    row = db.execute(text("SELECT * FROM usuarios.rol WHERE id_rol = :id"), {"id": id}).mappings().first()
    return dict(row) if row else None


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
    rows = db.execute(
        text("SELECT id_usuario, id_rol FROM usuarios.usuario_rol WHERE id_usuario = :id"),
        {"id": id_usuario},
    ).mappings().all()
    return [dict(r) for r in rows]


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
    rows = db.execute(text("SELECT * FROM usuarios.aplicacion ORDER BY id_aplicacion")).mappings().all()
    return [dict(r) for r in rows]


def get_aplicacion(db: Session, id: int):
    row = db.execute(text("SELECT * FROM usuarios.aplicacion WHERE id_aplicacion = :id"), {"id": id}).mappings().first()
    return dict(row) if row else None


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
        rows = db.execute(
            text("SELECT id_rol, id_aplicacion FROM usuarios.permiso_aplicacion WHERE id_rol = :r"),
            {"r": id_rol},
        ).mappings().all()
        return [dict(r) for r in rows]
    rows = db.execute(text("SELECT id_rol, id_aplicacion FROM usuarios.permiso_aplicacion")).mappings().all()
    return [dict(r) for r in rows]


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
        rows = db.execute(
            text("SELECT * FROM usuarios.sesion WHERE id_usuario = :id ORDER BY fecha_inicio DESC"),
            {"id": id_usuario},
        ).mappings().all()
        return [dict(r) for r in rows]
    rows = db.execute(text("SELECT * FROM usuarios.sesion ORDER BY fecha_inicio DESC LIMIT 100")).mappings().all()
    return [dict(r) for r in rows]


# ── AUDITORIA ──

def get_auditoria(db: Session, id_usuario: int | None = None, skip: int = 0, limit: int = 100):
    if id_usuario:
        rows = db.execute(
            text("SELECT * FROM usuarios.auditoria WHERE id_usuario = :id ORDER BY fecha DESC LIMIT :limit OFFSET :skip"),
            {"id": id_usuario, "limit": limit, "skip": skip},
        ).mappings().all()
        return [dict(r) for r in rows]
    rows = db.execute(
        text("SELECT * FROM usuarios.auditoria ORDER BY fecha DESC LIMIT :limit OFFSET :skip"),
        {"limit": limit, "skip": skip},
    ).mappings().all()
    return [dict(r) for r in rows]


# ── RESET CONTRASEÑA ──

def get_resets(db: Session, id_usuario: int | None = None):
    if id_usuario:
        rows = db.execute(
            text("SELECT * FROM usuarios.reset_contrasena WHERE id_usuario = :id ORDER BY fecha_solicitud DESC"),
            {"id": id_usuario},
        ).mappings().all()
        return [dict(r) for r in rows]
    rows = db.execute(text("SELECT * FROM usuarios.reset_contrasena ORDER BY fecha_solicitud DESC LIMIT 100")).mappings().all()
    return [dict(r) for r in rows]
