from sqlalchemy.orm import Session
from sqlalchemy import text


# ── REPORTE EVENTO ──

def get_reportes(db: Session, id_estado: int | None = None, id_municipio: int | None = None, skip: int = 0, limit: int = 50):
    query = "SELECT * FROM rea.reporte_evento"
    params = {}
    conditions = []
    if id_estado:
        conditions.append("id_estado = :estado")
        params["estado"] = id_estado
    if id_municipio:
        conditions.append("id_municipio = :muni")
        params["muni"] = id_municipio
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY id_reporte DESC LIMIT :limit OFFSET :skip"
    params["limit"] = limit
    params["skip"] = skip
    return db.execute(text(query), params).mappings().all()


def get_reporte(db: Session, id: int):
    return db.execute(
        text("SELECT * FROM rea.reporte_evento WHERE id_reporte = :id"), {"id": id}
    ).mappings().first()


def get_reporte_completo(db: Session, id: int):
    reporte = get_reporte(db, id)
    if not reporte:
        return None
    result = dict(reporte)
    cats = db.execute(
        text("SELECT id_categoria FROM rea.reporte_afectacion WHERE id_reporte = :id"), {"id": id}
    ).mappings().all()
    result["categorias"] = [c["id_categoria"] for c in cats]
    return result


def create_reporte(db: Session, data: dict) -> int:
    categorias = data.pop("categorias", None)
    cols = ", ".join(data.keys())
    vals = ", ".join(f":{k}" for k in data.keys())
    result = db.execute(
        text(f"INSERT INTO rea.reporte_evento ({cols}) VALUES ({vals}) RETURNING id_reporte"), data
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


def update_reporte(db: Session, id: int, data: dict) -> dict | None:
    categorias = data.pop("categorias", None)
    fields = {k: v for k, v in data.items() if v is not None}
    if fields:
        fields["id_reporte"] = id
        set_clause = ", ".join(f"{k} = :{k}" for k in fields)
        db.execute(text(f"UPDATE rea.reporte_evento SET {set_clause} WHERE id_reporte = :id_reporte"), fields)
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
    return get_reporte(db, id)


def delete_reporte(db: Session, id: int) -> bool:
    result = db.execute(text("DELETE FROM rea.reporte_evento WHERE id_reporte = :id"), {"id": id})
    db.commit()
    return result.rowcount > 0


# ── ESTADO REPORTE ──

def get_estados(db: Session):
    return db.execute(text("SELECT * FROM rea.estado_reporte ORDER BY orden")).mappings().all()


def get_estado(db: Session, id: int):
    return db.execute(text("SELECT * FROM rea.estado_reporte WHERE id_estado = :id"), {"id": id}).mappings().first()


def create_estado(db: Session, data: dict) -> int:
    result = db.execute(
        text("INSERT INTO rea.estado_reporte (nombre, descripcion, orden) VALUES (:n, :d, :o) RETURNING id_estado"),
        data,
    )
    db.commit()
    return result.scalar()


def update_estado(db: Session, id: int, data: dict) -> dict | None:
    fields = {k: v for k, v in data.items() if v is not None}
    if not fields:
        return get_estado(db, id)
    fields["id_estado"] = id
    set_clause = ", ".join(f"{k} = :{k}" for k in fields)
    db.execute(text(f"UPDATE rea.estado_reporte SET {set_clause} WHERE id_estado = :id_estado"), fields)
    db.commit()
    return get_estado(db, id)


def delete_estado(db: Session, id: int) -> bool:
    result = db.execute(text("DELETE FROM rea.estado_reporte WHERE id_estado = :id"), {"id": id})
    db.commit()
    return result.rowcount > 0


# ── AFFECTACION CATEGORIA ──

def get_categorias(db: Session):
    return db.execute(text("SELECT * FROM rea.afectacion_categoria ORDER BY orden")).mappings().all()


def get_categoria(db: Session, id: int):
    return db.execute(text("SELECT * FROM rea.afectacion_categoria WHERE id_categoria = :id"), {"id": id}).mappings().first()


def create_categoria(db: Session, data: dict) -> int:
    result = db.execute(
        text("INSERT INTO rea.afectacion_categoria (nombre, descripcion, orden) VALUES (:n, :d, :o) RETURNING id_categoria"),
        data,
    )
    db.commit()
    return result.scalar()


def update_categoria(db: Session, id: int, data: dict) -> dict | None:
    fields = {k: v for k, v in data.items() if v is not None}
    if not fields:
        return get_categoria(db, id)
    fields["id_categoria"] = id
    set_clause = ", ".join(f"{k} = :{k}" for k in fields)
    db.execute(text(f"UPDATE rea.afectacion_categoria SET {set_clause} WHERE id_categoria = :id_categoria"), fields)
    db.commit()
    return get_categoria(db, id)


def delete_categoria(db: Session, id: int) -> bool:
    result = db.execute(text("DELETE FROM rea.afectacion_categoria WHERE id_categoria = :id"), {"id": id})
    db.commit()
    return result.rowcount > 0
