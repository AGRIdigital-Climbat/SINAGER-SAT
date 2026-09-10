from datetime import date as date_type
from datetime import datetime as datetime_type
import json

from sqlalchemy import text
from sqlalchemy.orm import Session


# ============================================================================
#  HELPERS COMPARTIDOS
# ============================================================================

def _row(db: Session, query: str, params: dict):
    r = db.execute(text(query), params).mappings().first()
    return dict(r) if r else None


def _rows(db: Session, query: str, params: dict) -> list:
    return [dict(r) for r in db.execute(text(query), params).mappings().all()]


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
#  DOCUMENTOS: repositorio.documentos (tabla mínima, sin versionado)
# ============================================================================

def upload_documento(
    db: Session,
    id_edan: int,
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
) -> int:
    """Inserta un nuevo documento PDF (sin versionado)."""
    result = db.execute(text("""
        INSERT INTO repositorio.documentos
            (id_edan, id_tipo_documento, nombre_original, path_archivo,
             tamano_bytes, hash_sha256, id_usuario_subio,
             id_municipio, id_departamento, id_provincia,
             fecha_documento, nombre_documento,
             observaciones, tiene_firma_digital, resultado_firma,
             fecha_validacion_firma)
        VALUES
            (:id_edan, :id_tipo_documento, :nombre_original, :path_archivo,
             :tamano_bytes, :hash_sha256, :id_usuario_subio,
             :id_municipio, :id_departamento, :id_provincia,
             :fecha_documento, :nombre_documento,
             :observaciones, :tiene_firma_digital,
             CAST(:resultado_firma AS jsonb), :fecha_validacion_firma)
        RETURNING id_documento
    """), {
        "id_edan": id_edan,
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
    }).scalar()
    db.commit()
    return result


def list_documentos_by_edan(
    db: Session,
    id_edan: int,
    id_tipo_documento: int | None = None,
    include_inactive: bool = False,
):
    """Lista documentos de un EDAN."""
    conds = ["d.id_edan = :id"]
    params: dict = {"id": id_edan}
    if not include_inactive:
        conds.append("d.activo = TRUE")
    if id_tipo_documento:
        conds.append("d.id_tipo_documento = :tipo")
        params["tipo"] = id_tipo_documento

    where = " AND ".join(conds)
    return _rows(db, f"""
        SELECT d.*, t.codigo AS tipo_codigo, t.nombre AS tipo_nombre
        FROM repositorio.documentos d
        JOIN repositorio.tipo_documento t ON t.id_tipo_documento = d.id_tipo_documento
        WHERE {where}
        ORDER BY t.orden, d.fecha_subida DESC
    """, params)


def get_documento(db: Session, id_documento: int):
    """Obtiene un documento específico con su tipo."""
    return _row(db, """
        SELECT d.*, t.codigo AS tipo_codigo, t.nombre AS tipo_nombre
        FROM repositorio.documentos d
        JOIN repositorio.tipo_documento t ON t.id_tipo_documento = d.id_tipo_documento
        WHERE d.id_documento = :id
    """, {"id": id_documento})


def update_documento(db: Session, id_documento: int, data: dict) -> bool:
    """Actualiza observaciones/activo de un documento."""
    fields = {k: v for k, v in data.items() if v is not None}
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
):
    """Búsqueda por nombre_documento (ILIKE) y nombre_original."""
    params = {"q": f"%{query_text}%", "limit": limit}
    where = """(d.activo = TRUE)
               AND (d.nombre_documento ILIKE :q OR d.nombre_original ILIKE :q)"""
    if id_municipio:
        where += " AND d.id_municipio = :m"
        params["m"] = id_municipio

    return _rows(db, f"""
        SELECT d.*,
               t.codigo AS tipo_codigo, t.nombre AS tipo_nombre
        FROM repositorio.documentos d
        JOIN repositorio.tipo_documento t ON t.id_tipo_documento = d.id_tipo_documento
        WHERE {where}
        ORDER BY d.fecha_documento DESC NULLS LAST, d.fecha_subida DESC
        LIMIT :limit
    """, params)


def list_documentos_filtrados(
    db: Session,
    id_edan: int | None = None,
    id_departamento: int | None = None,
    id_provincia: int | None = None,
    id_municipio: int | None = None,
    id_tipo_documento: int | None = None,
    fecha_desde: str | None = None,
    fecha_hasta: str | None = None,
    nombre_documento_like: str | None = None,
    limit: int = 50,
    skip: int = 0,
):
    """Lista documentos con filtros por metadata estructurada."""
    conds = ["d.activo = TRUE"]
    params: dict = {"limit": limit, "skip": skip}

    if id_edan is not None:
        conds.append("d.id_edan = :id_edan")
        params["id_edan"] = id_edan
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
    if fecha_desde:
        conds.append("d.fecha_documento >= :fecha_desde")
        params["fecha_desde"] = fecha_desde
    if fecha_hasta:
        conds.append("d.fecha_documento <= :fecha_hasta")
        params["fecha_hasta"] = fecha_hasta
    if nombre_documento_like:
        conds.append("d.nombre_documento ILIKE :nombre_documento_like")
        params["nombre_documento_like"] = f"%{nombre_documento_like}%"

    where = " AND ".join(conds)
    rows = _rows(db, f"""
        SELECT d.*, t.codigo AS tipo_codigo, t.nombre AS tipo_nombre
        FROM repositorio.documentos d
        JOIN repositorio.tipo_documento t ON t.id_tipo_documento = d.id_tipo_documento
        WHERE {where}
        ORDER BY d.fecha_documento DESC NULLS LAST, d.fecha_subida DESC
        LIMIT :limit OFFSET :skip
    """, params)
    total = _row(db, f"""
        SELECT COUNT(*) AS c
        FROM repositorio.documentos d
        JOIN repositorio.tipo_documento t ON t.id_tipo_documento = d.id_tipo_documento
        WHERE {where}
    """, params)["c"]
    return rows, total
