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
#  ORIGEN DEL DOCUMENTO (EDAN / RIDA)
# ============================================================================
#  El origen NO es una columna: se deriva de 'id_evento_rida'. Asi no puede
#  quedar desincronizado del dato real, no necesita backfill y no hay dos
#  fuentes de verdad.
#
#      id_evento_rida IS NULL      -> 'edan'  (documento de EDAN)
#      id_evento_rida IS NOT NULL  -> 'rida'  (documento de RIDA/evento)
_ORIGEN_SQL = "CASE WHEN d.id_evento_rida IS NULL THEN 'edan' ELSE 'rida' END AS origen"

# Firmas digitales: tambien derivadas, no columnas.
#
#   resultado_firma es el jsonb con la respuesta de AGETIC, que ya trae
#   'cantidad_firmas' y 'finalizado'. Se exponen planas para que el front no
#   tenga que abrir el jsonb, y para poder distinguir "se valido y no tiene
#   firma" de "no se pudo validar" (AGETIC caido o PDF > 20 MB):
#
#       validado, N firmas -> cantidad_firmas=N, firma_validada=true
#       validado, sin firma-> cantidad_firmas=0, firma_validada=true
#       AGETIC caido/>20MB -> cantidad_firmas=0, firma_validada=false
#       doc sin validar     -> cantidad_firmas=0, firma_validada=false
#
# El CASE con regex evita que un jsonb inesperado reviente con un 500 toda la
# lista: si el valor no es un entero limpio, devuelve 0.
_CANTIDAD_FIRMAS_SQL = (
    "COALESCE(CASE WHEN (d.resultado_firma->>'cantidad_firmas') ~ '^[0-9]+$' "
    "THEN (d.resultado_firma->>'cantidad_firmas')::int END, 0) AS cantidad_firmas"
)
# lower(NULL) IN (...) no es TRUE, asi que un resultado_firma NULL cae en ELSE
# (no validado), que es lo correcto.
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
#  DOCUMENTOS: repositorio.documentos (tabla mínima, sin versionado)
# ============================================================================

def resolver_destino_documento(
    db: Session,
    id_edan: int | None = None,
    id_evento_rida: int | None = None,
) -> dict | None:
    """Valida el destino de un documento y devuelve los ids ya resueltos.

    El repositorio es compartido: un documento es de EDAN o de RIDA, segun cual
    de los dos ids llegue. Devuelve None si la entidad indicada no existe (el
    router responde 404) y lanza ValueError si no llega ninguno de los dos.

    Cuando llega 'id_evento_rida' se guarda TAMBIÉN el 'id_edan' que el
    evento ya tiene (rida.evento_rida.id_edan), para que el documento
    quede vinculado a las dos tablas y se pueda rastrear desde la pantalla del
    EDAN. El cliente solo manda un id; el otro lo resuelve la API.

    Returns:
        {
          "id_edan": int | None,        # el evento siempre tiene EDAN
          "id_evento_rida": int | None,  # NULL = documento de EDAN
          "id_municipio": int | None,    # resuelto, para el nombre del archivo
        }
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
    }


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
) -> int:
    """Inserta un nuevo documento PDF (sin versionado).

    Guarda el par (id_edan, id_evento_rida) ya resuelto por
    resolver_destino_documento(); 'id_evento_rida' NULL = documento de EDAN.
    """
    result = db.execute(text("""
        INSERT INTO repositorio.documentos
            (id_edan, id_evento_rida, id_tipo_documento, nombre_original, path_archivo,
             tamano_bytes, hash_sha256, id_usuario_subio,
             id_municipio, id_departamento, id_provincia,
             fecha_documento, nombre_documento,
             observaciones, tiene_firma_digital, resultado_firma,
             fecha_validacion_firma)
        VALUES
            (:id_edan, :id_evento_rida, :id_tipo_documento, :nombre_original, :path_archivo,
             :tamano_bytes, :hash_sha256, :id_usuario_subio,
             :id_municipio, :id_departamento, :id_provincia,
             :fecha_documento, :nombre_documento,
             :observaciones, :tiene_firma_digital,
             CAST(:resultado_firma AS jsonb), :fecha_validacion_firma)
        RETURNING id_documento
    """), {
        "id_edan": id_edan,
        "id_evento_rida": id_evento_rida,
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


def list_documentos_by_evento_rida(
    db: Session,
    id_evento_rida: int,
    id_tipo_documento: int | None = None,
    include_inactive: bool = False,
    limit: int | None = None,
    skip: int = 0,
    todos: bool = False,
):
    """Lista documentos de un evento RIDA (origen = rida)."""
    conds = ["d.id_evento_rida = :id"]
    params: dict = {"id": id_evento_rida}
    if not include_inactive:
        conds.append("d.activo = TRUE")
    if id_tipo_documento:
        conds.append("d.id_tipo_documento = :tipo")
        params["tipo"] = id_tipo_documento

    where = " AND ".join(conds)
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

    Sin 'origen' devuelve TODOS los documentos de ese EDAN, incluidos los de sus
    eventos RIDA (cada documento RIDA guarda tambien su id_edan, asi que es
    rastreable desde la pantalla del EDAN). Con origen='edan' se limita a los
    que no tienen evento RIDA, y con 'rida' a los que si.
    """
    conds = ["d.id_edan = :id"]
    params: dict = {"id": id_edan}
    if not include_inactive:
        conds.append("d.activo = TRUE")
    if id_tipo_documento:
        conds.append("d.id_tipo_documento = :tipo")
        params["tipo"] = id_tipo_documento
    if origen == "edan":
        conds.append("d.id_evento_rida IS NULL")
    elif origen == "rida":
        conds.append("d.id_evento_rida IS NOT NULL")

    where = " AND ".join(conds)
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
    origen: str | None = None,
    skip: int = 0,
    todos: bool = False,
):
    """Búsqueda por nombre_documento (ILIKE) y nombre_original.

    `limit`/`skip` paginan (los más recientes primero); `todos=True` devuelve todo.
    """
    params: dict = {"q": f"%{query_text}%"}
    if not todos:
        params.update({"limit": limit, "skip": skip})
    where = """(d.activo = TRUE)
               AND (d.nombre_documento ILIKE :q OR d.nombre_original ILIKE :q)"""
    if id_municipio:
        where += " AND d.id_municipio = :m"
        params["m"] = id_municipio
    if origen == "edan":
        where += " AND d.id_evento_rida IS NULL"
    elif origen == "rida":
        where += " AND d.id_evento_rida IS NOT NULL"

    # cantidad → paginación; todos=True → sin LIMIT/OFFSET
    page = "" if todos else " LIMIT :limit OFFSET :skip"

    return _rows(db, _SELECT_DOCS + f"""
        WHERE {where}
        ORDER BY d.fecha_documento DESC NULLS LAST, d.fecha_subida DESC
        {page}
    """, params)


def list_documentos_filtrados(
    db: Session,
    origen: str | None = None,
    id_edan: int | None = None,
    id_evento_rida: int | None = None,
    id_departamento: int | None = None,
    id_provincia: int | None = None,
    id_municipio: int | None = None,
    id_tipo_documento: int | None = None,
    fecha_desde: str | None = None,
    fecha_hasta: str | None = None,
    nombre_documento_like: str | None = None,
    limit: int = 50,
    skip: int = 0,
    todos: bool = False,
):
    """Lista documentos con filtros por metadata estructurada.

    'origen' es el filtro EDAN/RIDA. Se deriva de id_evento_rida, asi que
    se puede combinar con cualquier otro filtro: origen='rida' +
    id_municipio=1 devuelve solo los documentos RIDA de ese municipio.

    `limit`/`skip` paginan (los más recientes primero); `todos=True` devuelve todo.
    """
    conds = ["d.activo = TRUE"]
    params: dict = {}
    if not todos:
        params = {"limit": limit, "skip": skip}

    if origen == "edan":
        conds.append("d.id_evento_rida IS NULL")
    elif origen == "rida":
        conds.append("d.id_evento_rida IS NOT NULL")
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
    # cantidad → paginación; todos=True → sin LIMIT/OFFSET
    page = "" if todos else " LIMIT :limit OFFSET :skip"
    rows = _rows(db, _SELECT_DOCS + f"""
        WHERE {where}
        ORDER BY d.fecha_documento DESC NULLS LAST, d.fecha_subida DESC
        {page}
    """, params)
    total = _row(db, f"""
        SELECT COUNT(*) AS c
        FROM repositorio.documentos d
        JOIN repositorio.tipo_documento t ON t.id_tipo_documento = d.id_tipo_documento
        WHERE {where}
    """, params)["c"]
    return rows, total
