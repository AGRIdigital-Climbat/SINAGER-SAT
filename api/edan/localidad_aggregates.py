"""Agregados de reportes sobre edan.edan_localidades (TODAS las localidades,
huérfanas + consolidadas). Operación OPEN: cualquier token válido, sin scope por rol."""

from typing import Optional, List, Dict
from datetime import date

from sqlalchemy.orm import Session
from sqlalchemy import text

from .service import (
    _row, _rows, IMP_FLAGS, IMP_FLAGS_NUEVOS,
    _filters, _reporte_where, _filters_from_query,
    get_mis_localidades_resumen,
)
from . import __version__  # not needed


# ------------------------------------------------------------
# Filtros sobre edan.edan_localidades (alias "l")
// ------------------------------------------------------------

def _filters_localidades(f: dict, alias: str = "l") -> tuple[list[str], dict]:
    """Condiciones SQL sobre edan.edan_localidades.
    Filtra TODAS las localidades (huérfanas + consolidadas).
    Los parámetros son opcionales y combinables (AND).
    """
    conds: list[str] = []
    params: dict = {}
    a = alias

    if f.get("q"):
        conds.append(f"{a}.localidad ILIKE :q")
        params["q"] = f"%{f['q']}%"

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
    if f.get("id_tipo_localidad") is not None:
        conds.append(f"{a}.id_tipo_localidad = :id_tipo_localidad")
        params["id_tipo_localidad"] = f["id_tipo_localidad"]
    if f.get("id_estado") is not None:
        conds.append(f"{a}.id_edan_localidad_estado = :id_estado")
        params["id_estado"] = f["id_estado"]
    if f.get("estado"):
        conds.append(f"{a}.id_edan_localidad_estado IN ("
            "SELECT id_edan_localidad_estado FROM edan.edan_localidades_estado "
            "WHERE LOWER(nombre) = LOWER(:estado)")
        )
        params["estado"] = f["estado"]
    if f.get("id_usuario") is not None:
        conds.append(f"{a}.id_usuario = :id_usuario")
        params["id_usuario"] = f["id_usuario"]

    if f.get("fecha_llenado_desde"):
        conds.append(f"{a}.fecha_llenado >= :fecha_llenado_desde")
        params["fecha_llenado_desde"] = f["fecha_llenado_desde"]
    if f.get("fecha_llenado_hasta"):
        conds.append(f"{a}.fecha_llenado <= :fecha_llenado_hasta")
        params["fecha_llenado_hasta"] = f["fecha_llenado_hasta"]
    if f.get("fecha_evento_desde"):
        conds.append(f"{a}.fecha_evento >= :fecha_evento_desde")
        params["fecha_evento_desde"] = f["fecha_evento_desde"]
    if f.get("fecha_evento_hasta"):
        conds.append(f"{a}.fecha_evento <= :fecha_evento_hasta")
        params["fecha_evento_hasta"] = f["fecha_evento_hasta"]

    for flag in IMP_FLAGS:
        if f.get(flag):
            conds.append(f"{a}.{flag} = TRUE")

    if f.get("solo_huerfanas") is True:
        conds.append(f"{a}.id_edan IS NULL")
    elif f.get("solo_huerfanas") is False:
        conds.append(f"{a}.id_edan IS NOT NULL")

    if f.get("pendiente_eliminacion") is not None:
        conds.append(f"{a}.pendiente_eliminacion = :pendiente_eliminacion")
        params["pendiente_eliminacion"] = f["pendiente_eliminacion"]
    if f.get("pendiente_actualizacion") is not None:
        conds.append(f"{a}.pendiente_actualizacion = :pendiente_actualizacion")
        params["pendiente_actualizacion"] = f["pendiente_actualizacion"]

    if f.get("tiene_agricultura"):
        conds.append(f"EXISTS ("
            "SELECT 1 FROM edan.edan_localidades_danos_agricultura ag "
            "WHERE ag.id_edan_localidad = {a}.id_edan_localidad)"
        )
    if f.get("tiene_pecuario"):
        conds.append(f"EXISTS ("
            "SELECT 1 FROM edan.edan_localidades_danos_pecuario dp "
            "WHERE dp.id_edan_localidad = {a}.id_edan_localidad)"
        )

    return conds, params


def _where_localidades(f: dict) -> tuple[str, dict]:
    conds, params = _filters_localidades(f or {})
    where = " WHERE " + " AND ".join(conds) if conds else ""
    return where, params


# ------------------------------------------------------------
# Reportes de agregados sobre localidades
# ------------------------------------------------------------

def resumen_localidades_documento(db: Session, f: dict | None = None) -> dict:
    """Resumen agregado de localidades (TODAS: huérfanas + consolidadas).
    Retorna {"totales": {...}, "por_estado": [...], "por_tipo_evento": [...]}."""
    f = f or {}
    where, params = _where_localidades(f)

    row = _row(db, f"""SELECT COUNT(*) AS total_localidades,
               COUNT(*) FILTER (WHERE id_edan IS NULL) AS total_huerfanas,
               COUNT(*) FILTER (WHERE id_edan IS NOT NULL) AS total_consolidadas,
               COUNT(*) FILTER (WHERE id_edan_localidad_estado IS NOT NULL) AS total_con_estado,
               COALESCE(SUM(total_poblacion_afectada), 0) AS total_poblacion_afectada,
               COALESCE(SUM(total_familias_afectadas), 0) AS total_familias_afectadas,
               COALESCE(SUM(total_familias_damnificadas), 0) AS total_familias_damnificadas
        FROM edan.edan_localidades l{where}""", params) or {}

    por_estado = [dict(r) for r in _rows(db, f"""SELECT l.id_edan_localidad_estado, ele.nombre AS estado, COUNT(*) AS cantidad
        FROM edan.edan_localidades l
        LEFT JOIN edan.edan_localidades_estado ele
            ON ele.id_edan_localidad_estado = l.id_edan_localidad_estado
        {where}
        GROUP BY l.id_edan_localidad_estado, ele.nombre ORDER BY cantidad DESC
    """, params)]

    por_tipo_evento = [dict(r) for r in _rows(db, f"""SELECT l.id_tipo_evento, COALESCE(te.nombre, 'Sin tipo') AS tipo_evento, COUNT(*) AS cantidad
        FROM edan.edan_localidades l
        LEFT JOIN edan.tipo_evento te ON te.id_tipo_evento = l.id_tipo_evento
        {where}
        GROUP BY l.id_tipo_evento, te.nombre ORDER BY cantidad DESC
    """, params)]

    return {
        "totales": dict(row) if row else {},
        "por_estado": por_estado,
        "por_tipo_evento": por_tipo_evento,
    }


def reporte_agricultura_localidades(db: Session, f: dict | None = None) -> List[dict]:
    """Agricultura sobre TODAS las localidades (no solo consolidadas en EDAN).
    Agrupa por cultivo: tipo_cultivo, nombre, hectareas_afectadas, hectareas_perdidas."""
    f = f or {}
    where, params = _where_localidades(f)
    return [dict(r) for r in _rows(db, f"""SELECT a.id_cultivo, c.nombre AS cultivo_nombre, c.grupo AS cultivo_grupo,
               COUNT(DISTINCT a.id_edan_localidad) AS total_localidades,
               COUNT(*) AS total_registros,
               COALESCE(SUM(a.hectareas_afectadas), 0) AS hectareas_afectadas,
               COALESCE(SUM(a.hectareas_perdidas), 0) AS hectareas_perdidas
        FROM edan.edan_localidades_danos_agricultura a
        JOIN edan.edan_localidades l ON l.id_edan_localidad = a.id_edan_localidad
        LEFT JOIN shared.cultivo c ON c.id = a.id_cultivo
        {where}
        GROUP BY a.id_cultivo, c.nombre, c.grupo
        ORDER BY hectareas_afectadas DESC
    """"]]


def reporte_pecuario_localidades(db: Session, f: dict | None = None) -> List[dict]:
    """Pecuario sobre TODAS las localidades (no solo consolidadas en EDAN).
    Agrupa por especie: especie, animales_afectados, animales_muertos."""
    f = f or {}
    where, params = _where_localidades(f)
    return [dict(r) for r in _rows(db, f"""SELECT a.id_especie, sp.nombre AS especie_catalogo, sp.grupo AS especie_grupo,
               COUNT(DISTINCT a.id_edan_localidad) AS total_localidades,
               COUNT(*) AS total_registros,
               COALESCE(SUM(a.animales_afectados), 0) AS animales_afectados,
               COALESCE(SUM(a.animales_muertos), 0) AS animales_muertos
        FROM edan.edan_localidades_danos_pecuario a
        JOIN edan.edan_localidades l ON l.id_edan_localidad = a.id_edan_localidad
        LEFT JOIN shared.pecuario sp ON sp.id = a.id_especie
        {where}
        GROUP BY a.id_especie, sp.nombre, sp.grupo
        ORDER BY animales_afectados DESC
    """"]]


def reporte_geografico_localidades(db: Session, f: dict | None = None) -> List[dict]:
    """Geográfico sobre TODAS las localidades, agrupado por departamento/provincia/Municipio."""
    f = f or {}
    where, params = _where_localidades(f)
    return [dict(r) for r in _rows(db, f"""SELECT d.id AS id_departamento, d.nombre AS departamento,
               p.id AS id_provincia, p.nombre AS provincia,
               m.id AS id_municipio, m.nombre AS municipio,
               COUNT(*) AS total_localidades,
               COUNT(*) FILTER (WHERE l.id_edan IS NULL) AS total_huerfanas,
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
    """"]]
