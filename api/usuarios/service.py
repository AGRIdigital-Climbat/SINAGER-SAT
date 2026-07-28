from sqlalchemy.orm import Session
from sqlalchemy import text
from ..auth.jwt import hash_password


SELECT_USUARIO = """
    SELECT u.id_usuario, u.usuario, u.nombre, u.celular, u.carnet, u.comunidad,
           u.correo, u.cargo,
           u.id_departamento, u.id_provincia, u.id_municipio, u.id_rol, u.activo,
           d.id as d_id, d.codigo_ine as d_codigo_ine, d.nombre as d_nombre,
           p.id as p_id, p.codigo_ine as p_codigo_ine, p.nombre as p_nombre,
           m.id as m_id, m.codigo_ine as m_codigo_ine, m.nombre as m_nombre,
            r.id_rol as r_id, r.nombre as r_nombre, r.descripcion as r_descripcion
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
    existing = db.execute(
        text("SELECT id_usuario FROM usuarios.usuario WHERE usuario = :u"),
        {"u": data["usuario"]},
    ).first()
    if existing:
        raise ValueError("El nombre de usuario ya existe")
    hashed = hash_password(data["contrasena"])
    result = db.execute(
        text("""
            INSERT INTO usuarios.usuario (usuario, contrasena, nombre, celular, carnet, comunidad,
                correo, cargo,
                id_departamento, id_provincia, id_municipio, id_rol, activo)
            VALUES (:usuario, :contrasena, :nombre, :celular, :carnet, :comunidad,
                :correo, :cargo,
                :id_departamento, :id_provincia, :id_municipio, :id_rol, :activo)
            RETURNING id_usuario
        """),
        {**data, "contrasena": hashed},
    )
    db.commit()
    return result.scalar()


def update_usuario(db: Session, id: int, data: dict) -> dict | None:
    if "usuario" in data and data["usuario"] is not None:
        existing = db.execute(
            text("SELECT id_usuario FROM usuarios.usuario WHERE usuario = :u AND id_usuario != :id"),
            {"u": data["usuario"], "id": id},
        ).first()
        if existing:
            raise ValueError("El nombre de usuario ya está en uso")
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


def get_roles(db: Session):
    rows = db.execute(text("SELECT * FROM usuarios.rol ORDER BY id_rol")).mappings().all()
    roles = [dict(r) for r in rows]
    for rol in roles:
        try:
            rol["permisos"] = _agrupar_permisos(db, rol["id_rol"])
        except Exception:
            rol["permisos"] = {}
    return roles


def get_rol(db: Session, id: int):
    row = db.execute(text("SELECT * FROM usuarios.rol WHERE id_rol = :id"), {"id": id}).mappings().first()
    if not row:
        return None
    rol = dict(row)
    rol["permisos"] = _agrupar_permisos(db, id)
    return rol


def create_rol(db: Session, data: dict) -> int:
    result = db.execute(
        text("INSERT INTO usuarios.rol (nombre, descripcion) VALUES (:nombre, :descripcion) RETURNING id_rol"),
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


# ── APLICACIONES ──

def get_aplicaciones(db: Session):
    rows = db.execute(text("SELECT * FROM usuarios.aplicacion ORDER BY id_aplicacion")).mappings().all()
    return [dict(r) for r in rows]


def get_aplicacion(db: Session, id: int):
    row = db.execute(text("SELECT * FROM usuarios.aplicacion WHERE id_aplicacion = :id"), {"id": id}).mappings().first()
    return dict(row) if row else None


def create_aplicacion(db: Session, data: dict) -> int:
    result = db.execute(
        text("INSERT INTO usuarios.aplicacion (codigo, nombre, descripcion, activo) VALUES (:codigo, :nombre, :descripcion, :activo) RETURNING id_aplicacion"),
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


# ── ACCIONES ──

ACCION_SELECT = "SELECT id_accion, codigo, nombre FROM usuarios.accion"


def get_acciones(db: Session):
    rows = db.execute(text(f"{ACCION_SELECT} ORDER BY id_accion")).mappings().all()
    return [dict(r) for r in rows]


def get_accion(db: Session, id: int):
    row = db.execute(text(f"{ACCION_SELECT} WHERE id_accion = :id"), {"id": id}).mappings().first()
    return dict(row) if row else None


def create_accion(db: Session, data: dict) -> int:
    result = db.execute(
        text("INSERT INTO usuarios.accion (codigo, nombre) VALUES (:codigo, :nombre) RETURNING id_accion"),
        data,
    )
    db.commit()
    return result.scalar()


def update_accion(db: Session, id: int, data: dict) -> dict | None:
    fields = {k: v for k, v in data.items() if v is not None}
    if not fields:
        return get_accion(db, id)
    fields["id_accion"] = id
    set_clause = ", ".join(f"{k} = :{k}" for k in fields)
    db.execute(text(f"UPDATE usuarios.accion SET {set_clause} WHERE id_accion = :id_accion"), fields)
    db.commit()
    return get_accion(db, id)


def delete_accion(db: Session, id: int) -> bool:
    result = db.execute(text("DELETE FROM usuarios.accion WHERE id_accion = :id"), {"id": id})
    db.commit()
    return result.rowcount > 0


# ── PERMISOS ──

PERMISO_SELECT = """
    SELECT p.id_permiso, p.id_rol, p.id_aplicacion, p.id_accion,
           r.nombre as rol_nombre,
           a.codigo as app_codigo, a.nombre as app_nombre,
           ac.codigo as accion_codigo, ac.nombre as accion_nombre
    FROM usuarios.permiso p
    JOIN usuarios.rol r ON p.id_rol = r.id_rol
    JOIN usuarios.aplicacion a ON p.id_aplicacion = a.id_aplicacion
    JOIN usuarios.accion ac ON p.id_accion = ac.id_accion
"""


def get_permisos(db: Session, id_rol: int | None = None):
    if id_rol:
        rows = db.execute(
            text(f"{PERMISO_SELECT} WHERE p.id_rol = :r ORDER BY a.id_aplicacion, ac.id_accion"),
            {"r": id_rol},
        ).mappings().all()
        return [dict(r) for r in rows]
    rows = db.execute(
        text(f"{PERMISO_SELECT} ORDER BY r.id_rol, a.id_aplicacion, ac.id_accion")
    ).mappings().all()
    return [dict(r) for r in rows]


def assign_permiso(db: Session, id_rol: int, id_aplicacion: int, id_accion: int):
    db.execute(
        text("INSERT INTO usuarios.permiso (id_rol, id_aplicacion, id_accion) VALUES (:r, :a, :ac) ON CONFLICT DO NOTHING"),
        {"r": id_rol, "a": id_aplicacion, "ac": id_accion},
    )
    db.commit()


def remove_permiso(db: Session, id_rol: int, id_aplicacion: int, id_accion: int) -> bool:
    result = db.execute(
        text("DELETE FROM usuarios.permiso WHERE id_rol = :r AND id_aplicacion = :a AND id_accion = :ac"),
        {"r": id_rol, "a": id_aplicacion, "ac": id_accion},
    )
    db.commit()
    return result.rowcount > 0


def get_rol_permisos_agrupados(db: Session, id_rol: int) -> dict:
    row = db.execute(text("SELECT * FROM usuarios.rol WHERE id_rol = :id"), {"id": id_rol}).mappings().first()
    if not row:
        return None
    rol = dict(row)
    rol["permisos"] = _agrupar_permisos(db, id_rol)
    return rol


def get_permisos_estructura(db: Session) -> dict:
    roles = db.execute(text("SELECT * FROM usuarios.rol ORDER BY id_rol")).mappings().all()
    apps = db.execute(text("SELECT * FROM usuarios.aplicacion ORDER BY id_aplicacion")).mappings().all()
    acciones = db.execute(text("SELECT * FROM usuarios.accion ORDER BY id_accion")).mappings().all()

    matriz = {}
    for r in roles:
        rid = r["id_rol"]
        matriz[rid] = _agrupar_permisos(db, rid)

    return {
        "roles": [dict(r) for r in roles],
        "aplicaciones": [dict(a) for a in apps],
        "acciones": [dict(ac) for ac in acciones],
        "matriz": matriz,
    }


def assign_permisos_batch(db: Session, id_rol: int, permisos: dict[str, list[str]]):
    db.execute(text("DELETE FROM usuarios.permiso WHERE id_rol = :r"), {"r": id_rol})
    apps = {a["codigo"]: a["id_aplicacion"] for a in db.execute(
        text("SELECT id_aplicacion, codigo FROM usuarios.aplicacion")
    ).mappings().all()}
    accs = {a["codigo"]: a["id_accion"] for a in db.execute(
        text("SELECT id_accion, codigo FROM usuarios.accion")
    ).mappings().all()}
    for app_codigo, acciones_list in permisos.items():
        id_app = apps.get(app_codigo)
        if id_app is None:
            continue
        for acc_codigo in acciones_list:
            id_acc = accs.get(acc_codigo)
            if id_acc is None:
                continue
            db.execute(
                text("INSERT INTO usuarios.permiso (id_rol, id_aplicacion, id_accion) VALUES (:r, :a, :ac) ON CONFLICT DO NOTHING"),
                {"r": id_rol, "a": id_app, "ac": id_acc},
            )
    db.commit()


# ── SESIONES ──

def get_sesiones(db: Session, id_usuario: int | None = None):
    cols = "id_sesion, id_usuario, fecha_inicio, fecha_expiracion, ip_origen, activo"
    if id_usuario:
        rows = db.execute(
            text(f"SELECT {cols} FROM usuarios.sesion WHERE id_usuario = :id ORDER BY fecha_inicio DESC"),
            {"id": id_usuario},
        ).mappings().all()
        return [dict(r) for r in rows]
    rows = db.execute(text(f"SELECT {cols} FROM usuarios.sesion ORDER BY fecha_inicio DESC LIMIT 100")).mappings().all()
    return [dict(r) for r in rows]


# ── AUDITORIA ──

def get_auditoria(db: Session, id_usuario: int | None = None,
                  id_aplicacion: int | None = None,
                  accion: str | None = None,
                  fecha_desde: str | None = None,
                  fecha_hasta: str | None = None,
                  id_rol: int | None = None,
                  id_municipio: int | None = None,
                  skip: int = 0, limit: int = 100):
    conditions = []
    params = {}

    if id_usuario is not None:
        conditions.append("a.id_usuario = :id_usuario")
        params["id_usuario"] = id_usuario
    if id_aplicacion is not None:
        conditions.append("a.id_aplicacion = :id_aplicacion")
        params["id_aplicacion"] = id_aplicacion
    if accion is not None:
        conditions.append("a.accion = :accion")
        params["accion"] = accion
    if fecha_desde is not None:
        conditions.append("a.fecha >= :fecha_desde")
        params["fecha_desde"] = fecha_desde
    if fecha_hasta is not None:
        conditions.append("a.fecha <= :fecha_hasta")
        params["fecha_hasta"] = fecha_hasta
    if id_rol is not None:
        conditions.append("u.id_rol = :id_rol")
        params["id_rol"] = id_rol
    if id_municipio is not None:
        conditions.append("u.id_municipio = :id_municipio")
        params["id_municipio"] = id_municipio

    where_clause = " AND ".join(conditions) if conditions else "TRUE"

    joins = """
        FROM usuarios.auditoria a
        LEFT JOIN usuarios.usuario u ON u.id_usuario = a.id_usuario
        LEFT JOIN usuarios.rol r ON r.id_rol = u.id_rol
        LEFT JOIN shared.municipio m ON m.id = u.id_municipio
        LEFT JOIN shared.provincia p ON p.id = u.id_provincia
        LEFT JOIN shared.departamento d ON d.id = u.id_departamento
        LEFT JOIN usuarios.aplicacion ap ON ap.id_aplicacion = a.id_aplicacion
    """

    total = db.execute(
        text(f"SELECT COUNT(*) {joins} WHERE {where_clause}"),
        params,
    ).scalar()

    rows = db.execute(
        text(f"""
            SELECT a.*,
                   u.usuario, u.nombre as usuario_nombre,
                   u.id_rol, r.nombre as rol_nombre,
                   u.id_municipio, m.nombre as municipio_nombre,
                   m.codigo_ine as municipio_codigo,
                   p.nombre as provincia_nombre,
                   d.nombre as departamento_nombre,
                   ap.codigo as app_codigo, ap.nombre as app_nombre
            {joins}
            WHERE {where_clause}
            ORDER BY a.fecha DESC
            LIMIT :limit OFFSET :skip
        """),
        {**params, "limit": limit, "skip": skip},
    ).mappings().all()

    return [dict(r) for r in rows], total
