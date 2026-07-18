from sqlalchemy.orm import Session
from sqlalchemy import text
from .schemas import (
    DepartamentoCreate, DepartamentoUpdate,
    ProvinciaCreate, ProvinciaUpdate,
    MunicipioCreate, MunicipioUpdate,
)


# ── DEPARTAMENTOS ──

def get_departamentos(db: Session):
    return db.execute(text("SELECT id, codigo_ine, nombre FROM shared.departamento ORDER BY id")).mappings().all()


def get_departamento(db: Session, id: int):
    return db.execute(
        text("SELECT id, codigo_ine, nombre FROM shared.departamento WHERE id = :id"), {"id": id}
    ).mappings().first()


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

def get_provincias(db: Session, id_departamento: int | None = None):
    if id_departamento:
        return db.execute(
            text("SELECT id, codigo_ine, id_departamento, nombre FROM shared.provincia WHERE id_departamento = :d ORDER BY id"),
            {"d": id_departamento},
        ).mappings().all()
    return db.execute(text("SELECT id, codigo_ine, id_departamento, nombre FROM shared.provincia ORDER BY id")).mappings().all()


def get_provincia(db: Session, id: int):
    return db.execute(
        text("SELECT id, codigo_ine, id_departamento, nombre FROM shared.provincia WHERE id = :id"), {"id": id}
    ).mappings().first()


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

def get_municipios(db: Session, id_provincia: int | None = None, id_departamento: int | None = None):
    if id_provincia:
        return db.execute(
            text("SELECT id, codigo_ine, id_departamento, id_provincia, nombre FROM shared.municipio WHERE id_provincia = :p ORDER BY id"),
            {"p": id_provincia},
        ).mappings().all()
    if id_departamento:
        return db.execute(
            text("SELECT id, codigo_ine, id_departamento, id_provincia, nombre FROM shared.municipio WHERE id_departamento = :d ORDER BY id"),
            {"d": id_departamento},
        ).mappings().all()
    return db.execute(text("SELECT id, codigo_ine, id_departamento, id_provincia, nombre FROM shared.municipio ORDER BY id")).mappings().all()


def get_municipio(db: Session, id: int):
    return db.execute(
        text("SELECT id, codigo_ine, id_departamento, id_provincia, nombre FROM shared.municipio WHERE id = :id"), {"id": id}
    ).mappings().first()


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
