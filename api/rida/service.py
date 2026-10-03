"""Servicio de empadronamiento RIDA (esquema rida).

CRUD, scope geográfico y sync offline-first de las tablas de empadronamiento:
formulario_rida, familia, integrante, ubicacion_familia y catálogos asociados.
Sigue el mismo estilo que api/edan/service.py (SQL crudo con text()).
"""

from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from .geo_filters import validar_geografia_jerarquica, agregar_filtros_geo
from ..edan.service import (
    scope_geografico,
    _validar_geo,
    validar_scope_edan as _validar_geo_edan,
    ROLES_DEPARTAMENTAL,
    ROLES_MUNICIPAL,
    ROLES_PROPIOS,
)

# ============================================================================
#  HELPERS
# ============================================================================

def listar_edan_aprobados(db: Session, user: dict, f: dict | None = None,
                          skip: int = 0, limit: int = 50, todos: bool = False):
    """Lista EDAN aprobados (estado 3 ó 5) con filtros geográficos jerárquicos."""
    f = f or {}
    
    # Validar y normalizar filtros geográficos
    try:
        geo_filtros = validar_geografia_jerarquica(
            f.get("id_departamento"), f.get("id_provincia"), f.get("id_municipio")
        )
    except HTTPException:
        raise
    
    conds = ["e.id_estado IN (3, 5)"]
    params = {}
    
    if f.get("id_edan"):
        conds.append("e.id_edan = :id_edan")
        params["id_edan"] = f["id_edan"]
    
    # Aplicar filtros geográficos validados
    if geo_filtros.get("id_departamento"):
        conds.append("e.id_departamento = :id_departamento")
        params["id_departamento"] = geo_filtros["id_departamento"]
    if geo_filtros.get("id_provincia"):
        conds.append("e.id_provincia = :id_provincia")
        params["id_provincia"] = geo_filtros["id_provincia"]
    if geo_filtros.get("id_municipio"):
        conds.append("e.id_municipio = :id_municipio")
        params["id_municipio"] = geo_filtros["id_municipio"]
    
    # Scope geográfico del usuario
    rol = user.get("id_rol")
    if rol in ROLES_PROPIOS:
        if user.get("id_municipio"):
            conds.append("e.id_municipio = :id_municipio")
            params["id_municipio"] = user["id_municipio"]
        elif user.get("id_departamento"):
            conds.append("e.id_departamento = :id_departamento")
            params["id_departamento"] = user["id_departamento"]
    else:
        scope = scope_geografico(user)
        if "id_municipio" in scope:
            conds.append("e.id_municipio = :id_municipio")
            params["id_municipio"] = scope["id_municipio"]
        elif "id_departamento" in scope:
            conds.append("e.id_departamento = :id_departamento")
            params["id_departamento"] = scope["id_departamento"]
    
    where = " AND ".join(conds)
    
    total = db.execute(text(f"SELECT COUNT(*) FROM edan.edan e WHERE {where}"), params).scalar() or 0
    page_sql, page_params = _page_clause(skip, limit, todos)
    params |= page_params
    
    rows = _rows(
        db,
        f"""SELECT e.id_edan, e.codigo_edan, e.id_departamento, e.id_provincia, e.id_municipio,
                   e.id_tipo_evento, e.id_estado,
                   e.fecha_evento, e.hora_evento, e.fecha_creacion,
                   e.total_poblacion_afectada, e.total_familias_afectadas,
                   d.nombre as departamento_nombre,
                   p.nombre as provincia_nombre,
                   m.nombre as municipio_nombre,
                   te.nombre as tipo_evento_nombre,
                   ev.id_evento_rida,
                   (ev.id_evento_rida IS NOT NULL AND ev.anulado = false) AS rida_habilitado,
                   (ev.id_evento_rida IS NULL OR ev.anulado = true) AS puede_habilitar,
                   ce.codigo AS evento_estado_codigo,
                   ce.nombre AS evento_estado_nombre,
                   ev.fecha_habilitacion, ev.fecha_cierre
            FROM edan.edan e
            LEFT JOIN shared.departamento d ON d.id = e.id_departamento
            LEFT JOIN shared.provincia p ON p.id = e.id_provincia
            LEFT JOIN shared.municipio m ON m.id = e.id_municipio
            LEFT JOIN edan.tipo_evento te ON te.id_tipo_evento = e.id_tipo_evento
            LEFT JOIN rida.evento_rida ev ON ev.id_edan = e.id_edan
            LEFT JOIN rida.cat_estado_evento ce ON ce.id_estado_evento = ev.id_estado
            WHERE {where}
            ORDER BY (ev.id_evento_rida IS NOT NULL AND ev.anulado = false) DESC,
                     e.fecha_creacion DESC, e.id_edan DESC
            {page_sql}""",
        params,
    )
    return [dict(r) for r in rows], total


def _rows(db: Session, query: str, params: dict) -> list:
    return db.execute(text(query), params).mappings().all()


def _row(db: Session, query: str, params: dict):
    return db.execute(text(query), params).mappings().first()


def _parse_fecha(fecha: str | None):
    if not fecha:
        return None
    try:
        dt = datetime.fromisoformat(str(fecha).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _page_clause(skip: int = 0, limit: int = 50, todos: bool = False) -> tuple[str, dict]:
    """Cláusula LIMIT/OFFSET. Si `todos=True` devuelve todo sin paginar."""
    if todos:
        return "", {}
    return " LIMIT :limit OFFSET :skip", {"limit": limit, "skip": skip}


FORMULARIO_FROM = """
FROM rida.formulario_rida f
LEFT JOIN edan.edan_localidades el ON el.id_edan_localidad = f.id_edan_localidad
LEFT JOIN shared.municipio m ON m.id = el.id_municipio
LEFT JOIN shared.departamento d ON d.id = el.id_departamento
LEFT JOIN edan.edan e ON e.id_edan = f.id_edan
LEFT JOIN rida.cat_estado_formulario ef ON ef.id_estado_formulario = f.id_estado
"""

SQL_FORMULARIO = """
SELECT f.id_formulario, f.id_edan_localidad, f.id_edan, f.id_usuario,
       f.id_estado, f.id_evento_rida, f.fecha_creacion, f.fecha_modificacion,
       el.localidad AS localidad_nombre, el.id_municipio, el.id_departamento,
       el.imp_poblacion, el.imp_salud, el.imp_infraestructura, el.imp_servicios,
       el.imp_educacion, el.imp_vivienda, el.imp_agropecuario, el.imp_proteccion,
       el.imp_necesidades, el.imp_impacto_poblacion, el.imp_salud_establecimientos,
       el.imp_danos_viales, el.imp_danos_infra_publica, el.imp_servicios_basicos,
       el.imp_unidades_educativas, el.imp_danos_vivienda, el.imp_danos_agricultura,
       el.imp_danos_pecuarios, el.imp_infra_productiva, el.imp_primera_respuesta,
       el.imp_necesidad_salud, el.imp_necesidad_humanitaria,
       m.nombre AS municipio_nombre, d.nombre AS departamento_nombre,
       e.codigo_edan, e.id_estado AS edan_id_estado,
       ev.id_estado AS evento_id_estado,
       ce.codigo AS evento_codigo, ce.nombre AS evento_nombre,
       ef.codigo AS estado_codigo, ef.nombre AS estado_nombre,
       (SELECT COUNT(*) FROM rida.familia fa
         WHERE fa.id_formulario = f.id_formulario) AS n_familias,
       (SELECT COUNT(*) FROM rida.familia fa
          JOIN rida.integrante i ON i.id_familia = fa.id_familia
         WHERE fa.id_formulario = f.id_formulario) AS n_integrantes,
       (SELECT COUNT(*) FROM rida.necesidad n
         WHERE n.id_formulario = f.id_formulario) AS n_necesidades
""" + FORMULARIO_FROM + """
LEFT JOIN rida.evento_rida ev ON ev.id_evento_rida = f.id_evento_rida
LEFT JOIN rida.cat_estado_evento ce ON ce.id_estado_evento = ev.id_estado
"""


def _geo_conds(scope: dict, alias: str = "el") -> tuple[list, dict]:
    conds, params = [], {}
    if "id_municipio" in scope:
        conds.append(f"{alias}.id_municipio = :id_municipio")
        params["id_municipio"] = scope["id_municipio"]
    elif "id_departamento" in scope:
        conds.append(f"{alias}.id_departamento = :id_departamento")
        params["id_departamento"] = scope["id_departamento"]
    return conds, params


def _formulario_geo(db: Session, id_formulario: int):
    return _row(
        db,
        """SELECT el.id_departamento, el.id_municipio
           FROM rida.formulario_rida f
           LEFT JOIN edan.edan_localidades el
               ON el.id_edan_localidad = f.id_edan_localidad
           WHERE f.id_formulario = :id_formulario""",
        {"id_formulario": id_formulario},
    )


def _validar_scope_formulario(db: Session, user: dict, id_formulario: int) -> None:
    """Para roles 5/8/9 restringe el acceso al departamento/municipio del formulario."""
    geo = _formulario_geo(db, id_formulario)
    if not geo:
        raise HTTPException(status_code=404, detail="Formulario no encontrado")
    _validar_geo(db, user, geo["id_departamento"], geo["id_municipio"])


def _validar_scope_familia(db: Session, user: dict, id_familia: int):
    row = _row(
        db,
        """SELECT f.id_formulario FROM rida.familia f WHERE f.id_familia = :id""",
        {"id": id_familia},
    )
    if not row:
        raise HTTPException(status_code=404, detail="Familia no encontrada")
    _validar_scope_formulario(db, user, row["id_formulario"])
    return row["id_formulario"]


def _validar_scope_integrante(db: Session, user: dict, id_integrante: int):
    row = _row(
        db,
        """SELECT i.id_familia FROM rida.integrante i WHERE i.id_integrante = :id""",
        {"id": id_integrante},
    )
    if not row:
        raise HTTPException(status_code=404, detail="Integrante no encontrado")
    _validar_scope_familia(db, user, row["id_familia"])


def _validar_scope_ubicacion(db: Session, user: dict, id_ubicacion: int):
    row = _row(
        db,
        """SELECT u.id_familia FROM rida.ubicacion_familia u
           WHERE u.id_ubicacion_familia = :id""",
        {"id": id_ubicacion},
    )
    if not row:
        raise HTTPException(status_code=404, detail="Ubicación no encontrada")
    _validar_scope_familia(db, user, row["id_familia"])


# ============================================================================
#  FORMULARIO RIDA
# ============================================================================

def listar_formularios(db: Session, user: dict, f: dict | None = None,
                       skip: int = 0, limit: int = 50, todos: bool = False):
    """Lista formularios con filtros geográficos jerárquicos."""
    f = f or {}
    
    # Validar y normalizar filtros geográficos
    geo_filtros = validar_geografia_jerarquica(
        f.get("id_departamento"), f.get("id_provincia"), f.get("id_municipio")
    )
    
    conds, params = [], {}
    if f.get("id_edan"):
        conds.append("f.id_edan = :id_edan")
        params["id_edan"] = f["id_edan"]
    if f.get("id_edan_localidad"):
        conds.append("f.id_edan_localidad = :id_edan_localidad")
        params["id_edan_localidad"] = f["id_edan_localidad"]
    if f.get("id_estado"):
        conds.append("f.id_estado = :id_estado")
        params["id_estado"] = f["id_estado"]
    if f.get("id_usuario"):
        conds.append("f.id_usuario = :id_usuario")
        params["id_usuario"] = f["id_usuario"]
    
    # Aplicar filtros geográficos validados
    conds, params = agregar_filtros_geo(conds, params, "el", geo_filtros)

    rol = user.get("id_rol")
    if rol in ROLES_PROPIOS:
        conds.append("f.id_usuario = :uid")
        params["uid"] = user["id_usuario"]
    else:
        gconds, gparams = _geo_conds(scope_geografico(user))
        conds += gconds
        params |= gparams

    where = " WHERE " + " AND ".join(conds) if conds else ""
    page_sql, page_params = _page_clause(skip, limit, todos)
    params |= page_params
    total = db.execute(text("SELECT COUNT(*)" + FORMULARIO_FROM + where), params).scalar()
    rows = _rows(
        db,
        SQL_FORMULARIO + where + " ORDER BY f.fecha_creacion DESC, f.id_formulario DESC" + page_sql,
        params,
    )
    return [dict(r) for r in rows], total


def get_formulario(db: Session, id_formulario: int) -> dict | None:
    row = _row(db, SQL_FORMULARIO + " WHERE f.id_formulario = :id_formulario",
               {"id_formulario": id_formulario})
    if not row:
        return None
    data = dict(row)
    data["familias"] = list_familias(db, id_formulario)
    return data


def crear_formulario(db: Session, data: dict, uid: int) -> dict:
    """Crea un formulario de empadronamiento para una localidad (1:1).

    Regla de negocio: el EDAN debe estar aprobado (estado 3 ó 5) antes de
    empadronar. El id_edan_localidad es UNIQUE (un solo formulario por localidad).
    """
    id_localidad = data.get("id_edan_localidad")
    if not id_localidad:
        raise HTTPException(status_code=422, detail="id_edan_localidad es obligatorio")
    loc = _row(
        db,
        "SELECT id_edan_localidad, id_edan FROM edan.edan_localidades WHERE id_edan_localidad = :id",
        {"id": id_localidad},
    )
    if not loc:
        raise HTTPException(status_code=400, detail="La localidad no existe")

    id_edan = data.get("id_edan") or loc["id_edan"]
    if id_edan:
        edan = _row(
            db, "SELECT id_edan, id_estado FROM edan.edan WHERE id_edan = :id", {"id": int(id_edan)}
        )
        if not edan:
            raise HTTPException(status_code=400, detail="El EDAN no existe")
        if edan["id_estado"] not in (3, 5):
            raise HTTPException(
                status_code=400,
                detail=f"El EDAN no está aprobado (estado {edan['id_estado']}). "
                       "El empadronamiento requiere EDAN aprobado.",
            )

    existe = _row(
        db,
        "SELECT 1 FROM rida.formulario_rida WHERE id_edan_localidad = :id",
        {"id": id_localidad},
    )
    if existe:
        raise HTTPException(status_code=400, detail="La localidad ya tiene un formulario de empadronamiento")

    est = data.get("id_estado") or 1
    result = _row(
        db,
        """INSERT INTO rida.formulario_rida (id_edan_localidad, id_edan, id_usuario, id_estado)
           VALUES (:id_localidad, :id_edan, :uid, :estado)
           RETURNING id_formulario""",
        {"id_localidad": id_localidad, "id_edan": id_edan,
         "uid": uid, "estado": est},
    )
    db.commit()
    return get_formulario(db, result["id_formulario"])


def actualizar_formulario(db: Session, id_formulario: int, data: dict) -> dict | None:
    row = _row(db, "SELECT id_edan_localidad FROM rida.formulario_rida WHERE id_formulario = :id",
               {"id": id_formulario})
    if not row:
        return None

    fields, params = [], {"id": id_formulario}
    if "id_edan" in data and data["id_edan"] is not None:
        edan = _row(db, "SELECT id_edan, id_estado FROM edan.edan WHERE id_edan = :id",
                    {"id": int(data["id_edan"])})
        if not edan:
            raise HTTPException(status_code=400, detail="El EDAN no existe")
        if edan["id_estado"] not in (3, 5):
            raise HTTPException(status_code=400, detail="El EDAN no está aprobado")
        fields.append("id_edan = :id_edan")
        params["id_edan"] = int(data["id_edan"])
    if "id_estado" in data and data["id_estado"] is not None:
        fields.append("id_estado = :id_estado")
        params["id_estado"] = data["id_estado"]
    if fields:
        db.execute(text(f"UPDATE rida.formulario_rida SET {', '.join(fields)}, fecha_modificacion = NOW() WHERE id_formulario = :id"),
                   params)
        db.commit()
    return get_formulario(db, id_formulario)


def eliminar_formulario(db: Session, id_formulario: int, user: dict) -> bool:
    rol = user.get("id_rol")
    row = _row(db, "SELECT id_usuario FROM rida.formulario_rida WHERE id_formulario = :id",
               {"id": id_formulario})
    if not row:
        return False
    if rol not in (1, 2) and (rol not in ROLES_PROPIOS or row["id_usuario"] != user["id_usuario"]):
        raise HTTPException(status_code=403, detail="Solo puede eliminar sus propios formularios (o admin)")

    fams = _rows(db, "SELECT id_familia FROM rida.familia WHERE id_formulario = :id",
                 {"id": id_formulario})
    for fam in fams:
        _eliminar_familia_interno(db, fam["id_familia"])
    db.execute(text("DELETE FROM rida.formulario_rida WHERE id_formulario = :id"), {"id": id_formulario})
    db.commit()
    return True


def mis_formularios(db: Session, user: dict, f: dict | None = None,
                    skip: int = 0, limit: int = 50, todos: bool = False):
    """Resumen: 6/7 → propios; 8 → municipio (forzado); 5/9 → depto (forzado);
    1-4 → todo el país (honra filtros de geo/query)."""
    f = f or {}
    
    # Validar y normalizar filtros geográficos
    geo_filtros = validar_geografia_jerarquica(
        f.get("id_departamento"), f.get("id_provincia"), f.get("id_municipio")
    )
    
    conds, params = [], {}
    if f.get("id_edan"):
        conds.append("f.id_edan = :id_edan")
        params["id_edan"] = f["id_edan"]
    if f.get("id_edan_localidad"):
        conds.append("f.id_edan_localidad = :id_edan_localidad")
        params["id_edan_localidad"] = f["id_edan_localidad"]
    if f.get("id_estado"):
        conds.append("f.id_estado = :id_estado")
        params["id_estado"] = f["id_estado"]

    rol = user.get("id_rol")
    if rol in ROLES_PROPIOS:
        conds.append("f.id_usuario = :uid")
        params["uid"] = user["id_usuario"]
    elif rol in ROLES_DEPARTAMENTAL + ROLES_MUNICIPAL:
        gconds, gparams = _geo_conds(scope_geografico(user))
        conds += gconds
        params |= gparams
    elif f.get("id_usuario"):
        conds.append("f.id_usuario = :id_usuario")
        params["id_usuario"] = f["id_usuario"]
    
    # Aplicar filtros geográficos validados
    conds, params = agregar_filtros_geo(conds, params, "el", geo_filtros)

    where = " WHERE " + " AND ".join(conds) if conds else ""
    page_sql, page_params = _page_clause(skip, limit, todos)
    params |= page_params
    total = db.execute(text("SELECT COUNT(*)" + FORMULARIO_FROM + where), params).scalar()
    rows = _rows(
        db,
        SQL_FORMULARIO + where + " ORDER BY f.fecha_creacion DESC, f.id_formulario DESC" + page_sql,
        params,
    )
    return [dict(r) for r in rows], total


# ============================================================================
#  FAMILIA
# ============================================================================

SQL_FAMILIA = """
SELECT fa.id_familia, fa.id_familia_off, fa.id_formulario, fa.id_edan_localidad,
       fa.id_ubicacion_familia, fa.id_necesidad, fa.observacion,
       fa.fecha_creacion, fa.fecha_modificacion,
       el.localidad AS localidad_nombre,
       el.id_municipio, el.id_departamento
FROM rida.familia fa
LEFT JOIN edan.edan_localidades el ON el.id_edan_localidad = fa.id_edan_localidad
"""


def list_familias(db: Session, id_formulario: int) -> list:
    rows = _rows(
        db,
        SQL_FAMILIA + " WHERE fa.id_formulario = :id_formulario ORDER BY fa.id_familia",
        {"id_formulario": id_formulario},
    )
    return [_familia_compuesta(db, dict(r)) for r in rows]


def list_familias_paginado(db: Session, id_formulario: int,
                           geo_filtros: dict | None = None,
                           skip: int = 0, limit: int = 50, todos: bool = False):
    geo_filtros = geo_filtros or {}
    conds = ["fa.id_formulario = :id_formulario"]
    params = {"id_formulario": id_formulario}
    
    # Aplicar filtros geográficos vía localidad
    if geo_filtros.get("id_municipio"):
        conds.append("el.id_municipio = :id_municipio")
        params["id_municipio"] = geo_filtros["id_municipio"]
    if geo_filtros.get("id_provincia"):
        conds.append("el.id_provincia = :id_provincia")
        params["id_provincia"] = geo_filtros["id_provincia"]
    if geo_filtros.get("id_departamento"):
        conds.append("el.id_departamento = :id_departamento")
        params["id_departamento"] = geo_filtros["id_departamento"]
    
    where = " AND ".join(conds)
    
    total = db.execute(
        text(f"SELECT COUNT(*) FROM rida.familia fa JOIN edan.edan_localidades el ON el.id_edan_localidad = fa.id_edan_localidad WHERE {where}"),
        params,
    ).scalar() or 0
    
    page_sql, page_params = _page_clause(skip, limit, todos)
    params |= page_params
    
    rows = _rows(
        db,
        SQL_FAMILIA + " JOIN edan.edan_localidades el ON el.id_edan_localidad = fa.id_edan_localidad WHERE " + where + " ORDER BY fa.id_familia" + page_sql,
        params,
    )
    return [_familia_compuesta(db, dict(r)) for r in rows], total


def _familia_compuesta(db: Session, fam: dict) -> dict:
    fam["integrantes"] = list_integrantes(db, fam["id_familia"])
    fam["ubicaciones"] = list_ubicaciones(db, fam["id_familia"])
    return fam


def get_familia(db: Session, id_familia: int) -> dict | None:
    row = _row(db, SQL_FAMILIA + " WHERE fa.id_familia = :id", {"id": id_familia})
    if not row:
        return None
    return _familia_compuesta(db, dict(row))


def _validar_familia_data(db: Session, data: dict) -> None:
    if data.get("id_formulario"):
        if not _row(db, "SELECT 1 FROM rida.formulario_rida WHERE id_formulario = :id",
                    {"id": data["id_formulario"]}):
            raise HTTPException(status_code=400, detail="El formulario no existe")
    if data.get("id_edan_localidad"):
        if not _row(db, "SELECT 1 FROM edan.edan_localidades WHERE id_edan_localidad = :id",
                    {"id": data["id_edan_localidad"]}):
            raise HTTPException(status_code=400, detail="La localidad no existe")
    if data.get("id_necesidad"):
        if not _row(db, "SELECT 1 FROM rida.necesidad WHERE id_necesidad = :id",
                    {"id": data["id_necesidad"]}):
            raise HTTPException(status_code=400, detail="La necesidad no existe")


def crear_familia(db: Session, data: dict, uid: int) -> dict:
    """Crea una familia (UPSERT por id_familia_off si llega una existente)."""
    if not data.get("id_formulario"):
        raise HTTPException(status_code=422, detail="id_formulario es obligatorio")
    _validar_familia_data(db, data)

    off = data.get("id_familia_off")
    if off:
        existing = _row(db, "SELECT id_familia FROM rida.familia WHERE id_familia_off = :off",
                        {"off": off})
        if existing:
            return actualizar_familia(db, existing["id_familia"], data)

    cols = ["id_familia_off", "id_formulario", "id_edan_localidad",
            "id_necesidad", "observacion"]
    present = [k for k in cols if data.get(k) is not None]
    if not present:
        present = ["id_formulario"]
    result = _row(
        db,
        f"INSERT INTO rida.familia ({', '.join(present)}) "
        f"VALUES ({', '.join(':' + k for k in present)}) RETURNING id_familia",
        {k: data[k] for k in present},
    )
    id_familia = result["id_familia"]
    db.commit()

    if off:
        db.execute(text("UPDATE rida.familia SET id_familia_off = :off WHERE id_familia = :id"),
                   {"off": off, "id": id_familia})
        db.commit()
    return get_familia(db, id_familia)


def actualizar_familia(db: Session, id_familia: int, data: dict) -> dict | None:
    row = _row(db, "SELECT id_formulario FROM rida.familia WHERE id_familia = :id", {"id": id_familia})
    if not row:
        return None
    _validar_familia_data(db, data)

    cols = ["id_familia_off", "id_formulario", "id_edan_localidad",
            "id_necesidad", "observacion"]
    fields = [k for k in cols if data.get(k) is not None and k != "id_familia"]
    if not fields:
        return get_familia(db, id_familia)
    set_clause = ", ".join(f"{k} = :{k}" for k in fields) + ", fecha_modificacion = NOW()"
    params = {k: data[k] for k in fields} | {"id": id_familia}
    db.execute(text(f"UPDATE rida.familia SET {set_clause} WHERE id_familia = :id"), params)
    db.commit()
    return get_familia(db, id_familia)


def _eliminar_familia_interno(db: Session, id_familia: int) -> None:
    db.execute(text("UPDATE rida.familia SET id_ubicacion_familia = NULL WHERE id_familia = :id"),
               {"id": id_familia})
    db.execute(text("DELETE FROM rida.ubicacion_familia WHERE id_familia = :id"), {"id": id_familia})
    db.execute(text("DELETE FROM rida.integrante WHERE id_familia = :id"), {"id": id_familia})
    db.execute(text("DELETE FROM rida.familia WHERE id_familia = :id"), {"id": id_familia})


def eliminar_familia(db: Session, id_familia: int) -> bool:
    if not _row(db, "SELECT 1 FROM rida.familia WHERE id_familia = :id", {"id": id_familia}):
        return False
    _eliminar_familia_interno(db, id_familia)
    db.commit()
    return True


# ============================================================================
#  INTEGRANTE
# ============================================================================

SQL_INTEGRANTE = """
SELECT i.id_integrante, i.id_familia, i.id_integrante_off, i.sexo,
       i.fecha_nacimiento, i.numero_documento, i.tipo_documento,
       i.id_parentesco, i.es_jefe, i.gestante_semanas, i.lactante_meses,
       i.id_discapacidad, i.id_enfermedad, i.telefono, i.nombre, i.apellido,
       i.fecha_creacion, i.fecha_modificacion,
       p.nombre AS parentesco_nombre,
       d.nombre AS discapacidad_nombre,
       e.nombre AS enfermedad_nombre
FROM rida.integrante i
LEFT JOIN rida.cat_parentesco p ON p.id_parentesco = i.id_parentesco
LEFT JOIN rida.cat_tipo_discapacidad d ON d.id_discapacidad = i.id_discapacidad
LEFT JOIN rida.cat_enfermedad_cronica e ON e.id_enfermedad = i.id_enfermedad
"""


def list_integrantes(db: Session, id_familia: int) -> list:
    rows = _rows(db, SQL_INTEGRANTE + " WHERE i.id_familia = :id_familia ORDER BY i.es_jefe DESC, i.id_integrante",
                 {"id_familia": id_familia})
    return [dict(r) for r in rows]


def list_integrantes_paginado(db: Session, id_familia: int,
                              skip: int = 0, limit: int = 50, todos: bool = False):
    total = db.execute(
        text("SELECT COUNT(*) FROM rida.integrante i WHERE i.id_familia = :id_familia"),
        {"id_familia": id_familia}).scalar() or 0
    page_sql, page_params = _page_clause(skip, limit, todos)
    params = {"id_familia": id_familia} | page_params
    rows = _rows(
        db,
        SQL_INTEGRANTE + " WHERE i.id_familia = :id_familia ORDER BY i.es_jefe DESC, i.id_integrante" + page_sql,
        params,
    )
    return [dict(r) for r in rows], total


def get_integrante(db: Session, id_integrante: int) -> dict | None:
    row = _row(db, SQL_INTEGRANTE + " WHERE i.id_integrante = :id", {"id": id_integrante})
    return dict(row) if row else None


def _validar_integrante(db: Session, data: dict, id_integrante: int | None = None) -> None:
    if data.get("sexo"):
        data["sexo"] = str(data["sexo"]).upper()[:1]
        if data["sexo"] not in ("M", "F"):
            raise HTTPException(status_code=422, detail="sexo debe ser 'M' o 'F'")
    if data.get("gestante_semanas") is not None and not (0 <= data["gestante_semanas"] <= 45):
        raise HTTPException(status_code=422, detail="gestante_semanas debe estar entre 0 y 45")
    if data.get("lactante_meses") is not None and not (0 <= data["lactante_meses"] <= 36):
        raise HTTPException(status_code=422, detail="lactante_meses debe estar entre 0 y 36")
    if data.get("id_parentesco") and not _row(
            db, "SELECT 1 FROM rida.cat_parentesco WHERE id_parentesco = :id",
            {"id": data["id_parentesco"]}):
        raise HTTPException(status_code=400, detail="Parentesco no válido")
    if data.get("id_discapacidad") and not _row(
            db, "SELECT 1 FROM rida.cat_tipo_discapacidad WHERE id_discapacidad = :id",
            {"id": data["id_discapacidad"]}):
        raise HTTPException(status_code=400, detail="Discapacidad no válida")
    if data.get("id_enfermedad") and not _row(
            db, "SELECT 1 FROM rida.cat_enfermedad_cronica WHERE id_enfermedad = :id",
            {"id": data["id_enfermedad"]}):
        raise HTTPException(status_code=400, detail="Enfermedad crónica no válida")
    
    # Validar duplicados: tipo_documento + numero_documento + nombre + apellido + fecha_nacimiento
    if data.get("tipo_documento") and data.get("nombre") and data.get("fecha_nacimiento"):
        params = {
            "tipo_documento": data["tipo_documento"].upper() if data.get("tipo_documento") else "CARNET",
            "numero_documento": (data.get("numero_documento") or "").strip().upper(),
            "nombre": data["nombre"].strip().lower(),
            "apellido": data.get("apellido", "").strip().lower(),
            "fecha_nacimiento": data["fecha_nacimiento"],
        }
        exclude = f"AND id_integrante <> {id_integrante}" if id_integrante else ""
        existe = _row(
            db, f"""SELECT 1 FROM rida.integrante 
                    WHERE tipo_documento = :tipo_documento
                    AND COALESCE(NULLIF(TRIM(numero_documento), ''), '') = :numero_documento
                    AND LOWER(TRIM(nombre)) = :nombre
                    AND LOWER(TRIM(apellido)) = :apellido
                    AND COALESCE(fecha_nacimiento, '1900-01-01'::date) = :fecha_nacimiento
                    {exclude}""",
            params
        )
        if existe:
            raise HTTPException(
                status_code=400,
                detail=f"Ya existe una persona registrada con {params['tipo_documento']} {params['numero_documento']}, "
                       f"nombre {data['nombre']} {data.get('apellido', '')}, fecha nacimiento {params['fecha_nacimiento']}"
            )


def _unico_jefe(db: Session, id_familia: int, id_integrante: int | None) -> None:
    """Si el integrante es jefe, quita el flag de jefe a los demás de la familia."""
    db.execute(
        text("UPDATE rida.integrante SET es_jefe = FALSE "
             "WHERE id_familia = :id_familia AND es_jefe = TRUE "
             "AND (:id_integrante IS NULL OR id_integrante <> :id_integrante)"),
        {"id_familia": id_familia, "id_integrante": id_integrante},
    )


def crear_integrante(db: Session, data: dict) -> dict:
    """Crea un integrante (UPSERT por id_integrante_off si llega uno existente)."""
    if not data.get("id_familia"):
        raise HTTPException(status_code=422, detail="id_familia es obligatorio")
    if not _row(db, "SELECT 1 FROM rida.familia WHERE id_familia = :id", {"id": data["id_familia"]}):
        raise HTTPException(status_code=400, detail="La familia no existe")
    _validar_integrante(db, data, id_integrante=None)
    
    # Normalizar tipo_documento
    if data.get("tipo_documento"):
        data["tipo_documento"] = data["tipo_documento"].upper()
    else:
        data["tipo_documento"] = "CARNET"
    
    # Mapear numero_ci antiguo a numero_documento si existe
    if data.get("numero_ci") and not data.get("numero_documento"):
        data["numero_documento"] = data["numero_ci"]

    off = data.get("id_integrante_off")
    if off:
        existing = _row(db, "SELECT id_integrante FROM rida.integrante WHERE id_integrante_off = :off",
                        {"off": off})
        if existing:
            return actualizar_integrante(db, existing["id_integrante"], data)

    cols = ["id_familia", "id_integrante_off", "sexo", "fecha_nacimiento", "numero_documento",
            "tipo_documento", "id_parentesco", "es_jefe", "gestante_semanas", "lactante_meses",
            "id_discapacidad", "id_enfermedad", "telefono", "nombre", "apellido"]
    present = [k for k in cols if data.get(k) is not None]
    if not present:
        present = ["id_familia", "nombre", "apellido"]
    result = _row(
        db,
        f"INSERT INTO rida.integrante ({', '.join(present)}, "
        f"fecha_creacion) VALUES ({', '.join(':' + k for k in present)}, NOW()) RETURNING id_integrante",
        {k: data[k] for k in present},
    )
    id_integrante = result["id_integrante"]
    if data.get("es_jefe"):
        _unico_jefe(db, data["id_familia"], id_integrante)
    db.commit()
    return get_integrante(db, id_integrante)


def actualizar_integrante(db: Session, id_integrante: int, data: dict) -> dict | None:
    row = _row(db, "SELECT id_familia FROM rida.integrante WHERE id_integrante = :id",
               {"id": id_integrante})
    if not row:
        return None
    _validar_integrante(db, data, id_integrante=id_integrante)
    data.setdefault("id_familia", row["id_familia"])
    
    # Normalizar tipo_documento si se actualiza
    if data.get("tipo_documento"):
        data["tipo_documento"] = data["tipo_documento"].upper()
    
    # Mapear numero_ci antiguo a numero_documento
    if data.get("numero_ci") and not data.get("numero_documento"):
        data["numero_documento"] = data["numero_ci"]

    cols = ["id_integrante_off", "sexo", "fecha_nacimiento", "numero_documento", "tipo_documento",
            "id_parentesco", "es_jefe", "gestante_semanas", "lactante_meses", "id_discapacidad",
            "id_enfermedad", "telefono", "nombre", "apellido"]
    fields = [k for k in cols if data.get(k) is not None]
    if not fields:
        return get_integrante(db, id_integrante)
    set_clause = ", ".join(f"{k} = :{k}" for k in fields) + ", fecha_modificacion = NOW()"
    params = {k: data[k] for k in fields} | {"id": id_integrante}
    db.execute(text(f"UPDATE rida.integrante SET {set_clause} WHERE id_integrante = :id"), params)
    if data.get("es_jefe"):
        _unico_jefe(db, row["id_familia"], id_integrante)
    db.commit()
    return get_integrante(db, id_integrante)


def eliminar_integrante(db: Session, id_integrante: int) -> bool:
    result = db.execute(text("DELETE FROM rida.integrante WHERE id_integrante = :id"),
                        {"id": id_integrante})
    db.commit()
    return result.rowcount > 0


# ============================================================================
#  UBICACIÓN FAMILIA
# ============================================================================

SQL_UBICACION = """
SELECT u.id_ubicacion_familia, u.id_ubicacion_off, u.coordenada_lat,
       u.coordenada_lon, u.id_familia, u.id_cat_tipo_albergue,
       u.fecha_creacion, u.fecha_modificacion,
       ta.nombre AS tipo_albergue_nombre
FROM rida.ubicacion_familia u
LEFT JOIN rida.cat_tipo_albergue ta
    ON ta.id_cat_tipo_albergue = u.id_cat_tipo_albergue
"""


def list_ubicaciones(db: Session, id_familia: int) -> list:
    rows = _rows(db, SQL_UBICACION + " WHERE u.id_familia = :id_familia ORDER BY u.id_ubicacion_familia",
                 {"id_familia": id_familia})
    return [dict(r) for r in rows]


def list_ubicaciones_paginado(db: Session, id_familia: int,
                              skip: int = 0, limit: int = 50, todos: bool = False):
    total = db.execute(
        text("SELECT COUNT(*) FROM rida.ubicacion_familia u WHERE u.id_familia = :id_familia"),
        {"id_familia": id_familia}).scalar() or 0
    page_sql, page_params = _page_clause(skip, limit, todos)
    params = {"id_familia": id_familia} | page_params
    rows = _rows(
        db,
        SQL_UBICACION + " WHERE u.id_familia = :id_familia ORDER BY u.id_ubicacion_familia" + page_sql,
        params,
    )
    return [dict(r) for r in rows], total


def get_ubicacion(db: Session, id_ubicacion: int) -> dict | None:
    row = _row(db, SQL_UBICACION + " WHERE u.id_ubicacion_familia = :id", {"id": id_ubicacion})
    return dict(row) if row else None


def _validar_ubicacion(db: Session, data: dict) -> None:
    lat, lon = data.get("coordenada_lat"), data.get("coordenada_lon")
    if lat is not None and not (-90 <= lat <= 90):
        raise HTTPException(status_code=422, detail="coordenada_lat debe estar entre -90 y 90")
    if lon is not None and not (-180 <= lon <= 180):
        raise HTTPException(status_code=422, detail="coordenada_lon debe estar entre -180 y 180")
    if data.get("id_cat_tipo_albergue") and not _row(
            db, "SELECT 1 FROM rida.cat_tipo_albergue WHERE id_cat_tipo_albergue = :id",
            {"id": data["id_cat_tipo_albergue"]}):
        raise HTTPException(status_code=400, detail="Tipo de albergue no válido")


def crear_ubicacion(db: Session, data: dict) -> dict:
    """Crea la ubicación GPS de una familia (UPSERT por id_ubicacion_off)."""
    if not data.get("id_familia"):
        raise HTTPException(status_code=422, detail="id_familia es obligatorio")
    if not _row(db, "SELECT 1 FROM rida.familia WHERE id_familia = :id", {"id": data["id_familia"]}):
        raise HTTPException(status_code=400, detail="La familia no existe")
    _validar_ubicacion(db, data)

    off = data.get("id_ubicacion_off")
    if off:
        existing = _row(db, "SELECT id_ubicacion_familia FROM rida.ubicacion_familia WHERE id_ubicacion_off = :off",
                        {"off": off})
        if existing:
            return actualizar_ubicacion(db, existing["id_ubicacion_familia"], data)

    cols = ["id_ubicacion_off", "coordenada_lat", "coordenada_lon",
            "id_familia", "id_cat_tipo_albergue"]
    present = [k for k in cols if data.get(k) is not None]
    if not present:
        present = ["id_familia"]
    result = _row(
        db,
        f"INSERT INTO rida.ubicacion_familia ({', '.join(present)}) "
        f"VALUES ({', '.join(':' + k for k in present)}) RETURNING id_ubicacion_familia",
        {k: data[k] for k in present},
    )
    id_ubicacion = result["id_ubicacion_familia"]
    # Enlace opcional: la familia puede apuntar a su ubicación principal.
    db.execute(
        text("UPDATE rida.familia SET id_ubicacion_familia = :id_ubicacion "
             "WHERE id_familia = :id_familia AND id_ubicacion_familia IS NULL"),
        {"id_ubicacion": id_ubicacion, "id_familia": data["id_familia"]},
    )
    db.commit()
    return get_ubicacion(db, id_ubicacion)


def actualizar_ubicacion(db: Session, id_ubicacion: int, data: dict) -> dict | None:
    row = _row(db, "SELECT id_familia FROM rida.ubicacion_familia WHERE id_ubicacion_familia = :id",
               {"id": id_ubicacion})
    if not row:
        return None
    _validar_ubicacion(db, data)
    data.setdefault("id_familia", row["id_familia"])

    cols = ["id_ubicacion_off", "coordenada_lat", "coordenada_lon",
            "id_cat_tipo_albergue"]
    fields = [k for k in cols if data.get(k) is not None]
    if not fields:
        return get_ubicacion(db, id_ubicacion)
    set_clause = ", ".join(f"{k} = :{k}" for k in fields) + ", fecha_modificacion = NOW()"
    params = {k: data[k] for k in fields} | {"id": id_ubicacion}
    db.execute(text(f"UPDATE rida.ubicacion_familia SET {set_clause} WHERE id_ubicacion_familia = :id"),
               params)
    db.commit()
    return get_ubicacion(db, id_ubicacion)


def eliminar_ubicacion(db: Session, id_ubicacion: int) -> bool:
    row = _row(db, "SELECT id_familia FROM rida.ubicacion_familia WHERE id_ubicacion_familia = :id",
               {"id": id_ubicacion})
    if not row:
        return False
    db.execute(text("UPDATE rida.familia SET id_ubicacion_familia = NULL WHERE id_ubicacion_familia = :id"),
               {"id": id_ubicacion})
    result = db.execute(text("DELETE FROM rida.ubicacion_familia WHERE id_ubicacion_familia = :id"),
                        {"id": id_ubicacion})
    db.commit()
    return result.rowcount > 0


# ============================================================================
#  CATÁLOGOS (lectura)
# ============================================================================

def catalogo_albergues(db: Session):
    rows = _rows(db, "SELECT id_cat_tipo_albergue, nombre FROM rida.cat_tipo_albergue "
                     "ORDER BY nombre, id_cat_tipo_albergue", {})
    return [dict(r) for r in rows]


def catalogo_estados_formulario(db: Session):
    rows = _rows(db, "SELECT id_estado_formulario, codigo, nombre, descripcion, orden, activo "
                     "FROM rida.cat_estado_formulario ORDER BY orden, id_estado_formulario", {})
    return [dict(r) for r in rows]


def catalogo_parentescos(db: Session):
    rows = _rows(db, "SELECT id_parentesco, codigo, nombre, activo FROM rida.cat_parentesco "
                     "WHERE activo = TRUE ORDER BY id_parentesco", {})
    return [dict(r) for r in rows]


def catalogo_discapacidades(db: Session):
    rows = _rows(db, "SELECT id_discapacidad, codigo, nombre, requiere_movilidad, activo "
                     "FROM rida.cat_tipo_discapacidad WHERE activo = TRUE ORDER BY id_discapacidad", {})
    return [dict(r) for r in rows]


# ============================================================================
#  SYNC OFFLINE (batch, por id_*_off)
# ============================================================================

def sync_formulario(db: Session, data: dict, uid: int) -> dict:
    """Upsert de formulario por id_edan_localidad (identificador offline único)."""
    id_localidad = data.get("id_edan_localidad")
    if not id_localidad:
        raise HTTPException(status_code=422, detail="id_edan_localidad es obligatorio")
    existing = _row(db, "SELECT id_formulario FROM rida.formulario_rida WHERE id_edan_localidad = :id",
                    {"id": id_localidad})
    if existing:
        detalle = actualizar_formulario(db, existing["id_formulario"], data)
        return {"id_edan_localidad": id_localidad,
                "id_formulario": existing["id_formulario"], "aplicado": True, "data": detalle}
    detalle = crear_formulario(db, data, uid)
    return {"id_edan_localidad": id_localidad,
            "id_formulario": detalle["id_formulario"], "aplicado": True, "data": detalle}


def sync_familia(db: Session, data: dict, uid: int) -> dict:
    """Upsert de familia por id_familia_off. Si solo llega id_edan_localidad,
    resuelve el id_formulario del empadronamiento de esa localidad."""
    fam = dict(data)
    if not fam.get("id_formulario") and fam.get("id_edan_localidad"):
        f = _row(db, "SELECT id_formulario FROM rida.formulario_rida WHERE id_edan_localidad = :id",
                 {"id": fam["id_edan_localidad"]})
        if f:
            fam["id_formulario"] = f["id_formulario"]
    if not fam.get("id_formulario"):
        raise HTTPException(status_code=422,
                            detail="No se pudo resolver id_formulario (falta empadronar la localidad)")
    detalle = crear_familia(db, fam, uid)
    return {"id_familia_off": fam.get("id_familia_off"),
            "id_familia": detalle["id_familia"], "aplicado": True, "data": detalle}


def sync_integrante(db: Session, data: dict) -> dict:
    """Upsert de integrante por id_integrante_off. id_familia se resuelve
    por id_familia_off cuando el cliente manda ese vínculo offline."""
    intg = dict(data)
    if not intg.get("id_familia") and intg.get("id_familia_off"):
        fam = _row(db, "SELECT id_familia FROM rida.familia WHERE id_familia_off = :off",
                   {"off": intg["id_familia_off"]})
        if fam:
            intg["id_familia"] = fam["id_familia"]
    if not intg.get("id_familia"):
        raise HTTPException(status_code=422, detail="No se pudo resolver id_familia")
    detalle = crear_integrante(db, intg)
    return {"id_integrante_off": intg.get("id_integrante_off"),
            "id_integrante": detalle["id_integrante"], "aplicado": True, "data": detalle}


def sync_ubicacion(db: Session, data: dict) -> dict:
    """Upsert de ubicación por id_ubicacion_off. id_familia se resuelve
    por id_familia_off cuando el cliente manda ese vínculo offline."""
    ubi = dict(data)
    if not ubi.get("id_familia") and ubi.get("id_familia_off"):
        fam = _row(db, "SELECT id_familia FROM rida.familia WHERE id_familia_off = :off",
                   {"off": ubi["id_familia_off"]})
        if fam:
            ubi["id_familia"] = fam["id_familia"]
    if not ubi.get("id_familia"):
        raise HTTPException(status_code=422, detail="No se pudo resolver id_familia")
    detalle = crear_ubicacion(db, ubi)
    return {"id_ubicacion_off": ubi.get("id_ubicacion_off"),
            "id_ubicacion_familia": detalle["id_ubicacion_familia"], "aplicado": True, "data": detalle}


def sync_empadronamiento(db: Session, payload: dict, uid: int) -> dict:
    """Push batch del empadronamiento. El lote nunca falla completo: cada ítem
    se procesa por separado y los errores se recogen en la lista `errores`."""
    out = {"formularios": [], "familias": [], "integrantes": [],
           "ubicaciones": [], "errores": []}

    for f in payload.get("formularios") or []:
        try:
            out["formularios"].append(sync_formulario(db, f, uid))
        except HTTPException as e:
            out["errores"].append({"tipo": "formulario", "id": f.get("id_edan_localidad"),
                                   "aplicado": False, "detalle": e.detail})

    for f in payload.get("familias") or []:
        try:
            out["familias"].append(sync_familia(db, f, uid))
        except HTTPException as e:
            out["errores"].append({"tipo": "familia", "id": f.get("id_familia_off"),
                                   "aplicado": False, "detalle": e.detail})

    for i in payload.get("integrantes") or []:
        try:
            out["integrantes"].append(sync_integrante(db, i))
        except HTTPException as e:
            out["errores"].append({"tipo": "integrante", "id": i.get("id_integrante_off"),
                                   "aplicado": False, "detalle": e.detail})

    for u in payload.get("ubicaciones") or []:
        try:
            out["ubicaciones"].append(sync_ubicacion(db, u))
        except HTTPException as e:
            out["errores"].append({"tipo": "ubicacion", "id": u.get("id_ubicacion_off"),
                                   "aplicado": False, "detalle": e.detail})

    return out


# ============================================================================
#  EVENTO RIDA (PADRE) - jerarquía padre/hijo
#
#  La tabla rida.evento_rida es el PADRE (1:1 con edan.edan aprobado) y SOLO
#  guarda ids (id_edan, id_estado, id_usuario). Los nodos desglosables
#  (tipo de evento, geografía, alcalde/UGR, localidades) se resuelven aquí
#  vía JOIN contra el EDAN (patrón id-empotente).
#
#  Los HIJO son los formularios rida.formulario_rida (uno por localidad del
#  EDAN). Habilitar auto-crea los hijos listos (estado PENDIENTE) para luego
#  empadronar familias manualmente.
# ============================================================================

SQL_EVENTO = """
SELECT ev.id_evento_rida, ev.id_edan, ev.id_estado,
       ev.id_usuario_habilito, ev.fecha_habilitacion,
       ev.id_usuario_cierro, ev.fecha_cierre,
       ev.fecha_creacion, ev.fecha_modificacion,
       ce.codigo AS estado_codigo, ce.nombre AS estado_nombre,
       e.codigo_edan, e.fecha_evento, e.hora_evento,
       e.id_tipo_evento, te.nombre AS tipo_evento_nombre,
       e.id_departamento, d.nombre AS departamento_nombre,
       e.id_provincia, p.nombre AS provincia_nombre,
       e.id_municipio, m.nombre AS municipio_nombre,
       e.id_usuario_alcalde, ua.nombre AS usuario_alcalde_nombre,
       e.id_usuario_ugr, uu.nombre AS usuario_ugr_nombre
FROM rida.evento_rida ev
LEFT JOIN rida.cat_estado_evento ce ON ce.id_estado_evento = ev.id_estado
LEFT JOIN edan.edan e ON e.id_edan = ev.id_edan
LEFT JOIN edan.tipo_evento te ON te.id_tipo_evento = e.id_tipo_evento
LEFT JOIN shared.departamento d ON d.id = e.id_departamento
LEFT JOIN shared.provincia p ON p.id = e.id_provincia
LEFT JOIN shared.municipio m ON m.id = e.id_municipio
LEFT JOIN usuarios.usuario ua ON ua.id_usuario = e.id_usuario_alcalde
LEFT JOIN usuarios.usuario uu ON uu.id_usuario = e.id_usuario_ugr
"""

SQL_LOCALIDAD_EVENTO = """
SELECT f.id_formulario, f.id_edan_localidad, f.id_edan, f.id_usuario,
       f.id_estado, f.id_evento_rida, f.fecha_creacion, f.fecha_modificacion,
       el.localidad AS localidad, el.id_departamento, el.id_municipio,
       d.nombre AS departamento_nombre, m.nombre AS municipio_nombre,
       ef.codigo AS estado_codigo, ef.nombre AS estado_nombre,
       fa.count AS n_familias,
       (SELECT COUNT(*) FROM rida.integrante i
          JOIN rida.familia f2 ON f2.id_familia = i.id_familia
         WHERE f2.id_formulario = f.id_formulario) AS n_integrantes,
       (SELECT COUNT(*) FROM rida.necesidad n
         WHERE n.id_formulario = f.id_formulario) AS n_necesidades
FROM rida.evento_rida ev
JOIN edan.edan_localidades el ON el.id_edan = ev.id_edan
LEFT JOIN rida.formulario_rida f ON f.id_edan_localidad = el.id_edan_localidad
LEFT JOIN shared.departamento d ON d.id = el.id_departamento
LEFT JOIN shared.municipio m ON m.id = el.id_municipio
LEFT JOIN rida.cat_estado_formulario ef ON ef.id_estado_formulario = f.id_estado
LEFT JOIN LATERAL (
    SELECT COUNT(*) AS count FROM rida.familia fa
    WHERE fa.id_formulario = f.id_formulario
) fa ON TRUE
"""


def _evento_geo(db: Session, id_evento_rida: int):
    return _row(
        db,
        """SELECT e.id_departamento, e.id_municipio
           FROM rida.evento_rida ev
           LEFT JOIN edan.edan e ON e.id_edan = ev.id_edan
           WHERE ev.id_evento_rida = :id_evento_rida""",
        {"id_evento_rida": id_evento_rida},
    )


def _validar_scope_evento(db: Session, user: dict, id_evento_rida: int) -> None:
    """Para roles 5/8/9 restringe el evento a su departamento/municipio."""
    geo = _evento_geo(db, id_evento_rida)
    if not geo:
        raise HTTPException(status_code=404, detail="Evento RIDA no encontrado")
    if geo["id_departamento"] is None and geo["id_municipio"] is None:
        return
    _validar_geo(db, user, geo["id_departamento"], geo["id_municipio"])


def _build_evento(row: dict, localidades: list | None = None) -> dict:
    data = dict(row)
    data["estado"] = {
        "id_estado_evento": data["id_estado"],
        "codigo": data.pop("estado_codigo"),
        "nombre": data.pop("estado_nombre"),
    }
    data["tipo_evento"] = (
        {"id_tipo_evento": data["id_tipo_evento"], "nombre": data["tipo_evento_nombre"]}
        if data.get("id_tipo_evento")
        else None
    )
    data.pop("tipo_evento_nombre", None)
    data["departamento"] = (
        {"id": data["id_departamento"], "nombre": data["departamento_nombre"]}
        if data.get("id_departamento")
        else None
    )
    data.pop("departamento_nombre", None)
    data["provincia"] = (
        {"id": data["id_provincia"], "nombre": data["provincia_nombre"]}
        if data.get("id_provincia")
        else None
    )
    data.pop("provincia_nombre", None)
    data["municipio"] = (
        {"id": data["id_municipio"], "nombre": data["municipio_nombre"]}
        if data.get("id_municipio")
        else None
    )
    data.pop("municipio_nombre", None)
    data["usuario_alcalde"] = (
        {"id_usuario": data["id_usuario_alcalde"], "nombre": data["usuario_alcalde_nombre"]}
        if data.get("id_usuario_alcalde")
        else None
    )
    data.pop("usuario_alcalde_nombre", None)
    data["usuario_ugr"] = (
        {"id_usuario": data["id_usuario_ugr"], "nombre": data["usuario_ugr_nombre"]}
        if data.get("id_usuario_ugr")
        else None
    )
    data.pop("usuario_ugr_nombre", None)
    data["localidades"] = localidades or []
    data["num_localidades"] = len(data["localidades"])
    data["n_familias"] = sum((l.get("n_familias") or 0) for l in data["localidades"])
    data["n_integrantes"] = sum((l.get("n_integrantes") or 0) for l in data["localidades"])
    data["n_necesidades"] = sum((l.get("n_necesidades") or 0) for l in data["localidades"])
    for k in ("id_tipo_evento", "id_departamento", "id_provincia", "id_municipio",
              "id_usuario_alcalde", "id_usuario_ugr"):
        data.pop(k, None)
    return data


def listar_eventos(db: Session, user: dict, f: dict | None = None,
                   skip: int = 0, limit: int = 50, todos: bool = False):
    """Lista los eventos RIDA (padres) con desglose del EDAN padre.
    Scope geográfico: roles 6/7 solo sus eventos; 8 su municipio;
    5/9 su departamento; 1-4 todo (honra filtros de geo/query)."""
    f = f or {}
    
    # Validar y normalizar filtros geográficos jerárquicos
    try:
        geo_filtros = validar_geografia_jerarquica(
            f.get("id_departamento"), f.get("id_provincia"), f.get("id_municipio")
        )
    except HTTPException:
        raise
    
    conds, params = [], {}
    if f.get("id_evento_rida"):
        conds.append("ev.id_evento_rida = :id_evento_rida")
        params["id_evento_rida"] = f["id_evento_rida"]
    if f.get("id_edan"):
        conds.append("ev.id_edan = :id_edan")
        params["id_edan"] = f["id_edan"]
    if f.get("id_estado"):
        conds.append("ev.id_estado = :id_estado")
        params["id_estado"] = f["id_estado"]
    
    # Aplicar filtros geográficos validados
    if geo_filtros.get("id_departamento"):
        conds.append("e.id_departamento = :id_departamento")
        params["id_departamento"] = geo_filtros["id_departamento"]
    if geo_filtros.get("id_provincia"):
        conds.append("e.id_provincia = :id_provincia")
        params["id_provincia"] = geo_filtros["id_provincia"]
    if geo_filtros.get("id_municipio"):
        conds.append("e.id_municipio = :id_municipio")
        params["id_municipio"] = geo_filtros["id_municipio"]

    gconds, gparams = [], {}
    rol = user.get("id_rol")
    if rol in ROLES_PROPIOS:
        if user.get("id_municipio"):
            gconds = ["e.id_municipio = :id_municipio"]
            gparams = {"id_municipio": user["id_municipio"]}
        elif user.get("id_departamento"):
            gconds = ["e.id_departamento = :id_departamento"]
            gparams = {"id_departamento": user["id_departamento"]}
    else:
        # roles 5/8/9 el scope se calcula sobre la cabecera del EDAN (alias e)
        scope = scope_geografico(user)
        if "id_municipio" in scope:
            gconds = ["e.id_municipio = :id_municipio"]
            gparams = {"id_municipio": scope["id_municipio"]}
        elif "id_departamento" in scope:
            gconds = ["e.id_departamento = :id_departamento"]
            gparams = {"id_departamento": scope["id_departamento"]}
    conds += gconds
    params |= gparams

    where = " WHERE " + " AND ".join(conds) if conds else ""

    total = db.execute(text("SELECT COUNT(*)" + SQL_EVENTO + where), params).scalar()
    page_sql, page_params = _page_clause(skip, limit, todos)
    params |= page_params
    rows = _rows(
        db,
        SQL_EVENTO + where + " ORDER BY ev.fecha_habilitacion DESC, ev.id_evento_rida DESC" + page_sql,
        params,
    )
    eventos = []
    for r in rows:
        ev = dict(r)
        locs = localidades_evento(db, ev["id_evento_rida"])
        eventos.append(_build_evento(ev, locs))
    return eventos, total


def get_evento(db: Session, id_evento_rida: int) -> dict | None:
    row = _row(db, SQL_EVENTO + " WHERE ev.id_evento_rida = :id_evento_rida",
               {"id_evento_rida": id_evento_rida})
    if not row:
        return None
    return _build_evento(dict(row), localidades_evento(db, id_evento_rida))


def localidades_evento(db: Session, id_evento_rida: int) -> list:
    """HIJO del evento: formularios por localidad del EDAN (desglose de ids)."""
    rows = _rows(
        db,
        SQL_LOCALIDAD_EVENTO,
        {"id_evento_rida": id_evento_rida},
    )
    return [dict(r) for r in rows]


_LOCALIDAD_EVENTO_WHERE = """
WHERE ev.id_evento_rida = :id_evento_rida
"""


def localidades_evento_paginado(db: Session, id_evento_rida: int,
                                geo_filtros: dict | None = None,
                                skip: int = 0, limit: int = 50, todos: bool = False):
    geo_filtros = geo_filtros or {}
    conds = [_LOCALIDAD_EVENTO_WHERE]
    params = {"id_evento_rida": id_evento_rida}
    
    # Aplicar filtros geográficos
    if geo_filtros.get("id_municipio"):
        conds.append("el.id_municipio = :id_municipio")
        params["id_municipio"] = geo_filtros["id_municipio"]
    if geo_filtros.get("id_provincia"):
        conds.append("el.id_provincia = :id_provincia")
        params["id_provincia"] = geo_filtros["id_provincia"]
    if geo_filtros.get("id_departamento"):
        conds.append("el.id_departamento = :id_departamento")
        params["id_departamento"] = geo_filtros["id_departamento"]
    
    where = " AND ".join(conds)
    
    total = db.execute(
        text("SELECT COUNT(*) FROM rida.evento_rida ev JOIN edan.edan_localidades el ON el.id_edan = ev.id_edan WHERE " + where),
        params,
    ).scalar() or 0
    
    page_sql, page_params = _page_clause(skip, limit, todos)
    params |= page_params
    
    rows = _rows(
        db,
        SQL_LOCALIDAD_EVENTO + " WHERE " + where + " ORDER BY el.localidad" + page_sql,
        params,
    )
    return [dict(r) for r in rows], total


def habilitar_evento(db: Session, id_edan: int, uid: int) -> dict:
    """Habilita el RIDA (PADRE) desde un EDAN aprobado y auto-crea los HIJO:
    un formulario por localidad del EDAN (si no existía), quedando listos.
    Solo guarda ids; ninguna copia de datos del EDAN."""
    if not id_edan:
        raise HTTPException(status_code=422, detail="id_edan es obligatorio")
    edan = _row(db, "SELECT id_edan, id_estado FROM edan.edan WHERE id_edan = :id",
                {"id": int(id_edan)})
    if not edan:
        raise HTTPException(status_code=400, detail="El EDAN no existe")
    if edan["id_estado"] not in (3, 5):
        raise HTTPException(
            status_code=400,
            detail=f"El EDAN no está aprobado (estado {edan['id_estado']}). "
                   "El RIDA solo nace del EDAN aprobado.",
        )

    existe = _row(db, "SELECT 1 FROM rida.evento_rida WHERE id_edan = :id_edan",
                  {"id_edan": int(id_edan)})
    if existe:
        raise HTTPException(status_code=400, detail="El EDAN ya tiene un evento RIDA habilitado")

    estado_habilitado = _row(
        db, "SELECT id_estado_evento FROM rida.cat_estado_evento WHERE codigo = 'HABILITADO'", {}
    )
    if not estado_habilitado:
        raise HTTPException(status_code=500, detail="Catálogo estado evento sin HABILITADO")

    result = _row(
        db,
        """INSERT INTO rida.evento_rida (id_edan, id_estado, id_usuario_habilito)
           VALUES (:id_edan, :id_estado, :uid)
           RETURNING id_evento_rida""",
        {"id_edan": int(id_edan), "id_estado": estado_habilitado["id_estado_evento"], "uid": uid},
    )
    id_evento = result["id_evento_rida"]

    locs = _rows(
        db,
        "SELECT id_edan_localidad FROM edan.edan_localidades WHERE id_edan = :id_edan ORDER BY id_edan_localidad",
        {"id_edan": int(id_edan)},
    )
    for loc in locs:
        exists = _row(
            db, "SELECT 1 FROM rida.formulario_rida WHERE id_edan_localidad = :id_loc",
            {"id_loc": loc["id_edan_localidad"]},
        )
        if not exists:
            db.execute(
                text("""INSERT INTO rida.formulario_rida (id_edan_localidad, id_edan, id_usuario, id_estado, id_evento_rida)
                        VALUES (:id_loc, :id_edan, :uid, :id_estado, :id_evento)"""),
                {"id_loc": loc["id_edan_localidad"], "id_edan": int(id_edan), "uid": uid,
                 "id_estado": 1, "id_evento": id_evento},
            )
        else:
            db.execute(
                text("""UPDATE rida.formulario_rida SET id_evento_rida = :id_evento, id_edan = :id_edan
                        WHERE id_edan_localidad = :id_loc AND (id_evento_rida IS NULL OR id_evento_rida <> :id_evento)"""),
                {"id_evento": id_evento, "id_edan": int(id_edan), "id_loc": loc["id_edan_localidad"]},
            )
    db.commit()
    return get_evento(db, id_evento)


def cerrar_evento(db: Session, id_evento_rida: int, uid: int) -> dict:
    """Cierra el evento RIDA (PADRE): marca CERRADO con auditoría quién/cuándo."""
    row = _row(db, "SELECT 1 FROM rida.evento_rida WHERE id_evento_rida = :id",
               {"id": id_evento_rida})
    if not row:
        raise HTTPException(status_code=404, detail="Evento RIDA no encontrado")

    estado_cerrado = _row(
        db, "SELECT id_estado_evento FROM rida.cat_estado_evento WHERE codigo = 'CERRADO'", {}
    )
    if not estado_cerrado:
        raise HTTPException(status_code=500, detail="Catálogo estado evento sin CERRADO")

    db.execute(
        text("""UPDATE rida.evento_rida
                SET id_estado = :id_estado, id_usuario_cierro = :uid,
                    fecha_cierre = NOW(), fecha_modificacion = NOW()
                WHERE id_evento_rida = :id"""),
        {"id_estado": estado_cerrado["id_estado_evento"], "uid": uid, "id": id_evento_rida},
    )
    db.commit()
    return get_evento(db, id_evento_rida)


def anular_evento(db: Session, id_evento_rida: int, uid: int) -> dict:
    """Anula un evento RIDA habilitado por error.
    Solo permite anular eventos HABILITADOS y que NO tengan registros asociados.
    """
    # Verificar que el evento exista y esté habilitado (no anulado, no cerrado)
    row = _row(db, """SELECT 1 FROM rida.evento_rida 
                      WHERE id_evento_rida = :id AND anulado = FALSE AND id_estado = 1""",
               {"id": id_evento_rida})
    if not row:
        raise HTTPException(status_code=400, detail="El evento no puede ser anulado (ya está anulado, cerrado o no existe)")
    
    # Verificar que no haya formularios asociados
    hay_formularios = _row(db, 
        "SELECT 1 FROM rida.formulario_rida WHERE id_evento_rida = :id LIMIT 1",
        {"id": id_evento_rida})
    if hay_formularios:
        raise HTTPException(
            status_code=400, 
            detail="No se puede anular: el evento tiene formularios de empadronamiento asociados. "
                   "Primero elimine todos los formularios y sus datos (familias, integrantes, necesidades)."
        )
    
    # Verificar que no haya localidades del evento con datos (usando la tabla evento_rida directamente)
    # Los hijos se crean al habilitar, así que si hay formulario_rida con id_evento_rida, no se puede anular
    
    db.execute(
        text("""UPDATE rida.evento_rida
                SET anulado = TRUE, id_usuario_anulo = :uid,
                    fecha_anulacion = NOW(),
                    fecha_modificacion = NOW()
                WHERE id_evento_rida = :id"""),
        {"uid": uid, "id": id_evento_rida},
    )
    db.commit()
    return get_evento(db, id_evento_rida)

# ============================================================================
#  BÚSQUEDA DE PERSONAS (INTEGRANTES) - API POTENTE
# ============================================================================

def buscar_personas(db: Session, f: dict | None = None, skip: int = 0, limit: int = 50, todos: bool = False):
    """Búsqueda potente de personas (integrantes) con múltiples criterios:
    - busqueda: texto libre (nombre, apellido, documento)
    - nombre: nombre específico
    - apellido: apellido específico
    - numero_documento: carnet o certificado
    - fecha_nacimiento: fecha exacta
    - id_departamento, id_provincia, id_municipio: ubicación geográfica
    - id_parentesco: filtro por parentesco
    - es_jefe: filtro por jefe de familia
    - sexo: M o F
    """
    f = f or {}
    conds, params = [], {}
    
    # Búsqueda por texto libre (nombre, apellido, documento)
    if f.get("busqueda"):
        texto = f["busqueda"].upper()
        conds.append("""(UPPER(i.nombre) LIKE :busqueda 
                      OR UPPER(i.apellido) LIKE :busqueda 
                      OR UPPER(i.numero_documento) LIKE :busqueda
                      OR UPPER(fa.observacion) LIKE :busqueda)""")
        params["busqueda"] = f"%{texto}%"
    
    if f.get("nombre"):
        conds.append("UPPER(i.nombre) LIKE :nombre")
        params["nombre"] = f"%{f['nombre'].upper()}%"
    
    if f.get("apellido"):
        conds.append("UPPER(i.apellido) LIKE :apellido")
        params["apellido"] = f"%{f['apellido'].upper()}%"
    
    if f.get("numero_documento"):
        conds.append("i.numero_documento = :numero_documento")
        params["numero_documento"] = f["numero_documento"]
    
    if f.get("fecha_nacimiento"):
        conds.append("i.fecha_nacimiento = :fecha_nacimiento")
        params["fecha_nacimiento"] = f["fecha_nacimiento"]
    
    if f.get("id_parentesco"):
        conds.append("i.id_parentesco = :id_parentesco")
        params["id_parentesco"] = f["id_parentesco"]
    
    if f.get("es_jefe") is not None:
        conds.append("i.es_jefe = :es_jefe")
        params["es_jefe"] = f["es_jefe"]
    
    if f.get("sexo") and f["sexo"].upper() in ("M", "F"):
        conds.append("i.sexo = :sexo")
        params["sexo"] = f["sexo"].upper()
    
    # Filtros geográficos a través de la familia -> formulario -> localidad
    if f.get("id_departamento"):
        conds.append("el.id_departamento = :id_departamento")
        params["id_departamento"] = f["id_departamento"]
    
    if f.get("id_municipio"):
        conds.append("el.id_municipio = :id_municipio")
        params["id_municipio"] = f["id_municipio"]
    
    where = " WHERE " + " AND ".join(conds) if conds else " WHERE TRUE"
    
    # Contar total
    total_sql = f"""
        SELECT COUNT(*) FROM rida.integrante i
        JOIN rida.familia fa ON fa.id_familia = i.id_familia
        LEFT JOIN edan.edan_localidades el ON el.id_edan_localidad = fa.id_edan_localidad
        {where}
    """
    total = db.execute(text(total_sql), params).scalar() or 0
    
    # Query principal con joins para obtener datos completos
    page_sql, page_params = _page_clause(skip, limit, todos)
    params |= page_params
    
    sql = f"""
        SELECT i.id_integrante, i.id_familia, i.nombre, i.apellido,
               i.fecha_nacimiento, i.sexo, i.numero_documento, i.tipo_documento,
               i.id_parentesco, p.nombre AS parentesco_nombre,
               i.es_jefe, i.gestante_semanas, i.lactante_meses,
               i.id_discapacidad, d.nombre AS discapacidad_nombre,
               i.id_enfermedad, e.nombre AS enfermedad_nombre,
               i.telefono, i.id_integrante_off,
               i.fecha_creacion, i.fecha_modificacion,
               fa.id_familia_off, fa.observacion AS familia_observacion,
               el.id_edan_localidad, el.localidad AS localidad_nombre,
               el.id_municipio, m.nombre AS municipio_nombre,
               el.id_departamento, dep.nombre AS departamento_nombre
        FROM rida.integrante i
        JOIN rida.familia fa ON fa.id_familia = i.id_familia
        LEFT JOIN edan.edan_localidades el ON el.id_edan_localidad = fa.id_edan_localidad
        LEFT JOIN shared.municipio m ON m.id = el.id_municipio
        LEFT JOIN shared.departamento dep ON dep.id = el.id_departamento
        LEFT JOIN rida.cat_parentesco p ON p.id_parentesco = i.id_parentesco
        LEFT JOIN rida.cat_tipo_discapacidad d ON d.id_discapacidad = i.id_discapacidad
        LEFT JOIN rida.cat_enfermedad_cronica e ON e.id_enfermedad = i.id_enfermedad
        {where}
        ORDER BY i.apellido, i.nombre
        {page_sql}
    """
    
    rows = _rows(db, sql, params)
    return [dict(r) for r in rows], total
