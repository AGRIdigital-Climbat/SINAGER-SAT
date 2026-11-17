from datetime import date as date_type
from datetime import datetime as datetime_type
import json

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..pagination import pagina_limit_offset


# ============================================================================
#  HELPERS COMPARTIDOS
# ============================================================================

def _row(db: Session, query: str, params: dict):
    r = db.execute(text(query), params).mappings().first()
    return dict(r) if r else None


def _rows(db: Session, query: str, params: dict) -> list:
    return [dict(r) for r in db.execute(text(query), params).mappings().all()]


# ============================================================================
#  ORIGEN DEL DOCUMENTO (EDAN / RIDA / DOC_PRECEDENTE)
# ============================================================================
#  Columna explicita 'origen' (v2.65.0): EDAN, RIDA o DOC_PRECEDENTE.
#  Fallback defensivo para entornos previos a la migracion.
_ORIGEN_SQL = (
    "COALESCE(d.origen, CASE WHEN d.id_evento_rida IS NULL THEN 'EDAN' ELSE 'RIDA' END) "
    "AS origen"
)

# Firmas digitales: tambien derivadas, no columnas.
_CANTIDAD_FIRMAS_SQL = (
    "COALESCE(CASE WHEN (d.resultado_firma->>'cantidad_firmas') ~ '^[0-9]+$' "
    "THEN (d.resultado_firma->>'cantidad_firmas')::int END, 0) AS cantidad_firmas"
)
_FIRMA_VALIDADA_SQL = (
    "CASE WHEN lower(d.resultado_firma->>'finalizado') IN ('true','t','1') "
    "THEN TRUE ELSE FALSE END AS firma_validada"
)

_SELECT_DOCS = f"""
    SELECT d.*, {_ORIGEN_SQL}, {_CANTIDAD_FIRMAS_SQL}, {_FIRMA_VALIDADA_SQL},
           t.codigo AS tipo_codigo, t.nombre AS tipo_nombre
    FROM repositorio.documentos d
    JOIN repositorio.tipo_documento t ON t.id_tipo_documento = d.id_tipo_documento
"""

# Mismo FROM del listado, para el COUNT(*) del total sin paginar.
_FROM_DOCS = """
    FROM repositorio.documentos d
    JOIN repositorio.tipo_documento t ON t.id_tipo_documento = d.id_tipo_documento
"""


# ============================================================================
#  CATÁLOGO: repositorio.tipo_documento
# ============================================================================

def list_tipos_documento(db: Session, include_inactive: bool = False):
    if include_inactive:
        return _rows(db, """
            SELECT * FROM repositorio.tipo_documento ORDER BY orden, nombre
        """, {})
    return _rows(db, """
        SELECT * FROM repositorio.tipo_documento WHERE activo = TRUE ORDER BY orden, nombre
    """, {})


def get_tipo_documento(db: Session, id_tipo: int):
    return _row(db, """
        SELECT * FROM repositorio.tipo_documento WHERE id_tipo_documento = :id
    """, {"id": id_tipo})


def create_tipo_documento(db: Session, data: dict) -> int:
    payload = {
        "codigo": data["codigo"],
        "nombre": data["nombre"],
        "descripcion": data.get("descripcion"),
        "orden": data.get("orden", 0),
        "activo": data.get("activo", True),
        "requiere_versionado": data.get("requiere_versionado", False),
        "extensiones_permitidas": data.get("extensiones_permitidas", "pdf"),
        "tamano_maximo_bytes": data.get("tamano_maximo_bytes", 52428800),
    }
    result = db.execute(text("""
        INSERT INTO repositorio.tipo_documento
            (codigo, nombre, descripcion, orden, activo,
             requiere_versionado, extensiones_permitidas, tamano_maximo_bytes)
        VALUES (:codigo, :nombre, :descripcion, :orden, :activo,
                :requiere_versionado, :extensiones_permitidas, :tamano_maximo_bytes)
        RETURNING id_tipo_documento
    """), payload).scalar()
    db.commit()
    return result


def update_tipo_documento(db: Session, id_tipo: int, data: dict) -> bool:
    set_clause = ", ".join(f"{k} = :{k}" for k in data if data[k] is not None)
    if not set_clause:
        return True
    data["id"] = id_tipo
    db.execute(text(f"""
        UPDATE repositorio.tipo_documento SET {set_clause} WHERE id_tipo_documento = :id
    """), data)
    db.commit()
    return True


def delete_tipo_documento(db: Session, id_tipo: int, hard: bool = False) -> bool:
    if hard:
        result = db.execute(text("""
            DELETE FROM repositorio.tipo_documento WHERE id_tipo_documento = :id
        """), {"id": id_tipo})
    else:
        result = db.execute(text("""
            UPDATE repositorio.tipo_documento SET activo = FALSE WHERE id_tipo_documento = :id
        """), {"id": id_tipo})
    db.commit()
    return result.rowcount > 0


# ============================================================================
#  DOCUMENTOS: repositorio.documentos
# ============================================================================

def resolver_destino_documento(
    db: Session,
    id_edan: int | None = None,
    id_evento_rida: int | None = None,
) -> dict | None:
    """Valida el destino de un documento y devuelve los ids ya resueltos.

    EDAN/RIDA mantienen contrato existente. Para DOC_PRECEDENTE (respaldo
    municipal, sin id_edan/id_evento_rida) el destino se resuelve en el router
    con la geo del formulario.
    """
    if id_edan is None and id_evento_rida is None:
        raise ValueError("Se debe enviar id_edan o id_evento_rida")

    if id_evento_rida is not None:
        evento = _row(db, """
            SELECT ev.id_evento_rida, ev.id_edan, e.id_municipio
            FROM rida.evento_rida ev
            LEFT JOIN edan.edan e ON e.id_edan = ev.id_edan
            WHERE ev.id_evento_rida = :id
        """, {"id": id_evento_rida})
        if not evento:
            return None

        return {
            "id_edan": evento["id_edan"],
            "id_evento_rida": evento["id_evento_rida"],
            "id_municipio": evento["id_municipio"],
            "origen": "RIDA",
        }

    edan_row = _row(db, """
        SELECT id_municipio FROM edan.edan WHERE id_edan = :id
    """, {"id": id_edan})
    if not edan_row:
        return None

    return {
        "id_edan": id_edan,
        "id_evento_rida": None,
        "id_municipio": edan_row["id_municipio"],
        "origen": "EDAN",
    }


def normalizar_codigo_documento(codigo: str | None) -> str | None:
    """Codigo de agrupacion/rastreo en formato canonico (trim + MAYUSCULAS)."""
    if codigo is None:
        return None
    cod = codigo.strip().upper()
    return cod or None


def generar_codigo_documento(db: Session, id_municipio: int | None) -> str:
    """Codigo autogenerado para DOC_PRECEDENTE: RES-{codigo_ine}-{YYYY}-{sec:05d}.

    Usa la secuencia repositorio.codigo_documento_seq (sin condiciones de carrera
    entre workers uvicorn).
    """
    codigo_ine = "SINMUN"
    if id_municipio is not None:
        row = _row(db, "SELECT codigo_ine FROM shared.municipio WHERE id = :id",
                   {"id": id_municipio})
        if row and row["codigo_ine"]:
            codigo_ine = str(row["codigo_ine"])
    seq = db.execute(text("SELECT nextval('repositorio.codigo_documento_seq')")).scalar()
    return f"RES-{codigo_ine}-{datetime_type.now().year}-{int(seq):05d}"


def upload_documento(
    db: Session,
    id_edan: int | None,
    id_tipo_documento: int,
    file_path: str,
    nombre_original: str,
    tamano_bytes: int,
    id_usuario: int,
    id_municipio: int,
    id_departamento: int,
    id_provincia: int,
    fecha_documento: date_type | str,
    nombre_documento: str,
    observaciones: str | None = None,
    hash_sha256: str | None = None,
    tiene_firma_digital: bool = False,
    resultado_firma: dict | None = None,
    fecha_validacion_firma: datetime_type | None = None,
    id_evento_rida: int | None = None,
    origen: str | None = None,
    codigo_documento: str | None = None,
) -> int:
    """Inserta un nuevo documento PDF (sin versionado).

    'origen' lo define la ruta de subida (EDAN, RIDA, DOC_PRECEDENTE).
    Si no se indica, se infiere por compatibilidad.
    """
    if origen is None:
        origen = "RIDA" if id_evento_rida is not None else "EDAN"

    result = db.execute(text("""
        INSERT INTO repositorio.documentos
            (id_edan, id_evento_rida, origen, id_tipo_documento, nombre_original, path_archivo,
             tamano_bytes, hash_sha256, id_usuario_subio,
             id_municipio, id_departamento, id_provincia,
             fecha_documento, nombre_documento,
             observaciones, tiene_firma_digital, resultado_firma,
             fecha_validacion_firma, codigo_documento)
        VALUES
            (:id_edan, :id_evento_rida, :origen, :id_tipo_documento, :nombre_original, :path_archivo,
             :tamano_bytes, :hash_sha256, :id_usuario_subio,
             :id_municipio, :id_departamento, :id_provincia,
             :fecha_documento, :nombre_documento,
             :observaciones, :tiene_firma_digital,
             CAST(:resultado_firma AS jsonb), :fecha_validacion_firma, :codigo_documento)
        RETURNING id_documento
    """), {
        "id_edan": id_edan,
        "id_evento_rida": id_evento_rida,
        "origen": origen,
        "id_tipo_documento": id_tipo_documento,
        "nombre_original": nombre_original,
        "path_archivo": file_path,
        "tamano_bytes": tamano_bytes,
        "hash_sha256": hash_sha256,
        "id_usuario_subio": id_usuario,
        "id_municipio": id_municipio,
        "id_departamento": id_departamento,
        "id_provincia": id_provincia,
        "fecha_documento": fecha_documento,
        "nombre_documento": nombre_documento,
        "observaciones": observaciones,
        "tiene_firma_digital": tiene_firma_digital,
        "resultado_firma": json.dumps(resultado_firma) if resultado_firma else None,
        "fecha_validacion_firma": fecha_validacion_firma,
        "codigo_documento": normalizar_codigo_documento(codigo_documento),
    }).scalar()
    db.commit()
    return result


def _aplicar_filtros_documentos(
    *,
    origen: str | None = None,
    codigo_documento: str | None = None,
    id_edan: int | None = None,
    id_evento_rida: int | None = None,
    id_departamento: int | None = None,
    id_provincia: int | None = None,
    id_municipio: int | None = None,
    id_tipo_documento: int | None = None,
    id_usuario_subio: int | None = None,
    fecha_desde: str | None = None,
    fecha_hasta: str | None = None,
    nombre_documento_like: str | None = None,
    tiene_firma_digital: bool | None = None,
    include_inactive: bool = False,
    conds: list | None = None,
    params: dict | None = None,
):
    conds = list(conds or [])
    params = dict(params or {})

    if not include_inactive:
        conds.append("d.activo = TRUE")
    if origen is not None:
        conds.append(f"({_ORIGEN_SQL.split(' AS ')[0]}) = :origen")
        params["origen"] = origen
    if codigo_documento:
        conds.append("d.codigo_documento = :codigo_documento")
        params["codigo_documento"] = normalizar_codigo_documento(codigo_documento)
    if id_edan is not None:
        conds.append("d.id_edan = :id_edan")
        params["id_edan"] = id_edan
    if id_evento_rida is not None:
        conds.append("d.id_evento_rida = :id_evento_rida")
        params["id_evento_rida"] = id_evento_rida
    if id_departamento is not None:
        conds.append("d.id_departamento = :id_departamento")
        params["id_departamento"] = id_departamento
    if id_provincia is not None:
        conds.append("d.id_provincia = :id_provincia")
        params["id_provincia"] = id_provincia
    if id_municipio is not None:
        conds.append("d.id_municipio = :id_municipio")
        params["id_municipio"] = id_municipio
    if id_tipo_documento is not None:
        conds.append("d.id_tipo_documento = :id_tipo_documento")
        params["id_tipo_documento"] = id_tipo_documento
    if id_usuario_subio is not None:
        conds.append("d.id_usuario_subio = :id_usuario_subio")
        params["id_usuario_subio"] = id_usuario_subio
    if fecha_desde:
        conds.append("d.fecha_documento >= :fecha_desde")
        params["fecha_desde"] = fecha_desde
    if fecha_hasta:
        conds.append("d.fecha_documento <= :fecha_hasta")
        params["fecha_hasta"] = fecha_hasta
    if nombre_documento_like:
        conds.append("(d.nombre_documento ILIKE :nombre_documento_like OR d.nombre_original ILIKE :nombre_documento_like)")
        params["nombre_documento_like"] = f"%{nombre_documento_like}%"
    if tiene_firma_digital is not None:
        conds.append("d.tiene_firma_digital = :tiene_firma_digital")
        params["tiene_firma_digital"] = tiene_firma_digital

    if not conds:
        conds.append("1=1")
    return " AND ".join(conds), params


def list_documentos_by_evento_rida(
    db: Session,
    id_evento_rida: int,
    id_tipo_documento: int | None = None,
    include_inactive: bool = False,
    limit: int | None = None,
    skip: int = 0,
    todos: bool = False,
):
    """Lista documentos de un evento RIDA (origen = RIDA)."""
    where, params = _aplicar_filtros_documentos(
        origen="RIDA",
        id_evento_rida=id_evento_rida,
        id_tipo_documento=id_tipo_documento,
        include_inactive=include_inactive,
    )
    total = _row(db, f"SELECT COUNT(*) AS total {_FROM_DOCS} WHERE {where}", params)["total"]
    page, page_params = pagina_limit_offset(limit, skip, todos)
    rows = _rows(db, _SELECT_DOCS + f"""
        WHERE {where}
        ORDER BY t.orden, d.fecha_subida DESC
        {page}
    """, {**params, **page_params})
    return rows, total


def list_documentos_by_edan(
    db: Session,
    id_edan: int,
    id_tipo_documento: int | None = None,
    include_inactive: bool = False,
    origen: str | None = None,
    limit: int | None = None,
    skip: int = 0,
    todos: bool = False,
):
    """Lista documentos de un EDAN.

    Sin 'origen' devuelve TODOS los documentos de ese EDAN (incluye RIDA
    asociados). Con origen='EDAN' o 'RIDA' filtra por origen.
    """
    where, params = _aplicar_filtros_documentos(
        origen=origen,
        id_edan=id_edan,
        id_tipo_documento=id_tipo_documento,
        include_inactive=include_inactive,
    )
    total = _row(db, f"SELECT COUNT(*) AS total {_FROM_DOCS} WHERE {where}", params)["total"]
    page, page_params = pagina_limit_offset(limit, skip, todos)
    rows = _rows(db, _SELECT_DOCS + f"""
        WHERE {where}
        ORDER BY t.orden, d.fecha_subida DESC
        {page}
    """, {**params, **page_params})
    return rows, total


def get_documento(db: Session, id_documento: int):
    """Obtiene un documento específico con su tipo y su origen."""
    return _row(db, _SELECT_DOCS + """
        WHERE d.id_documento = :id
    """, {"id": id_documento})


def update_documento(db: Session, id_documento: int, data: dict) -> bool:
    """Actualiza observaciones/activo/codigo_documento de un documento."""
    fields = {k: v for k, v in data.items() if v is not None}
    if "codigo_documento" in fields:
        fields["codigo_documento"] = normalizar_codigo_documento(
            fields["codigo_documento"])
    if not fields:
        return True
    set_clause = ", ".join(f"{k} = :{k}" for k in fields)
    fields["id_documento"] = id_documento
    db.execute(text(f"""
        UPDATE repositorio.documentos SET {set_clause} WHERE id_documento = :id_documento
    """), fields)
    db.commit()
    return True


def delete_documento(db: Session, id_documento: int, hard: bool = False) -> bool:
    """Elimina un documento (soft delete por defecto)."""
    if hard:
        result = db.execute(text("""
            DELETE FROM repositorio.documentos WHERE id_documento = :id
        """), {"id": id_documento})
    else:
        result = db.execute(text("""
            UPDATE repositorio.documentos SET activo = FALSE WHERE id_documento = :id
        """), {"id": id_documento})
    db.commit()
    return result.rowcount > 0


def buscar_documentos(
    db: Session,
    query_text: str,
    id_municipio: int | None = None,
    limit: int = 50,
    origen: str | None = None,
    skip: int = 0,
    todos: bool = False,
):
    """Búsqueda por nombre_documento/nombre_original (ILIKE).

    `limit`/`skip` paginan (los más recientes primero); `todos=True` devuelve todo.
    Devuelve (rows, total) sin paginar con los mismos filtros.
    """
    where, params = _aplicar_filtros_documentos(
        origen=origen,
        id_municipio=id_municipio,
        nombre_documento_like=query_text,
        include_inactive=False,
    )

    total = _row(db, f"SELECT COUNT(*) AS total {_FROM_DOCS} WHERE {where}", params)["total"]
    page, page_params = pagina_limit_offset(limit, skip, todos)
    rows = _rows(db, _SELECT_DOCS + f"""
        WHERE {where}
        ORDER BY d.fecha_documento DESC NULLS LAST, d.fecha_subida DESC
        {page}
    """, {**params, **page_params})
    return rows, total


def list_documentos_filtrados(
    db: Session,
    origen: str | None = None,
    codigo_documento: str | None = None,
    id_edan: int | None = None,
    id_evento_rida: int | None = None,
    id_departamento: int | None = None,
    id_provincia: int | None = None,
    id_municipio: int | None = None,
    id_tipo_documento: int | None = None,
    id_usuario_subio: int | None = None,
    fecha_desde: str | None = None,
    fecha_hasta: str | None = None,
    nombre_documento_like: str | None = None,
    tiene_firma_digital: bool | None = None,
    include_inactive: bool = False,
    limit: int | None = 50,
    skip: int = 0,
    todos: bool = False,
):
    """Listado general de documentos (vista nacional) con filtros y paginación.

    Incluye EDAN, RIDA y DOC_PRECEDENTE. 'total' es el total sin paginar con
    los mismos filtros.
    """
    where, params = _aplicar_filtros_documentos(
        origen=origen,
        codigo_documento=codigo_documento,
        id_edan=id_edan,
        id_evento_rida=id_evento_rida,
        id_departamento=id_departamento,
        id_provincia=id_provincia,
        id_municipio=id_municipio,
        id_tipo_documento=id_tipo_documento,
        id_usuario_subio=id_usuario_subio,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        nombre_documento_like=nombre_documento_like,
        tiene_firma_digital=tiene_firma_digital,
        include_inactive=include_inactive,
    )

    total = _row(db, f"SELECT COUNT(*) AS total {_FROM_DOCS} WHERE {where}", params)["total"]
    page, page_params = pagina_limit_offset(limit, skip, todos)
    rows = _rows(db, _SELECT_DOCS + f"""
        WHERE {where}
        ORDER BY d.fecha_documento DESC NULLS LAST, d.fecha_subida DESC
        {page}
    """, {**params, **page_params})
    return rows, total


def list_documentos_by_codigo(
    db: Session,
    codigo_documento: str,
    limit: int = 50,
    skip: int = 0,
    todos: bool = False,
):
    """Documentos activos agrupados por codigo_documento (expediente de
    DOC_PRECEDENTE). Normaliza el codigo (trim + MAYUSCULAS).

    Devuelve (rows, total) con paginacion reciente primero, misma forma que
    el listado general.
    """
    cod = normalizar_codigo_documento(codigo_documento)
    if not cod:
        return [], 0
    return list_documentos_filtrados(
        db, codigo_documento=cod, limit=limit, skip=skip, todos=todos,
    )
