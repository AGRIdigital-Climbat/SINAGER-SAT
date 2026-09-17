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
    next_id = db.execute(text("SELECT COALESCE(MAX(id), 0) + 1 FROM shared.departamento")).scalar()
    result = db.execute(
        text("INSERT INTO shared.departamento (id, codigo_ine, nombre) VALUES (:id, :codigo, :nombre) RETURNING id"),
        {"id": next_id, "codigo": data.codigo_ine, "nombre": data.nombre},
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
    next_id = db.execute(text(
        "SELECT COALESCE(MAX(id), 0) + 1 FROM shared.provincia"
    )).scalar()
    result = db.execute(
        text("INSERT INTO shared.provincia (id, codigo_ine, id_departamento, nombre) VALUES (:id, :codigo, :dpto, :nombre) RETURNING id"),
        {"id": next_id, "codigo": data.codigo_ine, "dpto": data.id_departamento, "nombre": data.nombre},
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
        "id_departamento": data.get("id_departamento"),
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
    next_id = db.execute(text(
        "SELECT COALESCE(MAX(id), 0) + 1 FROM shared.municipio"
    )).scalar()
    result = db.execute(
        text("INSERT INTO shared.municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES (:id, :codigo, :dpto, :prov, :nombre) RETURNING id"),
        {"id": next_id, "codigo": data.codigo_ine, "dpto": data.id_departamento, "prov": data.id_provincia, "nombre": data.nombre},
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


# ── VALIDACIÓN DE GEOGRAFÍA ──

def validar_geografia(db: Session, id_departamento: int | None,
                      id_provincia: int | None, id_municipio: int | None):
    """
    Valida que la combinación departamento → provincia → municipio sea consistente.
    Lanza ValueError con mensaje claro si hay alguna inconsistencia.
    """
    if id_departamento is not None:
        depto = db.execute(
            text("SELECT 1 FROM shared.departamento WHERE id = :id"),
            {"id": id_departamento},
        ).scalar()
        if not depto:
            raise ValueError("El departamento seleccionado no existe")

    if id_provincia is not None:
        if id_departamento is None:
            raise ValueError("Debe seleccionar un departamento para la provincia")
        prov = db.execute(
            text("SELECT id_departamento FROM shared.provincia WHERE id = :id"),
            {"id": id_provincia},
        ).mappings().first()
        if not prov:
            raise ValueError("La provincia seleccionada no existe")
        if prov["id_departamento"] != id_departamento:
            raise ValueError("La provincia seleccionada no pertenece al departamento elegido")

    if id_municipio is not None:
        if id_departamento is None or id_provincia is None:
            raise ValueError("Debe seleccionar departamento y provincia para el municipio")
        mun = db.execute(
            text("SELECT id_provincia, id_departamento FROM shared.municipio WHERE id = :id"),
            {"id": id_municipio},
        ).mappings().first()
        if not mun:
            raise ValueError("El municipio seleccionado no existe")
        if mun["id_provincia"] != id_provincia or mun["id_departamento"] != id_departamento:
            raise ValueError("El municipio seleccionado no pertenece a la provincia o departamento elegidos")


# ── helpers ──

# ── CULTIVOS (catálogo SIIP) ──

def get_cultivos(db: Session, grupo: str | None = None, q: str | None = None):
    sql = "SELECT id, nombre, grupo FROM shared.cultivo"
    where = []
    params = {}
    if grupo:
        where.append("grupo = :grupo")
        params["grupo"] = grupo
    if q:
        where.append("nombre ILIKE :q")
        params["q"] = f"%{q}%"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY id"
    rows = db.execute(text(sql), params).mappings().all()
    return [dict(r) for r in rows]


def get_cultivo(db: Session, id: int):
    row = db.execute(
        text("SELECT id, nombre, grupo FROM shared.cultivo WHERE id = :id"), {"id": id}
    ).mappings().first()
    return dict(row) if row else None


def get_grupos_cultivo(db: Session):
    rows = db.execute(
        text("SELECT grupo FROM shared.cultivo GROUP BY grupo ORDER BY grupo")
    ).mappings().all()
    return [dict(r) for r in rows]


def create_cultivo(db: Session, data):
    next_id = db.execute(text(
        "SELECT COALESCE(MAX(id), 0) + 1 FROM shared.cultivo"
    )).scalar()
    result = db.execute(
        text("INSERT INTO shared.cultivo (id, nombre, grupo) VALUES (:id, :nombre, :grupo) RETURNING id"),
        {"id": next_id, "nombre": data.nombre, "grupo": data.grupo},
    )
    db.commit()
    return get_cultivo(db, result.scalar())


def update_cultivo(db: Session, id: int, data):
    current = get_cultivo(db, id)
    if not current:
        return None
    fields = {"id": id, "nombre": data.nombre if data.nombre is not None else current["nombre"],
              "grupo": data.grupo if data.grupo is not None else current["grupo"]}
    db.execute(
        text("UPDATE shared.cultivo SET nombre = :nombre, grupo = :grupo WHERE id = :id"),
        fields,
    )
    db.commit()
    return get_cultivo(db, id)


def delete_cultivo(db: Session, id: int):
    result = db.execute(
        text("DELETE FROM shared.cultivo WHERE id = :id RETURNING id"), {"id": id}
    ).scalar()
    db.commit()
    return result


# ── PECUARIO (especies animales) ──

def get_pecuario(db: Session, grupo: str | None = None, q: str | None = None):
    sql = "SELECT id, nombre, grupo FROM shared.pecuario"
    where = []
    params = {}
    if grupo:
        where.append("grupo = :grupo")
        params["grupo"] = grupo
    if q:
        where.append("nombre ILIKE :q")
        params["q"] = f"%{q}%"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY id"
    rows = db.execute(text(sql), params).mappings().all()
    return [dict(r) for r in rows]


def get_pecuario_by_id(db: Session, id: int):
    row = db.execute(
        text("SELECT id, nombre, grupo FROM shared.pecuario WHERE id = :id"), {"id": id}
    ).mappings().first()
    return dict(row) if row else None


def get_grupos_pecuario(db: Session):
    rows = db.execute(
        text("SELECT grupo FROM shared.pecuario GROUP BY grupo ORDER BY grupo")
    ).mappings().all()
    return [dict(r) for r in rows]


def create_pecuario(db: Session, data):
    next_id = db.execute(text(
        "SELECT COALESCE(MAX(id), 0) + 1 FROM shared.pecuario"
    )).scalar()
    result = db.execute(
        text("INSERT INTO shared.pecuario (id, nombre, grupo) VALUES (:id, :nombre, :grupo) RETURNING id"),
        {"id": next_id, "nombre": data.nombre, "grupo": data.grupo},
    )
    db.commit()
    return get_pecuario_by_id(db, result.scalar())


def update_pecuario(db: Session, id: int, data):
    current = get_pecuario_by_id(db, id)
    if not current:
        return None
    fields = {"id": id, "nombre": data.nombre if data.nombre is not None else current["nombre"],
              "grupo": data.grupo if data.grupo is not None else current["grupo"]}
    db.execute(
        text("UPDATE shared.pecuario SET nombre = :nombre, grupo = :grupo WHERE id = :id"),
        fields,
    )
    db.commit()
    return get_pecuario_by_id(db, id)


def delete_pecuario(db: Session, id: int):
    result = db.execute(
        text("DELETE FROM shared.pecuario WHERE id = :id RETURNING id"), {"id": id}
    ).scalar()
    db.commit()
    return result
