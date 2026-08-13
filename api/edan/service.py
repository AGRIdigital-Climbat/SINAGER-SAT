from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text


# ============================================================================
#  SQL BASE: cabecera + catálogos anidados
# ============================================================================

SQL_EDAN = """
    SELECT e.*,
           d.id as d_id, d.codigo_ine as d_codigo_ine, d.nombre as d_nombre,
           p.id as p_id, p.codigo_ine as p_codigo_ine, p.nombre as p_nombre,
           m.id as m_id, m.codigo_ine as m_codigo_ine, m.nombre as m_nombre,
           te.id_tipo_evento as te_id, te.nombre as te_nombre,
           es.id_estado as es_id, es.nombre as es_nombre,
           es.descripcion as es_descripcion, es.orden as es_orden,
           ugr.id_usuario as ugr_id, ugr.usuario as ugr_usuario, ugr.nombre as ugr_nombre,
           alc.id_usuario as alc_id, alc.usuario as alc_usuario, alc.nombre as alc_nombre,
           (SELECT COUNT(*) FROM edan.edan_localidades lc
             WHERE lc.id_edan = e.id_edan) AS num_localidades
    FROM edan.edan e
    LEFT JOIN shared.departamento d ON e.id_departamento = d.id
    LEFT JOIN shared.provincia p ON e.id_provincia = p.id
    LEFT JOIN shared.municipio m ON e.id_municipio = m.id
    LEFT JOIN edan.tipo_evento te ON e.id_tipo_evento = te.id_tipo_evento
    LEFT JOIN edan.estado_edan es ON e.id_estado = es.id_estado
    LEFT JOIN usuarios.usuario ugr ON e.id_usuario_ugr = ugr.id_usuario
    LEFT JOIN usuarios.usuario alc ON e.id_usuario_alcalde = alc.id_usuario
"""


# ============================================================================
#  BUILDER: JSON anidado de la cabecera (ids -> contenido del id relacionado)
# ============================================================================

def _build_edan(row):
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
    data["tipo_evento"] = {
        "id_tipo_evento": data.pop("te_id"),
        "nombre": data.pop("te_nombre"),
    } if data.get("te_id") else None
    data["estado"] = {
        "id_estado": data.pop("es_id"),
        "nombre": data.pop("es_nombre"),
        "descripcion": data.pop("es_descripcion"),
        "orden": data.pop("es_orden"),
    } if data.get("es_id") else None
    data["usuario_ugr"] = {
        "id_usuario": data.pop("ugr_id"),
        "usuario": data.pop("ugr_usuario"),
        "nombre": data.pop("ugr_nombre"),
    } if data.get("ugr_id") else None
    data["usuario_alcalde"] = {
        "id_usuario": data.pop("alc_id"),
        "usuario": data.pop("alc_usuario"),
        "nombre": data.pop("alc_nombre"),
    } if data.get("alc_id") else None
    for k in ("responsable_nombre", "responsable_cargo", "responsable_fono",
              "responsable_correo", "id_reporte_rea", "fotografia", "nombre_alcalde",
              "fono_alcalde", "id_server", "es_borrador", "sincronizado"):
        data.pop(k, None)
    return data


def _rows(db: Session, query: str, params: dict) -> list:
    return db.execute(text(query), params).mappings().all()


def _row(db: Session, query: str, params: dict):
    return db.execute(text(query), params).mappings().first()


# ============================================================================
#  CRUD CABECERA
# ============================================================================

def get_edan(db: Session, id: int):
    row = _row(db, f"{SQL_EDAN} WHERE e.id_edan = :id", {"id": id})
    return _build_edan(row) if row else None


def _build_header_payload(db: Session, data: dict) -> dict:
    header = {
        "id_local": data.get("id_local"),
        "codigo_edan": data.get("codigo_edan"),
        "id_departamento": data.get("id_departamento"),
        "id_provincia": data.get("id_provincia"),
        "id_municipio": data.get("id_municipio"),
        "id_tipo_evento": data.get("id_tipo_evento"),
        "id_usuario_ugr": data.get("id_usuario_ugr"),
        "id_usuario_alcalde": data.get("id_usuario_alcalde"),
        "fecha_llenado": data.get("fecha_llenado") or None,
        "fecha_evento": data.get("fecha_evento") or None,
        "hora_evento": data.get("hora_evento") or None,
        "total_poblacion_afectada": data.get("total_poblacion_afectada", 0),
        "total_familias_afectadas": data.get("total_familias_afectadas", 0),
        "total_familias_damnificadas": data.get("total_familias_damnificadas", 0),
        "id_estado": data.get("id_estado", 1),
        "pendiente_eliminacion": data.get("pendiente_eliminacion", False),
        "pendiente_actualizacion": data.get("pendiente_actualizacion", False),
    }

    if header["id_municipio"] and not (header["id_provincia"] and header["id_departamento"]):
        mun = _row(db, "SELECT id, id_provincia, id_departamento, nombre FROM shared.municipio WHERE id = :id",
                   {"id": header["id_municipio"]})
        if mun:
            header["id_provincia"] = header["id_provincia"] or mun["id_provincia"]
            header["id_departamento"] = header["id_departamento"] or mun["id_departamento"]
    return header


# ============================================================================
#  LOCALIDADES: lectura (anidada)
# ============================================================================


def _one(db: Session, table: str, id_localidad: int, extra: str = ""):
    return _row(db, f"SELECT * FROM edan.{table} WHERE id_edan_localidad = :id {extra}",
                {"id": id_localidad})


def _all(db: Session, table: str, id_localidad: int, order: str = ""):
    q = f"SELECT * FROM edan.{table} WHERE id_edan_localidad = :id {order}"
    return [dict(r) for r in _rows(db, q, {"id": id_localidad})]


def _impacto_poblacion(db, id_localidad):
    return _all(db, "edan_localidades_impacto_poblacion", id_localidad,
                "ORDER BY id_impacto_poblacion")


def _servicios_basicos(db, id_localidad):
    return _all(db, "edan_localidades_servicios_basicos", id_localidad,
                "ORDER BY id_servicio_basico")


def _grupos_vulnerables(db, id_localidad):
    rows = _all(db, "edan_localidades_proteccion", id_localidad,
                "ORDER BY id_grupo_vulnerable")
    return [
        {
            "id_grupo_vulnerable": g["id_grupo_vulnerable"],
            "grupo": g["grupo"],
            "mujeres": g["mujeres"] or 0,
            "hombres": g["hombres"] or 0,
            "total": g["total"] if g["total"] is not None else (g["mujeres"] or 0) + (g["hombres"] or 0),
            "apoyo_psicologico": g["apoyo_psicologico"],
            "reposicion_documentos": g["reposicion_documentos"],
            "observaciones": g["observaciones"] or "",
        } for g in rows
    ]


def _build_localidad(db: Session, id_localidad: int) -> dict:
    loc = {
        "id_edan_localidad": id_localidad,
        "id_edan": None,
        "es_huerfana": True,
        "id_tipo_localidad": None,
        "id_edan_localidad_estado": None,
        "id_tipo_evento": None,
        "id_departamento": None,
        "id_provincia": None,
        "id_municipio": None,
        "fecha_llenado": None,
        "fecha_evento": None,
        "hora_evento": None,
        "total_poblacion_afectada": 0,
        "total_familias_afectadas": 0,
        "total_familias_damnificadas": 0,
        "id_local": None,
        "id_usuario": None,
        "fecha_modificacion": None,
        "pendiente_actualizacion": False,
        "pendiente_eliminacion": False,
        "localidad": "",
        "imp_poblacion": False,
        "imp_salud": False,
        "imp_infraestructura": False,
        "imp_servicios": False,
        "imp_educacion": False,
        "imp_vivienda": False,
        "imp_agropecuario": False,
        "imp_proteccion": False,
        "imp_necesidades": False,
    }
    row = _row(db, "SELECT * FROM edan.edan_localidades WHERE id_edan_localidad = :id",
               {"id": id_localidad})
    if not row:
        return None
    for k in loc.keys():
        if k in row and k != "id_edan_localidad":
            loc[k] = row[k]

    # Marcar si es huérfana o consolidada
    loc["es_huerfana"] = loc["id_edan"] is None

    tl = None
    if loc["id_tipo_localidad"]:
        tl = _row(db, "SELECT id_tipo_localidad, nombre, descripcion, orden"
                      " FROM edan.tipo_localidad WHERE id_tipo_localidad = :id",
                  {"id": loc["id_tipo_localidad"]})
    loc["tipo_localidad"] = dict(tl) if tl else None

    le = None
    if loc["id_edan_localidad_estado"]:
        le = _row(db, "SELECT id_edan_localidad_estado, nombre, descripcion, orden"
                      " FROM edan.edan_localidades_estado"
                      " WHERE id_edan_localidad_estado = :id",
                  {"id": loc["id_edan_localidad_estado"]})
    loc["estado_localidad"] = dict(le) if le else None

    if loc["id_tipo_evento"]:
        te = _row(db, "SELECT id_tipo_evento, nombre FROM edan.tipo_evento"
                      " WHERE id_tipo_evento = :id", {"id": loc["id_tipo_evento"]})
        loc["tipo_evento"] = dict(te) if te else None
    else:
        loc["tipo_evento"] = None

    if loc["id_departamento"]:
        d = _row(db, "SELECT id, codigo_ine, nombre FROM shared.departamento WHERE id = :id",
                 {"id": loc["id_departamento"]})
        loc["departamento"] = dict(d) if d else None
    else:
        loc["departamento"] = None

    if loc["id_provincia"]:
        p = _row(db, "SELECT id, codigo_ine, nombre FROM shared.provincia WHERE id = :id",
                 {"id": loc["id_provincia"]})
        loc["provincia"] = dict(p) if p else None
    else:
        loc["provincia"] = None

    if loc["id_municipio"]:
        m = _row(db, "SELECT id, codigo_ine, nombre FROM shared.municipio WHERE id = :id",
                 {"id": loc["id_municipio"]})
        loc["municipio"] = dict(m) if m else None
    else:
        loc["municipio"] = None

    # EDAN cabecera (si está consolidada)
    if loc["id_edan"]:
        edan = _row(db, """
            SELECT e.id_edan, e.codigo_edan, e.id_estado,
                   es.nombre AS estado_nombre, es.orden AS estado_orden,
                   e.fecha_evento, e.hora_evento, e.fecha_llenado,
                   e.fecha_modificacion, e.id_usuario_ugr, e.id_usuario_alcalde
            FROM edan.edan e
            LEFT JOIN edan.estado_edan es ON es.id_estado = e.id_estado
            WHERE e.id_edan = :id
        """, {"id": loc["id_edan"]})
        if edan:
            loc["edan"] = {
                "id_edan": edan["id_edan"],
                "codigo_edan": edan["codigo_edan"],
                "id_estado": edan["id_estado"],
                "estado": {
                    "id_estado": edan["id_estado"],
                    "nombre": edan["estado_nombre"],
                    "orden": edan["estado_orden"],
                } if edan["id_estado"] else None,
                "fecha_evento": edan["fecha_evento"],
                "hora_evento": edan["hora_evento"],
                "fecha_llenado": edan["fecha_llenado"],
                "fecha_modificacion": edan["fecha_modificacion"],
                "id_usuario_ugr": edan["id_usuario_ugr"],
                "id_usuario_alcalde": edan["id_usuario_alcalde"],
            }
        else:
            loc["edan"] = None
    else:
        loc["edan"] = None

    # 1. Impacto en población (1:N por rango etario)
    loc["impacto_poblacion"] = _impacto_poblacion(db, id_localidad)

    # 2. Primera respuesta (1:1)
    pr = _one(db, "edan_localidades_primera_respuesta", id_localidad)
    loc["necesidad_primera_respuesta"] = {
        "busqueda": pr["busqueda"] if pr else False,
        "salvamento": pr["salvamento"] if pr else False,
        "evacuacion": pr["evacuacion"] if pr else False,
        "observaciones": pr["observaciones"] if pr else "",
    }

# 3. Establecimientos de salud (1:N)
    est = _all(db, "edan_localidades_salud_establecimientos", id_localidad,
               "ORDER BY id_establecimiento_salud")
    loc["establecimientos_salud"] = [
        {
            "id_establecimiento_salud": r["id_establecimiento_salud"],
            "nombre_establecimiento": r["nombre_establecimiento"],
            "comunidad": r["comunidad"],
            "nivel_atencion": r["nivel_atencion"],
            "dano_parcial": r["dano_parcial"],
            "dano_total": r["dano_total"],
            "medicos_afectados": r["medicos_afectados"],
            "enfermeras_afectadas": r["enfermeras_afectadas"],
            "otros_afectados": r["otros_afectados"],
            "fotografia": r.get("fotografia"),
            "coordenada_lat": r.get("coordenada_lat"),
            "coordenada_lon": r.get("coordenada_lon"),
        } for r in est
    ]   

    # 4. Necesidades de salud (1:1)
    ns = _one(db, "edan_localidades_salud_necesidades", id_localidad)
    loc["necesidad_salud"] = {
        "numero_personas": ns["numero_personas"] if ns else 0,
        "otras_necesidades": ns["otras_necesidades"] if ns else "",
        "observaciones": ns["observaciones"] if ns else "",
    }

    # 5. Daños viales (1:N)
    loc["danos_viales"] = _all(db, "edan_localidades_danos_viales", id_localidad,
                               "ORDER BY id_dano_vial")

    # 6. Daños infraestructura pública (1:N)
    loc["danos_infra_publica"] = _all(db, "edan_localidades_danos_infra_publica",
                                      id_localidad, "ORDER BY id_dano_infra")

    # 7. Servicios básicos (1:N)
    loc["servicios_basicos"] = _servicios_basicos(db, id_localidad)

    # 8. Unidades educativas (1:N)
    loc["unidades_educativas"] = _all(db, "edan_localidades_unidades_educativas",
                                      id_localidad, "ORDER BY id_unidad_educativa")

    # 9. Daños vivienda (1:N)
    loc["danos_vivienda"] = _all(db, "edan_localidades_danos_vivienda",
                                 id_localidad, "ORDER BY id_dano_vivienda")

    # 10. Agricultura (1:N) + cultivo anidado
    ag_rows = _rows(db, """
        SELECT a.*, c.id as c_id, c.nombre as c_nombre, c.grupo as c_grupo
        FROM edan.edan_localidades_danos_agricultura a
        LEFT JOIN shared.cultivo c ON c.id = a.id_cultivo
        WHERE a.id_edan_localidad = :id ORDER BY a.id_dano_agricultura
    """, {"id": id_localidad})
    loc["danos_agricultura"] = []
    for r in ag_rows:
        item = dict(r)
        c = item.pop("c_id", None)
        item.pop("c_nombre", None)
        item.pop("c_grupo", None)
        item["cultivo"] = {
            "id": c,
            "nombre": r.get("c_nombre"),
            "grupo": r.get("c_grupo"),
        } if c else None
        loc["danos_agricultura"].append(item)

    # 11. Pecuario (1:N) + especie anidada
    pe_rows = _rows(db, """
        SELECT a.*, pe.id as pe_id, pe.nombre as pe_nombre, pe.grupo as pe_grupo
        FROM edan.edan_localidades_danos_pecuario a
        LEFT JOIN shared.pecuario pe ON pe.id = a.id_especie
        WHERE a.id_edan_localidad = :id ORDER BY a.id_dano_pecuario
    """, {"id": id_localidad})
    loc["danos_pecuarios"] = []
    for r in pe_rows:
        item = dict(r)
        pe = item.pop("pe_id", None)
        item.pop("pe_nombre", None)
        item.pop("pe_grupo", None)
        item["especie"] = {
            "id": pe,
            "nombre": r.get("pe_nombre"),
            "grupo": r.get("pe_grupo"),
        } if pe else None
        loc["danos_pecuarios"].append(item)

    # 12. Infraestructura productiva (1:N)
    loc["infra_productiva"] = _all(db, "edan_localidades_infra_productiva",
                                   id_localidad, "ORDER BY id_infra_productiva")

    # 13. Protección (1:N por grupo vulnerable)
    loc["proteccion"] = _grupos_vulnerables(db, id_localidad)

    # 14. Necesidades humanitarias (1:1)
    nh = _one(db, "edan_localidades_necesidades_humanitarias", id_localidad)
    if nh:
        nh = dict(nh)
        nh.pop("id_edan_localidad", None)
        loc["necesidad_humanitaria"] = nh
    else:
        loc["necesidad_humanitaria"] = {k: (False if not k.startswith("obs_") else "")
                                        for k in _NH_FIELDS}

    return loc


_NH_FIELDS = [
    "alimentos", "refugio_vivienda", "ropa_cama", "articulos_higiene",
    "articulos_cocina", "prendas_vestir", "herramientas", "almacenamiento_agua",
    "banos",
] + [f"obs_{x}" for x in (
    "alimentos", "refugio_vivienda", "ropa_cama", "articulos_higiene",
    "articulos_cocina", "prendas_vestir", "herramientas", "almacenamiento_agua",
    "banos")]


def get_edan_completo(db: Session, id: int):
    edan = get_edan(db, id)
    if not edan:
        return None
    edan["localidades"] = _get_localidades(db, id)
    edan["reportes_rea"] = [dict(r) for r in _rows(db, """
        SELECT id_reporte, comunidad, fecha_evento, hora_evento,
               id_municipio, id_tipo_evento, descripcion
        FROM rea.reporte_evento WHERE id_edan = :id_edan ORDER BY id_reporte
    """, {"id_edan": id})]
    return edan


def get_edan_por_reporte(db: Session, id_reporte: int):
    """Devuelve el EDAN generado desde un reporte REA (o None si no está vinculado)."""
    row = _row(db, "SELECT id_edan FROM edan.edan WHERE id_reporte_rea = :id", {"id": id_reporte})
    if not row or row["id_edan"] is None:
        row = _row(db, "SELECT id_edan FROM rea.reporte_evento WHERE id_reporte = :id", {"id": id_reporte})
    if not row or row["id_edan"] is None:
        return None
    return get_edan_completo(db, row["id_edan"])


def _get_localidades(db: Session, id_edan: int) -> list:
    rows = _rows(db, """
        SELECT id_edan_localidad FROM edan.edan_localidades
        WHERE id_edan = :id ORDER BY id_edan_localidad
    """, {"id": id_edan})
    return [_build_localidad(db, r["id_edan_localidad"]) for r in rows]


# ============================================================================
#  LOCALIDADES: escritura
# ============================================================================

def _resolve_tipo_localidad(db: Session, loc: dict) -> int | None:
    """Prioriza id_tipo_localidad; si llega el string legacy 'tipo_localidad',
    lo resuelve por nombre (compatibilidad con la app durante la transición)."""
    if loc.get("id_tipo_localidad") is not None:
        return loc["id_tipo_localidad"]
    nombre = loc.get("tipo_localidad")
    if nombre:
        t = _row(db, "SELECT id_tipo_localidad FROM edan.tipo_localidad WHERE nombre = :n",
                 {"n": nombre})
        if t:
            return t["id_tipo_localidad"]
    return None


def _inherit_localidad_header(db: Session, loc: dict, id_edan: int | None):
    """Robustez de sync: si la localidad no trae evento/geografía/fechas,
    los hereda de su EDAN (evita pérdida de datos al reemplazar localidades)."""
    if id_edan is None:
        return
    row = _row(db, """
        SELECT id_tipo_evento, id_departamento, id_provincia, id_municipio,
               fecha_llenado, fecha_evento, hora_evento,
               total_poblacion_afectada, total_familias_afectadas,
               total_familias_damnificadas
        FROM edan.edan WHERE id_edan = :id
    """, {"id": id_edan})
    if not row:
        return
    for k in ("id_tipo_evento", "id_departamento", "id_provincia", "id_municipio",
              "fecha_llenado", "fecha_evento", "hora_evento"):
        if loc.get(k) in (None, "") and row[k] is not None:
            loc[k] = row[k]


def _insert_localidad(db: Session, id_edan: int | None, loc: dict) -> int:
    _inherit_localidad_header(db, loc, id_edan)
    lid = db.execute(text("""
        INSERT INTO edan.edan_localidades
            (id_edan, id_tipo_localidad, id_edan_localidad_estado, localidad,
             imp_poblacion, imp_salud, imp_infraestructura, imp_servicios,
             imp_educacion, imp_vivienda, imp_agropecuario, imp_proteccion, imp_necesidades,
             id_tipo_evento, id_departamento, id_provincia, id_municipio,
             fecha_llenado, fecha_evento, hora_evento,
             total_poblacion_afectada, total_familias_afectadas, total_familias_damnificadas,
             id_local, id_usuario, fecha_modificacion,
             pendiente_actualizacion, pendiente_eliminacion)
        VALUES (:id_edan, :id_tipo_localidad, :id_edan_localidad_estado, :localidad,
                :imp_poblacion, :imp_salud, :imp_infraestructura, :imp_servicios,
                :imp_educacion, :imp_vivienda, :imp_agropecuario, :imp_proteccion, :imp_necesidades,
                :id_tipo_evento, :id_departamento, :id_provincia, :id_municipio,
                :fecha_llenado, :fecha_evento, :hora_evento,
                :total_poblacion_afectada, :total_familias_afectadas, :total_familias_damnificadas,
                :id_local, :id_usuario, :fecha_modificacion,
                :pendiente_actualizacion, :pendiente_eliminacion)
        RETURNING id_edan_localidad
    """), {
        "id_edan": id_edan,
        "id_tipo_localidad": _resolve_tipo_localidad(db, loc),
        "id_edan_localidad_estado": loc.get("id_edan_localidad_estado"),
        "localidad": loc.get("localidad", ""),
        "imp_poblacion": loc.get("imp_poblacion", False),
        "imp_salud": loc.get("imp_salud", False),
        "imp_infraestructura": loc.get("imp_infraestructura", False),
        "imp_servicios": loc.get("imp_servicios", False),
        "imp_educacion": loc.get("imp_educacion", False),
        "imp_vivienda": loc.get("imp_vivienda", False),
        "imp_agropecuario": loc.get("imp_agropecuario", False),
        "imp_proteccion": loc.get("imp_proteccion", False),
        "imp_necesidades": loc.get("imp_necesidades", False),
        "id_tipo_evento": loc.get("id_tipo_evento"),
        "id_departamento": loc.get("id_departamento"),
        "id_provincia": loc.get("id_provincia"),
        "id_municipio": loc.get("id_municipio"),
        "fecha_llenado": loc.get("fecha_llenado") or None,
        "fecha_evento": loc.get("fecha_evento") or None,
        "hora_evento": loc.get("hora_evento") or None,
        "total_poblacion_afectada": loc.get("total_poblacion_afectada", 0),
        "total_familias_afectadas": loc.get("total_familias_afectadas", 0),
        "total_familias_damnificadas": loc.get("total_familias_damnificadas", 0),
        "id_local": loc.get("id_local"),
        "id_usuario": loc.get("id_usuario"),
        "fecha_modificacion": _parse_fecha(loc.get("fecha_modificacion")) or datetime.now(),
        "pendiente_actualizacion": loc.get("pendiente_actualizacion", False),
        "pendiente_eliminacion": loc.get("pendiente_eliminacion", False),
    }).scalar()

    _insert_sections_only(db, lid, loc)
    return lid


def _delete_localidad_sections(db: Session, id_localidad: int):
    tables = [
        "edan_localidades_impacto_poblacion",
        "edan_localidades_primera_respuesta",
        "edan_localidades_salud_establecimientos",
        "edan_localidades_salud_necesidades",
        "edan_localidades_danos_viales",
        "edan_localidades_danos_infra_publica",
        "edan_localidades_servicios_basicos",
        "edan_localidades_unidades_educativas",
        "edan_localidades_danos_vivienda",
        "edan_localidades_danos_agricultura",
        "edan_localidades_danos_pecuario",
        "edan_localidades_infra_productiva",
        "edan_localidades_proteccion",
        "edan_localidades_necesidades_humanitarias",
    ]
    for t in tables:
        db.execute(text(f"DELETE FROM edan.{t} WHERE id_edan_localidad = :id"),
                   {"id": id_localidad})


def _bump_edan_fecha(db: Session, id_edan: int):
    db.execute(text("""
        UPDATE edan.edan SET fecha_modificacion = NOW(),
            pendiente_actualizacion = TRUE
        WHERE id_edan = :id
    """), {"id": id_edan})


def delete_localidad(db: Session, id_localidad: int) -> bool:
    parent = _row(db, "SELECT id_edan FROM edan.edan_localidades WHERE id_edan_localidad = :id",
                  {"id": id_localidad})
    if not parent:
        return False
    db.execute(text("DELETE FROM edan.edan_localidades WHERE id_edan_localidad = :id"),
               {"id": id_localidad})
    if parent["id_edan"] is not None:
        _bump_edan_fecha(db, parent["id_edan"])
    db.commit()
    return True


def update_localidad(db: Session, id_localidad: int, data: dict) -> dict | None:
    parent = _row(db, "SELECT id_edan FROM edan.edan_localidades WHERE id_edan_localidad = :id",
                  {"id": id_localidad})
    if not parent:
        return None
    _inherit_localidad_header(db, data, parent["id_edan"])
    db.execute(text("""
        UPDATE edan.edan_localidades SET
            id_tipo_localidad = :id_tipo_localidad,
            id_edan_localidad_estado = :id_edan_localidad_estado,
            localidad = :localidad,
            imp_poblacion = :imp_poblacion, imp_salud = :imp_salud,
            imp_infraestructura = :imp_infraestructura, imp_servicios = :imp_servicios,
            imp_educacion = :imp_educacion, imp_vivienda = :imp_vivienda,
            imp_agropecuario = :imp_agropecuario, imp_proteccion = :imp_proteccion,
            imp_necesidades = :imp_necesidades,
            id_tipo_evento = :id_tipo_evento,
            id_departamento = :id_departamento, id_provincia = :id_provincia,
            id_municipio = :id_municipio,
            fecha_llenado = :fecha_llenado, fecha_evento = :fecha_evento,
            hora_evento = :hora_evento,
            total_poblacion_afectada = :total_poblacion_afectada,
            total_familias_afectadas = :total_familias_afectadas,
            total_familias_damnificadas = :total_familias_damnificadas,
            fecha_modificacion = NOW()
        WHERE id_edan_localidad = :id
    """), {
        "id": id_localidad,
        "id_tipo_localidad": _resolve_tipo_localidad(db, data),
        "id_edan_localidad_estado": data.get("id_edan_localidad_estado"),
        "localidad": data.get("localidad", ""),
        "imp_poblacion": data.get("imp_poblacion", False),
        "imp_salud": data.get("imp_salud", False),
        "imp_infraestructura": data.get("imp_infraestructura", False),
        "imp_servicios": data.get("imp_servicios", False),
        "imp_educacion": data.get("imp_educacion", False),
        "imp_vivienda": data.get("imp_vivienda", False),
        "imp_agropecuario": data.get("imp_agropecuario", False),
        "imp_proteccion": data.get("imp_proteccion", False),
        "imp_necesidades": data.get("imp_necesidades", False),
        "id_tipo_evento": data.get("id_tipo_evento"),
        "id_departamento": data.get("id_departamento"),
        "id_provincia": data.get("id_provincia"),
        "id_municipio": data.get("id_municipio"),
        "fecha_llenado": data.get("fecha_llenado") or None,
        "fecha_evento": data.get("fecha_evento") or None,
        "hora_evento": data.get("hora_evento") or None,
        "total_poblacion_afectada": data.get("total_poblacion_afectada", 0),
        "total_familias_afectadas": data.get("total_familias_afectadas", 0),
        "total_familias_damnificadas": data.get("total_familias_damnificadas", 0),
    })
    _delete_localidad_sections(db, id_localidad)
    _insert_sections_only(db, id_localidad, data)
    if parent["id_edan"] is not None:
        _bump_edan_fecha(db, parent["id_edan"])
    db.commit()
    return _build_localidad(db, id_localidad)


def _insert_sections_only(db: Session, lid: int, loc: dict):
    for ip in loc.get("impacto_poblacion") or []:
        db.execute(text("""
            INSERT INTO edan.edan_localidades_impacto_poblacion
                (id_edan_localidad, rango, fallecidos, heridos, desaparecidos, observaciones)
            VALUES (:id, :rango, :fallecidos, :heridos, :desaparecidos, :observaciones)
        """), {
            "id": lid, "rango": ip.get("rango", ""),
            "fallecidos": ip.get("fallecidos", 0), "heridos": ip.get("heridos", 0),
            "desaparecidos": ip.get("desaparecidos", 0),
            "observaciones": ip.get("observaciones", ""),
        })

    pr = loc.get("necesidad_primera_respuesta")
    if pr:
        db.execute(text("""
            INSERT INTO edan.edan_localidades_primera_respuesta
                (id_edan_localidad, busqueda, salvamento, evacuacion, observaciones)
            VALUES (:id, :busqueda, :salvamento, :evacuacion, :observaciones)
        """), {
            "id": lid, "busqueda": pr.get("busqueda", False),
            "salvamento": pr.get("salvamento", False),
            "evacuacion": pr.get("evacuacion", False),
            "observaciones": pr.get("observaciones", ""),
        })

    for e in loc.get("establecimientos_salud") or []:
        db.execute(text("""
            INSERT INTO edan.edan_localidades_salud_establecimientos
                (id_edan_localidad, nombre_establecimiento, comunidad, nivel_atencion,
                 dano_parcial, dano_total, medicos_afectados, enfermeras_afectadas, otros_afectados,
                 fotografia, coordenada_lat, coordenada_lon)
            VALUES (:id, :nombre_establecimiento, :comunidad, :nivel_atencion,
                    :dano_parcial, :dano_total, :medicos_afectados, :enfermeras_afectadas, :otros_afectados,
                    :fotografia, :coordenada_lat, :coordenada_lon)
        """), {
            "id": lid, "nombre_establecimiento": e.get("nombre_establecimiento", ""),
            "comunidad": e.get("comunidad", ""), "nivel_atencion": e.get("nivel_atencion", ""),
            "dano_parcial": e.get("dano_parcial", False), "dano_total": e.get("dano_total", False),
            "medicos_afectados": e.get("medicos_afectados", 0),
            "enfermeras_afectadas": e.get("enfermeras_afectadas", 0),
            "otros_afectados": e.get("otros_afectados", 0),
            "fotografia": e.get("fotografia"),
            "coordenada_lat": e.get("coordenada_lat"),
            "coordenada_lon": e.get("coordenada_lon"),
        })

    ns = loc.get("necesidad_salud")
    if ns:
        db.execute(text("""
            INSERT INTO edan.edan_localidades_salud_necesidades
                (id_edan_localidad, numero_personas, otras_necesidades, observaciones)
            VALUES (:id, :numero_personas, :otras_necesidades, :observaciones)
        """), {
            "id": lid, "numero_personas": ns.get("numero_personas", 0),
            "otras_necesidades": ns.get("otras_necesidades", ""),
            "observaciones": ns.get("observaciones", ""),
        })

    for d in loc.get("danos_viales") or []:
        db.execute(text("""
            INSERT INTO edan.edan_localidades_danos_viales
                (id_edan_localidad, via, puente, tramo, dano_parcial, dano_total,
                 km_danio, necesidades_inmediatas, observaciones,
                 fotografia, coordenada_lat, coordenada_lon)
            VALUES (:id, :via, :puente, :tramo, :dano_parcial, :dano_total,
                    :km_danio, :necesidades_inmediatas, :observaciones,
                    :fotografia, :coordenada_lat, :coordenada_lon)
        """), {
            "id": lid, "via": d.get("via", False), "puente": d.get("puente", False),
            "tramo": d.get("tramo", ""),
            "dano_parcial": d.get("dano_parcial", False), "dano_total": d.get("dano_total", False),
            "km_danio": d.get("km_danio") or 0,
            "necesidades_inmediatas": d.get("necesidades_inmediatas", ""),
            "observaciones": d.get("observaciones", ""),
            "fotografia": d.get("fotografia"),
            "coordenada_lat": d.get("coordenada_lat"),
            "coordenada_lon": d.get("coordenada_lon"),
        })

    for d in loc.get("danos_infra_publica") or []:
        db.execute(text("""
            INSERT INTO edan.edan_localidades_danos_infra_publica
                (id_edan_localidad, comunidad, tipo_estructura, dano_parcial, dano_total, observaciones,
                 fotografia, coordenada_lat, coordenada_lon)
            VALUES (:id, :comunidad, :tipo_estructura, :dano_parcial, :dano_total, :observaciones,
                    :fotografia, :coordenada_lat, :coordenada_lon)
        """), {
            "id": lid, "comunidad": d.get("comunidad", ""),
            "tipo_estructura": d.get("tipo_estructura", ""),
            "dano_parcial": d.get("dano_parcial", False), "dano_total": d.get("dano_total", False),
            "observaciones": d.get("observaciones", ""),
            "fotografia": d.get("fotografia"),
            "coordenada_lat": d.get("coordenada_lat"),
            "coordenada_lon": d.get("coordenada_lon"),
        })

    for s in loc.get("servicios_basicos") or []:
        db.execute(text("""
            INSERT INTO edan.edan_localidades_servicios_basicos
                (id_edan_localidad, tipo, dano_parcial, dano_total,
                 necesidades_inmediatas, observaciones,
                 fotografia, coordenada_lat, coordenada_lon)
            VALUES (:id, :tipo, :dano_parcial, :dano_total,
                    :necesidades_inmediatas, :observaciones,
                    :fotografia, :coordenada_lat, :coordenada_lon)
        """), {
            "id": lid, "tipo": s.get("tipo", ""),
            "dano_parcial": s.get("dano_parcial", False), "dano_total": s.get("dano_total", False),
            "necesidades_inmediatas": s.get("necesidades_inmediatas", ""),
            "observaciones": s.get("observaciones", ""),
            "fotografia": s.get("fotografia"),
            "coordenada_lat": s.get("coordenada_lat"),
            "coordenada_lon": s.get("coordenada_lon"),
        })

    for u in loc.get("unidades_educativas") or []:
        db.execute(text("""
            INSERT INTO edan.edan_localidades_unidades_educativas
                (id_edan_localidad, nombre_establecimiento, comunidad, dano_parcial, dano_total,
                 suspension_clases, perdida_material, funciona_albergue,
                 estudiantes, profesores, administrativos, observaciones,
                 fotografia, coordenada_lat, coordenada_lon)
            VALUES (:id, :nombre_establecimiento, :comunidad, :dano_parcial, :dano_total,
                    :suspension_clases, :perdida_material, :funciona_albergue,
                    :estudiantes, :profesores, :administrativos, :observaciones,
                    :fotografia, :coordenada_lat, :coordenada_lon)
        """), {
            "id": lid, "nombre_establecimiento": u.get("nombre_establecimiento", ""),
            "comunidad": u.get("comunidad", ""),
            "dano_parcial": u.get("dano_parcial", False), "dano_total": u.get("dano_total", False),
            "suspension_clases": u.get("suspension_clases"),
            "perdida_material": u.get("perdida_material"),
            "funciona_albergue": u.get("funciona_albergue"),
            "estudiantes": u.get("estudiantes", 0),
            "profesores": u.get("profesores", 0),
            "administrativos": u.get("administrativos", 0),
            "observaciones": u.get("observaciones", ""),
            "fotografia": u.get("fotografia"),
            "coordenada_lat": u.get("coordenada_lat"),
            "coordenada_lon": u.get("coordenada_lon"),
        })

    for v in loc.get("danos_vivienda") or []:
        db.execute(text("""
            INSERT INTO edan.edan_localidades_danos_vivienda
                (id_edan_localidad, comunidad, dano_parcial, dano_total,
                 necesidades_inmediatas, observaciones,
                 fotografia, coordenada_lat, coordenada_lon)
            VALUES (:id, :comunidad, :dano_parcial, :dano_total,
                    :necesidades_inmediatas, :observaciones,
                    :fotografia, :coordenada_lat, :coordenada_lon)
        """), {
            "id": lid, "comunidad": v.get("comunidad", ""),
            "dano_parcial": v.get("dano_parcial", 0), "dano_total": v.get("dano_total", 0),
            "necesidades_inmediatas": v.get("necesidades_inmediatas", ""),
            "observaciones": v.get("observaciones", ""),
            "fotografia": v.get("fotografia"),
            "coordenada_lat": v.get("coordenada_lat"),
            "coordenada_lon": v.get("coordenada_lon"),
        })

    for a in loc.get("danos_agricultura") or []:
        db.execute(text("""
            INSERT INTO edan.edan_localidades_danos_agricultura
                (id_edan_localidad, tipo_cultivo, id_cultivo,
                 hectareas_afectadas, hectareas_perdidas, necesidades_inmediatas, observaciones,
                 fotografia, coordenada_lat, coordenada_lon)
            VALUES (:id, :tipo_cultivo, :id_cultivo,
                    :hectareas_afectadas, :hectareas_perdidas, :necesidades_inmediatas, :observaciones,
                    :fotografia, :coordenada_lat, :coordenada_lon)
        """), {
            "id": lid, "tipo_cultivo": a.get("tipo_cultivo", ""),
            "id_cultivo": a.get("id_cultivo"),
            "hectareas_afectadas": a.get("hectareas_afectadas", 0),
            "hectareas_perdidas": a.get("hectareas_perdidas", 0),
            "necesidades_inmediatas": a.get("necesidades_inmediatas", ""),
            "observaciones": a.get("observaciones", ""),
            "fotografia": a.get("fotografia"),
            "coordenada_lat": a.get("coordenada_lat"),
            "coordenada_lon": a.get("coordenada_lon"),
        })

    for p in loc.get("danos_pecuarios") or []:
        db.execute(text("""
            INSERT INTO edan.edan_localidades_danos_pecuario
                (id_edan_localidad, especie, id_especie, raza,
                 animales_afectados, animales_muertos, necesidades_inmediatas,
                 fotografia, coordenada_lat, coordenada_lon)
            VALUES (:id, :especie, :id_especie, :raza,
                    :animales_afectados, :animales_muertos, :necesidades_inmediatas,
                    :fotografia, :coordenada_lat, :coordenada_lon)
        """), {
            "id": lid, "especie": p.get("especie", ""),
            "id_especie": p.get("id_especie"), "raza": p.get("raza", ""),
            "animales_afectados": p.get("animales_afectados", 0),
            "animales_muertos": p.get("animales_muertos", 0),
            "necesidades_inmediatas": p.get("necesidades_inmediatas", ""),
            "fotografia": p.get("fotografia"),
            "coordenada_lat": p.get("coordenada_lat"),
            "coordenada_lon": p.get("coordenada_lon"),
        })

    for i in loc.get("infra_productiva") or []:
        db.execute(text("""
            INSERT INTO edan.edan_localidades_infra_productiva
                (id_edan_localidad, tipo, dano_parcial, dano_total,
                 fotografia, coordenada_lat, coordenada_lon)
            VALUES (:id, :tipo, :dano_parcial, :dano_total,
                    :fotografia, :coordenada_lat, :coordenada_lon)
        """), {
            "id": lid, "tipo": i.get("tipo", ""),
            "dano_parcial": i.get("dano_parcial", 0), "dano_total": i.get("dano_total", 0),
            "fotografia": i.get("fotografia") or None,
            "coordenada_lat": i.get("coordenada_lat") or None,
            "coordenada_lon": i.get("coordenada_lon") or None,
        })

    for p in loc.get("proteccion") or []:
        if not isinstance(p, dict):
            continue
        db.execute(text("""
            INSERT INTO edan.edan_localidades_proteccion
                (id_edan_localidad, grupo, mujeres, hombres, total,
                 apoyo_psicologico, reposicion_documentos, observaciones)
            VALUES (:id, :grupo, :mujeres, :hombres, :total,
                    :apoyo_psicologico, :reposicion_documentos, :observaciones)
        """), {
            "id": lid, "grupo": p.get("grupo", ""),
            "mujeres": p.get("mujeres", 0), "hombres": p.get("hombres", 0),
            "total": p.get("total", 0),
            "apoyo_psicologico": p.get("apoyo_psicologico"),
            "reposicion_documentos": p.get("reposicion_documentos"),
            "observaciones": p.get("observaciones", ""),
        })

    nh = loc.get("necesidad_humanitaria")
    if nh:
        cols = ", ".join(_NH_FIELDS)
        ph = ", ".join(f":{k}" for k in _NH_FIELDS)
        db.execute(text(f"""
            INSERT INTO edan.edan_localidades_necesidades_humanitarias
                (id_edan_localidad, {cols}) VALUES (:id, {ph})
        """), {"id": lid, **{k: nh.get(k, False if not k.startswith("obs_") else "") for k in _NH_FIELDS}})


# ============================================================================
#  CREAR ITEM INDIVIDUAL (para endpoints con-foto)
#  Cada función inserta UN solo registro y retorna la fila creada.
#  Usado por POST /localidades/{id}/<tipo>/con-foto.
# ============================================================================

def _insert_single_row(db: Session, table: str, columns: list[str], data: dict) -> dict:
    """Inserta una fila en una tabla de items de daño/servicio y la retorna."""
    cols = ", ".join(columns)
    ph = ", ".join(f":{k}" for k in columns)
    params = {"id": data["_id"]} | {k: data.get(k) for k in columns if k != "id_edan_localidad"}
    result = db.execute(
        text(f"""
            INSERT INTO edan.{table} (id_edan_localidad, {cols})
            VALUES (:id, {ph})
            RETURNING *
        """),
        params,
    ).mappings().first()
    db.commit()
    return dict(result) if result else {}


def create_dano_vial(db: Session, id_localidad: int, data: dict) -> dict:
    data["_id"] = id_localidad
    return _insert_single_row(db, "edan_localidades_danos_viales",
        ["via", "puente", "tramo", "dano_parcial", "dano_total", "km_danio",
         "necesidades_inmediatas", "observaciones", "fotografia",
         "coordenada_lat", "coordenada_lon"], data)


def create_dano_infra_publica(db: Session, id_localidad: int, data: dict) -> dict:
    data["_id"] = id_localidad
    return _insert_single_row(db, "edan_localidades_danos_infra_publica",
        ["comunidad", "tipo_estructura", "dano_parcial", "dano_total", "observaciones",
         "fotografia", "coordenada_lat", "coordenada_lon"], data)


def create_dano_vivienda(db: Session, id_localidad: int, data: dict) -> dict:
    data["_id"] = id_localidad
    return _insert_single_row(db, "edan_localidades_danos_vivienda",
        ["comunidad", "dano_parcial", "dano_total", "necesidades_inmediatas",
         "observaciones", "fotografia", "coordenada_lat", "coordenada_lon"], data)


def create_dano_agricultura(db: Session, id_localidad: int, data: dict) -> dict:
    data["_id"] = id_localidad
    return _insert_single_row(db, "edan_localidades_danos_agricultura",
        ["tipo_cultivo", "id_cultivo", "hectareas_afectadas", "hectareas_perdidas",
         "necesidades_inmediatas", "observaciones", "fotografia",
         "coordenada_lat", "coordenada_lon"], data)


def create_dano_pecuario(db: Session, id_localidad: int, data: dict) -> dict:
    data["_id"] = id_localidad
    return _insert_single_row(db, "edan_localidades_danos_pecuario",
        ["especie", "id_especie", "raza", "animales_afectados", "animales_muertos",
         "necesidades_inmediatas", "fotografia", "coordenada_lat", "coordenada_lon"], data)


def create_establecimiento_salud(db: Session, id_localidad: int, data: dict) -> dict:
    data["_id"] = id_localidad
    return _insert_single_row(db, "edan_localidades_salud_establecimientos",
        ["nombre_establecimiento", "comunidad", "nivel_atencion", "dano_parcial",
         "dano_total", "medicos_afectados", "enfermeras_afectadas", "otros_afectados",
         "fotografia", "coordenada_lat", "coordenada_lon"], data)


def create_servicio_basico(db: Session, id_localidad: int, data: dict) -> dict:
    data["_id"] = id_localidad
    return _insert_single_row(db, "edan_localidades_servicios_basicos",
        ["tipo", "dano_parcial", "dano_total", "necesidades_inmediatas",
         "observaciones", "fotografia", "coordenada_lat", "coordenada_lon"], data)


def create_unidad_educativa(db: Session, id_localidad: int, data: dict) -> dict:
    data["_id"] = id_localidad
    return _insert_single_row(db, "edan_localidades_unidades_educativas",
        ["nombre_establecimiento", "comunidad", "dano_parcial", "dano_total",
         "suspension_clases", "perdida_material", "funciona_albergue",
         "estudiantes", "profesores", "administrativos", "observaciones",
         "fotografia", "coordenada_lat", "coordenada_lon"], data)


def create_infra_productiva(db: Session, id_localidad: int, data: dict) -> dict:
    data["_id"] = id_localidad
    return _insert_single_row(db, "edan_localidades_infra_productiva",
        ["tipo", "dano_parcial", "dano_total", "fotografia",
         "coordenada_lat", "coordenada_lon"], data)


# ============================================================================
#  CRUD PRINCIPAL (transaccional)
# ============================================================================

def _validar_reporte_rea(db: Session, id_reporte_rea):
    """Valida que el REA de origen exista. NULL (sin vínculo) siempre es válido."""
    if id_reporte_rea is None:
        return None
    row = _row(db, "SELECT id_reporte FROM rea.reporte_evento WHERE id_reporte = :id",
               {"id": id_reporte_rea})
    if not row:
        raise HTTPException(status_code=404, detail=f"El reporte REA {id_reporte_rea} no existe")
    return id_reporte_rea


def _sync_reporte_edan(db: Session, id_reporte_rea: int | None, id_edan: int | None,
                       prev_id_reporte_rea: int | None = None):
    """Mantiene el vínculo inverso rea.reporte_evento.id_edan en sincronía con el EDAN.

    - Si el REA cambió o se desvinculó (NULL), se limpia el id_edan del REA anterior.
    - Si hay REA nuevo, se apunta rea.id_edan hacia este EDAN.
    """
    if prev_id_reporte_rea is not None and prev_id_reporte_rea != id_reporte_rea:
        db.execute(text("""
            UPDATE rea.reporte_evento SET id_edan = NULL
            WHERE id_reporte = :id AND id_edan = :id_edan
        """), {"id": prev_id_reporte_rea, "id_edan": id_edan})
    if id_reporte_rea is not None:
        db.execute(text("""
            UPDATE rea.reporte_evento SET id_edan = :id_edan WHERE id_reporte = :id_reporte
        """), {"id_edan": id_edan, "id_reporte": id_reporte_rea})


def create_edan(db: Session, data: dict) -> int:
    _validar_reporte_rea(db, data.get("id_reporte_rea"))
    header = _build_header_payload(db, data)
    cols = ", ".join(header.keys())
    ph = ", ".join(f":{k}" for k in header.keys())
    result = db.execute(text(f"""
        INSERT INTO edan.edan ({cols}) VALUES ({ph}) RETURNING id_edan
    """), header)
    id_edan = result.scalar()
    if data.get("id_reporte_rea"):
        _sync_reporte_edan(db, data["id_reporte_rea"], id_edan)
    for loc in data.get("localidades") or []:
        _insert_localidad(db, id_edan, loc)
    db.commit()
    return id_edan


def update_edan(db: Session, id: int, data: dict) -> dict | None:
    if not get_edan(db, id):
        return None
    prev_rea = (_row(db, "SELECT id_reporte_rea FROM edan.edan WHERE id_edan = :id",
                     {"id": id}) or {}).get("id_reporte_rea")
    resp = data.get("responsable") or {}
    fields = {
        "id_local": data.get("id_local"),
        "codigo_edan": data.get("codigo_edan"),
        "id_usuario_ugr": data.get("id_usuario_ugr"),
        "id_usuario_alcalde": data.get("id_usuario_alcalde"),
        "id_departamento": data.get("id_departamento"),
        "id_provincia": data.get("id_provincia"),
        "id_municipio": data.get("id_municipio"),
        "id_tipo_evento": data.get("id_tipo_evento"),
        "fecha_llenado": data.get("fecha_llenado"),
        "fecha_evento": data.get("fecha_evento"),
        "hora_evento": data.get("hora_evento"),
        "total_poblacion_afectada": data.get("total_poblacion_afectada"),
        "total_familias_afectadas": data.get("total_familias_afectadas"),
        "total_familias_damnificadas": data.get("total_familias_damnificadas"),
        "id_estado": data.get("id_estado"),
        "estado": data.get("estado"),
        "pendiente_eliminacion": data.get("pendiente_eliminacion"),
        "pendiente_actualizacion": data.get("pendiente_actualizacion"),
        "responsable_nombre": resp.get("nombre"),
        "responsable_cargo": resp.get("cargo"),
        "responsable_fono": resp.get("fono"),
        "responsable_correo": resp.get("correo"),
    }
    if data.get("id_municipio") is not None and (data.get("id_departamento") is None or data.get("id_provincia") is None):
        mun = _row(db, "SELECT id, id_provincia, id_departamento, nombre FROM shared.municipio WHERE id = :id",
                   {"id": data["id_municipio"]})
        if mun:
            if fields.get("id_departamento") is None:
                fields["id_departamento"] = mun["id_departamento"]
            if fields.get("id_provincia") is None:
                fields["id_provincia"] = mun["id_provincia"]
    fields = {k: v for k, v in fields.items() if v is not None}
    if not fields:
        return get_edan_completo(db, id)
    fields["id_edan"] = id
    set_clause = ", ".join(f"{k} = :{k}" for k in fields)
    db.execute(text(f"UPDATE edan.edan SET {set_clause}, fecha_modificacion = NOW() WHERE id_edan = :id_edan"), fields)
    if "id_reporte_rea" in data:
        _sync_reporte_edan(db, data.get("id_reporte_rea"), id, prev_rea)
    db.commit()
    return get_edan_completo(db, id)


def delete_edan(db: Session, id: int) -> bool:
    result = db.execute(text("DELETE FROM edan.edan WHERE id_edan = :id"), {"id": id})
    db.commit()
    return result.rowcount > 0


def soft_delete_edan(db: Session, id: int) -> dict | None:
    if not get_edan(db, id):
        return None
    db.execute(text("""
        UPDATE edan.edan SET pendiente_eliminacion = TRUE,
            fecha_modificacion = GREATEST(fecha_modificacion, NOW())
        WHERE id_edan = :id
    """), {"id": id})
    db.commit()
    return get_edan_completo(db, id)


# ============================================================================
#  SINCRONIZACIÓN OFFLINE-FIRST (móvil <-> servidor <-> PC)
# ============================================================================

def _delete_all_localidades(db: Session, id_edan: int):
    db.execute(text("DELETE FROM edan.edan_localidades WHERE id_edan = :id"), {"id": id_edan})


def _replace_localidades(db: Session, id_edan: int, localidades: list):
    """Reemplaza las localidades de un EDAN. Preserva la identidad de sync
    (id_local, id_usuario, estado, fecha) de las que coinciden por id_local,
    para no duplicar registros ni perder el estado al sincronizar repetidamente."""
    prev: dict = {}
    for r in _rows(db, """
        SELECT id_edan_localidad, id_local, id_usuario, id_edan_localidad_estado,
               fecha_modificacion
        FROM edan.edan_localidades WHERE id_edan = :id
    """, {"id": id_edan}):
        if r["id_local"]:
            prev[r["id_local"]] = dict(r)
    _delete_all_localidades(db, id_edan)
    for loc in localidades or []:
        ident = prev.get(loc.get("id_local")) if loc.get("id_local") else None
        if ident:
            if loc.get("id_usuario") is None:
                loc["id_usuario"] = ident["id_usuario"]
            if loc.get("id_edan_localidad_estado") is None:
                loc["id_edan_localidad_estado"] = ident["id_edan_localidad_estado"]
            if loc.get("fecha_modificacion") is None:
                loc["fecha_modificacion"] = ident["fecha_modificacion"]
        _insert_localidad(db, id_edan, loc)


def _parse_fecha(fecha: str | None):
    """Parsea una fecha ISO del cliente. Devuelve SIEMPRE un datetime naive en
    UTC para poder compararlo con las columnas 'timestamp without time zone'
    de PostgreSQL sin lanzar TypeError (aware vs naive)."""
    if not fecha:
        return None
    try:
        dt = datetime.fromisoformat(str(fecha).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _edan_by_id_local(db: Session, id_local: str):
    return _row(db, "SELECT id_edan FROM edan.edan WHERE id_local = :id_local", {"id_local": id_local})


def sync_upsert(db: Session, data: dict, uid: int) -> dict:
    """Push de un EDAN completo. Retorna el documento convergido y flags de sync."""
    id_local = data.get("id_local")
    payload_fecha = _parse_fecha(data.get("fecha_modificacion"))

    if data.get("id_usuario_ugr") is None:
        data["id_usuario_ugr"] = uid

    existing = None
    if id_local:
        existing = _edan_by_id_local(db, id_local)

    # Tombstone (borrado local que debe propagarse). Solo aplica si la versión
    # local no es más antigua que la del servidor.
    if data.get("pendiente_eliminacion"):
        if existing:
            st = _row(db, "SELECT fecha_modificacion FROM edan.edan WHERE id_edan = :id",
                      {"id": existing["id_edan"]})
            server_fecha = _parse_fecha(st["fecha_modificacion"]) if st else None
            if payload_fecha is None or server_fecha is None or payload_fecha >= server_fecha:
                soft_delete_edan(db, existing["id_edan"])
        return {"id_local": id_local, "id_edan": None,
                "aplicado": True, "tombstone": True, "data": None}

    if not existing:
        id_edan = create_edan(db, data)
        db.execute(text("""
            UPDATE edan.edan SET id_local = :id_local
            WHERE id_edan = :id
        """), {"id_local": id_local, "id": id_edan})
        db.commit()
        result = get_edan_completo(db, id_edan)
        return {"id_local": id_local, "id_edan": id_edan,
                "aplicado": True, "conflicto": False, "data": result}

    id_edan = existing["id_edan"]
    row = _row(db, "SELECT fecha_modificacion, pendiente_eliminacion FROM edan.edan WHERE id_edan = :id",
               {"id": id_edan})
    server_fecha = _parse_fecha(row["fecha_modificacion"])

    # Conflicto: el cliente envía la fecha de la última versión que conoce;
    # si es más antigua que la del servidor, su push es una versión atrasada.
    if payload_fecha is not None and server_fecha is not None and payload_fecha < server_fecha:
        result = get_edan_completo(db, id_edan)
        return {"id_local": id_local, "id_edan": id_edan,
                "aplicado": False, "conflicto": True, "data": result}

    update_edan(db, id_edan, data)
    if id_local:
        db.execute(text("UPDATE edan.edan SET id_local = :id_local WHERE id_edan = :id"),
                   {"id_local": id_local, "id": id_edan})
    if data.get("localidades") is not None:
        _replace_localidades(db, id_edan, data["localidades"])
    db.execute(text("""
        UPDATE edan.edan SET pendiente_actualizacion = FALSE,
            pendiente_eliminacion = FALSE
        WHERE id_edan = :id
    """), {"id": id_edan})
    db.commit()
    result = get_edan_completo(db, id_edan)
    return {"id_local": id_local, "id_edan": id_edan,
            "aplicado": True, "conflicto": False, "data": result}


def list_edans_sync(db: Session, id_usuario: int, fecha_desde: str | None = None,
                    skip: int = 0, limit: int = 50):
    conds = ["e.id_usuario_ugr = :uid"]
    params: dict = {"uid": id_usuario}
    if fecha_desde:
        conds.append("e.fecha_modificacion >= :fecha_desde")
        params["fecha_desde"] = fecha_desde
    where = " AND ".join(conds)
    total = db.execute(text(f"SELECT COUNT(*) FROM edan.edan e WHERE {where}"), params).scalar()
    rows = _rows(db, f"""
        {SQL_EDAN}
        WHERE {where} ORDER BY e.fecha_modificacion DESC, e.id_edan DESC
        LIMIT :limit OFFSET :skip
    """, {**params, "limit": limit, "skip": skip})
    data = []
    for r in rows:
        item = _build_edan(r)
        item["localidades"] = _get_localidades(db, item["id_edan"])
        data.append(item)
    return data, total


# ============================================================================
#  SINCRONIZACIÓN DE LOCALIDADES (la localidad es la unidad de reporte)
#  Misma regla simple que el EDAN: última escritura gana, dedupe por id_local.
# ============================================================================

def _localidad_by_id_local(db: Session, id_local: str):
    return _row(db, "SELECT id_edan_localidad FROM edan.edan_localidades WHERE id_local = :id_local",
                {"id_local": id_local})


def localidad_sync_upsert(db: Session, data: dict, uid: int) -> dict:
    """Push de una localidad (reporte de una comunidad). Retorna la localidad
    convergida y flags de sync por ítem (el lote nunca falla completo)."""
    id_local = data.get("id_local")
    payload_fecha = _parse_fecha(data.get("fecha_modificacion"))

    existing = _localidad_by_id_local(db, id_local) if id_local else None

    # Tombstone: borrado local que se propaga (eliminación física en servidor)
    if data.get("pendiente_eliminacion"):
        if existing:
            db.execute(text("DELETE FROM edan.edan_localidades WHERE id_edan_localidad = :id"),
                       {"id": existing["id_edan_localidad"]})
            db.commit()
        return {"id_local": id_local, "id_edan_localidad": None,
                "aplicado": True, "tombstone": True, "data": None}

    if not existing:
        lid = _insert_localidad(db, None, data)
        db.execute(text("""
            UPDATE edan.edan_localidades SET id_local = :id_local
            WHERE id_edan_localidad = :id
        """), {"id_local": id_local, "id": lid})
        db.commit()
        result = _build_localidad(db, lid)
        return {"id_local": id_local, "id_edan_localidad": lid,
                "aplicado": True, "conflicto": False, "data": result}

    lid = existing["id_edan_localidad"]
    row = _row(db, "SELECT fecha_modificacion FROM edan.edan_localidades WHERE id_edan_localidad = :id",
               {"id": lid})
    server_fecha = _parse_fecha(row["fecha_modificacion"])

    if payload_fecha is not None and server_fecha is not None and payload_fecha < server_fecha:
        result = _build_localidad(db, lid)
        return {"id_local": id_local, "id_edan_localidad": lid,
                "aplicado": False, "conflicto": True, "data": result}

    # Preserva el estado decidido por el UGR si el payload no lo trae
    if data.get("id_edan_localidad_estado") is None:
        st = _row(db, "SELECT id_edan_localidad_estado FROM edan.edan_localidades"
                      " WHERE id_edan_localidad = :id", {"id": lid})
        data["id_edan_localidad_estado"] = st["id_edan_localidad_estado"] if st else None

    update_localidad(db, lid, data)
    db.execute(text("""
        UPDATE edan.edan_localidades SET pendiente_actualizacion = FALSE,
            pendiente_eliminacion = FALSE
        WHERE id_edan_localidad = :id
    """), {"id": lid})
    db.commit()
    result = _build_localidad(db, lid)
    return {"id_local": id_local, "id_edan_localidad": lid,
            "aplicado": True, "conflicto": False, "data": result}


def list_localidades_sync(db: Session, id_usuario: int, fecha_desde: str | None = None,
                          skip: int = 0, limit: int = 50):
    """Pull para el móvil: sus propias localidades (incluye cambios de estado
    hechos por el UGR y tombstones para borrar localmente)."""
    conds = ["l.id_usuario = :uid"]
    params: dict = {"uid": id_usuario}
    if fecha_desde:
        conds.append("l.fecha_modificacion >= :fecha_desde")
        params["fecha_desde"] = fecha_desde
    where = " AND ".join(conds)
    total = db.execute(text(f"SELECT COUNT(*) FROM edan.edan_localidades l WHERE {where}"), params).scalar()
    rows = _rows(db, f"""
        SELECT id_edan_localidad FROM edan.edan_localidades l
        WHERE {where} ORDER BY l.fecha_modificacion DESC, l.id_edan_localidad DESC
        LIMIT :limit OFFSET :skip
    """, {**params, "limit": limit, "skip": skip})
    return [_build_localidad(db, r["id_edan_localidad"]) for r in rows], total


# ============================================================================
#  ESTADO DE LOCALIDAD Y CONSOLIDACIÓN
# ============================================================================

def cambiar_estado_localidad(db: Session, id_localidad: int, id_estado: int) -> dict | None:
    """Cambia el estado de una localidad (borrador/enviado/aprobado/rechazado/cerrado).
    Estados libres: la API no impone transiciones (el frontend las gestiona)."""
    st = _row(db, "SELECT id_edan_localidad_estado FROM edan.edan_localidades_estado"
                  " WHERE id_edan_localidad_estado = :id", {"id": id_estado})
    if not st:
        raise HTTPException(status_code=404, detail="Estado de localidad no encontrado")
    cur = _row(db, "SELECT id_edan FROM edan.edan_localidades WHERE id_edan_localidad = :id",
               {"id": id_localidad})
    if not cur:
        return None
    db.execute(text("""
        UPDATE edan.edan_localidades SET id_edan_localidad_estado = :est,
            fecha_modificacion = NOW(), pendiente_actualizacion = TRUE
        WHERE id_edan_localidad = :id
    """), {"est": id_estado, "id": id_localidad})
    if cur["id_edan"] is not None:
        _bump_edan_fecha(db, cur["id_edan"])
    db.commit()
    return _build_localidad(db, id_localidad)


def cambiar_estado_edan(db: Session, id_edan: int, id_estado: int) -> dict | None:
    """Cambia SOLO el campo id_estado (estado_edan) de un EDAN consolidado.
    Acceso abierto para roles 1-5, 9 (admin y roles superiores).
    Roles 6, 7, 8 NO pueden modificar este campo."""
    st = _row(db, "SELECT id_estado, nombre FROM edan.estado_edan WHERE id_estado = :id",
              {"id": id_estado})
    if not st:
        raise HTTPException(status_code=404, detail="Estado EDAN no encontrado")
    cur = _row(db, "SELECT id_edan FROM edan.edan WHERE id_edan = :id", {"id": id_edan})
    if not cur:
        return None
    db.execute(text("""
        UPDATE edan.edan SET id_estado = :id_estado,
            fecha_modificacion = NOW()
        WHERE id_edan = :id
    """), {"id_estado": id_estado, "id": id_edan})
    db.commit()
    return get_edan(db, id_edan)


def listar_consolidables(db: Session, id_municipio: int | None = None,
                         estado_nombre: str = "aprobado"):
    """Localidades aprobadas sin EDAN, agrupadas por (tipo_evento, municipio),
    listas para consolidar."""
    conds = ["l.id_edan IS NULL"]
    params: dict = {}
    if id_municipio is not None:
        conds.append("l.id_municipio = :id_municipio")
        params["id_municipio"] = id_municipio
    if estado_nombre:
        conds.append("""l.id_edan_localidad_estado IN (
            SELECT id_edan_localidad_estado FROM edan.edan_localidades_estado
            WHERE nombre = :estado_nombre
        )""")
        params["estado_nombre"] = estado_nombre
    where = " AND ".join(conds)
    rows = _rows(db, f"""
        SELECT l.id_municipio, m.nombre AS municipio_nombre,
               d.id AS id_departamento, d.nombre AS departamento_nombre,
               p.id AS id_provincia, p.nombre AS provincia_nombre,
               l.id_tipo_evento, te.nombre AS tipo_evento_nombre,
               COUNT(*) AS cantidad_localidades,
               ARRAY_AGG(l.id_edan_localidad ORDER BY l.id_edan_localidad) AS localidad_ids,
               COALESCE(SUM(l.total_poblacion_afectada), 0) AS total_poblacion_afectada,
               COALESCE(SUM(l.total_familias_afectadas), 0) AS total_familias_afectadas,
               COALESCE(SUM(l.total_familias_damnificadas), 0) AS total_familias_damnificadas,
               MIN(l.fecha_evento) AS fecha_evento
        FROM edan.edan_localidades l
        LEFT JOIN shared.municipio m ON m.id = l.id_municipio
        LEFT JOIN shared.departamento d ON d.id = l.id_departamento
        LEFT JOIN shared.provincia p ON p.id = l.id_provincia
        LEFT JOIN edan.tipo_evento te ON te.id_tipo_evento = l.id_tipo_evento
        WHERE {where}
        GROUP BY l.id_municipio, m.nombre, d.id, d.nombre, p.id, p.nombre,
                 l.id_tipo_evento, te.nombre
        ORDER BY te.nombre, m.nombre
    """, params)
    return [dict(r) for r in rows]


def _next_codigo_edan(db: Session, id_municipio: int) -> str:
    year = datetime.now().year
    prefix = f"{id_municipio:06d}/{year}/"
    row = _row(db, """
        SELECT codigo_edan FROM edan.edan
        WHERE codigo_edan LIKE :prefix || '%'
        ORDER BY codigo_edan DESC LIMIT 1
    """, {"prefix": prefix})
    if not row or not row["codigo_edan"]:
        return f"{prefix}001"
    seq_str = str(row["codigo_edan"]).split("/")[-1]
    seq = int(seq_str) if seq_str.isdigit() else 0
    return f"{prefix}{seq + 1:03d}"


def consolidar(db: Session, id_municipio: int, id_tipo_evento: int,
               localidad_ids: list[int], id_usuario: int) -> dict:
    """Consolida localidades aprobadas en un EDAN (borrador, editable por el UGR).
    La cabecera se agrega desde las localidades: geografía común, fecha/hora del
    evento y totales = SUMA. Operación atómica."""
    if not localidad_ids:
        raise HTTPException(status_code=400, detail="Debe incluir al menos una localidad")
    ids = list(dict.fromkeys(localidad_ids))
    ph = ", ".join(f":id_{i}" for i in range(len(ids)))
    params = {f"id_{i}": v for i, v in enumerate(ids)}
    params["mun"] = id_municipio
    params["ev"] = id_tipo_evento

    ok = _rows(db, f"""
        SELECT id_edan_localidad FROM edan.edan_localidades
        WHERE id_edan_localidad IN ({ph})
          AND id_edan IS NULL
          AND id_municipio = :mun AND id_tipo_evento = :ev
          AND id_edan_localidad_estado IN (
              SELECT id_edan_localidad_estado FROM edan.edan_localidades_estado
              WHERE nombre = 'aprobado'
          )
    """, params)
    if len(ok) != len(ids):
        raise HTTPException(
            status_code=400,
            detail="Algunas localidades no son consolidables: deben estar aprobadas, sin EDAN y del mismo municipio/tipo de evento",
        )

    agg = _row(db, f"""
        SELECT id_departamento, id_provincia, id_municipio, id_tipo_evento,
               MIN(fecha_evento) AS fecha_evento, MIN(hora_evento) AS hora_evento,
               COALESCE(SUM(total_poblacion_afectada), 0) AS total_poblacion_afectada,
               COALESCE(SUM(total_familias_afectadas), 0) AS total_familias_afectadas,
               COALESCE(SUM(total_familias_damnificadas), 0) AS total_familias_damnificadas
        FROM edan.edan_localidades
        WHERE id_edan_localidad IN ({ph})
        GROUP BY id_departamento, id_provincia, id_municipio, id_tipo_evento
    """, params)
    if not agg:
        raise HTTPException(status_code=400, detail="No hay localidades válidas para consolidar")

    id_edan = db.execute(text("""
        INSERT INTO edan.edan (codigo_edan, id_departamento, id_provincia, id_municipio,
            id_tipo_evento, fecha_llenado, fecha_evento, hora_evento,
            total_poblacion_afectada, total_familias_afectadas,
            total_familias_damnificadas, id_usuario_ugr, id_estado, estado)
        VALUES (:codigo_edan, :id_departamento, :id_provincia, :id_municipio,
            :id_tipo_evento, :fecha_llenado, :fecha_evento, :hora_evento,
            :total_poblacion_afectada, :total_familias_afectadas,
            :total_familias_damnificadas, :id_usuario_ugr, :id_estado, :estado)
        RETURNING id_edan
    """), {
        "codigo_edan": _next_codigo_edan(db, id_municipio),
        "id_departamento": agg["id_departamento"],
        "id_provincia": agg["id_provincia"],
        "id_municipio": agg["id_municipio"],
        "id_tipo_evento": agg["id_tipo_evento"],
        "fecha_llenado": datetime.now().date(),
        "fecha_evento": agg["fecha_evento"],
        "hora_evento": agg["hora_evento"],
        "total_poblacion_afectada": agg["total_poblacion_afectada"],
        "total_familias_afectadas": agg["total_familias_afectadas"],
        "total_familias_damnificadas": agg["total_familias_damnificadas"],
        "id_usuario_ugr": id_usuario,
        "id_estado": 1,
        "estado": "borrador",
    }).scalar()
    db.execute(text(f"""
        UPDATE edan.edan_localidades SET id_edan = :id_edan,
            fecha_modificacion = NOW(), pendiente_actualizacion = TRUE
        WHERE id_edan_localidad IN ({ph})
    """), {**params, "id_edan": id_edan})
    db.commit()
    return get_edan_completo(db, id_edan)

ALLOWED_ORDER = {
    "id_edan", "codigo_edan", "fecha_evento", "fecha_creacion",
    "fecha_modificacion", "total_poblacion_afectada", "id_departamento",
    "id_municipio", "estado",
}

IMP_FLAGS = [
    "imp_poblacion", "imp_salud", "imp_infraestructura", "imp_servicios",
    "imp_educacion", "imp_vivienda", "imp_agropecuario", "imp_proteccion",
    "imp_necesidades",
]


def _filters(f: dict, alias: str = "e") -> tuple[list[str], dict]:
    conds: list[str] = []
    params: dict = {}
    a = alias

    if f.get("id_departamento") is not None:
        conds.append(f"{a}.id_departamento = :id_departamento")
        params["id_departamento"] = f["id_departamento"]
    if f.get("id_provincia") is not None:
        conds.append(f"{a}.id_provincia = :id_provincia")
        params["id_provincia"] = f["id_provincia"]
    if f.get("id_municipio") is not None:
        conds.append(f"{a}.id_municipio = :id_municipio")
        params["id_municipio"] = f["id_municipio"]
    if f.get("id_tipo_evento") is not None:
        conds.append(f"{a}.id_tipo_evento = :id_tipo_evento")
        params["id_tipo_evento"] = f["id_tipo_evento"]
    if f.get("id_estado") is not None:
        conds.append(f"{a}.id_estado = :id_estado")
        params["id_estado"] = f["id_estado"]
    if f.get("estado"):
        conds.append(f"LOWER({a}.estado) = LOWER(:estado)")
        params["estado"] = f["estado"]
    if f.get("id_usuario_ugr") is not None:
        conds.append(f"{a}.id_usuario_ugr = :id_usuario_ugr")
        params["id_usuario_ugr"] = f["id_usuario_ugr"]

    if f.get("fecha_evento_desde"):
        conds.append(f"{a}.fecha_evento >= :fecha_evento_desde")
        params["fecha_evento_desde"] = f["fecha_evento_desde"]
    if f.get("fecha_evento_hasta"):
        conds.append(f"{a}.fecha_evento <= :fecha_evento_hasta")
        params["fecha_evento_hasta"] = f["fecha_evento_hasta"]
    if f.get("fecha_creacion_desde"):
        conds.append(f"{a}.fecha_creacion >= :fecha_creacion_desde")
        params["fecha_creacion_desde"] = f["fecha_creacion_desde"]
    if f.get("fecha_creacion_hasta"):
        conds.append(f"{a}.fecha_creacion <= :fecha_creacion_hasta")
        params["fecha_creacion_hasta"] = f["fecha_creacion_hasta"]

    for flag in ("pendiente_eliminacion", "pendiente_actualizacion"):
        if f.get(flag) is not None:
            conds.append(f"{a}.{flag} = :{flag}")
            params[flag] = f[flag]

    if f.get("con_foto"):
        conds.append(f"{a}.fotografia IS NOT NULL AND {a}.fotografia <> ''")
    if f.get("sin_foto"):
        conds.append(f"({a}.fotografia IS NULL OR {a}.fotografia = '')")

    if f.get("q"):
        conds.append(f"""(
            {a}.codigo_edan ILIKE :q OR EXISTS (
                SELECT 1 FROM edan.edan_localidades lq
                WHERE lq.id_edan = {a}.id_edan AND lq.localidad ILIKE :q
            )
        )""")
        params["q"] = f"%{f['q']}%"

    for flag in IMP_FLAGS:
        if f.get(flag):
            conds.append(f"""EXISTS (
                SELECT 1 FROM edan.edan_localidades li
                WHERE li.id_edan = {a}.id_edan AND li.{flag} = TRUE
            )""")

    if f.get("tiene_agricultura"):
        conds.append(f"""EXISTS (
            SELECT 1 FROM edan.edan_localidades la
            JOIN edan.edan_localidades_danos_agricultura ag
                ON ag.id_edan_localidad = la.id_edan_localidad
            WHERE la.id_edan = {a}.id_edan
        )""")
    if f.get("tiene_pecuario"):
        conds.append(f"""EXISTS (
            SELECT 1 FROM edan.edan_localidades lp
            JOIN edan.edan_localidades_danos_pecuario dp
                ON dp.id_edan_localidad = lp.id_edan_localidad
            WHERE lp.id_edan = {a}.id_edan
        )""")

    return conds, params


def _order_clause(f: dict) -> str:
    order_by = f.get("order_by") or "id_edan"
    if order_by not in ALLOWED_ORDER:
        order_by = "id_edan"
    direction = "ASC" if str(f.get("order", "desc")).lower() == "asc" else "DESC"
    return f"ORDER BY e.{order_by} {direction}"


def get_edans(db: Session, f: dict | None = None, skip: int = 0, limit: int = 50):
    f = f or {}
    conds, params = _filters(f)
    where = " WHERE " + " AND ".join(conds) if conds else ""
    total = db.execute(text(f"SELECT COUNT(*) FROM edan.edan e{where}"), params).scalar()
    query = SQL_EDAN + where + " " + _order_clause(f) + " LIMIT :limit OFFSET :skip"
    params = dict(params)
    params["limit"] = limit
    params["skip"] = skip
    rows = _rows(db, query, params)
    data = []
    for r in rows:
        item = _build_edan(r)
        item["localidades"] = _get_localidades(db, item["id_edan"])
        data.append(item)
    return data, total


# ============================================================================
#  MIS REPORTES (por usuario, patrón REA)
# ============================================================================

def get_mis_resumen_edan(db: Session, id_usuario: int):
    return reporte_resumen(db, {"id_usuario_ugr": id_usuario})


def get_mis_edans(db: Session, id_usuario: int, skip: int = 0, limit: int = 50):
    total = db.execute(
        text("SELECT COUNT(*) FROM edan.edan WHERE id_usuario_ugr = :uid"),
        {"uid": id_usuario},
    ).scalar()
    rows = _rows(db, f"""
        {SQL_EDAN}
        WHERE e.id_usuario_ugr = :uid ORDER BY e.id_edan DESC LIMIT :limit OFFSET :skip
    """, {"uid": id_usuario, "limit": limit, "skip": skip})
    data = []
    for r in rows:
        item = _build_edan(r)
        item["localidades"] = _get_localidades(db, item["id_edan"])
        data.append(item)
    return data, total


def get_mis_localidades_resumen(db: Session, id_usuario: int):
    """Resumen de TODAS las localidades del usuario (huérfanas + consolidadas).

    Permite que un usuario con rol 7 (responsable local) o 6 (UGR) recupere
    sus localidades tras perder el celular: si ya consolidó, también las ve.
    """
    row = _row(db, """
        SELECT COUNT(*) AS total_localidades,
               COUNT(*) FILTER (WHERE id_edan IS NULL) AS total_huerfanas,
               COUNT(*) FILTER (WHERE id_edan IS NOT NULL) AS total_consolidadas,
               COALESCE(SUM(total_poblacion_afectada), 0) AS total_poblacion,
               COALESCE(SUM(total_familias_afectadas), 0) AS total_familias,
               COALESCE(SUM(total_familias_damnificadas), 0) AS total_familias_damnificadas,
               COUNT(*) FILTER (WHERE id_edan_localidad_estado IS NOT NULL) AS total_con_estado,
               COUNT(*) FILTER (WHERE id_edan IS NULL AND id_edan_localidad_estado IS NOT NULL)
                   AS total_huerfanas_con_estado,
               COUNT(*) FILTER (WHERE id_edan IS NOT NULL AND id_edan_localidad_estado IS NOT NULL)
                   AS total_consolidadas_con_estado
        FROM edan.edan_localidades
        WHERE id_usuario = :uid
    """, {"uid": id_usuario})
    return dict(row) if row else {}


def get_mis_localidades(db: Session, id_usuario: int, skip: int = 0, limit: int = 50,
                       solo_huerfanas: bool | None = None):
    """Lista TODAS las localidades del usuario (huérfanas + consolidadas).

    Args:
        id_usuario: Usuario solicitante.
        skip/limit: Paginación.
        solo_huerfanas: Si True, solo id_edan IS NULL. Si False, solo consolidadas.
                        Si None, devuelve todas.
    """
    where_extra = ""
    if solo_huerfanas is True:
        where_extra = "AND l.id_edan IS NULL"
    elif solo_huerfanas is False:
        where_extra = "AND l.id_edan IS NOT NULL"

    total = db.execute(text(f"""
        SELECT COUNT(*) FROM edan.edan_localidades l
        WHERE l.id_usuario = :uid {where_extra}
    """), {"uid": id_usuario}).scalar()
    rows = _rows(db, f"""
        SELECT l.*,
               te.nombre AS tipo_evento_nombre,
               ele.nombre AS estado_localidad_nombre,
               d.nombre AS departamento_nombre,
               p.nombre AS provincia_nombre,
               m.nombre AS municipio_nombre,
               e.id_edan AS edan_id, e.codigo_edan, e.id_estado AS edan_id_estado,
               es_e.nombre AS edan_estado_nombre
        FROM edan.edan_localidades l
        LEFT JOIN edan.tipo_evento te ON te.id_tipo_evento = l.id_tipo_evento
        LEFT JOIN edan.edan_localidades_estado ele ON ele.id_edan_localidad_estado = l.id_edan_localidad_estado
        LEFT JOIN shared.departamento d ON d.id = l.id_departamento
        LEFT JOIN shared.provincia p ON p.id = l.id_provincia
        LEFT JOIN shared.municipio m ON m.id = l.id_municipio
        LEFT JOIN edan.edan e ON e.id_edan = l.id_edan
        LEFT JOIN edan.estado_edan es_e ON es_e.id_estado = e.id_estado
        WHERE l.id_usuario = :uid {where_extra}
        ORDER BY l.fecha_modificacion DESC NULLS LAST, l.id_edan_localidad DESC
        LIMIT :limit OFFSET :skip
    """, {"uid": id_usuario, "limit": limit, "skip": skip})
    return [_build_localidad(db, r["id_edan_localidad"]) for r in rows], total


# ============================================================================
#  REPORTES AGREGADOS
# ============================================================================

def _reporte_where(f: dict) -> tuple[str, dict]:
    conds, params = _filters(f, alias="e")
    return (" WHERE " + " AND ".join(conds) if conds else ""), params


def reporte_resumen(db: Session, f: dict | None = None):
    f = f or {}
    where, params = _reporte_where(f)
    total = db.execute(text(f"""
        SELECT COUNT(*) AS total_edans,
               COALESCE(SUM(e.total_poblacion_afectada), 0) AS total_poblacion,
               COALESCE(SUM(e.total_familias_afectadas), 0) AS total_familias_afectadas,
               COALESCE(SUM(e.total_familias_damnificadas), 0) AS total_familias_damnificadas
        FROM edan.edan e{where}
    """), params).mappings().first()
    total_localidades = db.execute(text(f"""
        SELECT COUNT(*) FROM edan.edan_localidades l
        JOIN edan.edan e ON e.id_edan = l.id_edan{where}
    """), params).scalar()

    por_estado = [dict(r) for r in _rows(db, f"""
        SELECT e.estado, e.id_estado, COUNT(*) AS cantidad
        FROM edan.edan e{where} GROUP BY e.id_estado, e.estado ORDER BY cantidad DESC
    """, params)]

    por_tipo_evento = [dict(r) for r in _rows(db, f"""
        SELECT e.id_tipo_evento,
               COALESCE(te.nombre, 'Sin tipo') AS tipo_evento,
               COUNT(*) AS cantidad
        FROM edan.edan e{where}
        LEFT JOIN edan.tipo_evento te ON te.id_tipo_evento = e.id_tipo_evento
        GROUP BY e.id_tipo_evento, te.nombre ORDER BY cantidad DESC
    """, params)]

    return {
        "totales": {
            "total_edans": total["total_edans"],
            "total_localidades": total_localidades,
            "total_poblacion_afectada": total["total_poblacion"],
            "total_familias_afectadas": total["total_familias_afectadas"],
            "total_familias_damnificadas": total["total_familias_damnificadas"],
        },
        "por_estado": por_estado,
        "por_tipo_evento": por_tipo_evento,
    }


def reporte_geografico(db: Session, f: dict | None = None):
    f = f or {}
    where, params = _reporte_where(f)
    rows = _rows(db, f"""
        SELECT d.id AS id_departamento, d.nombre AS departamento,
               p.id AS id_provincia, p.nombre AS provincia,
               m.id AS id_municipio, m.nombre AS municipio,
               COUNT(*) AS total_edans,
               COALESCE(SUM(e.total_poblacion_afectada), 0) AS poblacion_afectada,
               COALESCE(SUM(e.total_familias_afectadas), 0) AS familias_afectadas,
               COALESCE(SUM(e.total_familias_damnificadas), 0) AS familias_damnificadas
        FROM edan.edan e
        LEFT JOIN shared.departamento d ON e.id_departamento = d.id
        LEFT JOIN shared.provincia p ON e.id_provincia = p.id
        LEFT JOIN shared.municipio m ON e.id_municipio = m.id
        {where}
        GROUP BY d.id, d.nombre, p.id, p.nombre, m.id, m.nombre
        ORDER BY d.nombre, p.nombre, m.nombre
    """, params)
    return [dict(r) for r in rows]


def reporte_agricultura(db: Session, f: dict | None = None):
    f = f or {}
    where, params = _reporte_where(f)
    rows = _rows(db, f"""
        SELECT a.tipo_cultivo,
               a.id_cultivo,
               c.nombre AS cultivo_nombre,
               c.grupo AS cultivo_grupo,
               COUNT(*) AS total_registros,
               COUNT(DISTINCT e.id_edan) AS total_edans,
               COALESCE(SUM(a.hectareas_afectadas), 0) AS hectareas_afectadas,
               COALESCE(SUM(a.hectareas_perdidas), 0) AS hectareas_perdidas
        FROM edan.edan_localidades_danos_agricultura a
        JOIN edan.edan_localidades l ON l.id_edan_localidad = a.id_edan_localidad
        JOIN edan.edan e ON e.id_edan = l.id_edan
        LEFT JOIN shared.cultivo c ON c.id = a.id_cultivo
        {where}
        GROUP BY a.tipo_cultivo, a.id_cultivo, c.nombre, c.grupo
        ORDER BY hectareas_afectadas DESC
    """, params)
    return [dict(r) for r in rows]


def reporte_pecuario(db: Session, f: dict | None = None):
    f = f or {}
    where, params = _reporte_where(f)
    rows = _rows(db, f"""
        SELECT a.especie,
               a.id_especie,
               p.nombre AS especie_catalogo,
               p.grupo AS especie_grupo,
               COUNT(*) AS total_registros,
               COUNT(DISTINCT e.id_edan) AS total_edans,
               COALESCE(SUM(a.animales_afectados), 0) AS animales_afectados,
               COALESCE(SUM(a.animales_muertos), 0) AS animales_muertos
        FROM edan.edan_localidades_danos_pecuario a
        JOIN edan.edan_localidades l ON l.id_edan_localidad = a.id_edan_localidad
        JOIN edan.edan e ON e.id_edan = l.id_edan
        LEFT JOIN shared.pecuario p ON p.id = a.id_especie
        {where}
        GROUP BY a.especie, a.id_especie, p.nombre, p.grupo
        ORDER BY animales_afectados DESC
    """, params)
    return [dict(r) for r in rows]


def reporte_localidades(db: Session, f: dict | None = None, skip: int = 0, limit: int = 200):
    f = f or {}
    conds, params = _filters(f, alias="e")
    where = " WHERE " + " AND ".join(conds) if conds else ""
    total = db.execute(text(f"""
        SELECT COUNT(*) FROM edan.edan_localidades l
        JOIN edan.edan e ON e.id_edan = l.id_edan{where}
    """), params).scalar()
    rows = _rows(db, f"""
        SELECT e.id_edan, e.codigo_edan, e.estado,
               d.nombre AS departamento, p.nombre AS provincia, m.nombre AS municipio,
               l.id_edan_localidad, t.nombre AS tipo_localidad,
               es.nombre AS estado_localidad, l.localidad AS localidad,
               l.imp_poblacion, l.imp_salud, l.imp_infraestructura, l.imp_servicios,
               l.imp_educacion, l.imp_vivienda, l.imp_agropecuario, l.imp_proteccion, l.imp_necesidades
        FROM edan.edan_localidades l
        JOIN edan.edan e ON e.id_edan = l.id_edan
        LEFT JOIN edan.tipo_localidad t ON t.id_tipo_localidad = l.id_tipo_localidad
        LEFT JOIN edan.edan_localidades_estado es
               ON es.id_edan_localidad_estado = l.id_edan_localidad_estado
        LEFT JOIN shared.departamento d ON e.id_departamento = d.id
        LEFT JOIN shared.provincia p ON e.id_provincia = p.id
        LEFT JOIN shared.municipio m ON e.id_municipio = m.id
        {where}
        ORDER BY e.id_edan DESC, l.id_edan_localidad
        LIMIT :limit OFFSET :skip
    """, {**params, "limit": limit, "skip": skip})
    return [dict(r) for r in rows], total


# ============================================================================
#  CATÁLOGOS GENÉRICOS
# ============================================================================

def _catalog_crud(table: str, pk: str, order_col: str | None = None):
    def get_all(db: Session):
        order = order_col or pk
        rows = db.execute(text(f"SELECT * FROM edan.{table} ORDER BY {order}, {pk}")).mappings().all()
        return [dict(r) for r in rows]

    def get_one(db: Session, id: int):
        row = db.execute(text(f"SELECT * FROM edan.{table} WHERE {pk} = :id"), {"id": id}).mappings().first()
        return dict(row) if row else None

    def create(db: Session, data: dict) -> int:
        cols = ", ".join(data.keys())
        vals = ", ".join(f":{k}" for k in data.keys())
        result = db.execute(text(f"INSERT INTO edan.{table} ({cols}) VALUES ({vals}) RETURNING {pk}"), data)
        db.commit()
        return result.scalar()

    def update(db: Session, id: int, data: dict) -> dict | None:
        fields = {k: v for k, v in data.items() if v is not None}
        if not fields:
            return get_one(db, id)
        set_clause = ", ".join(f"{k} = :{k}" for k in fields)
        params = {**fields, "pk": id}
        db.execute(text(f"UPDATE edan.{table} SET {set_clause} WHERE {pk} = :pk"), params)
        db.commit()
        return get_one(db, id)

    def delete(db: Session, id: int) -> bool:
        result = db.execute(text(f"DELETE FROM edan.{table} WHERE {pk} = :id"), {"id": id})
        db.commit()
        return result.rowcount > 0

    return get_all, get_one, create, update, delete


tipo_evento_crud = _catalog_crud("tipo_evento", "id_tipo_evento")
estado_edan_crud = _catalog_crud("estado_edan", "id_estado")
tipo_localidad_crud = _catalog_crud("tipo_localidad", "id_tipo_localidad", order_col="orden")
edan_localidades_estado_crud = _catalog_crud("edan_localidades_estado", "id_edan_localidad_estado", order_col="orden")
