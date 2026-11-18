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
    LEFT JOIN edan.edan ee2 ON ee2.id_edan = d.id_edan
    LEFT JOIN rida.evento_rida ev2 ON ev2.id_evento_rida = d.id_evento_rida
"""

# Mismo FROM del listado, para el COUNT(*) del total sin paginar.
_FROM_DOCS = """
    FROM repositorio.documentos d
    JOIN repositorio.tipo_documento t ON t.id_tipo_documento = d.id_tipo_documento
    LEFT JOIN edan.edan ee2 ON ee2.id_edan = d.id_edan
    LEFT JOIN rida.evento_rida ev2 ON ev2.id_evento_rida = d.id_evento_rida
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
    codigo_grupo: str | None = None,
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
    edan_solo: bool = False,
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
    if codigo_grupo:
        # Codigo VISIBLE del grupo, respetando la regla 'id_edan gana':
        # cada codigo empareja SOLO documentos de su propio origen
        # (codigo_edan->EDAN, evento.codigo->RIDA, codigo_documento->PRECEDENTE),
        # ignorando codigos heredados del EDAN padre. Sin distinguir mayusculas.
        _origen_expr_up = f"UPPER({_ORIGEN_SQL.split(' AS ')[0]})"
        conds.append(
            f"(({_origen_expr_up} = 'EDAN' AND UPPER(ee2.codigo_edan) = UPPER(:codigo_grupo)) "
            f"OR ({_origen_expr_up} = 'RIDA' AND UPPER(ev2.codigo) = UPPER(:codigo_grupo)) "
            "OR UPPER(d.codigo_documento) = UPPER(:codigo_grupo))")
        params["codigo_grupo"] = codigo_grupo.strip()
    if id_edan is not None:
        conds.append("d.id_edan = :id_edan")
        params["id_edan"] = id_edan
        if edan_solo:
            # 'id_edan gana': el filtro por EDAN solo empareja documentos de
            # origen EDAN; los RIDA que heredan este id_edan quedan fuera
            # (para verlos usar GET /edan/{id_edan}/documentos).
            _origen_expr = _ORIGEN_SQL.split(" AS ")[0]
            conds.append(f"UPPER({_origen_expr}) = 'EDAN'")
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
    codigo_grupo: str | None = None,
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
    los mismos filtros. `id_edan` usa la regla 'id_edan gana': solo empareja
    documentos de origen EDAN (los RIDA que heredan el id se excluyen; ver
    GET /edan/{id_edan}/documentos para la vista completa).
    """
    where, params = _aplicar_filtros_documentos(
        origen=origen,
        codigo_documento=codigo_documento,
        codigo_grupo=codigo_grupo,
        edan_solo=True,
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
    codigo: str,
    limit: int = 50,
    skip: int = 0,
    todos: bool = False,
):
    """Documentos activos de un grupo por su CODIGO VISIBLE.

    Acepta cualquiera de los tres: `codigo_edan` (EDAN, p. ej.
    070101/2026/003), `rida.evento_rida.codigo` (RIDA, p. ej. 070101/2026/003-R)
    o `codigo_documento` (DOC_PRECEDENTE). Comparacion sin distinguir
    mayusculas. Devuelve (rows, total) reciente primero, misma forma que el
    listado general.
    """
    cod = (codigo or "").strip()
    if not cod:
        return [], 0
    return list_documentos_filtrados(
        db, codigo_grupo=cod, limit=limit, skip=skip, todos=todos,
    )


_GRUPO_KEY_SQL = """
    CASE
        WHEN COALESCE(d.origen, CASE WHEN d.id_evento_rida IS NULL THEN 'EDAN' ELSE 'RIDA' END) = 'DOC_PRECEDENTE'
            THEN COALESCE(d.codigo_documento, 'DOC-' || d.id_documento::text)
        WHEN COALESCE(d.origen, CASE WHEN d.id_evento_rida IS NULL THEN 'EDAN' ELSE 'RIDA' END) = 'RIDA'
            THEN 'EV-' || COALESCE(d.id_evento_rida::text, d.id_documento::text)
        ELSE 'ED-' || COALESCE(d.id_edan::text, d.id_documento::text)
    END
"""


def list_documentos_grupos(
    db: Session,
    origen: str | None = None,
    codigo_documento: str | None = None,
    codigo_grupo: str | None = None,
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
    """Listado AGRUPADO del repositorio: un grupo por expediente/entidad padre.

    Regla de agrupacion (unica fuente de verdad):
      - origen RIDA           -> grupo por id_evento_rida (aunque herede id_edan:
                                 se mantiene como RIDA, no se mezcla con el EDAN)
      - origen EDAN           -> grupo por id_edan
      - origen DOC_PRECEDENTE -> grupo por codigo_documento (si faltara, el
                                 propio documento forma su grupo)

    Identidad visible: `clave` es el CODIGO REAL
    del grupo: `edan.edan.codigo_edan` (p. ej. 070101/2026/003) para EDAN,
    `rida.evento_rida.codigo` (p. ej. 070101/2026/003-R) para RIDA y el mismo
    `codigo_documento` para DOC_PRECEDENTE. Solo si el padre careciera de
    codigo se usa el fallback tecnico ED-<id>/EV-<id>/DOC-<id_documento>.

    Copias EXACTAS por hash (sin apis nuevas): `documentos_compartidos` y
    `comparte_con` (grupos hermanos referenciados por su codigo real, con los
    documentos comunes). Se calcula contra todos los docs activos,
    independiente de filtros/paginacion; copias del mismo grupo no cuentan.

    `total` = numero de GRUPOS sin paginar con los mismos filtros.
    """
    where, params = _aplicar_filtros_documentos(
        origen=origen,
        codigo_documento=codigo_documento,
        codigo_grupo=codigo_grupo,
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
        edan_solo=True,
    )

    tipo_expr = (
        "COALESCE(d.origen, CASE WHEN d.id_evento_rida IS NULL THEN 'EDAN' ELSE 'RIDA' END)"
    )

    joins_padres = """
            LEFT JOIN edan.edan ee2 ON ee2.id_edan = d.id_edan
            LEFT JOIN rida.evento_rida ev2 ON ev2.id_evento_rida = d.id_evento_rida"""

    codigo_fila = f"""CASE {tipo_expr}
                WHEN 'EDAN' THEN COALESCE(ee2.codigo_edan, 'ED-' || d.id_edan::text)
                WHEN 'RIDA' THEN COALESCE(ev2.codigo, 'EV-' || d.id_evento_rida::text)
                ELSE COALESCE(d.codigo_documento, 'DOC-' || d.id_documento::text)
            END"""

    grupo_inner = f"""
        SELECT
            {tipo_expr} AS tipo,
            {_GRUPO_KEY_SQL} AS clave_tecnica,
            CASE {tipo_expr}
                WHEN 'EDAN' THEN COALESCE(min(ee2.codigo_edan),
                                          'ED-' || min(d.id_edan)::text)
                WHEN 'RIDA' THEN COALESCE(min(ev2.codigo),
                                          'EV-' || min(d.id_evento_rida)::text)
                ELSE min(COALESCE(d.codigo_documento,
                                  'DOC-' || d.id_documento::text))
            END AS clave,
            min(d.id_edan) AS id_edan,
            min(d.id_evento_rida) AS id_evento_rida,
            CASE WHEN {tipo_expr} = 'DOC_PRECEDENTE'
                 THEN min(COALESCE(d.codigo_documento,
                                   'DOC-' || d.id_documento::text))
            END AS codigo_documento,
            min(d.id_departamento) AS id_departamento,
            min(d.id_provincia) AS id_provincia,
            min(d.id_municipio) AS id_municipio,
            count(*)::int AS total_documentos,
            max(d.fecha_documento) AS fecha_documento_max,
            max(d.fecha_subida) AS fecha_subida_max
        FROM repositorio.documentos d
        JOIN repositorio.tipo_documento t ON t.id_tipo_documento = d.id_tipo_documento
        {joins_padres}
        WHERE {where}
        GROUP BY {tipo_expr}, {_GRUPO_KEY_SQL}
    """

    hash_ctes = f"""
        WITH docs AS (
            SELECT d.id_documento, d.hash_sha256, d.nombre_documento,
                   {tipo_expr} AS tipo,
                   {_GRUPO_KEY_SQL} AS clave_tecnica,
                   {codigo_fila} AS clave
              FROM repositorio.documentos d
              {joins_padres}
             WHERE d.activo = TRUE AND d.hash_sha256 IS NOT NULL
        ), comp AS (
            SELECT a.clave_tecnica AS clave,
                   count(DISTINCT a.id_documento)::int AS documentos_compartidos
              FROM docs a
             WHERE EXISTS (
                 SELECT 1 FROM docs b
                  WHERE b.hash_sha256 = a.hash_sha256
                    AND b.clave_tecnica <> a.clave_tecnica)
             GROUP BY a.clave_tecnica
        ), por_dest AS (
            SELECT a.clave_tecnica AS clave,
                   b.clave_tecnica AS dest_tecnica,
                   min(b.tipo) AS dest_tipo,
                   min(b.clave) AS dest_clave,
                   count(DISTINCT b.id_documento)::int AS documentos_comunes,
                   jsonb_agg(DISTINCT jsonb_build_object(
                       'id_documento', b.id_documento,
                       'nombre_documento', b.nombre_documento,
                       'hash_sha256', left(b.hash_sha256, 16))) AS documentos
              FROM docs a
              JOIN docs b
                ON a.hash_sha256 = b.hash_sha256
               AND a.clave_tecnica <> b.clave_tecnica
             GROUP BY a.clave_tecnica, b.clave_tecnica
        ), comp_con AS (
            SELECT clave,
                   jsonb_agg(jsonb_build_object(
                       'tipo', dest_tipo,
                       'clave', dest_clave,
                       'documentos_comunes', documentos_comunes,
                       'documentos', documentos)
                       ORDER BY documentos_comunes DESC) AS comparte_con
              FROM por_dest GROUP BY clave
        )
    """

    total = _row(
        db, f"SELECT COUNT(*) AS total FROM ({grupo_inner}) g", params
    )["total"]

    q_page = "" if todos else " LIMIT :limit OFFSET :skip"
    page_params = {} if todos else {"limit": limit, "skip": skip}

    rows = _rows(db, f"""
        {hash_ctes}
        SELECT g.tipo, g.clave,
               g.id_edan, g.id_evento_rida, g.codigo_documento,
               g.id_departamento, g.id_provincia, g.id_municipio,
               g.total_documentos, g.fecha_documento_max, g.fecha_subida_max,
               COALESCE(c.documentos_compartidos, 0) AS documentos_compartidos,
               COALESCE(k.comparte_con, '[]'::jsonb) AS comparte_con
          FROM ({grupo_inner}) g
          LEFT JOIN comp c ON c.clave = g.clave_tecnica
          LEFT JOIN comp_con k ON k.clave = g.clave_tecnica
         ORDER BY g.fecha_documento_max DESC NULLS LAST, g.fecha_subida_max DESC
         {q_page}
    """, {**params, **page_params})
    return rows, total


_TIPO_EXPR = (
    "COALESCE(d.origen, CASE WHEN d.id_evento_rida IS NULL THEN 'EDAN' ELSE 'RIDA' END)"
)

_CODIGO_REAL_FILA = f"""CASE {_TIPO_EXPR}
        WHEN 'EDAN' THEN COALESCE(ee2.codigo_edan, 'ED-' || d.id_edan::text)
        WHEN 'RIDA' THEN COALESCE(ev2.codigo, 'EV-' || d.id_evento_rida::text)
        ELSE COALESCE(d.codigo_documento, 'DOC-' || d.id_documento::text)
    END"""


def repositorio_todo(
    db: Session,
    origen: str | None = None,
    codigo_documento: str | None = None,
    codigo_grupo: str | None = None,
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
    limite_documentos: int = 500,
):
    """Todo el repositorio en UNA respuesta, por secciones de origen.

    data = {"EDAN": {...}, "RIDA": {...}, "DOC_PRECEDENTE": {...}}. Cada seccion
    contiene `grupos` (misma fila que modo=agrupado: clave=codigo real,
    total_documentos, fechas, documentos_compartidos, comparte_con) con los
    `documentos` de cada grupo anidados. Obedece todos los filtros (geografia,
    fechas, tipo, q, etc.). `limite_documentos` (default 500, duro) acota el
    listado anidado por payload; si recorta, la seccion marca `truncateda`.
    Reglas de negocio identicas al agrupado: RIDA no se mezcla con el EDAN
    heredado; DOC_PRECEDENTE agrupa por codigo_documento tal cual.
    """
    groups, _ = list_documentos_grupos(
        db, origen=origen, codigo_documento=codigo_documento,
        codigo_grupo=codigo_grupo, id_edan=id_edan, id_evento_rida=id_evento_rida,
        id_departamento=id_departamento, id_provincia=id_provincia,
        id_municipio=id_municipio, id_tipo_documento=id_tipo_documento,
        id_usuario_subio=id_usuario_subio, fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta, nombre_documento_like=nombre_documento_like,
        tiene_firma_digital=tiene_firma_digital, include_inactive=include_inactive,
        todos=True,
    )

    where, params = _aplicar_filtros_documentos(
        origen=origen,
        codigo_documento=codigo_documento,
        codigo_grupo=codigo_grupo,
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
        edan_solo=True,
    )

    rows = _rows(db, f"""
        SELECT d.id_documento, d.id_edan, d.id_evento_rida, d.codigo_documento,
               {_TIPO_EXPR} AS tipo,
               {_CODIGO_REAL_FILA} AS clave,
               d.id_tipo_documento, t.codigo AS tipo_codigo, t.nombre AS tipo_nombre,
               d.nombre_documento, d.fecha_documento, d.fecha_subida,
               d.id_usuario_subio, d.tamano_bytes, d.hash_sha256,
               d.tiene_firma_digital, d.activo,
               d.id_departamento, d.id_provincia, d.id_municipio,
               d.observaciones
        FROM repositorio.documentos d
        JOIN repositorio.tipo_documento t ON t.id_tipo_documento = d.id_tipo_documento
        LEFT JOIN edan.edan ee2 ON ee2.id_edan = d.id_edan
        LEFT JOIN rida.evento_rida ev2 ON ev2.id_evento_rida = d.id_evento_rida
        WHERE {where}
        ORDER BY 6, 7, d.fecha_documento DESC NULLS LAST, d.fecha_subida DESC
        LIMIT :limite_documentos
    """, {**params, "limite_documentos": limite_documentos})

    docs_map: dict = {}
    for r in rows:
        docs_map.setdefault((r["tipo"], r["clave"]), []).append(r)

    secciones = {}
    for tipo in ("EDAN", "RIDA", "DOC_PRECEDENTE"):
        grupos = []
        total_docs = 0
        listados = 0
        for g in groups:
            if g["tipo"] != tipo:
                continue
            doc_hijos = docs_map.get((g["tipo"], g["clave"]), [])
            total_docs += g["total_documentos"]
            listados += len(doc_hijos)
            grupos.append({**g, "documentos": doc_hijos})
        secciones[tipo] = {
            "total_grupos": len(grupos),
            "total_documentos": total_docs,
            "documentos_listados": listados,
            "truncateda": listados < total_docs,
            "grupos": grupos,
        }

    total_general = sum(s["total_documentos"] for s in secciones.values())
    return secciones, total_general
