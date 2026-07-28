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


# ── GEOJSON (RFC 7946) ──

SQL_GEOJSON_FEATURES = """
    SELECT json_build_object(
        'type', 'Feature',
        'geometry', ST_AsGeoJSON(ST_Transform(m.geom, 4326), 6, 0)::json,
        'properties', json_build_object(
            'id', m.id,
            'codigo_ine', m.codigo_ine,
            'nombre', m.nombre,
            'departamento', CASE WHEN d.id IS NOT NULL THEN
                json_build_object('id', d.id, 'codigo_ine', d.codigo_ine, 'nombre', d.nombre)
            ELSE NULL END,
            'provincia', CASE WHEN p.id IS NOT NULL THEN
                json_build_object('id', p.id, 'codigo_ine', p.codigo_ine, 'nombre', p.nombre)
            ELSE NULL END,
            'area_km2', ROUND((ST_Area(m.geom::geography) / 1000000)::numeric, 2)
        ),
        'bbox', json_build_array(
            ST_XMin(ST_Transform(m.geom, 4326)),
            ST_YMin(ST_Transform(m.geom, 4326)),
            ST_XMax(ST_Transform(m.geom, 4326)),
            ST_YMax(ST_Transform(m.geom, 4326))
        )
    ) as feature
    FROM shared.municipio m
    LEFT JOIN shared.departamento d ON m.id_departamento = d.id
    LEFT JOIN shared.provincia p ON m.id_provincia = p.id
"""




def get_municipios_geojson(db: Session, id_provincia: int | None = None, id_departamento: int | None = None):
    where = ""
    params = {}
    if id_provincia:
        where = "WHERE m.id_provincia = :p"
        params["p"] = id_provincia
    elif id_departamento:
        where = "WHERE m.id_departamento = :d"
        params["d"] = id_departamento

    features_query = f"{SQL_GEOJSON_FEATURES} {where} GROUP BY m.id, d.id, p.id ORDER BY m.id"
    rows = db.execute(text(features_query), params).mappings().all()
    features = [dict(r)["feature"] for r in rows]

    return {
        "type": "FeatureCollection",
        "name": "municipios_bolivia",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": features,
        "total": len(features),
    }


def get_municipio_geojson(db: Session, id: int):
    row = db.execute(
        text(f"{SQL_GEOJSON_FEATURES} WHERE m.id = :id GROUP BY m.id, d.id, p.id"),
        {"id": id},
    ).mappings().first()
    if not row:
        return None
    return dict(row)["feature"]


# ── GEOM/WKT ──

SQL_MUNICIPIO_GEOM = """
    SELECT m.id, m.codigo_ine, m.nombre,
           ST_AsText(m.geom) as geom_wkt,
           ST_SRID(m.geom) as srid,
           d.id as d_id, d.codigo_ine as d_codigo_ine, d.nombre as d_nombre,
           p.id as p_id, p.codigo_ine as p_codigo_ine, p.nombre as p_nombre
    FROM shared.municipio m
    LEFT JOIN shared.departamento d ON m.id_departamento = d.id
    LEFT JOIN shared.provincia p ON m.id_provincia = p.id
"""


def _build_municipio_geom(row):
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


def get_municipios_geom(db: Session, id_provincia: int | None = None, id_departamento: int | None = None):
    where = ""
    params = {}
    if id_provincia:
        where = "WHERE m.id_provincia = :p"
        params["p"] = id_provincia
    elif id_departamento:
        where = "WHERE m.id_departamento = :d"
        params["d"] = id_departamento

    rows = db.execute(
        text(f"{SQL_MUNICIPIO_GEOM} {where} ORDER BY m.id"), params
    ).mappings().all()
    return [_build_municipio_geom(r) for r in rows]


def get_municipio_geom(db: Session, id: int):
    row = db.execute(
        text(f"{SQL_MUNICIPIO_GEOM} WHERE m.id = :id"), {"id": id}
    ).mappings().first()
    return _build_municipio_geom(row) if row else None


# ── UBICACIÓN (punto-dentro-de-polígono) ──

def obtener_ubicacion(db: Session, lat: float, lon: float):
    sql = """
        SELECT
            m.id, m.codigo_ine, m.nombre,
            d.id as d_id, d.codigo_ine as d_codigo_ine, d.nombre as d_nombre,
            p.id as p_id, p.codigo_ine as p_codigo_ine, p.nombre as p_nombre
        FROM shared.municipio m
        LEFT JOIN shared.departamento d ON m.id_departamento = d.id
        LEFT JOIN shared.provincia p ON m.id_provincia = p.id
        WHERE ST_Contains(m.geom, ST_SetSRID(ST_Point(:lon, :lat), 4326))
        LIMIT 1
    """
    row = db.execute(text(sql), {"lat": lat, "lon": lon}).mappings().first()
    if not row:
        return None

    data = dict(row)
    municipio = {
        "id": data["id"],
        "codigo_ine": data["codigo_ine"],
        "nombre": data["nombre"],
    }
    departamento = {
        "id": data["d_id"],
        "codigo_ine": data["d_codigo_ine"],
        "nombre": data["d_nombre"],
    } if data.get("d_id") else None
    provincia = {
        "id": data["p_id"],
        "codigo_ine": data["p_codigo_ine"],
        "nombre": data["p_nombre"],
    } if data.get("p_id") else None

    return {
        "lat": lat,
        "lon": lon,
        "municipio": municipio,
        "provincia": provincia,
        "departamento": departamento,
    }


# ── helpers ──
