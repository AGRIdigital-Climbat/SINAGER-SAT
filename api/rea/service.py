from sqlalchemy.orm import Session
from sqlalchemy import text


REPORTE_COLS = {
    "id_usuario", "id_departamento", "id_provincia", "id_municipio",
    "comunidad", "fecha_evento", "hora_evento", "id_tipo_evento",
    "coordenada_lat", "coordenada_lon", "fotografia", "descripcion", "id_estado",
}

ESTADO_COLS = {"nombre", "descripcion", "orden"}

CAT_COLS = {"nombre", "descripcion", "orden"}


# ── REPORTE EVENTO ──

USER_COLS = """
           u.id_usuario as u_id, u.usuario as u_usuario, u.nombre as u_nombre,
           u.celular as u_celular, u.carnet as u_carnet, u.comunidad as u_comunidad,
           u.correo as u_correo, u.cargo as u_cargo, u.activo as u_activo,
           u.id_rol as u_id_rol, u.id_departamento as u_dep_id, u.id_provincia as u_prov_id, u.id_municipio as u_muni_id,
           rol.id_rol as r_id, rol.nombre as r_nombre, rol.descripcion as r_descripcion,
           ud.id as ud_id, ud.codigo_ine as ud_codigo_ine, ud.nombre as ud_nombre,
           up.id as up_id, up.codigo_ine as up_codigo_ine, up.nombre as up_nombre,
           um.id as um_id, um.codigo_ine as um_codigo_ine, um.nombre as um_nombre
"""

USER_JOIN = """
    LEFT JOIN usuarios.usuario u ON re.id_usuario = u.id_usuario
    LEFT JOIN usuarios.rol rol ON u.id_rol = rol.id_rol
    LEFT JOIN shared.departamento ud ON u.id_departamento = ud.id
    LEFT JOIN shared.provincia up ON u.id_provincia = up.id
    LEFT JOIN shared.municipio um ON u.id_municipio = um.id
"""

SQL_REPORTE = """
    SELECT re.*,
           d.id as d_id, d.codigo_ine as d_codigo_ine, d.nombre as d_nombre,
           prov.id as prov_id, prov.codigo_ine as prov_codigo_ine, prov.nombre as prov_nombre,
           m.id as m_id, m.codigo_ine as m_codigo_ine, m.nombre as m_nombre,
           te.id_tipo_evento as te_id, te.nombre as te_nombre,
           er.id_estado as er_id, er.nombre as er_nombre, er.descripcion as er_descripcion, er.orden as er_orden,
""" + USER_COLS + """
    FROM rea.reporte_evento re
    LEFT JOIN shared.departamento d ON re.id_departamento = d.id
    LEFT JOIN shared.provincia prov ON re.id_provincia = prov.id
    LEFT JOIN shared.municipio m ON re.id_municipio = m.id
    LEFT JOIN edan.tipo_evento te ON re.id_tipo_evento = te.id_tipo_evento
    LEFT JOIN rea.estado_reporte er ON re.id_estado = er.id_estado
""" + USER_JOIN


def _build_usuario_node(data):
    if not data.get("u_id"):
        for k in ("u_id", "u_usuario", "u_nombre", "u_celular", "u_carnet", "u_comunidad",
                  "u_correo", "u_cargo", "u_activo", "u_id_rol",
                  "u_dep_id", "u_prov_id", "u_muni_id",
                  "r_id", "r_nombre", "r_descripcion",
                  "ud_id", "ud_codigo_ine", "ud_nombre",
                  "up_id", "up_codigo_ine", "up_nombre",
                  "um_id", "um_codigo_ine", "um_nombre"):
            data.pop(k, None)
        return None
    departamento = {
        "id": data.pop("ud_id"),
        "codigo_ine": data.pop("ud_codigo_ine"),
        "nombre": data.pop("ud_nombre"),
    } if data.get("ud_id") else None
    provincia = {
        "id": data.pop("up_id"),
        "codigo_ine": data.pop("up_codigo_ine"),
        "nombre": data.pop("up_nombre"),
        "departamento": departamento,
    } if data.get("up_id") else None
    municipio = {
        "id": data.pop("um_id"),
        "codigo_ine": data.pop("um_codigo_ine"),
        "nombre": data.pop("um_nombre"),
        "departamento": departamento,
        "provincia": provincia,
    } if data.get("um_id") else None
    rol = {
        "id_rol": data.pop("r_id"),
        "nombre": data.pop("r_nombre"),
        "descripcion": data.pop("r_descripcion"),
    } if data.get("r_id") else None
    return {
        "id_usuario": data.pop("u_id"),
        "usuario": data.pop("u_usuario"),
        "nombre": data.pop("u_nombre"),
        "celular": data.pop("u_celular"),
        "carnet": data.pop("u_carnet"),
        "comunidad": data.pop("u_comunidad"),
        "correo": data.pop("u_correo"),
        "cargo": data.pop("u_cargo"),
        "activo": data.pop("u_activo"),
        "id_rol": data.pop("u_id_rol"),
        "rol": rol,
        "id_departamento": data.pop("u_dep_id"),
        "id_provincia": data.pop("u_prov_id"),
        "id_municipio": data.pop("u_muni_id"),
        "departamento": departamento,
        "provincia": provincia,
        "municipio": municipio,
    }


def _build_reporte(row):
    data = dict(row)
    data["departamento"] = {
        "id": data.pop("d_id"),
        "codigo_ine": data.pop("d_codigo_ine"),
        "nombre": data.pop("d_nombre"),
    } if data.get("d_id") else None
    if data.get("prov_id"):
        data["provincia"] = {
            "id": data.pop("prov_id"),
            "codigo_ine": data.pop("prov_codigo_ine"),
            "nombre": data.pop("prov_nombre"),
        }
    else:
        data.pop("prov_id", None)
        data.pop("prov_codigo_ine", None)
        data.pop("prov_nombre", None)
        data["provincia"] = None
    data["municipio"] = {
        "id": data.pop("m_id"),
        "codigo_ine": data.pop("m_codigo_ine"),
        "nombre": data.pop("m_nombre"),
        "departamento": data["departamento"],
        "provincia": data["provincia"],
    } if data.get("m_id") else None
    data["tipo_evento"] = {
        "id_tipo_evento": data.pop("te_id"),
        "nombre": data.pop("te_nombre"),
    } if data.get("te_id") else None
    data["estado"] = {
        "id_estado": data.pop("er_id"),
        "nombre": data.pop("er_nombre"),
        "descripcion": data.pop("er_descripcion"),
        "orden": data.pop("er_orden"),
    } if data.get("er_id") else None
    data["usuario"] = _build_usuario_node(data)
    return data


def _get_categorias(db: Session, id_reporte: int) -> list:
    rows = db.execute(
        text("""
            SELECT ac.id_categoria, ac.nombre, ac.descripcion, ac.orden
            FROM rea.reporte_afectacion ra
            JOIN rea.afectacion_categoria ac ON ra.id_categoria = ac.id_categoria
            WHERE ra.id_reporte = :id ORDER BY ac.orden
        """),
        {"id": id_reporte},
    ).mappings().all()
    return [
        {"id_categoria": r["id_categoria"], "nombre": r["nombre"], "descripcion": r["descripcion"], "orden": r["orden"]}
        for r in rows
    ]


def get_reportes(db: Session, id_estado: int | None = None, id_municipio: int | None = None, skip: int = 0, limit: int = 50):
    query = SQL_REPORTE
    count_query = "SELECT COUNT(*) FROM rea.reporte_evento re"
    params = {}
    conditions = []
    if id_estado:
        c = "re.id_estado = :estado"
        conditions.append(c)
        params["estado"] = id_estado
    if id_municipio:
        c = "re.id_municipio = :muni"
        conditions.append(c)
        params["muni"] = id_municipio
    if conditions:
        where = " WHERE " + " AND ".join(conditions)
        query += where
        count_query += where
    total = db.execute(text(count_query), params).scalar()
    query += " ORDER BY re.id_reporte DESC LIMIT :limit OFFSET :skip"
    params["limit"] = limit
    params["skip"] = skip
    rows = db.execute(text(query), params).mappings().all()
    data = []
    for r in rows:
        item = _build_reporte(r)
        item["categorias"] = _get_categorias(db, item["id_reporte"])
        data.append(item)
    return data, total


def get_mis_resumen(db: Session, id_usuario: int, skip: int = 0, limit: int = 50):
    total = db.execute(
        text("SELECT COUNT(*) FROM rea.reporte_evento WHERE id_usuario = :uid"),
        {"uid": id_usuario},
    ).scalar()
    rows = db.execute(
        text(f"""
            SELECT re.id_reporte, re.id_estado,{USER_COLS}
            FROM rea.reporte_evento re{USER_JOIN}
            WHERE re.id_usuario = :uid ORDER BY re.id_reporte DESC LIMIT :limit OFFSET :skip
        """),
        {"uid": id_usuario, "limit": limit, "skip": skip},
    ).mappings().all()
    data = []
    for r in rows:
        item = dict(r)
        item["usuario"] = _build_usuario_node(item)
        data.append(item)
    return data, total


def get_mis_reportes(db: Session, id_usuario: int, skip: int = 0, limit: int = 50):
    total = db.execute(
        text("SELECT COUNT(*) FROM rea.reporte_evento WHERE id_usuario = :uid"),
        {"uid": id_usuario},
    ).scalar()
    query = SQL_REPORTE + " WHERE re.id_usuario = :uid ORDER BY re.id_reporte DESC LIMIT :limit OFFSET :skip"
    rows = db.execute(text(query), {"uid": id_usuario, "limit": limit, "skip": skip}).mappings().all()
    data = []
    for r in rows:
        item = _build_reporte(r)
        item["categorias"] = _get_categorias(db, item["id_reporte"])
        data.append(item)
    return data, total


def get_reporte(db: Session, id: int):
    row = db.execute(
        text(f"{SQL_REPORTE} WHERE re.id_reporte = :id"), {"id": id}
    ).mappings().first()
    return _build_reporte(row) if row else None


def get_reporte_completo(db: Session, id: int):
    reporte = get_reporte(db, id)
    if not reporte:
        return None
    result = dict(reporte)
    result["categorias"] = _get_categorias(db, id)
    return result


def create_reporte(db: Session, data: dict) -> int:
    categorias = data.pop("categorias", None)
    safe_data = {k: v for k, v in data.items() if k in REPORTE_COLS}
    cols = ", ".join(safe_data.keys())
    vals = ", ".join(f":{k}" for k in safe_data.keys())
    result = db.execute(
        text(f"INSERT INTO rea.reporte_evento ({cols}) VALUES ({vals}) RETURNING id_reporte"), safe_data
    )
    reporte_id = result.scalar()
    if categorias:
        for cat_id in categorias:
            db.execute(
                text("INSERT INTO rea.reporte_afectacion (id_reporte, id_categoria) VALUES (:r, :c)"),
                {"r": reporte_id, "c": cat_id},
            )
    db.commit()
    return reporte_id


def _build_set_clause(fields: dict, whitelist: set) -> tuple[list[str], dict]:
    set_parts = []
    param_dict = {}
    for k, v in fields.items():
        if k not in whitelist:
            continue
        if v is None:
            set_parts.append(f"{k} = NULL")
        else:
            set_parts.append(f"{k} = :{k}")
            param_dict[k] = v
    return set_parts, param_dict


def update_reporte(db: Session, id: int, data: dict) -> dict | None:
    categorias = data.pop("categorias", None)
    set_parts, params = _build_set_clause(data, REPORTE_COLS)
    if set_parts:
        params["id_reporte"] = id
        db.execute(text(f"UPDATE rea.reporte_evento SET {', '.join(set_parts)} WHERE id_reporte = :id_reporte"), params)
    if categorias is not None:
        db.execute(text("DELETE FROM rea.reporte_afectacion WHERE id_reporte = :id"), {"id": id})
        for cat_id in categorias:
            db.execute(
                text("INSERT INTO rea.reporte_afectacion (id_reporte, id_categoria) VALUES (:r, :c)"),
                {"r": id, "c": cat_id},
            )
    db.commit()
    return get_reporte_completo(db, id)


def change_estado(db: Session, id: int, id_estado: int) -> dict | None:
    db.execute(
        text("UPDATE rea.reporte_evento SET id_estado = :estado WHERE id_reporte = :id"),
        {"estado": id_estado, "id": id},
    )
    db.commit()
    return get_reporte_completo(db, id)


def delete_reporte(db: Session, id: int) -> bool:
    db.execute(text("DELETE FROM rea.reporte_afectacion WHERE id_reporte = :id"), {"id": id})
    result = db.execute(text("DELETE FROM rea.reporte_evento WHERE id_reporte = :id"), {"id": id})
    db.commit()
    return result.rowcount > 0


# ── ESTADO REPORTE ──

def get_estados(db: Session):
    rows = db.execute(text("SELECT * FROM rea.estado_reporte ORDER BY orden")).mappings().all()
    return [dict(r) for r in rows]


def get_estado(db: Session, id: int):
    row = db.execute(text("SELECT * FROM rea.estado_reporte WHERE id_estado = :id"), {"id": id}).mappings().first()
    return dict(row) if row else None


def create_estado(db: Session, data: dict) -> int:
    result = db.execute(
        text("INSERT INTO rea.estado_reporte (nombre, descripcion, orden) VALUES (:n, :d, :o) RETURNING id_estado"),
        data,
    )
    db.commit()
    return result.scalar()


def update_estado(db: Session, id: int, data: dict) -> dict | None:
    set_parts, params = _build_set_clause(data, ESTADO_COLS)
    if not set_parts:
        return get_estado(db, id)
    params["id_estado"] = id
    db.execute(text(f"UPDATE rea.estado_reporte SET {', '.join(set_parts)} WHERE id_estado = :id_estado"), params)
    db.commit()
    return get_estado(db, id)


def delete_estado(db: Session, id: int) -> bool:
    result = db.execute(text("DELETE FROM rea.estado_reporte WHERE id_estado = :id"), {"id": id})
    db.commit()
    return result.rowcount > 0


# ── AFFECTACION CATEGORIA ──

def get_categorias(db: Session):
    rows = db.execute(text("SELECT * FROM rea.afectacion_categoria ORDER BY orden")).mappings().all()
    return [dict(r) for r in rows]


def get_categoria(db: Session, id: int):
    row = db.execute(text("SELECT * FROM rea.afectacion_categoria WHERE id_categoria = :id"), {"id": id}).mappings().first()
    return dict(row) if row else None


def create_categoria(db: Session, data: dict) -> int:
    result = db.execute(
        text("INSERT INTO rea.afectacion_categoria (nombre, descripcion, orden) VALUES (:n, :d, :o) RETURNING id_categoria"),
        data,
    )
    db.commit()
    return result.scalar()


def update_categoria(db: Session, id: int, data: dict) -> dict | None:
    set_parts, params = _build_set_clause(data, CAT_COLS)
    if not set_parts:
        return get_categoria(db, id)
    params["id_categoria"] = id
    db.execute(text(f"UPDATE rea.afectacion_categoria SET {', '.join(set_parts)} WHERE id_categoria = :id_categoria"), params)
    db.commit()
    return get_categoria(db, id)


def delete_categoria(db: Session, id: int) -> bool:
    result = db.execute(text("DELETE FROM rea.afectacion_categoria WHERE id_categoria = :id"), {"id": id})
    db.commit()
    return result.rowcount > 0
