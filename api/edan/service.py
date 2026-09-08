from datetime import date, datetime, timezone

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
            "total_poblacion_afectada": data.get("total_poblacion_afectada") or 0,
            "total_familias_afectadas": data.get("total_familias_afectadas") or 0,
            "total_familias_damnificadas": data.get("total_familias_damnificadas") or 0,
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
    rows = _rows(db, """
        SELECT ip.*, ge.codigo AS ge_codigo, ge.nombre AS ge_nombre,
               ge.orden AS ge_orden, ge.activo AS ge_activo
        FROM edan.edan_localidades_impacto_poblacion ip
        JOIN edan.grupo_etario ge ON ge.id_grupo_etario = ip.id_grupo_etario
        WHERE ip.id_edan_localidad = :id
        ORDER BY ge.orden, ip.id_impacto_poblacion
    """, {"id": id_localidad})
    return [
        {
            "id_seccion": ip["id_seccion"],
            "id_grupo_etario": ip["id_grupo_etario"],
            "grupo_etario": {
                "id": ip["id_grupo_etario"],
                "codigo": ip["ge_codigo"],
                "nombre": ip["ge_nombre"],
                "orden": ip["ge_orden"],
                "activo": ip["ge_activo"],
            },
            "rango": ip["ge_nombre"],
            "fallecidos": ip["fallecidos"],
            "heridos": ip["heridos"],
            "desaparecidos": ip["desaparecidos"],
            "observaciones": ip["observaciones"] or "",
            "fecha_modificacion": ip.get("fecha_modificacion"),
        } for ip in rows
    ]


def _servicios_basicos(db, id_localidad):
    return _all(db, "edan_localidades_servicios_basicos", id_localidad,
                "ORDER BY id_servicio_basico")


def _grupos_vulnerables(db, id_localidad):
    rows = _rows(db, """
        SELECT p.*, g.codigo, g.nombre, g.orden, g.activo
        FROM edan.edan_localidades_proteccion p
        JOIN edan.grupo_vulnerable g ON g.id_grupo_vulnerable = p.id_grupo_vulnerable_catalogo
        WHERE p.id_edan_localidad = :id
        ORDER BY g.orden, p.id_grupo_vulnerable
    """, {"id": id_localidad})
    return [
        {
            "id_seccion": p["id_seccion"] if p.get("id_seccion") else None,
            "id_grupo_vulnerable_catalogo": p["id_grupo_vulnerable_catalogo"],
            "grupo": {"id": p["id_grupo_vulnerable_catalogo"], "codigo": p["codigo"], "nombre": p["nombre"], "orden": p["orden"], "activo": p["activo"]},
            "mujeres": p["mujeres"] or 0,
            "hombres": p["hombres"] or 0,
            "total": p["total"] if p["total"] is not None else (p["mujeres"] or 0) + (p["hombres"] or 0),
            "apoyo_psicologico": p["apoyo_psicologico"],
            "reposicion_documentos": p["reposicion_documentos"],
            "observaciones": p["observaciones"] or "",
            "fecha_modificacion": p.get("fecha_modificacion"),
        } for p in rows
    ]


# Claves de salida de las 14 secciones dentro de _build_localidad.
SECCION_KEYS = [
    "impacto_poblacion", "necesidad_primera_respuesta", "establecimientos_salud",
    "necesidad_salud", "danos_viales", "danos_infra_publica",
    "servicios_basicos", "unidades_educativas", "danos_vivienda",
    "danos_agricultura", "danos_pecuarios", "infra_productiva",
    "proteccion", "necesidad_humanitaria",
]


def _build_localidad(db: Session, id_localidad: int, solo_con_datos: bool = False) -> dict:
    """Construye la localidad completa (cabecera + flags + 14 secciones).

    Si `solo_con_datos=True` (modo comprimido), elimina de la respuesta las
    secciones sin datos (lista vacía o 1:1 sin registro). Los 22 flags imp_*
    siempre se devuelven para que la app sepa qué secciones habilitar.
    """
    con_datos: set[str] = set()
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
        "imp_impacto_poblacion": False,
        "imp_salud_establecimientos": False,
        "imp_danos_viales": False,
        "imp_danos_infra_publica": False,
        "imp_servicios_basicos": False,
        "imp_unidades_educativas": False,
        "imp_danos_vivienda": False,
        "imp_danos_agricultura": False,
        "imp_danos_pecuarios": False,
        "imp_infra_productiva": False,
        "imp_primera_respuesta": False,
        "imp_necesidad_salud": False,
        "imp_necesidad_humanitaria": False,
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
            u_ugr = None
            if edan["id_usuario_ugr"]:
                r = _row(db, "SELECT id_usuario, usuario, nombre, carnet, celular, correo, cargo"
                             " FROM usuarios.usuario WHERE id_usuario = :id",
                         {"id": edan["id_usuario_ugr"]})
                u_ugr = dict(r) if r else None
            u_alc = None
            if edan["id_usuario_alcalde"]:
                r = _row(db, "SELECT id_usuario, usuario, nombre, carnet, celular, correo, cargo"
                             " FROM usuarios.usuario WHERE id_usuario = :id",
                         {"id": edan["id_usuario_alcalde"]})
                u_alc = dict(r) if r else None
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
                "usuario_ugr": u_ugr,
                "id_usuario_alcalde": edan["id_usuario_alcalde"],
                "usuario_alcalde": u_alc,
            }
        else:
            loc["edan"] = None
    else:
        loc["edan"] = None

    # Usuario creador de la localidad
    if loc["id_usuario"]:
        u = _row(db, "SELECT id_usuario, usuario, nombre, carnet, celular, correo, cargo"
                      " FROM usuarios.usuario WHERE id_usuario = :id",
                 {"id": loc["id_usuario"]})
        loc["usuario"] = dict(u) if u else None
    else:
        loc["usuario"] = None

    # 1. Impacto en población (1:N por rango etario)
    impactos = _impacto_poblacion(db, id_localidad)
    loc["impacto_poblacion"] = impactos
    if impactos:
        con_datos.add("impacto_poblacion")

    # 2. Primera respuesta (1:1)
    pr = _one(db, "edan_localidades_primera_respuesta", id_localidad)
    loc["necesidad_primera_respuesta"] = {
        "id_seccion": pr["id_seccion"] if pr else None,
        "busqueda": pr["busqueda"] if pr else False,
        "salvamento": pr["salvamento"] if pr else False,
        "evacuacion": pr["evacuacion"] if pr else False,
        "observaciones": pr["observaciones"] if pr else "",
        "fecha_modificacion": pr.get("fecha_modificacion") if pr else None,
    }
    if pr:
        con_datos.add("necesidad_primera_respuesta")

# 3. Establecimientos de salud (1:N)
    est = _all(db, "edan_localidades_salud_establecimientos", id_localidad,
               "ORDER BY id_establecimiento_salud")
    loc["establecimientos_salud"] = [
        {
            "id_seccion": r["id_seccion"] if r.get("id_seccion") else None,
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
    if est:
        con_datos.add("establecimientos_salud")

    # 4. Necesidades de salud (1:1)
    ns = _one(db, "edan_localidades_salud_necesidades", id_localidad)
    loc["necesidad_salud"] = {
        "id_seccion": ns["id_seccion"] if ns else None,
        "numero_personas": ns["numero_personas"] if ns else 0,
        "otras_necesidades": ns["otras_necesidades"] if ns else "",
        "observaciones": ns["observaciones"] if ns else "",
        "fecha_modificacion": ns.get("fecha_modificacion") if ns else None,
    }
    if ns:
        con_datos.add("necesidad_salud")

    # 5. Daños viales (1:N)
    dv = _all(db, "edan_localidades_danos_viales", id_localidad,
              "ORDER BY id_dano_vial")
    loc["danos_viales"] = dv
    if dv:
        con_datos.add("danos_viales")

    # 6. Daños infraestructura pública (1:N)
    dip = _all(db, "edan_localidades_danos_infra_publica",
               id_localidad, "ORDER BY id_dano_infra")
    loc["danos_infra_publica"] = dip
    if dip:
        con_datos.add("danos_infra_publica")

    # 7. Servicios básicos (1:N)
    sb = _servicios_basicos(db, id_localidad)
    loc["servicios_basicos"] = sb
    if sb:
        con_datos.add("servicios_basicos")

    # 8. Unidades educativas (1:N)
    ue = _all(db, "edan_localidades_unidades_educativas",
              id_localidad, "ORDER BY id_unidad_educativa")
    loc["unidades_educativas"] = ue
    if ue:
        con_datos.add("unidades_educativas")

    # 9. Daños vivienda (1:N)
    dvv = _all(db, "edan_localidades_danos_vivienda",
               id_localidad, "ORDER BY id_dano_vivienda")
    loc["danos_vivienda"] = dvv
    if dvv:
        con_datos.add("danos_vivienda")

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
    if ag_rows:
        con_datos.add("danos_agricultura")

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
    if pe_rows:
        con_datos.add("danos_pecuarios")

    # 12. Infraestructura productiva (1:N)
    ipr = _all(db, "edan_localidades_infra_productiva",
               id_localidad, "ORDER BY id_infra_productiva")
    loc["infra_productiva"] = ipr
    if ipr:
        con_datos.add("infra_productiva")

    # 13. Protección (1:N por grupo vulnerable)
    prot = _grupos_vulnerables(db, id_localidad)
    loc["proteccion"] = prot
    if prot:
        con_datos.add("proteccion")

    # 14. Necesidades humanitarias (1:1)
    nh = _one(db, "edan_localidades_necesidades_humanitarias", id_localidad)
    if nh:
        nh = dict(nh)
        nh.pop("id_edan_localidad", None)
        loc["necesidad_humanitaria"] = nh
        con_datos.add("necesidad_humanitaria")
    else:
        loc["necesidad_humanitaria"] = {k: (False if not k.startswith("obs_") else "")
                                        for k in _NH_FIELDS}
        loc["necesidad_humanitaria"]["fecha_modificacion"] = None

    # Modo comprimido: dejar solo las secciones con datos (los flags siempre quedan)
    if solo_con_datos:
        for k in SECCION_KEYS:
            if k not in con_datos:
                loc.pop(k, None)

    return loc


# IDs internos del backend (PK de filas que la app NO debe ver). El único
# identificador del documento es `id_seccion` (UUID generado por el cliente).
_INTERNAL_ROW_IDS = {
    "impacto_poblacion":        {"id_impacto_poblacion"},
    "establecimientos_salud":   {"id_establecimiento_salud"},
    "danos_viales":             {"id_dano_vial"},
    "danos_infra_publica":      {"id_dano_infra"},
    "servicios_basicos":        {"id_servicio_basico"},
    "unidades_educativas":      {"id_unidad_educativa"},
    "danos_vivienda":           {"id_dano_vivienda"},
    "danos_agricultura":        {"id_dano_agricultura"},
    "danos_pecuarios":          {"id_dano_pecuario"},
    "infra_productiva":         {"id_infra_productiva"},
    "proteccion":               {"id_grupo_vulnerable"},
    "necesidad_primera_respuesta": set(),
    "necesidad_salud":          set(),
    "necesidad_humanitaria":    set(),
}


def _sanitizar_doc(loc: dict) -> dict:
    """Elimina de cada sección del documento los IDs internos del backend
    (`id_<pk>` de fila e `id_edan_localidad`), dejando solo `id_seccion` + campos
    de negocio. Es **exclusivo del flujo v2**: lo aplican `serialize_document`
    y `get_mis_localidades` (mis-reportes), sin alterar el output v1.
    """
    for key, meta in DOCUMENT_SECCION.items():
        if key not in loc:
            continue
        strip = _INTERNAL_ROW_IDS.get(key, set()) | {"id_edan_localidad"}
        if meta["forma"] == "array":
            items = loc[key]
            if not isinstance(items, list):
                continue
            loc[key] = [
                {k: v for k, v in (item or {}).items() if k not in strip}
                for item in items
            ]
        else:
            item = loc[key]
            if isinstance(item, dict):
                loc[key] = {k: v for k, v in item.items() if k not in strip}
    return loc


_NH_FIELDS = [
    "alimentos", "refugio_vivienda", "ropa_cama", "articulos_higiene",
    "articulos_cocina", "prendas_vestir", "herramientas", "almacenamiento_agua",
    "banos",
] + [f"obs_{x}" for x in (
    "alimentos", "refugio_vivienda", "ropa_cama", "articulos_higiene",
    "articulos_cocina", "prendas_vestir", "herramientas", "almacenamiento_agua",
    "banos")]


def _get_resumen_localidades(db: Session, id_edan: int) -> list:
    """Devuelve resumen compacto de cada localidad del EDAN."""
    rows = _rows(db, """
        SELECT l.id_edan_localidad, l.localidad,
               l.total_poblacion_afectada, l.total_familias_afectadas,
               l.total_familias_damnificadas,
               t.nombre AS tipo_localidad, es.nombre AS estado_localidad
        FROM edan.edan_localidades l
        LEFT JOIN edan.tipo_localidad t ON t.id_tipo_localidad = l.id_tipo_localidad
        LEFT JOIN edan.edan_localidades_estado es ON es.id_edan_localidad_estado = l.id_edan_localidad_estado
        WHERE l.id_edan = :id_edan ORDER BY l.id_edan_localidad
    """, {"id_edan": id_edan})
    return [dict(r) for r in rows]


def _get_sumatorias(db: Session, id_edan: int) -> dict:
    """Calcula sumatorias de todas las secciones 1:N de las localidades del EDAN."""
    locs = _rows(db, "SELECT id_edan_localidad FROM edan.edan_localidades WHERE id_edan = :id",
                 {"id": id_edan})
    if not locs:
        return {}
    ids = [r["id_edan_localidad"] for r in locs]
    ph = ", ".join(f":_{i}" for i in range(len(ids)))
    params = {f"_{i}": v for i, v in enumerate(ids)}

    def _sum(table, cols):
        selects = ", ".join(f"COALESCE(SUM({c}), 0) AS {c}" for c in cols)
        row = _row(db, f"SELECT {selects} FROM edan.{table} WHERE id_edan_localidad IN ({ph})", params)
        return dict(row) if row else {c: 0 for c in cols}

    return {
        "danos_agricultura": _sum("edan_localidades_danos_agricultura",
                                  ["hectareas_afectadas", "hectareas_perdidas"]),
        "danos_pecuarios": _sum("edan_localidades_danos_pecuario",
                                ["animales_afectados", "animales_muertos"]),
        "impacto_poblacion": _sum("edan_localidades_impacto_poblacion",
                                  ["fallecidos", "heridos", "desaparecidos"]),
        "proteccion": _sum("edan_localidades_proteccion", ["mujeres", "hombres", "total"]),
        "establecimientos_salud": _sum("edan_localidades_salud_establecimientos",
                                       ["medicos_afectados", "enfermeras_afectadas", "otros_afectados"]),
        "necesidad_salud": _sum("edan_localidades_salud_necesidades", ["numero_personas"]),
    }


def _get_resumen_secciones(db: Session, id_edan: int) -> dict:
    """Resumen agregado de las 14 secciones para el EDAN (grupo consolidado).
    Agrega por grupo donde aplica (grupo etario, tipo, cultivo, especie, grupo
    vulnerable) y expone totales por sección. Los totales son por id_edan_localidad
    (fila base en tablas de localidad) o sumatorias en tablas 1:N."""
    locs = _rows(db, """
        SELECT id_edan_localidad FROM edan.edan_localidades
        WHERE id_edan = :id ORDER BY id_edan_localidad
    """, {"id": id_edan})
    ids = [r["id_edan_localidad"] for r in locs]
    if not ids:
        return {}

    ph = ", ".join(f":_{i}" for i in range(len(ids)))
    prm = lambda i: f"_{i}"
    params = {prm(i): v for i, v in enumerate(ids)}

    def totals(rows, keys):
        return {k: sum(int(r.get(k) or 0) for r in rows) for k in keys}

    def _overview(rows_by_localidad):
        return {"localidades": len(rows_by_localidad)}

    impacto = [dict(r) for r in _rows(db, f"""
        SELECT ip.id_grupo_etario, COALESCE(ge.nombre, 'Sin grupo') AS grupo_etario,
               COALESCE(SUM(ip.fallecidos), 0) AS fallecidos,
               COALESCE(SUM(ip.heridos), 0) AS heridos,
               COALESCE(SUM(ip.desaparecidos), 0) AS desaparecidos
        FROM edan.edan_localidades_impacto_poblacion ip
        LEFT JOIN edan.grupo_etario ge ON ge.id_grupo_etario = ip.id_grupo_etario
        WHERE ip.id_edan_localidad IN ({ph})
        GROUP BY ip.id_grupo_etario, ge.nombre ORDER BY fallecidos DESC
    """, params)]

    primera = _row(db, f"""
        SELECT COUNT(*) AS localidades,
               COUNT(*) FILTER (WHERE pr.busqueda) AS busqueda,
               COUNT(*) FILTER (WHERE pr.salvamento) AS salvamento,
               COUNT(*) FILTER (WHERE pr.evacuacion) AS evacuacion
        FROM edan.edan_localidades_primera_respuesta pr
        WHERE pr.id_edan_localidad IN ({ph})
    """, params)

    salud_est = dict(_row(db, f"""
        SELECT COUNT(*) AS total_establecimientos,
               COALESCE(SUM((se.dano_parcial)::int), 0) AS dano_parcial,
               COALESCE(SUM((se.dano_total)::int), 0) AS dano_total,
               COALESCE(SUM(se.medicos_afectados), 0) AS medicos_afectados,
               COALESCE(SUM(se.enfermeras_afectadas), 0) AS enfermeras_afectadas,
               COALESCE(SUM(se.otros_afectados), 0) AS otros_afectados,
               COUNT(DISTINCT se.id_edan_localidad) AS localidades
        FROM edan.edan_localidades_salud_establecimientos se
        WHERE se.id_edan_localidad IN ({ph})
    """, params) or {})

    nec_salud = dict(_row(db, f"""
        SELECT COUNT(*) AS localidades,
               COALESCE(SUM(sn.numero_personas), 0) AS numero_personas
        FROM edan.edan_localidades_salud_necesidades sn
        WHERE sn.id_edan_localidad IN ({ph})
    """, params) or {})

    viales = dict(_row(db, f"""
        SELECT COUNT(*) AS total_registros,
               COUNT(*) FILTER (WHERE dv.via) AS via,
               COUNT(*) FILTER (WHERE dv.puente) AS puente,
               COALESCE(SUM((dv.dano_parcial)::int), 0) AS dano_parcial,
               COALESCE(SUM((dv.dano_total)::int), 0) AS dano_total,
               COALESCE(SUM(dv.km_danio), 0) AS km_danio,
               COUNT(DISTINCT dv.id_edan_localidad) AS localidades
        FROM edan.edan_localidades_danos_viales dv
        WHERE dv.id_edan_localidad IN ({ph})
    """, params) or {})

    infra_publica = [dict(r) for r in _rows(db, f"""
        SELECT COALESCE(di.tipo_estructura, 'Sin especificar') AS tipo_estructura,
               COALESCE(SUM((di.dano_parcial)::int), 0) AS dano_parcial,
               COALESCE(SUM((di.dano_total)::int), 0) AS dano_total
        FROM edan.edan_localidades_danos_infra_publica di
        WHERE di.id_edan_localidad IN ({ph})
        GROUP BY di.tipo_estructura ORDER BY dano_total DESC
    """, params)]
    infra_publica_tot = {**totals(infra_publica, ["dano_parcial", "dano_total"]),
                         "total_registros": len(infra_publica)}

    servicios_base = [dict(r) for r in _rows(db, f"""
        SELECT COALESCE(sb.tipo, 'Sin especificar') AS tipo,
               COALESCE(SUM((sb.dano_parcial)::int), 0) AS dano_parcial,
               COALESCE(SUM((sb.dano_total)::int), 0) AS dano_total
        FROM edan.edan_localidades_servicios_basicos sb
        WHERE sb.id_edan_localidad IN ({ph})
        GROUP BY sb.tipo ORDER BY dano_total DESC
    """, params)]

    educativas = dict(_row(db, f"""
        SELECT COUNT(*) AS total_establecimientos,
               COALESCE(SUM((ue.dano_parcial)::int), 0) AS dano_parcial,
               COALESCE(SUM((ue.dano_total)::int), 0) AS dano_total,
               COUNT(*) FILTER (WHERE ue.suspension_clases) AS suspension_clases,
               COUNT(*) FILTER (WHERE ue.perdida_material) AS perdida_material,
               COUNT(*) FILTER (WHERE ue.funciona_albergue) AS funciona_albergue,
               COALESCE(SUM(ue.estudiantes), 0) AS estudiantes,
               COALESCE(SUM(ue.profesores), 0) AS profesores,
               COALESCE(SUM(ue.administrativos), 0) AS administrativos,
               COUNT(DISTINCT ue.id_edan_localidad) AS localidades
        FROM edan.edan_localidades_unidades_educativas ue
        WHERE ue.id_edan_localidad IN ({ph})
    """, params) or {})

    vivienda = dict(_row(db, f"""
        SELECT COUNT(*) AS total_registros,
               COALESCE(SUM(dv.dano_parcial), 0) AS dano_parcial,
               COALESCE(SUM(dv.dano_total), 0) AS dano_total,
               COUNT(DISTINCT dv.id_edan_localidad) AS localidades
        FROM edan.edan_localidades_danos_vivienda dv
        WHERE dv.id_edan_localidad IN ({ph})
    """, params) or {})

    agricultura = [dict(r) for r in _rows(db, f"""
        SELECT a.id_cultivo, COALESCE(c.nombre, 'Sin especificar') AS cultivo,
               COALESCE(a.tipo_cultivo, 'Sin especificar') AS tipo_cultivo,
               COALESCE(SUM(a.hectareas_afectadas), 0) AS hectareas_afectadas,
               COALESCE(SUM(a.hectareas_perdidas), 0) AS hectareas_perdidas
        FROM edan.edan_localidades_danos_agricultura a
        LEFT JOIN shared.cultivo c ON c.id = a.id_cultivo
        WHERE a.id_edan_localidad IN ({ph})
        GROUP BY a.id_cultivo, c.nombre, a.tipo_cultivo
        ORDER BY hectareas_afectadas DESC
    """, params)]
    agricultura_tot = {**totals(agricultura, ["hectareas_afectadas", "hectareas_perdidas"]),
                       "total_registros": len(agricultura)}

    pecuario = [dict(r) for r in _rows(db, f"""
        SELECT dp.id_especie, COALESCE(p.nombre, dp.especie, 'Sin especificar') AS especie,
               COALESCE(SUM(dp.animales_afectados), 0) AS animales_afectados,
               COALESCE(SUM(dp.animales_muertos), 0) AS animales_muertos
        FROM edan.edan_localidades_danos_pecuario dp
        LEFT JOIN shared.pecuario p ON p.id = dp.id_especie
        WHERE dp.id_edan_localidad IN ({ph})
        GROUP BY dp.id_especie, p.nombre, dp.especie
        ORDER BY animales_afectados DESC
    """, params)]
    pecuario_tot = {**totals(pecuario, ["animales_afectados", "animales_muertos"]),
                    "total_registros": len(pecuario)}

    infra_productiva = [dict(r) for r in _rows(db, f"""
        SELECT COALESCE(ip.tipo, 'Sin especificar') AS tipo,
               COALESCE(SUM(ip.dano_parcial), 0) AS dano_parcial,
               COALESCE(SUM(ip.dano_total), 0) AS dano_total
        FROM edan.edan_localidades_infra_productiva ip
        WHERE ip.id_edan_localidad IN ({ph})
        GROUP BY ip.tipo ORDER BY dano_total DESC
    """, params)]

    proteccion = [dict(r) for r in _rows(db, f"""
        SELECT COALESCE(pr.grupo, 'Sin especificar') AS grupo,
               COALESCE(SUM(pr.mujeres), 0) AS mujeres,
               COALESCE(SUM(pr.hombres), 0) AS hombres,
               COALESCE(SUM(pr.total), 0) AS total,
               COUNT(*) FILTER (WHERE pr.apoyo_psicologico) AS apoyo_psicologico,
               COUNT(*) FILTER (WHERE pr.reposicion_documentos) AS reposicion_documentos
        FROM edan.edan_localidades_proteccion pr
        WHERE pr.id_edan_localidad IN ({ph})
        GROUP BY pr.grupo ORDER BY total DESC
    """, params)]
    proteccion_tot = {**totals(proteccion, ["mujeres", "hombres", "total"]),
                      "total_registros": len(proteccion)}

    nec_humanitaria = dict(_row(db, f"""
        SELECT COUNT(*) AS localidades,
               COUNT(*) FILTER (WHERE nh.alimentos) AS alimentos,
               COUNT(*) FILTER (WHERE nh.refugio_vivienda) AS refugio_vivienda,
               COUNT(*) FILTER (WHERE nh.ropa_cama) AS ropa_cama,
               COUNT(*) FILTER (WHERE nh.articulos_higiene) AS articulos_higiene,
               COUNT(*) FILTER (WHERE nh.articulos_cocina) AS articulos_cocina,
               COUNT(*) FILTER (WHERE nh.prendas_vestir) AS prendas_vestir,
               COUNT(*) FILTER (WHERE nh.herramientas) AS herramientas,
               COUNT(*) FILTER (WHERE nh.almacenamiento_agua) AS almacenamiento_agua,
               COUNT(*) FILTER (WHERE nh.banos) AS banos
        FROM edan.edan_localidades_necesidades_humanitarias nh
        WHERE nh.id_edan_localidad IN ({ph})
    """, params) or {})

    return {
        "impacto_poblacion": {
            "por_grupo_etario": impacto,
            "totales": {**totals(impacto, ["fallecidos", "heridos", "desaparecidos"]),
                        "localidades": _overview(impacto)["localidades"]},
        },
        "primera_respuesta": dict(primera) if primera else {},
        "salud_establecimientos": salud_est,
        "necesidad_salud": nec_salud,
        "danos_viales": viales,
        "danos_infra_publica": {"por_tipo": infra_publica, **infra_publica_tot},
        "servicios_basicos": {"por_tipo": servicios_base,
                              **totals(servicios_base, ["dano_parcial", "dano_total"]),
                              "total_registros": len(servicios_base)},
        "unidades_educativas": educativas,
        "danos_vivienda": vivienda,
        "danos_agricultura": {"por_cultivo": agricultura, **agricultura_tot},
        "danos_pecuarios": {"por_especie": pecuario, **pecuario_tot},
        "infra_productiva": {"por_tipo": infra_productiva,
                             **totals(infra_productiva, ["dano_parcial", "dano_total"]),
                             "total_registros": len(infra_productiva)},
        "proteccion": {"por_grupo": proteccion, **proteccion_tot},
        "necesidad_humanitaria": nec_humanitaria,
    }


def get_edan_completo(db: Session, id: int, modo: str = "detallado"):
    """Devuelve EDAN completo. modos: 'detallado' (con localidades completas) o
    'compacto' (resumen de localidades + sumatorias)."""
    edan = get_edan(db, id)
    if not edan:
        return None
    if modo == "compacto":
        edan["resumen_localidades"] = _get_resumen_localidades(db, id)
        edan["sumatorias"] = _get_sumatorias(db, id)
    else:
        edan["localidades"] = _get_localidades(db, id)
    edan["resumen_secciones"] = _get_resumen_secciones(db, id)
    edan["reportes_rea"] = [dict(r) for r in _rows(db, """
        SELECT id_reporte, comunidad, fecha_evento, hora_evento,
               id_municipio, id_tipo_evento, descripcion
        FROM rea.reporte_evento WHERE id_edan = :id_edan ORDER BY id_reporte
    """, {"id_edan": id})]
    return edan


def get_edan_por_reporte(db: Session, id_reporte: int):
    """Devuelve el EDAN generado desde un reporte REA (o None si no está vinculado)."""
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


def _resolve_grupo_etario(db: Session, item: dict) -> int | None:
    """Prioriza id_grupo_etario; si llega el string legacy 'rango' o 'grupo_etario',
    lo resuelve por nombre/codigo (compatibilidad con la app durante la transición).
    Returns: idGrupoEtario o None si no resuelve."""
    if item.get("id_grupo_etario") is not None:
        return item["id_grupo_etario"]
    nombre = item.get("rango") or item.get("grupo_etario")
    if nombre:
        t = _row(db, "SELECT id_grupo_etario FROM edan.grupo_etario WHERE nombre = :n OR codigo = :n",
                 {"n": nombre})
        if t:
            return t["id_grupo_etario"]
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


def _bump_localidad_fecha(db: Session, id_localidad: int):
    """Marca una localidad como modificada por una escritura de sección, para
    que el pull y la consolidación detecten el cambio. Si está consolidada,
    propaga el bump al EDAN."""
    db.execute(text("""
        UPDATE edan.edan_localidades SET fecha_modificacion = NOW(),
            pendiente_actualizacion = TRUE
        WHERE id_edan_localidad = :id
    """), {"id": id_localidad})
    parent = _row(db, "SELECT id_edan FROM edan.edan_localidades WHERE id_edan_localidad = :id",
                  {"id": id_localidad})
    if parent and parent["id_edan"] is not None:
        _bump_edan_fecha(db, parent["id_edan"])


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
            "total_poblacion_afectada": data.get("total_poblacion_afectada") or 0,
            "total_familias_afectadas": data.get("total_familias_afectadas") or 0,
            "total_familias_damnificadas": data.get("total_familias_damnificadas") or 0,
    })
    _delete_localidad_sections(db, id_localidad)
    _insert_sections_only(db, id_localidad, data)
    if parent["id_edan"] is not None:
        _bump_edan_fecha(db, parent["id_edan"])
    db.commit()
    return _build_localidad(db, id_localidad)


def _insert_sections_only(db: Session, lid: int, loc: dict):
    """Inserta o actualiza secciones usando UPSERT por id_seccion.
    
    Para secciones 1:N: UPSERT por id_seccion (generado por cliente).
    Para secciones 1:1: UPSERT por id_edan_localidad.
    """
    # 1. Impacto Poblacion (1:N) - UPSERT por id_seccion
    for ip in loc.get("impacto_poblacion") or []:
        id_seccion = ip.get("id_seccion")
        id_grupo_etario = _resolve_grupo_etario(db, ip)
        if id_grupo_etario is None:
            continue
        db.execute(text("""
            INSERT INTO edan.edan_localidades_impacto_poblacion
                (id_edan_localidad, id_seccion, id_grupo_etario, fallecidos, heridos, desaparecidos, observaciones)
            VALUES (:id, :id_seccion, :id_grupo_etario, :fallecidos, :heridos, :desaparecidos, :observaciones)
            ON CONFLICT (id_seccion) DO UPDATE SET
                id_edan_localidad = EXCLUDED.id_edan_localidad,
                id_grupo_etario = EXCLUDED.id_grupo_etario,
                fallecidos = EXCLUDED.fallecidos,
                heridos = EXCLUDED.heridos,
                desaparecidos = EXCLUDED.desaparecidos,
                observaciones = EXCLUDED.observaciones
        """), {
            "id": lid, "id_seccion": id_seccion,
            "id_grupo_etario": id_grupo_etario,
            "fallecidos": ip.get("fallecidos", 0), "heridos": ip.get("heridos", 0),
            "desaparecidos": ip.get("desaparecidos", 0),
            "observaciones": ip.get("observaciones", ""),
        })

    # 2. Primera Respuesta (1:1) - UPSERT por id_seccion o id_edan_localidad
    pr = loc.get("necesidad_primera_respuesta")
    if pr:
        id_seccion = pr.get("id_seccion")
        if id_seccion:
            db.execute(text("""
                INSERT INTO edan.edan_localidades_primera_respuesta
                    (id_edan_localidad, id_seccion, busqueda, salvamento, evacuacion, observaciones)
                VALUES (:id, :id_seccion, :busqueda, :salvamento, :evacuacion, :observaciones)
                ON CONFLICT (id_seccion) DO UPDATE SET
                    id_edan_localidad = EXCLUDED.id_edan_localidad,
                    busqueda = EXCLUDED.busqueda,
                    salvamento = EXCLUDED.salvamento,
                    evacuacion = EXCLUDED.evacuacion,
                    observaciones = EXCLUDED.observaciones
            """), {
                "id": lid, "id_seccion": id_seccion,
                "busqueda": pr.get("busqueda", False),
                "salvamento": pr.get("salvamento", False),
                "evacuacion": pr.get("evacuacion", False),
                "observaciones": pr.get("observaciones", ""),
            })
        else:
            db.execute(text("""
                INSERT INTO edan.edan_localidades_primera_respuesta
                    (id_edan_localidad, busqueda, salvamento, evacuacion, observaciones)
                VALUES (:id, :busqueda, :salvamento, :evacuacion, :observaciones)
                ON CONFLICT (id_edan_localidad) DO UPDATE SET
                    busqueda = EXCLUDED.busqueda,
                    salvamento = EXCLUDED.salvamento,
                    evacuacion = EXCLUDED.evacuacion,
                    observaciones = EXCLUDED.observaciones
            """), {
                "id": lid,
                "busqueda": pr.get("busqueda", False),
                "salvamento": pr.get("salvamento", False),
                "evacuacion": pr.get("evacuacion", False),
                "observaciones": pr.get("observaciones", ""),
            })

    # 3. Establecimientos Salud (1:N) - UPSERT por id_seccion
    for e in loc.get("establecimientos_salud") or []:
        id_seccion = e.get("id_seccion")
        db.execute(text("""
            INSERT INTO edan.edan_localidades_salud_establecimientos
                (id_edan_localidad, id_seccion, nombre_establecimiento, comunidad, nivel_atencion,
                 dano_parcial, dano_total, medicos_afectados, enfermeras_afectadas, otros_afectados,
                 fotografia, coordenada_lat, coordenada_lon)
            VALUES (:id, :id_seccion, :nombre_establecimiento, :comunidad, :nivel_atencion,
                    :dano_parcial, :dano_total, :medicos_afectados, :enfermeras_afectadas, :otros_afectados,
                    :fotografia, :coordenada_lat, :coordenada_lon)
            ON CONFLICT (id_seccion) DO UPDATE SET
                nombre_establecimiento = EXCLUDED.nombre_establecimiento,
                comunidad = EXCLUDED.comunidad,
                nivel_atencion = EXCLUDED.nivel_atencion,
                dano_parcial = EXCLUDED.dano_parcial,
                dano_total = EXCLUDED.dano_total,
                medicos_afectados = EXCLUDED.medicos_afectados,
                enfermeras_afectadas = EXCLUDED.enfermeras_afectadas,
                otros_afectados = EXCLUDED.otros_afectados,
                fotografia = EXCLUDED.fotografia,
                coordenada_lat = EXCLUDED.coordenada_lat,
                coordenada_lon = EXCLUDED.coordenada_lon
        """), {
            "id": lid, "id_seccion": id_seccion,
            "nombre_establecimiento": e.get("nombre_establecimiento", ""),
            "comunidad": e.get("comunidad", ""), "nivel_atencion": e.get("nivel_atencion", ""),
            "dano_parcial": e.get("dano_parcial", False), "dano_total": e.get("dano_total", False),
            "medicos_afectados": e.get("medicos_afectados", 0),
            "enfermeras_afectadas": e.get("enfermeras_afectadas", 0),
            "otros_afectados": e.get("otros_afectados", 0),
            "fotografia": e.get("fotografia"),
            "coordenada_lat": e.get("coordenada_lat"),
            "coordenada_lon": e.get("coordenada_lon"),
        })

    # 4. Necesidad Salud (1:1) - UPSERT por id_seccion o id_edan_localidad
    ns = loc.get("necesidad_salud")
    if ns:
        id_seccion = ns.get("id_seccion")
        if id_seccion:
            db.execute(text("""
                INSERT INTO edan.edan_localidades_salud_necesidades
                    (id_edan_localidad, id_seccion, numero_personas, otras_necesidades, observaciones)
                VALUES (:id, :id_seccion, :numero_personas, :otras_necesidades, :observaciones)
                ON CONFLICT (id_seccion) DO UPDATE SET
                    id_edan_localidad = EXCLUDED.id_edan_localidad,
                    numero_personas = EXCLUDED.numero_personas,
                    otras_necesidades = EXCLUDED.otras_necesidades,
                    observaciones = EXCLUDED.observaciones
            """), {
                "id": lid, "id_seccion": id_seccion,
                "numero_personas": ns.get("numero_personas", 0),
                "otras_necesidades": ns.get("otras_necesidades", ""),
                "observaciones": ns.get("observaciones", ""),
            })
        else:
            db.execute(text("""
                INSERT INTO edan.edan_localidades_salud_necesidades
                    (id_edan_localidad, numero_personas, otras_necesidades, observaciones)
                VALUES (:id, :numero_personas, :otras_necesidades, :observaciones)
                ON CONFLICT (id_edan_localidad) DO UPDATE SET
                    numero_personas = EXCLUDED.numero_personas,
                    otras_necesidades = EXCLUDED.otras_necesidades,
                    observaciones = EXCLUDED.observaciones
            """), {
                "id": lid,
                "numero_personas": ns.get("numero_personas", 0),
                "otras_necesidades": ns.get("otras_necesidades", ""),
                "observaciones": ns.get("observaciones", ""),
            })

    # 5. Daños Viales (1:N) - UPSERT por id_seccion
    for d in loc.get("danos_viales") or []:
        id_seccion = d.get("id_seccion")
        db.execute(text("""
            INSERT INTO edan.edan_localidades_danos_viales
                (id_edan_localidad, id_seccion, via, puente, tramo, dano_parcial, dano_total,
                 km_danio, necesidades_inmediatas, observaciones,
                 fotografia, coordenada_lat, coordenada_lon)
            VALUES (:id, :id_seccion, :via, :puente, :tramo, :dano_parcial, :dano_total,
                    :km_danio, :necesidades_inmediatas, :observaciones,
                    :fotografia, :coordenada_lat, :coordenada_lon)
            ON CONFLICT (id_seccion) DO UPDATE SET
                via = EXCLUDED.via,
                puente = EXCLUDED.puente,
                tramo = EXCLUDED.tramo,
                dano_parcial = EXCLUDED.dano_parcial,
                dano_total = EXCLUDED.dano_total,
                km_danio = EXCLUDED.km_danio,
                necesidades_inmediatas = EXCLUDED.necesidades_inmediatas,
                observaciones = EXCLUDED.observaciones,
                fotografia = EXCLUDED.fotografia,
                coordenada_lat = EXCLUDED.coordenada_lat,
                coordenada_lon = EXCLUDED.coordenada_lon
        """), {
            "id": lid, "id_seccion": id_seccion,
            "via": d.get("via", False), "puente": d.get("puente", False),
            "tramo": d.get("tramo", ""),
            "dano_parcial": d.get("dano_parcial", False), "dano_total": d.get("dano_total", False),
            "km_danio": d.get("km_danio") or 0,
            "necesidades_inmediatas": d.get("necesidades_inmediatas", ""),
            "observaciones": d.get("observaciones", ""),
            "fotografia": d.get("fotografia"),
            "coordenada_lat": d.get("coordenada_lat"),
            "coordenada_lon": d.get("coordenada_lon"),
        })

    # 6. Daños Infra Publica (1:N) - UPSERT por id_seccion
    for d in loc.get("danos_infra_publica") or []:
        id_seccion = d.get("id_seccion")
        db.execute(text("""
            INSERT INTO edan.edan_localidades_danos_infra_publica
                (id_edan_localidad, id_seccion, comunidad, tipo_estructura, dano_parcial, dano_total, observaciones,
                 fotografia, coordenada_lat, coordenada_lon)
            VALUES (:id, :id_seccion, :comunidad, :tipo_estructura, :dano_parcial, :dano_total, :observaciones,
                    :fotografia, :coordenada_lat, :coordenada_lon)
            ON CONFLICT (id_seccion) DO UPDATE SET
                comunidad = EXCLUDED.comunidad,
                tipo_estructura = EXCLUDED.tipo_estructura,
                dano_parcial = EXCLUDED.dano_parcial,
                dano_total = EXCLUDED.dano_total,
                observaciones = EXCLUDED.observaciones,
                fotografia = EXCLUDED.fotografia,
                coordenada_lat = EXCLUDED.coordenada_lat,
                coordenada_lon = EXCLUDED.coordenada_lon
        """), {
            "id": lid, "id_seccion": id_seccion,
            "comunidad": d.get("comunidad", ""),
            "tipo_estructura": d.get("tipo_estructura", ""),
            "dano_parcial": d.get("dano_parcial", False), "dano_total": d.get("dano_total", False),
            "observaciones": d.get("observaciones", ""),
            "fotografia": d.get("fotografia"),
            "coordenada_lat": d.get("coordenada_lat"),
            "coordenada_lon": d.get("coordenada_lon"),
        })

    # 7. Servicios Basicos (1:N) - UPSERT por id_seccion
    for s in loc.get("servicios_basicos") or []:
        id_seccion = s.get("id_seccion")
        db.execute(text("""
            INSERT INTO edan.edan_localidades_servicios_basicos
                (id_edan_localidad, id_seccion, tipo, dano_parcial, dano_total,
                 necesidades_inmediatas, observaciones,
                 fotografia, coordenada_lat, coordenada_lon)
            VALUES (:id, :id_seccion, :tipo, :dano_parcial, :dano_total,
                    :necesidades_inmediatas, :observaciones,
                    :fotografia, :coordenada_lat, :coordenada_lon)
            ON CONFLICT (id_seccion) DO UPDATE SET
                tipo = EXCLUDED.tipo,
                dano_parcial = EXCLUDED.dano_parcial,
                dano_total = EXCLUDED.dano_total,
                necesidades_inmediatas = EXCLUDED.necesidades_inmediatas,
                observaciones = EXCLUDED.observaciones,
                fotografia = EXCLUDED.fotografia,
                coordenada_lat = EXCLUDED.coordenada_lat,
                coordenada_lon = EXCLUDED.coordenada_lon
        """), {
            "id": lid, "id_seccion": id_seccion,
            "tipo": s.get("tipo", ""),
            "dano_parcial": s.get("dano_parcial", False), "dano_total": s.get("dano_total", False),
            "necesidades_inmediatas": s.get("necesidades_inmediatas", ""),
            "observaciones": s.get("observaciones", ""),
            "fotografia": s.get("fotografia"),
            "coordenada_lat": s.get("coordenada_lat"),
            "coordenada_lon": s.get("coordenada_lon"),
        })

    # 8. Unidades Educativas (1:N) - UPSERT por id_seccion
    for u in loc.get("unidades_educativas") or []:
        id_seccion = u.get("id_seccion")
        db.execute(text("""
            INSERT INTO edan.edan_localidades_unidades_educativas
                (id_edan_localidad, id_seccion, nombre_establecimiento, comunidad, dano_parcial, dano_total,
                 suspension_clases, perdida_material, funciona_albergue,
                 estudiantes, profesores, administrativos, observaciones,
                 fotografia, coordenada_lat, coordenada_lon)
            VALUES (:id, :id_seccion, :nombre_establecimiento, :comunidad, :dano_parcial, :dano_total,
                    :suspension_clases, :perdida_material, :funciona_albergue,
                    :estudiantes, :profesores, :administrativos, :observaciones,
                    :fotografia, :coordenada_lat, :coordenada_lon)
            ON CONFLICT (id_seccion) DO UPDATE SET
                nombre_establecimiento = EXCLUDED.nombre_establecimiento,
                comunidad = EXCLUDED.comunidad,
                dano_parcial = EXCLUDED.dano_parcial,
                dano_total = EXCLUDED.dano_total,
                suspension_clases = EXCLUDED.suspension_clases,
                perdida_material = EXCLUDED.perdida_material,
                funciona_albergue = EXCLUDED.funciona_albergue,
                estudiantes = EXCLUDED.estudiantes,
                profesores = EXCLUDED.profesores,
                administrativos = EXCLUDED.administrativos,
                observaciones = EXCLUDED.observaciones,
                fotografia = EXCLUDED.fotografia,
                coordenada_lat = EXCLUDED.coordenada_lat,
                coordenada_lon = EXCLUDED.coordenada_lon
        """), {
            "id": lid, "id_seccion": id_seccion,
            "nombre_establecimiento": u.get("nombre_establecimiento", ""),
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

    # 9. Daños Vivienda (1:N) - UPSERT por id_seccion
    for v in loc.get("danos_vivienda") or []:
        id_seccion = v.get("id_seccion")
        db.execute(text("""
            INSERT INTO edan.edan_localidades_danos_vivienda
                (id_edan_localidad, id_seccion, comunidad, dano_parcial, dano_total,
                 necesidades_inmediatas, observaciones,
                 fotografia, coordenada_lat, coordenada_lon)
            VALUES (:id, :id_seccion, :comunidad, :dano_parcial, :dano_total,
                    :necesidades_inmediatas, :observaciones,
                    :fotografia, :coordenada_lat, :coordenada_lon)
            ON CONFLICT (id_seccion) DO UPDATE SET
                comunidad = EXCLUDED.comunidad,
                dano_parcial = EXCLUDED.dano_parcial,
                dano_total = EXCLUDED.dano_total,
                necesidades_inmediatas = EXCLUDED.necesidades_inmediatas,
                observaciones = EXCLUDED.observaciones,
                fotografia = EXCLUDED.fotografia,
                coordenada_lat = EXCLUDED.coordenada_lat,
                coordenada_lon = EXCLUDED.coordenada_lon
        """), {
            "id": lid, "id_seccion": id_seccion,
            "comunidad": v.get("comunidad", ""),
            "dano_parcial": v.get("dano_parcial", 0), "dano_total": v.get("dano_total", 0),
            "necesidades_inmediatas": v.get("necesidades_inmediatas", ""),
            "observaciones": v.get("observaciones", ""),
            "fotografia": v.get("fotografia"),
            "coordenada_lat": v.get("coordenada_lat"),
            "coordenada_lon": v.get("coordenada_lon"),
        })

    # 10. Daños Agricultura (1:N) - UPSERT por id_seccion
    for a in loc.get("danos_agricultura") or []:
        id_seccion = a.get("id_seccion")
        db.execute(text("""
            INSERT INTO edan.edan_localidades_danos_agricultura
                (id_edan_localidad, id_seccion, tipo_cultivo, id_cultivo,
                 hectareas_afectadas, hectareas_perdidas, necesidades_inmediatas, observaciones,
                 fotografia, coordenada_lat, coordenada_lon)
            VALUES (:id, :id_seccion, :tipo_cultivo, :id_cultivo,
                    :hectareas_afectadas, :hectareas_perdidas, :necesidades_inmediatas, :observaciones,
                    :fotografia, :coordenada_lat, :coordenada_lon)
            ON CONFLICT (id_seccion) DO UPDATE SET
                tipo_cultivo = EXCLUDED.tipo_cultivo,
                id_cultivo = EXCLUDED.id_cultivo,
                hectareas_afectadas = EXCLUDED.hectareas_afectadas,
                hectareas_perdidas = EXCLUDED.hectareas_perdidas,
                necesidades_inmediatas = EXCLUDED.necesidades_inmediatas,
                observaciones = EXCLUDED.observaciones,
                fotografia = EXCLUDED.fotografia,
                coordenada_lat = EXCLUDED.coordenada_lat,
                coordenada_lon = EXCLUDED.coordenada_lon
        """), {
            "id": lid, "id_seccion": id_seccion,
            "tipo_cultivo": a.get("tipo_cultivo", ""),
            "id_cultivo": a.get("id_cultivo"),
            "hectareas_afectadas": a.get("hectareas_afectadas", 0),
            "hectareas_perdidas": a.get("hectareas_perdidas", 0),
            "necesidades_inmediatas": a.get("necesidades_inmediatas", ""),
            "observaciones": a.get("observaciones", ""),
            "fotografia": a.get("fotografia"),
            "coordenada_lat": a.get("coordenada_lat"),
            "coordenada_lon": a.get("coordenada_lon"),
        })

    # 11. Daños Pecuario (1:N) - UPSERT por id_seccion
    for p in loc.get("danos_pecuarios") or []:
        id_seccion = p.get("id_seccion")
        db.execute(text("""
            INSERT INTO edan.edan_localidades_danos_pecuario
                (id_edan_localidad, id_seccion, especie, id_especie, raza,
                 animales_afectados, animales_muertos, necesidades_inmediatas,
                 fotografia, coordenada_lat, coordenada_lon)
            VALUES (:id, :id_seccion, :especie, :id_especie, :raza,
                    :animales_afectados, :animales_muertos, :necesidades_inmediatas,
                    :fotografia, :coordenada_lat, :coordenada_lon)
            ON CONFLICT (id_seccion) DO UPDATE SET
                especie = EXCLUDED.especie,
                id_especie = EXCLUDED.id_especie,
                raza = EXCLUDED.raza,
                animales_afectados = EXCLUDED.animales_afectados,
                animales_muertos = EXCLUDED.animales_muertos,
                necesidades_inmediatas = EXCLUDED.necesidades_inmediatas,
                fotografia = EXCLUDED.fotografia,
                coordenada_lat = EXCLUDED.coordenada_lat,
                coordenada_lon = EXCLUDED.coordenada_lon
        """), {
            "id": lid, "id_seccion": id_seccion,
            "especie": p.get("especie", ""),
            "id_especie": p.get("id_especie"), "raza": p.get("raza", ""),
            "animales_afectados": p.get("animales_afectados", 0),
            "animales_muertos": p.get("animales_muertos", 0),
            "necesidades_inmediatas": p.get("necesidades_inmediatas", ""),
            "fotografia": p.get("fotografia"),
            "coordenada_lat": p.get("coordenada_lat"),
            "coordenada_lon": p.get("coordenada_lon"),
        })

    # 12. Infra Productiva (1:N) - UPSERT por id_seccion
    for i in loc.get("infra_productiva") or []:
        id_seccion = i.get("id_seccion")
        db.execute(text("""
            INSERT INTO edan.edan_localidades_infra_productiva
                (id_edan_localidad, id_seccion, tipo, dano_parcial, dano_total,
                 fotografia, coordenada_lat, coordenada_lon)
            VALUES (:id, :id_seccion, :tipo, :dano_parcial, :dano_total,
                    :fotografia, :coordenada_lat, :coordenada_lon)
            ON CONFLICT (id_seccion) DO UPDATE SET
                tipo = EXCLUDED.tipo,
                dano_parcial = EXCLUDED.dano_parcial,
                dano_total = EXCLUDED.dano_total,
                fotografia = EXCLUDED.fotografia,
                coordenada_lat = EXCLUDED.coordenada_lat,
                coordenada_lon = EXCLUDED.coordenada_lon
        """), {
            "id": lid, "id_seccion": id_seccion,
            "tipo": i.get("tipo", ""),
            "dano_parcial": i.get("dano_parcial", 0), "dano_total": i.get("dano_total", 0),
            "fotografia": i.get("fotografia") or None,
            "coordenada_lat": i.get("coordenada_lat") or None,
            "coordenada_lon": i.get("coordenada_lon") or None,
        })

    # 13. Proteccion (1:N) - UPSERT por id_seccion
    for p in loc.get("proteccion") or []:
        if not isinstance(p, dict):
            continue
        id_seccion = p.get("id_seccion")
        db.execute(text("""
            INSERT INTO edan.edan_localidades_proteccion
                (id_edan_localidad, id_seccion, id_grupo_vulnerable_catalogo, mujeres, hombres, total,
                 apoyo_psicologico, reposicion_documentos, observaciones)
            VALUES (:id, :id_seccion, :id_grupo_vulnerable_catalogo, :mujeres, :hombres, :total,
                    :apoyo_psicologico, :reposicion_documentos, :observaciones)
            ON CONFLICT (id_seccion) DO UPDATE SET
                id_grupo_vulnerable_catalogo = EXCLUDED.id_grupo_vulnerable_catalogo,
                mujeres = EXCLUDED.mujeres,
                hombres = EXCLUDED.hombres,
                total = EXCLUDED.total,
                apoyo_psicologico = EXCLUDED.apoyo_psicologico,
                reposicion_documentos = EXCLUDED.reposicion_documentos,
                observaciones = EXCLUDED.observaciones
        """), {
            "id": lid, "id_seccion": id_seccion,
            "id_grupo_vulnerable_catalogo": p.get("id_grupo_vulnerable_catalogo"),
            "mujeres": p.get("mujeres", 0), "hombres": p.get("hombres", 0),
            "total": p.get("total", 0),
            "apoyo_psicologico": p.get("apoyo_psicologico"),
            "reposicion_documentos": p.get("reposicion_documentos"),
            "observaciones": p.get("observaciones", ""),
        })

    # 14. Necesidad Humanitaria (1:1) - UPSERT por id_seccion o id_edan_localidad
    nh = loc.get("necesidad_humanitaria")
    if nh:
        id_seccion = nh.get("id_seccion")
        cols = ", ".join(_NH_FIELDS)
        ph = ", ".join(f":{k}" for k in _NH_FIELDS)
        update_set = ", ".join(f"{k} = EXCLUDED.{k}" for k in _NH_FIELDS)
        if id_seccion:
            db.execute(text(f"""
                INSERT INTO edan.edan_localidades_necesidades_humanitarias
                    (id_edan_localidad, id_seccion, {cols}) VALUES (:id, :id_seccion, {ph})
                ON CONFLICT (id_seccion) DO UPDATE SET id_edan_localidad = EXCLUDED.id_edan_localidad, {update_set}
            """), {"id": lid, "id_seccion": id_seccion, **{k: nh.get(k, False if not k.startswith("obs_") else "") for k in _NH_FIELDS}})
        else:
            db.execute(text(f"""
                INSERT INTO edan.edan_localidades_necesidades_humanitarias
                    (id_edan_localidad, {cols}) VALUES (:id, {ph})
                ON CONFLICT (id_edan_localidad) DO UPDATE SET {update_set}
            """), {"id": lid, **{k: nh.get(k, False if not k.startswith("obs_") else "") for k in _NH_FIELDS}})


# ============================================================================
#  CREAR ITEM INDIVIDUAL (para endpoints con-foto)
#  Cada función inserta UN solo registro y retorna la fila creada.
#  Usado por POST /localidades/{id}/<tipo>/con-foto.
# ============================================================================

def _insert_single_row(db: Session, table: str, columns: list[str], data: dict,
                       expand: dict | None = None) -> dict:
    """Inserta o actualiza una fila en una tabla de items de daño/servicio.
    
    Si id_seccion está presente en data, usa UPSERT (ON CONFLICT id_seccion DO UPDATE).
    Si no, hace INSERT normal (compatibilidad).
    
    Args:
        expand: dict opcional de campos a expandir. Ej:
            {"id_cultivo": ("shared.cultivo", "id", ["id", "nombre", "grupo"]),
             "id_especie": ("shared.pecuario", "id", ["id", "nombre", "grupo"])}
    """
    id_seccion = data.get("id_seccion")
    # Solo se envía lo que viene con valor (no None): en INSERT aplican los
    # DEFAULT de la BD; en UPDATE se omiten las columnas ausentes/null (sync
    # no-destructivo a nivel de campo).
    present = [k for k in columns if data.get(k) is not None]
    # LWW por sección: la app envía su fecha UTC de edición. El servidor adopta
    # la del cliente si es más nueva que la actual (GREATEST); si no viene,
    # usa la fecha actual de persistencia.
    fmod = data.get("fecha_modificacion") if data.get("fecha_modificacion") else None
    f_ph = ":fmod" if fmod else "NOW()"
    f_val = {"fmod": fmod} if fmod else {}

    if id_seccion:
        # UPSERT sin ON CONFLICT: primero UPDATE por id_seccion; si la fila no
        # existe, INSERT (los campos ausentes toman el DEFAULT de la BD).
        params = {"id_sec": id_seccion, "id_loc": data["_id"]}
        if present:
            update_set = ", ".join(f"{k} = :{k}" for k in present)
            update_set += f", fecha_modificacion = GREATEST(fecha_modificacion, {f_ph})"
            params |= {k: data[k] for k in present}
            params |= f_val
            result = db.execute(
                text(f"""
                    UPDATE edan.{table} SET {update_set}
                    WHERE id_seccion = :id_sec AND id_edan_localidad = :id_loc
                    RETURNING *
                """),
                params,
            ).mappings().first()
        else:
            result = None
        if not result:
            cols = ", ".join(["id_seccion"] + present + ["fecha_modificacion"])
            ph = ", ".join([":id_seccion"] + [f":{k}" for k in present] + [f_ph])
            result = db.execute(
                text(f"""
                    INSERT INTO edan.{table} (id_edan_localidad, {cols})
                    VALUES (:id, {ph})
                    RETURNING *
                """),
                {"id": data["_id"], "id_seccion": id_seccion}
                | {k: data[k] for k in present}
                | f_val,
            ).mappings().first()
    else:
        # INSERT normal (compatibilidad con código existente)
        cols = ", ".join(present + ["fecha_modificacion"])
        ph = ", ".join([f":{k}" for k in present] + [f_ph])
        params = {"id": data["_id"]} | {k: data[k] for k in present if k != "id_edan_localidad"} | f_val
        result = db.execute(
            text(f"""
                INSERT INTO edan.{table} (id_edan_localidad, {cols})
                VALUES (:id, {ph})
                RETURNING *
            """),
            params,
        ).mappings().first()
    
    db.commit()
    _marcar_impacto(db, data["_id"], table)
    db.commit()
    row = dict(result) if result else {}
    if expand and row:
        for fk_col, (cat_table, cat_pk, cat_cols) in expand.items():
            fk_val = row.get(fk_col)
            if fk_val:
                sel = ", ".join(cat_cols)
                cat_row = _row(db, f"SELECT {sel} FROM {cat_table} WHERE {cat_pk} = :id", {"id": fk_val})
                row[fk_col.replace("id_", "")] = dict(cat_row) if cat_row else None
        # Campo de compat 'rango' (nombre del catálogo) para impacto_poblacion
        ge = row.get("grupo_etario")
        if isinstance(ge, dict) and ge.get("nombre"):
            row["rango"] = ge["nombre"]
    return row


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
         "coordenada_lat", "coordenada_lon"], data,
        expand={"id_cultivo": ("shared.cultivo", "id", ["id", "nombre", "grupo"])})


def create_dano_pecuario(db: Session, id_localidad: int, data: dict) -> dict:
    data["_id"] = id_localidad
    return _insert_single_row(db, "edan_localidades_danos_pecuario",
        ["especie", "id_especie", "raza", "animales_afectados", "animales_muertos",
         "necesidades_inmediatas", "fotografia", "coordenada_lat", "coordenada_lon"], data,
        expand={"id_especie": ("shared.pecuario", "id", ["id", "nombre", "grupo"])})


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


def create_proteccion(db: Session, id_localidad: int, data: dict) -> dict:
    data["_id"] = id_localidad
    return _insert_single_row(db, "edan_localidades_proteccion",
        ["id_grupo_vulnerable_catalogo", "mujeres", "hombres", "total",
         "apoyo_psicologico", "reposicion_documentos", "observaciones"], data,
        expand={"id_grupo_vulnerable_catalogo": ("edan.grupo_vulnerable", "id_grupo_vulnerable",
                ["id_grupo_vulnerable", "codigo", "nombre", "orden", "activo"])})


def update_proteccion(db: Session, id_grupo_vulnerable: int, data: dict) -> dict | None:
    fields = {k: v for k, v in data.items() if v is not None and k != "_id"}
    if not fields:
        row = _row(db, "SELECT * FROM edan.edan_localidades_proteccion WHERE id_grupo_vulnerable = :id",
                   {"id": id_grupo_vulnerable})
        return dict(row) if row else None
    set_clause = ", ".join(f"{k} = :{k}" for k in fields)
    db.execute(text(f"UPDATE edan.edan_localidades_proteccion SET {set_clause} WHERE id_grupo_vulnerable = :pk"),
               {**fields, "pk": id_grupo_vulnerable})
    db.commit()
    row = _row(db, "SELECT * FROM edan.edan_localidades_proteccion WHERE id_grupo_vulnerable = :id",
               {"id": id_grupo_vulnerable})
    return dict(row) if row else None


def delete_proteccion(db: Session, id_grupo_vulnerable: int) -> bool:
    result = db.execute(text("DELETE FROM edan.edan_localidades_proteccion WHERE id_grupo_vulnerable = :id"),
                        {"id": id_grupo_vulnerable})
    db.commit()
    return result.rowcount > 0


# ============================================================================
#  SYNC INCREMENTAL POR SECCIONES
#  API de segmentos (cabecera + sección = UPSERT por id_seccion, no-destructivo).
# ============================================================================

def _seccion_error_detail(exc: Exception) -> str:
    """Traduce un error de BD a mensaje limpio (sufijo de router._db_error)."""
    if isinstance(exc, HTTPException):
        return exc.detail
    try:
        code = getattr(exc.orig, "sqlstate", None) or getattr(exc.orig, "pgcode", None)
    except AttributeError:
        code = None
    if code == "23503":
        return "El registro referenciado no existe (violación de clave foránea)"
    if code == "23505":
        return "Ya existe un registro con el mismo valor (violación de unicidad)"
    if code == "23502":
        return "Falta un campo obligatorio"
    if code == "23514":
        return "Valor no permitido (restricción CHECK)"
    return "Error al procesar la solicitud"


def _normalize_list(payload) -> list:
    """Acepta un objeto único o una lista de objetos (grupo de una sección)."""
    if payload is None:
        return []
    return payload if isinstance(payload, list) else [payload]


def _upsert_11(db: Session, table: str, id_localidad: int, data: dict,
               columns: list[str], value_defaults: dict | None = None) -> dict:
    """UPSERT de 1 sola fila en una tabla 1:1 (PR/SN/NH) por id_seccion,
    con fallback por id_edan_localidad cuando no viene id_seccion.
    No-destructivo: el UPDATE solo toca los campos enviados (no resetea a
    default los ausentes); el INSERT completo (con defaults) aplica cuando
    la fila aún no existe."""
    value_defaults = value_defaults or {}
    id_seccion = data.get("id_seccion")
    present = [k for k in columns if data.get(k) is not None]
    insert_cols = columns
    vals = {k: (data.get(k) if data.get(k) is not None else value_defaults.get(k, False))
            for k in insert_cols}
    # LWW por sección 1:1 (misma regla que _insert_single_row).
    fmod = data.get("fecha_modificacion") if data.get("fecha_modificacion") else None
    f_ph = ":fmod" if fmod else "NOW()"
    f_val = {"fmod": fmod} if fmod else {}

    row = None
    if id_seccion:
        if present:
            update_set = ", ".join(f"{k} = :{k}" for k in present)
            update_set += f", fecha_modificacion = GREATEST(fecha_modificacion, {f_ph})"
            params = {"id_sec": id_seccion, "id_loc": id_localidad,
                      **{k: data[k] for k in present}, **f_val}
            row = db.execute(text(f"""
                UPDATE edan.{table} SET {update_set}
                WHERE id_seccion = :id_sec AND id_edan_localidad = :id_loc
                RETURNING *
            """), params).mappings().first()
        if not row:
            all_cols = ["id_seccion"] + insert_cols + ["fecha_modificacion"]
            row = db.execute(text(f"""
                INSERT INTO edan.{table} (id_edan_localidad, {", ".join(all_cols)})
                VALUES (:id, :id_seccion, {", ".join(f":{k}" for k in insert_cols)}, {f_ph})
                RETURNING *
            """), {"id": id_localidad, "id_seccion": id_seccion, **vals, **f_val}).mappings().first()
    else:
        if present:
            update_set = ", ".join(f"{k} = :{k}" for k in present)
            update_set += f", fecha_modificacion = GREATEST(fecha_modificacion, {f_ph})"
            params = {"id_loc": id_localidad, **{k: data[k] for k in present}, **f_val}
            row = db.execute(text(f"""
                UPDATE edan.{table} SET {update_set}
                WHERE id_edan_localidad = :id_loc
                RETURNING *
            """), params).mappings().first()
        if not row:
            row = db.execute(text(f"""
                INSERT INTO edan.{table} (id_edan_localidad, {", ".join(insert_cols)}, fecha_modificacion)
                VALUES (:id, {", ".join(f":{k}" for k in insert_cols)}, {f_ph})
                RETURNING *
            """), {"id": id_localidad, **vals, **f_val}).mappings().first()
    db.commit()
    _marcar_impacto(db, id_localidad, table)
    db.commit()
    return dict(row) if row else {}


def create_impacto_poblacion(db: Session, id_localidad: int, data: dict) -> dict:
    data["_id"] = id_localidad
    id_ge = _resolve_grupo_etario(db, data)
    if id_ge is not None:
        data["id_grupo_etario"] = id_ge
    return _insert_single_row(db, "edan_localidades_impacto_poblacion",
        ["id_grupo_etario", "fallecidos", "heridos", "desaparecidos", "observaciones"], data,
        expand={"id_grupo_etario": ("edan.grupo_etario", "id_grupo_etario",
                ["id_grupo_etario", "codigo", "nombre", "orden", "activo"])})


def create_primera_respuesta(db: Session, id_localidad: int, data: dict) -> dict:
    return _upsert_11(db, "edan_localidades_primera_respuesta", id_localidad, data,
        ["busqueda", "salvamento", "evacuacion", "observaciones"],
        value_defaults={"observaciones": ""})


def create_necesidad_salud(db: Session, id_localidad: int, data: dict) -> dict:
    return _upsert_11(db, "edan_localidades_salud_necesidades", id_localidad, data,
        ["numero_personas", "otras_necesidades", "observaciones"],
        value_defaults={"otras_necesidades": "", "observaciones": ""})


def create_necesidad_humanitaria(db: Session, id_localidad: int, data: dict) -> dict:
    nh_defaults = {k: ("" if k.startswith("obs_") else False) for k in _NH_FIELDS}
    return _upsert_11(db, "edan_localidades_necesidades_humanitarias", id_localidad, data,
        _NH_FIELDS, value_defaults=nh_defaults)


def upsert_seccion_batch(db: Session, id_localidad: int,
                         seccion_fn, payload, defaults: dict | None = None) -> dict:
    """UPSERT de un grupo de items de una misma sección. Aísla errores por fila
    (nunca falla el lote completo) y devuelve results + errors por índice.

    `defaults` rellena los campos ausentes (None) de cada fila para no violar
    NOT NULL cuando el cliente omite un campo numérico/bool/texto."""
    items = _normalize_list(payload)
    if not items:
        return {"results": [], "errors": []}
    results: list = []
    errors: list = []
    for i, item in enumerate(items):
        row = dict(item)
        for k, v in (defaults or {}).items():
            if row.get(k) is None:
                row[k] = v
        row["_id"] = id_localidad
        try:
            results.append(seccion_fn(db, id_localidad, row))
        except Exception as e:
            db.rollback()
            errors.append({"index": i, "detail": _seccion_error_detail(e)})
    if results:
        _bump_localidad_fecha(db, id_localidad)
        db.commit()
    return {"results": results, "errors": errors}


def delete_seccion_item(db: Session, table: str, id_localidad: int,
                        id_seccion: str) -> bool:
    result = db.execute(text(f"""
        DELETE FROM edan.{table} WHERE id_edan_localidad = :id AND id_seccion = :id_seccion
    """), {"id": id_localidad, "id_seccion": id_seccion})
    deleted = result.rowcount > 0
    if deleted:
        _bump_localidad_fecha(db, id_localidad)
        db.commit()
        _marcar_impacto(db, id_localidad, table)
        db.commit()
    return deleted


def delete_seccion_todo(db: Session, table: str, id_localidad: int) -> int:
    """Borra TODA la sección de la localidad (vale para 1:1 y clear-all 1:N)."""
    result = db.execute(text(f"DELETE FROM edan.{table} WHERE id_edan_localidad = :id"),
                        {"id": id_localidad})
    n = result.rowcount
    if n:
        _bump_localidad_fecha(db, id_localidad)
        db.commit()
        _marcar_impacto(db, id_localidad, table)
        db.commit()
    return n


def _resolve_localidad_id(db: Session, id_localidad: str) -> int:
    """Resuelve id_localidad (puede ser id_edan_localidad int o id_local UUID).
    
    Para modo offline-first: si el cliente envía id_local (UUID), busca
    la cabecera y devuelve id_edan_localidad. Si no existe, lanza 400
    para que el cliente reintente después (la cabecera puede estar en camino).
    
    Para modo online: si el cliente envía id_edan_localidad (int), lo usa directo.
    """
    try:
        id_int = int(id_localidad)
        row = _row(db, "SELECT id_edan_localidad FROM edan.edan_localidades WHERE id_edan_localidad = :id", {"id": id_int})
        if row:
            return row["id_edan_localidad"]
    except (ValueError, TypeError):
        pass
    
    row = _row(db, "SELECT id_edan_localidad FROM edan.edan_localidades WHERE id_local = :id_local", {"id_local": id_localidad})
    if not row:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail="Cabecera no encontrada. Envía POST /cabecera primero o reintenta.",
            headers={"X-Retry-After": "2"}
        )
    return row["id_edan_localidad"]


def _existe_localidad(db: Session, id_localidad: int) -> bool:
    return bool(_row(db, "SELECT 1 FROM edan.edan_localidades WHERE id_edan_localidad = :id",
                     {"id": id_localidad}))


def upsert_cabecera(db: Session, data: dict) -> dict | None:
    """Crea o actualiza SOLO la cabecera del edan_localidad (por id_local).
    Nunca toca secciones."""
    external_id = data.get("id_local")
    existing = _localidad_by_id_local(db, external_id) if external_id else None
    if existing:
        lid = existing["id_edan_localidad"]
        parent = _row(db, "SELECT id_edan FROM edan.edan_localidades WHERE id_edan_localidad = :id",
                      {"id": lid})
        _inherit_localidad_header(db, data, parent["id_edan"] if parent else None)
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
            "id": lid,
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
        if parent and parent["id_edan"] is not None:
            _bump_edan_fecha(db, parent["id_edan"])
        db.commit()
        return _build_localidad(db, lid)
    lid = _insert_localidad(db, None, data)
    if external_id:
        db.execute(text("""
            UPDATE edan.edan_localidades SET id_local = :id_local
            WHERE id_edan_localidad = :id
        """), {"id_local": external_id, "id": lid})
    db.commit()
    return _build_localidad(db, lid)


def _map_localidad_by_id_local(db: Session, id_local: str) -> dict | None:
    row = _localidad_by_id_local(db, id_local)
    if not row:
        return None
    return _build_localidad(db, row["id_edan_localidad"])


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
        "pendiente_eliminacion": data.get("pendiente_eliminacion"),
        "pendiente_actualizacion": data.get("pendiente_actualizacion"),
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

    if data.get("id_usuario") is None:
        data["id_usuario"] = uid

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


def cambiar_estado_localidad_por_id_local(db: Session, id_local: str, id_estado: int) -> dict | None:
    """Cambia el estado de una localidad usando id_local (clave offline del móvil)."""
    st = _row(db, "SELECT id_edan_localidad_estado FROM edan.edan_localidades_estado"
                  " WHERE id_edan_localidad_estado = :id", {"id": id_estado})
    if not st:
        raise HTTPException(status_code=404, detail="Estado de localidad no encontrado")
    cur = _row(db, "SELECT id_edan_localidad, id_edan FROM edan.edan_localidades WHERE id_local = :id_local",
               {"id_local": id_local})
    if not cur:
        return None
    db.execute(text("""
        UPDATE edan.edan_localidades SET id_edan_localidad_estado = :est,
            fecha_modificacion = NOW(), pendiente_actualizacion = TRUE
        WHERE id_local = :id_local
    """), {"est": id_estado, "id_local": id_local})
    if cur["id_edan"] is not None:
        _bump_edan_fecha(db, cur["id_edan"])
    db.commit()
    return _build_localidad(db, cur["id_edan_localidad"])


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
                         estado_nombre: str | None = None,
                         id_estado: int | None = None):
    """Localidades huérfanas sin EDAN, agrupadas por (tipo_evento, municipio),
    listas para consolidar.

    Filtros:
      - estado_nombre: ILIKE contra edan_localidades_estado.nombre (ej: "aprobado"
        matchea "Aprobado UGR" y "Aprobado Ajuste UGR"). None = todos los estados.
      - id_estado: ID exacto de edan_localidad_estado. Tiene prioridad sobre estado_nombre.
    """
    conds = ["l.id_edan IS NULL"]
    params: dict = {}
    if id_municipio is not None:
        conds.append("l.id_municipio = :id_municipio")
        params["id_municipio"] = id_municipio
    if id_estado is not None:
        conds.append("l.id_edan_localidad_estado = :id_estado")
        params["id_estado"] = id_estado
    elif estado_nombre:
        conds.append("""l.id_edan_localidad_estado IN (
            SELECT id_edan_localidad_estado FROM edan.edan_localidades_estado
            WHERE LOWER(nombre) LIKE LOWER(:estado_patron)
        )""")
        params["estado_patron"] = f"{estado_nombre}%"
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


def listar_localidades_municipio(db: Session, id_municipio: int,
                                  id_tipo_evento: int | None = None,
                                  id_estado: int | None = None,
                                  estado_nombre: str | None = None,
                                  solo_huerfanas: bool | None = None,
                                  id_usuario: int | None = None,
                                  con_foto: bool | None = None,
                                  skip: int = 0, limit: int = 50):
    """Todas las localidades de un municipio (huérfanas + consolidadas),
    de todos los usuarios. Retorna la estructura completa con 14 secciones."""
    conds = ["l.id_municipio = :id_municipio"]
    params: dict = {"id_municipio": id_municipio}
    if id_tipo_evento is not None:
        conds.append("l.id_tipo_evento = :id_tipo_evento")
        params["id_tipo_evento"] = id_tipo_evento
    if id_estado is not None:
        conds.append("l.id_edan_localidad_estado = :id_estado")
        params["id_estado"] = id_estado
    elif estado_nombre:
        conds.append("""l.id_edan_localidad_estado IN (
            SELECT id_edan_localidad_estado FROM edan.edan_localidades_estado
            WHERE LOWER(nombre) LIKE LOWER(:estado_patron)
        )""")
        params["estado_patron"] = f"{estado_nombre}%"
    if solo_huerfanas is True:
        conds.append("l.id_edan IS NULL")
    elif solo_huerfanas is False:
        conds.append("l.id_edan IS NOT NULL")
    if id_usuario is not None:
        conds.append("l.id_usuario = :id_usuario")
        params["id_usuario"] = id_usuario
    if con_foto is True:
        conds.append("""EXISTS (
            SELECT 1 FROM edan.edan_localidades_danos_viales v WHERE v.id_edan_localidad = l.id_edan_localidad AND v.fotografia IS NOT NULL
        ) OR EXISTS (
            SELECT 1 FROM edan.edan_localidades_danos_infra_publica ip WHERE ip.id_edan_localidad = l.id_edan_localidad AND ip.fotografia IS NOT NULL
        ) OR EXISTS (
            SELECT 1 FROM edan.edan_localidades_danos_vivienda vi WHERE vi.id_edan_localidad = l.id_edan_localidad AND vi.fotografia IS NOT NULL
        ) OR EXISTS (
            SELECT 1 FROM edan.edan_localidades_danos_agricultura ag WHERE ag.id_edan_localidad = l.id_edan_localidad AND ag.fotografia IS NOT NULL
        ) OR EXISTS (
            SELECT 1 FROM edan.edan_localidades_danos_pecuario pe WHERE pe.id_edan_localidad = l.id_edan_localidad AND pe.fotografia IS NOT NULL
        ) OR EXISTS (
            SELECT 1 FROM edan.edan_localidades_salud_establecimientos sa WHERE sa.id_edan_localidad = l.id_edan_localidad AND sa.fotografia IS NOT NULL
        ) OR EXISTS (
            SELECT 1 FROM edan.edan_localidades_servicios_basicos sb WHERE sb.id_edan_localidad = l.id_edan_localidad AND sb.fotografia IS NOT NULL
        ) OR EXISTS (
            SELECT 1 FROM edan.edan_localidades_unidades_educativas ue WHERE ue.id_edan_localidad = l.id_edan_localidad AND ue.fotografia IS NOT NULL
        ) OR EXISTS (
            SELECT 1 FROM edan.edan_localidades_infra_productiva ip2 WHERE ip2.id_edan_localidad = l.id_edan_localidad AND ip2.fotografia IS NOT NULL
        )""")
    elif con_foto is False:
        conds.append("""NOT EXISTS (
            SELECT 1 FROM edan.edan_localidades_danos_viales v WHERE v.id_edan_localidad = l.id_edan_localidad AND v.fotografia IS NOT NULL
        ) AND NOT EXISTS (
            SELECT 1 FROM edan.edan_localidades_danos_infra_publica ip WHERE ip.id_edan_localidad = l.id_edan_localidad AND ip.fotografia IS NOT NULL
        ) AND NOT EXISTS (
            SELECT 1 FROM edan.edan_localidades_danos_vivienda vi WHERE vi.id_edan_localidad = l.id_edan_localidad AND vi.fotografia IS NOT NULL
        ) AND NOT EXISTS (
            SELECT 1 FROM edan.edan_localidades_danos_agricultura ag WHERE ag.id_edan_localidad = l.id_edan_localidad AND ag.fotografia IS NOT NULL
        ) AND NOT EXISTS (
            SELECT 1 FROM edan.edan_localidades_danos_pecuario pe WHERE pe.id_edan_localidad = l.id_edan_localidad AND pe.fotografia IS NOT NULL
        ) AND NOT EXISTS (
            SELECT 1 FROM edan.edan_localidades_salud_establecimientos sa WHERE sa.id_edan_localidad = l.id_edan_localidad AND sa.fotografia IS NOT NULL
        ) AND NOT EXISTS (
            SELECT 1 FROM edan.edan_localidades_servicios_basicos sb WHERE sb.id_edan_localidad = l.id_edan_localidad AND sb.fotografia IS NOT NULL
        ) AND NOT EXISTS (
            SELECT 1 FROM edan.edan_localidades_unidades_educativas ue WHERE ue.id_edan_localidad = l.id_edan_localidad AND ue.fotografia IS NOT NULL
        ) AND NOT EXISTS (
            SELECT 1 FROM edan.edan_localidades_infra_productiva ip2 WHERE ip2.id_edan_localidad = l.id_edan_localidad AND ip2.fotografia IS NOT NULL
        )""")
    where = " AND ".join(conds)
    total = db.execute(text(f"""
        SELECT COUNT(*) FROM edan.edan_localidades l WHERE {where}
    """), params).scalar()
    rows = _rows(db, f"""
        SELECT l.id_edan_localidad
        FROM edan.edan_localidades l
        WHERE {where}
        ORDER BY l.fecha_modificacion DESC NULLS LAST, l.id_edan_localidad DESC
        LIMIT :limit OFFSET :skip
    """, {**params, "limit": limit, "skip": skip})
    items = [_build_localidad(db, r["id_edan_localidad"]) for r in rows]
    return items, total


def resumen_localidades_municipio(db: Session, id_municipio: int):
    """Resumen ejecutivo de todas las localidades de un municipio:
    conteos por estado, huérfanas vs consolidadas, totales de población."""
    row = _row(db, """
        SELECT COUNT(*) AS total,
               COUNT(*) FILTER (WHERE l.id_edan IS NULL) AS huerfanas,
               COUNT(*) FILTER (WHERE l.id_edan IS NOT NULL) AS consolidadas,
               COALESCE(SUM(l.total_poblacion_afectada), 0) AS total_poblacion_afectada,
               COALESCE(SUM(l.total_familias_afectadas), 0) AS total_familias_afectadas,
               COALESCE(SUM(l.total_familias_damnificadas), 0) AS total_familias_damnificadas
        FROM edan.edan_localidades l
        WHERE l.id_municipio = :id_municipio
    """, {"id_municipio": id_municipio})
    base = dict(row) if row else {}
    estados_rows = _rows(db, """
        SELECT e.nombre AS estado, COUNT(*) AS cantidad
        FROM edan.edan_localidades l
        JOIN edan.edan_localidades_estado e
             ON e.id_edan_localidad_estado = l.id_edan_localidad_estado
        WHERE l.id_municipio = :id_municipio
        GROUP BY e.nombre, e.orden
        ORDER BY e.orden
    """, {"id_municipio": id_municipio})
    base["por_estado"] = [dict(r) for r in estados_rows]
    eventos_rows = _rows(db, """
        SELECT te.nombre AS tipo_evento, COUNT(*) AS cantidad
        FROM edan.edan_localidades l
        JOIN edan.tipo_evento te ON te.id_tipo_evento = l.id_tipo_evento
        WHERE l.id_municipio = :id_municipio
        GROUP BY te.nombre
        ORDER BY te.nombre
    """, {"id_municipio": id_municipio})
    base["por_tipo_evento"] = [dict(r) for r in eventos_rows]
    return base


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
          AND id_edan_localidad_estado = 3
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
            total_familias_damnificadas, id_usuario_ugr, id_estado)
        VALUES (:codigo_edan, :id_departamento, :id_provincia, :id_municipio,
            :id_tipo_evento, :fecha_llenado, :fecha_evento, :hora_evento,
            :total_poblacion_afectada, :total_familias_afectadas,
            :total_familias_damnificadas, :id_usuario_ugr, :id_estado)
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
    }).scalar()
    db.execute(text(f"""
        UPDATE edan.edan_localidades SET id_edan = :id_edan,
            fecha_modificacion = NOW(), pendiente_actualizacion = TRUE
        WHERE id_edan_localidad IN ({ph})
    """), {**params, "id_edan": id_edan})
    db.commit()
    return get_edan_completo(db, id_edan)


def desconsolidar(db: Session, id_localidad: int) -> dict | None:
    """Desvincula una localidad de su EDAN (la convierte en huérfana de nuevo).
    Si el EDAN queda vacío, lo elimina."""
    loc = _row(db, "SELECT id_edan FROM edan.edan_localidades WHERE id_edan_localidad = :id",
               {"id": id_localidad})
    if not loc:
        raise HTTPException(status_code=404, detail="Localidad no encontrada")
    if not loc["id_edan"]:
        raise HTTPException(status_code=400, detail="La localidad no está consolidada en ningún EDAN")
    id_edan = loc["id_edan"]
    db.execute(text("""
        UPDATE edan.edan_localidades SET id_edan = NULL,
            fecha_modificacion = NOW(), pendiente_actualizacion = TRUE
        WHERE id_edan_localidad = :id
    """), {"id": id_localidad})
    restantes = db.execute(text(
        "SELECT COUNT(*) FROM edan.edan_localidades WHERE id_edan = :id"
    ), {"id": id_edan}).scalar()
    if restantes == 0:
        db.execute(text("DELETE FROM edan.edan WHERE id_edan = :id"), {"id": id_edan})
        db.commit()
        return {"desconsolidada": id_localidad, "edan_eliminado": id_edan}
    _recalcular_totales_edan(db, id_edan)
    db.commit()
    return {"desconsolidada": id_localidad, "edan_restante": id_edan, "localidades_restantes": restantes}


def _recalcular_totales_edan(db: Session, id_edan: int):
    """Recalcula totales del EDAN sumando las localidades que le quedan."""
    agg = _row(db, """
        SELECT COALESCE(SUM(total_poblacion_afectada), 0) AS total_poblacion,
               COALESCE(SUM(total_familias_afectadas), 0) AS total_familias,
               COALESCE(SUM(total_familias_damnificadas), 0) AS total_damnificadas
        FROM edan.edan_localidades WHERE id_edan = :id
    """, {"id": id_edan})
    db.execute(text("""
        UPDATE edan.edan SET total_poblacion_afectada = :pob,
            total_familias_afectadas = :fam, total_familias_damnificadas = :dam,
            fecha_modificacion = NOW()
         WHERE id_edan = :id
    """), {"id": id_edan, "pob": agg["total_poblacion"],
           "fam": agg["total_familias"], "dam": agg["total_damnificadas"]})


def deshacer_consolidacion(db: Session, id_edan: int, id_usuario: int) -> dict:
    """Deshace una consolidación: libera todas las localidades como huérfanas
    y elimina el EDAN. Solo permitido en estado Borrador (id=1)."""
    edan = get_edan(db, id_edan)
    if not edan:
        raise HTTPException(status_code=404, detail="EDAN no encontrado")
    if edan.get("id_estado") != 1:
        raise HTTPException(status_code=400,
                            detail="Solo se puede deshacer EDANs en estado borrador")
    if edan.get("id_usuario_ugr") != id_usuario:
        raise HTTPException(status_code=403,
                            detail="Solo el UGR que consolidó puede deshacer este EDAN")
    docs = _row(db, "SELECT COUNT(*) AS cnt FROM repositorio.documentos WHERE id_edan = :id",
                {"id": id_edan})
    if docs and docs["cnt"] > 0:
        raise HTTPException(status_code=400,
                            detail="Elimine primero los documentos del repositorio")
    count = db.execute(text("""
        UPDATE edan.edan_localidades SET id_edan = NULL,
            fecha_modificacion = NOW(), pendiente_actualizacion = TRUE
        WHERE id_edan = :id
    """), {"id": id_edan}).rowcount
    db.execute(text("DELETE FROM edan.edan WHERE id_edan = :id"), {"id": id_edan})
    db.commit()
    return {"edan_deshecho": id_edan, "localidades_liberadas": count}


def consolidar_auto(db: Session, id_municipio: int, id_tipo_evento: int,
                    id_usuario: int) -> dict:
    """Consolida automáticamente TODAS las localidades huérfanas del mismo
    municipio y tipo de evento que estén en estado aprobado (id=3)."""
    rows = _rows(db, """
        SELECT id_edan_localidad FROM edan.edan_localidades
        WHERE id_edan IS NULL AND id_municipio = :mun AND id_tipo_evento = :ev
          AND id_edan_localidad_estado = 3
        ORDER BY id_edan_localidad
    """, {"mun": id_municipio, "ev": id_tipo_evento})
    if not rows:
        raise HTTPException(status_code=404,
                            detail="No hay localidades consolidables para este municipio/tipo de evento")
    ids = [r["id_edan_localidad"] for r in rows]
    return consolidar(db, id_municipio, id_tipo_evento, ids, id_usuario)


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

# 14 flags 1:1 (uno por tabla de sección), con nombres limpios por tabla.
IMP_FLAGS_NUEVOS = [
    "imp_impacto_poblacion", "imp_salud_establecimientos", "imp_danos_viales",
    "imp_danos_infra_publica", "imp_servicios_basicos", "imp_unidades_educativas",
    "imp_danos_vivienda", "imp_danos_agricultura", "imp_danos_pecuarios",
    "imp_infra_productiva", "imp_proteccion", "imp_primera_respuesta",
    "imp_necesidad_salud", "imp_necesidad_humanitaria",
]

# tabla de sección -> (flag 1:1, [flags legacy agrupados que se mantienen al dia])
IMP_FLAG_POR_TABLA = {
    "edan_localidades_impacto_poblacion": ("imp_impacto_poblacion", ["imp_poblacion"]),
    "edan_localidades_salud_establecimientos": ("imp_salud_establecimientos", ["imp_salud"]),
    "edan_localidades_danos_viales": ("imp_danos_viales", []),
    "edan_localidades_danos_infra_publica": ("imp_danos_infra_publica", ["imp_infraestructura"]),
    "edan_localidades_servicios_basicos": ("imp_servicios_basicos", ["imp_servicios"]),
    "edan_localidades_unidades_educativas": ("imp_unidades_educativas", ["imp_educacion"]),
    "edan_localidades_danos_vivienda": ("imp_danos_vivienda", ["imp_vivienda"]),
    "edan_localidades_danos_agricultura": ("imp_danos_agricultura", ["imp_agropecuario"]),
    "edan_localidades_danos_pecuario": ("imp_danos_pecuarios", ["imp_agropecuario"]),
    "edan_localidades_infra_productiva": ("imp_infra_productiva", []),
    "edan_localidades_proteccion": ("imp_proteccion", ["imp_proteccion"]),
    "edan_localidades_primera_respuesta": ("imp_primera_respuesta", []),
    "edan_localidades_salud_necesidades": ("imp_necesidad_salud", ["imp_salud", "imp_necesidades"]),
    "edan_localidades_necesidades_humanitarias": ("imp_necesidad_humanitaria", ["imp_necesidades"]),
}


def _marcar_impacto(db: Session, id_localidad: int, tabla: str):
    """Replica el/los flag(s) de impacto de una localidad según si su tabla de
    sección tiene al menos una fila. Se invoca tras guardar/borrar una sección
    para que los flags reflejen automáticamente la realidad de los datos."""
    entry = IMP_FLAG_POR_TABLA.get(tabla)
    if not entry:
        return
    nuevo, legacies = entry
    if not _row(db, "SELECT 1 FROM edan.edan_localidades WHERE id_edan_localidad = :id", {"id": id_localidad}):
        return
    count = _row(db, f"SELECT COUNT(*) AS c FROM edan.{tabla} WHERE id_edan_localidad = :id",
                 {"id": id_localidad})["c"] or 0
    val = bool(count > 0)
    cols = list(dict.fromkeys([nuevo] + legacies))
    set_clause = ", ".join(f"{c} = :{c}" for c in cols)
    db.execute(text(f"UPDATE edan.edan_localidades SET {set_clause} WHERE id_edan_localidad = :id"),
               {"id": id_localidad, **{c: val for c in cols}})


def _filters_from_query(
    q: str | None = None,
    id_departamento: int | None = None,
    id_provincia: int | None = None,
    id_municipio: int | None = None,
    id_tipo_evento: int | None = None,
    id_estado: int | None = None,
    estado: str | None = None,
    id_usuario_ugr: int | None = None,
    fecha_evento_desde: str | None = None,
    fecha_evento_hasta: str | None = None,
    fecha_creacion_desde: str | None = None,
    fecha_creacion_hasta: str | None = None,
    pendiente_eliminacion: bool | None = None,
    pendiente_actualizacion: bool | None = None,
    con_foto: bool | None = None,
    sin_foto: bool | None = None,
    imp_poblacion: bool | None = None,
    imp_salud: bool | None = None,
    imp_infraestructura: bool | None = None,
    imp_servicios: bool | None = None,
    imp_educacion: bool | None = None,
    imp_vivienda: bool | None = None,
    imp_agropecuario: bool | None = None,
    imp_proteccion: bool | None = None,
    imp_necesidades: bool | None = None,
    tiene_agricultura: bool | None = None,
    tiene_pecuario: bool | None = None,
) -> dict:
    return {
        "q": q, "id_departamento": id_departamento, "id_provincia": id_provincia,
        "id_municipio": id_municipio, "id_tipo_evento": id_tipo_evento,
        "id_estado": id_estado, "estado": estado, "id_usuario_ugr": id_usuario_ugr,
        "fecha_evento_desde": fecha_evento_desde,
        "fecha_evento_hasta": fecha_evento_hasta,
        "fecha_creacion_desde": fecha_creacion_desde,
        "fecha_creacion_hasta": fecha_creacion_hasta,
        "pendiente_eliminacion": pendiente_eliminacion,
        "pendiente_actualizacion": pendiente_actualizacion,
        "con_foto": con_foto, "sin_foto": sin_foto,
        "imp_poblacion": imp_poblacion, "imp_salud": imp_salud,
        "imp_infraestructura": imp_infraestructura, "imp_servicios": imp_servicios,
        "imp_educacion": imp_educacion, "imp_vivienda": imp_vivienda,
        "imp_agropecuario": imp_agropecuario, "imp_proteccion": imp_proteccion,
        "imp_necesidades": imp_necesidades,
        "tiene_agricultura": tiene_agricultura, "tiene_pecuario": tiene_pecuario,
    }


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
        conds.append(f"""{a}.id_estado IN (
            SELECT id_estado FROM edan.estado_edan WHERE LOWER(nombre) = LOWER(:estado)
        )""")
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
    col = "es.nombre" if order_by == "estado" else f"e.{order_by}"
    direction = "ASC" if str(f.get("order", "desc")).lower() == "asc" else "DESC"
    return f"ORDER BY {col} {direction}"


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
    Incluye `por_estado` (id_edan_localidad_estado + nombre + cantidad) para
    refrescar badges en la web sin recorrer el listado completo.
    """
    row = _row(db, """
        SELECT COUNT(*) AS total_localidades,
               COUNT(*) FILTER (WHERE id_edan IS NULL) AS total_huerfanas,
               COUNT(*) FILTER (WHERE id_edan IS NOT NULL) AS total_consolidadas,
               COALESCE(SUM(total_poblacion_afectada), 0) AS total_poblacion,
               COALESCE(SUM(total_familias_afectadas), 0) AS total_familias,
               COALESCE(SUM(total_familias_damnificadas), 0) AS total_familias_damnificadas,
               COUNT(*) FILTER (WHERE id_edan_localidad_estado IS NOT NULL) AS total_con_estado
        FROM edan.edan_localidades
        WHERE id_usuario = :uid
    """, {"uid": id_usuario})
    por_estado = [dict(r) for r in _rows(db, """
        SELECT l.id_edan_localidad_estado, ele.nombre AS estado, COUNT(*) AS cantidad
        FROM edan.edan_localidades l
        LEFT JOIN edan.edan_localidades_estado ele
            ON ele.id_edan_localidad_estado = l.id_edan_localidad_estado
        WHERE l.id_usuario = :uid
        GROUP BY l.id_edan_localidad_estado, ele.nombre
        ORDER BY COUNT(*) DESC
    """, {"uid": id_usuario})]
    data = dict(row) if row else {}
    data["por_estado"] = por_estado
    return data


def list_mis_localidades_estados(db: Session, id_usuario: int, skip: int = 0, limit: int = 50):
    """Listado LIGERO de localidades del usuario para badges de estado.

    Devuelve solo los campos de cabecera + estado (sin secciones), para
    refrescar rápidamente `id_edan_localidad_estado` en una lista.
    """
    total = db.execute(text("""
        SELECT COUNT(*) FROM edan.edan_localidades WHERE id_usuario = :uid
    """), {"uid": id_usuario}).scalar()
    rows = _rows(db, """
        SELECT l.id_edan_localidad, l.id_local, l.localidad,
               l.id_edan_localidad_estado,
               l.id_edan, l.pendiente_actualizacion,
               l.fecha_modificacion,
               ele.nombre AS estado_localidad_nombre, ele.orden AS estado_localidad_orden
        FROM edan.edan_localidades l
        LEFT JOIN edan.edan_localidades_estado ele
            ON ele.id_edan_localidad_estado = l.id_edan_localidad_estado
        WHERE l.id_usuario = :uid
        ORDER BY l.fecha_modificacion DESC NULLS LAST, l.id_edan_localidad DESC
        LIMIT :limit OFFSET :skip
    """, {"uid": id_usuario, "limit": limit, "skip": skip})
    data = []
    for r in rows:
        item = dict(r)
        item["es_huerfana"] = item.get("id_edan") is None
        if item.get("id_edan_localidad_estado"):
            item["estado_localidad"] = {
                "id_edan_localidad_estado": item["id_edan_localidad_estado"],
                "nombre": item.pop("estado_localidad_nombre"),
                "orden": item.pop("estado_localidad_orden"),
            }
        else:
            item.pop("estado_localidad_nombre", None)
            item.pop("estado_localidad_orden", None)
            item["estado_localidad"] = None
        data.append(item)
    return data, total


def get_mis_resumen_edan(db: Session, id_usuario: int):
    """Resumen de los EDAN (grupos consolidados) del UGR: totales de cabecera,
    `por_estado` de estado_edan y `por_tipo_evento`. Scoped a id_usuario_ugr."""
    row = _row(db, """
        SELECT COUNT(*) AS total_edans,
               COUNT(*) FILTER (WHERE id_estado = 1) AS total_borrador,
               COUNT(*) FILTER (WHERE id_estado = 3) AS total_enviado,
               COUNT(*) FILTER (WHERE id_estado = 4) AS total_aprobado,
               COALESCE(SUM(total_poblacion_afectada), 0) AS total_poblacion_afectada,
               COALESCE(SUM(total_familias_afectadas), 0) AS total_familias_afectadas,
               COALESCE(SUM(total_familias_damnificadas), 0) AS total_familias_damnificadas,
               COALESCE(SUM((SELECT COUNT(*) FROM edan.edan_localidades l
                             WHERE l.id_edan = e.id_edan)), 0) AS total_localidades
        FROM edan.edan e WHERE e.id_usuario_ugr = :uid
    """, {"uid": id_usuario})
    totales = dict(row) if row else {}
    por_estado = [dict(r) for r in _rows(db, """
        SELECT e.id_estado, es.nombre AS estado, COUNT(*) AS cantidad
        FROM edan.edan e
        LEFT JOIN edan.estado_edan es ON es.id_estado = e.id_estado
        WHERE e.id_usuario_ugr = :uid
        GROUP BY e.id_estado, es.nombre ORDER BY cantidad DESC
    """, {"uid": id_usuario})]
    por_tipo_evento = [dict(r) for r in _rows(db, """
        SELECT e.id_tipo_evento, COALESCE(te.nombre, 'Sin tipo') AS tipo_evento, COUNT(*) AS cantidad
        FROM edan.edan e
        LEFT JOIN edan.tipo_evento te ON te.id_tipo_evento = e.id_tipo_evento
        WHERE e.id_usuario_ugr = :uid
        GROUP BY e.id_tipo_evento, te.nombre ORDER BY cantidad DESC
    """, {"uid": id_usuario})]
    return {**totales, "por_estado": por_estado, "por_tipo_evento": por_tipo_evento}


def list_mis_edans_estados(db: Session, id_usuario: int, skip: int = 0, limit: int = 50):
    """Listado LIGERO de EDAN del usuario para badges de estado (estado_edan)."""
    total = db.execute(text("""
        SELECT COUNT(*) FROM edan.edan WHERE id_usuario_ugr = :uid
    """), {"uid": id_usuario}).scalar()
    rows = _rows(db, f"""
        SELECT e.id_edan, e.codigo_edan, e.id_estado, e.id_tipo_evento,
               e.fecha_evento, e.fecha_modificacion, e.id_usuario_ugr,
               es.nombre AS estado_nombre, es.orden AS estado_orden,
               te.nombre AS tipo_evento_nombre
        FROM edan.edan e
        LEFT JOIN edan.estado_edan es ON es.id_estado = e.id_estado
        LEFT JOIN edan.tipo_evento te ON te.id_tipo_evento = e.id_tipo_evento
        WHERE e.id_usuario_ugr = :uid
        ORDER BY e.id_edan DESC LIMIT :limit OFFSET :skip
    """, {"uid": id_usuario, "limit": limit, "skip": skip})
    data = []
    for r in rows:
        item = dict(r)
        tipo = ({"id_tipo_evento": item["id_tipo_evento"], "nombre": item.get("tipo_evento_nombre")}
                if item.get("id_tipo_evento") else None)
        estado = ({"id_estado": item["id_estado"], "nombre": item.pop("estado_nombre"),
                   "orden": item.pop("estado_orden")} if item.get("id_estado") else None)
        item["tipo_evento"] = tipo
        item["estado"] = estado
        item.pop("tipo_evento_nombre", None)
        data.append(item)
    return data, total


def get_mis_localidades(db: Session, id_usuario: int, skip: int = 0, limit: int = 50,
                       solo_huerfanas: bool | None = None, solo_con_datos: bool = False,
                       id_departamento: int | None = None,
                       id_municipio: int | None = None):
    """Lista TODAS las localidades del usuario (huérfanas + consolidadas).

    Args:
        id_usuario: Usuario solicitante.
        skip/limit: Paginación.
        solo_huerfanas: Si True, solo id_edan IS NULL. Si False, solo consolidadas.
                        Si None, devuelve todas.
        solo_con_datos: True (modo comprimido) → cada localidad sale con los 22
                        flags y SOLO las secciones que tienen datos.
        id_departamento: Filtrar por departamento.
        id_municipio: Filtrar por municipio.
    """
    where_extra = ""
    if solo_huerfanas is True:
        where_extra = "AND l.id_edan IS NULL"
    elif solo_huerfanas is False:
        where_extra = "AND l.id_edan IS NOT NULL"
    if id_departamento is not None:
        where_extra += " AND l.id_departamento = :id_departamento"
    if id_municipio is not None:
        where_extra += " AND l.id_municipio = :id_municipio"

    params = {"uid": id_usuario}
    if id_departamento is not None:
        params["id_departamento"] = id_departamento
    if id_municipio is not None:
        params["id_municipio"] = id_municipio

    total = db.execute(text(f"""
        SELECT COUNT(*) FROM edan.edan_localidades l
        WHERE l.id_usuario = :uid {where_extra}
    """), params).scalar()
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
    """, {**params, "limit": limit, "skip": skip})
    return [_sanitizar_doc(_build_localidad(db, r["id_edan_localidad"], solo_con_datos=solo_con_datos)) for r in rows], total


def filtrar_localidades_documento(db: Session,
                                  skip: int = 0, limit: int = 50,
                                  fecha_llenado_desde: date | None = None,
                                  fecha_llenado_hasta: date | None = None,
                                  id_tipo_evento: int | None = None,
                                  id_tipo_localidad: int | None = None,
                                  id_departamento: int | None = None,
                                  id_provincia: int | None = None,
                                  id_municipio: int | None = None,
                                  id_estado: int | None = None,
                                  solo_huerfanas: bool | None = None,
                                  id_usuario: int | None = None):
    """Lista localidades (TODAS, de cualquier usuario) como documento v2
    COMPRIMIDO (cabecera + 22 flags imp_* + solo las secciones con datos),
    aplicando filtros opcionales de la cabecera.

    Filtros (todos opcionales, combinables con AND):
        fecha_llenado_desde/hasta: rango de fecha de llenado del formulario.
        id_tipo_evento, id_tipo_localidad, id_departamento, id_provincia,
        id_municipio, id_estado: igualdad por FK.
        solo_huerfanas: True=id_edan IS NULL, False=id_edan IS NOT NULL.
        id_usuario: si viene, limita a las localidades de ese usuario.
    """
    conds: list[str] = []
    params: dict = {}
    if fecha_llenado_desde is not None:
        conds.append("l.fecha_llenado >= :fecha_llenado_desde")
        params["fecha_llenado_desde"] = fecha_llenado_desde
    if fecha_llenado_hasta is not None:
        conds.append("l.fecha_llenado <= :fecha_llenado_hasta")
        params["fecha_llenado_hasta"] = fecha_llenado_hasta
    if id_tipo_evento is not None:
        conds.append("l.id_tipo_evento = :id_tipo_evento")
        params["id_tipo_evento"] = id_tipo_evento
    if id_tipo_localidad is not None:
        conds.append("l.id_tipo_localidad = :id_tipo_localidad")
        params["id_tipo_localidad"] = id_tipo_localidad
    if id_departamento is not None:
        conds.append("l.id_departamento = :id_departamento")
        params["id_departamento"] = id_departamento
    if id_provincia is not None:
        conds.append("l.id_provincia = :id_provincia")
        params["id_provincia"] = id_provincia
    if id_municipio is not None:
        conds.append("l.id_municipio = :id_municipio")
        params["id_municipio"] = id_municipio
    if id_estado is not None:
        conds.append("l.id_edan_localidad_estado = :id_estado")
        params["id_estado"] = id_estado
    if solo_huerfanas is True:
        conds.append("l.id_edan IS NULL")
    elif solo_huerfanas is False:
        conds.append("l.id_edan IS NOT NULL")
    if id_usuario is not None:
        conds.append("l.id_usuario = :id_usuario")
        params["id_usuario"] = id_usuario
    where = f"WHERE {' AND '.join(conds)}" if conds else ""

    total = db.execute(text(f"""
        SELECT COUNT(*) FROM edan.edan_localidades l {where}
    """), params).scalar()
    rows = _rows(db, f"""
        SELECT l.id_edan_localidad
        FROM edan.edan_localidades l
        {where}
        ORDER BY l.fecha_modificacion DESC NULLS LAST, l.id_edan_localidad DESC
        LIMIT :limit OFFSET :skip
    """, {**params, "limit": limit, "skip": skip})
    items = [_sanitizar_doc(_build_localidad(db, r["id_edan_localidad"], solo_con_datos=True)) for r in rows]
    return items, total


# ============================================================================
#  DOCUMENTO (grupo exclusivo v2): serializar/deserializar la localidad COMPLETA
#  como un JSON simétrico (GET devuelve lo que POST/PUT aceptan).
#  - Secciones SOLO presentes si su flag imp_* = true (o hay datos).
#  - Forma fija: 11 secciones SIEMPRE array (aunque haya 1 solo), 3 SIEMPRE objeto.
#  - LWW por fila de sección + fecha_modificacion top-level (cabecera).
# ============================================================================

# key de _build_localidad -> (forma, tabla backend, create_fn, flag 1:1).
# Las 14 claves coinciden con SECCION_KEYS.
DOCUMENT_SECCION: dict[str, dict] = {
    "impacto_poblacion":            {"forma": "array",  "tabla": "edan_localidades_impacto_poblacion",           "create": create_impacto_poblacion},
    "establecimientos_salud":       {"forma": "array",  "tabla": "edan_localidades_salud_establecimientos",      "create": create_establecimiento_salud},
    "danos_viales":                 {"forma": "array",  "tabla": "edan_localidades_danos_viales",                "create": create_dano_vial},
    "danos_infra_publica":          {"forma": "array",  "tabla": "edan_localidades_danos_infra_publica",         "create": create_dano_infra_publica},
    "servicios_basicos":            {"forma": "array",  "tabla": "edan_localidades_servicios_basicos",           "create": create_servicio_basico},
    "unidades_educativas":          {"forma": "array",  "tabla": "edan_localidades_unidades_educativas",         "create": create_unidad_educativa},
    "danos_vivienda":               {"forma": "array",  "tabla": "edan_localidades_danos_vivienda",              "create": create_dano_vivienda},
    "danos_agricultura":            {"forma": "array",  "tabla": "edan_localidades_danos_agricultura",           "create": create_dano_agricultura},
    "danos_pecuarios":              {"forma": "array",  "tabla": "edan_localidades_danos_pecuario",              "create": create_dano_pecuario},
    "infra_productiva":             {"forma": "array",  "tabla": "edan_localidades_infra_productiva",            "create": create_infra_productiva},
    "proteccion":                   {"forma": "array",  "tabla": "edan_localidades_proteccion",                  "create": create_proteccion},
    "necesidad_primera_respuesta":  {"forma": "objeto", "tabla": "edan_localidades_primera_respuesta",           "create": create_primera_respuesta},
    "necesidad_salud":              {"forma": "objeto", "tabla": "edan_localidades_salud_necesidades",           "create": create_necesidad_salud},
    "necesidad_humanitaria":        {"forma": "objeto", "tabla": "edan_localidades_necesidades_humanitarias",    "create": create_necesidad_humanitaria},
}


def normalize_seccion_doc(key: str, value) -> tuple[list | dict, str]:
    """Coerciona una sección del documento a su forma fija (array u objeto).

    Retorna (valor_normalizado, nullable).
    - 1:N (array): si llega un objeto único se envuelve en [objeto]; si None -> [].
    - 1:1 (objeto): si llega un array de 1 se toma [0]; si array de >1 -> ValueError
      con un mensaje explicativo (el router lo traduce a HTTP 400). None -> None.
    """
    meta = DOCUMENT_SECCION.get(key)
    if meta is None:
        return (value, None)
    if value is None:
        return ([] if meta["forma"] == "array" else None, meta["forma"])
    if meta["forma"] == "array":
        return (value if isinstance(value, list) else [value], "array")
    # objeto (1:1)
    if isinstance(value, list):
        if len(value) == 1:
            return (value[0], "objeto")
        if len(value) > 1:
            raise ValueError(
                f"La sección '{key}' es de relación 1:1 (un solo objeto). Se recibió un "
                f"array de {len(value)} elementos. Envía un solo objeto o un array de 1 elemento."
            )
        return (None, "objeto")
    return (value, "objeto")


def serialize_document(db: Session, id_localidad: int) -> dict:
    """Serializa la localidad como documento completo en modo comprimido
    (solo secciones con datos + fecha_modificacion por fila y top-level).
    Reconstruye cada sección para exponer SOLO `id_seccion` (sin IDs internos)."""
    return _sanitizar_doc(_build_localidad(db, id_localidad, solo_con_datos=True))


def apply_document(db: Session, id_localidad: int | None, doc: dict,
                   id_usuario: int | None = None) -> dict:
    """Deserializa un documento completo y lo persiste (UPSERT por sección con LWW).

    `id_localidad` puede ser:
    - un int (id_edan_localidad) existente → PUT (actualiza esa localidad);
    - None o 0 → POST (crea la localidad por `doc['id_local']` y resuelve el id).

    Reglas:
    - Cabecera: se actualiza con upsert_cabecera (flags imp_* legacy declarados se
      respetan, pero la verdad por datos se impone luego con _marcar_impacto).
    - Secciones: SOLO se procesan las presentes en `doc` (las que su flag = true).
      Cada fila lleva su `fecha_modificacion` (LWW GREATEST); si la fila no la trae,
      se usa el `fecha_modificacion` top-level del documento como fallback.
    - Forma fija: las 1:N se iteran como array; las 1:1 se aplican como objeto.
    - Nunca borra secciones ausentes (flag false sin datos no destruye lo existente).
    """
    if id_usuario is not None:
        doc = {**doc, "id_usuario": doc.get("id_usuario") or id_usuario}
    # Modo PUT: id_localidad ya existe. Forzamos el id_local real de la fila para
    # que upsert_cabecera ACTUALICE esa localidad y NO cree una nueva por un
    # id_local ajeno del documento (evita duplicar localidades en el sync).
    if id_localidad:
        row = _row(db, "SELECT id_local FROM edan.edan_localidades WHERE id_edan_localidad = :id",
                   {"id": id_localidad})
        if not row:
            raise ValueError(f"No existe la localidad id_edan_localidad={id_localidad}")
        if row["id_local"]:
            doc["id_local"] = row["id_local"]
        else:
            doc.pop("id_local", None)
    cabecera = upsert_cabecera(db, doc)
    db.commit()
    if not id_localidad:
        built = cabecera or {}
        id_localidad = built.get("id_edan_localidad")
    if not id_localidad:
        raise ValueError("No se pudo resolver el id_edan_localidad para el documento (falta 'id_local').")

    top_fmod = doc.get("fecha_modificacion") or None
    errors: list[dict] = []
    for key, meta in DOCUMENT_SECCION.items():
        raw = doc.get(key)
        # Solo procesa si el cliente envió la sección.
        if raw is None:
            continue
        try:
            value, _forma = normalize_seccion_doc(key, raw)
            # v2: contrato SIEMPRE COMPACTO exige id_seccion (UUID generado por
            # la app) en CADA sección. Es el único identificador aceptado.
            if _forma == "array":
                vistos: set = set()
                for row in value:
                    isec = (row or {}).get("id_seccion")
                    if not isec or not str(isec).strip():
                        raise ValueError(
                            f"La sección '{key}' es 1:N y requiere 'id_seccion' (UUID offline "
                            f"generado por el cliente) en cada fila. El backend no lo genera."
                        )
                    if isec in vistos:
                        raise ValueError(
                            f"La sección '{key}' tiene 'id_seccion' duplicado ('{isec}') en el "
                            f"mismo payload. Cada fila debe tener un id_seccion único."
                        )
                    vistos.add(isec)
            else:
                item = dict(value or {})
                isec = item.get("id_seccion")
                if not isec or not str(isec).strip():
                    raise ValueError(
                        f"La sección '{key}' es 1:1 y requiere 'id_seccion' (UUID offline "
                        f"generado por el cliente). El backend no lo genera."
                    )
            if meta["forma"] == "array":
                for item in value:
                    row = dict(item or {})
                    if not row.get("fecha_modificacion") and top_fmod:
                        row["fecha_modificacion"] = top_fmod
                    row["_id"] = id_localidad
                    meta["create"](db, id_localidad, row)
            else:
                item = dict(value or {})
                if not item.get("fecha_modificacion") and top_fmod:
                    item["fecha_modificacion"] = top_fmod
                item["_id"] = id_localidad
                meta["create"](db, id_localidad, item)
            db.commit()
        except ValueError as e:
            # Error de contrato (p.ej. sección 1:1 recibida como array de >1).
            # Se propaga para que la ruta responda HTTP 400 con mensaje claro.
            db.rollback()
            raise ValueError(str(e))
        except Exception as e:
            db.rollback()
            errors.append({"seccion": key, "detail": _seccion_error_detail(e)})
            continue
    # Reconciliar los flags reales (verdad por datos) tras persistir secciones.
    for key, meta in DOCUMENT_SECCION.items():
        _marcar_impacto(db, id_localidad, meta["tabla"])
    _bump_localidad_fecha(db, id_localidad)
    db.commit()
    result = _sanitizar_doc(_build_localidad(db, id_localidad, solo_con_datos=True))
    result["_errores"] = errors if errors else []
    return result


def delete_document(db: Session, id_localidad: str) -> None:
    """Elimina físicamente una localidad completa (todo-en-uno) por DELETE versión 2.

    Acepta `id_localidad` como `id_edan_localidad` (int) o `id_local` (UUID),
    igual que GET/PUT /documento. Regla de negocio:
    - Si la localidad NO existe → HTTP 400 (via _resolve_localidad_id).
    - Si está CONSOLIDADA en un EDAN (id_edan NOT NULL) → NO se permite borrar:
      se responde 400/403 para que se elimine desde `DELETE /edan/{id}/localidades/{id}`.
    - Si es huérfana (id_edan NULL) → borrado físico (localidad + todas sus secciones).
    """
    id_edan_localidad = _resolve_localidad_id(db, id_localidad)
    row = _row(db, "SELECT id_edan FROM edan.edan_localidades WHERE id_edan_localidad = :id",
               {"id": id_edan_localidad})
    if row and row["id_edan"] is not None:
        from fastapi import HTTPException as _H
        raise _H(
            status_code=403,
            detail="La localidad está consolidada en un EDAN (id_edan) y no se puede eliminar "
                   "desde el documento. Elimínela con `DELETE /edan/{id}/localidades/{id_localidad}`."
        )
    if not delete_localidad(db, id_edan_localidad):
        raise ValueError(f"No se pudo eliminar la localidad id_edan_localidad={id_edan_localidad}")
    return None


# ============================================================================
#  REPORTES AGREGADOS
# ============================================================================

def _filters_localidades(f: dict, alias: str = "l") -> tuple[list[str], dict]:
    """Condiciones SQL sobre edan.edan_localidades (TODAS las localidades:
    huérfanas + consolidadas). Filtros opcionales y combinables (AND).

    Mapeo desde el filtro v2 de EDAN:
      - id_estado/estado  -> id_edan_localidad_estado
      - fecha_creacion_*  -> fecha_llenado
      - id_usuario        -> id_usuario (autor de la localidad)
      - id_usuario_ugr    -> se IGNORA (reportes abiertos, sin scope por rol)
    """
    conds: list[str] = []
    params: dict = {}
    a = alias

    if f.get("q"):
        conds.append(f"""{a}.localidad ILIKE :q""")
        params["q"] = f"%{f['q']}%"

    for col in ("id_departamento", "id_provincia", "id_municipio",
                "id_tipo_evento", "id_tipo_localidad"):
        if f.get(col) is not None:
            conds.append(f"{a}.{col} = :{col}")
            params[col] = f[col]

    if f.get("id_estado") is not None:
        conds.append(f"{a}.id_edan_localidad_estado = :id_estado")
        params["id_estado"] = f["id_estado"]
    if f.get("estado"):
        conds.append(f"""{a}.id_edan_localidad_estado IN (
            SELECT id_edan_localidad_estado FROM edan.edan_localidades_estado
            WHERE LOWER(nombre) = LOWER(:estado)
        )""")
        params["estado"] = f["estado"]
    if f.get("id_usuario") is not None:
        conds.append(f"{a}.id_usuario = :id_usuario")
        params["id_usuario"] = f["id_usuario"]

    for fecha_from, fecha_to, col in (
        ("fecha_llenado_desde", "fecha_llenado_hasta", "fecha_llenado"),
        ("fecha_creacion_desde", "fecha_creacion_hasta", "fecha_llenado"),
        ("fecha_evento_desde", "fecha_evento_hasta", "fecha_evento"),
    ):
        if f.get(fecha_from):
            conds.append(f"{a}.{col} >= :{fecha_from}")
            params[fecha_from] = f[fecha_from]
        if f.get(fecha_to):
            conds.append(f"{a}.{col} <= :{fecha_to}")
            params[fecha_to] = f[fecha_to]

    if f.get("solo_huerfanas") is True:
        conds.append(f"{a}.id_edan IS NULL")
    elif f.get("solo_huerfanas") is False:
        conds.append(f"{a}.id_edan IS NOT NULL")

    for flag in ("pendiente_eliminacion", "pendiente_actualizacion"):
        if f.get(flag) is not None:
            conds.append(f"{a}.{flag} = :{flag}")
            params[flag] = f[flag]

    for flag in IMP_FLAGS:
        if f.get(flag):
            conds.append(f"{a}.{flag} = TRUE")

    if f.get("tiene_agricultura"):
        conds.append(f"""EXISTS (
            SELECT 1 FROM edan.edan_localidades_danos_agricultura ag
            WHERE ag.id_edan_localidad = {a}.id_edan_localidad
        )""")
    if f.get("tiene_pecuario"):
        conds.append(f"""EXISTS (
            SELECT 1 FROM edan.edan_localidades_danos_pecuario dp
            WHERE dp.id_edan_localidad = {a}.id_edan_localidad
        )""")

    return conds, params


def _where_localidades(f: dict) -> tuple[str, dict]:
    conds, params = _filters_localidades(f or {})
    return (" WHERE " + " AND ".join(conds) if conds else ""), params


def _reporte_where(f: dict) -> tuple[str, dict]:
    conds, params = _filters(f, alias="e")
    return (" WHERE " + " AND ".join(conds) if conds else ""), params


def reporte_resumen(db: Session, f: dict | None = None):
    """Resumen agregado de localidades (TODAS: huérfanas + consolidadas).
    Filtros aplicados sobre la tabla edan.edan_localidades.
    """
    f = f or {}
    where, params = _where_localidades(f)
    
    # Contar localidades totales y desglose
    total = db.execute(text(f"""
        SELECT COUNT(*) AS total_localidades,
               COUNT(*) FILTER (WHERE id_edan IS NULL) AS total_huerfanas,
               COUNT(*) FILTER (WHERE id_edan IS NOT NULL) AS total_consolidadas,
               COALESCE(SUM(total_poblacion_afectada), 0) AS total_poblacion_afectada,
               COALESCE(SUM(total_familias_afectadas), 0) AS total_familias_afectadas,
               COALESCE(SUM(total_familias_damnificadas), 0) AS total_familias_damnificadas
        FROM edan.edan_localidades l{where}
    """), params).mappings().first()
    
    por_estado = [dict(r) for r in _rows(db, f"""
        SELECT l.id_edan_localidad_estado, ele.nombre AS estado, COUNT(*) AS cantidad
        FROM edan.edan_localidades l
        LEFT JOIN edan.edan_localidades_estado ele
            ON ele.id_edan_localidad_estado = l.id_edan_localidad_estado{where}
        GROUP BY l.id_edan_localidad_estado, ele.nombre ORDER BY cantidad DESC
    """, params)]

    por_tipo_evento = [dict(r) for r in _rows(db, f"""
        SELECT l.id_tipo_evento, COALESCE(te.nombre, 'Sin tipo') AS tipo_evento, COUNT(*) AS cantidad
        FROM edan.edan_localidades l
        LEFT JOIN edan.tipo_evento te ON te.id_tipo_evento = l.id_tipo_evento{where}
        GROUP BY l.id_tipo_evento, te.nombre ORDER BY cantidad DESC
    """, params)]

    return {
        "totales": {
            "total_localidades": total["total_localidades"] if total else 0,
            "total_huerfanas": total["total_huerfanas"] if total else 0,
            "total_consolidadas": total["total_consolidadas"] if total else 0,
            "total_poblacion_afectada": total["total_poblacion_afectada"] if total else 0,
            "total_familias_afectadas": total["total_familias_afectadas"] if total else 0,
            "total_familias_damnificadas": total["total_familias_damnificadas"] if total else 0,
        },
        "por_estado": por_estado,
        "por_tipo_evento": por_tipo_evento,
    }


def reporte_geografico(db: Session, f: dict | None = None):
    """Distribución geográfica sobre TODAS las localidades (huérfanas + consolidadas)."""
    f = f or {}
    where, params = _where_localidades(f)
    rows = _rows(db, f"""
        SELECT d.id AS id_departamento, d.nombre AS departamento,
               p.id AS id_provincia, p.nombre AS provincia,
               m.id AS id_municipio, m.nombre AS municipio,
               COUNT(*) AS total_localidades,
               COUNT(*) FILTER (WHERE l.id_edan IS NULL) AS total_huerfanas,
               COUNT(*) FILTER (WHERE l.id_edan IS NOT NULL) AS total_consolidadas,
               COALESCE(SUM(l.total_poblacion_afectada), 0) AS poblacion_afectada,
               COALESCE(SUM(l.total_familias_afectadas), 0) AS familias_afectadas,
               COALESCE(SUM(l.total_familias_damnificadas), 0) AS familias_damnificadas
        FROM edan.edan_localidades l
        LEFT JOIN shared.departamento d ON l.id_departamento = d.id
        LEFT JOIN shared.provincia p ON l.id_provincia = p.id
        LEFT JOIN shared.municipio m ON l.id_municipio = m.id
        {where}
        GROUP BY d.id, d.nombre, p.id, p.nombre, m.id, m.nombre
        ORDER BY d.nombre, p.nombre, m.nombre
    """, params)
    return [dict(r) for r in rows]


def reporte_agricultura(db: Session, f: dict | None = None):
    """Agricultura sobre TODAS las localidades (no solo consolidadas en EDAN)."""
    f = f or {}
    where, params = _where_localidades(f)
    rows = _rows(db, f"""
        SELECT a.tipo_cultivo,
               a.id_cultivo,
               c.nombre AS cultivo_nombre,
               c.grupo AS cultivo_grupo,
               COUNT(*) AS total_registros,
               COALESCE(SUM(a.hectareas_afectadas), 0) AS hectareas_afectadas,
               COALESCE(SUM(a.hectareas_perdidas), 0) AS hectareas_perdidas
        FROM edan.edan_localidades_danos_agricultura a
        JOIN edan.edan_localidades l ON l.id_edan_localidad = a.id_edan_localidad
        LEFT JOIN shared.cultivo c ON c.id = a.id_cultivo
        {where}
        GROUP BY a.tipo_cultivo, a.id_cultivo, c.nombre, c.grupo
        ORDER BY hectareas_afectadas DESC
    """, params)
    return [dict(r) for r in rows]


def reporte_pecuario(db: Session, f: dict | None = None):
    """Pecuario sobre TODAS las localidades (no solo consolidadas en EDAN)."""
    f = f or {}
    where, params = _where_localidades(f)
    rows = _rows(db, f"""
        SELECT a.especie,
               a.id_especie,
               p.nombre AS especie_catalogo,
               p.grupo AS especie_grupo,
               COUNT(*) AS total_registros,
               COALESCE(SUM(a.animales_afectados), 0) AS animales_afectados,
               COALESCE(SUM(a.animales_muertos), 0) AS animales_muertos
        FROM edan.edan_localidades_danos_pecuario a
        JOIN edan.edan_localidades l ON l.id_edan_localidad = a.id_edan_localidad
        LEFT JOIN shared.pecuario p ON p.id = a.id_especie
        {where}
        GROUP BY a.especie, a.id_especie, p.nombre, p.grupo
        ORDER BY animales_afectados DESC
    """, params)
    return [dict(r) for r in rows]


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
grupo_vulnerable_crud = _catalog_crud("grupo_vulnerable", "id_grupo_vulnerable", order_col="orden")
grupo_etario_crud = _catalog_crud("grupo_etario", "id_grupo_etario", order_col="orden")
