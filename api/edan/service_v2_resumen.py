"""APIs de resumen y gráficas EDAN (familia nueva, v2.60) — agregados procesados.

Cuatro endpoints (`api/edan/router_v2_resumen.py`):

    GET /edan/resumen/formularios/contadores   → tarjetas de EDAN localidad
    GET /edan/resumen/formularios/graficas     → gráficas de localidad (+tabla)
    GET /edan/resumen/edan/contadores          → tarjetas de EDAN padre
    GET /edan/resumen/edan/graficas            → gráficas de EDAN padre (+tabla)

Reglas (decididas con el cliente, PLAN §21):

* **SIN scope por rol**: aquí NO aplica la matriz de alcance geográfico.
  Cualquier usuario autenticado (token + permiso READ EDAN) consulta con los
  filtros que quiera; la geografía se abre/cierra por query.
* **Filtros combinables con AND** (`id_departamento` + `id_provincia` +
  `id_municipio` a la vez). Si la combinación es incoherente jerárquicamente
  (municipio de otra provincia, etc.) → **400** con detalle.
* **Todas las gráficas obedecen todos los filtros** y cada una trae su
  **`tabla`** (el agregado que la alimenta). Con `incluir_detalle=true`
  cada gráfica trae además **`tabla_registros`** (filas crudas filtradas,
  paginadas con `detalle_limit`/`detalle_skip`).
* **Tipos abiertos**: cada gráfica entrega `items`, `categorias` y `series`
  (los tres formatos) + `tipos[]` con los renderizables — el frontend usa
  torta, donut, barras, apiladas o línea sobre los MISMOS datos.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from .grupos import GRUPO_FLAG, GRUPO_WIRE_LEGACY, SECCION_FLAG

# ===========================================================================
#  PALETA (color fijo en el backend: misma categoría → mismo color siempre)
# ===========================================================================
COLORES_PALETA = [
    "#0072B2", "#E69F00", "#009E73", "#CC79A7", "#56B4E9",
    "#D55E00", "#F0E442", "#999999", "#661E1E", "#1B9E77",
    "#8C564B", "#7F7F7F", "#BCBD22", "#17BECF", "#9467BD",
]

COLORES_ESTADO_LOCALIDAD = {
    "Borrador": "#94A3B8",
    "En revision UGR": "#F59E00",
    "Enviado UGR": "#3B82F6",
    "Aprobado UGR": "#10B981",
    "Rechazado UGR": "#EF4444",
    "Aprobado Ajuste UGR": "#8B5CF6",
}
COLORES_ESTADO_EDAN = {
    "Pendiente aprobaciones": "#94A3B8",
    "Rechazado": "#EF4444",
    "Aprobado": "#10B981",
    "Observado": "#F59E00",
}
COLORES_GRUPO = {
    "grup_poblacion": "#0072B2", "grup_salud": "#009E73",
    "grup_infraestructura": "#E69F00", "grup_servicios": "#56B4E9",
    "grup_educacion": "#CC79A7", "grup_vivienda": "#D55E00",
    "grup_agropecuario": "#F0E442", "grup_proteccion": "#999999",
    "grup_necesidades": "#661E1E",
}
COLORES_EVENTO_GRUPO = {
    "Biológico": "#009E73", "Cambio climático": "#D55E00",
    "Geológico": "#8B5CF6", "Hidrológico": "#0072B2",
    "Meteorológico": "#56B4E9", "Antrópico y tecnológico": "#EF4444",
    "Otro": "#94A3B8",
}
COLORES_HUMANITARIAS = {
    "Alimentos": "#E69F00", "Refugio / vivienda": "#0072B2",
    "Ropa y cama": "#56B4E9", "Artículos de higiene": "#009E73",
    "Artículos de cocina": "#CC79A7", "Prendas de vestir": "#D55E00",
    "Herramientas": "#999999", "Almacenamiento de agua": "#17BECF",
    "Baños": "#661E1E",
}
COLORES_SI_NO = {"Sí": "#10B981", "No": "#EF4444",
                 "Con": "#10B981", "Sin": "#EF4444",
                 "Huérfana": "#94A3B8", "Consolidada": "#10B981",
                 "Al día": "#10B981", "Pendiente": "#F59E00"}

# ===========================================================================
#  CONJUNTOS DE FILTROS POR TABLA
# ===========================================================================
# Sólo aplican sobre edan.edan_localidades
_F_ONLY = {
    "id_edan_localidad_estado", "estado_localidad", "id_tipo_localidad",
    "solo_huerfanas", "id_usuario",
}
# Sólo aplican sobre edan.edan
_E_ONLY = {
    "id_estado", "estado", "fecha_creacion_desde", "fecha_creacion_hasta",
    "id_usuario_ugr", "id_usuario_alcalde", "id_importacion",
}
# Claves de presentación (nunca son filtros de SQL)
_PRESENTACION = {
    "nivel", "top", "granularidad", "rellenar_vacios", "incluir",
    "incluir_detalle", "detalle_limit", "detalle_skip",
}
# Columnas imp_* (14) + wire imp_* (9) y grupo (9) que se pueden filtrar
_GRUPOS_9 = list(GRUPO_FLAG.keys())
_IMP_14 = list(SECCION_FLAG.keys())
_IMP_9 = list(GRUPO_WIRE_LEGACY.keys())

FEC_F = (
    ("fecha_llenado_desde", "fecha_llenado", ">="),
    ("fecha_llenado_hasta", "fecha_llenado", "<="),
    ("fecha_evento_desde", "fecha_evento", ">="),
    ("fecha_evento_hasta", "fecha_evento", "<="),
    ("fecha_modificacion_desde", "fecha_modificacion", ">="),
    ("fecha_modificacion_hasta", "fecha_modificacion", "<="),
)
FEC_E = FEC_F + (
    ("fecha_creacion_desde", "fecha_creacion", ">="),
    ("fecha_creacion_hasta", "fecha_creacion", "<="),
)

GRANULARES = {"dia": "day", "semana": "week", "mes": "month", "anio": "year"}


# ===========================================================================
#  HELPERS
# ===========================================================================
def _rows(db: Session, query: str, params: dict) -> list:
    return [dict(r) for r in db.execute(text(query), params).mappings().all()]


def _row(db: Session, query: str, params: dict):
    r = db.execute(text(query), params).mappings().first()
    return dict(r) if r else None


def _scalar(db: Session, query: str, params: dict, default=0):
    v = db.execute(text(query), params).scalar()
    return default if v is None else v


def _filtros_aplicados(f: dict) -> dict:
    return {k: v for k, v in (f or {}).items()
            if k not in _PRESENTACION and v is not None}


def _validar_geo(db: Session, f: dict) -> None:
    """400 si id_departamento/provincia/municipio no forman una cadena válida."""
    dep, prov, mun = f.get("id_departamento"), f.get("id_provincia"), f.get("id_municipio")
    if mun is not None:
        row = _row(db, "SELECT id_departamento, id_provincia FROM shared.municipio WHERE id = :m",
                   {"m": mun})
        if not row:
            raise HTTPException(status_code=400, detail=f"El municipio {mun} no existe")
        if prov is not None and row["id_provincia"] != prov:
            raise HTTPException(status_code=400, detail=(
                f"El municipio {mun} no pertenece a la provincia {prov} "
                f"(pertenece a la provincia {row['id_provincia']})"))
        if dep is not None and row["id_departamento"] != dep:
            raise HTTPException(status_code=400, detail=(
                f"El municipio {mun} no pertenece al departamento {dep} "
                f"(pertenece al departamento {row['id_departamento']})"))
        return
    if prov is not None:
        row = _row(db, "SELECT id_departamento FROM shared.provincia WHERE id = :p", {"p": prov})
        if not row:
            raise HTTPException(status_code=400, detail=f"La provincia {prov} no existe")
        if dep is not None and row["id_departamento"] != dep:
            raise HTTPException(status_code=400, detail=(
                f"La provincia {prov} no pertenece al departamento {dep} "
                f"(pertenece al departamento {row['id_departamento']})"))


# ===========================================================================
#  CONSTRUCCIÓN DE CLÁUSULAS WHERE
# ===========================================================================
def _f_where(f: dict, alias: str = "l") -> tuple[str, dict]:
    """Filtros sobre `edan.edan_localidades` (combinados con AND)."""
    a = alias
    conds: list[str] = []
    params: dict = {}

    for col in ("id_departamento", "id_provincia", "id_municipio", "id_tipo_evento",
                "id_tipo_localidad", "id_usuario", "id_edan_localidad_estado"):
        if f.get(col) is not None:
            conds.append(f"{a}.{col} = :{col}")
            params[col] = f[col]

    if f.get("grupo_evento"):
        conds.append(f"""EXISTS (SELECT 1 FROM edan.tipo_evento te
            WHERE te.id_tipo_evento = {a}.id_tipo_evento AND te.grupo = :grupo_evento)""")
        params["grupo_evento"] = f["grupo_evento"]

    for key, col, op in FEC_F:
        if f.get(key):
            if op == "<=":
                conds.append(f"{a}.{col} < CAST(:{key} AS date) + interval '1 day'")
            else:
                conds.append(f"{a}.{col} {op} CAST(:{key} AS timestamp)")
            params[key] = f[key]

    if f.get("estado_localidad"):
        conds.append(f"""{a}.id_edan_localidad_estado IN (
            SELECT id_edan_localidad_estado FROM edan.edan_localidades_estado
            WHERE LOWER(nombre) = LOWER(:estado_localidad))""")
        params["estado_localidad"] = f["estado_localidad"]

    if f.get("q"):
        conds.append(f"{a}.localidad ILIKE :q")
        params["q"] = f"%{f['q']}%"

    if f.get("procedencia"):
        conds.append(f"{a}.procedencia = :procedencia")
        params["procedencia"] = f["procedencia"]

    if f.get("solo_huerfanas") is True:
        conds.append(f"{a}.id_edan IS NULL")
    elif f.get("solo_huerfanas") is False:
        conds.append(f"{a}.id_edan IS NOT NULL")

    for col in ("pendiente_actualizacion", "pendiente_eliminacion"):
        if f.get(col) is not None:
            conds.append(f"{a}.{col} = :{col}")
            params[col] = f[col]

    if f.get("grupo") in _GRUPOS_9:
        conds.append(f"{a}.{f['grupo']} = TRUE")

    for col in _GRUPOS_9:
        if f.get(col) is not None:
            conds.append(f"{a}.{col} = :{col}")
            params[col] = f[col]

    for wire, col in GRUPO_WIRE_LEGACY.items():
        if f.get(wire) is not None:
            conds.append(f"{a}.{col} = :{col}__w")
            params[f"{col}__w"] = f[wire]

    for col in _IMP_14:
        if f.get(col) is not None:
            conds.append(f"{a}.{col} = :{col}")
            params[col] = f[col]

    if f.get("tiene_agricultura") is not None:
        cond = f"""EXISTS (SELECT 1 FROM edan.edan_localidades_danos_agricultura x
            WHERE x.id_edan_localidad = {a}.id_edan_localidad)"""
        conds.append(cond if f["tiene_agricultura"] else f"NOT ({cond})")
    if f.get("tiene_pecuario") is not None:
        cond = f"""EXISTS (SELECT 1 FROM edan.edan_localidades_danos_pecuario x
            WHERE x.id_edan_localidad = {a}.id_edan_localidad)"""
        conds.append(cond if f["tiene_pecuario"] else f"NOT ({cond})")

    _foto = f"""EXISTS (SELECT 1 FROM edan.fotografias fo
            WHERE fo.id_edan_localidad = {a}.id_edan_localidad AND fo.borrado_logico = FALSE)"""
    if f.get("con_foto") is not None:
        conds.append(_foto if f["con_foto"] else f"NOT ({_foto})")
    if f.get("sin_foto") is not None:
        conds.append(f"NOT ({_foto})" if f["sin_foto"] else _foto)

    return (" AND ".join(conds) if conds else "1=1"), params


def _e_where(f: dict, alias: str = "e") -> tuple[str, dict]:
    """Filtros sobre `edan.edan` (combinados con AND)."""
    a = alias
    conds: list[str] = []
    params: dict = {}

    for col in ("id_departamento", "id_provincia", "id_municipio", "id_tipo_evento",
                "id_estado", "id_usuario_ugr", "id_usuario_alcalde", "id_importacion",
                "procedencia"):
        if f.get(col) is not None:
            conds.append(f"{a}.{col} = :{col}")
            params[col] = f[col]

    if f.get("grupo_evento"):
        conds.append(f"""EXISTS (SELECT 1 FROM edan.tipo_evento te
            WHERE te.id_tipo_evento = {a}.id_tipo_evento AND te.grupo = :grupo_evento)""")
        params["grupo_evento"] = f["grupo_evento"]

    for key, col, op in FEC_E:
        if f.get(key):
            if op == "<=":
                conds.append(f"{a}.{col} < CAST(:{key} AS date) + interval '1 day'")
            else:
                conds.append(f"{a}.{col} {op} CAST(:{key} AS timestamp)")
            params[key] = f[key]

    if f.get("estado"):
        conds.append(f"""{a}.id_estado IN (
            SELECT id_estado FROM edan.estado_edan WHERE LOWER(nombre) = LOWER(:estado))""")
        params["estado"] = f["estado"]

    if f.get("q"):
        conds.append(f"""({a}.codigo_edan ILIKE :q OR EXISTS (
            SELECT 1 FROM edan.edan_localidades lq
            WHERE lq.id_edan = {a}.id_edan AND lq.localidad ILIKE :q))""")
        params["q"] = f"%{f['q']}%"

    for col in ("pendiente_actualizacion", "pendiente_eliminacion"):
        if f.get(col) is not None:
            conds.append(f"{a}.{col} = :{col}")
            params[col] = f[col]

    # flags de grupos/secciones → existencia de localidad que los tenga
    if f.get("grupo") in _GRUPOS_9:
        conds.append(f"""EXISTS (SELECT 1 FROM edan.edan_localidades li
            WHERE li.id_edan = {a}.id_edan AND li.{f['grupo']} = TRUE)""")

    def _existe(col: str, valor, sufi: str = "") -> str:
        inner = f"""EXISTS (SELECT 1 FROM edan.edan_localidades li
            WHERE li.id_edan = {a}.id_edan AND li.{col} = :{col}{sufi})"""
        return inner if valor else f"NOT ({inner})"

    for col in _GRUPOS_9:
        if f.get(col) is not None:
            conds.append(_existe(col, f[col]))
            params[col] = f[col]

    for wire, col in GRUPO_WIRE_LEGACY.items():
        if f.get(wire) is not None:
            conds.append(_existe(col, f[wire], "__w"))
            params[f"{col}__w"] = f[wire]

    for col in _IMP_14:
        if f.get(col) is not None:
            conds.append(_existe(col, f[col]))
            params[col] = f[col]

    if f.get("tiene_agricultura") is not None:
        _ag = f"""EXISTS (SELECT 1 FROM edan.edan_localidades la
            JOIN edan.edan_localidades_danos_agricultura x
                 ON x.id_edan_localidad = la.id_edan_localidad
            WHERE la.id_edan = {a}.id_edan)"""
        conds.append(_ag if f["tiene_agricultura"] else f"NOT ({_ag})")
    if f.get("tiene_pecuario") is not None:
        _pe = f"""EXISTS (SELECT 1 FROM edan.edan_localidades la
            JOIN edan.edan_localidades_danos_pecuario x
                 ON x.id_edan_localidad = la.id_edan_localidad
            WHERE la.id_edan = {a}.id_edan)"""
        conds.append(_pe if f["tiene_pecuario"] else f"NOT ({_pe})")

    _foto_e = f"""EXISTS (SELECT 1 FROM edan.edan_localidades la
            JOIN edan.fotografias fo ON fo.id_edan_localidad = la.id_edan_localidad
            WHERE la.id_edan = {a}.id_edan AND fo.borrado_logico = FALSE)"""
    if f.get("con_foto") is not None:
        conds.append(_foto_e if f["con_foto"] else f"NOT ({_foto_e})")
    if f.get("sin_foto") is not None:
        conds.append(f"NOT ({_foto_e})" if f["sin_foto"] else _foto_e)

    return (" AND ".join(conds) if conds else "1=1"), params


def _where_l_con_edan(f: dict) -> tuple[str, dict]:
    """Where de localidades + restringe a las que pertenecen a los EDAN filtrados.

    Sólo se añade el subconjunto de EDAN si hay algún filtro EDAN activo;
    si no, las localidades huérfanas (id_edan NULL) deben seguir contando.
    """
    wl, pl = _f_where(f, "l")
    we, pe = _e_where(f, "e")
    if we != "1=1":
        wl = (f"{wl} AND l.id_edan IN "
              f"(SELECT e.id_edan FROM edan.edan e WHERE {we})")
        pl = {**pl, **pe}
    return wl, pl


# ===========================================================================
#  EMPAQUETADO DE GRÁFICAS (items + categorias + series + tabla)
# ===========================================================================
def _color_de(spec: dict, label: Any, idx: int) -> str:
    cm = spec.get("color_map")
    if cm:
        for k, v in cm.items():
            if str(k) == str(label):
                return v
        return spec.get("color", COLORES_PALETA[idx % len(COLORES_PALETA)])
    return spec.get("color") or COLORES_PALETA[idx % len(COLORES_PALETA)]


def _tabla(col_label: str, extra: list[tuple[str, str]], metricas: list[tuple[str, str, str]],
           rows: list[dict], con_pct: bool) -> dict:
    cols = [col_label] + [n for _, n in extra] + [m[1] for m in metricas]
    if con_pct:
        cols.append("porcentaje")
    filas = []
    base = 0
    if len(metricas) == 1:
        base = sum((r.get(metricas[0][0]) or 0) for r in rows)
    for r in rows:
        item = {col_label: r.get(col_label)}
        for c, n in extra:
            item[n] = r.get(c)
        for c, n, _ in metricas:
            item[n] = r.get(c)
        if con_pct:
            v = (r.get(metricas[0][0]) or 0)
            item["porcentaje"] = round(v * 100 / base, 2) if base else 0.0
        filas.append(item)
    return {"columnas": cols, "filas": filas}


def _pack(spec: dict, rows: list[dict]) -> dict:
    """Una query con GROUP BY -> gráfica con items/categorias/series/tabla."""
    label_col = spec.get("label_col", "label")
    metricas = spec.get("metricas") or [
        ("value", spec.get("eje_y") or spec.get("unidad") or "valor",
         spec.get("color", "#0072B2"))]
    extra = spec.get("extra", [])
    orden = spec.get("orden", "desc")
    orden_labels = spec.get("orden_labels")

    if orden == "desc" or orden == "asc":
        key = (lambda r: (r.get(metricas[0][0]) or 0))
        rows = sorted(rows, key=key, reverse=(orden == "desc"))
    elif orden == "sql":
        pass
    if orden_labels:
        idx = {str(l): i for i, l in enumerate(orden_labels)}
        rows = sorted(rows, key=lambda r: idx.get(str(r.get(label_col)), 999))

    if not rows and spec.get("rellenar_categorias"):
        rows = [{label_col: l, **{m[0]: 0 for m in metricas}} for l in spec["rellenar_categorias"]]

    categorias = [r.get(label_col) for r in rows]
    items = []
    suma = 0
    for i, r in enumerate(rows):
        v = r.get(metricas[0][0]) or 0
        suma += v
        items.append({"label": r.get(label_col), "value": v,
                      "color": _color_de(spec, r.get(label_col), i)})
    if suma:
        for it in items:
            it["porcentaje"] = round(it["value"] * 100 / suma, 2)

    series = [{"label": m[1], "color": m[2], "datos": [(r.get(m[0]) or 0) for r in rows]}
              for m in metricas]

    out = {
        "id": spec["id"],
        "titulo": spec["titulo"],
        "descripcion": spec.get("descripcion", ""),
        "tipos": spec.get("tipos") or _tipos(spec.get("tipo", "barras")),
        "tipo": spec.get("tipo", "barras"),
        "unidad": spec.get("unidad", "registros"),
        "eje_x": spec.get("eje_x", ""),
        "eje_y": spec.get("eje_y", ""),
        "total": len(rows),
        "categorias": categorias,
        "series": series,
        "items": items,
        "tabla": _tabla(spec["label_col"], extra, metricas, rows,
                        con_pct=(len(metricas) == 1)),
    }
    if len(metricas) == 1:
        out["suma"] = suma
    else:
        out["totales_serie"] = {m[1]: sum((r.get(m[0]) or 0) for r in rows)
                                for m in metricas}
    return out


def _pack_tupla(spec: dict, row: dict | None) -> dict:
    """Una sola fila agregada (SUM/COUNT de varios campos) -> categorías."""
    row = row or {}
    cols = spec["tupla"]
    rows = [{"__label": lbl, "__value": (row.get(col) or 0)} for col, lbl, _ in cols]
    spec2 = dict(spec)
    spec2["metricas"] = [("__value", spec.get("eje_y", "valor"), spec.get("color", "#0072B2"))]
    spec2["label_col"] = "__label"
    out = _pack(spec2, rows)
    out["items"] = [{"label": lbl, "value": (row.get(col) or 0), "color": colr}
                    for col, lbl, colr in cols]
    tot = sum(i["value"] for i in out["items"])
    for i in out["items"]:
        i["porcentaje"] = round(i["value"] * 100 / tot, 2) if tot else 0.0
    out["suma"] = tot
    out["tabla"]["columnas"] = [spec.get("col_label", "concepto"), spec.get("eje_y", "valor"), "porcentaje"]
    out["tabla"]["filas"] = [{"concepto": i["label"], spec.get("eje_y", "valor"): i["value"],
                              "porcentaje": i["porcentaje"]} for i in out["items"]]
    return out


def _fmt_periodo(dt, gran: str) -> str:
    d = dt if isinstance(dt, (date, datetime)) else datetime.fromisoformat(str(dt))
    if gran == "dia":
        return d.strftime("%Y-%m-%d")
    if gran == "mes":
        return d.strftime("%Y-%m")
    if gran == "anio":
        return d.strftime("%Y")
    iso = d.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def _sum_mes(d: datetime, n: int) -> datetime:
    m = d.month - 1 + n
    y = d.year + m // 12
    m = m % 12 + 1
    return datetime(y, m, 1)


def _rango_periodos(gran: str, desde, hasta) -> list[datetime]:
    """Lista de instantes (uno por periodo) entre `desde` y `hasta`."""
    if not (desde and hasta):
        return []
    try:
        ini = datetime.fromisoformat(str(desde)[:10])
        fin = datetime.fromisoformat(str(hasta)[:10])
    except Exception:
        return []
    out, cur, guard = [], ini, 0
    while cur <= fin and guard < 5000:
        out.append(datetime(cur.year, 1, 1) if gran == "anio" else cur)
        if gran == "dia":
            cur = cur + timedelta(days=1)
        elif gran == "semana":
            cur = cur + timedelta(days=7)
        elif gran == "mes":
            cur = _sum_mes(cur, 1)
        else:
            cur = _sum_mes(cur, 12)
        guard += 1
    if gran == "anio":
        seen, uniq = set(), []
        for d in out:
            if d.year not in seen:
                seen.add(d.year)
                uniq.append(d)
        return uniq
    return out


def _pack_serie(spec: dict, rows: list[dict], gran: str, desde=None, hasta=None,
                rellenar: bool = True) -> dict:
    """Serie temporal: rows [{periodo, valor}] -> line/area con categorías."""
    data = {}
    for r in rows:
        if r.get("periodo") is None:
            continue
        data[_fmt_periodo(r["periodo"], gran)] = r.get("valor") or 0

    claves = sorted(data)
    if rellenar:
        rango = _rango_periodos(gran, desde, hasta)
        if rango:
            claves = [_fmt_periodo(d, gran) for d in rango]
        elif claves:
            claves = _rellenar(claves, gran)

    etiquetas = {"dia": "Día", "semana": "Semana ISO", "mes": "Mes",
                 "anio": "Año"}[gran]
    spec2 = dict(spec)
    spec2["metricas"] = [("v", spec.get("eje_y", "valor"), spec.get("color", "#0072B2"))]
    spec2["label_col"] = "k"
    spec2["orden"] = "sql"
    out = _pack(spec2, [{"k": k, "v": data.get(k, 0)} for k in claves])
    out["serie_temporal"] = {
        "granularidad": gran,
        "etiqueta_eje_x": etiquetas,
        "rellenada": bool(rango) if rellenar else False,
    }
    return out


def _rellenar(claves: list[str], gran: str) -> list[str]:
    """Completa huecos entre la primera y la última clave observadas."""
    if not claves:
        return claves
    paso = {"dia": timedelta(days=1), "semana": timedelta(days=7)}
    try:
        if gran in paso:
            fmt = (lambda d: d.strftime("%Y-%m-%d")) if gran == "dia" else (
                lambda d: f"{d.isocalendar()[0]}-W{d.isocalendar()[1]:02d}")
            parse = ((lambda s: datetime.strptime(s, "%Y-%m-%d")) if gran == "dia"
                     else (lambda s: datetime.strptime(s + "-1", "%G-W%V-%u")))
            cur, fin = parse(claves[0]), parse(claves[-1])
        else:
            fmt = (lambda d: d.strftime("%Y-%m")) if gran == "mes" else (
                lambda d: d.strftime("%Y"))
            parse = ((lambda s: datetime.strptime(s, "%Y-%m")) if gran == "mes"
                     else (lambda s: datetime.strptime(s, "%Y")))
            cur, fin = parse(claves[0]), parse(claves[-1])
    except Exception:
        return claves
    out, guard = [], 0
    while cur <= fin and guard < 5000:
        out.append(fmt(cur))
        if gran in paso:
            cur = cur + paso[gran]
        elif gran == "mes":
            cur = _sum_mes(cur, 1)
        else:
            cur = _sum_mes(cur, 12)
        guard += 1
    return out or claves


# ===========================================================================
#  TIPOS SUGERIDOS
# ===========================================================================
TIPOS_DISTRIBUCION = ["torta", "donut", "barras", "barras_horizontales", "treemap"]
TIPOS_RANKING = ["barras", "barras_horizontales", "torta", "donut", "treemap", "lollipop"]
TIPOS_COMPARATIVA = ["barras_agrupadas", "barras_apiladas", "barras", "radar"]
TIPOS_SERIE = ["linea", "area", "barras", "barras_acumuladas", "paso"]
TIPOS_SEMFORO = ["torta", "donut", "barras", "indicador"]


def _tipos(tipo: str) -> list[str]:
    return {
        "torta": TIPOS_DISTRIBUCION, "donut": TIPOS_DISTRIBUCION,
        "barras": TIPOS_RANKING, "barras_apiladas": TIPOS_COMPARATIVA,
        "barras_agrupadas": TIPOS_COMPARATIVA, "linea": TIPOS_SERIE,
        "area": TIPOS_SERIE,
    }.get(tipo, TIPOS_DISTRIBUCION)


# ===========================================================================
#  TABLA DE DETALLE (filas crudas) POR FUENTE
# ===========================================================================
# sección -> claves que se sustituyen (columnas que sólo existen vía catálogo)
_DET_EXTRA_JOIN = {
    "edan_localidades_impacto_poblacion":
        "LEFT JOIN edan.grupo_etario ge ON ge.id_grupo_etario = ip.id_grupo_etario",
    "edan_localidades_proteccion":
        "LEFT JOIN edan.grupo_vulnerable gv "
        "ON gv.id_grupo_vulnerable = pp.id_grupo_vulnerable_catalogo",
    "edan_localidades_danos_agricultura":
        "LEFT JOIN shared.cultivo c ON c.id = a.id_cultivo",
    "edan_localidades_danos_pecuario":
        "LEFT JOIN shared.pecuario p ON p.id = d.id_especie",
}

DETALLE_SECCIONES: dict[str, list[tuple[str, str]]] = {
    "edan_localidades_impacto_poblacion": [
        ("ge.nombre", "grupo_etario"), ("ip.fallecidos", "fallecidos"),
        ("ip.heridos", "heridos"), ("ip.desaparecidos", "desaparecidos")],
    "edan_localidades_proteccion": [
        ("gv.nombre", "grupo_vulnerable"), ("pp.mujeres", "mujeres"),
        ("pp.hombres", "hombres"), ("pp.total", "total"),
        ("pp.apoyo_psicologico", "apoyo_psicologico"),
        ("pp.reposicion_documentos", "reposicion_documentos")],
    "edan_localidades_danos_vivienda": [
        ("v.comunidad", "comunidad"), ("v.dano_parcial", "dano_parcial"),
        ("v.dano_total", "dano_total")],
    "edan_localidades_danos_viales": [
        ("v.tramo", "tramo"), ("v.km_danio", "km_danio"),
        ("v.dano_parcial", "dano_parcial"), ("v.dano_total", "dano_total"),
        ("v.via", "via"), ("v.puente", "puente")],
    "edan_localidades_danos_infra_publica": [
        ("v.comunidad", "comunidad"), ("v.tipo_estructura", "tipo_estructura"),
        ("v.dano_parcial", "dano_parcial"), ("v.dano_total", "dano_total")],
    "edan_localidades_servicios_basicos": [
        ("v.tipo", "tipo"), ("v.dano_parcial", "dano_parcial"),
        ("v.dano_total", "dano_total")],
    "edan_localidades_infra_productiva": [
        ("v.tipo", "tipo"), ("v.dano_parcial", "dano_parcial"),
        ("v.dano_total", "dano_total")],
    "edan_localidades_unidades_educativas": [
        ("v.nombre_establecimiento", "establecimiento"), ("v.comunidad", "comunidad"),
        ("v.dano_parcial", "dano_parcial"), ("v.dano_total", "dano_total"),
        ("v.suspension_clases", "suspension_clases"),
        ("v.perdida_material", "perdida_material"), ("v.funciona_albergue", "funciona_albergue"),
        ("v.estudiantes", "estudiantes"), ("v.profesores", "profesores"),
        ("v.administrativos", "administrativos")],
    "edan_localidades_salud_establecimientos": [
        ("v.nombre_establecimiento", "establecimiento"), ("v.comunidad", "comunidad"),
        ("v.nivel_atencion", "nivel_atencion"),
        ("v.dano_parcial", "dano_parcial"), ("v.dano_total", "dano_total"),
        ("v.medicos_afectados", "medicos_afectados"),
        ("v.enfermeras_afectadas", "enfermeras_afectadas"),
        ("v.otros_afectados", "otros_afectados")],
    "edan_localidades_salud_necesidades": [
        ("v.numero_personas", "numero_personas"), ("v.otras_necesidades", "otras_necesidades")],
    "edan_localidades_danos_agricultura": [
        ("COALESCE(c.nombre, a.tipo_cultivo)", "cultivo"), ("c.grupo", "grupo_cultivo"),
        ("a.hectareas_afectadas", "hectareas_afectadas"),
        ("a.hectareas_perdidas", "hectareas_perdidas")],
    "edan_localidades_danos_pecuario": [
        ("COALESCE(p.nombre, d.especie)", "especie"), ("p.grupo", "grupo_especie"),
        ("d.raza", "raza"), ("d.animales_afectados", "animales_afectados"),
        ("d.animales_muertos", "animales_muertos")],
    "edan_localidades_primera_respuesta": [
        ("v.busqueda", "busqueda"), ("v.salvamento", "salvamento"),
        ("v.evacuacion", "evacuacion")],
    "edan_localidades_necesidades_humanitarias": [
        ("v.alimentos", "alimentos"), ("v.refugio_vivienda", "refugio_vivienda"),
        ("v.ropa_cama", "ropa_cama"), ("v.articulos_higiene", "articulos_higiene"),
        ("v.articulos_cocina", "articulos_cocina"), ("v.prendas_vestir", "prendas_vestir"),
        ("v.herramientas", "herramientas"),
        ("v.almacenamiento_agua", "almacenamiento_agua"), ("v.banos", "banos")],
}
_DET_ALIAS = {"edan_localidades_impacto_poblacion": "ip",
              "edan_localidades_proteccion": "pp",
              "edan_localidades_danos_agricultura": "a",
              "edan_localidades_danos_pecuario": "d"}


def _detalle(fuente: str, w: str) -> tuple[str, str]:
    """(SQL de filas, SQL de total) para `tabla_registros`."""
    if fuente == "localidad":
        sql = f"""
            SELECT l.uuid_edan_localidad AS uuid, l.localidad,
                   COALESCE(d.nombre, '') AS departamento,
                   COALESCE(p.nombre, '') AS provincia,
                   COALESCE(m.nombre, '') AS municipio,
                   te.nombre AS tipo_evento, ele.nombre AS estado,
                   l.fecha_evento, l.fecha_llenado, l.fecha_modificacion,
                   l.total_poblacion_afectada AS poblacion_afectada,
                   l.total_familias_afectadas AS familias_afectadas,
                   l.total_familias_damnificadas AS familias_damnificadas,
                   (l.id_edan IS NULL) AS huerfana, l.procedencia,
                   l.id_edan, l.uuid_edan
            FROM edan.edan_localidades l
            LEFT JOIN shared.departamento d ON d.id = l.id_departamento
            LEFT JOIN shared.provincia p ON p.id = l.id_provincia
            LEFT JOIN shared.municipio m ON m.id = l.id_municipio
            LEFT JOIN edan.tipo_evento te ON te.id_tipo_evento = l.id_tipo_evento
            LEFT JOIN edan.edan_localidades_estado ele
                   ON ele.id_edan_localidad_estado = l.id_edan_localidad_estado
            WHERE {w}
            ORDER BY l.fecha_modificacion DESC NULLS LAST, l.id_edan_localidad DESC
        """
        cnt = f"SELECT COUNT(*) FROM edan.edan_localidades l WHERE {w}"
        return sql, cnt

    if fuente == "edan":
        sql = f"""
            SELECT e.uuid_edan, e.codigo_edan,
                   COALESCE(d.nombre, '') AS departamento,
                   COALESCE(p.nombre, '') AS provincia,
                   COALESCE(m.nombre, '') AS municipio,
                   te.nombre AS tipo_evento, es.nombre AS estado,
                   e.fecha_evento, e.fecha_creacion, e.fecha_modificacion,
                   e.total_poblacion_afectada AS poblacion_afectada,
                   e.total_familias_afectadas AS familias_afectadas,
                   e.total_familias_damnificadas AS familias_damnificadas,
                   (SELECT COUNT(*) FROM edan.edan_localidades l
                     WHERE l.id_edan = e.id_edan) AS localidades,
                   ugr.nombre AS responsable_ugr, alc.nombre AS alcalde,
                   e.procedencia, e.id_importacion
            FROM edan.edan e
            LEFT JOIN shared.departamento d ON d.id = e.id_departamento
            LEFT JOIN shared.provincia p ON p.id = e.id_provincia
            LEFT JOIN shared.municipio m ON m.id = e.id_municipio
            LEFT JOIN edan.tipo_evento te ON te.id_tipo_evento = e.id_tipo_evento
            LEFT JOIN edan.estado_edan es ON es.id_estado = e.id_estado
            LEFT JOIN usuarios.usuario ugr ON ugr.id_usuario = e.id_usuario_ugr
            LEFT JOIN usuarios.usuario alc ON alc.id_usuario = e.id_usuario_alcalde
            WHERE {w}
            ORDER BY e.fecha_modificacion DESC NULLS LAST, e.id_edan DESC
        """
        cnt = f"SELECT COUNT(*) FROM edan.edan e WHERE {w}"
        return sql, cnt

    if fuente == "fotografia":
        sql = f"""
            SELECT f.uuid_fotografia AS uuid, l.localidad,
                   COALESCE(m.nombre, '') AS municipio, f.tipo_entidad,
                   f.mime_type, f.tamano_bytes, f.fecha_creacion
            FROM edan.fotografias f
            JOIN edan.edan_localidades l ON l.id_edan_localidad = f.id_edan_localidad
            LEFT JOIN shared.municipio m ON m.id = l.id_municipio
            WHERE {w} AND f.borrado_logico = FALSE
            ORDER BY f.fecha_creacion DESC
        """
        cnt = (f"SELECT COUNT(*) FROM edan.fotografias f "
               f"JOIN edan.edan_localidades l ON l.id_edan_localidad = f.id_edan_localidad "
               f"WHERE {w} AND f.borrado_logico = FALSE")
        return sql, cnt

    if fuente == "vivienda":
        sql = f"""
            SELECT v.uuid_registro AS uuid, l.uuid_edan_localidad AS uuid_localidad,
                   l.localidad, COALESCE(m.nombre, '') AS municipio,
                   v.tipo_dano, v.coordenada_lat, v.coordenada_lon, v.fecha_modificacion
            FROM edan.edan_localidades_viviendas v
            JOIN edan.edan_localidades_danos_vivienda d
                 ON d.id_dano_vivienda = v.id_dano_vivienda
            JOIN edan.edan_localidades l ON l.id_edan_localidad = d.id_edan_localidad
            LEFT JOIN shared.municipio m ON m.id = l.id_municipio
            WHERE {w}
            ORDER BY v.fecha_modificacion DESC NULLS LAST
        """
        cnt = (f"SELECT COUNT(*) FROM edan.edan_localidades_viviendas v "
               f"JOIN edan.edan_localidades_danos_vivienda d "
               f"     ON d.id_dano_vivienda = v.id_dano_vivienda "
               f"JOIN edan.edan_localidades l ON l.id_edan_localidad = d.id_edan_localidad "
               f"WHERE {w}")
        return sql, cnt

    if fuente == "aprobacion":
        sql = f"""
            SELECT a.id_aprobacion, e.uuid_edan, e.codigo_edan, a.nivel, a.estado,
                   a.observacion, a.fecha_ultima_accion, a.fecha_aprobacion,
                   a.fecha_devolucion
            FROM edan.aprobaciones_edan a
            JOIN edan.edan e ON e.id_edan = a.id_edan
            WHERE {w}
            ORDER BY a.fecha_ultima_accion DESC NULLS LAST
        """
        cnt = (f"SELECT COUNT(*) FROM edan.aprobaciones_edan a "
               f"JOIN edan.edan e ON e.id_edan = a.id_edan WHERE {w}")
        return sql, cnt

    if fuente == "importacion":
        sql = f"""
            SELECT il.id_importacion, il.nombre_archivo, il.procedencia,
                   il.fecha_importacion, il.filas_procesadas, il.filas_insertadas,
                   il.filas_actualizadas, il.filas_omitidas, il.errores
            FROM edan.edan_importacion_log il
            WHERE il.id_importacion IN (
                SELECT e.id_importacion FROM edan.edan e
                WHERE {w} AND e.id_importacion IS NOT NULL)
            ORDER BY il.fecha_importacion DESC
        """
        cnt = (f"SELECT COUNT(*) FROM edan.edan_importacion_log il WHERE "
               f"il.id_importacion IN (SELECT e.id_importacion FROM edan.edan e "
               f"WHERE {w} AND e.id_importacion IS NOT NULL)")
        return sql, cnt

    if fuente.startswith("sec:"):
        tabla = fuente[4:]
        al = _DET_ALIAS.get(tabla, "v")
        cols = DETALLE_SECCIONES.get(tabla, [])
        sel = ", ".join(f"{expr} AS {name}" for expr, name in cols)
        joins = _DET_EXTRA_JOIN.get(tabla, "")
        sql = f"""
            SELECT {al}.uuid_registro AS uuid, {al}.uuid_edan_localidad AS uuid_localidad,
                   l.localidad, COALESCE(m.nombre, '') AS municipio, {sel}
            FROM edan.{tabla} {al}
            JOIN edan.edan_localidades l ON l.id_edan_localidad = {al}.id_edan_localidad
            LEFT JOIN shared.municipio m ON m.id = l.id_municipio
            {joins}
            WHERE {w}
            ORDER BY {al}.fecha_modificacion DESC NULLS LAST
        """
        cnt = (f"SELECT COUNT(*) FROM edan.{tabla} {al} "
               f"JOIN edan.edan_localidades l ON l.id_edan_localidad = {al}.id_edan_localidad "
               f"{joins} WHERE {w}")
        return sql, cnt

    raise HTTPException(status_code=500, detail=f"Fuente de detalle desconocida: {fuente}")


def _detalle_tabla(db: Session, fuente: str, w: str, params: dict, opts: dict) -> dict:
    sql, cnt = _detalle(fuente, w)
    total = _scalar(db, cnt, params)
    rows = _rows(db, sql + " LIMIT :dl OFFSET :ds",
                 {**params, "dl": opts.get("detalle_limit", 100),
                  "ds": opts.get("detalle_skip", 0)})
    columnas = list(rows[0].keys()) if rows else []
    return {"columnas": columnas, "filas": rows, "total": total,
            "limit": opts.get("detalle_limit", 100),
            "skip": opts.get("detalle_skip", 0)}


def _armar(db: Session, spec: dict, rows: list[dict] | dict, w: str,
           params: dict, opts: dict, desde=None, hasta=None) -> dict:
    if spec.get("tupla"):
        out = _pack_tupla(spec, rows[0] if rows else None)
    elif spec.get("serie"):
        out = _pack_serie(spec, rows, opts.get("granularidad") or "mes",
                          desde=desde, hasta=hasta,
                          rellenar=bool(opts.get("rellenar_vacios", True)))
    else:
        out = _pack(spec, rows)
    if opts.get("incluir_detalle") and spec.get("fuente"):
        out["tabla_registros"] = _detalle_tabla(db, spec["fuente"], w, params, opts)
    out["grupo"] = spec.get("grupo", "general")
    return out


# rango de desagregación geográfica (mayor = más fino)
_NIVEL_RANK = {"nacional": 1, "departamento": 2, "provincia": 3,
              "municipio": 4, "localidad": 5}


def _elegible(spec: dict, opts: dict, f: dict) -> bool:
    """`incluir` (ids) -> `nivel` (hasta dónde desagregar) -> descarte de
    desagregaciones degeneradas (si ya filtraste por id_X, no desagregues por
    X ni por algo más fino)."""
    if opts.get("incluir") and spec["id"] not in set(opts["incluir"]):
        return False
    geo = _NIVEL_RANK.get(spec.get("geo"), 0)
    nivel = opts.get("nivel")
    if nivel in _NIVEL_RANK and geo > _NIVEL_RANK[nivel]:
        return False
    filtro = 4 if f.get("id_municipio") else (
        3 if f.get("id_provincia") else (2 if f.get("id_departamento") else 0))
    if filtro and geo and geo <= filtro:
        return False
    return True


# ===========================================================================
#  AGRUPACIONES COMPARTIDAS / UTILIDADES DE LISTA
# ===========================================================================
_LJ = """
  LEFT JOIN edan.tipo_evento te ON te.id_tipo_evento = l.id_tipo_evento
  LEFT JOIN edan.edan_localidades_estado ele
         ON ele.id_edan_localidad_estado = l.id_edan_localidad_estado
  LEFT JOIN edan.tipo_localidad tl ON tl.id_tipo_localidad = l.id_tipo_localidad
  LEFT JOIN shared.departamento d ON d.id = l.id_departamento
  LEFT JOIN shared.provincia pr ON pr.id = l.id_provincia
  LEFT JOIN shared.municipio m ON m.id = l.id_municipio
  LEFT JOIN usuarios.usuario u ON u.id_usuario = l.id_usuario
"""

_EJ = """
  LEFT JOIN edan.tipo_evento te ON te.id_tipo_evento = e.id_tipo_evento
  LEFT JOIN edan.estado_edan es ON es.id_estado = e.id_estado
  LEFT JOIN shared.departamento d ON d.id = e.id_departamento
  LEFT JOIN shared.provincia pr ON pr.id = e.id_provincia
  LEFT JOIN shared.municipio m ON m.id = e.id_municipio
  LEFT JOIN usuarios.usuario ugr ON ugr.id_usuario = e.id_usuario_ugr
  LEFT JOIN usuarios.usuario alc ON alc.id_usuario = e.id_usuario_alcalde
"""

_DIAS_SEMANA = ["Domingo", "Lunes", "Martes", "Miércoles", "Jueves",
                "Viernes", "Sábado"]
MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio",
         "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]


def _pf(sql: str, params: dict) -> dict:
    """Sólo los parámetros realmente referenciados en `sql`."""
    import re
    return {k: v for k, v in params.items()
            if re.search(rf":{re.escape(k)}(?![A-Za-z0-9_])", sql)}


def _con_porcentaje(items: list[dict]) -> list[dict]:
    tot = sum(i.get("value") or 0 for i in items)
    for i in items:
        i["porcentaje"] = round((i.get("value") or 0) * 100 / tot, 2) if tot else 0.0
    return items


def _lista(rows: list[dict], etiqueta: str = "label", valor: str = "value",
           color_map: dict | None = None) -> list[dict]:
    items = []
    for i, r in enumerate(rows):
        lab = r.get(etiqueta)
        color = (color_map or {}).get(str(lab))
        if not color:
            color = COLORES_PALETA[i % len(COLORES_PALETA)]
        items.append({"label": lab, "value": r.get(valor) or 0, "color": color})
    return _con_porcentaje(items)


def _de_fila(row: dict | None, cols: list[tuple[str, str, str]]) -> list[dict]:
    row = row or {}
    return _con_porcentaje([{"label": lab, "value": row.get(k) or 0, "color": c}
                            for k, lab, c in cols])


def _rango_fecha(f: dict, campo: str | None) -> tuple:
    if not campo:
        return (f.get("fecha_llenado_desde") or f.get("fecha_evento_desde")
                or f.get("fecha_modificacion_desde"),
                f.get("fecha_llenado_hasta") or f.get("fecha_evento_hasta")
                or f.get("fecha_modificacion_hasta"))
    return (f.get(f"fecha_{campo}_desde"), f.get(f"fecha_{campo}_hasta"))


def _colector(db: Session, w: str, p: dict, opts: dict, f: dict,
              acc: list[dict] | None = None):
    """Devuelve (lista acumulada, add(spec, sql, params, desde, hasta)).

    `add` honra `incluir`/`nivel` (selector de gráficas) y ejecuta la SQL con
    `{w}` ya resuelto; las series temporales toman su rango de `desde`/
    `hasta` o de los filtros de fecha del query. `acc` permite que dos
    colectores (localidades y EDAN) compartan el mismo orden de salida.
    """
    acc: list[dict] = [] if acc is None else acc

    def add(spec: dict, sql: str, params: dict | None = None,
            desde=None, hasta=None, **extra):
        if not _elegible(spec, opts, f):
            return
        if extra:
            spec = {**spec, **extra}
        q = sql.replace("{w}", w)
        pp = _pf(q, {**p, **(params or {})})
        if spec.get("serie") and desde is None:
            desde, hasta = _rango_fecha(f, spec.get("campo_fecha"))
        rows = _rows(db, q, pp)
        acc.append(_armar(db, spec, rows, w, pp, opts, desde=desde, hasta=hasta))

    return acc, add


def _pie(filtros: dict, opts: dict, nivel_geo: str) -> dict:
    return {
        "filtros": _filtros_aplicados(filtros),
        "nivel": nivel_geo or "nacional",
        "granularidad": opts.get("granularidad", "mes"),
        "top": opts.get("top", 15),
        "rellenar_vacios": bool(opts.get("rellenar_vacios", True)),
        "generado_en": datetime.now().isoformat(timespec="seconds"),
    }


def _esp(id_: str, titulo: str, unidad: str, tipo: str = "barras",
         grupo: str = "general", geo: str | None = None, **kw) -> dict:
    """Especificación de gráfica: tipos abiertos + agrupación lógica."""
    s = {"id": id_, "titulo": titulo, "unidad": unidad, "tipo": tipo,
         "tipos": kw.pop("tipos", None) or _tipos(tipo), "grupo": grupo,
         "label_col": kw.pop("label_col", "label"),
         "eje_y": kw.pop("eje_y", unidad), "eje_x": kw.pop("eje_x", "")}
    if geo:
        s["geo"] = geo
    s.update(kw)
    return s


# ===========================================================================
#  TARJETAS DE RESUMEN (contadores)
# ===========================================================================
def contadores_formularios(db: Session, f: dict, opts: dict | None = None) -> dict:
    """Tarjetas de resumen de EDAN localidad (formularios) bajo los filtros."""
    opts = opts or {}
    _validar_geo(db, f)
    w, p = _f_where(f, "l")
    sql = f"""
        SELECT COUNT(*) AS total,
               COUNT(*) FILTER (WHERE l.id_edan IS NULL) AS huerfanas,
               COUNT(*) FILTER (WHERE l.id_edan IS NOT NULL) AS consolidadas,
               COUNT(*) FILTER (WHERE l.pendiente_actualizacion) AS pendientes_actualizacion,
               COUNT(*) FILTER (WHERE l.pendiente_eliminacion) AS pendientes_eliminacion,
               COUNT(*) FILTER (WHERE l.id_edan_localidad_estado = 3) AS aprobadas,
               COUNT(*) FILTER (WHERE EXISTS (
                   SELECT 1 FROM edan.fotografias fo
                   WHERE fo.id_edan_localidad = l.id_edan_localidad
                     AND fo.borrado_logico = FALSE)) AS con_foto,
               COUNT(DISTINCT l.id_departamento) AS departamentos,
               COUNT(DISTINCT l.id_provincia) AS provincias,
               COUNT(DISTINCT l.id_municipio) AS municipios,
               COUNT(DISTINCT l.id_edan) FILTER (WHERE l.id_edan IS NOT NULL) AS edan_vinculados,
               COALESCE(SUM(l.total_poblacion_afectada), 0) AS poblacion_afectada,
               COALESCE(SUM(l.total_familias_afectadas), 0) AS familias_afectadas,
               COALESCE(SUM(l.total_familias_damnificadas), 0) AS familias_damnificadas,
               MIN(l.fecha_llenado) AS primera_fecha_llenado,
               MAX(l.fecha_llenado) AS ultima_fecha_llenado,
               MAX(l.fecha_modificacion) AS ultima_modificacion
        FROM edan.edan_localidades l WHERE {w}
    """
    tot = _row(db, sql, _pf(sql, p)) or {}
    por_estado = _lista(_rows(db, f"""
        SELECT ele.nombre AS label, COUNT(*) AS value
        FROM edan.edan_localidades l
        LEFT JOIN edan.edan_localidades_estado ele
               ON ele.id_edan_localidad_estado = l.id_edan_localidad_estado
        WHERE {w}
        GROUP BY ele.id_edan_localidad_estado, ele.nombre, ele.orden
        ORDER BY ele.orden NULLS LAST
    """, p), color_map=COLORES_ESTADO_LOCALIDAD)
    grow = _row(db, f"""
        SELECT {", ".join(f"COUNT(*) FILTER (WHERE l.{c}) AS {c}" for c in _GRUPOS_9)}
        FROM edan.edan_localidades l WHERE {w}
    """, p)
    por_grupo = _de_fila(grow, [(c, c, COLORES_GRUPO.get(c, "#0072B2"))
                                for c in _GRUPOS_9])
    por_tipo_evento = _lista(_rows(db, f"""
        SELECT COALESCE(te.nombre, 'Sin tipo de evento') AS label, COUNT(*) AS value
        FROM edan.edan_localidades l
        LEFT JOIN edan.tipo_evento te ON te.id_tipo_evento = l.id_tipo_evento
        WHERE {w}
        GROUP BY te.nombre ORDER BY value DESC, label
    """, p))
    por_departamento = _lista(_rows(db, f"""
        SELECT COALESCE(d.nombre, 'Sin departamento') AS label, COUNT(*) AS value
        FROM edan.edan_localidades l
        LEFT JOIN shared.departamento d ON d.id = l.id_departamento
        WHERE {w} GROUP BY d.id, d.nombre ORDER BY value DESC, label
    """, p))
    top = int(opts.get("top") or 15)
    por_municipio = _lista(_rows(db, f"""
        SELECT COALESCE(m.nombre, 'Sin municipio') AS label, COUNT(*) AS value
        FROM edan.edan_localidades l
        LEFT JOIN shared.municipio m ON m.id = l.id_municipio
        WHERE {w} GROUP BY m.id, m.nombre ORDER BY value DESC, label LIMIT {top}
    """, p))

    return {
        **_pie(f, opts, opts.get("nivel")),
        "unidad": "formularios",
        "totales": {
            "total": int(tot.get("total") or 0),
            "huerfanas": int(tot.get("huerfanas") or 0),
            "consolidadas": int(tot.get("consolidadas") or 0),
            "aprobadas": int(tot.get("aprobadas") or 0),
            "pendientes_actualizacion": int(tot.get("pendientes_actualizacion") or 0),
            "pendientes_eliminacion": int(tot.get("pendientes_eliminacion") or 0),
            "con_foto": int(tot.get("con_foto") or 0),
            "poblacion_afectada": int(tot.get("poblacion_afectada") or 0),
            "familias_afectadas": int(tot.get("familias_afectadas") or 0),
            "familias_damnificadas": int(tot.get("familias_damnificadas") or 0),
            "edan_vinculados": int(tot.get("edan_vinculados") or 0),
        },
        "cobertura": {
            "departamentos": int(tot.get("departamentos") or 0),
            "provincias": int(tot.get("provincias") or 0),
            "municipios": int(tot.get("municipios") or 0),
        },
        "periodo": {
            "primera_fecha_llenado": tot.get("primera_fecha_llenado"),
            "ultima_fecha_llenado": tot.get("ultima_fecha_llenado"),
            "ultima_modificacion": tot.get("ultima_modificacion"),
        },
        "por_estado": por_estado,
        "por_grupo": por_grupo,
        "por_tipo_evento": por_tipo_evento,
        "por_departamento": por_departamento,
        "por_municipio": por_municipio,
    }


def contadores_edan(db: Session, f: dict, opts: dict | None = None) -> dict:
    """Tarjetas de resumen de EDAN padre (cabeceras) bajo los filtros."""
    opts = opts or {}
    _validar_geo(db, f)
    w, p = _e_where(f, "e")
    sql = f"""
        SELECT COUNT(*) AS total,
               COUNT(*) FILTER (WHERE e.pendiente_actualizacion) AS pendientes_actualizacion,
               COUNT(*) FILTER (WHERE e.pendiente_eliminacion) AS pendientes_eliminacion,
               COUNT(DISTINCT e.id_departamento) AS departamentos,
               COUNT(DISTINCT e.id_provincia) AS provincias,
               COUNT(DISTINCT e.id_municipio) AS municipios,
               COUNT(DISTINCT e.id_usuario_ugr) AS ugr_responsables,
               COUNT(DISTINCT e.id_usuario_alcalde) AS alcaldes,
               COUNT(DISTINCT e.id_importacion) FILTER (WHERE e.id_importacion IS NOT NULL) AS importaciones,
               COUNT(DISTINCT e.id_tipo_evento) AS tipos_evento,
               COALESCE(SUM(e.total_poblacion_afectada), 0) AS poblacion_afectada,
               COALESCE(SUM(e.total_familias_afectadas), 0) AS familias_afectadas,
               COALESCE(SUM(e.total_familias_damnificadas), 0) AS familias_damnificadas,
               COALESCE(SUM((SELECT COUNT(*) FROM edan.edan_localidades ll
                              WHERE ll.id_edan = e.id_edan)), 0) AS localidades,
               MIN(e.fecha_evento) AS primer_evento,
               MAX(e.fecha_evento) AS ultimo_evento,
               MAX(e.fecha_modificacion) AS ultima_modificacion
        FROM edan.edan e WHERE {w}
    """
    tot = _row(db, sql, _pf(sql, p)) or {}
    sel = set(opts["incluir"]) if opts.get("incluir") else None

    def _opt(clave: str, lista):
        return lista if (sel is None or clave in sel) else []

    por_estado = _lista(_rows(db, f"""
        SELECT COALESCE(es.nombre, 'Sin estado') AS label, COUNT(*) AS value
        FROM edan.edan e LEFT JOIN edan.estado_edan es ON es.id_estado = e.id_estado
        WHERE {w} GROUP BY es.id_estado, es.nombre, es.orden ORDER BY es.orden NULLS LAST
    """, p),
        color_map=COLORES_ESTADO_EDAN)
    por_tipo_evento = _lista(_rows(db, f"""
        SELECT COALESCE(te.nombre, 'Sin tipo de evento') AS label, COUNT(*) AS value
        FROM edan.edan e LEFT JOIN edan.tipo_evento te ON te.id_tipo_evento = e.id_tipo_evento
        WHERE {w} GROUP BY te.nombre ORDER BY value DESC, label
    """, p))
    por_departamento = _lista(_rows(db, f"""
        SELECT COALESCE(d.nombre, 'Sin departamento') AS label, COUNT(*) AS value
        FROM edan.edan e LEFT JOIN shared.departamento d ON d.id = e.id_departamento
        WHERE {w} GROUP BY d.id, d.nombre ORDER BY value DESC, label
    """, p))
    top = int(opts.get("top") or 15)
    por_municipio = _lista(_rows(db, f"""
        SELECT COALESCE(m.nombre, 'Sin municipio') AS label, COUNT(*) AS value
        FROM edan.edan e LEFT JOIN shared.municipio m ON m.id = e.id_municipio
        WHERE {w} GROUP BY m.id, m.nombre ORDER BY value DESC, label LIMIT {top}
    """, p))
    aprob = _rows(db, f"""
        SELECT a.nivel, a.estado, COUNT(*) AS value
        FROM edan.aprobaciones_edan a JOIN edan.edan e ON e.id_edan = a.id_edan
        WHERE {w} GROUP BY a.nivel, a.estado ORDER BY a.nivel, a.estado
    """, p)
    aprob_totales = _de_fila(_row(db, f"""
        SELECT COUNT(*) AS total,
               COUNT(*) FILTER (WHERE a.estado = 'aprobado') AS aprobadas,
               COUNT(*) FILTER (WHERE a.estado = 'pendiente') AS pendientes,
               COUNT(*) FILTER (WHERE a.estado = 'observado') AS observadas,
               COUNT(*) FILTER (WHERE a.estado = 'espera_correccion') AS correccion
        FROM edan.aprobaciones_edan a JOIN edan.edan e ON e.id_edan = a.id_edan
        WHERE {w}
    """, p),
        [("total", "Aprobaciones registradas", "#0072B2"),
         ("aprobadas", "Aprobadas", "#10B981"),
         ("pendientes", "Pendientes", "#F59E00"),
         ("observadas", "Observadas", "#EF4444"),
         ("correccion", "En espera de corrección", "#8B5CF6")])

    return {
        **_pie(f, opts, opts.get("nivel")),
        "unidad": "edan",
        "totales": {
            "total": int(tot.get("total") or 0),
            "localidades": int(tot.get("localidades") or 0),
            "poblacion_afectada": int(tot.get("poblacion_afectada") or 0),
            "familias_afectadas": int(tot.get("familias_afectadas") or 0),
            "familias_damnificadas": int(tot.get("familias_damnificadas") or 0),
            "pendientes_actualizacion": int(tot.get("pendientes_actualizacion") or 0),
            "pendientes_eliminacion": int(tot.get("pendientes_eliminacion") or 0),
            "ugr_responsables": int(tot.get("ugr_responsables") or 0),
            "alcaldes": int(tot.get("alcaldes") or 0),
            "importaciones": int(tot.get("importaciones") or 0),
            "tipos_evento": int(tot.get("tipos_evento") or 0),
        },
        "cobertura": {
            "departamentos": int(tot.get("departamentos") or 0),
            "provincias": int(tot.get("provincias") or 0),
            "municipios": int(tot.get("municipios") or 0),
        },
        "periodo": {
            "primer_evento": tot.get("primer_evento"),
            "ultimo_evento": tot.get("ultimo_evento"),
            "ultima_modificacion": tot.get("ultima_modificacion"),
        },
        "por_estado": _opt("por_estado", por_estado),
        "por_tipo_evento": _opt("por_tipo_evento", por_tipo_evento),
        "por_departamento": _opt("por_departamento", por_departamento),
        "por_municipio": _opt("por_municipio", por_municipio),
        "aprobaciones": {
            "totales": aprob_totales if (sel is None or "aprobaciones" in sel) else [],
            "por_nivel_estado": aprob if (sel is None or "aprobaciones" in sel) else [],
        },
    }


# ===========================================================================
#  ETIQUETAS DE COLUMNAS Y SENTINELA DE WHERE (para f-strings)
# ===========================================================================
W = "{w}"

_ETIQ_SECCION = {
    "imp_impacto_poblacion": "Impacto de población",
    "imp_primera_respuesta": "Primera respuesta",
    "imp_salud_establecimientos": "Establecimientos de salud",
    "imp_necesidad_salud": "Necesidades de salud",
    "imp_danos_viales": "Daños viales",
    "imp_danos_infra_publica": "Infraestructura pública",
    "imp_servicios_basicos": "Servicios básicos",
    "imp_unidades_educativas": "Unidades educativas",
    "imp_danos_vivienda": "Daños en vivienda",
    "imp_danos_agricultura": "Daños en agricultura",
    "imp_danos_pecuarios": "Daños pecuarios",
    "imp_infra_productiva": "Infraestructura productiva",
    "imp_proteccion": "Protección",
    "imp_necesidad_humanitaria": "Necesidades humanitarias",
}
_ETIQ_GRUPO = {
    "grup_poblacion": "Población", "grup_salud": "Salud",
    "grup_infraestructura": "Infraestructura", "grup_servicios": "Servicios básicos",
    "grup_educacion": "Educación", "grup_vivienda": "Vivienda",
    "grup_agropecuario": "Agropecuario", "grup_proteccion": "Protección",
    "grup_necesidades": "Necesidades humanitarias",
}


def _estados_locales(db: Session) -> list[dict]:
    return _rows(db, "SELECT id_edan_localidad_estado AS id, nombre, orden "
                     "FROM edan.edan_localidades_estado ORDER BY orden", {})


def graficas_formularios(db: Session, f: dict, opts: dict | None = None) -> dict:
    """Catálogo de gráficas de EDAN localidad: TODAS obedecen TODOS los
    filtros y cada una entrega `items` + `categorias` + `series` + `tabla`
    (agregado) — sirve para torta, donut, barras, apiladas o línea."""
    opts = opts or {}
    _validar_geo(db, f)
    w, p = _f_where(f, "l")
    g, add = _colector(db, w, p, opts, f)
    top = int(opts.get("top") or 15)
    gran = opts.get("granularidad") or "mes"
    dt = GRANULARES[gran] if gran in GRANULARES else "month"
    FROM_L = f"FROM edan.edan_localidades l {_LJ}"
    estados = _estados_locales(db)
    col_estado = {e["nombre"]: COLORES_ESTADO_LOCALIDAD.get(e["nombre"], "#94A3B8")
                  for e in estados}

    # ---------------------------------------------------------------- estados
    add(_esp("estado_localidad", "Formularios por estado", "formularios",
             "donut", grupo="estados", color_map=col_estado, orden="sql",
             orden_labels=[e["nombre"] for e in estados], fuente="localidad",
             eje_x="Estado", col_label="label"),
        f"""SELECT COALESCE(ele.nombre, 'Sin estado') AS label, COUNT(*) AS value
            {FROM_L} WHERE {W}
            GROUP BY ele.id_edan_localidad_estado, ele.nombre, ele.orden
            ORDER BY ele.orden NULLS LAST""")

    add(_esp("estado_localidad_poblacion", "Población afectada por estado",
             "personas", "barras_apiladas", grupo="estados", fuente="localidad",
             color_map=col_estado, orden="sql",
             orden_labels=[e["nombre"] for e in estados]),
        f"""SELECT COALESCE(ele.nombre, 'Sin estado') AS label,
                   COALESCE(SUM(l.total_poblacion_afectada), 0) AS value
            {FROM_L} WHERE {W}
            GROUP BY ele.id_edan_localidad_estado, ele.nombre, ele.orden
            ORDER BY ele.orden NULLS LAST""")

    add(_esp("estado_por_departamento", "Estados por departamento",
             "formularios", "barras_apiladas", grupo="estados", geo="departamento",
             orden="sql"),
        f"""SELECT COALESCE(d.nombre, 'Sin departamento') AS label,
                   COUNT(*) AS total,
                   {", ".join(f"COUNT(*) FILTER (WHERE l.id_edan_localidad_estado = {e['id']}) AS s{e['id']}" for e in estados)}
            {FROM_L} WHERE {W}
            GROUP BY d.id, d.nombre ORDER BY COUNT(*) DESC LIMIT {top}""",
        metricas=[(f"s{e['id']}", e["nombre"], col_estado[e["nombre"]])
                  for e in estados])

    add(_esp("estado_por_municipio", "Estados por municipio", "formularios",
             "barras_apiladas", grupo="estados", geo="municipio", orden="sql"),
        f"""SELECT COALESCE(m.nombre, 'Sin municipio') AS label,
                   COUNT(*) AS total,
                   {", ".join(f"COUNT(*) FILTER (WHERE l.id_edan_localidad_estado = {e['id']}) AS s{e['id']}" for e in estados)}
            {FROM_L} WHERE {W}
            GROUP BY m.id, m.nombre ORDER BY COUNT(*) DESC LIMIT {top}""",
        metricas=[(f"s{e['id']}", e["nombre"], col_estado[e["nombre"]])
                  for e in estados])

    add(_esp("huerfanas_vs_consolidadas", "Localidades huérfanas vs consolidadas",
             "formularios", "donut", grupo="estados", fuente="localidad",
             col_label="concepto", eje_y="Formularios"),
        f"""SELECT COUNT(*) FILTER (WHERE l.id_edan IS NULL) AS huerfanas,
                   COUNT(*) FILTER (WHERE l.id_edan IS NOT NULL) AS consolidadas
            {FROM_L} WHERE {W}""",
        tupla=[("huerfanas", "Huérfanas (sin EDAN)", "#94A3B8"),
               ("consolidadas", "Consolidadas (con EDAN)", "#10B981")])

    add(_esp("sincronizacion", "Sincronización (pendientes)", "formularios",
             "donut", grupo="sincronizacion", fuente="localidad",
             col_label="concepto", eje_y="Formularios"),
        f"""SELECT COUNT(*) FILTER (WHERE l.pendiente_actualizacion) AS actualizacion,
                   COUNT(*) FILTER (WHERE l.pendiente_eliminacion) AS eliminacion,
                   COUNT(*) FILTER (WHERE NOT l.pendiente_actualizacion
                                    AND NOT l.pendiente_eliminacion) AS al_dia
            {FROM_L} WHERE {W}""",
        tupla=[("actualizacion", "Actualización pendiente", "#F59E00"),
               ("eliminacion", "Eliminación pendiente", "#EF4444"),
               ("al_dia", "Al día", "#10B981")])

    add(_esp("procedencia", "Formularios por procedencia", "formularios",
             "torta", grupo="sincronizacion", fuente="localidad"),
        f"""SELECT COALESCE(l.procedencia, 'sin_procedencia') AS label,
                   COUNT(*) AS value {FROM_L} WHERE {W}
            GROUP BY l.procedencia ORDER BY value DESC""")

    # ---------------------------------------------------------- grupos/secciones
    add(_esp("grupos_activos", "Grupos con actividad (9 grupos)", "formularios",
             "barras_horizontales", grupo="secciones", fuente="localidad",
             col_label="etiqueta", eje_x="Grupo"),
        f"""SELECT {", ".join(f"COUNT(*) FILTER (WHERE l.{c}) AS {c}" for c in _GRUPOS_9)}
            {FROM_L} WHERE {W}""",
        tupla=[(c, _ETIQ_GRUPO[c], COLORES_GRUPO.get(c, "#0072B2"))
               for c in _GRUPOS_9])

    add(_esp("secciones_activas", "Secciones con actividad (14 secciones)",
             "formularios", "barras", grupo="secciones", fuente="localidad",
             orden="sql", col_label="etiqueta"),
        f"""SELECT {", ".join(f"COUNT(*) FILTER (WHERE l.{c}) AS {c}" for c in _IMP_14)}
            {FROM_L} WHERE {W}""",
        tupla=[(c, _ETIQ_SECCION[c], COLORES_PALETA[i % len(COLORES_PALETA)])
               for i, c in enumerate(_IMP_14)])

    # ------------------------------------------------------------------ eventos
    add(_esp("tipo_evento", "Formularios por tipo de evento", "formularios",
             "barras", grupo="eventos", fuente="localidad"),
        f"""SELECT COALESCE(te.nombre, 'Sin tipo de evento') AS label,
                   COUNT(*) AS value {FROM_L} WHERE {W}
            GROUP BY te.id_tipo_evento, te.nombre
            ORDER BY value DESC, label LIMIT {top}""")

    add(_esp("grupo_evento", "Formularios por grupo de evento", "formularios",
             "torta", grupo="eventos", color_map=COLORES_EVENTO_GRUPO,
             orden="sql", fuente="localidad"),
        f"""SELECT COALESCE(te.grupo, 'Sin grupo') AS label, COUNT(*) AS value
            {FROM_L} WHERE {W} GROUP BY te.grupo ORDER BY value DESC, label""")

    add(_esp("categoria_evento", "Formularios por categoría de evento",
             "formularios", "barras_horizontales", grupo="eventos",
             fuente="localidad"),
        f"""SELECT COALESCE(te.categoria, 'Sin categoría') AS label,
                   COUNT(*) AS value {FROM_L} WHERE {W}
            GROUP BY te.categoria ORDER BY value DESC, label LIMIT {top}""")

    add(_esp("tipo_localidad", "Formularios por tipo de localidad",
             "formularios", "barras_horizontales", grupo="eventos",
             fuente="localidad"),
        f"""SELECT COALESCE(tl.nombre, 'Sin tipo') AS label, COUNT(*) AS value
            {FROM_L} WHERE {W} GROUP BY tl.id_tipo_localidad, tl.nombre
            ORDER BY value DESC, label LIMIT {top}""")

    tipos_ev = _rows(db, f"""
        SELECT te.id_tipo_evento AS id, te.nombre
        FROM edan.edan_localidades l
        LEFT JOIN edan.tipo_evento te ON te.id_tipo_evento = l.id_tipo_evento
        WHERE {W} AND te.id_tipo_evento IS NOT NULL
        GROUP BY te.id_tipo_evento, te.nombre ORDER BY te.nombre""".replace("{w}", w), p)
    if tipos_ev:
        add(_esp("tipo_evento_por_departamento", "Tipos de evento por departamento",
                 "formularios", "barras_apiladas", grupo="eventos",
                 geo="departamento", orden="sql",
                 metricas=[(f"t{t['id']}", t["nombre"],
                            COLORES_PALETA[i % len(COLORES_PALETA)])
                           for i, t in enumerate(tipos_ev)]),
            f"""SELECT COALESCE(d.nombre, 'Sin departamento') AS label,
                       {", ".join(f"COUNT(*) FILTER (WHERE l.id_tipo_evento = {t['id']}) AS t{t['id']}" for t in tipos_ev)}
                FROM edan.edan_localidades l
                LEFT JOIN shared.departamento d ON d.id = l.id_departamento
                WHERE {W} GROUP BY d.id, d.nombre
                ORDER BY COUNT(*) DESC LIMIT {top}""")

    # --------------------------------------------------------------- geografía
    add(_esp("localidades_por_departamento", "Formularios por departamento",
             "formularios", "barras", grupo="geografia", geo="departamento",
             fuente="localidad"),
        f"""SELECT COALESCE(d.nombre, 'Sin departamento') AS label, COUNT(*) AS value
            {FROM_L} WHERE {W} GROUP BY d.id, d.nombre ORDER BY value DESC, label""")

    add(_esp("localidades_por_provincia", "Formularios por provincia",
             "formularios", "barras", grupo="geografia", geo="provincia",
             fuente="localidad"),
        f"""SELECT COALESCE(pr.nombre, 'Sin provincia') AS label, COUNT(*) AS value
            {FROM_L} WHERE {W} GROUP BY pr.id, pr.nombre ORDER BY value DESC, label""")

    add(_esp("localidades_por_municipio", "Formularios por municipio",
             "formularios", "barras", grupo="geografia", geo="municipio",
             fuente="localidad"),
        f"""SELECT COALESCE(m.nombre, 'Sin municipio') AS label, COUNT(*) AS value
            {FROM_L} WHERE {W} GROUP BY m.id, m.nombre
            ORDER BY value DESC, label LIMIT {top}""")

    for campo, titulo, geo, col in (
            ("poblacion_afectada", "Población afectada por ", "departamento",
             "l.total_poblacion_afectada"),
            ("familias_afectadas", "Familias afectadas por ", "municipio",
             "l.total_familias_afectadas"),
            ("familias_damnificadas", "Familias damnificadas por ", "municipio",
             "l.total_familias_damnificadas")):
        nodo = "d.nombre" if geo == "departamento" else "m.nombre"
        add(_esp(f"{campo}_por_{geo}", titulo + geo, "personas", "barras",
                 grupo="geografia", geo=geo, fuente="localidad"),
            f"""SELECT COALESCE({nodo}, 'Sin {geo}') AS label,
                       COALESCE(SUM({col}), 0) AS value
                {FROM_L} WHERE {W} GROUP BY {nodo}
                ORDER BY value DESC, label LIMIT {top}""")

    add(_esp("poblacion_por_provincia", "Población afectada por provincia",
             "personas", "barras", grupo="geografia", geo="provincia",
             fuente="localidad"),
        f"""SELECT COALESCE(pr.nombre, 'Sin provincia') AS label,
                   COALESCE(SUM(l.total_poblacion_afectada), 0) AS value
            {FROM_L} WHERE {W} GROUP BY pr.id, pr.nombre
            ORDER BY value DESC, label LIMIT {top}""")

    # ----------------------------------------------------------------- tiempo
    for clave, campo, titulo in (
            ("llenado", "fecha_llenado", "Formularios llenados"),
            ("evento", "fecha_evento", "Formularios por fecha de evento"),
            ("modificacion", "fecha_modificacion", "Formularios modificados")):
        add(_esp(f"serie_{clave}", titulo, "formularios", "linea", grupo="tiempo",
                 serie="periodo", campo_fecha=campo, fuente="localidad",
                 tipos=TIPOS_SERIE + ["torta", "donut"],
                 descripcion=f"Granularidad: {gran}"),
            f"""SELECT date_trunc('{dt}', l.{campo}) AS periodo, COUNT(*) AS valor
                {FROM_L} WHERE {W} AND l.{campo} IS NOT NULL
                GROUP BY 1 ORDER BY 1""")

    add(_esp("mes_llenado", "Formularios por mes de llenado", "formularios",
             "barras", grupo="tiempo", fuente="localidad", orden="sql",
             orden_labels=MESES),
        f"""SELECT EXTRACT(MONTH FROM l.fecha_llenado)::int AS label,
                   COUNT(*) AS value {FROM_L} WHERE {W}
            AND l.fecha_llenado IS NOT NULL GROUP BY 1 ORDER BY 1""")

    add(_esp("mes_evento", "Formularios por mes del evento", "formularios",
             "barras", grupo="tiempo", fuente="localidad", orden="sql",
             orden_labels=MESES),
        f"""SELECT EXTRACT(MONTH FROM l.fecha_evento)::int AS label,
                   COUNT(*) AS value {FROM_L} WHERE {W}
            AND l.fecha_evento IS NOT NULL GROUP BY 1 ORDER BY 1""")

    add(_esp("dia_semana_evento", "Formularios por día de la semana (evento)",
             "formularios", "barras", grupo="tiempo", fuente="localidad",
             orden="sql", orden_labels=_DIAS_SEMANA),
        f"""SELECT EXTRACT(DOW FROM l.fecha_evento)::int AS label,
                   COUNT(*) AS value {FROM_L} WHERE {W}
            AND l.fecha_evento IS NOT NULL GROUP BY 1 ORDER BY 1""")

    add(_esp("hora_evento", "Formularios por hora del evento", "formularios",
             "barras", grupo="tiempo", fuente="localidad", orden="sql",
             orden_labels=list(range(24))),
        f"""SELECT EXTRACT(HOUR FROM l.hora_evento)::int AS label,
                   COUNT(*) AS value {FROM_L} WHERE {W}
            AND l.hora_evento IS NOT NULL GROUP BY 1 ORDER BY 1""")

    # ------------------------------------------------- población / protección
    add(_esp("impacto_poblacion_total", "Impacto de población registrado",
             "personas", "donut", grupo="poblacion", fuente="sec:edan_localidades_impacto_poblacion",
             col_label="concepto", eje_y="Personas"),
        f"""SELECT COALESCE(SUM(ip.fallecidos), 0) AS fallecidos,
                   COALESCE(SUM(ip.heridos), 0) AS heridos,
                   COALESCE(SUM(ip.desaparecidos), 0) AS desaparecidos
            FROM edan.edan_localidades_impacto_poblacion ip
            JOIN edan.edan_localidades l ON l.id_edan_localidad = ip.id_edan_localidad
            WHERE {W}""",
        tupla=[("fallecidos", "Fallecidos", "#7F1D1D"),
               ("heridos", "Heridos", "#D55E00"),
               ("desaparecidos", "Desaparecidos", "#E69F00")])

    add(_esp("impacto_por_grupo_etario", "Impacto por grupo etario", "personas",
             "barras_apiladas", grupo="poblacion", fuente="sec:edan_localidades_impacto_poblacion",
             orden="sql", eje_x="Grupo etario",
             metricas=[("fallecidos", "Fallecidos", "#7F1D1D"),
                       ("heridos", "Heridos", "#D55E00"),
                       ("desaparecidos", "Desaparecidos", "#E69F00")],
             extra=[("grupo_etario", "Grupo etario")]),
        f"""SELECT COALESCE(ge.nombre, 'Sin grupo') AS label,
                   COALESCE(SUM(ip.fallecidos), 0) AS fallecidos,
                   COALESCE(SUM(ip.heridos), 0) AS heridos,
                   COALESCE(SUM(ip.desaparecidos), 0) AS desaparecidos,
                   ge.nombre AS grupo_etario
            FROM edan.edan_localidades_impacto_poblacion ip
            JOIN edan.edan_localidades l ON l.id_edan_localidad = ip.id_edan_localidad
            LEFT JOIN edan.grupo_etario ge ON ge.id_grupo_etario = ip.id_grupo_etario
            WHERE {W} GROUP BY ge.id_grupo_etario, ge.nombre, ge.orden
            ORDER BY ge.orden NULLS LAST""")

    add(_esp("proteccion_por_grupo_vulnerable",
             "Protección por grupo vulnerable (mujeres/hombres)", "personas",
             "barras_apiladas", grupo="poblacion",
             fuente="sec:edan_localidades_proteccion", orden="sql", eje_x="Grupo",
             metricas=[("mujeres", "Mujeres", "#CC79A7"),
                       ("hombres", "Hombres", "#0072B2")],
             extra=[("grupo_vulnerable", "Grupo vulnerable")]),
        f"""SELECT COALESCE(gv.nombre, 'Sin grupo') AS label,
                   COALESCE(SUM(pp.mujeres), 0) AS mujeres,
                   COALESCE(SUM(pp.hombres), 0) AS hombres,
                   gv.nombre AS grupo_vulnerable
            FROM edan.edan_localidades_proteccion pp
            JOIN edan.edan_localidades l ON l.id_edan_localidad = pp.id_edan_localidad
            LEFT JOIN edan.grupo_vulnerable gv
                   ON gv.id_grupo_vulnerable = pp.id_grupo_vulnerable_catalogo
            WHERE {W} GROUP BY gv.id_grupo_vulnerable, gv.nombre, gv.orden
            ORDER BY gv.orden NULLS LAST""")

    add(_esp("apoyo_psicologico", "Apoyo psicológico (localidades)", "formularios",
             "torta", grupo="poblacion", fuente="sec:edan_localidades_proteccion",
             col_label="concepto", eje_y="Registros"),
        f"""SELECT COUNT(*) FILTER (WHERE pp.apoyo_psicologico) AS con,
                   COUNT(*) FILTER (WHERE NOT pp.apoyo_psicologico) AS sin
            FROM edan.edan_localidades_proteccion pp
            JOIN edan.edan_localidades l ON l.id_edan_localidad = pp.id_edan_localidad
            WHERE {W}""",
        tupla=[("con", "Con apoyo", "#10B981"), ("sin", "Sin apoyo", "#EF4444")])

    add(_esp("reposicion_documentos", "Reposición de documentos", "formularios",
             "torta", grupo="poblacion", fuente="sec:edan_localidades_proteccion",
             col_label="concepto", eje_y="Registros"),
        f"""SELECT COUNT(*) FILTER (WHERE pp.reposicion_documentos) AS con,
                   COUNT(*) FILTER (WHERE NOT pp.reposicion_documentos) AS sin
            FROM edan.edan_localidades_proteccion pp
            JOIN edan.edan_localidades l ON l.id_edan_localidad = pp.id_edan_localidad
            WHERE {W}""",
        tupla=[("con", "Con reposición", "#10B981"),
               ("sin", "Sin reposición", "#EF4444")])

    add(_esp("top_localidades_poblacion", "Localidades con más población afectada",
             "personas", "barras", grupo="poblacion", geo="localidad",
             fuente="localidad", orden="sql", extra=[("municipio", "Municipio")]),
        f"""SELECT l.localidad AS label,
                   COALESCE(l.total_poblacion_afectada, 0) AS value,
                   COALESCE(m.nombre, '') AS municipio
            {FROM_L} WHERE {W} AND l.total_poblacion_afectada > 0
            ORDER BY value DESC LIMIT {top}""")

    add(_esp("top_localidades_familias", "Localidades con más familias afectadas",
             "familias", "barras", grupo="poblacion", geo="localidad",
             fuente="localidad", orden="sql", extra=[("municipio", "Municipio")]),
        f"""SELECT l.localidad AS label,
                   COALESCE(l.total_familias_afectadas, 0) AS value,
                   COALESCE(m.nombre, '') AS municipio
            {FROM_L} WHERE {W} AND l.total_familias_afectadas > 0
            ORDER BY value DESC LIMIT {top}""")

    # ---------------------------------------------------------------- vivienda
    add(_esp("vivienda_danos", "Daños de vivienda (parcial/total)", "viviendas",
             "donut", grupo="vivienda", fuente="sec:edan_localidades_danos_vivienda",
             col_label="concepto", eje_y="Viviendas"),
        f"""SELECT COALESCE(SUM(v.dano_parcial), 0) AS parcial,
                   COALESCE(SUM(v.dano_total), 0) AS total
            FROM edan.edan_localidades_danos_vivienda v
            JOIN edan.edan_localidades l ON l.id_edan_localidad = v.id_edan_localidad
            WHERE {W}""",
        tupla=[("parcial", "Daño parcial", "#E69F00"),
               ("total", "Daño total", "#D55E00")])

    add(_esp("vivienda_por_municipio", "Viviendas dañadas por municipio",
             "viviendas", "barras_apiladas", grupo="vivienda", geo="municipio",
             fuente="sec:edan_localidades_danos_vivienda", orden="sql",
             metricas=[("parcial", "Daño parcial", "#E69F00"),
                       ("total", "Daño total", "#D55E00")]),
        f"""SELECT COALESCE(m.nombre, 'Sin municipio') AS label,
                   COALESCE(SUM(v.dano_parcial), 0) AS parcial,
                   COALESCE(SUM(v.dano_total), 0) AS total
            FROM edan.edan_localidades_danos_vivienda v
            JOIN edan.edan_localidades l ON l.id_edan_localidad = v.id_edan_localidad
            LEFT JOIN shared.municipio m ON m.id = l.id_municipio
            WHERE {W} GROUP BY m.id, m.nombre
            ORDER BY COALESCE(SUM(v.dano_parcial), 0) + COALESCE(SUM(v.dano_total), 0) DESC
            LIMIT {top}""")

    add(_esp("viviendas_por_tipo", "Viviendas registradas por tipo de daño",
             "viviendas", "torta", grupo="vivienda", fuente="vivienda"),
        f"""SELECT v.tipo_dano AS label, COUNT(*) AS value
            FROM edan.edan_localidades_viviendas v
            JOIN edan.edan_localidades_danos_vivienda dv
                 ON dv.id_dano_vivienda = v.id_dano_vivienda
            JOIN edan.edan_localidades l ON l.id_edan_localidad = dv.id_edan_localidad
            WHERE {W} GROUP BY v.tipo_dano ORDER BY value DESC""")

    add(_esp("viviendas_con_coordenadas", "Viviendas con/sin coordenadas",
             "viviendas", "donut", grupo="vivienda", fuente="vivienda",
             col_label="concepto", eje_y="Viviendas"),
        f"""SELECT COUNT(*) FILTER (WHERE v.coordenada_lat IS NOT NULL
                                        AND v.coordenada_lon IS NOT NULL) AS con,
                   COUNT(*) FILTER (WHERE v.coordenada_lat IS NULL
                                     OR v.coordenada_lon IS NULL) AS sin
            FROM edan.edan_localidades_viviendas v
            JOIN edan.edan_localidades_danos_vivienda dv
                 ON dv.id_dano_vivienda = v.id_dano_vivienda
            JOIN edan.edan_localidades l ON l.id_edan_localidad = dv.id_edan_localidad
            WHERE {W}""",
        tupla=[("con", "Con coordenadas", "#10B981"),
               ("sin", "Sin coordenadas", "#EF4444")])

    add(_esp("top_localidades_viviendas", "Localidades con más viviendas dañadas",
             "viviendas", "barras", grupo="vivienda", geo="localidad",
             fuente="vivienda", orden="sql", extra=[("municipio", "Municipio")]),
        f"""SELECT l.localidad AS label, COUNT(*) AS value,
                   COALESCE(m.nombre, '') AS municipio
            FROM edan.edan_localidades_viviendas v
            JOIN edan.edan_localidades_danos_vivienda dv
                 ON dv.id_dano_vivienda = v.id_dano_vivienda
            JOIN edan.edan_localidades l ON l.id_edan_localidad = dv.id_edan_localidad
            LEFT JOIN shared.municipio m ON m.id = l.id_municipio
            WHERE {W} GROUP BY l.id_edan_localidad, l.localidad, m.nombre
            ORDER BY value DESC LIMIT {top}""")

    # -------------------------------------------- vías / infra / servicios
    add(_esp("danos_viales_km", "Kilómetros de daño vial por municipio",
             "kilómetros", "barras", grupo="servicios", geo="municipio",
             fuente="sec:edan_localidades_danos_viales", orden="sql"),
        f"""SELECT COALESCE(m.nombre, 'Sin municipio') AS label,
                   COALESCE(SUM(v.km_danio), 0) AS value
            FROM edan.edan_localidades_danos_viales v
            JOIN edan.edan_localidades l ON l.id_edan_localidad = v.id_edan_localidad
            LEFT JOIN shared.municipio m ON m.id = l.id_municipio
            WHERE {W} GROUP BY m.id, m.nombre ORDER BY value DESC LIMIT {top}""")

    add(_esp("danos_viales_estado", "Tramos viales por tipo de daño", "tramos",
             "donut", grupo="servicios", fuente="sec:edan_localidades_danos_viales",
             col_label="concepto", eje_y="Tramos"),
        f"""SELECT COUNT(*) FILTER (WHERE v.dano_parcial) AS parcial,
                   COUNT(*) FILTER (WHERE v.dano_total) AS total,
                   COUNT(*) FILTER (WHERE NOT v.dano_parcial AND NOT v.dano_total) AS sin
            FROM edan.edan_localidades_danos_viales v
            JOIN edan.edan_localidades l ON l.id_edan_localidad = v.id_edan_localidad
            WHERE {W}""",
        tupla=[("parcial", "Daño parcial", "#E69F00"),
               ("total", "Daño total", "#D55E00"),
               ("sin", "Sin daño", "#10B981")])

    add(_esp("infra_publica_por_tipo", "Infraestructura pública por tipo",
             "registros", "barras_apiladas", grupo="servicios",
             fuente="sec:edan_localidades_danos_infra_publica", orden="sql",
             metricas=[("parcial", "Daño parcial", "#E69F00"),
                       ("total", "Daño total", "#D55E00")]),
        f"""SELECT COALESCE(v.tipo_estructura, 'Sin tipo') AS label,
                   COUNT(*) FILTER (WHERE v.dano_parcial) AS parcial,
                   COUNT(*) FILTER (WHERE v.dano_total) AS total
            FROM edan.edan_localidades_danos_infra_publica v
            JOIN edan.edan_localidades l ON l.id_edan_localidad = v.id_edan_localidad
            WHERE {W} GROUP BY v.tipo_estructura
            ORDER BY (COUNT(*) FILTER (WHERE v.dano_parcial)
                    + COUNT(*) FILTER (WHERE v.dano_total)) DESC LIMIT {top}""")

    add(_esp("servicios_basicos", "Servicios básicos dañados por tipo",
             "registros", "barras_apiladas", grupo="servicios",
             fuente="sec:edan_localidades_servicios_basicos", orden="sql",
             metricas=[("parcial", "Daño parcial", "#E69F00"),
                       ("total", "Daño total", "#D55E00")]),
        f"""SELECT COALESCE(v.tipo, 'Sin tipo') AS label,
                   COUNT(*) FILTER (WHERE v.dano_parcial) AS parcial,
                   COUNT(*) FILTER (WHERE v.dano_total) AS total
            FROM edan.edan_localidades_servicios_basicos v
            JOIN edan.edan_localidades l ON l.id_edan_localidad = v.id_edan_localidad
            WHERE {W} GROUP BY v.tipo
            ORDER BY (COUNT(*) FILTER (WHERE v.dano_parcial)
                   + COUNT(*) FILTER (WHERE v.dano_total)) DESC, label""")

    add(_esp("infra_productiva_por_tipo", "Infraestructura productiva dañada",
             "registros", "barras_apiladas", grupo="agropecuario",
             fuente="sec:edan_localidades_infra_productiva", orden="sql",
             metricas=[("parcial", "Daño parcial", "#E69F00"),
                       ("total", "Daño total", "#D55E00")]),
        f"""SELECT COALESCE(v.tipo, 'Sin tipo') AS label,
                   COALESCE(SUM(v.dano_parcial), 0) AS parcial,
                   COALESCE(SUM(v.dano_total), 0) AS total
            FROM edan.edan_localidades_infra_productiva v
            JOIN edan.edan_localidades l ON l.id_edan_localidad = v.id_edan_localidad
            WHERE {W} GROUP BY v.tipo
            ORDER BY COALESCE(SUM(v.dano_parcial), 0)
                   + COALESCE(SUM(v.dano_total), 0) DESC, label""")

    # ------------------------------------------------------------- educación
    add(_esp("unidades_educativas_dano", "Unidades educativas por daño",
             "establecimientos", "donut", grupo="educacion",
             fuente="sec:edan_localidades_unidades_educativas",
             col_label="concepto", eje_y="Unidades"),
        f"""SELECT COUNT(*) FILTER (WHERE v.dano_parcial) AS parcial,
                   COUNT(*) FILTER (WHERE v.dano_total) AS total,
                   COUNT(*) FILTER (WHERE NOT v.dano_parcial AND NOT v.dano_total) AS sin
            FROM edan.edan_localidades_unidades_educativas v
            JOIN edan.edan_localidades l ON l.id_edan_localidad = v.id_edan_localidad
            WHERE {W}""",
        tupla=[("parcial", "Daño parcial", "#E69F00"),
               ("total", "Daño total", "#D55E00"),
               ("sin", "Sin daño", "#10B981")])

    add(_esp("unidades_educativas_personas", "Personas en unidades educativas",
             "personas", "donut", grupo="educacion",
             fuente="sec:edan_localidades_unidades_educativas",
             col_label="concepto", eje_y="Personas"),
        f"""SELECT COALESCE(SUM(v.estudiantes), 0) AS estudiantes,
                   COALESCE(SUM(v.profesores), 0) AS profesores,
                   COALESCE(SUM(v.administrativos), 0) AS administrativos
            FROM edan.edan_localidades_unidades_educativas v
            JOIN edan.edan_localidades l ON l.id_edan_localidad = v.id_edan_localidad
            WHERE {W}""",
        tupla=[("estudiantes", "Estudiantes", "#0072B2"),
               ("profesores", "Docentes", "#E69F00"),
               ("administrativos", "Administrativos", "#CC79A7")])

    add(_esp("unidades_educativas_impacto", "Impacto en unidades educativas",
             "establecimientos", "barras", grupo="educacion",
             fuente="sec:edan_localidades_unidades_educativas", orden="sql"),
        f"""SELECT COUNT(*) FILTER (WHERE v.suspension_clases) AS suspension,
                   COUNT(*) FILTER (WHERE v.perdida_material) AS perdida,
                   COUNT(*) FILTER (WHERE v.funciona_albergue) AS albergue
            FROM edan.edan_localidades_unidades_educativas v
            JOIN edan.edan_localidades l ON l.id_edan_localidad = v.id_edan_localidad
            WHERE {W}""",
        tupla=[("suspension", "Suspensión de clases", "#D55E00"),
               ("perdida", "Pérdida de material", "#E69F00"),
               ("albergue", "Funciona como albergue", "#56B4E9")])

    # ------------------------------------------------------------------ salud
    add(_esp("salud_por_nivel", "Establecimientos de salud por nivel",
             "establecimientos", "barras_apiladas", grupo="salud",
             fuente="sec:edan_localidades_salud_establecimientos", orden="sql",
             metricas=[("parcial", "Daño parcial", "#E69F00"),
                       ("total", "Daño total", "#D55E00")]),
        f"""SELECT COALESCE(v.nivel_atencion, 'Sin nivel') AS label,
                   COUNT(*) FILTER (WHERE v.dano_parcial) AS parcial,
                   COUNT(*) FILTER (WHERE v.dano_total) AS total
            FROM edan.edan_localidades_salud_establecimientos v
            JOIN edan.edan_localidades l ON l.id_edan_localidad = v.id_edan_localidad
            WHERE {W} GROUP BY v.nivel_atencion
            ORDER BY (COUNT(*) FILTER (WHERE v.dano_parcial)
                   + COUNT(*) FILTER (WHERE v.dano_total)) DESC, label""")

    add(_esp("salud_personal_afectado", "Personal de salud afectado", "personas",
             "donut", grupo="salud",
             fuente="sec:edan_localidades_salud_establecimientos",
             col_label="concepto", eje_y="Personas"),
        f"""SELECT COALESCE(SUM(v.medicos_afectados), 0) AS medicos,
                   COALESCE(SUM(v.enfermeras_afectadas), 0) AS enfermeras,
                   COALESCE(SUM(v.otros_afectados), 0) AS otros
            FROM edan.edan_localidades_salud_establecimientos v
            JOIN edan.edan_localidades l ON l.id_edan_localidad = v.id_edan_localidad
            WHERE {W}""",
        tupla=[("medicos", "Médicos", "#0072B2"),
               ("enfermeras", "Enfermeras", "#009E73"),
               ("otros", "Otros", "#999999")])

    add(_esp("salud_necesidades", "Necesidades de salud atendidas", "personas",
             "indicador", grupo="salud",
             fuente="sec:edan_localidades_salud_necesidades",
             col_label="concepto", eje_y="Personas",
             tipos=TIPOS_SEMFORO + ["barras", "linea"]),
        f"""SELECT COALESCE(SUM(v.numero_personas), 0) AS personas,
                   COUNT(*) AS registros
            FROM edan.edan_localidades_salud_necesidades v
            JOIN edan.edan_localidades l ON l.id_edan_localidad = v.id_edan_localidad
            WHERE {W}""",
        tupla=[("personas", "Personas con necesidades de salud", "#0072B2"),
               ("registros", "Localidades registradas", "#56B4E9")])

    # ------------------------------------------------------------- agropecuario
    add(_esp("agricultura_totales", "Hectáreas de agricultura afectadas",
             "hectáreas", "donut", grupo="agropecuario",
             fuente="sec:edan_localidades_danos_agricultura",
             col_label="concepto", eje_y="Hectáreas"),
        f"""SELECT COALESCE(SUM(a.hectareas_afectadas), 0) AS afectadas,
                   COALESCE(SUM(a.hectareas_perdidas), 0) AS perdidas
            FROM edan.edan_localidades_danos_agricultura a
            JOIN edan.edan_localidades l ON l.id_edan_localidad = a.id_edan_localidad
            WHERE {W}""",
        tupla=[("afectadas", "Hectáreas afectadas", "#E69F00"),
               ("perdidas", "Hectáreas perdidas", "#D55E00")])

    add(_esp("agricultura_por_cultivo", "Hectáneas afectadas por cultivo",
             "hectáreas", "barras", grupo="agropecuario",
             fuente="sec:edan_localidades_danos_agricultura"),
        f"""SELECT COALESCE(c.nombre, a.tipo_cultivo, 'Sin cultivo') AS label,
                   COALESCE(SUM(a.hectareas_afectadas), 0) AS value
            FROM edan.edan_localidades_danos_agricultura a
            JOIN edan.edan_localidades l ON l.id_edan_localidad = a.id_edan_localidad
            LEFT JOIN shared.cultivo c ON c.id = a.id_cultivo
            WHERE {W} GROUP BY c.id, c.nombre, a.tipo_cultivo
            ORDER BY value DESC, label LIMIT {top}""")

    add(_esp("agricultura_por_grupo", "Hectáneas afectadas por grupo de cultivo",
             "hectáreas", "torta", grupo="agropecuario",
             fuente="sec:edan_localidades_danos_agricultura"),
        f"""SELECT COALESCE(c.grupo, 'Sin grupo') AS label,
                   COALESCE(SUM(a.hectareas_afectadas), 0) AS value
            FROM edan.edan_localidades_danos_agricultura a
            JOIN edan.edan_localidades l ON l.id_edan_localidad = a.id_edan_localidad
            LEFT JOIN shared.cultivo c ON c.id = a.id_cultivo
            WHERE {W} GROUP BY c.grupo ORDER BY value DESC, label""")

    add(_esp("pecuario_totales", "Animales pecuarios afectados", "animales",
             "donut", grupo="agropecuario",
             fuente="sec:edan_localidades_danos_pecuario",
             col_label="concepto", eje_y="Animales"),
        f"""SELECT COALESCE(SUM(d.animales_afectados), 0) AS afectados,
                   COALESCE(SUM(d.animales_muertos), 0) AS muertos
            FROM edan.edan_localidades_danos_pecuario d
            JOIN edan.edan_localidades l ON l.id_edan_localidad = d.id_edan_localidad
            WHERE {W}""",
        tupla=[("afectados", "Animales afectados", "#E69F00"),
               ("muertos", "Animales muertos", "#7F1D1D")])

    add(_esp("pecuario_por_especie", "Animales afectados por especie",
             "animales", "barras", grupo="agropecuario",
             fuente="sec:edan_localidades_danos_pecuario"),
        f"""SELECT COALESCE(p.nombre, d.especie, 'Sin especie') AS label,
                   COALESCE(SUM(d.animales_afectados), 0) AS value
            FROM edan.edan_localidades_danos_pecuario d
            JOIN edan.edan_localidades l ON l.id_edan_localidad = d.id_edan_localidad
            LEFT JOIN shared.pecuario p ON p.id = d.id_especie
            WHERE {W} GROUP BY p.id, p.nombre, d.especie
            ORDER BY value DESC, label LIMIT {top}""")

    add(_esp("pecuario_por_grupo", "Animales afectados por grupo", "animales",
             "torta", grupo="agropecuario",
             fuente="sec:edan_localidades_danos_pecuario"),
        f"""SELECT COALESCE(p.grupo, 'Sin grupo') AS label,
                   COALESCE(SUM(d.animales_afectados), 0) AS value
            FROM edan.edan_localidades_danos_pecuario d
            JOIN edan.edan_localidades l ON l.id_edan_localidad = d.id_edan_localidad
            LEFT JOIN shared.pecuario p ON p.id = d.id_especie
            WHERE {W} GROUP BY p.grupo ORDER BY value DESC, label""")

    # -------------------------------------------- primera respuesta / humanitarias
    add(_esp("primera_respuesta", "Primera respuesta activada", "localidades",
             "barras", grupo="secciones", fuente="sec:edan_localidades_primera_respuesta",
             orden="sql"),
        f"""SELECT COUNT(*) FILTER (WHERE v.busqueda) AS busqueda,
                   COUNT(*) FILTER (WHERE v.salvamento) AS salvamento,
                   COUNT(*) FILTER (WHERE v.evacuacion) AS evacuacion
            FROM edan.edan_localidades_primera_respuesta v
            JOIN edan.edan_localidades l ON l.id_edan_localidad = v.id_edan_localidad
            WHERE {W}""",
        tupla=[("busqueda", "Búsqueda", "#0072B2"),
               ("salvamento", "Salvamento", "#009E73"),
               ("evacuacion", "Evacuación", "#D55E00")])

    add(_esp("necesidades_humanitarias", "Necesidades humanitarias cubiertas",
             "localidades", "barras_horizontales", grupo="secciones",
             fuente="sec:edan_localidades_necesidades_humanitarias", orden="sql"),
        f"""SELECT {", ".join(f"COUNT(*) FILTER (WHERE v.{c}) AS {c}"
                              for c in ("alimentos", "refugio_vivienda", "ropa_cama",
                                        "articulos_higiene", "articulos_cocina",
                                        "prendas_vestir", "herramientas",
                                        "almacenamiento_agua", "banos"))}
            FROM edan.edan_localidades_necesidades_humanitarias v
            JOIN edan.edan_localidades l ON l.id_edan_localidad = v.id_edan_localidad
            WHERE {W}""",
        tupla=[("alimentos", "Alimentos", COLORES_HUMANITARIAS["Alimentos"]),
               ("refugio_vivienda", "Refugio / vivienda",
                COLORES_HUMANITARIAS["Refugio / vivienda"]),
               ("ropa_cama", "Ropa y cama", COLORES_HUMANITARIAS["Ropa y cama"]),
               ("articulos_higiene", "Artículos de higiene",
                COLORES_HUMANITARIAS["Artículos de higiene"]),
               ("articulos_cocina", "Artículos de cocina",
                COLORES_HUMANITARIAS["Artículos de cocina"]),
               ("prendas_vestir", "Prendas de vestir",
                COLORES_HUMANITARIAS["Prendas de vestir"]),
               ("herramientas", "Herramientas", COLORES_HUMANITARIAS["Herramientas"]),
               ("almacenamiento_agua", "Almacenamiento de agua",
                COLORES_HUMANITARIAS["Almacenamiento de agua"]),
               ("banos", "Baños", COLORES_HUMANITARIAS["Baños"])])

    # --------------------------------------------------------------- fotografías
    add(_esp("fotos_por_municipio", "Fotografías por municipio", "fotos",
             "barras", grupo="fotos", geo="municipio", fuente="fotografia"),
        f"""SELECT COALESCE(m.nombre, 'Sin municipio') AS label, COUNT(*) AS value
            FROM edan.fotografias f
            JOIN edan.edan_localidades l ON l.id_edan_localidad = f.id_edan_localidad
            LEFT JOIN shared.municipio m ON m.id = l.id_municipio
            WHERE {W} AND f.borrado_logico = FALSE
            GROUP BY m.id, m.nombre ORDER BY value DESC, label LIMIT {top}""")

    add(_esp("fotos_por_tipo_entidad", "Fotografías por tipo de sección",
             "fotos", "barras_horizontales", grupo="fotos", fuente="fotografia"),
        f"""SELECT f.tipo_entidad AS label, COUNT(*) AS value
            FROM edan.fotografias f
            JOIN edan.edan_localidades l ON l.id_edan_localidad = f.id_edan_localidad
            WHERE {W} AND f.borrado_logico = FALSE
            GROUP BY f.tipo_entidad ORDER BY value DESC, label LIMIT {top}""")

    add(_esp("serie_fotos", "Fotografías subidas en el tiempo", "fotos", "linea",
             grupo="fotos", serie="periodo", campo_fecha="modificacion",
             fuente="fotografia", tipos=TIPOS_SERIE),
        f"""SELECT date_trunc('{dt}', f.fecha_creacion) AS periodo, COUNT(*) AS valor
            FROM edan.fotografias f
            JOIN edan.edan_localidades l ON l.id_edan_localidad = f.id_edan_localidad
            WHERE {W} AND f.borrado_logico = FALSE
            GROUP BY 1 ORDER BY 1""")

    add(_esp("fotos_cobertura", "Localidades con/sin fotografía", "formularios",
             "donut", grupo="fotos", fuente="localidad", col_label="concepto",
             eje_y="Formularios"),
        f"""SELECT COUNT(*) FILTER (WHERE EXISTS (
                     SELECT 1 FROM edan.fotografias fo
                     WHERE fo.id_edan_localidad = l.id_edan_localidad
                       AND fo.borrado_logico = FALSE)) AS con,
                   COUNT(*) FILTER (WHERE NOT EXISTS (
                     SELECT 1 FROM edan.fotografias fo
                     WHERE fo.id_edan_localidad = l.id_edan_localidad
                       AND fo.borrado_logico = FALSE)) AS sin
            {FROM_L} WHERE {W}""",
        tupla=[("con", "Con fotografía", "#10B981"),
               ("sin", "Sin fotografía", "#EF4444")])

    # ------------------------------------------------- usuarios / importaciones
    add(_esp("formularios_por_usuario", "Formularios por usuario capturista",
             "formularios", "barras", grupo="usuarios", fuente="localidad"),
        f"""SELECT COALESCE(u.nombre, u.usuario, 'Sin usuario') AS label,
                   COUNT(*) AS value {FROM_L} WHERE {W}
            GROUP BY u.id_usuario, u.nombre, u.usuario
            ORDER BY value DESC, label LIMIT {top}""")

    add(_esp("formularios_por_importacion", "Formularios por archivo importado",
             "formularios", "barras", grupo="usuarios", fuente="localidad"),
        f"""SELECT COALESCE(il.nombre_archivo, 'Sin importación') AS label,
                   COUNT(*) AS value
            FROM edan.edan_localidades l
            LEFT JOIN edan.edan_importacion_log il ON il.id_importacion = l.id_importacion
            WHERE {W} GROUP BY il.id_importacion, il.nombre_archivo
            ORDER BY value DESC, label LIMIT {top}""")

    return {**_pie(f, opts, opts.get("nivel")), "unidad": "formularios",
            "total_graficas": len(g), "graficas": g}


def graficas_edan(db: Session, f: dict, opts: dict | None = None) -> dict:
    """Catálogo de gráficas de EDAN padre (cabecera) + las gráficas de sus
    localidades restringidas por los MISMOS filtros (incluye aprobaciones e
    importaciones). Todo obedece todos los filtros y cada gráfica trae `tabla`.
    """
    opts = opts or {}
    _validar_geo(db, f)
    w, p = _e_where(f, "e")
    wl, pl = _where_l_con_edan(f)
    acc: list[dict] = []
    _, add = _colector(db, w, p, opts, f, acc)
    _, add_l = _colector(db, wl, pl, opts, f, acc)
    g = acc
    top = int(opts.get("top") or 15)
    gran = opts.get("granularidad") or "mes"
    dt = GRANULARES[gran] if gran in GRANULARES else "month"
    FROM_E = f"FROM edan.edan e {_EJ}"
    FROM_L = f"FROM edan.edan_localidades l {_LJ}"
    estados = _rows(db, "SELECT id_estado AS id, nombre, orden "
                        "FROM edan.estado_edan ORDER BY orden", {})
    col_estado = {e["nombre"]: COLORES_ESTADO_EDAN.get(e["nombre"], "#94A3B8")
                  for e in estados}
    COLOR_APROB = {"aprobado": "#10B981", "pendiente": "#F59E00",
                   "observado": "#EF4444", "espera_correccion": "#8B5CF6"}
    COLOR_NIVEL = {"ugr": "#0072B2", "alcalde": "#E69F00",
                   "dgr": "#009E73", "videcid": "#CC79A7"}

    # ---------------------------------------------------------------- estados
    add(_esp("estado_edan", "EDAN por estado", "edan", "donut", grupo="estados",
             color_map=col_estado, orden="sql", fuente="edan",
             orden_labels=[e["nombre"] for e in estados]),
        f"""SELECT COALESCE(es.nombre, 'Sin estado') AS label, COUNT(*) AS value
            {FROM_E} WHERE {W} GROUP BY es.id_estado, es.nombre, es.orden
            ORDER BY es.orden NULLS LAST""")

    add(_esp("poblacion_por_estado", "Población afectada por estado", "personas",
             "barras_apiladas", grupo="estados", fuente="edan",
             color_map=col_estado, orden="sql",
             orden_labels=[e["nombre"] for e in estados]),
        f"""SELECT COALESCE(es.nombre, 'Sin estado') AS label,
                   COALESCE(SUM(e.total_poblacion_afectada), 0) AS value
            {FROM_E} WHERE {W} GROUP BY es.id_estado, es.nombre, es.orden
            ORDER BY es.orden NULLS LAST""")

    for clave, geo, nodo in (("departamento", "departamento", "d.nombre"),
                             ("municipio", "municipio", "m.nombre")):
        add(_esp(f"estado_por_{clave}", f"Estados por {clave}", "edan",
                 "barras_apiladas", grupo="estados", geo=geo, orden="sql"),
            f"""SELECT COALESCE({nodo}, 'Sin {clave}') AS label, COUNT(*) AS total,
                       {", ".join(f"COUNT(*) FILTER (WHERE e.id_estado = {e['id']}) AS s{e['id']}" for e in estados)}
                {FROM_E} WHERE {W} GROUP BY 1
                ORDER BY COUNT(*) DESC LIMIT {top}""",
            metricas=[(f"s{e['id']}", e["nombre"], col_estado[e["nombre"]])
                      for e in estados])

    # ---------------------------------------------------------------- eventos
    add(_esp("tipo_evento_edan", "EDAN por tipo de evento", "edan", "barras",
             grupo="eventos", fuente="edan"),
        f"""SELECT COALESCE(te.nombre, 'Sin tipo de evento') AS label,
                   COUNT(*) AS value {FROM_E} WHERE {W}
            GROUP BY te.id_tipo_evento, te.nombre ORDER BY value DESC, label
            LIMIT {top}""")

    add(_esp("grupo_evento_edan", "EDAN por grupo de evento", "edan", "torta",
             grupo="eventos", color_map=COLORES_EVENTO_GRUPO, orden="sql",
             fuente="edan"),
        f"""SELECT COALESCE(te.grupo, 'Sin grupo') AS label, COUNT(*) AS value
            {FROM_E} WHERE {W} GROUP BY te.grupo ORDER BY value DESC, label""")

    add(_esp("categoria_evento_edan", "EDAN por categoría de evento", "edan",
             "barras_horizontales", grupo="eventos", fuente="edan"),
        f"""SELECT COALESCE(te.categoria, 'Sin categoría') AS label,
                   COUNT(*) AS value {FROM_E} WHERE {W}
            GROUP BY te.categoria ORDER BY value DESC, label LIMIT {top}""")

    tipos_ev = _rows(db, f"""
        SELECT te.id_tipo_evento AS id, te.nombre FROM edan.edan e
        LEFT JOIN edan.tipo_evento te ON te.id_tipo_evento = e.id_tipo_evento
        WHERE {W} AND te.id_tipo_evento IS NOT NULL
        GROUP BY te.id_tipo_evento, te.nombre ORDER BY te.nombre""".replace("{w}", w), p)
    if tipos_ev:
        add(_esp("tipo_evento_por_departamento_edan",
                 "Tipos de evento por departamento", "edan", "barras_apiladas",
                 grupo="eventos", geo="departamento", orden="sql",
                 metricas=[(f"t{t['id']}", t["nombre"],
                            COLORES_PALETA[i % len(COLORES_PALETA)])
                           for i, t in enumerate(tipos_ev)]),
            f"""SELECT COALESCE(d.nombre, 'Sin departamento') AS label,
                       {", ".join(f"COUNT(*) FILTER (WHERE e.id_tipo_evento = {t['id']}) AS t{t['id']}" for t in tipos_ev)}
                FROM edan.edan e
                LEFT JOIN shared.departamento d ON d.id = e.id_departamento
                WHERE {W} GROUP BY d.id, d.nombre ORDER BY COUNT(*) DESC
                LIMIT {top}""")

        add(_esp("estado_por_tipo_evento", "Estados por tipo de evento", "edan",
                 "barras_apiladas", grupo="estados", orden="sql",
                 metricas=[(f"s{e['id']}", e["nombre"], col_estado[e["nombre"]])
                           for e in estados]),
            f"""SELECT COALESCE(te.nombre, 'Sin tipo de evento') AS label,
                       COUNT(*) AS total,
                       {", ".join(f"COUNT(*) FILTER (WHERE e.id_estado = {e['id']}) AS s{e['id']}" for e in estados)}
                FROM edan.edan e
                LEFT JOIN edan.tipo_evento te ON te.id_tipo_evento = e.id_tipo_evento
                WHERE {W} GROUP BY te.id_tipo_evento, te.nombre
                ORDER BY COUNT(*) DESC LIMIT {top}""")

    # --------------------------------------------------------------- geografía
    add(_esp("edan_por_departamento", "EDAN por departamento", "edan", "barras",
             grupo="geografia", geo="departamento", fuente="edan"),
        f"""SELECT COALESCE(d.nombre, 'Sin departamento') AS label, COUNT(*) AS value
            {FROM_E} WHERE {W} GROUP BY d.id, d.nombre ORDER BY value DESC, label""")

    add(_esp("edan_por_provincia", "EDAN por provincia", "edan", "barras",
             grupo="geografia", geo="provincia", fuente="edan"),
        f"""SELECT COALESCE(pr.nombre, 'Sin provincia') AS label, COUNT(*) AS value
            {FROM_E} WHERE {W} GROUP BY pr.id, pr.nombre ORDER BY value DESC, label""")

    add(_esp("edan_por_municipio", "EDAN por municipio", "edan", "barras",
             grupo="geografia", geo="municipio", fuente="edan"),
        f"""SELECT COALESCE(m.nombre, 'Sin municipio') AS label, COUNT(*) AS value
            {FROM_E} WHERE {W} GROUP BY m.id, m.nombre
            ORDER BY value DESC, label LIMIT {top}""")

    for campo, titulo, geo, col, nodo in (
            ("poblacion_afectada", "Población afectada por ", "departamento",
             "e.total_poblacion_afectada", "d.nombre"),
            ("poblacion_afectada_municipio", "Población afectada por municipio",
             "municipio", "e.total_poblacion_afectada", "m.nombre"),
            ("familias_afectadas", "Familias afectadas por municipio", "municipio",
             "e.total_familias_afectadas", "m.nombre"),
            ("familias_damnificadas", "Familias damnificadas por municipio",
             "municipio", "e.total_familias_damnificadas", "m.nombre")):
        add(_esp(f"edan_{campo}", titulo + (geo if titulo.endswith("por ") else ""),
                 "personas", "barras", grupo="geografia", geo=geo, fuente="edan"),
            f"""SELECT COALESCE({nodo}, 'Sin {geo}') AS label,
                       COALESCE(SUM({col}), 0) AS value
                {FROM_E} WHERE {W} GROUP BY {nodo}
                ORDER BY value DESC, label LIMIT {top}""")

    add(_esp("top_edan_poblacion", "EDAN con más población afectada", "personas",
             "barras", grupo="geografia", fuente="edan", orden="sql",
             extra=[("municipio", "Municipio")]),
        f"""SELECT COALESCE(e.codigo_edan, e.uuid_edan::text) AS label,
                   COALESCE(e.total_poblacion_afectada, 0) AS value,
                   COALESCE(m.nombre, '') AS municipio
            {FROM_E} WHERE {W} AND COALESCE(e.total_poblacion_afectada, 0) > 0
            ORDER BY value DESC LIMIT {top}""")

    add(_esp("top_edan_localidades", "EDAN con más localidades", "localidades",
             "barras", grupo="geografia", fuente="edan", orden="sql",
             extra=[("municipio", "Municipio")]),
        f"""SELECT COALESCE(e.codigo_edan, e.uuid_edan::text) AS label,
                   (SELECT COUNT(*) FROM edan.edan_localidades ll
                     WHERE ll.id_edan = e.id_edan) AS value,
                   COALESCE(m.nombre, '') AS municipio
            {FROM_E} WHERE {W}
            ORDER BY value DESC, label LIMIT {top}""")

    add(_esp("histograma_localidades_por_edan", "Distribución de EDAN por número "
             "de localidades", "edan", "barras", grupo="geografia", orden="sql",
             orden_labels=["1 localidad", "2-4 localidades", "5-9 localidades",
                           "10 o más localidades"]),
        f"""SELECT CASE
                       WHEN n = 1 THEN '1 localidad'
                       WHEN n <= 4 THEN '2-4 localidades'
                       WHEN n <= 9 THEN '5-9 localidades'
                       ELSE '10 o más localidades' END AS label,
                   COUNT(*) AS value
            FROM edan.edan e
            CROSS JOIN LATERAL (SELECT COUNT(*) AS n FROM edan.edan_localidades ll
                                WHERE ll.id_edan = e.id_edan) c
            WHERE {W} GROUP BY 1 ORDER BY 1""")

    # ----------------------------------------------------------------- tiempo
    for clave, campo, titulo in (
            ("evento", "fecha_evento", "EDAN por fecha de evento"),
            ("llenado", "fecha_llenado", "EDAN por fecha de llenado"),
            ("creacion", "fecha_creacion", "EDAN por fecha de creación"),
            ("modificacion", "fecha_modificacion", "EDAN por última modificación")):
        add(_esp(f"serie_{clave}_edan", titulo, "edan", "linea", grupo="tiempo",
                 serie="periodo", campo_fecha=campo, fuente="edan",
                 tipos=TIPOS_SERIE + ["torta", "donut"],
                 descripcion=f"Granularidad: {gran}"),
            f"""SELECT date_trunc('{dt}', e.{campo}) AS periodo, COUNT(*) AS valor
                {FROM_E} WHERE {W} AND e.{campo} IS NOT NULL
                GROUP BY 1 ORDER BY 1""")

    add(_esp("mes_evento_edan", "EDAN por mes del evento", "edan", "barras",
             grupo="tiempo", fuente="edan", orden="sql", orden_labels=MESES),
        f"""SELECT EXTRACT(MONTH FROM e.fecha_evento)::int AS label,
                   COUNT(*) AS value {FROM_E} WHERE {W}
            AND e.fecha_evento IS NOT NULL GROUP BY 1 ORDER BY 1""")

    add(_esp("mes_llenado_edan", "EDAN por mes de llenado", "edan", "barras",
             grupo="tiempo", fuente="edan", orden="sql", orden_labels=MESES),
        f"""SELECT EXTRACT(MONTH FROM e.fecha_llenado)::int AS label,
                   COUNT(*) AS value {FROM_E} WHERE {W}
            AND e.fecha_llenado IS NOT NULL GROUP BY 1 ORDER BY 1""")

    add(_esp("dia_semana_evento_edan", "EDAN por día de la semana (evento)",
             "edan", "barras", grupo="tiempo", fuente="edan", orden="sql",
             orden_labels=_DIAS_SEMANA),
        f"""SELECT EXTRACT(DOW FROM e.fecha_evento)::int AS label,
                   COUNT(*) AS value {FROM_E} WHERE {W}
            AND e.fecha_evento IS NOT NULL GROUP BY 1 ORDER BY 1""")

    add(_esp("hora_evento_edan", "EDAN por hora del evento", "edan", "barras",
             grupo="tiempo", fuente="edan", orden="sql", orden_labels=list(range(24))),
        f"""SELECT EXTRACT(HOUR FROM e.hora_evento)::int AS label,
                   COUNT(*) AS value {FROM_E} WHERE {W}
            AND e.hora_evento IS NOT NULL GROUP BY 1 ORDER BY 1""")

    # ------------------------------------------------- sincronización / usuarios
    add(_esp("sincronizacion_edan", "Sincronización de EDAN (pendientes)",
             "edan", "donut", grupo="sincronizacion", fuente="edan",
             col_label="concepto", eje_y="EDAN"),
        f"""SELECT COUNT(*) FILTER (WHERE e.pendiente_actualizacion) AS actualizacion,
                   COUNT(*) FILTER (WHERE e.pendiente_eliminacion) AS eliminacion,
                   COUNT(*) FILTER (WHERE NOT e.pendiente_actualizacion
                                    AND NOT e.pendiente_eliminacion) AS al_dia
            {FROM_E} WHERE {W}""",
        tupla=[("actualizacion", "Actualización pendiente", "#F59E00"),
               ("eliminacion", "Eliminación pendiente", "#EF4444"),
               ("al_dia", "Al día", "#10B981")])

    add(_esp("procedencia_edan", "EDAN por procedencia", "edan", "torta",
             grupo="sincronizacion", fuente="edan"),
        f"""SELECT COALESCE(e.procedencia, 'sin_procedencia') AS label,
                   COUNT(*) AS value {FROM_E} WHERE {W}
            GROUP BY e.procedencia ORDER BY value DESC, label""")

    add(_esp("edan_por_usuario_ugr", "EDAN por UGR responsable", "edan",
             "barras", grupo="usuarios", fuente="edan"),
        f"""SELECT COALESCE(ugr.nombre, ugr.usuario, 'Sin UGR') AS label,
                   COUNT(*) AS value {FROM_E} WHERE {W}
            GROUP BY e.id_usuario_ugr, ugr.nombre, ugr.usuario
            ORDER BY value DESC, label LIMIT {top}""")

    add(_esp("edan_por_alcalde", "EDAN por alcalde", "edan", "barras",
             grupo="usuarios", fuente="edan"),
        f"""SELECT COALESCE(alc.nombre, alc.usuario, 'Sin alcalde') AS label,
                   COUNT(*) AS value {FROM_E} WHERE {W}
            GROUP BY e.id_usuario_alcalde, alc.nombre, alc.usuario
            ORDER BY value DESC, label LIMIT {top}""")

    add(_esp("edan_por_importacion", "EDAN por archivo importado", "edan",
             "barras", grupo="usuarios", fuente="edan"),
        f"""SELECT COALESCE(il.nombre_archivo, 'Sin importación') AS label,
                   COUNT(*) AS value
            FROM edan.edan e
            LEFT JOIN edan.edan_importacion_log il ON il.id_importacion = e.id_importacion
            WHERE {W} GROUP BY e.id_importacion, il.nombre_archivo
            ORDER BY value DESC, label LIMIT {top}""")

    # ------------------------------------------------------------ aprobaciones
    aprob_rows = _rows(db, f"""
        SELECT a.nivel, a.estado, COUNT(*) AS value
        FROM edan.aprobaciones_edan a JOIN edan.edan e ON e.id_edan = a.id_edan
        WHERE {W} GROUP BY a.nivel, a.estado""".replace("{w}", w), p)

    add(_esp("aprobaciones_por_estado", "Aprobaciones por estado", "registros",
             "donut", grupo="aprobaciones", fuente="aprobacion",
             color_map=COLOR_APROB, orden="sql",
             orden_labels=["aprobado", "pendiente", "observado", "espera_correccion"],
             eje_x="Estado"),
        f"""SELECT COALESCE(a.estado, 'sin_estado') AS label, COUNT(*) AS value
            FROM edan.aprobaciones_edan a JOIN edan.edan e ON e.id_edan = a.id_edan
            WHERE {W} GROUP BY a.estado ORDER BY value DESC""")

    add(_esp("aprobaciones_por_nivel", "Aprobaciones por nivel de validación",
             "registros", "barras", grupo="aprobaciones", fuente="aprobacion",
             color_map=COLOR_NIVEL, orden="sql",
             orden_labels=["ugr", "alcalde", "dgr", "videcid"], eje_x="Nivel"),
        f"""SELECT COALESCE(a.nivel, 'sin_nivel') AS label, COUNT(*) AS value
            FROM edan.aprobaciones_edan a JOIN edan.edan e ON e.id_edan = a.id_edan
            WHERE {W} GROUP BY a.nivel ORDER BY value DESC""")

    if aprob_rows:
        niveles = [n for n in ("ugr", "alcalde", "dgr", "videcid")
                   if any(r["nivel"] == n for r in aprob_rows)]
        ests = [e for e in ("aprobado", "pendiente", "observado", "espera_correccion")
                if any(r["estado"] == e for r in aprob_rows)]
        add(_esp("aprobaciones_nivel_x_estado",
                 "Aprobaciones por nivel y estado", "registros",
                 "barras_apiladas", grupo="aprobaciones", fuente="aprobacion",
                 orden="sql", eje_x="Nivel"),
            f"""SELECT COALESCE(a.nivel, 'sin_nivel') AS label,
                       {", ".join(f"COUNT(*) FILTER (WHERE a.estado = '{e}') AS {e}" for e in ests)}
                FROM edan.aprobaciones_edan a
                JOIN edan.edan e ON e.id_edan = a.id_edan
                WHERE {W} GROUP BY a.nivel ORDER BY 1""",
            metricas=[(e, e.capitalize(), COLOR_APROB.get(e, "#999"))
                      for e in ests],
            extra=[(e, e.capitalize()) for e in ests])

    add(_esp("serie_aprobaciones", "Aprobaciones registradas en el tiempo",
             "registros", "linea", grupo="aprobaciones", serie="periodo",
             campo_fecha="modificacion", fuente="aprobacion",
             tipos=TIPOS_SERIE + ["torta", "donut"]),
        f"""SELECT date_trunc('{dt}', a.fecha_ultima_accion) AS periodo,
                   COUNT(*) AS valor
            FROM edan.aprobaciones_edan a JOIN edan.edan e ON e.id_edan = a.id_edan
            WHERE {W} AND a.fecha_ultima_accion IS NOT NULL
            GROUP BY 1 ORDER BY 1""")

    add(_esp("aprobaciones_observaciones", "Aprobaciones con observaciones y "
             "devoluciones", "registros", "donut", grupo="aprobaciones",
             fuente="aprobacion", col_label="concepto", eje_y="Registros"),
        f"""SELECT COUNT(*) FILTER (WHERE a.observacion IS NOT NULL
                                     AND a.observacion <> '') AS con_observacion,
                   COUNT(*) FILTER (WHERE a.fecha_devolucion IS NOT NULL) AS devueltas,
                   COUNT(*) FILTER (WHERE a.fecha_aprobacion IS NOT NULL) AS aprobadas
            FROM edan.aprobaciones_edan a JOIN edan.edan e ON e.id_edan = a.id_edan
            WHERE {W}""",
        tupla=[("con_observacion", "Con observación", "#E69F00"),
               ("devueltas", "Devueltas para corrección", "#8B5CF6"),
               ("aprobadas", "Con fecha de aprobación", "#10B981")])

    add(_esp("aprobaciones_por_edan", "EDAN con más aprobaciones registradas",
             "registros", "barras", grupo="aprobaciones", fuente="aprobacion",
             orden="sql", extra=[("municipio", "Municipio")]),
        f"""SELECT COALESCE(e.codigo_edan, e.uuid_edan::text) AS label,
                   COUNT(*) AS value, COALESCE(m.nombre, '') AS municipio
            FROM edan.aprobaciones_edan a JOIN edan.edan e ON e.id_edan = a.id_edan
            LEFT JOIN shared.municipio m ON m.id = e.id_municipio
            WHERE {W} GROUP BY e.id_edan, e.codigo_edan, e.uuid_edan, m.nombre
            ORDER BY value DESC LIMIT {top}""")

    # ------------------------------------------------------------ importaciones
    add(_esp("importaciones_totales", "Totales de importación", "filas", "donut",
             grupo="importaciones", fuente="importacion", col_label="concepto",
             eje_y="Filas"),
        f"""SELECT COALESCE(SUM(il.filas_procesadas), 0) AS procesadas,
                   COALESCE(SUM(il.filas_insertadas), 0) AS insertadas,
                   COALESCE(SUM(il.filas_actualizadas), 0) AS actualizadas,
                   COALESCE(SUM(il.filas_omitidas), 0) AS omitidas,
                   COALESCE(SUM(il.errores), 0) AS errores
            FROM edan.edan_importacion_log il
            WHERE il.id_importacion IN (SELECT e.id_importacion FROM edan.edan e
                                        WHERE {W} AND e.id_importacion IS NOT NULL)""",
        tupla=[("procesadas", "Filas procesadas", "#0072B2"),
               ("insertadas", "Insertadas", "#10B981"),
               ("actualizadas", "Actualizadas", "#56B4E9"),
               ("omitidas", "Omitidas", "#E69F00"),
               ("errores", "Con error", "#EF4444")])

    add(_esp("importaciones_por_archivo", "Filas insertadas por archivo importado",
             "filas", "barras", grupo="importaciones", fuente="importacion"),
        f"""SELECT il.nombre_archivo AS label,
                   COALESCE(SUM(il.filas_insertadas), 0) AS value
            FROM edan.edan_importacion_log il
            WHERE il.id_importacion IN (SELECT e.id_importacion FROM edan.edan e
                                        WHERE {W} AND e.id_importacion IS NOT NULL)
            GROUP BY il.id_importacion, il.nombre_archivo
            ORDER BY value DESC, label LIMIT {top}""")

    add(_esp("serie_importaciones", "Importaciones en el tiempo", "registros",
             "linea", grupo="importaciones", serie="periodo",
             campo_fecha="modificacion", fuente="importacion",
             tipos=TIPOS_SERIE + ["torta", "donut"]),
        f"""SELECT date_trunc('{dt}', il.fecha_importacion) AS periodo,
                   COUNT(*) AS valor
            FROM edan.edan_importacion_log il
            WHERE il.id_importacion IN (SELECT e.id_importacion FROM edan.edan e
                                        WHERE {W} AND e.id_importacion IS NOT NULL)
            GROUP BY 1 ORDER BY 1""")

    add(_esp("importaciones_por_resultado", "Resultado de la última importación",
             "filas", "barras_apiladas", grupo="importaciones",
             fuente="importacion", orden="sql"),
        f"""SELECT il.nombre_archivo AS label,
                   COALESCE(SUM(il.filas_insertadas), 0) AS insertadas,
                   COALESCE(SUM(il.filas_actualizadas), 0) AS actualizadas,
                   COALESCE(SUM(il.filas_omitidas), 0) AS omitidas,
                   COALESCE(SUM(il.errores), 0) AS errores
            FROM edan.edan_importacion_log il
            WHERE il.id_importacion IN (SELECT e.id_importacion FROM edan.edan e
                                        WHERE {W} AND e.id_importacion IS NOT NULL)
            GROUP BY il.id_importacion, il.nombre_archivo ORDER BY 1""",
        metricas=[("insertadas", "Insertadas", "#10B981"),
                  ("actualizadas", "Actualizadas", "#56B4E9"),
                  ("omitidas", "Omitidas", "#E69F00"),
                  ("errores", "Errores", "#EF4444")])

    # ------------------------------------ localidades de los EDAN filtrados
    ests_l = _estados_locales(db)
    col_est_l = {e["nombre"]: COLORES_ESTADO_LOCALIDAD.get(e["nombre"], "#94A3B8")
                 for e in ests_l}

    add_l(_esp("estados_localidades", "Estado de las localidades de los EDAN "
               "filtrados", "localidades", "donut", grupo="estados",
               color_map=col_est_l, orden="sql",
               orden_labels=[e["nombre"] for e in ests_l], fuente="localidad"),
          f"""SELECT COALESCE(ele.nombre, 'Sin estado') AS label, COUNT(*) AS value
              {FROM_L} WHERE {W}
              GROUP BY ele.id_edan_localidad_estado, ele.nombre, ele.orden
              ORDER BY ele.orden NULLS LAST""")

    add_l(_esp("grupos_activos_en_edan", "Grupos con actividad en los EDAN "
               "filtrados", "localidades", "barras_horizontales", grupo="secciones",
               fuente="localidad", orden="sql"),
          f"""SELECT {", ".join(f"COUNT(*) FILTER (WHERE l.{c}) AS {c}" for c in _GRUPOS_9)}
              {FROM_L} WHERE {W}""",
          tupla=[(c, _ETIQ_GRUPO[c], COLORES_GRUPO.get(c, "#0072B2"))
                 for c in _GRUPOS_9])

    add_l(_esp("localidades_por_edan", "Localidades por EDAN", "localidades",
               "barras", grupo="geografia", geo="municipio", fuente="localidad"),
          f"""SELECT COALESCE(m.nombre, 'Sin municipio') AS label, COUNT(*) AS value
              {FROM_L} WHERE {W} GROUP BY m.id, m.nombre
              ORDER BY value DESC, label LIMIT {top}""")

    add_l(_esp("poblacion_localidades_por_edan", "Población de las localidades "
               "por municipio", "personas", "barras", grupo="geografia",
               geo="municipio", fuente="localidad"),
          f"""SELECT COALESCE(m.nombre, 'Sin municipio') AS label,
                     COALESCE(SUM(l.total_poblacion_afectada), 0) AS value
              {FROM_L} WHERE {W} GROUP BY m.id, m.nombre
              ORDER BY value DESC, label LIMIT {top}""")

    add_l(_esp("fotos_por_edan", "Fotografías de las localidades por municipio",
               "fotos", "barras", grupo="fotos", geo="municipio",
               fuente="fotografia"),
          f"""SELECT COALESCE(m.nombre, 'Sin municipio') AS label, COUNT(*) AS value
              FROM edan.fotografias fo
              JOIN edan.edan_localidades l ON l.id_edan_localidad = fo.id_edan_localidad
              LEFT JOIN shared.municipio m ON m.id = l.id_municipio
              WHERE {W} AND fo.borrado_logico = FALSE
              GROUP BY m.id, m.nombre ORDER BY value DESC, label LIMIT {top}""")

    add_l(_esp("serie_localidades_llenado", "Localidades llenadas en el tiempo",
               "localidades", "linea", grupo="tiempo", serie="periodo",
               campo_fecha="llenado", fuente="localidad",
               tipos=TIPOS_SERIE + ["torta", "donut"]),
          f"""SELECT date_trunc('{dt}', l.fecha_llenado) AS periodo, COUNT(*) AS valor
              {FROM_L} WHERE {W} AND l.fecha_llenado IS NOT NULL
              GROUP BY 1 ORDER BY 1""")

    return {**_pie(f, opts, opts.get("nivel")), "unidad": "edan",
            "total_graficas": len(g), "graficas": g}
