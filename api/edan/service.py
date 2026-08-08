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
           u.id_usuario as u_id, u.usuario as u_usuario, u.nombre as u_nombre,
           (SELECT COUNT(*) FROM edan.edan_localidades lc
             WHERE lc.id_edan = e.id_edan) AS num_localidades
    FROM edan.edan e
    LEFT JOIN shared.departamento d ON e.id_departamento = d.id
    LEFT JOIN shared.provincia p ON e.id_provincia = p.id
    LEFT JOIN shared.municipio m ON e.id_municipio = m.id
    LEFT JOIN edan.tipo_evento te ON e.id_tipo_evento = te.id_tipo_evento
    LEFT JOIN edan.estado_edan es ON e.id_estado = es.id_estado
    LEFT JOIN usuarios.usuario u ON e.id_usuario = u.id_usuario
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
    data["usuario"] = {
        "id_usuario": data.pop("u_id"),
        "usuario": data.pop("u_usuario"),
        "nombre": data.pop("u_nombre"),
    } if data.get("u_id") else None
    data["responsable"] = {
        "nombre": data.pop("responsable_nombre", None) or "",
        "cargo": data.pop("responsable_cargo", None) or "",
        "fono": data.pop("responsable_fono", None) or "",
        "correo": data.pop("responsable_correo", None) or "",
    }
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


def _lookup_nombre(db: Session, table: str, pk: str, id) -> str | None:
    if id is None:
        return None
    row = _row(db, f"SELECT {pk}, nombre FROM shared.{table} WHERE {pk} = :id", {"id": id})
    return row["nombre"] if row else None


def _build_header_payload(db: Session, data: dict) -> dict:
    header = {
        "codigo_edan": data.get("codigo_edan"),
        "id_server": data.get("id_server"),
        "id_usuario": data.get("id_usuario"),
        "id_departamento": data.get("id_departamento"),
        "id_provincia": data.get("id_provincia"),
        "id_municipio": data.get("id_municipio"),
        "id_tipo_evento": data.get("id_tipo_evento"),
        "nombre_alcalde": data.get("nombre_alcalde", ""),
        "fono_alcalde": data.get("fono_alcalde", ""),
        "fecha_llenado": data.get("fecha_llenado") or None,
        "fecha_evento": data.get("fecha_evento") or None,
        "hora_evento": data.get("hora_evento") or None,
        "total_poblacion_afectada": data.get("total_poblacion_afectada", 0),
        "total_familias_afectadas": data.get("total_familias_afectadas", 0),
        "total_familias_damnificadas": data.get("total_familias_damnificadas", 0),
        "id_estado": data.get("id_estado", 1),
        "estado": data.get("estado", "borrador"),
        "sincronizado": data.get("sincronizado", False),
        "pendiente_eliminacion": data.get("pendiente_eliminacion", False),
        "pendiente_actualizacion": data.get("pendiente_actualizacion", False),
        "es_borrador": data.get("es_borrador", False),
        "id_reporte_rea": data.get("id_reporte_rea"),
        "fotografia": data.get("fotografia"),
    }
    resp = data.get("responsable") or {}
    header["responsable_nombre"] = resp.get("nombre") or ""
    header["responsable_cargo"] = resp.get("cargo") or ""
    header["responsable_fono"] = resp.get("fono") or ""
    header["responsable_correo"] = resp.get("correo") or ""

    if header["id_estado"]:
        st = _row(db, "SELECT id_estado, nombre FROM edan.estado_edan WHERE id_estado = :id",
                  {"id": header["id_estado"]})
        if st:
            if not header.get("estado"):
                header["estado"] = st["nombre"]
            header["es_borrador"] = st["nombre"] == "borrador"

    if header["id_municipio"] and not (header["id_provincia"] and header["id_departamento"]):
        mun = _row(db, "SELECT id, id_provincia, id_departamento, nombre FROM shared.municipio WHERE id = :id",
                   {"id": header["id_municipio"]})
        if mun:
            header["id_provincia"] = header["id_provincia"] or mun["id_provincia"]
            header["id_departamento"] = header["id_departamento"] or mun["id_departamento"]

    header["departamento_nombre"] = (
        data.get("departamento_nombre")
        or _lookup_nombre(db, "departamento", "id", header["id_departamento"])
    )
    header["provincia_nombre"] = (
        data.get("provincia_nombre")
        or _lookup_nombre(db, "provincia", "id", header["id_provincia"])
    )
    header["municipio_nombre"] = (
        data.get("municipio_nombre")
        or _lookup_nombre(db, "municipio", "id", header["id_municipio"])
    )
    if header["id_tipo_evento"]:
        te = _row(db, "SELECT id_tipo_evento, nombre FROM edan.tipo_evento WHERE id_tipo_evento = :id",
                  {"id": header["id_tipo_evento"]})
        header["tipo_evento_nombre"] = te["nombre"] if te else None
    else:
        header["tipo_evento_nombre"] = None
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


def _grupo_etario_detalle(db, id_localidad):
    return _all(db, "edan_grupo_etario_detalle", id_localidad,
                "ORDER BY id_grupo_etario_detalle")


def _servicios_basicos(db, id_localidad):
    return _all(db, "edan_localidades_servicios_basicos", id_localidad,
                "ORDER BY id_servicio_basico")


def _grupos_vulnerables(db, id_localidad):
    rows = _all(db, "edan_localidades_proteccion_grupos", id_localidad,
                "ORDER BY id_grupo_vulnerable")
    grupos = {
        "ninos": {}, "adolescentes": {}, "mujeres_lactantes": {},
        "mujeres_embarazadas": {}, "adultos_mayores": {},
        "personas_discapacidad": {}, "personas_enfermedad": {},
    }
    base = {
        "mujeres": 0, "hombres": 0,
        "apoyo_psicologico": None, "reposicion_documentos": None,
        "observaciones": "",
    }
    for g in rows:
        if g["grupo"] in grupos:
            grupos[g["grupo"]] = {
                "mujeres": g["mujeres"] or 0,
                "hombres": g["hombres"] or 0,
                "apoyo_psicologico": g["apoyo_psicologico"],
                "reposicion_documentos": g["reposicion_documentos"],
                "observaciones": g["observaciones"] or "",
            }
    return {k: (v if v else dict(base)) for k, v in grupos.items()}


def _build_localidad(db: Session, id_localidad: int) -> dict:
    loc = {
        "id_edan_localidad": id_localidad,
        "tipo_localidad": "",
        "nombre": "",
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
    for k in ("tipo_localidad", "nombre", "imp_poblacion", "imp_salud",
              "imp_infraestructura", "imp_servicios", "imp_educacion",
              "imp_vivienda", "imp_agropecuario", "imp_proteccion", "imp_necesidades"):
        loc[k] = row[k]

    # 1. Impacto en población (1:1) + detalle de grupos etarios (1:N)
    ip = _one(db, "edan_localidades_impacto_poblacion", id_localidad)
    loc["impacto_poblacion"] = {
        "grupo_etario": ip["grupo_etario"] if ip else "",
        "fallecidos": ip["fallecidos"] if ip else 0,
        "heridos": ip["heridos"] if ip else 0,
        "desaparecidos": ip["desaparecidos"] if ip else 0,
        "observaciones": ip["observaciones"] if ip else "",
        "grupos_etarios": _grupo_etario_detalle(db, id_localidad),
    }

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
            "enfermeras_afectados": r["enfermeras_afectadas"],
            "otros_afectados": r["otros_afectados"],
        } for r in est
    ]

    # 4. Necesidades de salud (1:1)
    ns = _one(db, "edan_localidades_salud_necesidades", id_localidad)
    loc["necesidad_salud"] = {
        "botiquines": ns["botiquines"] if ns else False,
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
        item["especie_obj"] = {
            "id": pe,
            "nombre": r.get("pe_nombre"),
            "grupo": r.get("pe_grupo"),
        } if pe else None
        loc["danos_pecuarios"].append(item)

    # 12. Infraestructura productiva (1:N)
    loc["infra_productiva"] = _all(db, "edan_localidades_infra_productiva",
                                   id_localidad, "ORDER BY id_infra_productiva")

    # 13. Protección (1:1) + grupos vulnerables
    loc["proteccion"] = {
        "vulnerables": _grupos_vulnerables(db, id_localidad),
    }

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
    return edan


def _get_localidades(db: Session, id_edan: int) -> list:
    rows = _rows(db, """
        SELECT id_edan_localidad FROM edan.edan_localidades
        WHERE id_edan = :id ORDER BY id_edan_localidad
    """, {"id": id_edan})
    return [_build_localidad(db, r["id_edan_localidad"]) for r in rows]


# ============================================================================
#  LOCALIDADES: escritura
# ============================================================================

def _insert_localidad(db: Session, id_edan: int, loc: dict) -> int:
    lid = db.execute(text("""
        INSERT INTO edan.edan_localidades
            (id_edan, tipo_localidad, nombre,
             imp_poblacion, imp_salud, imp_infraestructura, imp_servicios,
             imp_educacion, imp_vivienda, imp_agropecuario, imp_proteccion, imp_necesidades)
        VALUES (:id_edan, :tipo_localidad, :nombre,
                :imp_poblacion, :imp_salud, :imp_infraestructura, :imp_servicios,
                :imp_educacion, :imp_vivienda, :imp_agropecuario, :imp_proteccion, :imp_necesidades)
        RETURNING id_edan_localidad
    """), {
        "id_edan": id_edan,
        "tipo_localidad": loc.get("tipo_localidad", ""),
        "nombre": loc.get("nombre", ""),
        "imp_poblacion": loc.get("imp_poblacion", False),
        "imp_salud": loc.get("imp_salud", False),
        "imp_infraestructura": loc.get("imp_infraestructura", False),
        "imp_servicios": loc.get("imp_servicios", False),
        "imp_educacion": loc.get("imp_educacion", False),
        "imp_vivienda": loc.get("imp_vivienda", False),
        "imp_agropecuario": loc.get("imp_agropecuario", False),
        "imp_proteccion": loc.get("imp_proteccion", False),
        "imp_necesidades": loc.get("imp_necesidades", False),
    }).scalar()

    # 1. Impacto en población (1:1)
    ip = loc.get("impacto_poblacion")
    if ip:
        db.execute(text("""
            INSERT INTO edan.edan_localidades_impacto_poblacion
                (id_edan_localidad, grupo_etario, fallecidos, heridos, desaparecidos, observaciones)
            VALUES (:id, :grupo_etario, :fallecidos, :heridos, :desaparecidos, :observaciones)
        """), {
            "id": lid,
            "grupo_etario": ip.get("grupo_etario", ""),
            "fallecidos": ip.get("fallecidos", 0),
            "heridos": ip.get("heridos", 0),
            "desaparecidos": ip.get("desaparecidos", 0),
            "observaciones": ip.get("observaciones", ""),
        })
        for g in ip.get("grupos_etarios") or []:
            db.execute(text("""
                INSERT INTO edan.edan_grupo_etario_detalle
                    (id_edan_localidad, rango, fallecidos, heridos, desaparecidos, observaciones)
                VALUES (:id, :rango, :fallecidos, :heridos, :desaparecidos, :observaciones)
            """), {
                "id": lid, "rango": g.get("rango", ""),
                "fallecidos": g.get("fallecidos", 0),
                "heridos": g.get("heridos", 0),
                "desaparecidos": g.get("desaparecidos", 0),
                "observaciones": g.get("observaciones", ""),
            })

    # 2. Primera respuesta (1:1)
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

    # 3. Establecimientos de salud (1:N)
    for e in loc.get("establecimientos_salud") or []:
        db.execute(text("""
            INSERT INTO edan.edan_localidades_salud_establecimientos
                (id_edan_localidad, nombre_establecimiento, comunidad, nivel_atencion,
                 dano_parcial, dano_total, medicos_afectados, enfermeras_afectadas, otros_afectados)
            VALUES (:id, :nombre_establecimiento, :comunidad, :nivel_atencion,
                    :dano_parcial, :dano_total, :medicos_afectados, :enfermeras_afectadas, :otros_afectados)
        """), {
            "id": lid,
            "nombre_establecimiento": e.get("nombre_establecimiento", ""),
            "comunidad": e.get("comunidad", ""),
            "nivel_atencion": e.get("nivel_atencion", ""),
            "dano_parcial": e.get("dano_parcial", False),
            "dano_total": e.get("dano_total", False),
            "medicos_afectados": e.get("medicos_afectados", 0),
            "enfermeras_afectadas": e.get("enfermeras_afectados", 0),
            "otros_afectados": e.get("otros_afectados", 0),
        })

    # 4. Necesidades de salud (1:1)
    ns = loc.get("necesidad_salud")
    if ns:
        db.execute(text("""
            INSERT INTO edan.edan_localidades_salud_necesidades
                (id_edan_localidad, botiquines, numero_personas, otras_necesidades, observaciones)
            VALUES (:id, :botiquines, :numero_personas, :otras_necesidades, :observaciones)
        """), {
            "id": lid, "botiquines": ns.get("botiquines", False),
            "numero_personas": ns.get("numero_personas", 0),
            "otras_necesidades": ns.get("otras_necesidades", ""),
            "observaciones": ns.get("observaciones", ""),
        })

    # 5. Daños viales (1:N)
    for d in loc.get("danos_viales") or []:
        db.execute(text("""
            INSERT INTO edan.edan_localidades_danos_viales
                (id_edan_localidad, via_puente, tramo, dano_parcial, dano_total,
                 km_danio, necesidades_inmediatas, observaciones)
            VALUES (:id, :via_puente, :tramo, :dano_parcial, :dano_total,
                    :km_danio, :necesidades_inmediatas, :observaciones)
        """), {
            "id": lid, "via_puente": d.get("via_puente", ""),
            "tramo": d.get("tramo", ""),
            "dano_parcial": d.get("dano_parcial", False),
            "dano_total": d.get("dano_total", False),
            "km_danio": d.get("km_danio") or 0,
            "necesidades_inmediatas": d.get("necesidades_inmediatas", ""),
            "observaciones": d.get("observaciones", ""),
        })

    # 6. Daños infraestructura pública (1:N)
    for d in loc.get("danos_infra_publica") or []:
        db.execute(text("""
            INSERT INTO edan.edan_localidades_danos_infra_publica
                (id_edan_localidad, comunidad, tipo_estructura, dano_parcial, dano_total, observaciones)
            VALUES (:id, :comunidad, :tipo_estructura, :dano_parcial, :dano_total, :observaciones)
        """), {
            "id": lid, "comunidad": d.get("comunidad", ""),
            "tipo_estructura": d.get("tipo_estructura", ""),
            "dano_parcial": d.get("dano_parcial", False),
            "dano_total": d.get("dano_total", False),
            "observaciones": d.get("observaciones", ""),
        })

    # 7. Servicios básicos (1:N)
    for s in loc.get("servicios_basicos") or []:
        db.execute(text("""
            INSERT INTO edan.edan_localidades_servicios_basicos
                (id_edan_localidad, tipo, afectado, dano_parcial, dano_total,
                 necesidades_inmediatas, observaciones)
            VALUES (:id, :tipo, :afectado, :dano_parcial, :dano_total,
                    :necesidades_inmediatas, :observaciones)
        """), {
            "id": lid, "tipo": s.get("tipo", ""),
            "afectado": s.get("afectado", False),
            "dano_parcial": s.get("dano_parcial", False),
            "dano_total": s.get("dano_total", False),
            "necesidades_inmediatas": s.get("necesidades_inmediatas", ""),
            "observaciones": s.get("observaciones", ""),
        })

    # 8. Unidades educativas (1:N)
    for u in loc.get("unidades_educativas") or []:
        db.execute(text("""
            INSERT INTO edan.edan_localidades_unidades_educativas
                (id_edan_localidad, nombre_establecimiento, comunidad, dano_parcial, dano_total,
                 suspension_clases, perdida_material, funciona_albergue,
                 estudiantes, profesores, administrativos, observaciones)
            VALUES (:id, :nombre_establecimiento, :comunidad, :dano_parcial, :dano_total,
                    :suspension_clases, :perdida_material, :funciona_albergue,
                    :estudiantes, :profesores, :administrativos, :observaciones)
        """), {
            "id": lid,
            "nombre_establecimiento": u.get("nombre_establecimiento", ""),
            "comunidad": u.get("comunidad", ""),
            "dano_parcial": u.get("dano_parcial", False),
            "dano_total": u.get("dano_total", False),
            "suspension_clases": u.get("suspension_clases"),
            "perdida_material": u.get("perdida_material"),
            "funciona_albergue": u.get("funciona_albergue"),
            "estudiantes": u.get("estudiantes", 0),
            "profesores": u.get("profesores", 0),
            "administrativos": u.get("administrativos", 0),
            "observaciones": u.get("observaciones", ""),
        })

    # 9. Daños vivienda (1:N)
    for v in loc.get("danos_vivienda") or []:
        db.execute(text("""
            INSERT INTO edan.edan_localidades_danos_vivienda
                (id_edan_localidad, comunidad, dano_parcial, dano_total,
                 necesidades_inmediatas, observaciones)
            VALUES (:id, :comunidad, :dano_parcial, :dano_total,
                    :necesidades_inmediatas, :observaciones)
        """), {
            "id": lid, "comunidad": v.get("comunidad", ""),
            "dano_parcial": v.get("dano_parcial", 0),
            "dano_total": v.get("dano_total", 0),
            "necesidades_inmediatas": v.get("necesidades_inmediatas", ""),
            "observaciones": v.get("observaciones", ""),
        })

    # 10. Agricultura (1:N)
    for a in loc.get("danos_agricultura") or []:
        db.execute(text("""
            INSERT INTO edan.edan_localidades_danos_agricultura
                (id_edan_localidad, tipo_cultivo, id_cultivo,
                 hectareas_afectadas, hectareas_perdidas, necesidades_inmediatas, observaciones)
            VALUES (:id, :tipo_cultivo, :id_cultivo,
                    :hectareas_afectadas, :hectareas_perdidas, :necesidades_inmediatas, :observaciones)
        """), {
            "id": lid, "tipo_cultivo": a.get("tipo_cultivo", ""),
            "id_cultivo": a.get("id_cultivo"),
            "hectareas_afectadas": a.get("hectareas_afectadas", 0),
            "hectareas_perdidas": a.get("hectareas_perdidas", 0),
            "necesidades_inmediatas": a.get("necesidades_inmediatas", ""),
            "observaciones": a.get("observaciones", ""),
        })

    # 11. Pecuario (1:N)
    for p in loc.get("danos_pecuarios") or []:
        db.execute(text("""
            INSERT INTO edan.edan_localidades_danos_pecuario
                (id_edan_localidad, especie, id_especie, raza,
                 animales_afectados, animales_muertos, necesidades_inmediatas)
            VALUES (:id, :especie, :id_especie, :raza,
                    :animales_afectados, :animales_muertos, :necesidades_inmediatas)
        """), {
            "id": lid, "especie": p.get("especie", ""),
            "id_especie": p.get("id_especie"),
            "raza": p.get("raza", ""),
            "animales_afectados": p.get("animales_afectados", 0),
            "animales_muertos": p.get("animales_muertos", 0),
            "necesidades_inmediatas": p.get("necesidades_inmediatas", ""),
        })

    # 12. Infraestructura productiva (1:N)
    for i in loc.get("infra_productiva") or []:
        db.execute(text("""
            INSERT INTO edan.edan_localidades_infra_productiva
                (id_edan_localidad, tipo, dano_parcial, dano_total)
            VALUES (:id, :tipo, :dano_parcial, :dano_total)
        """), {
            "id": lid, "tipo": i.get("tipo", ""),
            "dano_parcial": i.get("dano_parcial", 0),
            "dano_total": i.get("dano_total", 0),
        })

    # 13. Protección (1:1) + grupos vulnerables (1:N)
    prot = loc.get("proteccion")
    if prot:
        db.execute(text("""
            INSERT INTO edan.edan_localidades_proteccion (id_edan_localidad)
            VALUES (:id)
        """), {"id": lid})
        vuln = (prot.get("vulnerables") or {})
        for grupo, g in vuln.items():
            if not isinstance(g, dict):
                continue
            db.execute(text("""
                INSERT INTO edan.edan_localidades_proteccion_grupos
                    (id_edan_localidad, grupo, mujeres, hombres,
                     apoyo_psicologico, reposicion_documentos, observaciones)
                VALUES (:id, :grupo, :mujeres, :hombres,
                        :apoyo_psicologico, :reposicion_documentos, :observaciones)
            """), {
                "id": lid, "grupo": grupo,
                "mujeres": g.get("mujeres", 0),
                "hombres": g.get("hombres", 0),
                "apoyo_psicologico": g.get("apoyo_psicologico"),
                "reposicion_documentos": g.get("reposicion_documentos"),
                "observaciones": g.get("observaciones", ""),
            })

    # 14. Necesidades humanitarias (1:1)
    nh = loc.get("necesidad_humanitaria")
    if nh:
        cols = ", ".join(_NH_FIELDS)
        ph = ", ".join(f":{k}" for k in _NH_FIELDS)
        db.execute(text(f"""
            INSERT INTO edan.edan_localidades_necesidades_humanitarias
                (id_edan_localidad, {cols})
            VALUES (:id, {ph})
        """), {"id": lid, **{k: nh.get(k, False if not k.startswith("obs_") else "") for k in _NH_FIELDS}})

    return lid


def _delete_localidad_sections(db: Session, id_localidad: int):
    tables = [
        "edan_grupo_etario_detalle",
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
        "edan_localidades_proteccion_grupos",
        "edan_localidades_proteccion",
        "edan_localidades_necesidades_humanitarias",
    ]
    for t in tables:
        db.execute(text(f"DELETE FROM edan.{t} WHERE id_edan_localidad = :id"),
                   {"id": id_localidad})


def update_localidad(db: Session, id_localidad: int, data: dict) -> dict | None:
    db.execute(text("""
        UPDATE edan.edan_localidades SET
            tipo_localidad = :tipo_localidad, nombre = :nombre,
            imp_poblacion = :imp_poblacion, imp_salud = :imp_salud,
            imp_infraestructura = :imp_infraestructura, imp_servicios = :imp_servicios,
            imp_educacion = :imp_educacion, imp_vivienda = :imp_vivienda,
            imp_agropecuario = :imp_agropecuario, imp_proteccion = :imp_proteccion,
            imp_necesidades = :imp_necesidades
        WHERE id_edan_localidad = :id
    """), {
        "id": id_localidad,
        "tipo_localidad": data.get("tipo_localidad", ""),
        "nombre": data.get("nombre", ""),
        "imp_poblacion": data.get("imp_poblacion", False),
        "imp_salud": data.get("imp_salud", False),
        "imp_infraestructura": data.get("imp_infraestructura", False),
        "imp_servicios": data.get("imp_servicios", False),
        "imp_educacion": data.get("imp_educacion", False),
        "imp_vivienda": data.get("imp_vivienda", False),
        "imp_agropecuario": data.get("imp_agropecuario", False),
        "imp_proteccion": data.get("imp_proteccion", False),
        "imp_necesidades": data.get("imp_necesidades", False),
    })
    _delete_localidad_sections(db, id_localidad)
    _insert_sections_only(db, id_localidad, data)
    db.commit()
    return _build_localidad(db, id_localidad)


def _insert_sections_only(db: Session, lid: int, loc: dict):
    ip = loc.get("impacto_poblacion")
    if ip:
        db.execute(text("""
            INSERT INTO edan.edan_localidades_impacto_poblacion
                (id_edan_localidad, grupo_etario, fallecidos, heridos, desaparecidos, observaciones)
            VALUES (:id, :grupo_etario, :fallecidos, :heridos, :desaparecidos, :observaciones)
        """), {
            "id": lid, "grupo_etario": ip.get("grupo_etario", ""),
            "fallecidos": ip.get("fallecidos", 0), "heridos": ip.get("heridos", 0),
            "desaparecidos": ip.get("desaparecidos", 0),
            "observaciones": ip.get("observaciones", ""),
        })
        for g in ip.get("grupos_etarios") or []:
            db.execute(text("""
                INSERT INTO edan.edan_grupo_etario_detalle
                    (id_edan_localidad, rango, fallecidos, heridos, desaparecidos, observaciones)
                VALUES (:id, :rango, :fallecidos, :heridos, :desaparecidos, :observaciones)
            """), {
                "id": lid, "rango": g.get("rango", ""),
                "fallecidos": g.get("fallecidos", 0), "heridos": g.get("heridos", 0),
                "desaparecidos": g.get("desaparecidos", 0),
                "observaciones": g.get("observaciones", ""),
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
                 dano_parcial, dano_total, medicos_afectados, enfermeras_afectadas, otros_afectados)
            VALUES (:id, :nombre_establecimiento, :comunidad, :nivel_atencion,
                    :dano_parcial, :dano_total, :medicos_afectados, :enfermeras_afectadas, :otros_afectados)
        """), {
            "id": lid, "nombre_establecimiento": e.get("nombre_establecimiento", ""),
            "comunidad": e.get("comunidad", ""), "nivel_atencion": e.get("nivel_atencion", ""),
            "dano_parcial": e.get("dano_parcial", False), "dano_total": e.get("dano_total", False),
            "medicos_afectados": e.get("medicos_afectados", 0),
            "enfermeras_afectadas": e.get("enfermeras_afectados", 0),
            "otros_afectados": e.get("otros_afectados", 0),
        })

    ns = loc.get("necesidad_salud")
    if ns:
        db.execute(text("""
            INSERT INTO edan.edan_localidades_salud_necesidades
                (id_edan_localidad, botiquines, numero_personas, otras_necesidades, observaciones)
            VALUES (:id, :botiquines, :numero_personas, :otras_necesidades, :observaciones)
        """), {
            "id": lid, "botiquines": ns.get("botiquines", False),
            "numero_personas": ns.get("numero_personas", 0),
            "otras_necesidades": ns.get("otras_necesidades", ""),
            "observaciones": ns.get("observaciones", ""),
        })

    for d in loc.get("danos_viales") or []:
        db.execute(text("""
            INSERT INTO edan.edan_localidades_danos_viales
                (id_edan_localidad, via_puente, tramo, dano_parcial, dano_total,
                 km_danio, necesidades_inmediatas, observaciones)
            VALUES (:id, :via_puente, :tramo, :dano_parcial, :dano_total,
                    :km_danio, :necesidades_inmediatas, :observaciones)
        """), {
            "id": lid, "via_puente": d.get("via_puente", ""), "tramo": d.get("tramo", ""),
            "dano_parcial": d.get("dano_parcial", False), "dano_total": d.get("dano_total", False),
            "km_danio": d.get("km_danio") or 0,
            "necesidades_inmediatas": d.get("necesidades_inmediatas", ""),
            "observaciones": d.get("observaciones", ""),
        })

    for d in loc.get("danos_infra_publica") or []:
        db.execute(text("""
            INSERT INTO edan.edan_localidades_danos_infra_publica
                (id_edan_localidad, comunidad, tipo_estructura, dano_parcial, dano_total, observaciones)
            VALUES (:id, :comunidad, :tipo_estructura, :dano_parcial, :dano_total, :observaciones)
        """), {
            "id": lid, "comunidad": d.get("comunidad", ""),
            "tipo_estructura": d.get("tipo_estructura", ""),
            "dano_parcial": d.get("dano_parcial", False), "dano_total": d.get("dano_total", False),
            "observaciones": d.get("observaciones", ""),
        })

    for s in loc.get("servicios_basicos") or []:
        db.execute(text("""
            INSERT INTO edan.edan_localidades_servicios_basicos
                (id_edan_localidad, tipo, afectado, dano_parcial, dano_total,
                 necesidades_inmediatas, observaciones)
            VALUES (:id, :tipo, :afectado, :dano_parcial, :dano_total,
                    :necesidades_inmediatas, :observaciones)
        """), {
            "id": lid, "tipo": s.get("tipo", ""), "afectado": s.get("afectado", False),
            "dano_parcial": s.get("dano_parcial", False), "dano_total": s.get("dano_total", False),
            "necesidades_inmediatas": s.get("necesidades_inmediatas", ""),
            "observaciones": s.get("observaciones", ""),
        })

    for u in loc.get("unidades_educativas") or []:
        db.execute(text("""
            INSERT INTO edan.edan_localidades_unidades_educativas
                (id_edan_localidad, nombre_establecimiento, comunidad, dano_parcial, dano_total,
                 suspension_clases, perdida_material, funciona_albergue,
                 estudiantes, profesores, administrativos, observaciones)
            VALUES (:id, :nombre_establecimiento, :comunidad, :dano_parcial, :dano_total,
                    :suspension_clases, :perdida_material, :funciona_albergue,
                    :estudiantes, :profesores, :administrativos, :observaciones)
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
        })

    for v in loc.get("danos_vivienda") or []:
        db.execute(text("""
            INSERT INTO edan.edan_localidades_danos_vivienda
                (id_edan_localidad, comunidad, dano_parcial, dano_total,
                 necesidades_inmediatas, observaciones)
            VALUES (:id, :comunidad, :dano_parcial, :dano_total,
                    :necesidades_inmediatas, :observaciones)
        """), {
            "id": lid, "comunidad": v.get("comunidad", ""),
            "dano_parcial": v.get("dano_parcial", 0), "dano_total": v.get("dano_total", 0),
            "necesidades_inmediatas": v.get("necesidades_inmediatas", ""),
            "observaciones": v.get("observaciones", ""),
        })

    for a in loc.get("danos_agricultura") or []:
        db.execute(text("""
            INSERT INTO edan.edan_localidades_danos_agricultura
                (id_edan_localidad, tipo_cultivo, id_cultivo,
                 hectareas_afectadas, hectareas_perdidas, necesidades_inmediatas, observaciones)
            VALUES (:id, :tipo_cultivo, :id_cultivo,
                    :hectareas_afectadas, :hectareas_perdidas, :necesidades_inmediatas, :observaciones)
        """), {
            "id": lid, "tipo_cultivo": a.get("tipo_cultivo", ""),
            "id_cultivo": a.get("id_cultivo"),
            "hectareas_afectadas": a.get("hectareas_afectadas", 0),
            "hectareas_perdidas": a.get("hectareas_perdidas", 0),
            "necesidades_inmediatas": a.get("necesidades_inmediatas", ""),
            "observaciones": a.get("observaciones", ""),
        })

    for p in loc.get("danos_pecuarios") or []:
        db.execute(text("""
            INSERT INTO edan.edan_localidades_danos_pecuario
                (id_edan_localidad, especie, id_especie, raza,
                 animales_afectados, animales_muertos, necesidades_inmediatas)
            VALUES (:id, :especie, :id_especie, :raza,
                    :animales_afectados, :animales_muertos, :necesidades_inmediatas)
        """), {
            "id": lid, "especie": p.get("especie", ""),
            "id_especie": p.get("id_especie"), "raza": p.get("raza", ""),
            "animales_afectados": p.get("animales_afectados", 0),
            "animales_muertos": p.get("animales_muertos", 0),
            "necesidades_inmediatas": p.get("necesidades_inmediatas", ""),
        })

    for i in loc.get("infra_productiva") or []:
        db.execute(text("""
            INSERT INTO edan.edan_localidades_infra_productiva
                (id_edan_localidad, tipo, dano_parcial, dano_total)
            VALUES (:id, :tipo, :dano_parcial, :dano_total)
        """), {
            "id": lid, "tipo": i.get("tipo", ""),
            "dano_parcial": i.get("dano_parcial", 0), "dano_total": i.get("dano_total", 0),
        })

    prot = loc.get("proteccion")
    if prot:
        db.execute(text("""
            INSERT INTO edan.edan_localidades_proteccion (id_edan_localidad) VALUES (:id)
        """), {"id": lid})
        vuln = prot.get("vulnerables") or {}
        for grupo, g in vuln.items():
            if not isinstance(g, dict):
                continue
            db.execute(text("""
                INSERT INTO edan.edan_localidades_proteccion_grupos
                    (id_edan_localidad, grupo, mujeres, hombres,
                     apoyo_psicologico, reposicion_documentos, observaciones)
                VALUES (:id, :grupo, :mujeres, :hombres,
                        :apoyo_psicologico, :reposicion_documentos, :observaciones)
            """), {
                "id": lid, "grupo": grupo,
                "mujeres": g.get("mujeres", 0), "hombres": g.get("hombres", 0),
                "apoyo_psicologico": g.get("apoyo_psicologico"),
                "reposicion_documentos": g.get("reposicion_documentos"),
                "observaciones": g.get("observaciones", ""),
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
#  CRUD PRINCIPAL (transaccional)
# ============================================================================

def create_edan(db: Session, data: dict) -> int:
    header = _build_header_payload(db, data)
    cols = ", ".join(header.keys())
    ph = ", ".join(f":{k}" for k in header.keys())
    result = db.execute(text(f"""
        INSERT INTO edan.edan ({cols}) VALUES ({ph}) RETURNING id_edan
    """), header)
    id_edan = result.scalar()
    for loc in data.get("localidades") or []:
        _insert_localidad(db, id_edan, loc)
    db.commit()
    return id_edan


def update_edan(db: Session, id: int, data: dict) -> dict | None:
    if not get_edan(db, id):
        return None
    resp = data.get("responsable") or {}
    fields = {
        "codigo_edan": data.get("codigo_edan"),
        "id_server": data.get("id_server"),
        "id_usuario": data.get("id_usuario"),
        "id_departamento": data.get("id_departamento"),
        "id_provincia": data.get("id_provincia"),
        "id_municipio": data.get("id_municipio"),
        "id_tipo_evento": data.get("id_tipo_evento"),
        "nombre_alcalde": data.get("nombre_alcalde"),
        "fono_alcalde": data.get("fono_alcalde"),
        "fecha_llenado": data.get("fecha_llenado"),
        "fecha_evento": data.get("fecha_evento"),
        "hora_evento": data.get("hora_evento"),
        "total_poblacion_afectada": data.get("total_poblacion_afectada"),
        "total_familias_afectadas": data.get("total_familias_afectadas"),
        "total_familias_damnificadas": data.get("total_familias_damnificadas"),
        "id_estado": data.get("id_estado"),
        "estado": data.get("estado"),
        "sincronizado": data.get("sincronizado"),
        "pendiente_eliminacion": data.get("pendiente_eliminacion"),
        "pendiente_actualizacion": data.get("pendiente_actualizacion"),
        "es_borrador": data.get("es_borrador"),
        "responsable_nombre": resp.get("nombre"),
        "responsable_cargo": resp.get("cargo"),
        "responsable_fono": resp.get("fono"),
        "responsable_correo": resp.get("correo"),
        "id_reporte_rea": data.get("id_reporte_rea"),
        "fotografia": data.get("fotografia"),
    }
    fields = {k: v for k, v in fields.items() if v is not None}
    if fields.get("id_estado") is not None and fields.get("estado") is None:
        st = _row(db, "SELECT id_estado, nombre FROM edan.estado_edan WHERE id_estado = :id",
                  {"id": fields["id_estado"]})
        if st:
            fields["estado"] = st["nombre"]
            if st["nombre"] == "borrador":
                if fields.get("es_borrador") is None:
                    fields["es_borrador"] = True
            else:
                fields["es_borrador"] = False
    elif fields.get("estado") is not None and fields.get("id_estado") is None:
        st = _row(db, "SELECT id_estado, nombre FROM edan.estado_edan WHERE nombre = :nombre",
                  {"nombre": fields["estado"]})
        if st:
            fields["id_estado"] = st["id_estado"]
            if st["nombre"] == "borrador":
                if fields.get("es_borrador") is None:
                    fields["es_borrador"] = True
            else:
                fields["es_borrador"] = False
    if data.get("id_municipio") is not None and (data.get("id_departamento") is None or data.get("id_provincia") is None):
        mun = _row(db, "SELECT id, id_provincia, id_departamento, nombre FROM shared.municipio WHERE id = :id",
                   {"id": data["id_municipio"]})
        if mun:
            if fields.get("id_departamento") is None:
                fields["id_departamento"] = mun["id_departamento"]
            if fields.get("id_provincia") is None:
                fields["id_provincia"] = mun["id_provincia"]
    if fields.get("id_departamento") is not None and data.get("departamento_nombre") is None:
        fields["departamento_nombre"] = _lookup_nombre(db, "departamento", "id", fields["id_departamento"])
    if fields.get("id_provincia") is not None and data.get("provincia_nombre") is None:
        fields["provincia_nombre"] = _lookup_nombre(db, "provincia", "id", fields["id_provincia"])
    if fields.get("id_municipio") is not None and data.get("municipio_nombre") is None:
        fields["municipio_nombre"] = _lookup_nombre(db, "municipio", "id", fields["id_municipio"])
    if data.get("id_tipo_evento") is not None:
        te = _row(db, "SELECT nombre FROM edan.tipo_evento WHERE id_tipo_evento = :id",
                  {"id": data["id_tipo_evento"]})
        fields["tipo_evento_nombre"] = te["nombre"] if te else None
    if not fields:
        return get_edan_completo(db, id)
    fields["id_edan"] = id
    set_clause = ", ".join(f"{k} = :{k}" for k in fields)
    db.execute(text(f"UPDATE edan.edan SET {set_clause}, fecha_modificacion = NOW() WHERE id_edan = :id_edan"), fields)
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
        UPDATE edan.edan SET pendiente_eliminacion = TRUE, sincronizado = FALSE,
            es_borrador = FALSE, fecha_modificacion = NOW()
        WHERE id_edan = :id
    """), {"id": id})
    db.commit()
    return get_edan_completo(db, id)


# ============================================================================
#  LISTADO CON FILTROS POTENTES
# ============================================================================

ALLOWED_ORDER = {
    "id_edan", "codigo_edan", "fecha_evento", "fecha_creacion",
    "fecha_modificacion", "total_poblacion_afectada", "id_departamento",
    "id_municipio", "estado", "nombre_alcalde",
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
    if f.get("id_usuario") is not None:
        conds.append(f"{a}.id_usuario = :id_usuario")
        params["id_usuario"] = f["id_usuario"]

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

    for flag in ("sincronizado", "pendiente_eliminacion", "pendiente_actualizacion", "es_borrador"):
        if f.get(flag) is not None:
            conds.append(f"{a}.{flag} = :{flag}")
            params[flag] = f[flag]

    if f.get("con_foto"):
        conds.append(f"{a}.fotografia IS NOT NULL AND {a}.fotografia <> ''")
    if f.get("sin_foto"):
        conds.append(f"({a}.fotografia IS NULL OR {a}.fotografia = '')")

    if f.get("q"):
        conds.append(f"""(
            {a}.codigo_edan ILIKE :q OR {a}.nombre_alcalde ILIKE :q OR EXISTS (
                SELECT 1 FROM edan.edan_localidades lq
                WHERE lq.id_edan = {a}.id_edan AND lq.nombre ILIKE :q
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
    return [_build_edan(r) for r in rows], total


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
        SELECT e.id_tipo_evento, COALESCE(e.tipo_evento_nombre, 'Sin tipo') AS tipo_evento,
               COUNT(*) AS cantidad
        FROM edan.edan e{where}
        GROUP BY e.id_tipo_evento, e.tipo_evento_nombre ORDER BY cantidad DESC
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
               l.id_edan_localidad, l.tipo_localidad, l.nombre AS localidad,
               l.imp_poblacion, l.imp_salud, l.imp_infraestructura, l.imp_servicios,
               l.imp_educacion, l.imp_vivienda, l.imp_agropecuario, l.imp_proteccion, l.imp_necesidades
        FROM edan.edan_localidades l
        JOIN edan.edan e ON e.id_edan = l.id_edan
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

def _catalog_crud(table: str, pk: str):
    def get_all(db: Session):
        rows = db.execute(text(f"SELECT * FROM edan.{table} ORDER BY {pk}")).mappings().all()
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
