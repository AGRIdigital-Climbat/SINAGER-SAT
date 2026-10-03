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


# ── CENSO 2024 (shared.manzanos / shared.comunidades) ──

TABLAS_CENSO = ("manzanos", "comunidades")

TABLAS_CENSO = ("manzanos", "comunidades")

# Columnas de datos (codigo_ine, nombre, id_municipio se tratan aparte;
# id_departamento/id_provincia se derivan de la jerarquia geografica)
UNIDAD_CENSO_COLUMNAS = [
    "tipo_unidad", "personas", "viviendas", "lat", "lon", "area_oficial",
]


def _validar_tabla_censo(tabla: str) -> str:
    if tabla not in TABLAS_CENSO:
        raise ValueError("Tabla censo invalida")
    return tabla


def _ids_municipio(db: Session, id_municipio: int):
    """(id_provincia, id_departamento) del municipio, o None si no existe."""
    row = db.execute(
        text("SELECT id_provincia, id_departamento FROM shared.municipio WHERE id = :id"),
        {"id": id_municipio},
    ).mappings().first()
    return (row["id_provincia"], row["id_departamento"]) if row else None


def _sql_unidad_censo(tabla: str) -> str:
    _validar_tabla_censo(tabla)
    return f"""
        SELECT a.codigo_ine, a.nombre, a.tipo_unidad, a.personas, a.viviendas,
               a.lat, a.lon, a.area_oficial, a.id_municipio,
               a.id_departamento, a.id_provincia,
               mu.id as mu_id, mu.codigo_ine as mu_codigo_ine, mu.nombre as mu_nombre
        FROM shared.{tabla} a
        LEFT JOIN shared.municipio mu ON a.id_municipio = mu.id
    """


def _build_unidad_censo(row):
    data = dict(row)
    data["municipio"] = {
        "id": data.pop("mu_id"),
        "codigo_ine": data.pop("mu_codigo_ine"),
        "nombre": data.pop("mu_nombre"),
    } if data.get("mu_id") else None
    return data


def get_unidades_censo(db: Session, tabla: str, id_municipio: int | None = None,
                       codigo_ine: str | None = None, q: str | None = None,
                       area_oficial: str | None = None,
                       limit: int | None = None, offset: int | None = None):
    where = []
    params = {}
    if id_municipio:
        where.append("a.id_municipio = :im")
        params["im"] = id_municipio
    if codigo_ine:
        where.append("a.codigo_ine = :c")
        params["c"] = codigo_ine
    if q:
        where.append("a.nombre ILIKE :q")
        params["q"] = f"%{q}%"
    if area_oficial:
        where.append("a.area_oficial = :ao")
        params["ao"] = area_oficial
    sql = _sql_unidad_censo(tabla)
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY a.codigo_ine"
    if limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = limit
        if offset is not None:
            sql += " OFFSET :offset"
            params["offset"] = offset
    rows = db.execute(text(sql), params).mappings().all()
    return [_build_unidad_censo(r) for r in rows]


def get_unidad_censo(db: Session, tabla: str, codigo_ine: str):
    row = db.execute(
        text(f"{_sql_unidad_censo(tabla)} WHERE a.codigo_ine = :c"), {"c": codigo_ine}
    ).mappings().first()
    return _build_unidad_censo(row) if row else None


def create_unidad_censo(db: Session, tabla: str, data):
    _validar_tabla_censo(tabla)
    ids = _ids_municipio(db, data.id_municipio)
    if not ids:
        raise ValueError("El municipio seleccionado no existe")
    id_provincia, id_departamento = ids

    cols = ["codigo_ine", "nombre", "id_municipio", "id_departamento", "id_provincia"]
    vals = {"codigo_ine": data.codigo_ine, "nombre": data.nombre,
            "id_municipio": data.id_municipio,
            "id_departamento": id_departamento, "id_provincia": id_provincia}
    for c in UNIDAD_CENSO_COLUMNAS:
        v = getattr(data, c, None)
        if v is not None:
            cols.append(c)
            vals[c] = v
    placeholders = ", ".join(f":{c}" for c in cols)
    result = db.execute(
        text(f"INSERT INTO shared.{tabla} ({', '.join(cols)}) "
             f"VALUES ({placeholders}) RETURNING codigo_ine"),
        vals,
    )
    db.commit()
    return result.scalar()


def update_unidad_censo(db: Session, tabla: str, codigo_ine: str, data):
    current = get_unidad_censo(db, tabla, codigo_ine)
    if not current:
        return None

    fields = {}
    if data.nombre is not None:
        fields["nombre"] = data.nombre
    if data.id_municipio is not None:
        ids = _ids_municipio(db, data.id_municipio)
        if not ids:
            raise ValueError("El municipio seleccionado no existe")
        fields["id_municipio"] = data.id_municipio
        fields["id_departamento"] = ids[1]
        fields["id_provincia"] = ids[0]
    for c in UNIDAD_CENSO_COLUMNAS:
        v = getattr(data, c, None)
        if v is not None:
            fields[c] = v
    if not fields:
        return current

    set_clause = ", ".join(f"{k} = :{k}" for k in fields)
    fields["codigo_ine"] = codigo_ine
    db.execute(
        text(f"UPDATE shared.{tabla} SET {set_clause} WHERE codigo_ine = :codigo_ine"),
        fields,
    )
    db.commit()
    return get_unidad_censo(db, tabla, codigo_ine)


def delete_unidad_censo(db: Session, tabla: str, codigo_ine: str):
    result = db.execute(
        text(f"DELETE FROM shared.{tabla} WHERE codigo_ine = :c RETURNING codigo_ine"),
        {"c": codigo_ine},
    ).scalar()
    db.commit()
    return result


# ── CENSO 2024 GeoJSON (RFC 7946, para consultas en mapas) ──

_SQL_GEOJSON_UNIDAD = """
    SELECT json_build_object(
        'type', 'Feature',
        'geometry', ST_AsGeoJSON(a.geom, 6, 0)::json,
        'properties', json_build_object(
            'codigo_ine', a.codigo_ine,
            'nombre', a.nombre,
            'tipo_unidad', a.tipo_unidad,
            'personas', a.personas,
            'viviendas', a.viviendas,
            'area_oficial', a.area_oficial,
            'lat', a.lat,
            'lon', a.lon,
            'id_departamento', a.id_departamento,
            'id_provincia', a.id_provincia,
            'id_municipio', a.id_municipio,
            'municipio', CASE WHEN mu.id IS NOT NULL THEN
                json_build_object('id', mu.id, 'codigo_ine', mu.codigo_ine,
                                  'nombre', mu.nombre)
            ELSE NULL END
        ),
        'bbox', json_build_array(
            ST_XMin(a.geom), ST_YMin(a.geom),
            ST_XMax(a.geom), ST_YMax(a.geom)
        )
    ) as feature
    FROM shared.%(tabla)s a
    LEFT JOIN shared.municipio mu ON a.id_municipio = mu.id
"""


def get_unidades_censo_geojson(db: Session, tabla: str,
                               id_municipio: int | None = None,
                               codigo_ine: str | None = None, q: str | None = None,
                               area_oficial: str | None = None,
                               bbox: str | None = None,
                               limit: int = 5000):
    _validar_tabla_censo(tabla)
    where = ["a.geom IS NOT NULL"]
    params = {}
    if id_municipio:
        where.append("a.id_municipio = :im")
        params["im"] = id_municipio
    if codigo_ine:
        where.append("a.codigo_ine = :c")
        params["c"] = codigo_ine
    if q:
        where.append("a.nombre ILIKE :q")
        params["q"] = f"%{q}%"
    if area_oficial:
        where.append("a.area_oficial = :ao")
        params["ao"] = area_oficial
    if bbox:
        try:
            minx, miny, maxx, maxy = (float(v) for v in bbox.split(","))
        except ValueError:
            raise ValueError(
                "bbox debe ser 'minx,miny,maxx,maxy' (ej: -68.5,-17.6,-68.3,-17.3)")
        if minx >= maxx or miny >= maxy:
            raise ValueError("bbox invalido: min < max en ambos ejes")
        where.append("a.geom && ST_MakeEnvelope(:minx, :miny, :maxx, :maxy, 4326)")
        params.update(minx=minx, miny=miny, maxx=maxx, maxy=maxy)

    params["limit"] = limit
    sql = (f"{_SQL_GEOJSON_UNIDAD % {'tabla': tabla}} "
           f"WHERE {' AND '.join(where)} ORDER BY a.codigo_ine LIMIT :limit")
    rows = db.execute(text(sql), params).mappings().all()
    features = [dict(r)["feature"] for r in rows]

    return {
        "type": "FeatureCollection",
        "name": f"{tabla}_censo2024",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": features,
        "total": len(features),
        "limit": limit,
    }


def get_unidad_censo_geojson(db: Session, tabla: str, codigo_ine: str):
    row = db.execute(
        text(f"{_SQL_GEOJSON_UNIDAD % {'tabla': tabla}} "
             "WHERE a.codigo_ine = :c AND a.geom IS NOT NULL"),
        {"c": codigo_ine},
    ).mappings().first()
    if not row:
        return None
    return dict(row)["feature"]


# ── CENSO 2024: Poblacion y viviendas (resumenes agregados) ──
# Las agregaciones suman manzanos + comunidades (unidades disjuntas del CPV-2024).

_NIVELES_CENSO = {"departamento", "provincia", "municipio"}

_CTE_UNIDADES = """
    WITH m AS (
        SELECT {key} k, count(*) n,
               COALESCE(sum(personas), 0) pers, COALESCE(sum(viviendas), 0) viv
        FROM shared.manzanos
        GROUP BY {key}
    ),
    c AS (
        SELECT {key} k, count(*) n,
               COALESCE(sum(personas), 0) pers, COALESCE(sum(viviendas), 0) viv
        FROM shared.comunidades
        GROUP BY {key}
    )
"""

_SEL_RESUMEN = """
    COALESCE(m.n, 0) manzanos, COALESCE(c.n, 0) comunidades,
    COALESCE(m.n, 0) + COALESCE(c.n, 0) unidades_censales,
    COALESCE(m.pers, 0) + COALESCE(c.pers, 0) poblacion,
    COALESCE(m.viv, 0) + COALESCE(c.viv, 0) viviendas
"""


def resumen_censo_nacional(db: Session) -> dict:
    """Totales del pais: personas, viviendas y conteo de unidades (manz+com)."""
    sql = """
        SELECT
            (SELECT count(*) FROM shared.manzanos) AS manzanos,
            (SELECT count(*) FROM shared.comunidades) AS comunidades,
            (SELECT COALESCE(sum(personas), 0) FROM shared.manzanos) AS personas_m,
            (SELECT COALESCE(sum(personas), 0) FROM shared.comunidades) AS personas_c,
            (SELECT COALESCE(sum(viviendas), 0) FROM shared.manzanos) AS viviendas_m,
            (SELECT COALESCE(sum(viviendas), 0) FROM shared.comunidades) AS viviendas_c
    """
    row = db.execute(text(sql)).mappings().first()
    return {
        "nivel": "nacional",
        "id_departamento": None,
        "id_provincia": None,
        "id_municipio": None,
        "codigo_ine": None,
        "nombre": "Estado Plurinacional de Bolivia",
        "manzanos": row["manzanos"],
        "comunidades": row["comunidades"],
        "unidades_censales": row["manzanos"] + row["comunidades"],
        "poblacion": row["personas_m"] + row["personas_c"],
        "viviendas": row["viviendas_m"] + row["viviendas_c"],
    }


def resumen_censo_por_nivel(db: Session, nivel: str,
                            id_departamento: int | None = None,
                            id_provincia: int | None = None,
                            id_municipio: int | None = None) -> list[dict]:
    """Resumen agregado por departamento / provincia / municipio (con filtros)."""
    if nivel not in _NIVELES_CENSO:
        raise ValueError("nivel invalido (departamento, provincia, municipio)")
    key = {"departamento": "id_departamento",
           "provincia": "id_provincia",
           "municipio": "id_municipio"}[nivel]

    where = []
    params = {}
    col_dep = {"departamento": "g.id", "provincia": "g.id_departamento",
               "municipio": "g.id_departamento"}[nivel]
    col_prov = {"provincia": "g.id", "municipio": "g.id_provincia"}.get(nivel)
    if id_departamento:
        where.append(f"{col_dep} = :id_departamento")
        params["id_departamento"] = id_departamento
    if id_provincia and col_prov:
        where.append(f"{col_prov} = :id_provincia")
        params["id_provincia"] = id_provincia
    if id_municipio:
        where.append("g.id = :id_municipio")
        params["id_municipio"] = id_municipio
    where_sql = (" WHERE " + " AND ".join(where)) if where else ""

    if nivel == "departamento":
        select = """
            SELECT 'departamento' AS nivel, g.id AS id_departamento,
                   NULL AS id_provincia, NULL AS id_municipio,
                   g.codigo_ine, g.nombre,
        """
        from_sql = " FROM shared.departamento g"
    elif nivel == "provincia":
        select = """
            SELECT 'provincia' AS nivel, g.id_departamento,
                   g.id AS id_provincia, NULL AS id_municipio,
                   g.codigo_ine, g.nombre,
        """
        from_sql = " FROM shared.provincia g"
    else:
        select = """
            SELECT 'municipio' AS nivel, g.id_departamento, g.id_provincia,
                   g.id AS id_municipio, g.codigo_ine, g.nombre,
        """
        from_sql = " FROM shared.municipio g"

    sql = f"""
        {_CTE_UNIDADES.format(key=key)}
        {select}
        {_SEL_RESUMEN}
        {from_sql}
        LEFT JOIN m ON m.k = g.id
        LEFT JOIN c ON c.k = g.id
        {where_sql}
        ORDER BY g.id
    """
    rows = db.execute(text(sql), params).mappings().all()
    return [dict(r) for r in rows]


def get_poblacion_unidad(db: Session, tabla: str, codigo_ine: str):
    """Personas y viviendas directamente de un manzano o comunidad."""
    _validar_tabla_censo(tabla)
    row = db.execute(
        text(f"SELECT codigo_ine, tipo_unidad, nombre, "
             f"personas AS poblacion, viviendas "
             f"FROM shared.{tabla} WHERE codigo_ine = :c"),
        {"c": codigo_ine},
    ).mappings().first()
    return dict(row) if row else None
