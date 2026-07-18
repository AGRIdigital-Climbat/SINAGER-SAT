from sqlalchemy.orm import Session
from sqlalchemy import text
from .schemas import (
    DepartamentoCreate, DepartamentoUpdate,
    ProvinciaCreate, ProvinciaUpdate,
    MunicipioCreate, MunicipioUpdate,
)


# ── DEPARTAMENTOS ──

def get_departamentos(db: Session):
    rows = db.execute(text("SELECT id, codigo_ine, nombre FROM shared.departamento ORDER BY id")).mappings().all()
    return [dict(r) for r in rows]


def get_departamento(db: Session, id: int):
    row = db.execute(
        text("SELECT id, codigo_ine, nombre FROM shared.departamento WHERE id = :id"), {"id": id}
    ).mappings().first()
    return dict(row) if row else None


def create_departamento(db: Session, data: DepartamentoCreate):
    result = db.execute(
        text("INSERT INTO shared.departamento (codigo_ine, nombre) VALUES (:codigo, :nombre) RETURNING id"),
        {"codigo": data.codigo_ine, "nombre": data.nombre},
    )
    db.commit()
    return result.scalar()


def update_departamento(db: Session, id: int, data: DepartamentoUpdate):
    fields = {}
    if data.codigo_ine is not None:
        fields["codigo_ine"] = data.codigo_ine
    if data.nombre is not None:
        fields["nombre"] = data.nombre
    if not fields:
        return get_departamento(db, id)
    fields["id"] = id
    set_clause = ", ".join(f"{k} = :{k}" for k in fields)
    db.execute(text(f"UPDATE shared.departamento SET {set_clause} WHERE id = :id"), fields)
    db.commit()
    return get_departamento(db, id)


def delete_departamento(db: Session, id: int):
    result = db.execute(text("DELETE FROM shared.departamento WHERE id = :id"), {"id": id})
    db.commit()
    return result.rowcount > 0


# ── PROVINCIAS ──

SQL_PROVINCIA = """
    SELECT p.id, p.codigo_ine, p.id_departamento, p.nombre,
           d.id as d_id, d.codigo_ine as d_codigo_ine, d.nombre as d_nombre
    FROM shared.provincia p
    LEFT JOIN shared.departamento d ON p.id_departamento = d.id
"""


def _build_provincia(row):
    data = dict(row)
    data["departamento"] = {
        "id": data.pop("d_id"),
        "codigo_ine": data.pop("d_codigo_ine"),
        "nombre": data.pop("d_nombre"),
    } if data.get("d_id") else None
    return data


def get_provincias(db: Session, id_departamento: int | None = None):
    if id_departamento:
        rows = db.execute(
            text(f"{SQL_PROVINCIA} WHERE p.id_departamento = :d ORDER BY p.id"),
            {"d": id_departamento},
        ).mappings().all()
    else:
        rows = db.execute(text(f"{SQL_PROVINCIA} ORDER BY p.id")).mappings().all()
    return [_build_provincia(r) for r in rows]


def get_provincia(db: Session, id: int):
    row = db.execute(
        text(f"{SQL_PROVINCIA} WHERE p.id = :id"), {"id": id}
    ).mappings().first()
    return _build_provincia(row) if row else None


def create_provincia(db: Session, data: ProvinciaCreate):
    result = db.execute(
        text("INSERT INTO shared.provincia (codigo_ine, id_departamento, nombre) VALUES (:codigo, :dpto, :nombre) RETURNING id"),
        {"codigo": data.codigo_ine, "dpto": data.id_departamento, "nombre": data.nombre},
    )
    db.commit()
    return result.scalar()


def update_provincia(db: Session, id: int, data: ProvinciaUpdate):
    fields = {}
    if data.codigo_ine is not None:
        fields["codigo_ine"] = data.codigo_ine
    if data.id_departamento is not None:
        fields["id_departamento"] = data.id_departamento
    if data.nombre is not None:
        fields["nombre"] = data.nombre
    if not fields:
        return get_provincia(db, id)
    fields["id"] = id
    set_clause = ", ".join(f"{k} = :{k}" for k in fields)
    db.execute(text(f"UPDATE shared.provincia SET {set_clause} WHERE id = :id"), fields)
    db.commit()
    return get_provincia(db, id)


def delete_provincia(db: Session, id: int):
    result = db.execute(text("DELETE FROM shared.provincia WHERE id = :id"), {"id": id})
    db.commit()
    return result.rowcount > 0


# ── MUNICIPIOS ──

SQL_MUNICIPIO = """
    SELECT m.id, m.codigo_ine, m.id_departamento, m.id_provincia, m.nombre,
           d.id as d_id, d.codigo_ine as d_codigo_ine, d.nombre as d_nombre,
           p.id as p_id, p.codigo_ine as p_codigo_ine, p.nombre as p_nombre
    FROM shared.municipio m
    LEFT JOIN shared.departamento d ON m.id_departamento = d.id
    LEFT JOIN shared.provincia p ON m.id_provincia = p.id
"""


def _build_municipio(row):
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
    return data


def get_municipios(db: Session, id_provincia: int | None = None, id_departamento: int | None = None):
    if id_provincia:
        rows = db.execute(
            text(f"{SQL_MUNICIPIO} WHERE m.id_provincia = :p ORDER BY m.id"),
            {"p": id_provincia},
        ).mappings().all()
    elif id_departamento:
        rows = db.execute(
            text(f"{SQL_MUNICIPIO} WHERE m.id_departamento = :d ORDER BY m.id"),
            {"d": id_departamento},
        ).mappings().all()
    else:
        rows = db.execute(text(f"{SQL_MUNICIPIO} ORDER BY m.id")).mappings().all()
    return [_build_municipio(r) for r in rows]


def get_municipio(db: Session, id: int):
    row = db.execute(
        text(f"{SQL_MUNICIPIO} WHERE m.id = :id"), {"id": id}
    ).mappings().first()
    return _build_municipio(row) if row else None


def create_municipio(db: Session, data: MunicipioCreate):
    result = db.execute(
        text("INSERT INTO shared.municipio (codigo_ine, id_departamento, id_provincia, nombre) VALUES (:codigo, :dpto, :prov, :nombre) RETURNING id"),
        {"codigo": data.codigo_ine, "dpto": data.id_departamento, "prov": data.id_provincia, "nombre": data.nombre},
    )
    db.commit()
    return result.scalar()


def update_municipio(db: Session, id: int, data: MunicipioUpdate):
    fields = {}
    if data.codigo_ine is not None:
        fields["codigo_ine"] = data.codigo_ine
    if data.id_departamento is not None:
        fields["id_departamento"] = data.id_departamento
    if data.id_provincia is not None:
        fields["id_provincia"] = data.id_provincia
    if data.nombre is not None:
        fields["nombre"] = data.nombre
    if not fields:
        return get_municipio(db, id)
    fields["id"] = id
    set_clause = ", ".join(f"{k} = :{k}" for k in fields)
    db.execute(text(f"UPDATE shared.municipio SET {set_clause} WHERE id = :id"), fields)
    db.commit()
    return get_municipio(db, id)


def delete_municipio(db: Session, id: int):
    result = db.execute(text("DELETE FROM shared.municipio WHERE id = :id"), {"id": id})
    db.commit()
    return result.rowcount > 0
