"""Servicio de empadronamiento RIDA (esquema rida).

CRUD, scope geográfico y sync offline-first de las tablas de empadronamiento:
formulario_rida, familia, integrante, ubicacion_familia y catálogos asociados.
Sigue el mismo estilo que api/edan/service.py (SQL crudo con text()).
"""

from datetime import date, datetime, timezone
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
                    (ev.id_evento_rida IS NOT NULL) AS rida_habilitado,
                    (ev.id_evento_rida IS NULL) AS puede_habilitar,
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
            ORDER BY (ev.id_evento_rida IS NOT NULL) DESC,
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
LEFT JOIN edan.tipo_localidad tl ON tl.id_tipo_localidad = el.id_tipo_localidad
LEFT JOIN shared.municipio m ON m.id = el.id_municipio
LEFT JOIN shared.departamento d ON d.id = el.id_departamento
LEFT JOIN edan.edan e ON e.id_edan = f.id_edan
LEFT JOIN rida.cat_estado_formulario ef ON ef.id_estado_formulario = f.id_estado
"""

SQL_FORMULARIO = """
SELECT f.id_formulario, f.id_edan_localidad, f.id_edan, f.id_usuario,
       f.id_estado, f.id_evento_rida, f.fecha_creacion, f.fecha_modificacion,
       el.localidad AS localidad_nombre, el.id_municipio, el.id_departamento,
       el.id_tipo_localidad, tl.nombre AS tipo_localidad_nombre,
       el.grup_poblacion AS imp_poblacion, el.grup_salud AS imp_salud,
       el.grup_infraestructura AS imp_infraestructura, el.grup_servicios AS imp_servicios,
       el.grup_educacion AS imp_educacion, el.grup_vivienda AS imp_vivienda,
       el.grup_agropecuario AS imp_agropecuario, el.grup_proteccion AS imp_proteccion,
       el.grup_necesidades AS imp_necesidades, el.imp_impacto_poblacion, el.imp_salud_establecimientos,
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
         JOIN rida.familia fn ON fn.id_familia = n.id_familia
        WHERE fn.id_formulario = f.id_formulario) AS n_necesidades
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
       el.id_tipo_localidad, tl.nombre AS tipo_localidad_nombre,
       el.id_municipio, el.id_departamento
FROM rida.familia fa
LEFT JOIN edan.edan_localidades el ON el.id_edan_localidad = fa.id_edan_localidad
LEFT JOIN edan.tipo_localidad tl ON tl.id_tipo_localidad = el.id_tipo_localidad
"""


def list_familias(db: Session, id_formulario: int) -> list:
    rows = _rows(
        db,
        SQL_FAMILIA + " WHERE fa.id_formulario = :id_formulario ORDER BY fa.id_familia DESC",
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
        text(f"SELECT COUNT(*) FROM rida.familia fa WHERE {where}"),
        params,
    ).scalar() or 0
    
    page_sql, page_params = _page_clause(skip, limit, todos)
    params |= page_params
    
    rows = _rows(
        db,
        SQL_FAMILIA + " WHERE " + where + " ORDER BY fa.id_familia DESC" + page_sql,
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


def _pasar_a_en_proceso_si_habilitado(db: Session, id_formulario: int | None) -> None:
    """Ciclo de vida del evento RIDA: al primer registro de empadronamiento
    (familia, integrante o ubicación) un evento HABILITADO pasa a EN PROCESO.
    Es el ÚNICO cambio de estado automático; ATENDIDO y CERRADO solo los
    cambian sus APIs explícitas."""
    if not id_formulario:
        return
    db.execute(text("""
        UPDATE rida.evento_rida ev
           SET id_estado = (SELECT id_estado_evento FROM rida.cat_estado_evento
                             WHERE codigo = 'EN PROCESO'),
               fecha_modificacion = (NOW() AT TIME ZONE 'America/La_Paz')
         WHERE ev.id_evento_rida = (SELECT id_evento_rida FROM rida.formulario_rida
                                     WHERE id_formulario = :f)
           AND ev.id_estado = (SELECT id_estado_evento FROM rida.cat_estado_evento
                                WHERE codigo = 'HABILITADO')
    """), {"f": id_formulario})


def crear_familia(db: Session, data: dict, uid: int) -> dict:
    """Crea una familia (UPSERT por id_familia_off si llega una existente)."""
    if not data.get("id_formulario"):
        raise HTTPException(status_code=422, detail="id_formulario es obligatorio")
    _validar_familia_data(db, data)

    # Rastreo: si no viene la localidad, se hereda del formulario para que
    # toda familia quede siempre ligada a su id_edan_localidad.
    if data.get("id_edan_localidad") is None:
        frm = _row(db, "SELECT id_edan_localidad FROM rida.formulario_rida WHERE id_formulario = :id",
                   {"id": data["id_formulario"]})
        if frm and frm["id_edan_localidad"] is not None:
            data["id_edan_localidad"] = frm["id_edan_localidad"]

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
    _pasar_a_en_proceso_si_habilitado(db, data["id_formulario"])
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
    fam = _row(db, "SELECT id_formulario FROM rida.familia WHERE id_familia = :id",
               {"id": data["id_familia"]})
    _pasar_a_en_proceso_si_habilitado(db, fam["id_formulario"] if fam else None)
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
    rows = _rows(db, SQL_UBICACION + " WHERE u.id_familia = :id_familia ORDER BY u.id_ubicacion_familia DESC",
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
        SQL_UBICACION + " WHERE u.id_familia = :id_familia ORDER BY u.id_ubicacion_familia DESC" + page_sql,
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
    fam = _row(db, "SELECT id_formulario FROM rida.familia WHERE id_familia = :id",
               {"id": data["id_familia"]})
    _pasar_a_en_proceso_si_habilitado(db, fam["id_formulario"] if fam else None)
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
SELECT ev.id_evento_rida, ev.id_edan, ev.id_estado, ev.codigo,
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
       el.id_tipo_localidad, tl.nombre AS tipo_localidad_nombre,
       d.nombre AS departamento_nombre, m.nombre AS municipio_nombre,
       ef.codigo AS estado_codigo, ef.nombre AS estado_nombre,
       fa.count AS n_familias,
       (SELECT COUNT(*) FROM rida.integrante i
          JOIN rida.familia f2 ON f2.id_familia = i.id_familia
         WHERE f2.id_formulario = f.id_formulario) AS n_integrantes,
       (SELECT COUNT(*) FROM rida.necesidad n
         JOIN rida.familia fn ON fn.id_familia = n.id_familia
        WHERE fn.id_formulario = f.id_formulario) AS n_necesidades
FROM rida.evento_rida ev
JOIN edan.edan_localidades el ON el.id_edan = ev.id_edan
LEFT JOIN rida.formulario_rida f ON f.id_edan_localidad = el.id_edan_localidad
LEFT JOIN edan.tipo_localidad tl ON tl.id_tipo_localidad = el.id_tipo_localidad
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
    if f.get("codigo"):
        conds.append("UPPER(ev.codigo) = UPPER(:codigo)")
        params["codigo"] = f["codigo"]
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

    total = db.execute(
        text(f"SELECT COUNT(*) FROM ({SQL_EVENTO}{where}) _cnt"), params
    ).scalar()
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


# ============================================================================
#  REPORTE DE EVENTO (empadronamiento consolidado)
#  GET /rida/evento/{identificador}/reporte — resumen total + cada formulario
#  con sus 3 secciones: poblacion por grupo etario, capacidades especiales por
#  grupo etario y necesidades por familia. Edades al momento del
#  empadronamiento (fecha_creacion del integrante, fallback la del formulario).
# ============================================================================

# Rangos de edan.grupo_etario (codigo, nombre, orden, min, max). 'sin_fecha' es
# el bucket de fecha_nacimiento NULL o edad invalida (nacimiento futuro).
GRUPOS_ETARIOS_REPORTE = [
    ("ninas_ninos_0_5", "Niño (a) 0-5 años", 1, 0, 5),
    ("escolar_6_18", "Escolar de 6-18 años", 2, 6, 18),
    ("adulto_19_60", "Adulto de 19-60 años", 3, 19, 60),
    ("adulto_mayor_60", "Adulto mayor de 60 años adelante", 4, 61, 150),
    ("sin_fecha", "Sin fecha de nacimiento", 5, None, None),
]

_SQL_LOCALIDADES_REPORTE = """
SELECT el.id_edan_localidad, el.localidad,
       el.id_tipo_localidad,
       tl.nombre AS tipo_localidad_nombre,
       ele.nombre AS estado_localidad_nombre,
       f.id_formulario, f.id_estado, f.fecha_creacion, f.id_usuario,
       ef.codigo AS estado_codigo, ef.nombre AS estado_nombre,
       u.nombre AS usuario_nombre, u.usuario AS usuario_login
FROM rida.evento_rida ev
JOIN edan.edan_localidades el ON el.id_edan = ev.id_edan
LEFT JOIN edan.tipo_localidad tl ON tl.id_tipo_localidad = el.id_tipo_localidad
LEFT JOIN edan.edan_localidades_estado ele
       ON ele.id_edan_localidad_estado = el.id_edan_localidad_estado
LEFT JOIN rida.formulario_rida f ON f.id_edan_localidad = el.id_edan_localidad
LEFT JOIN rida.cat_estado_formulario ef ON ef.id_estado_formulario = f.id_estado
LEFT JOIN usuarios.usuario u ON u.id_usuario = f.id_usuario
WHERE ev.id_evento_rida = :id
ORDER BY el.id_edan_localidad
"""


def resolver_evento(db: Session, identificador) -> int | None:
    """Resuelve un evento por id numerico o por codigo RIDA (exacto, sin
    distinguir mayusculas). Sin coincidencia -> None (404 en el router)."""
    ident = str(identificador or "").strip()
    if not ident:
        return None
    if ident.isdigit():
        row = _row(db, "SELECT id_evento_rida FROM rida.evento_rida "
                       "WHERE id_evento_rida = :i", {"i": int(ident)})
    else:
        row = _row(db, "SELECT id_evento_rida FROM rida.evento_rida "
                       "WHERE UPPER(codigo) = UPPER(:c)", {"c": ident})
    return row["id_evento_rida"] if row else None


def _edad_en(fecha_nac: date | None, ref) -> int | None:
    """Edad completada en la fecha del empadronamiento (`ref`: fecha_creacion
    del integrante/formulario). None si falta la fecha o la edad es negativa."""
    if not fecha_nac:
        return None
    if isinstance(ref, datetime):
        ref = ref.date()
    elif not ref:
        ref = datetime.now(timezone.utc).date()
    edad = ref.year - fecha_nac.year - ((ref.month, ref.day) < (fecha_nac.month, fecha_nac.day))
    return edad if edad >= 0 else None


def _grupo_de(edad: int | None) -> str:
    if edad is None:
        return "sin_fecha"
    for codigo, _n, _o, vmin, vmax in GRUPOS_ETARIOS_REPORTE:
        if vmin is not None and vmin <= edad <= vmax:
            return codigo
    return "sin_fecha"


def _seccion_reporte(integrantes: list, familias: list, necesidades: list,
                     cats: dict) -> dict:
    """Construye las 3 secciones sobre un subconjunto (total evento o un
    formulario). `cats` trae los catalogos ya leidos (discapacidad sin NINGUNA,
    enfermedad y categorias de ayuda)."""
    ints_por_fam: dict[int, int] = {}
    for i in integrantes:
        ints_por_fam[i["id_familia"]] = ints_por_fam.get(i["id_familia"], 0) + 1

    counts = [ints_por_fam.get(f["id_familia"], 0) for f in familias]
    prom = round(sum(counts) / len(counts), 2) if counts else 0.0

    pobl = {c: {"total": 0, "m": 0, "f": 0} for c, *_ in GRUPOS_ETARIOS_REPORTE}
    cap = {c: {"gestantes": 0, "lactantes": 0, "disc": {}, "enf": {}}
           for c, *_ in GRUPOS_ETARIOS_REPORTE}

    for i in integrantes:
        edad = _edad_en(i["fecha_nacimiento"], i["fecha_empadronamiento"])
        g = _grupo_de(edad)
        pobl[g]["total"] += 1
        if i["sexo"] == "M":
            pobl[g]["m"] += 1
        elif i["sexo"] == "F":
            pobl[g]["f"] += 1
        if i.get("gestante_semanas") is not None:
            cap[g]["gestantes"] += 1
        if i.get("lactante_meses") is not None:
            cap[g]["lactantes"] += 1
        if i.get("id_discapacidad") and i["id_discapacidad"] != cats["id_discapacidad_ninguna"]:
            cap[g]["disc"][i["id_discapacidad"]] = cap[g]["disc"].get(i["id_discapacidad"], 0) + 1
        if i.get("id_enfermedad"):
            cap[g]["enf"][i["id_enfermedad"]] = cap[g]["enf"].get(i["id_enfermedad"], 0) + 1

    poblacion = [
        {"grupo": c, "nombre": n, "orden": o, **pobl[c]}
        for c, n, o, *_ in GRUPOS_ETARIOS_REPORTE
    ]

    def _por_tipo(clave_map, catalogo):
        out = []
        for item in catalogo:
            total = clave_map.get(item["id"], 0)
            if total:
                out.append({"id": item["id"], "codigo": item["codigo"],
                            "nombre": item["nombre"], "total": total})
        return out

    capacidades = []
    for c, n, o, *_ in GRUPOS_ETARIOS_REPORTE:
        disc = cap[c]["disc"]
        enf = cap[c]["enf"]
        capacidades.append({
            "grupo": c, "nombre": n, "orden": o,
            "gestantes": cap[c]["gestantes"],
            "lactantes": cap[c]["lactantes"],
            "discapacidad": {"total": sum(disc.values()),
                             "por_tipo": _por_tipo(disc, cats["discapacidad"])},
            "enfermedad": {"total": sum(enf.values()),
                           "por_tipo": _por_tipo(enf, cats["enfermedad"])},
        })

    # Necesidades por familia (solo familias con al menos una) agrupadas por
    # categoria de ayuda — sin costos ni detalle de articulo (regla del reporte).
    por_familia: dict[int, dict] = {}
    for n in necesidades:
        fid = n["id_familia"]
        if fid is None:
            continue
        fam = por_familia.setdefault(fid, {
            "id_familia": fid,
            "id_formulario": n["id_formulario_resuelto"],
            "cats": {},
            "n": 0,
        })
        fam["n"] += 1
        c = fam["cats"].setdefault(n["id_categoria_ayuda"], {"n": 0, "completadas": 0})
        c["n"] += 1
        if n["estado"]:
            c["completadas"] += 1

    cat_by_id = {c["id"]: c for c in cats["categoria"]}
    necesidad_familia = []
    for fid in sorted(por_familia):
        fam = por_familia[fid]
        necesidad_familia.append({
            "id_familia": fid,
            "id_formulario": fam["id_formulario"],
            "integrantes": ints_por_fam.get(fid, 0),
            "n_necesidades": fam["n"],
            "por_categoria": [
                {"id_categoria": cid,
                 "codigo": (cat_by_id.get(cid) or {}).get("codigo"),
                 "nombre": (cat_by_id.get(cid) or {}).get("nombre"),
                 "n_necesidades": v["n"],
                 "completadas": v["completadas"]}
                for cid, v in sorted(fam["cats"].items())
            ],
        })

    total_nec = len(necesidades)
    completadas = sum(1 for n in necesidades if n["estado"])

    return {
        "familias": len(familias),
        "integrantes": len(integrantes),
        "integrantes_por_familia": {
            "promedio": prom,
            "minimo": min(counts) if counts else 0,
            "maximo": max(counts) if counts else 0,
        },
        "poblacion_por_grupo_etario": poblacion,
        "capacidades_especiales_por_grupo_etario": capacidades,
        "necesidades_por_familia": necesidad_familia,
        "necesidades": {
            "total": total_nec,
            "completadas": completadas,
            "pendientes": total_nec - completadas,
        },
    }


def _cabecera_reporte(db: Session, id_evento: int):
    """Bloques `evento` y `edan` del JSON de los reportes del evento
    (compartidos por el reporte de secciones y el listado de integrantes).
    `edan.n_localidades` queda en 0: lo completa cada llamador con su propio
    conteo. Devuelve None si el evento no existe. El scope geografico lo
    aplica cada endpoint aparte."""
    ev = _row(db, SQL_EVENTO + " WHERE ev.id_evento_rida = :id_evento_rida",
              {"id_evento_rida": id_evento})
    if not ev:
        return None
    # _build_evento arma estado/tipo_evento/geografia/usuarios como dicts.
    ev = _build_evento(dict(ev))

    ed = _row(db, """
        SELECT procedencia, fecha_llenado,
               total_poblacion_afectada, total_familias_afectadas,
               total_familias_damnificadas, id_importacion
        FROM edan.edan WHERE id_edan = :id
    """, {"id": ev["id_edan"]}) or {}

    # Quienes levantaron la informacion: creadores de las localidades del EDAN
    # (distinct) + el usuario del log de importacion si el EDAN es importado.
    levantaron: list[dict] = []
    if ev.get("id_edan"):
        for r in _rows(db, """
            SELECT DISTINCT l.id_usuario, u.nombre, u.usuario
            FROM edan.edan_localidades l
            LEFT JOIN usuarios.usuario u ON u.id_usuario = l.id_usuario
            WHERE l.id_edan = :id AND l.id_usuario IS NOT NULL
            ORDER BY l.id_usuario
        """, {"id": ev["id_edan"]}):
            levantaron.append(dict(r))
        if ed.get("id_importacion"):
            imp = _row(db, """
                SELECT il.id_usuario, u.nombre, u.usuario
                FROM edan.edan_importacion_log il
                LEFT JOIN usuarios.usuario u ON u.id_usuario = il.id_usuario
                WHERE il.id_importacion = :imp AND il.id_usuario IS NOT NULL
            """, {"imp": ed["id_importacion"]})
            if imp and imp["id_usuario"] not in {x["id_usuario"] for x in levantaron}:
                levantaron.insert(0, dict(imp))

    def _login(uid):
        if not uid:
            return None
        r = _row(db, "SELECT usuario FROM usuarios.usuario WHERE id_usuario = :i", {"i": uid})
        return r["usuario"] if r else None

    for _k in ("usuario_ugr", "usuario_alcalde"):
        _u = ev.get(_k)
        if _u:
            _u["usuario"] = _login(_u.get("id_usuario"))

    evento_block = {
        "id_evento_rida": ev["id_evento_rida"],
        "codigo": ev["codigo"],
        "estado": ev["estado"],
        "fecha_habilitacion": ev["fecha_habilitacion"],
        "fecha_cierre": ev["fecha_cierre"],
        "fecha_creacion": ev["fecha_creacion"],
    }
    edan_block = {
        "id_edan": ev["id_edan"],
        "codigo_edan": ev["codigo_edan"],
        "procedencia": ed.get("procedencia"),
        "fecha_evento": ev["fecha_evento"],
        "hora_evento": ev["hora_evento"],
        "fecha_llenado": ed.get("fecha_llenado"),
        "tipo_evento": ev["tipo_evento"],
        "departamento": ev["departamento"],
        "provincia": ev["provincia"],
        "municipio": ev["municipio"],
        "levantaron": levantaron,
        "ugr": ev.get("usuario_ugr"),
        "alcalde": ev.get("usuario_alcalde"),
        "poblacion_declarada": {
            "poblacion_afectada": ed.get("total_poblacion_afectada"),
            "familias_afectadas": ed.get("total_familias_afectadas"),
            "familias_damnificadas": ed.get("total_familias_damnificadas"),
        },
        "n_localidades": 0,
    }
    return evento_block, edan_block


def _localidades_reporte(db: Session, id_evento: int) -> list[dict]:
    """Todas las localidades del evento, en orden estable por
    id_edan_localidad: las ligadas al EDAN + los formularios que cuelgan del
    evento sin localidad asociada (caso legado)."""
    localidades = [dict(r) for r in _rows(db, _SQL_LOCALIDADES_REPORTE,
                                          {"id": id_evento})]
    listados = {l["id_formulario"] for l in localidades if l["id_formulario"]}
    evento_forms = {r["id_formulario"] for r in _rows(
        db, "SELECT id_formulario FROM rida.formulario_rida "
            "WHERE id_evento_rida = :id", {"id": id_evento})}
    faltantes = sorted(evento_forms - listados)
    if faltantes:
        in_falt = ",".join(str(int(x)) for x in faltantes)
        localidades += [dict(r) for r in _rows(db, f"""
            SELECT f.id_edan_localidad, NULL AS localidad,
                   NULL AS id_tipo_localidad,
                   NULL AS tipo_localidad_nombre, NULL AS estado_localidad_nombre,
                   f.id_formulario, f.id_estado, f.fecha_creacion, f.id_usuario,
                   ef.codigo AS estado_codigo, ef.nombre AS estado_nombre,
                   u.nombre AS usuario_nombre, u.usuario AS usuario_login
            FROM rida.formulario_rida f
            LEFT JOIN rida.cat_estado_formulario ef
                   ON ef.id_estado_formulario = f.id_estado
            LEFT JOIN usuarios.usuario u ON u.id_usuario = f.id_usuario
            WHERE f.id_formulario IN ({in_falt})
            ORDER BY f.id_formulario
        """, {})]
    return localidades


def get_evento_reporte(db: Session, identificador, user: dict | None = None) -> dict | None:
    """Reporte consolidado del evento: evento + EDAN (con quienes levantaron la
    informacion, UGR y alcalde) + `resumen` total + cada formulario con sus 3
    secciones. `identificador` es id numerico o codigo RIDA; si no existe
    devuelve None. Aplica scope geografico del usuario si se pasa `user`."""
    id_evento = resolver_evento(db, identificador)
    if not id_evento:
        return None
    if user is not None:
        _validar_scope_evento(db, user, id_evento)

    cab = _cabecera_reporte(db, id_evento)
    if not cab:
        return None
    evento_block, edan_block = cab

    # Catalogos (una sola vez para resumen y formularios).
    disc = _rows(db, "SELECT id_discapacidad AS id, codigo, nombre "
                     "FROM rida.cat_tipo_discapacidad WHERE activo ORDER BY id_discapacidad", {})
    disc_ninguna = next((d["id"] for d in disc if d["codigo"] == "NINGUNA"), None)
    cats = {
        "discapacidad": [d for d in disc if d["codigo"] != "NINGUNA"],
        "id_discapacidad_ninguna": disc_ninguna,
        "enfermedad": _rows(db, "SELECT id_enfermedad AS id, codigo, nombre "
                                "FROM rida.cat_enfermedad_cronica WHERE activo "
                                "ORDER BY id_enfermedad", {}),
        "categoria": _rows(db, "SELECT id_categoria_ayuda AS id, codigo, nombre "
                               "FROM rida.cat_categoria_ayuda ORDER BY id_categoria_ayuda", {}),
    }

    # Localidades del EDAN UNION formularios colgando del evento (legado):
    # así suma(formularios) == resumen siempre.
    localidades = _localidades_reporte(db, id_evento)
    form_ids = sorted({l["id_formulario"] for l in localidades if l["id_formulario"]})
    edan_block["n_localidades"] = len(localidades)

    if form_ids:
        in_sql = ",".join(str(int(x)) for x in form_ids)
        integrantes = [dict(r) for r in _rows(db, f"""
            SELECT i.id_integrante, i.id_familia, i.sexo, i.fecha_nacimiento,
                   i.gestante_semanas, i.lactante_meses,
                   i.id_discapacidad, i.id_enfermedad,
                   fa.id_formulario,
                   COALESCE(i.fecha_creacion, fo.fecha_creacion) AS fecha_empadronamiento
            FROM rida.integrante i
            JOIN rida.familia fa ON fa.id_familia = i.id_familia
            JOIN rida.formulario_rida fo ON fo.id_formulario = fa.id_formulario
            WHERE fa.id_formulario IN ({in_sql})
        """, {})]
        familias = [dict(r) for r in _rows(db, f"""
            SELECT fa.id_familia, fa.id_formulario
            FROM rida.familia fa
            WHERE fa.id_formulario IN ({in_sql})
            ORDER BY fa.id_familia
        """, {})]
        necesidades = [dict(r) for r in _rows(db, f"""
            SELECT n.id_familia, n.id_categoria_ayuda, n.estado,
                   fa.id_formulario AS id_formulario_resuelto
            FROM rida.necesidad n
            JOIN rida.familia fa ON fa.id_familia = n.id_familia
            WHERE fa.id_formulario IN ({in_sql})
        """, {})]
    else:
        integrantes, familias, necesidades = [], [], []

    resumen = _seccion_reporte(integrantes, familias, necesidades, cats)

    formularios = []
    for loc in localidades:
        fid = loc["id_formulario"]
        seccion = _seccion_reporte(
            [i for i in integrantes if fid and i["id_formulario"] == fid],
            [f for f in familias if fid and f["id_formulario"] == fid],
            [n for n in necesidades if fid and n["id_formulario_resuelto"] == fid],
            cats,
        )
        formularios.append({
            "id_edan_localidad": loc["id_edan_localidad"],
            "id_tipo_localidad": loc["id_tipo_localidad"],
            "localidad": {
                "id_edan_localidad": loc["id_edan_localidad"],
                "id_tipo_localidad": loc["id_tipo_localidad"],
                "tipo_localidad": loc["tipo_localidad_nombre"],
                "localidad": loc["localidad"],
                "estado_localidad": loc["estado_localidad_nombre"],
            },
            "id_formulario": fid,
            "estado_formulario": (
                {"id_estado": loc["id_estado"],
                 "codigo": loc["estado_codigo"], "nombre": loc["estado_nombre"]}
                if fid else None
            ),
            "fecha_creacion": loc["fecha_creacion"],
            "levantado_por": (
                {"id_usuario": loc["id_usuario"], "nombre": loc["usuario_nombre"],
                 "usuario": loc["usuario_login"]}
                if loc["id_usuario"] else None
            ),
            **seccion,
        })

    return {
        "evento": evento_block,
        "edan": edan_block,
        "resumen": resumen,
        "formularios": formularios,
    }


# Integrantes de todos los formularios del evento, con nombres de los
# catalogos de apoyo y la fecha de empadronamiento para calcular la edad.
# Orden por apellido: `lower()` evita mayusculas; tambien entra nombre y id
# como desempate (estable si hay homonimos).
_SQL_INTEGRANTES_POR_EVENTO = """
SELECT i.id_integrante, i.id_familia, i.numero_documento, i.tipo_documento,
       i.nombre, i.apellido, i.sexo, i.fecha_nacimiento, i.es_jefe,
       i.id_parentesco, p.nombre AS parentesco_nombre,
       i.id_discapacidad, d.nombre AS discapacidad_nombre,
       d.codigo AS discapacidad_codigo,
       i.id_enfermedad, e.nombre AS enfermedad_nombre,
       i.gestante_semanas, i.lactante_meses,
       fa.id_formulario,
       COALESCE(i.fecha_creacion, fo.fecha_creacion) AS fecha_empadronamiento
FROM rida.integrante i
JOIN rida.familia fa ON fa.id_familia = i.id_familia
JOIN rida.formulario_rida fo ON fo.id_formulario = fa.id_formulario
LEFT JOIN rida.cat_parentesco p ON p.id_parentesco = i.id_parentesco
LEFT JOIN rida.cat_tipo_discapacidad d ON d.id_discapacidad = i.id_discapacidad
LEFT JOIN rida.cat_enfermedad_cronica e ON e.id_enfermedad = i.id_enfermedad
WHERE fa.id_formulario IN ({in_sql})
ORDER BY lower(i.apellido), lower(i.nombre), i.id_integrante
"""

_SEXO_NOMBRE = {"M": "Masculino", "F": "Femenino"}


def get_evento_integrantes(db: Session, identificador, user: dict | None = None) -> dict | None:
    """Listado de TODOS los integrantes del evento agrupados por lugar
    (localidad), sin paginar. `identificador` es id numerico o codigo RIDA;
    None si no existe. Aplica scope geografico del usuario si se pasa `user`.

    Cada bloque de localidad trae los ids de rastreo al inicio y sus
    `personas` ordenadas por apellido. Edades y grupo etario calculados a la
    fecha del empadronamiento (mismos criterios que el reporte de secciones).
    """
    id_evento = resolver_evento(db, identificador)
    if not id_evento:
        return None
    if user is not None:
        _validar_scope_evento(db, user, id_evento)

    cab = _cabecera_reporte(db, id_evento)
    if not cab:
        return None
    evento_block, edan_block = cab

    localidades = _localidades_reporte(db, id_evento)
    edan_block["n_localidades"] = len(localidades)

    form_ids = sorted({l["id_formulario"] for l in localidades if l["id_formulario"]})
    ints_por_form: dict[int, list[dict]] = {}
    fams_por_form: dict[int, int] = {}
    if form_ids:
        in_sql = ",".join(str(int(x)) for x in form_ids)
        for r in _rows(db, _SQL_INTEGRANTES_POR_EVENTO.format(in_sql=in_sql), {}):
            ints_por_form.setdefault(r["id_formulario"], []).append(dict(r))
        for r in _rows(db, f"""
            SELECT fa.id_formulario, COUNT(*) AS n
            FROM rida.familia fa
            WHERE fa.id_formulario IN ({in_sql})
            GROUP BY fa.id_formulario
        """, {}):
            fams_por_form[r["id_formulario"]] = r["n"]

    grupos = {c: {"total": 0, "m": 0, "f": 0} for c, *_ in GRUPOS_ETARIOS_REPORTE}
    nombre_grupo = {c: n for c, n, *_ in GRUPOS_ETARIOS_REPORTE}
    resumen = {"n_localidades": len(localidades), "familias": 0, "integrantes": 0,
               "masculino": 0, "femenino": 0, "sin_sexo": 0,
               "por_grupo_etario": [], "con_discapacidad": 0, "con_enfermedad": 0,
               "gestantes": 0, "lactantes": 0}

    localidades_out: list[dict] = []
    for loc in localidades:
        fid = loc.get("id_formulario")
        filas = ints_por_form.get(fid, []) if fid else []
        personas: list[dict] = []
        for i in filas:
            edad = _edad_en(i["fecha_nacimiento"], i["fecha_empadronamiento"])
            g = _grupo_de(edad)
            sexo = i["sexo"] if i["sexo"] in ("M", "F") else None
            completa = " ".join(p.strip() for p in (i.get("apellido"), i.get("nombre"))
                                if p and p.strip()) or None
            personas.append({
                "numero_documento": i["numero_documento"],
                "tipo_documento": i["tipo_documento"],
                "nombre": i["nombre"],
                "apellido": i["apellido"],
                "nombre_completo": completa,
                "sexo": sexo,
                "sexo_nombre": _SEXO_NOMBRE.get(sexo),
                "fecha_nacimiento": i["fecha_nacimiento"],
                "edad": edad,
                "grupo_etario": g,
                "grupo_etario_nombre": nombre_grupo.get(g),
                "id_parentesco": i["id_parentesco"],
                "parentesco_nombre": i["parentesco_nombre"],
                "es_jefe": i["es_jefe"],
                "id_discapacidad": i["id_discapacidad"],
                "discapacidad_nombre": i["discapacidad_nombre"],
                "id_enfermedad": i["id_enfermedad"],
                "enfermedad_nombre": i["enfermedad_nombre"],
                "gestante_semanas": i["gestante_semanas"],
                "lactante_meses": i["lactante_meses"],
            })
            grupos[g]["total"] += 1
            if sexo == "M":
                grupos[g]["m"] += 1
                resumen["masculino"] += 1
            elif sexo == "F":
                grupos[g]["f"] += 1
                resumen["femenino"] += 1
            else:
                resumen["sin_sexo"] += 1
            # NINGUNA no es discapacidad (mismo criterio del reporte).
            if i["id_discapacidad"] and i.get("discapacidad_codigo") != "NINGUNA":
                resumen["con_discapacidad"] += 1
            if i["id_enfermedad"]:
                resumen["con_enfermedad"] += 1
            if i["gestante_semanas"] is not None:
                resumen["gestantes"] += 1
            if i["lactante_meses"] is not None:
                resumen["lactantes"] += 1
            resumen["integrantes"] += 1

        n_fams = fams_por_form.get(fid, 0) if fid else 0
        resumen["familias"] += n_fams
        localidades_out.append({
            "id_edan_localidad": loc.get("id_edan_localidad"),
            "id_tipo_localidad": loc.get("id_tipo_localidad"),
            "tipo_localidad": loc.get("tipo_localidad_nombre"),
            "localidad": loc.get("localidad"),
            "estado_localidad": loc.get("estado_localidad_nombre"),
            "id_formulario": fid,
            "familias": n_fams,
            "integrantes": len(personas),
            "personas": personas,
        })

    resumen["por_grupo_etario"] = [
        {"grupo": c, "nombre": n, "orden": o, **grupos[c]}
        for c, n, o, *_ in GRUPOS_ETARIOS_REPORTE
    ]

    return {
        "evento": evento_block,
        "edan": edan_block,
        "resumen": resumen,
        "localidades": localidades_out,
    }


def localidades_evento(db: Session, id_evento_rida: int) -> list:
    """HIJO del evento: formularios por localidad del EDAN (desglose de ids)."""
    rows = _rows(
        db,
        SQL_LOCALIDAD_EVENTO + " WHERE " + _LOCALIDAD_EVENTO_WHERE + " ORDER BY el.localidad",
        {"id_evento_rida": id_evento_rida},
    )
    return [dict(r) for r in rows]


_LOCALIDAD_EVENTO_WHERE = "ev.id_evento_rida = :id_evento_rida"


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


def _next_codigo_evento(db: Session, codigo_edan: str) -> str:
    """Codigo propio del evento RIDA: `codigo_edan` + '-R' (v2.46.0).

    edan.codigo_edan NO tiene UNIQUE (dos EDAN heredados pueden compartir
    codigo), asi que si '-R' ya existe se ensancha: '-R2', '-R3', ...
    """
    base = f"{codigo_edan}-R"
    filas = _rows(db,
                  "SELECT codigo FROM rida.evento_rida WHERE codigo LIKE :pref",
                  {"pref": base + "%"})
    seq = 0
    for f in filas:
        suf = str(f["codigo"] or "")[len(base):]
        if suf == "":
            seq = max(seq, 1)
        elif suf.isdigit():
            seq = max(seq, int(suf))
    return base if seq == 0 else f"{base}{seq + 1}"


def habilitar_evento(db: Session, id_edan: int, uid: int) -> dict:
    """Habilita el RIDA (PADRE) desde un EDAN aprobado y auto-crea los HIJO:
    un formulario por localidad del EDAN (si no existía), quedando listos.
    Solo guarda ids; ninguna copia de datos del EDAN.

    Genera `codigo` = codigo_edan + '-R'. Regla: un EDAN sin codigo_edan no
    puede habilitar RIDA (400) — sin codigo no hay RIDA ni consulta por codigo.
    """
    if not id_edan:
        raise HTTPException(status_code=422, detail="id_edan es obligatorio")
    edan = _row(db, "SELECT id_edan, id_estado, codigo_edan FROM edan.edan WHERE id_edan = :id",
                {"id": int(id_edan)})
    if not edan:
        raise HTTPException(status_code=400, detail="El EDAN no existe")
    if edan["id_estado"] not in (3, 5):
        raise HTTPException(
            status_code=400,
            detail=f"El EDAN no está aprobado (estado {edan['id_estado']}). "
                   "El RIDA solo nace del EDAN aprobado.",
        )
    if not edan.get("codigo_edan"):
        raise HTTPException(
            status_code=400,
            detail="El EDAN no tiene código (codigo_edan); consolídelo primero. "
                   "Sin código no se habilita RIDA.",
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

    codigo = _next_codigo_evento(db, edan["codigo_edan"])
    result = _row(
        db,
        """INSERT INTO rida.evento_rida (id_edan, id_estado, id_usuario_habilito, codigo)
           VALUES (:id_edan, :id_estado, :uid, :codigo)
           RETURNING id_evento_rida""",
        {"id_edan": int(id_edan), "id_estado": estado_habilitado["id_estado_evento"],
         "uid": uid, "codigo": codigo},
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


def atender_evento(db: Session, id_evento_rida: int, uid: int) -> dict:
    """Marca el evento RIDA como ATENDIDO (4). Solo desde EN PROCESO (3):
    HABILITADO(1) significa aún sin registros y CERRADO(5) es terminal."""
    row = _row(db, """SELECT ce.codigo AS estado_codigo
                      FROM rida.evento_rida ev
                      JOIN rida.cat_estado_evento ce ON ce.id_estado_evento = ev.id_estado
                      WHERE ev.id_evento_rida = :id""",
               {"id": id_evento_rida})
    if not row:
        raise HTTPException(status_code=404, detail="Evento RIDA no encontrado")
    if row["estado_codigo"] == "CERRADO":
        raise HTTPException(status_code=400, detail="Un evento CERRADO no se puede modificar (cerrar es terminal)")
    if row["estado_codigo"] != "EN PROCESO":
        raise HTTPException(
            status_code=400,
            detail=f"Solo un evento EN PROCESO puede pasar a ATENDIDO (estado actual: {row['estado_codigo']})")

    estado_atendido = _row(
        db, "SELECT id_estado_evento FROM rida.cat_estado_evento WHERE codigo = 'ATENDIDO'", {}
    )
    db.execute(
        text("""UPDATE rida.evento_rida
                SET id_estado = :id_estado,
                    fecha_modificacion = (NOW() AT TIME ZONE 'America/La_Paz')
                WHERE id_evento_rida = :id"""),
        {"id_estado": estado_atendido["id_estado_evento"], "id": id_evento_rida},
    )
    db.commit()
    return get_evento(db, id_evento_rida)


def cerrar_evento(db: Session, id_evento_rida: int, uid: int) -> dict:
    """Cierra el evento RIDA (PADRE): estado CERRADO + id_usuario_cierro +
    fecha_cierre con la hora automática del sistema de Bolivia (America/La_Paz).
    Cerrar es terminal: un evento ya cerrado no se re-cierra ni se reabre.
    Solo desde EN PROCESO o ATENDIDO (un evento HABILITADO sin registros no
    se cierra: primero debe empadronarse y/o atenderse)."""
    row = _row(db, """SELECT ce.codigo AS estado_codigo
                      FROM rida.evento_rida ev
                      JOIN rida.cat_estado_evento ce ON ce.id_estado_evento = ev.id_estado
                      WHERE ev.id_evento_rida = :id""",
               {"id": id_evento_rida})
    if not row:
        raise HTTPException(status_code=404, detail="Evento RIDA no encontrado")
    if row["estado_codigo"] == "CERRADO":
        raise HTTPException(status_code=400, detail="El evento RIDA ya está cerrado")
    if row["estado_codigo"] == "HABILITADO":
        raise HTTPException(
            status_code=400,
            detail="Un evento HABILITADO sin registros no se cierra: "
                   "registre el empadronamiento (pasa a EN PROCESO) y/o atiéndalo primero.")

    estado_cerrado = _row(
        db, "SELECT id_estado_evento FROM rida.cat_estado_evento WHERE codigo = 'CERRADO'", {}
    )
    if not estado_cerrado:
        raise HTTPException(status_code=500, detail="Catálogo estado evento sin CERRADO")

    db.execute(
        text("""UPDATE rida.evento_rida
                SET id_estado = :id_estado, id_usuario_cierro = :uid,
                    fecha_cierre = (NOW() AT TIME ZONE 'America/La_Paz'),
                    fecha_modificacion = (NOW() AT TIME ZONE 'America/La_Paz')
                WHERE id_evento_rida = :id"""),
        {"id_estado": estado_cerrado["id_estado_evento"], "uid": uid, "id": id_evento_rida},
    )
    db.commit()
    return get_evento(db, id_evento_rida)


def deshabilitar_evento(db: Session, id_evento_rida: int) -> dict:
    """Lo contrario de habilitar: evento creado por error y SIN datos.
    Borra físicamente el PADRE y sus HIJOS (los formularios auto-creados al
    habilitar; documentos caen en cascada) y libera id_edan para poder
    volver a habilitar. Bloqueado si algún hijo tiene familias, necesidades
    o solicitudes, o si el evento ya está CERRADO."""
    row = _row(db, """SELECT ev.id_edan, ce.codigo AS estado_codigo
                      FROM rida.evento_rida ev
                      JOIN rida.cat_estado_evento ce ON ce.id_estado_evento = ev.id_estado
                      WHERE ev.id_evento_rida = :id""",
               {"id": id_evento_rida})
    if not row:
        raise HTTPException(status_code=404, detail="Evento RIDA no encontrado")
    if row["estado_codigo"] == "CERRADO":
        raise HTTPException(status_code=400, detail="Un evento CERRADO no se puede deshabilitar (cerrar es terminal)")

    con_datos = _row(db, """SELECT COUNT(*) AS n
                             FROM rida.formulario_rida f
                             WHERE f.id_evento_rida = :id
                               AND (EXISTS (SELECT 1 FROM rida.familia fa
                                            WHERE fa.id_formulario = f.id_formulario)
                                    OR EXISTS (SELECT 1 FROM rida.necesidad nn
                                               JOIN rida.familia fnn ON fnn.id_familia = nn.id_familia
                                               WHERE fnn.id_formulario = f.id_formulario))""",
                    {"id": id_evento_rida})
    hay_solicitudes = _row(db, "SELECT COUNT(*) AS n FROM rida.solicitud WHERE id_evento_rida = :id",
                           {"id": id_evento_rida})
    if con_datos["n"] > 0 or hay_solicitudes["n"] > 0:
        raise HTTPException(
            status_code=400,
            detail="El evento tiene datos cargados (familias, necesidades o solicitudes). "
                   "Deshabilitar solo revierte habilitaciones por error, sin datos cargados.",
        )

    borrados = db.execute(
        text("DELETE FROM rida.formulario_rida WHERE id_evento_rida = :id"),
        {"id": id_evento_rida},
    ).rowcount
    db.execute(
        text("DELETE FROM rida.evento_rida WHERE id_evento_rida = :id"),
        {"id": id_evento_rida},
    )
    db.commit()
    return {
        "id_evento_rida": id_evento_rida,
        "id_edan": row["id_edan"],
        "formularios_eliminados": borrados,
    }

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
