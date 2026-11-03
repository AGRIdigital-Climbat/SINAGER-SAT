"""
SERVICIO SINB - Funciones completas para catálogos, observaciones, pronósticos, validación y reportes
"""
from datetime import date, datetime, timedelta
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from sqlalchemy.exc import IntegrityError
from uuid import UUID

from ..pagination import pagina_limit_offset


# ============================================================================
# UTILIDADES DE BASE DE DATOS
# ============================================================================

def _rows(db: Session, query: str, params: dict = None):
    """Ejecutar query y retornar filas como lista de dicts."""
    params = params or {}
    result = db.execute(text(query), params)
    return [dict(row._mapping) for row in result]


def _row(db: Session, query: str, params: dict = None):
    """Ejecutar query y retornar primera fila como dict."""
    params = params or {}
    result = db.execute(text(query), params)
    row = result.mappings().first()
    return dict(row) if row else None


def _execute(db: Session, query: str, params: dict = None):
    """Ejecutar query sin retorno."""
    params = params or {}
    result = db.execute(text(query), params)
    db.commit()
    return result

def _update_params(id_: UUID, data: dict, *keys):
    """Params de UPDATE: None en los campos que el cliente no envió (los PUT son parciales).

    Sin esto, text() lanza InvalidRequestError porque cada :bind debe venir en el dict.
    """
    params = {k: data.get(k) for k in keys}
    params["id"] = id_
    return params



# ============================================================================
# BORRADO FÍSICO + CONTROL DE BORRADOS (v2.43.0)
# ============================================================================

# Referencias que impiden borrar una fila: FK RESTRICT reales (grafo de sinb) más
# los datos propios que no deben desaparecer por arrastre (fotos, índices).
_USOS_CATALOGO = {
    "grupo": [
        ("indicador natural", "SELECT count(*) AS n FROM sinb.indicador_natural WHERE id_grupo = :id"),
        ("comportamiento", "SELECT count(*) AS n FROM sinb.comportamiento WHERE id_grupo = :id"),
        ("significado", "SELECT count(*) AS n FROM sinb.significado WHERE id_grupo = :id"),
        ("pronóstico estacional", "SELECT count(*) AS n FROM sinb.pronostico_largo WHERE id_grupo = :id"),
    ],
    "indicador_natural": [
        ("característica", "SELECT count(*) AS n FROM sinb.caracteristica WHERE id_indicador_natural = :id"),
        ("foto", "SELECT count(*) AS n FROM sinb.indicador_foto WHERE id_indicador_natural = :id"),
        ("índice de observador", "SELECT count(*) AS n FROM sinb.observador_indice WHERE id_indicador_natural = :id"),
        ("pronóstico estacional", "SELECT count(*) AS n FROM sinb.pronostico_largo WHERE id_indicador_natural = :id"),
    ],
    "caracteristica": [
        ("comportamiento", "SELECT count(*) AS n FROM sinb.comportamiento WHERE id_caracteristica = :id"),
        ("pronóstico estacional", "SELECT count(*) AS n FROM sinb.pronostico_largo WHERE id_caracteristica = :id"),
    ],
    "comportamiento": [
        ("significado", "SELECT count(*) AS n FROM sinb.significado WHERE id_comportamiento = :id"),
        ("pronóstico estacional", "SELECT count(*) AS n FROM sinb.pronostico_largo WHERE id_comportamiento = :id"),
    ],
    "categoria_pronostico": [
        ("escenario", "SELECT count(*) AS n FROM sinb.escenario WHERE id_categoria = :id"),
        ("bloque de pronóstico", "SELECT count(*) AS n FROM sinb.pronostico_largo_item WHERE id_categoria = :id"),
        ("pronóstico temporal", "SELECT count(*) AS n FROM sinb.pronostico_corto WHERE id_categoria = :id"),
        ("aviso", "SELECT count(*) AS n FROM sinb.avisos WHERE id_categoria = :id"),
    ],
    "escenario": [
        ("escenario asignado a un pronóstico",
         "SELECT count(*) AS n FROM sinb.escenario_estacional WHERE id_escenario = :id"),
    ],
    "significado": [],
    "zona_geografica": [],
    "avisos": [],
    "pronostico_largo": [],
    "pronostico_corto": [],
    "indicador_foto": [],
    "observador_indice": [],
}


def _usos_catalogo(db: Session, tabla: str, id_: UUID) -> dict:
    """Cuenta los datos que referencian a una fila antes de borrarla físicamente."""
    usos = {}
    for etiqueta, sql in _USOS_CATALOGO.get(tabla, []):
        n = _row(db, sql, {"id": id_})["n"]
        if n:
            usos[etiqueta] = n
    return usos


def _registro_borrado_sql():
    return text("""
        INSERT INTO sinb.registro_borrado (tabla, id_registro, codigo, id_off, id_usuario)
        VALUES (:tabla, :id_registro, :codigo, :id_off, :id_usuario)
        ON CONFLICT (tabla, id_registro) DO UPDATE
            SET borrado_en = now(), codigo = EXCLUDED.codigo, id_off = EXCLUDED.id_off
    """)


def _etiqueta_borrada(fila: dict):
    """Identificador legible del tombstone: código, nombre o el texto que lo describa."""
    for clave in ("codigo", "nombre", "caracteristica", "comportamiento", "significado", "path_foto"):
        valor = fila.get(clave)
        if valor:
            return str(valor)[:80]
    return None


def _registrar_borrado(db: Session, tabla: str, fila: dict, id_usuario: int | None = None):
    """Escribe el tombstone (sin comitear: va en la misma transacción del DELETE)."""
    db.execute(_registro_borrado_sql(), {
        "tabla": tabla,
        "id_registro": fila["id"],
        "codigo": _etiqueta_borrada(fila),
        "id_off": fila.get("id_pe_off") or fila.get("id_pt_off") or fila.get("id_aviso_off"),
        "id_usuario": id_usuario,
    })


def _borrar_fisico(db: Session, tabla: str, id_: UUID, id_usuario: int | None = None,
                   etiqueta: str = "el registro"):
    """
    Borrado físico de una fila con dos protecciones:
      - si otros datos la referencian, 409 con el detalle (nada se destruye ni queda huérfano)
      - deja su tombstone en sinb.registro_borrado para que la app offline la retire

    Un id que no existe no borra nada y no cambia el comportamiento previo (200).
    Devuelve la fila eliminada o None.
    """
    fila = _row(db, f"SELECT * FROM sinb.{tabla} WHERE id = :id", {"id": id_})
    if not fila:
        return None

    usos = _usos_catalogo(db, tabla, id_)
    if usos:
        detalle = ", ".join(f"{k}: {n}" for k, n in usos.items())
        raise HTTPException(
            status_code=409,
            detail=f"No se puede eliminar {etiqueta} porque está en uso ({detalle}). "
                   f"Retírelo con estado INACTIVO o elimine primero lo que lo referencia.",
        )

    _registrar_borrado(db, tabla, fila, id_usuario)
    db.execute(text(f"DELETE FROM sinb.{tabla} WHERE id = :id"), {"id": id_})
    db.commit()
    return fila


def get_borrados(db: Session, desde: datetime | None = None, tabla: str | None = None,
                 limit: int | None = None, skip: int = 0, todos: bool = False):
    """Borrados físicos registrados desde una fecha, para sincronizar la app offline.

    Devuelve (filas, total). Por defecto devuelve todo (la app offline necesita el
    conjunto completo); `limit`/`skip` sólo paginan si se piden y `todos=true`
    fuerza sin paginar. `total` es SIEMPRE el total sin paginar, con los mismos filtros.
    """
    where = ["borrado_en >= COALESCE(:desde, borrado_en)"]
    params: dict = {"desde": desde}
    if tabla:
        where.append("tabla = :tabla")
        params["tabla"] = tabla
    where_sql = " AND ".join(where)

    total = _row(db, f"""
        SELECT COUNT(*) AS total FROM sinb.registro_borrado WHERE {where_sql}
    """, params)["total"]

    page, page_params = pagina_limit_offset(limit, skip, todos)
    rows = _rows(db, f"""
        SELECT tabla, id_registro, codigo, id_off, borrado_en, id_usuario
        FROM sinb.registro_borrado
        WHERE {where_sql}
        ORDER BY borrado_en DESC
        {page}
    """, {**params, **page_params})
    return rows, total


def _serialize(obj):
    """Serializar objeto SQLAlchemy a dict, manejando datetime y UUID."""
    import json
    def default(o):
        if isinstance(o, (datetime, date)):
            return o.isoformat()
        if isinstance(o, UUID):
            return str(o)
        if hasattr(o, '__dict__'):
            return {k: default(v) for k, v in o.__dict__.items() if not k.startswith('_')}
        return o
    
    if isinstance(obj, list):
        return [dict(item) if hasattr(item, '_mapping') else default(item) for item in obj]
    if hasattr(obj, '_mapping'):
        return dict(obj._mapping)
    return default(obj)


def _now():
    """Retornar datetime actual."""
    return datetime.now()

# ============================================================================
# CATÁLOGOS BIOCURALTURALES
# ============================================================================

def _crear_unico(db: Session, sql: str, params: dict, etiqueta: str):
    """
    Alta de catálogo con clave única (codigo/nombre): un duplicado debe responder
    409, no 500. Sin esto, el handler global de api/main.py convierte la
    IntegrityError en "Error interno del servidor".
    """
    try:
        result = db.execute(text(sql), params)
        fila = dict(result.mappings().first())
        db.commit()
        return fila
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"{etiqueta} ya existe")


def get_grupos(db: Session):
    """Obtener todos los grupos activos."""
    rows = _rows(db, "SELECT * FROM sinb.grupo WHERE estado = 'ACTIVO' ORDER BY codigo")
    return [dict(row) for row in rows]


def get_grupo(db: Session, id: UUID):
    """Obtener grupo por ID."""
    row = _row(db, "SELECT * FROM sinb.grupo WHERE id = :id AND estado = 'ACTIVO'", {"id": id})
    return dict(row) if row else None


def create_grupo(db: Session, data: dict):
    """Crear nuevo grupo (codigo único: duplicado -> 409)."""
    return _crear_unico(db, """
        INSERT INTO sinb.grupo (codigo, nombre, descripcion, estado)
        VALUES (:codigo, :nombre, :descripcion, 'ACTIVO')
        RETURNING *
    """, data, f"El código de grupo '{data.get('codigo')}'")


def update_grupo(db: Session, id: UUID, data: dict):
    """Actualizar grupo."""
    params = _update_params(id, data, "codigo", "nombre", "descripcion", "estado")
    result = db.execute(text("""
        UPDATE sinb.grupo SET
            codigo = COALESCE(:codigo, codigo),
            nombre = COALESCE(:nombre, nombre),
            descripcion = COALESCE(:descripcion, descripcion),
            estado = COALESCE(:estado, estado),
            actualizado_en = now()
        WHERE id = :id
        RETURNING *
    """), params)
    db.commit()
    return dict(result.mappings().first()) if result.rowcount > 0 else None


def delete_grupo(db: Session, id: UUID, id_usuario: int | None = None):
    """Eliminar grupo definitivamente (borrado físico + registro de borrado)."""
    return _borrar_fisico(db, "grupo", id, id_usuario, "el grupo")


def get_indicadores_naturales(db: Session, id_grupo: UUID | None = None,
                               codigo: str | None = None,
                               nombre_cientifico: str | None = None,
                               nombre_comun: str | None = None):
    """Obtener indicadores naturales con filtros."""
    where = ["i.estado = 'ACTIVO'"]
    params = {}
    if id_grupo:
        where.append("i.id_grupo = :id_grupo")
        params["id_grupo"] = id_grupo
    if codigo:
        where.append("i.codigo ILIKE :codigo")
        params["codigo"] = f"%{codigo}%"
    if nombre_cientifico:
        where.append("i.nombre_cientifico ILIKE :nombre_cientifico")
        params["nombre_cientifico"] = f"%{nombre_cientifico}%"
    if nombre_comun:
        where.append("i.nombre_comun ILIKE :nombre_comun")
        params["nombre_comun"] = f"%{nombre_comun}%"
    
    query = f"""
        SELECT i.*, g.nombre as grupo_nombre
        FROM sinb.indicador_natural i
        LEFT JOIN sinb.grupo g ON g.id = i.id_grupo
        WHERE {' AND '.join(where)}
        ORDER BY i.nombre_cientifico
    """
    rows = _rows(db, query, params)
    return [dict(row) for row in rows]


def get_indicador_natural(db: Session, id: UUID):
    """Obtener indicador por ID con grupo y fotos anidadas."""
    row = _row(db, """
        SELECT i.*, 
               jsonb_build_object(
                   'id', g.id,
                   'codigo', g.codigo,
                   'nombre', g.nombre,
                   'descripcion', g.descripcion
               ) as grupo
        FROM sinb.indicador_natural i
        LEFT JOIN sinb.grupo g ON g.id = i.id_grupo
        WHERE i.id = :id AND i.estado = 'ACTIVO'
    """, {"id": id})
    if not row:
        return None
    data = dict(row)
    data["fotos"] = get_fotos_indicador(db, id)[0]
    return data


def create_indicador_natural(db: Session, data: dict):
    """Crear indicador natural (codigo único, también dentro del grupo: duplicado -> 409)."""
    return _crear_unico(db, """
        INSERT INTO sinb.indicador_natural 
        (codigo, nombre_cientifico, nombre_comun, id_grupo, descripcion, requiere_consentimiento, estado)
        VALUES (:codigo, :nombre_cientifico, :nombre_comun, :id_grupo, :descripcion, :requiere_consentimiento, 'ACTIVO')
        RETURNING *
    """, data, f"El código de indicador '{data.get('codigo')}'")


def update_indicador_natural(db: Session, id: UUID, data: dict):
    """Actualizar indicador."""
    params = _update_params(id, data, "codigo", "nombre_cientifico", "nombre_comun", "id_grupo", "descripcion", "requiere_consentimiento", "estado")
    result = db.execute(text("""
        UPDATE sinb.indicador_natural SET
            codigo = COALESCE(:codigo, codigo),
            nombre_cientifico = COALESCE(:nombre_cientifico, nombre_cientifico),
            nombre_comun = COALESCE(:nombre_comun, nombre_comun),
            id_grupo = COALESCE(:id_grupo, id_grupo),
            descripcion = COALESCE(:descripcion, descripcion),
            requiere_consentimiento = COALESCE(:requiere_consentimiento, requiere_consentimiento),
            estado = COALESCE(:estado, estado),
            actualizado_en = now()
        WHERE id = :id
        RETURNING *
    """), params)
    db.commit()
    return dict(result.mappings().first()) if result.rowcount > 0 else None


def delete_indicador_natural(db: Session, id: UUID, id_usuario: int | None = None):
    """Eliminar indicador natural definitivamente (bloqueado si tiene fotos, índices o pronósticos)."""
    return _borrar_fisico(db, "indicador_natural", id, id_usuario, "el indicador natural")


def get_caracteristicas(db: Session, id_indicador_natural: UUID | None = None):
    """Obtener características con indicador anidado."""
    where = ["c.estado = 'ACTIVO'"]
    params = {}
    if id_indicador_natural:
        where.append("c.id_indicador_natural = :id_indicador_natural")
        params["id_indicador_natural"] = id_indicador_natural
    
    query = f"""
        SELECT c.*, 
               jsonb_build_object(
                   'id', i.id,
                   'nombre_cientifico', i.nombre_cientifico,
                   'nombre_comun', i.nombre_comun,
                   'codigo', i.codigo
               ) as indicador
        FROM sinb.caracteristica c
        JOIN sinb.indicador_natural i ON i.id = c.id_indicador_natural
        WHERE {' AND '.join(where)}
        ORDER BY i.nombre_cientifico, c.caracteristica
    """
    rows = _rows(db, query, params)
    return _serialize(rows)


def create_caracteristica(db: Session, data: dict):
    """Crear característica."""
    result = db.execute(text("""
        INSERT INTO sinb.caracteristica (id_indicador_natural, caracteristica, estado)
        VALUES (:id_indicador_natural, :caracteristica, 'ACTIVO')
        RETURNING *
    """), data)
    db.commit()
    return dict(result.mappings().first())


def update_caracteristica(db: Session, id: UUID, data: dict):
    """Actualizar característica."""
    params = _update_params(id, data, "id_indicador_natural", "caracteristica", "estado")
    result = db.execute(text("""
        UPDATE sinb.caracteristica SET
            id_indicador_natural = COALESCE(:id_indicador_natural, id_indicador_natural),
            caracteristica = COALESCE(:caracteristica, caracteristica),
            estado = COALESCE(:estado, estado)
        WHERE id = :id
        RETURNING *
    """), params)
    db.commit()
    return dict(result.mappings().first()) if result.rowcount > 0 else None


def delete_caracteristica(db: Session, id: UUID, id_usuario: int | None = None):
    """Eliminar característica definitivamente."""
    return _borrar_fisico(db, "caracteristica", id, id_usuario, "la característica")


def get_comportamientos(db: Session, id_grupo: UUID | None = None,
                        id_caracteristica: UUID | None = None):
    """Obtener comportamientos con grupo y característica anidados."""
    where = ["c.estado = 'ACTIVO'"]
    params = {}
    if id_grupo:
        where.append("c.id_grupo = :id_grupo")
        params["id_grupo"] = id_grupo
    if id_caracteristica:
        where.append("c.id_caracteristica = :id_caracteristica")
        params["id_caracteristica"] = id_caracteristica
    
    query = f"""
        SELECT c.*, 
               jsonb_build_object(
                   'id', g.id,
                   'nombre', g.nombre,
                   'codigo', g.codigo
               ) as grupo,
               jsonb_build_object(
                   'id', car.id,
                   'caracteristica', car.caracteristica,
                   'id_indicador_natural', car.id_indicador_natural
               ) as caracteristica
        FROM sinb.comportamiento c
        JOIN sinb.caracteristica car ON car.id = c.id_caracteristica
        LEFT JOIN sinb.grupo g ON g.id = c.id_grupo
        WHERE {' AND '.join(where)}
        ORDER BY COALESCE(g.nombre, ''), COALESCE(car.caracteristica, ''), c.comportamiento
    """
    rows = _rows(db, query, params)
    return _serialize(rows)


def create_comportamiento(db: Session, data: dict):
    """Crear comportamiento."""
    result = db.execute(text("""
        INSERT INTO sinb.comportamiento (id_grupo, id_caracteristica, comportamiento, estado)
        VALUES (:id_grupo, :id_caracteristica, :comportamiento, 'ACTIVO')
        RETURNING *
    """), data)
    db.commit()
    return dict(result.mappings().first())


def update_comportamiento(db: Session, id: UUID, data: dict):
    """Actualizar comportamiento."""
    params = _update_params(id, data, "id_grupo", "id_caracteristica", "comportamiento", "estado")
    result = db.execute(text("""
        UPDATE sinb.comportamiento SET
            id_grupo = COALESCE(:id_grupo, id_grupo),
            id_caracteristica = COALESCE(:id_caracteristica, id_caracteristica),
            comportamiento = COALESCE(:comportamiento, comportamiento),
            estado = COALESCE(:estado, estado)
        WHERE id = :id
        RETURNING *
    """), params)
    db.commit()
    return dict(result.mappings().first()) if result.rowcount > 0 else None


def delete_comportamiento(db: Session, id: UUID, id_usuario: int | None = None):
    """Eliminar comportamiento definitivamente."""
    return _borrar_fisico(db, "comportamiento", id, id_usuario, "el comportamiento")


def get_significados(db: Session, id_grupo: UUID | None = None,
                     id_comportamiento: UUID | None = None,
                     categoria: str | None = None):
    """Obtener significados con grupo y comportamiento anidados."""
    where = ["s.estado = 'ACTIVO'"]
    params = {}
    if id_grupo:
        where.append("s.id_grupo = :id_grupo")
        params["id_grupo"] = id_grupo
    if id_comportamiento:
        where.append("s.id_comportamiento = :id_comportamiento")
        params["id_comportamiento"] = id_comportamiento
    if categoria:
        where.append("s.categoria = :categoria")
        params["categoria"] = categoria
    
    query = f"""
        SELECT s.*, 
               jsonb_build_object(
                   'id', g.id,
                   'nombre', g.nombre,
                   'codigo', g.codigo
               ) as grupo,
               jsonb_build_object(
                   'id', c.id,
                   'comportamiento', c.comportamiento,
                   'id_caracteristica', c.id_caracteristica
               ) as comportamiento
        FROM sinb.significado s
        JOIN sinb.comportamiento c ON c.id = s.id_comportamiento
        LEFT JOIN sinb.grupo g ON g.id = s.id_grupo
        WHERE {' AND '.join(where)}
        ORDER BY COALESCE(g.nombre, ''), COALESCE(c.comportamiento, ''), s.significado
    """
    rows = _rows(db, query, params)
    return _serialize(rows)


def create_significado(db: Session, data: dict):
    """Crear significado."""
    result = db.execute(text("""
        INSERT INTO sinb.significado (id_grupo, id_comportamiento, significado, categoria, estado)
        VALUES (:id_grupo, :id_comportamiento, :significado, :categoria, 'ACTIVO')
        RETURNING *
    """), data)
    db.commit()
    return dict(result.mappings().first())


def update_significado(db: Session, id: UUID, data: dict):
    """Actualizar significado."""
    params = _update_params(id, data, "id_grupo", "id_comportamiento", "significado", "categoria", "estado")
    result = db.execute(text("""
        UPDATE sinb.significado SET
            id_grupo = COALESCE(:id_grupo, id_grupo),
            id_comportamiento = COALESCE(:id_comportamiento, id_comportamiento),
            significado = COALESCE(:significado, significado),
            categoria = COALESCE(:categoria, categoria),
            estado = COALESCE(:estado, estado)
        WHERE id = :id
        RETURNING *
    """), params)
    db.commit()
    return dict(result.mappings().first()) if result.rowcount > 0 else None


def delete_significado(db: Session, id: UUID, id_usuario: int | None = None):
    """Eliminar significado definitivamente."""
    return _borrar_fisico(db, "significado", id, id_usuario, "el significado")


def get_zonas_geograficas(db: Session):
    """Obtener zonas geográficas."""
    rows = _rows(db, "SELECT * FROM sinb.zona_geografica WHERE estado = 'ACTIVO' ORDER BY nombre")
    return [dict(row) for row in rows]


def create_zona_geografica(db: Session, data: dict):
    """Crear zona geográfica (codigo único: duplicado -> 409)."""
    return _crear_unico(db, """
        INSERT INTO sinb.zona_geografica (codigo, nombre, descripcion, estado)
        VALUES (:codigo, :nombre, :descripcion, 'ACTIVO')
        RETURNING *
    """, data, f"El código de zona '{data.get('codigo')}'")


def update_zona_geografica(db: Session, id: UUID, data: dict):
    """Actualizar zona."""
    params = _update_params(id, data, "codigo", "nombre", "descripcion", "estado")
    result = db.execute(text("""
        UPDATE sinb.zona_geografica SET
            codigo = COALESCE(:codigo, codigo),
            nombre = COALESCE(:nombre, nombre),
            descripcion = COALESCE(:descripcion, descripcion),
            estado = COALESCE(:estado, estado)
        WHERE id = :id
        RETURNING *
    """), params)
    db.commit()
    return dict(result.mappings().first()) if result.rowcount > 0 else None


def delete_zona_geografica(db: Session, id: UUID, id_usuario: int | None = None):
    """Eliminar zona geográfica definitivamente."""
    return _borrar_fisico(db, "zona_geografica", id, id_usuario, "la zona geográfica")


def get_categorias_pronostico(db: Session, nombre: str | None = None):
    """Obtener categorías de pronóstico."""
    where = "WHERE estado = 'ACTIVO'"
    params = {}
    if nombre:
        where += " AND nombre ILIKE :nombre"
        params["nombre"] = f"%{nombre}%"
    rows = _rows(db, f"SELECT * FROM sinb.categoria_pronostico {where} ORDER BY nombre", params)
    return [dict(row) for row in rows]


def create_categoria_pronostico(db: Session, data: dict):
    """Crear categoría de pronóstico (nombre único: duplicado -> 409)."""
    return _crear_unico(db, """
        INSERT INTO sinb.categoria_pronostico (nombre, descripcion, estado)
        VALUES (:nombre, :descripcion, 'ACTIVO')
        RETURNING *
    """, data, f"La categoría '{data.get('nombre')}'")


def update_categoria_pronostico(db: Session, id: UUID, data: dict):
    """Actualizar categoría."""
    params = _update_params(id, data, "nombre", "descripcion", "estado")
    result = db.execute(text("""
        UPDATE sinb.categoria_pronostico SET
            nombre = COALESCE(:nombre, nombre),
            descripcion = COALESCE(:descripcion, descripcion),
            estado = COALESCE(:estado, estado)
        WHERE id = :id
        RETURNING *
    """), params)
    db.commit()
    return dict(result.mappings().first()) if result.rowcount > 0 else None


def delete_categoria_pronostico(db: Session, id: UUID, id_usuario: int | None = None):
    """Eliminar categoría de pronóstico definitivamente (bloqueada si tiene escenarios o pronósticos)."""
    return _borrar_fisico(db, "categoria_pronostico", id, id_usuario, "la categoría de pronóstico")


def get_escenarios(db: Session, id_categoria: UUID | None = None):
    """Obtener escenarios con categoría anidada."""
    where = ["e.estado = 'ACTIVO'"]
    params = {}
    if id_categoria:
        where.append("e.id_categoria = :id_categoria")
        params["id_categoria"] = id_categoria
    
    query = f"""
        SELECT e.*, 
               jsonb_build_object(
                   'id', c.id,
                   'nombre', c.nombre
               ) as categoria
        FROM sinb.escenario e
        LEFT JOIN sinb.categoria_pronostico c ON c.id = e.id_categoria
        WHERE {' AND '.join(where)}
        ORDER BY COALESCE(c.nombre, ''), e.nombre
    """
    rows = _rows(db, query, params)
    return _serialize(rows)


def create_escenario(db: Session, data: dict):
    """Crear escenario."""
    result = db.execute(text("""
        INSERT INTO sinb.escenario (id_categoria, nombre, descripcion, valor_min, valor_max, estado)
        VALUES (:id_categoria, :nombre, :descripcion, :valor_min, :valor_max, 'ACTIVO')
        RETURNING *
    """), data)
    db.commit()
    return dict(result.mappings().first())


def update_escenario(db: Session, id: UUID, data: dict):
    """Actualizar escenario."""
    params = {
        "id": id,
        "id_categoria": data.get("id_categoria"),
        "nombre": data.get("nombre"),
        "descripcion": data.get("descripcion"),
        "valor_min": data.get("valor_min"),
        "valor_max": data.get("valor_max"),
        "estado": data.get("estado"),
    }
    result = db.execute(text("""
        UPDATE sinb.escenario SET
            id_categoria = COALESCE(:id_categoria, id_categoria),
            nombre = COALESCE(:nombre, nombre),
            descripcion = COALESCE(:descripcion, descripcion),
            valor_min = COALESCE(:valor_min, valor_min),
            valor_max = COALESCE(:valor_max, valor_max),
            estado = COALESCE(:estado, estado)
        WHERE id = :id
        RETURNING *
    """), params)
    db.commit()
    return dict(result.mappings().first()) if result.rowcount > 0 else None


def delete_escenario(db: Session, id: UUID, id_usuario: int | None = None):
    """Eliminar escenario definitivamente."""
    return _borrar_fisico(db, "escenario", id, id_usuario, "el escenario")


# --- Catálogos: detalle por ID (mismo shape que los listados) ---

def get_caracteristica(db: Session, id: UUID):
    """Obtener característica por ID con su indicador natural anidado."""
    return _row(db, """
        SELECT c.*,
               jsonb_build_object(
                   'id', i.id,
                   'nombre_cientifico', i.nombre_cientifico,
                   'nombre_comun', i.nombre_comun,
                   'codigo', i.codigo
               ) as indicador
        FROM sinb.caracteristica c
        JOIN sinb.indicador_natural i ON i.id = c.id_indicador_natural
        WHERE c.id = :id AND c.estado = 'ACTIVO'
    """, {"id": id})


def get_comportamiento(db: Session, id: UUID):
    """Obtener comportamiento por ID con grupo y característica anidados."""
    return _row(db, """
        SELECT c.*,
               jsonb_build_object(
                   'id', g.id,
                   'nombre', g.nombre,
                   'codigo', g.codigo
               ) as grupo,
               jsonb_build_object(
                   'id', car.id,
                   'caracteristica', car.caracteristica,
                   'id_indicador_natural', car.id_indicador_natural
               ) as caracteristica
        FROM sinb.comportamiento c
        JOIN sinb.caracteristica car ON car.id = c.id_caracteristica
        LEFT JOIN sinb.grupo g ON g.id = c.id_grupo
        WHERE c.id = :id AND c.estado = 'ACTIVO'
    """, {"id": id})


def get_significado(db: Session, id: UUID):
    """Obtener significado por ID con grupo y comportamiento anidados."""
    return _row(db, """
        SELECT s.*,
               jsonb_build_object(
                   'id', g.id,
                   'nombre', g.nombre,
                   'codigo', g.codigo
               ) as grupo,
               jsonb_build_object(
                   'id', c.id,
                   'comportamiento', c.comportamiento,
                   'id_caracteristica', c.id_caracteristica
               ) as comportamiento
        FROM sinb.significado s
        JOIN sinb.comportamiento c ON c.id = s.id_comportamiento
        LEFT JOIN sinb.grupo g ON g.id = s.id_grupo
        WHERE s.id = :id AND s.estado = 'ACTIVO'
    """, {"id": id})


def get_zona_geografica(db: Session, id: UUID):
    """Obtener zona geográfica por ID."""
    return _row(db, "SELECT * FROM sinb.zona_geografica WHERE id = :id AND estado = 'ACTIVO'",
                {"id": id})


def get_categoria_pronostico(db: Session, id: UUID):
    """Obtener categoría de pronóstico por ID."""
    return _row(db, "SELECT * FROM sinb.categoria_pronostico WHERE id = :id AND estado = 'ACTIVO'",
                {"id": id})


def get_escenario(db: Session, id: UUID):
    """Obtener escenario por ID con su categoría anidada."""
    return _row(db, """
        SELECT e.*,
               jsonb_build_object(
                   'id', c.id,
                   'nombre', c.nombre
               ) as categoria
        FROM sinb.escenario e
        LEFT JOIN sinb.categoria_pronostico c ON c.id = e.id_categoria
        WHERE e.id = :id AND e.estado = 'ACTIVO'
    """, {"id": id})




# ============================================================================
# PRONÓSTICOS ESTACIONALES Y TEMPORALES
# ============================================================================

_LARGO_HEADER_SELECT = """
        SELECT pe.id, pe.codigo, pe.fecha_emision, pe.periodo_inicio, pe.periodo_fin, pe.estado,
               pe.id_usuario_subio, pe.id_municipio, pe.codigo_comunidad, pe.texto_observador,
               pe.id_grupo, pe.id_indicador_natural, pe.id_caracteristica, pe.id_comportamiento,
               pe.latitud::float, pe.longitud::float, pe.altitud::float,
               pe.notas, pe.id_pe_off, pe.es_ingesta,
               pe.creado_en, pe.actualizado_en,
               g.nombre as grupo_nombre,
               COALESCE(NULLIF(i.nombre_comun, ''), i.nombre_cientifico, i.codigo) as indicador_nombre,
               c.caracteristica as caracteristica_nombre, co.comportamiento as comportamiento_nombre,
               u.nombre as elaborador_nombre
        FROM sinb.pronostico_largo pe
        JOIN sinb.grupo g ON g.id = pe.id_grupo
        JOIN sinb.indicador_natural i ON i.id = pe.id_indicador_natural
        JOIN sinb.caracteristica c ON c.id = pe.id_caracteristica
        JOIN sinb.comportamiento co ON co.id = pe.id_comportamiento
        LEFT JOIN usuarios.usuario u ON u.id_usuario = pe.id_usuario_subio
    """


def _cadena_biocultural(row: dict) -> dict:
    """Construir la cadena biocultural (4 niveles) desde las columnas de la cabecera."""
    return {
        "id_grupo": row.get("id_grupo"),
        "grupo": row.get("grupo_nombre"),
        "id_indicador_natural": row.get("id_indicador_natural"),
        "indicador": row.get("indicador_nombre"),
        "id_caracteristica": row.get("id_caracteristica"),
        "caracteristica": row.get("caracteristica_nombre"),
        "id_comportamiento": row.get("id_comportamiento"),
        "comportamiento": row.get("comportamiento_nombre"),
    }


def _contexto(row: dict) -> dict:
    return {
        "latitud": row.get("latitud"),
        "longitud": row.get("longitud"),
        "altitud": row.get("altitud"),
        "notas": row.get("notas"),
    }


def _hijos_pronostico_largo(db: Session, ids: list[UUID]) -> dict:
    """Cargar bloques (con escenarios), recomendaciones y observadores para uno o más pronósticos."""
    hijos = {"pronosticos": {}, "recomendaciones": {}, "observadores": {}}
    if not ids:
        return hijos

    items = _rows(db, """
        SELECT i.id, i.id_pronostico_largo, i.id_categoria, i.metodo_validacion, i.id_regla_pronostica,
               i.ejecutar_en, i.fuente, i.orden, i.creado_en, i.id_item_off,
               cp.nombre as categoria_nombre
        FROM sinb.pronostico_largo_item i
        JOIN sinb.categoria_pronostico cp ON cp.id = i.id_categoria
        WHERE i.id_pronostico_largo = ANY(:ids)
        ORDER BY i.orden, i.creado_en
    """, {"ids": ids})

    item_ids = [it["id"] for it in items]
    escenarios: dict = {}
    if item_ids:
        for e in _rows(db, """
            SELECT ee.id_pronostico_largo_item, ee.confianza::text as confianza,
                   e.id as id_escenario, e.nombre, e.descripcion, ee.id_escenario_off
            FROM sinb.escenario_estacional ee
            JOIN sinb.escenario e ON e.id = ee.id_escenario
            WHERE ee.id_pronostico_largo_item = ANY(:item_ids)
            ORDER BY e.nombre
        """, {"item_ids": item_ids}):
            escenarios.setdefault(e["id_pronostico_largo_item"], []).append({
                "id_escenario": e["id_escenario"],
                "nombre": e["nombre"],
                "descripcion": e["descripcion"],
                "confianza": e["confianza"],
                "id_escenario_off": e["id_escenario_off"],
            })

    for it in items:
        it = dict(it)
        it["escenarios"] = escenarios.get(it["id"], [])
        hijos["pronosticos"].setdefault(it["id_pronostico_largo"], []).append(it)

    recs = _rows(db, """
        SELECT pr.id, pr.id_pronostico_largo, pr.id as id_recomendacion,
               pr.nombre, pr.id_recomendacion_off, pr.creado_en
        FROM sinb.pronostico_largo_recomendacion pr
        WHERE pr.id_pronostico_largo = ANY(:ids)
        ORDER BY pr.creado_en
    """, {"ids": ids})

    for r in recs:
        hijos["recomendaciones"].setdefault(r["id_pronostico_largo"], []).append(dict(r))

    for o in _rows(db, """
        SELECT po.id_pronostico_largo, po.id_usuario, u.nombre, u.usuario,
               po.fecha_asignacion, po.id_observador_off
        FROM sinb.pronostico_largo_observador po
        JOIN usuarios.usuario u ON u.id_usuario = po.id_usuario
        WHERE po.id_pronostico_largo = ANY(:ids)
        ORDER BY u.nombre
    """, {"ids": ids}):
        hijos["observadores"].setdefault(o["id_pronostico_largo"], []).append({
            "id_usuario": o["id_usuario"],
            "nombre": o["nombre"],
            "usuario": o["usuario"],
            "fecha_asignacion": o["fecha_asignacion"],
            "id_observador_off": o["id_observador_off"],
        })

    return hijos


def _armar_pronostico_largo(row: dict, hijos: dict) -> dict:
    """Ensamblar la respuesta anidada de un pronóstico largo."""
    observadores = hijos["observadores"].get(row["id"], [])
    return {
        **row,
        "cadena_biocultural": _cadena_biocultural(row),
        "contexto": _contexto(row),
        "pronosticos": hijos["pronosticos"].get(row["id"], []),
        "recomendaciones": hijos["recomendaciones"].get(row["id"], []),
        "observadores": observadores,
        "tipo_registro": "COLECTIVO" if len(observadores) > 1 else "INDIVIDUAL",
    }


def get_pronosticos_estacionales(db: Session, skip: int = 0, limit: int = 15,
                                  todos: bool = False,
                                  id_categoria: UUID | None = None,
                                  fecha_emision_desde: date | None = None,
                                  fecha_emision_hasta: date | None = None,
                                  estado: str | None = None,
                                  id_usuario_subio: int | None = None,
                                  id_departamento: int | None = None,
                                  id_municipio: int | None = None,
                                  codigo_comunidad: str | None = None):
    """Obtener pronósticos largo plazo con paginación, filtros y hijos anidados.

    `todos=True` devuelve el conjunto completo (sin `LIMIT`/`OFFSET`).
    """
    params = {"limit": limit, "skip": skip}
    where = ["pe.estado IN ('EMITIDO', 'ACEPTADO', 'RECHAZADO', 'EN_REVISION')"]

    if id_categoria:
        where.append("""EXISTS (SELECT 1 FROM sinb.pronostico_largo_item it
                                WHERE it.id_pronostico_largo = pe.id
                                  AND it.id_categoria = :id_categoria)""")
        params["id_categoria"] = id_categoria
    if fecha_emision_desde:
        where.append("pe.fecha_emision >= :fecha_emision_desde")
        params["fecha_emision_desde"] = fecha_emision_desde
    if fecha_emision_hasta:
        where.append("pe.fecha_emision <= :fecha_emision_hasta")
        params["fecha_emision_hasta"] = fecha_emision_hasta
    if estado:
        where.append("pe.estado = CAST(:estado AS sinb.estado_validacion)")
        params["estado"] = estado
    if id_usuario_subio:
        where.append("pe.id_usuario_subio = :id_usuario_subio")
        params["id_usuario_subio"] = id_usuario_subio
    if id_municipio:
        where.append("pe.id_municipio = :id_municipio")
        params["id_municipio"] = id_municipio
    if codigo_comunidad:
        where.append("pe.codigo_comunidad = :codigo_comunidad")
        params["codigo_comunidad"] = codigo_comunidad

    where_clause = " AND ".join(where)

    # cantidad → paginación; todos=True → sin LIMIT/OFFSET
    page = "" if todos else " LIMIT :limit OFFSET :skip"
    query_params = params if not todos else {
        k: v for k, v in params.items() if k not in ("limit", "skip")}

    rows = _rows(db, f"""
        {_LARGO_HEADER_SELECT}
        WHERE {where_clause}
        ORDER BY pe.fecha_emision DESC, pe.creado_en DESC
        {page}
    """, query_params)

    total = _row(db, f"""
        SELECT COUNT(*) as total
        FROM sinb.pronostico_largo pe
        WHERE {where_clause}
    """, {k: v for k, v in params.items() if k not in ['limit', 'skip']})['total']

    hijos = _hijos_pronostico_largo(db, [r["id"] for r in rows])
    return _serialize([_armar_pronostico_largo(r, hijos) for r in rows]), total


def get_pronostico_largo(db: Session, id: UUID):
    """Obtener pronóstico largo plazo completo: cadena, periodo, contexto, bloques y recomendaciones."""
    row = _row(db, f"{_LARGO_HEADER_SELECT} WHERE pe.id = :id", {"id": id})
    if not row:
        return None
    hijos = _hijos_pronostico_largo(db, [row["id"]])
    return _serialize(_armar_pronostico_largo(row, hijos))


def _validar_cadena_biocultural(db: Session, cadena: dict | None):
    """Validar que la cadena grupo → indicador → característica → comportamiento sea coherente (422)."""
    if not cadena:
        raise HTTPException(status_code=422, detail="cadena_biocultural es obligatoria")
    fila = _row(db, """
        SELECT 1
        FROM sinb.grupo g
        JOIN sinb.indicador_natural i ON i.id = :id_indicador_natural AND i.id_grupo = g.id
        JOIN sinb.caracteristica c ON c.id = :id_caracteristica AND c.id_indicador_natural = i.id
        JOIN sinb.comportamiento co ON co.id = :id_comportamiento AND co.id_caracteristica = c.id
        WHERE g.id = :id_grupo
          AND g.estado = 'ACTIVO' AND i.estado = 'ACTIVO'
          AND c.estado = 'ACTIVO' AND co.estado = 'ACTIVO'
    """, {
        "id_grupo": cadena.get("id_grupo"),
        "id_indicador_natural": cadena.get("id_indicador_natural"),
        "id_caracteristica": cadena.get("id_caracteristica"),
        "id_comportamiento": cadena.get("id_comportamiento"),
    })
    if not fila:
        raise HTTPException(
            status_code=422,
            detail="La cadena biocultural es incoherente: el indicador no pertenece al grupo, "
                   "la característica al indicador o el comportamiento a la característica"
        )


def _validar_escenarios_de_item(db: Session, id_categoria: UUID, escenarios: list):
    """
    Validar los escenarios de un bloque:
    - confianza ALTA | MEDIA | BAJA cuando viene (es opcional)
    - el escenario existe, está activo y pertenece a la categoría del bloque
    """
    for esc in escenarios or []:
        conf = esc.get("confianza")
        if conf is not None and conf not in ("ALTA", "MEDIA", "BAJA"):
            raise HTTPException(status_code=422, detail="La confianza debe ser ALTA, MEDIA o BAJA")
        existe = _row(db, """
            SELECT 1 FROM sinb.escenario
            WHERE id = :id AND id_categoria = :id_categoria AND estado = 'ACTIVO'
        """, {"id": esc.get("id_escenario"), "id_categoria": id_categoria})
        if not existe:
            raise HTTPException(
                status_code=422,
                detail="El escenario no existe o no pertenece a la categoría del bloque de pronóstico"
            )


def _validar_items_pronostico_largo(db: Session, items: list | None):
    """Validar los bloques de pronóstico: al menos uno y categoría activa por bloque."""
    if not items:
        raise HTTPException(status_code=422, detail="Debe incluir al menos un bloque de pronóstico")
    for it in items:
        categoria = _row(db, """
            SELECT id FROM sinb.categoria_pronostico
            WHERE id = :id AND estado = 'ACTIVO'
        """, {"id": it.get("id_categoria")})
        if not categoria:
            raise HTTPException(status_code=422, detail="La categoría de pronóstico no existe o no está activa")
        _validar_escenarios_de_item(db, categoria["id"], it.get("id_escenarios") or [])


def _validar_recomendaciones_largo(db: Session, recomendaciones: list | None):
    """Validar recomendaciones en texto libre: nombre no vacío y sin IDs duplicados (422)."""
    if not recomendaciones:
        return
    ids = [r.get("id_recomendacion") for r in recomendaciones if r.get("id_recomendacion")]
    if len(set(ids)) != len(ids):
        raise HTTPException(status_code=422, detail="Recomendación duplicada en la lista")
    for r in recomendaciones:
        nombre = (r.get("nombre") or "").strip()
        if not nombre:
            raise HTTPException(
                status_code=422,
                detail="Cada recomendación debe tener texto (nombre) no vacío"
            )
        r["nombre"] = nombre


def _validar_codigo_comunidad_municipio(db: Session, codigo_comunidad: str | None, id_municipio: int | None):
    """Validar que la comunidad pertenece al municipio especificado (422)."""
    if not codigo_comunidad or not id_municipio:
        return
    existe = _row(db, """
        SELECT 1 
        FROM shared.comunidades c
        WHERE c.codigo_ine = :codigo_comunidad 
          AND c.id_municipio = :id_municipio
    """, {"codigo_comunidad": codigo_comunidad, "id_municipio": id_municipio})
    
    if not existe:
        raise HTTPException(
            status_code=422,
            detail=f"La comunidad {codigo_comunidad} no pertenece al municipio {id_municipio}"
        )


def _validar_observadores_largo(db: Session, observadores: list | None, id_municipio: int | None = None):
    """
    1..N observadores obligatorios (07 §4.5): auto-registro o en representación.
    Valida existencia, rol, actividad y mismo municipio.
    """
    if not observadores:
        raise HTTPException(
            status_code=422,
            detail="Debe mencionar al menos un observador (auto-registro o en representación)"
        )
    ids = [o.get("id_usuario") for o in observadores]
    if len(set(ids)) != len(ids):
        raise HTTPException(status_code=422, detail="Observador duplicado en la lista")
    filas = _rows(db, """
        SELECT id_usuario, id_municipio, id_rol, nombre, activo
        FROM usuarios.usuario
        WHERE id_usuario = ANY(:ids)
    """, {"ids": ids})
    if len(filas) != len(ids):
        raise HTTPException(status_code=422, detail="Uno o más observadores no existen")
    roles_validos = {6, 7, 8, 12, 13}  # UGR Municipio, Responsable Local, Alcalde, Recolector, Observador local
    for f in filas:
        if f.get("activo") is False:
            raise HTTPException(status_code=422, detail=f"El usuario {f['nombre']} está inactivo")
        if f["id_rol"] not in roles_validos:
            raise HTTPException(status_code=422, detail=f"El usuario {f['nombre']} no tiene rol de observador")
    municipios = {f["id_municipio"] for f in filas if f["id_municipio"]}
    if len(municipios) > 1:
        raise HTTPException(status_code=422, detail="Todos los observadores deben ser del mismo municipio")
    if id_municipio and municipios and municipios != {id_municipio}:
        raise HTTPException(status_code=422, detail="Los observadores deben pertenecer al municipio del pronóstico")


def _insertar_hijos_largo(db: Session, id_pronostico: UUID,
                          items: list | None, recomendaciones: list | None, observadores: list | None):
    """Insertar bloques+escenarios, recomendaciones (texto libre) y observadores (misma transacción)."""
    import uuid
    if items is not None:
        for idx, it in enumerate(items):
            item = _row(db, """
                INSERT INTO sinb.pronostico_largo_item
                (id_pronostico_largo, id_categoria, metodo_validacion, id_regla_pronostica,
                 ejecutar_en, fuente, orden, id_item_off)
                VALUES (:id_pronostico_largo, :id_categoria, :metodo_validacion, :id_regla_pronostica,
                        :ejecutar_en, :fuente, :orden, :id_item_off)
                RETURNING id
            """, {
                "id_pronostico_largo": id_pronostico,
                "id_categoria": it.get("id_categoria"),
                "metodo_validacion": it.get("metodo_validacion"),
                "id_regla_pronostica": it.get("id_regla_pronostica"),
                "ejecutar_en": it.get("ejecutar_en"),
                "fuente": it.get("fuente"),
                "orden": it.get("orden") or (idx + 1),
                "id_item_off": it.get("id_item_off") or str(uuid.uuid4()),
            })
            for esc in it.get("id_escenarios") or []:
                confianza = esc.get("confianza") if isinstance(esc, dict) else None
                db.execute(text("""
                    INSERT INTO sinb.escenario_estacional
                    (id_pronostico_largo_item, id_escenario, confianza, id_escenario_off)
                    VALUES (:id_item, :id_escenario, CAST(:confianza AS sinb.confianza_nivel), :id_escenario_off)
                """), {
                    "id_item": item["id"],
                    "id_escenario": esc.get("id_escenario"),
                    "confianza": confianza,
                    "id_escenario_off": esc.get("id_escenario_off") if isinstance(esc, dict) else None or str(uuid.uuid4()),
                })

    for r in recomendaciones or []:
        db.execute(text("""
            INSERT INTO sinb.pronostico_largo_recomendacion
            (id, id_pronostico_largo, nombre, id_recomendacion_off)
            VALUES (:id, :id_pronostico_largo, :nombre, :id_recomendacion_off)
            ON CONFLICT (id) DO UPDATE SET
                nombre = EXCLUDED.nombre,
                id_recomendacion_off = EXCLUDED.id_recomendacion_off
        """), {
            "id": r.get("id_recomendacion") or str(uuid.uuid4()),
            "id_pronostico_largo": id_pronostico,
            "nombre": r.get("nombre"),
            "id_recomendacion_off": r.get("id_recomendacion_off") or str(uuid.uuid4()),
        })

    for obs in observadores or []:
        db.execute(text("""
            INSERT INTO sinb.pronostico_largo_observador (id_pronostico_largo, id_usuario, id_observador_off)
            VALUES (:id_pronostico_largo, :id_usuario, :id_observador_off)
            ON CONFLICT (id_pronostico_largo, id_usuario)
            DO UPDATE SET fecha_asignacion = now()
        """), {
            "id_pronostico_largo": id_pronostico,
            "id_usuario": obs.get("id_usuario"),
            "id_observador_off": obs.get("id_observador_off") or str(uuid.uuid4()),
        })


def create_pronostico_largo(db: Session, data: dict, id_usuario: int | None = None):
    """Crear pronóstico largo plazo con contrato anidado (MD 15): cadena, periodo, contexto, bloques y recomendaciones."""
    # El autor SIEMPRE lo fija el servidor: así la regla "solo el autor edita"
    # no se puede eludir enviando el id_usuario_subio de otra persona.
    if id_usuario:
        data["id_usuario_subio"] = id_usuario

    periodo = data.get("periodo") or {}
    _validar_periodo_pronostico(periodo.get("inicio"), periodo.get("fin"))
    _validar_cadena_biocultural(db, data.get("cadena_biocultural"))
    
    # Validar municipio si existe
    if data.get("id_municipio") is not None and not _row(
            db, "SELECT 1 FROM shared.municipio WHERE id = :id", {"id": data["id_municipio"]}):
        raise HTTPException(status_code=422, detail="El municipio no existe")
    
    # Validar coherencia comunidad-municipio
    _validar_codigo_comunidad_municipio(db, data.get("codigo_comunidad"), data.get("id_municipio"))

    items = data.get("pronosticos")
    _validar_items_pronostico_largo(db, items)
    _validar_recomendaciones_largo(db, data.get("recomendaciones"))
    _validar_observadores_largo(db, data.get("observadores"), data.get("id_municipio"))

    cadena = data["cadena_biocultural"]
    contexto = data.get("contexto") or {}

    params = {
        "codigo": f"PE-{datetime.now(ZONA_BOLIVIA).strftime('%Y%m%d%H%M%S')}",
        "id_pe_off": data.get("id_pe_off"),
        "fecha_emision": data.get("fecha_emision") or _hoy_bolivia(),
        "periodo_inicio": periodo.get("inicio"),
        "periodo_fin": periodo.get("fin"),
        "id_usuario_subio": data.get("id_usuario_subio"),
        "id_municipio": data.get("id_municipio"),
        "codigo_comunidad": data.get("codigo_comunidad"),
        "texto_observador": data.get("texto_observador"),
        "id_grupo": cadena.get("id_grupo"),
        "id_indicador_natural": cadena.get("id_indicador_natural"),
        "id_caracteristica": cadena.get("id_caracteristica"),
        "id_comportamiento": cadena.get("id_comportamiento"),
        "latitud": contexto.get("latitud"),
        "longitud": contexto.get("longitud"),
        "altitud": contexto.get("altitud"),
        "notas": contexto.get("notas"),
    }

    try:
        pe = _row(db, """
            INSERT INTO sinb.pronostico_largo
            (codigo, id_pe_off, fecha_emision, periodo_inicio, periodo_fin,
             id_usuario_subio, id_municipio, codigo_comunidad, texto_observador,
             id_grupo, id_indicador_natural, id_caracteristica, id_comportamiento,
             latitud, longitud, altitud, notas)
            VALUES (:codigo, :id_pe_off, :fecha_emision, :periodo_inicio, :periodo_fin,
                    :id_usuario_subio, :id_municipio, :codigo_comunidad, :texto_observador,
                    :id_grupo, :id_indicador_natural, :id_caracteristica, :id_comportamiento,
                    :latitud, :longitud, :altitud, :notas)
            RETURNING *
        """, params)
    except IntegrityError as e:
        db.rollback()
        if "codigo" in str(e.orig):
            raise HTTPException(status_code=409, detail="Código de pronóstico duplicado")
        raise HTTPException(status_code=422, detail="Violación de integridad referencial")

    if not pe:
        db.rollback()
        return None

    _insertar_hijos_largo(db, pe["id"], items, data.get("recomendaciones"), data.get("observadores"))
    db.commit()
    return get_pronostico_largo(db, pe["id"])


def _validar_periodo_pronostico(periodo_inicio, periodo_fin):
    """Validar que el periodo sea coherente (fecha_fin >= fecha_inicio)."""
    if periodo_inicio and periodo_fin and periodo_fin < periodo_inicio:
        raise HTTPException(status_code=422, detail="periodo_fin debe ser posterior o igual a periodo_inicio")


def update_pronostico_largo(db: Session, id: UUID, data: dict):
    """Actualizar pronóstico largo plazo; si vienen bloques o recomendaciones, reemplazan a los hijos."""
    actual = _row(db, "SELECT * FROM sinb.pronostico_largo WHERE id = :id", {"id": id})
    if not actual:
        return None

    periodo = data.get("periodo")
    if periodo:
        _validar_periodo_pronostico(
            periodo.get("inicio") or actual["periodo_inicio"],
            periodo.get("fin") or actual["periodo_fin"],
        )
    if data.get("cadena_biocultural"):
        _validar_cadena_biocultural(db, data["cadena_biocultural"])
    if data.get("id_municipio") is not None and not _row(
            db, "SELECT 1 FROM shared.municipio WHERE id = :id", {"id": data["id_municipio"]}):
        raise HTTPException(status_code=422, detail="El municipio no existe")

    items = data.get("pronosticos")
    if items is not None:
        _validar_items_pronostico_largo(db, items)
    recomendaciones = data.get("recomendaciones")
    if recomendaciones is not None:
        _validar_recomendaciones_largo(db, recomendaciones)

    cadena = data.get("cadena_biocultural") or {}
    contexto = data.get("contexto") or {}
    con_contexto = data.get("contexto") is not None

    params = {
        "id": id,
        "fecha_emision": data.get("fecha_emision"),
        "periodo_inicio": (periodo or {}).get("inicio"),
        "periodo_fin": (periodo or {}).get("fin"),
        "estado": data.get("estado"),
        "id_municipio": data.get("id_municipio"),
        "texto_observador": data.get("texto_observador"),
        "id_grupo": cadena.get("id_grupo"),
        "id_indicador_natural": cadena.get("id_indicador_natural"),
        "id_caracteristica": cadena.get("id_caracteristica"),
        "id_comportamiento": cadena.get("id_comportamiento"),
        "latitud": contexto.get("latitud") if con_contexto else None,
        "longitud": contexto.get("longitud") if con_contexto else None,
        "altitud": contexto.get("altitud") if con_contexto else None,
        "notas": contexto.get("notas") if con_contexto else None,
    }
    _row(db, """
        UPDATE sinb.pronostico_largo SET
            fecha_emision = COALESCE(:fecha_emision, fecha_emision),
            periodo_inicio = COALESCE(:periodo_inicio, periodo_inicio),
            periodo_fin = COALESCE(:periodo_fin, periodo_fin),
            estado = COALESCE(:estado, estado),
            id_municipio = COALESCE(:id_municipio, id_municipio),
            texto_observador = COALESCE(:texto_observador, texto_observador),
            id_grupo = COALESCE(:id_grupo, id_grupo),
            id_indicador_natural = COALESCE(:id_indicador_natural, id_indicador_natural),
            id_caracteristica = COALESCE(:id_caracteristica, id_caracteristica),
            id_comportamiento = COALESCE(:id_comportamiento, id_comportamiento),
            latitud = COALESCE(:latitud, latitud),
            longitud = COALESCE(:longitud, longitud),
            altitud = COALESCE(:altitud, altitud),
            notas = COALESCE(:notas, notas)
        WHERE id = :id
        RETURNING *
    """, params)

    if items is not None:
        _execute(db, "DELETE FROM sinb.pronostico_largo_item WHERE id_pronostico_largo = :id", {"id": id})
    if recomendaciones is not None:
        _execute(db, """
            DELETE FROM sinb.pronostico_largo_recomendacion WHERE id_pronostico_largo = :id
        """, {"id": id})
    _insertar_hijos_largo(
        db, id,
        items if items is not None else None,
        recomendaciones if recomendaciones is not None else None,
        None,
    )
    db.commit()
    return get_pronostico_largo(db, id)


def delete_pronostico_largo(db: Session, id: UUID, id_usuario: int | None = None):
    """
    Eliminar pronóstico largo plazo (borrado físico en cascada desde la cabecera):
    bloques -> escenario_estacional, recomendaciones, observadores
    y verificacion_pronostico tienen ON DELETE CASCADE sobre esta tabla.

    Deja su tombstone: es una cabecera, así que al retirar la fila la app
    descarta también sus hijos.
    """
    existe = _row(db, "SELECT id, codigo, id_pe_off FROM sinb.pronostico_largo WHERE id = :id", {"id": id})
    if not existe:
        raise HTTPException(status_code=404, detail="Pronóstico no encontrado")
    _registrar_borrado(db, "pronostico_largo", existe, id_usuario)
    db.execute(text("DELETE FROM sinb.pronostico_largo WHERE id = :id"), {"id": id})
    db.commit()


def _item_pertenece_al_pronostico(db: Session, id_pronostico: UUID, id_item: UUID) -> dict:
    item = _row(db, """
        SELECT id, id_categoria FROM sinb.pronostico_largo_item
        WHERE id = :id AND id_pronostico_largo = :id_pronostico
    """, {"id": id_item, "id_pronostico": id_pronostico})
    if not item:
        raise HTTPException(status_code=404, detail="Bloque de pronóstico no encontrado")
    return item


def add_escenario_a_pronostico(db: Session, id_pronostico: UUID, id_item: UUID,
                               id_escenario: UUID, confianza: str | None = None):
    """Agregar (o actualizar) un escenario en un bloque del pronóstico."""
    item = _item_pertenece_al_pronostico(db, id_pronostico, id_item)
    _validar_escenarios_de_item(
        db, item["id_categoria"], [{"id_escenario": id_escenario, "confianza": confianza}]
    )
    result = _row(db, """
        INSERT INTO sinb.escenario_estacional
        (id_pronostico_largo_item, id_escenario, confianza)
        VALUES (:id_item, :id_escenario, CAST(:confianza AS sinb.confianza_nivel))
        ON CONFLICT (id_pronostico_largo_item, id_escenario)
        DO UPDATE SET confianza = EXCLUDED.confianza
        RETURNING *
    """, {"id_item": id_item, "id_escenario": id_escenario, "confianza": confianza})
    db.commit()
    return result


def remove_escenario_de_pronostico(db: Session, id_pronostico: UUID, id_item: UUID, id_escenario: UUID):
    """Remover un escenario de un bloque del pronóstico."""
    _item_pertenece_al_pronostico(db, id_pronostico, id_item)
    result = _row(db, """
        DELETE FROM sinb.escenario_estacional
        WHERE id_pronostico_largo_item = :id_item AND id_escenario = :id_escenario
        RETURNING *
    """, {"id_item": id_item, "id_escenario": id_escenario})
    if not result:
        raise HTTPException(status_code=404, detail="El escenario no está en este bloque de pronóstico")
    db.commit()
    return result


# --- Pronósticos Temporales ---

def get_pronosticos_temporales(db: Session, skip: int = 0, limit: int = 15,
                                todos: bool = False,
                                id_categoria: UUID | None = None,
                                fecha_emision_desde: date | None = None,
                                confianza: str | None = None,
                                estado: str | None = None,
                                codigo_comunidad: str | None = None):
    """Obtener pronósticos temporales con paginación.

    `todos=True` devuelve el conjunto completo (sin `LIMIT`/`OFFSET`).
    """
    params = {"limit": limit, "skip": skip}
    where = ["pt.estado IN ('EMITIDO', 'ACEPTADO', 'RECHAZADO', 'EN_REVISION')"]
    
    if id_categoria:
        where.append("pt.id_categoria = :id_categoria")
        params["id_categoria"] = id_categoria
    if fecha_emision_desde:
        where.append("pt.fecha_emision >= :fecha_emision_desde")
        params["fecha_emision_desde"] = fecha_emision_desde
    if confianza:
        where.append("pt.confianza = CAST(:confianza AS sinb.confianza_nivel)")
        params["confianza"] = confianza
    if estado:
        where.append("pt.estado = CAST(:estado AS sinb.estado_validacion)")
        params["estado"] = estado
    if codigo_comunidad:
        where.append("pt.codigo_comunidad = :codigo_comunidad")
        params["codigo_comunidad"] = codigo_comunidad
    
    where_clause = " AND ".join(where)
    
    # cantidad → paginación; todos=True → sin LIMIT/OFFSET
    page = "" if todos else " LIMIT :limit OFFSET :skip"
    query_params = params if not todos else {
        k: v for k, v in params.items() if k not in ("limit", "skip")}

    rows = _rows(db, f"""
        SELECT pt.id, pt.codigo, pt.id_pt_off, pt.id_categoria, pt.codigo_comunidad, pt.id_municipio,
               pt.fecha_emision, pt.fecha_inicio, pt.fecha_fin, pt.texto_observador,
               pt.confianza, pt.estado, pt.creado_en, cat.nombre as categoria_nombre,
               pt.id_usuario_subio
        FROM sinb.pronostico_corto pt
        LEFT JOIN sinb.categoria_pronostico cat ON cat.id = pt.id_categoria
        WHERE {where_clause}
        ORDER BY pt.fecha_emision DESC
        {page}
    """, query_params)
    
    total = _row(db, f"""
        SELECT COUNT(*) as total
        FROM sinb.pronostico_corto pt
        WHERE {where_clause}
    """, {k: v for k, v in params.items() if k not in ['limit', 'skip']})['total']
    
    return _serialize(rows), total


def get_pronostico_corto_by_id(db: Session, id: UUID):
    """Obtener pronóstico corto plazo completo."""
    pc = _row(db, """
        SELECT pt.id, pt.codigo, pt.id_pt_off, pt.id_categoria, pt.codigo_comunidad, pt.id_municipio,
               pt.fecha_emision, pt.fecha_inicio, pt.fecha_fin, pt.texto_observador,
               pt.confianza, pt.estado, pt.creado_en, cat.nombre as categoria_nombre,
               pt.id_usuario_subio
        FROM sinb.pronostico_corto pt
        LEFT JOIN sinb.categoria_pronostico cat ON cat.id = pt.id_categoria
        WHERE pt.id = :id
    """, {"id": id})
    
    if pc:
        pc = dict(pc)
        # Observadores asignados
        pc["observadores"] = _rows(db, """
            SELECT po.id_usuario, u.nombre, u.usuario, po.confianza, po.fecha_asignacion
            FROM sinb.pronostico_corto_observador po
            JOIN usuarios.usuario u ON u.id_usuario = po.id_usuario
            WHERE po.id_pronostico_corto = :id
        """, {"id": id})
    
    return pc


def create_pronostico_corto(db: Session, data: dict, id_usuario: int | None = None):
    """Crear pronóstico temporal."""
    # El autor SIEMPRE lo fija el servidor (misma regla que el pronóstico largo).
    if id_usuario:
        data["id_usuario_subio"] = id_usuario
    
    _validar_periodo_pronostico(data.get("fecha_inicio"), data.get("fecha_fin"))
    if not _row(db, """
        SELECT 1 FROM sinb.categoria_pronostico WHERE id = :id AND estado = 'ACTIVO'
    """, {"id": data.get("id_categoria")}):
        raise HTTPException(status_code=422, detail="La categoría de pronóstico no existe o no está activa")
    
    # Validar coherencia comunidad-municipio
    _validar_codigo_comunidad_municipio(db, data.get("codigo_comunidad"), data.get("id_municipio"))
    
    data["codigo"] = f"PT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    params = {
        "codigo": data["codigo"],
        "id_pt_off": data.get("id_pt_off"),
        "id_categoria": data.get("id_categoria"),
        "fecha_emision": data.get("fecha_emision"),
        "fecha_inicio": data.get("fecha_inicio"),
        "fecha_fin": data.get("fecha_fin"),
        "texto_observador": data.get("texto_observador"),
        "confianza": data.get("confianza"),
        "id_usuario_subio": data.get("id_usuario_subio"),
        "id_municipio": data.get("id_municipio"),
        "codigo_comunidad": data.get("codigo_comunidad"),
    }
    result = _row(db, """
        INSERT INTO sinb.pronostico_corto 
        (codigo, id_pt_off, id_categoria, fecha_emision, fecha_inicio, fecha_fin,
         texto_observador, confianza, id_usuario_subio, id_municipio, codigo_comunidad)
        VALUES (:codigo, :id_pt_off, :id_categoria, :fecha_emision, :fecha_inicio, :fecha_fin,
                :texto_observador, :confianza, :id_usuario_subio, :id_municipio, :codigo_comunidad)
        RETURNING *
    """, params)
    db.commit()
    return result


def update_pronostico_corto(db: Session, id: UUID, data: dict):
    """Actualizar pronóstico temporal."""
    if "fecha_inicio" in data or "fecha_fin" in data:
        actual = _row(db, "SELECT fecha_inicio, fecha_fin FROM sinb.pronostico_corto WHERE id = :id", {"id": id})
        if not actual:
            return None
        _validar_periodo_pronostico(
            data.get("fecha_inicio", actual["fecha_inicio"]),
            data.get("fecha_fin", actual["fecha_fin"]),
        )
    
    data["id"] = id
    for key in ("id_categoria", "fecha_emision", "fecha_inicio", "fecha_fin",
                "texto_observador", "confianza", "codigo_comunidad"):
        data.setdefault(key, None)
    result = _row(db, """
        UPDATE sinb.pronostico_corto SET
            id_categoria = COALESCE(:id_categoria, id_categoria),
            fecha_emision = COALESCE(:fecha_emision, fecha_emision),
            fecha_inicio = COALESCE(:fecha_inicio, fecha_inicio),
            fecha_fin = COALESCE(:fecha_fin, fecha_fin),
            texto_observador = COALESCE(:texto_observador, texto_observador),
            confianza = COALESCE(:confianza, confianza),
            codigo_comunidad = COALESCE(:codigo_comunidad, codigo_comunidad)
        WHERE id = :id
        RETURNING *
    """, data)
    db.commit()
    return result


def delete_pronostico_corto(db: Session, id: UUID, id_usuario: int | None = None):
    """Eliminar pronóstico temporal (borrado físico en cascada + tombstone)."""
    existe = _row(db, "SELECT id, codigo, id_pt_off FROM sinb.pronostico_corto WHERE id = :id", {"id": id})
    if not existe:
        raise HTTPException(status_code=404, detail="Pronóstico no encontrado")
    _registrar_borrado(db, "pronostico_corto", existe, id_usuario)
    db.execute(text("DELETE FROM sinb.pronostico_corto WHERE id = :id"), {"id": id})
    db.commit()


# ============================================================================
# ASIGNACIÓN DE OBSERVADORES A PRONÓSTICOS
# ============================================================================

def _norm_tipo_pronostico(tipo: str | None) -> str | None:
    """Normalizar 'estacional'/'temporal' (contrato API) a 'largo'/'corto' (interno de tablas)."""
    return {"estacional": "largo", "temporal": "corto"}.get(tipo, tipo)


def asignar_observadores_a_pronostico(db: Session, id_pronostico: UUID, tipo_pronostico: str,
                                       id_observadores: list[int], confianza: str | None = None,
                                       id_usuario_asigna: int | None = None):
    """
    Asignar 1..N observadores a un pronóstico (recolector → observadores del mismo municipio).
    Valida que todos los observadores sean del mismo municipio.
    """
    tipo_pronostico = _norm_tipo_pronostico(tipo_pronostico)
    if not id_observadores:
        raise HTTPException(status_code=400, detail="Debe especificar al menos un observador")

    # El pronóstico destino debe existir; si no, el INSERT choca con la FK (500)
    tabla_pron = "sinb.pronostico_largo" if tipo_pronostico == "largo" else "sinb.pronostico_corto"
    if not _row(db, f"SELECT 1 FROM {tabla_pron} WHERE id = :id", {"id": id_pronostico}):
        raise HTTPException(status_code=404, detail="Pronóstico no encontrado")
    
    # Validar que todos los observadores existen y son del mismo municipio
    observadores = _rows(db, """
        SELECT id_usuario, id_municipio, id_rol, nombre
        FROM usuarios.usuario
        WHERE id_usuario = ANY(:ids)
    """, {"ids": id_observadores})
    
    if len(observadores) != len(id_observadores):
        raise HTTPException(status_code=400, detail="Uno o más observadores no existen")
    
    # Validar que todos son del mismo municipio
    municipios = set(o["id_municipio"] for o in observadores if o["id_municipio"])
    if len(municipios) > 1:
        raise HTTPException(status_code=400, detail="Los observadores deben ser del mismo municipio")
    
    # Validar que tienen rol de observador local o usuario recolector
    roles_validos = {6, 7, 8, 12, 13}  # UGR Municipio, Responsable Local, Alcalde, Usuario recolector, Observador local
    for obs in observadores:
        if obs["id_rol"] not in roles_validos:
            raise HTTPException(status_code=400, detail=f"El usuario {obs['nombre']} no tiene rol de observador")
    
    # Insertar asignaciones
    # El pronóstico largo NO guarda confianza por observador (la confianza vive en los
    # escenarios); la tabla de corto plazo sí la mantiene.
    asignaciones = []
    es_largo = tipo_pronostico == "largo"
    tabla = "sinb.pronostico_largo_observador" if es_largo else "sinb.pronostico_corto_observador"
    columna = "id_pronostico_largo" if es_largo else "id_pronostico_corto"

    for id_obs in id_observadores:
        if es_largo:
            result = _row(db, f"""
                INSERT INTO {tabla}
                ({columna}, id_usuario)
                VALUES (:id_pronostico, :id_usuario)
                ON CONFLICT ({columna}, id_usuario)
                DO UPDATE SET fecha_asignacion = now()
                RETURNING *, NULL::text AS confianza
            """, {"id_pronostico": id_pronostico, "id_usuario": id_obs})
        else:
            result = _row(db, f"""
                INSERT INTO {tabla}
                ({columna}, id_usuario, confianza)
                VALUES (:id_pronostico, :id_usuario, :confianza)
                ON CONFLICT ({columna}, id_usuario)
                DO UPDATE SET confianza = :confianza, fecha_asignacion = now()
                RETURNING *
            """, {"id_pronostico": id_pronostico, "id_usuario": id_obs, "confianza": confianza})
        asignaciones.append(result)
    
    db.commit()
    return asignaciones


def remover_observador_de_pronostico(db: Session, id_pronostico: UUID, tipo_pronostico: str,
                                      id_usuario: int):
    """Remover asignación de observador de un pronóstico (idempotente si no estaba asignado)."""
    tipo_pronostico = _norm_tipo_pronostico(tipo_pronostico)
    es_largo = tipo_pronostico == "largo"
    tabla = "sinb.pronostico_largo_observador" if es_largo else "sinb.pronostico_corto_observador"
    columna = "id_pronostico_largo" if es_largo else "id_pronostico_corto"
    tabla_pron = "sinb.pronostico_largo" if es_largo else "sinb.pronostico_corto"

    if not _row(db, f"SELECT 1 FROM {tabla_pron} WHERE id = :id", {"id": id_pronostico}):
        raise HTTPException(status_code=404, detail="Pronóstico no encontrado")

    _execute(db, f"""
        DELETE FROM {tabla}
        WHERE {columna} = :id_pronostico AND id_usuario = :id_usuario
    """, {"id_pronostico": id_pronostico, "id_usuario": id_usuario})


# ============================================================================
# VALIDACIÓN AUTOMÁTICA DE PRONÓSTICOS
# ============================================================================

def calcular_verificacion_automatica(db: Session, id_pronostico: UUID | None = None,
                                      tipo: str = "todos"):
    """
    Calcular automáticamente verificación de pronósticos vencidos con NDVI + digital.
    
    Reglas automáticas:
    1. Pronóstico vencido (periodo_fin < NOW()) → verificar
    2. Usar datos digitales (precipitación, temperatura) para el periodo
    3. Usar NDVI para estado de vegetación
    4. Si no hay datos → NO_VERIFICABLE
    5. Si hay datos y coinciden → COINCIDE, si no → NO_COINCIDE
    
    Retorna lista de verificaciones calculadas.
    """
    tipo = _norm_tipo_pronostico(tipo)
    resultados = []
    
    # Pronósticos estacionales vencidos
    if tipo in ["largo", "todos"]:
        vencidos_largo = _rows(db, """
            SELECT pe.id, pe.periodo_inicio, pe.periodo_fin, pe.id_municipio
            FROM sinb.pronostico_largo pe
            WHERE pe.periodo_fin < CURRENT_DATE
            AND pe.estado = 'EMITIDO'
            AND NOT EXISTS (
                SELECT 1 FROM sinb.verificacion_pronostico vp
                WHERE vp.id_pronostico_largo = pe.id
            )
        """, {})
        
        for pe in vencidos_largo:
            resultado = _verificar_pronostico_individual(db, pe["id"], "largo")
            resultados.append(resultado)
    
    # Pronósticos temporales vencidos
    if tipo in ["corto", "todos"]:
        vencidos_corto = _rows(db, """
            SELECT pt.id, pt.fecha_emision, pt.periodo_inicio, pt.periodo_fin, 
                   pt.id_categoria, pt.id_municipio
            FROM sinb.pronostico_corto pt
            WHERE pt.periodo_fin < CURRENT_DATE
            AND pt.estado = 'EMITIDO'
            AND NOT EXISTS (
                SELECT 1 FROM sinb.verificacion_pronostico vp
                WHERE vp.id_pronostico_corto = pt.id
            )
        """, {})
        
        for pt in vencidos_corto:
            resultado = _verificar_pronostico_individual(db, pt["id"], "corto")
            resultados.append(resultado)
    
    return resultados


def _verificar_pronostico_individual(db: Session, id_pronostico: UUID, tipo: str):
    """
    Verificar un pronóstico individual usando datos digitales (Open-Meteo) y NDVI.
    
    Para corto plazo: compara categoría predicha vs datos digitales en la ventana
    Para largo plazo: verifica si el campo ocurrió (ej. lluvia) usando datos digitales
    
    Retorna dict con estado de verificación.
    """
    from datetime import timedelta
    
    if tipo == "largo":
        pron = _row(db, """
            SELECT pe.*, pe.latitud, pe.longitud,
                   (SELECT cp.nombre FROM sinb.pronostico_largo_item it
                    JOIN sinb.categoria_pronostico cp ON cp.id = it.id_categoria
                    WHERE it.id_pronostico_largo = pe.id
                    ORDER BY it.orden, it.creado_en LIMIT 1) as categoria_nombre
            FROM sinb.pronostico_largo pe
            WHERE pe.id = :id
        """, {"id": id_pronostico})
    else:
        pron = _row(db, """
            SELECT pt.*, cp.nombre as categoria_nombre, 
                   COALESCE(m.latitud, 0) as latitud, COALESCE(m.longitud, 0) as longitud
            FROM sinb.pronostico_corto pt
            JOIN sinb.categoria_pronostico cp ON cp.id = pt.id_categoria
            LEFT JOIN shared.municipio m ON m.id = pt.id_municipio
            WHERE pt.id = :id
        """, {"id": id_pronostico})
    
    if not pron:
        return {"error": "Pronóstico no encontrado"}
    
    id_largo = id_pronostico if tipo == "largo" else None
    id_corto = id_pronostico if tipo == "corto" else None
    id_municipio = pron.get("id_municipio")
    
    # Intentar obtener datos digitales para el periodo
    datos_digital = _row(db, """
        SELECT 
            AVG(precipitacion_suma) as precip_promedio,
            SUM(precipitacion_suma) as precip_total,
            AVG(temp_max) as temp_max_prom,
            AVG(temp_min) as temp_min_prom,
            COUNT(*) as dias_con_datos
        FROM sinb.pronostico_diario_municipal
        WHERE id_municipio = :id_municipio
        AND fecha BETWEEN :fecha_inicio AND :fecha_fin
    """, {
        "id_municipio": id_municipio,
        "fecha_inicio": pron["periodo_inicio"],
        "fecha_fin": pron["periodo_fin"]
    })
    
    # Verificar si hay datos suficientes
    if not datos_digital or datos_digital.get("dias_con_datos", 0) == 0:
        # No hay datos digitales → NO_VERIFICABLE
        verif = _row(db, """
            INSERT INTO sinb.verificacion_pronostico
            (id_pronostico_largo, id_pronostico_corto, estado, es_autoevaluada,
             fecha_verificacion, notas)
            VALUES (:id_largo, :id_corto, 'NO_VERIFICABLE', true, now(),
                    'Sin datos digitales en el periodo de verificación')
            RETURNING *
        """, {
            "id_largo": id_largo,
            "id_corto": id_corto
        })
        db.commit()
        
        return {
            "id_pronostico": id_pronostico,
            "tipo": tipo,
            "estado_calculo": "NO_VERIFICABLE",
            "mensaje": "Sin datos digitales en el periodo"
        }
    
    # Determinar si coincidió según el campo
    # Simplificado: lluvia = precip_total > 0, helada = temp_min < 0
    campo = (pron.get("categoria_nombre") or pron.get("campo_nombre") or "").lower()
    acierto = False
    notas = ""
    
    if "lluvia" in campo:
        acierto = datos_digital.get("precip_total", 0) > 0
        notas = f"Precipitación total: {datos_digital.get('precip_total', 0):.1f}mm"
    elif "helada" in campo or "frost" in campo:
        temp_min = datos_digital.get("temp_min_prom", 10)
        acierto = temp_min < 0
        notas = f"Temp mínima promedio: {temp_min:.1f}°C"
    elif "sequía" in campo or "calor" in campo:
        temp_max = datos_digital.get("temp_max_prom", 20)
        acierto = temp_max > 30
        notas = f"Temp máxima promedio: {temp_max:.1f}°C"
    else:
        notas = f"Campo '{campo}' sin regla de verificación automática"
    
    estado = "COINCIDE" if acierto else "NO_COINCIDE"
    
    # Insertar/actualizar verificación
    verif = _row(db, """
        INSERT INTO sinb.verificacion_pronostico
        (id_pronostico_largo, id_pronostico_corto, estado, es_autoevaluada,
         fecha_verificacion, notas, acierto_categoria)
        VALUES (:id_largo, :id_corto, :estado, true, now(), :notas, :acierto)
        ON CONFLICT DO NOTHING
        RETURNING *
    """, {
        "id_largo": id_largo,
        "id_corto": id_corto,
        "estado": estado,
        "notas": notas,
        "acierto": acierto
    })
    db.commit()
    
    return {
        "id_pronostico": id_pronostico,
        "tipo": tipo,
        "estado_calculo": estado,
        "acierto": acierto,
        "mensaje": notas
    }


def get_verificaciones_pendientes(db: Session, limit: int | None = None,
                                  skip: int = 0, todos: bool = False):
    """Obtener lista de pronósticos pendientes de verificación.

    Por defecto sin paginar; `limit`/`skip` sólo si se piden, `todos=true` fuerza el completo.
    """
    page, page_params = pagina_limit_offset(limit, skip, todos)
    return _rows(db, f"""
        SELECT 
            pe.id as id_pronostico_largo,
            pt.id as id_pronostico_corto,
            COALESCE(cp_largo.nombre, cp_corto.nombre) as categoria_nombre,
            pe.periodo_fin as periodo_fin_estacional,
            pt.fecha_fin as periodo_fin_temporal,
            CURRENT_DATE - COALESCE(pe.periodo_fin, pt.fecha_fin) as dias_vencido
        FROM (
            SELECT pl.id, pl.periodo_fin, 'LARGO'::text as tipo,
                   (SELECT it.id_categoria FROM sinb.pronostico_largo_item it
                    WHERE it.id_pronostico_largo = pl.id
                    ORDER BY it.orden, it.creado_en LIMIT 1) as id_categoria
            FROM sinb.pronostico_largo pl
            WHERE pl.periodo_fin < CURRENT_DATE
            AND pl.estado IN ('EMITIDO', 'ACEPTADO')
            UNION ALL
            SELECT pc.id, pc.fecha_fin, 'CORTO'::text as tipo, pc.id_categoria
            FROM sinb.pronostico_corto pc
            WHERE pc.fecha_fin < CURRENT_DATE
            AND pc.estado IN ('EMITIDO', 'ACEPTADO')
        ) p
        LEFT JOIN sinb.verificacion_pronostico vp 
            ON (p.tipo = 'LARGO' AND vp.id_pronostico_largo = p.id)
            OR (p.tipo = 'CORTO' AND vp.id_pronostico_corto = p.id)
        LEFT JOIN sinb.categoria_pronostico cp_largo ON p.tipo = 'LARGO' AND cp_largo.id = p.id_categoria
        LEFT JOIN sinb.categoria_pronostico cp_corto ON p.tipo = 'CORTO' AND cp_corto.id = p.id_categoria
        LEFT JOIN sinb.pronostico_largo pe ON p.tipo = 'LARGO' AND pe.id = p.id
        LEFT JOIN sinb.pronostico_corto pt ON p.tipo = 'CORTO' AND pt.id = p.id
        WHERE vp.id IS NULL
        ORDER BY dias_vencido DESC
        {page}
    """, page_params)


def validar_pronostico_manual(db: Session, id_pronostico: UUID, tipo: str,
                               estado: str, notas: str | None = None,
                               acierto_categoria: bool | None = None,
                               id_usuario_verifica: int | None = None):
    """
    Validación MANUAL de pronóstico por usuario autorizado.
    Sobrescribe validación automática si existe.
    """
    tipo = _norm_tipo_pronostico(tipo)
    if estado not in ["COINCIDE", "NO_COINCIDE", "PENDIENTE", "EN_VERIFICACION", "NO_VERIFICABLE"]:
        raise HTTPException(status_code=400, detail="Estado no válido")
    
    id_largo = id_pronostico if tipo == "largo" else None
    id_corto = id_pronostico if tipo == "corto" else None
    
    result = _row(db, """
        INSERT INTO sinb.verificacion_pronostico
        (id_pronostico_largo, id_pronostico_corto, estado, notas,
         acierto_categoria, es_autoevaluada, verificado_por, fecha_verificacion)
        VALUES (:id_largo, :id_corto, :estado, :notas, :acierto,
                false, :id_usuario, now())
        ON CONFLICT (id) DO UPDATE SET
            estado = :estado,
            notas = :notas,
            acierto_categoria = :acierto,
            es_autoevaluada = false,
            verificado_por = :id_usuario,
            fecha_verificacion = now()
        RETURNING *
    """, {
        "id_largo": id_largo,
        "id_corto": id_corto,
        "estado": estado,
        "notas": notas,
        "acierto": acierto_categoria,
        "id_usuario": id_usuario_verifica
    })
    
    db.commit()
    return result
# CALENDARIO DE SIEMBRA Y RECOMENDACIONES
# ============================================================================


# ============================================================================
# PRONÓSTICOS DIGITALES (Open-Meteo Integration)
# ============================================================================

import httpx
import time
from zoneinfo import ZoneInfo

OPEN_METEO_BASE = "https://api.open-meteo.com/v1"
ZONA_BOLIVIA = ZoneInfo("America/La_Paz")
HORIZONTE_DIAS = 16


def _hoy_bolivia() -> date:
    """
    Fecha local de Bolivia. El servidor corre en UTC: entre 00:00 y 04:00 UTC
    (20:00-24:00 Bolivia) date.today() devolvería un día adelantado y la ventana
    de 16 días quedaría desfasada respecto al día solar de los datos.
    """
    return datetime.now(ZONA_BOLIVIA).date()


def _serie(arr: list, i: int):
    """Valor i-ésimo de una serie de Open-Meteo, o None si la serie viene más corta que `time`."""
    return arr[i] if i < len(arr) else None


def _con_reintentos(fn, intentos: int = 3, base: float = 2.0):
    """
    Ejecutar fn reintentando ante cualquier fallo (timeout/SSL/503 de Open-Meteo)
    con espera exponencial: 2 s, 4 s, 8 s...
    """
    ultima_exception = None
    for n in range(1, intentos + 1):
        try:
            return fn()
        except Exception as e:
            ultima_exception = e
            if n < intentos:
                time.sleep(base ** n)
    raise ultima_exception


def consultar_open_meteo(
    latitud: float,
    longitud: float,
    tipo: str = "daily",
    variables: list[str] = None,
    horizonte_dias: int = 16
) -> dict:
    """
    Consultar API de Open-Meteo.
    
    Args:
        latitud: Latitud del punto
        longitud: Longitud del punto
        tipo: "daily" (16 días) o "hourly" (168 horas)
        variables: Lista de variables a consultar
        horizonte_dias: Días de horizonte (default 16, max 16)
    
    Returns:
        Datos crudos de Open-Meteo
    """
    params = {
        "latitude": latitud,
        "longitude": longitud,
        "timezone": "America/La_Paz",
        "forecast_days": min(horizonte_dias, HORIZONTE_DIAS)
    }
    
    # Variables por defecto según tipo (agricultura-focused)
    if tipo == "daily":
        params["daily"] = ",".join(variables or [
            "temperature_2m_max", "temperature_2m_min",
            "precipitation_sum", "precipitation_probability_max",
            "relative_humidity_2m_max", "relative_humidity_2m_min",
            "et0_fao_evapotranspiration",
            "wind_speed_10m_max", "wind_direction_10m_dominant",
            "shortwave_radiation_sum", "uv_index_max",
            "sunrise", "sunset"
        ])
    elif tipo == "hourly":
        params["hourly"] = ",".join(variables or [
            "temperature_2m", "relative_humidity_2m",
            "precipitation", "precipitation_probability",
            "wind_speed_10m", "wind_direction_10m",
            "et0_fao_evapotranspiration", "weather_code"
        ])
        params["forecast_hours"] = min(horizonte_dias * 24, 168)
    
    try:
        response = httpx.get(f"{OPEN_METEO_BASE}/forecast", params=params, timeout=30.0)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Error consultando Open-Meteo: {str(e)}"
        )


def guardar_pronostico_diario_municipal(
    db: Session,
    id_municipio: int,
    latitud: float,
    longitud: float,
    fecha: date = None,
    reintentos: int = 3
) -> dict:
    """
    Guardar pronóstico diario para un municipio (uso automático cron).
    
    **Horario de referencia:** Los datos son del día COMPLETO en hora local
    (0:00 a 23:59 America/La_Paz, UTC-4).
    
    Variables guardadas:
    - Temperatura: máx, mín
    - Precipitación: suma, probabilidad máx
    - Humedad relativa: máx, mín
    - Evapotranspiración FAO ET₀
    - Viento: velocidad máx, dirección dominante
    - Radiación solar
    - Índice UV máx
    - Amanecer/atardecer
    
    Se escribe en UN solo upsert por municipio (ON CONFLICT uk_pronostico_diario)
    y se comitea una vez: o quedan los 16 días o ninguno. Sólo se tocan las fechas
    que trae Open-Meteo (hoy en adelante); los días pasados quedan como evidencia.
    
    Args:
        db: Sesión de base de datos
        id_municipio: ID del municipio
        latitud: Latitud del centroide del municipio
        longitud: Longitud del centroide del municipio
        fecha: Fecha a consultar (hoy en hora Bolivia por defecto)
        reintentos: Intentos sobre Open-Meteo antes de rendirse (default 3, espera 2/4/8 s)
    
    Returns:
        Datos guardados
    """
    if fecha is None:
        fecha = _hoy_bolivia()

    # 3 intentos con backoff: un timeout de Open-Meteo dejaba al municipio con la
    # cola de la corrida anterior (15 días en vez de 16).
    datos = _con_reintentos(
        lambda: consultar_open_meteo(latitud, longitud, "daily", horizonte_dias=HORIZONTE_DIAS),
        intentos=reintentos
    )

    daily = datos.get("daily") or {}
    fechas = daily.get("time") or []
    if not fechas:
        raise HTTPException(status_code=503, detail="Open-Meteo no devolvió datos diarios")

    series = {
        "temp_max": daily.get("temperature_2m_max", []),
        "temp_min": daily.get("temperature_2m_min", []),
        "precip_sum": daily.get("precipitation_sum", []),
        "precip_prob": daily.get("precipitation_probability_max", []),
        "humedad_max": daily.get("relative_humidity_2m_max", []),
        "humedad_min": daily.get("relative_humidity_2m_min", []),
        "eto": daily.get("et0_fao_evapotranspiration", []),
        "viento_vel": daily.get("wind_speed_10m_max", []),
        "viento_dir": daily.get("wind_direction_10m_dominant", []),
        "radiacion": daily.get("shortwave_radiation_sum", []),
        "uv_max": daily.get("uv_index_max", []),
    }

    # Una serie más corta que `time` ya no rompe la mitad del lote: se guarda None y avisa.
    cortas = {k: len(v) for k, v in series.items() if 0 < len(v) != len(fechas)}
    if cortas:
        print(f"[advertencia] municipio {id_municipio}: series más cortas que time -> {cortas}")

    filas = []
    for i, fecha_str in enumerate(fechas):
        fila = {"id_municipio": id_municipio, "fecha": date.fromisoformat(fecha_str)}
        for k, v in series.items():
            fila[k] = _serie(v, i)
        fila["sunrise"] = _parsear_hora_local(daily.get("sunrise", []), i)
        fila["sunset"] = _parsear_hora_local(daily.get("sunset", []), i)
        filas.append(fila)

    db.execute(text("""
        INSERT INTO sinb.pronostico_diario_municipal
            (id_municipio, fecha, temp_max, temp_min, precipitacion_suma,
             precipitacion_prob_max, humedad_relativa_max, humedad_relativa_min,
             evapotranspiracion, viento_velocidad_max, viento_direccion,
             radiacion_solar, uv_index_max, sunrise, sunset)
        VALUES
            (:id_municipio, :fecha, :temp_max, :temp_min, :precip_sum,
             :precip_prob, :humedad_max, :humedad_min,
             :eto, :viento_vel, :viento_dir,
             :radiacion, :uv_max, :sunrise, :sunset)
        ON CONFLICT (id_municipio, fecha) DO UPDATE SET
            temp_max = EXCLUDED.temp_max,
            temp_min = EXCLUDED.temp_min,
            precipitacion_suma = EXCLUDED.precipitacion_suma,
            precipitacion_prob_max = EXCLUDED.precipitacion_prob_max,
            humedad_relativa_max = EXCLUDED.humedad_relativa_max,
            humedad_relativa_min = EXCLUDED.humedad_relativa_min,
            evapotranspiracion = EXCLUDED.evapotranspiracion,
            viento_velocidad_max = EXCLUDED.viento_velocidad_max,
            viento_direccion = EXCLUDED.viento_direccion,
            radiacion_solar = EXCLUDED.radiacion_solar,
            uv_index_max = EXCLUDED.uv_index_max,
            sunrise = EXCLUDED.sunrise,
            sunset = EXCLUDED.sunset,
            actualizado_en = now()
    """), filas)
    db.commit()

    return {
        "municipio_id": id_municipio,
        "registros_guardados": len(filas),
        "fechas": [f["fecha"].isoformat() for f in filas],
        "nota": "16 días desde hoy (0:00-23:59 hora local America/La_Paz)"
    }


def _parsear_hora_local(serie: list, i: int):
    """sunrise/sunset vienen como '2026-10-07T06:12' en hora local; la columna es timestamptz."""
    valor = _serie(serie, i)
    if not valor:
        return None
    try:
        return datetime.fromisoformat(str(valor).replace("T", " "))
    except ValueError:
        return None


def get_pronostico_diario_historico(
    db: Session,
    filtros: dict,
    pagina: int = 1,
    por_pagina: int = 50
) -> tuple[list, int]:
    """
    Obtener histórico de pronóstico diario con filtros y paginación.
    
    Args:
        db: Sesión de base de datos
        filtros: Diccionario de filtros (id_municipio, codigo_comunidad, fechas, etc.)
        pagina: Número de página (default 1)
        por_pagina: Registros por página (default 50)
    
    Returns:
        Tupla (lista_de_registros, total_registros)
    """
    where = []
    params = {}
    
    # Filtros geográficos
    if filtros.get("id_municipio"):
        where.append("pdm.id_municipio = :id_municipio")
        params["id_municipio"] = filtros["id_municipio"]
    
    if filtros.get("codigo_comunidad"):
        where.append("c.codigo_ine = :codigo_comunidad")
        params["codigo_comunidad"] = filtros["codigo_comunidad"]
    
    # Filtros de fecha
    if filtros.get("fecha_desde"):
        where.append("pdm.fecha >= :fecha_desde")
        params["fecha_desde"] = filtros["fecha_desde"]
    
    if filtros.get("fecha_hasta"):
        where.append("pdm.fecha <= :fecha_hasta")
        params["fecha_hasta"] = filtros["fecha_hasta"]
    
    # Filtros de datos meteorológicos
    if filtros.get("temp_max_min") is not None:
        where.append("pdm.temp_max >= :temp_max_min")
        params["temp_max_min"] = filtros["temp_max_min"]
    
    if filtros.get("temp_max_max") is not None:
        where.append("pdm.temp_max <= :temp_max_max")
        params["temp_max_max"] = filtros["temp_max_max"]
    
    if filtros.get("precipitacion_min") is not None:
        where.append("pdm.precipitacion_suma >= :precipitacion_min")
        params["precipitacion_min"] = filtros["precipitacion_min"]
    
    if filtros.get("precipitacion_max") is not None:
        where.append("pdm.precipitacion_suma <= :precipitacion_max")
        params["precipitacion_max"] = filtros["precipitacion_max"]
    
    if filtros.get("humedad_max_min") is not None:
        where.append("pdm.humedad_relativa_max >= :humedad_max_min")
        params["humedad_max_min"] = filtros["humedad_max_min"]
    
    # JOIN con municipio y comunidad si es necesario
    joins = ["JOIN shared.municipio m ON m.id = pdm.id_municipio"]
    if filtros.get("codigo_comunidad"):
        joins.append("LEFT JOIN shared.comunidades c ON c.codigo_ine = pdm.codigo_comunidad")
    
    joins_clause = " ".join(joins)
    where_clause = " AND ".join(where) if where else "TRUE"
    
    # Count total
    count_query = f"""
        SELECT COUNT(*) as total
        FROM sinb.pronostico_diario_municipal pdm
        {joins_clause}
        WHERE {where_clause}
    """
    total_result = _row(db, count_query, params)
    total = total_result["total"] if total_result else 0
    
    # Paginación
    offset = (pagina - 1) * por_pagina
    
    rows = _rows(db, f"""
        SELECT 
            pdm.id, pdm.id_municipio, pdm.fecha,
            pdm.temp_max, pdm.temp_min,
            pdm.precipitacion_suma, pdm.precipitacion_prob_max,
            pdm.humedad_relativa_max, pdm.humedad_relativa_min,
            pdm.evapotranspiracion, pdm.viento_velocidad_max, pdm.viento_direccion,
            pdm.radiacion_solar, pdm.uv_index_max,
            pdm.sunrise, pdm.sunset,
            pdm.fuente,
            m.nombre as municipio_nombre
        FROM sinb.pronostico_diario_municipal pdm
        {joins_clause}
        WHERE {where_clause}
        ORDER BY pdm.fecha DESC
        LIMIT :limit OFFSET :offset
    """, {**params, "limit": por_pagina, "offset": offset})
    
    return _serialize(rows), total


def get_pronostico_diario_consultar(
    db: Session,
    id_municipio: int,
    tipo: str = "daily"
) -> tuple[list, str, date]:
    """
    Consultar pronóstico digital almacenado (16 días desde hoy).
    
    Args:
        db: Sesión de base de datos
        id_municipio: ID del municipio
        tipo: "daily" o "hourly"
    
    Returns:
        Tupla (lista_de_registros, nombre_municipio, fecha_hoy)
    """
    fecha_hoy = _hoy_bolivia()
    fecha_fin = fecha_hoy + timedelta(days=HORIZONTE_DIAS - 1)

    rows = _rows(db, """
        SELECT 
            pdm.id, pdm.id_municipio, pdm.fecha,
            pdm.temp_max, pdm.temp_min,
            pdm.precipitacion_suma, pdm.precipitacion_prob_max,
            pdm.humedad_relativa_max, pdm.humedad_relativa_min,
            pdm.evapotranspiracion, pdm.viento_velocidad_max, pdm.viento_direccion,
            pdm.radiacion_solar, pdm.uv_index_max,
            pdm.sunrise, pdm.sunset,
            pdm.fuente,
            m.nombre as municipio_nombre
        FROM sinb.pronostico_diario_municipal pdm
        JOIN shared.municipio m ON m.id = pdm.id_municipio
        WHERE pdm.id_municipio = :id_municipio 
          AND pdm.fecha BETWEEN :fecha_hoy AND :fecha_fin
        ORDER BY pdm.fecha ASC
        LIMIT 16
    """, {"id_municipio": id_municipio, "fecha_hoy": fecha_hoy, "fecha_fin": fecha_fin})
    
    municipio_nombre = rows[0]["municipio_nombre"] if rows else None
    
    return _serialize(rows), municipio_nombre, fecha_hoy


def get_pronostico_comunidad_directo(
    db: Session,
    latitud: float,
    longitud: float,
    id_municipio: int = None
) -> tuple[list, str, date]:
    """
    Obtener pronóstico directo de Open-Meteo para una comunidad (16 días).
    No guarda en base de datos, solo retorna los datos crudos formateados.
    
    Args:
        latitud: Latitud de la comunidad
        longitud: Longitud de la comunidad
        id_municipio: ID del municipio (opcional, para obtener nombre)
    
    Returns:
        Tupla (lista_de_registros_formateados, nombre_municipio, fecha_hoy)
    """
    from datetime import date as date_type, datetime as datetime_type
    from uuid import uuid4
    
    fecha_hoy = _hoy_bolivia()
    
    datos = _con_reintentos(
        lambda: consultar_open_meteo(latitud, longitud, "daily", horizonte_dias=HORIZONTE_DIAS)
    )
    
    if "daily" not in datos:
        raise HTTPException(status_code=503, detail="Open-Meteo no devolvió datos diarios")
    
    daily = datos["daily"]
    fechas = daily.get("time", [])
    temp_max = daily.get("temperature_2m_max", [])
    temp_min = daily.get("temperature_2m_min", [])
    precip_sum = daily.get("precipitation_sum", [])
    precip_prob = daily.get("precipitation_probability_max", [])
    humedad_max = daily.get("relative_humidity_2m_max", [])
    humedad_min = daily.get("relative_humidity_2m_min", [])
    eto = daily.get("et0_fao_evapotranspiration", [])
    viento_vel = daily.get("wind_speed_10m_max", [])
    viento_dir = daily.get("wind_direction_10m_dominant", [])
    radiacion = daily.get("shortwave_radiation_sum", [])
    uv_max = daily.get("uv_index_max", [])
    sunrise_list = daily.get("sunrise", [])
    sunset_list = daily.get("sunset", [])
    
    registros = []
    
    for i, fecha_str in enumerate(fechas):
        fecha_obj = date_type.fromisoformat(fecha_str)
        
        sunrise_dt = None
        sunset_dt = None
        if i < len(sunrise_list):
            try:
                sunrise_dt = datetime_type.fromisoformat(sunrise_list[i])
            except:
                pass
        if i < len(sunset_list):
            try:
                sunset_dt = datetime_type.fromisoformat(sunset_list[i])
            except:
                pass
        
        registros.append({
            "id": str(uuid4()),
            "id_municipio": id_municipio,
            "fecha": fecha_str,
            "temp_max": temp_max[i] if i < len(temp_max) else None,
            "temp_min": temp_min[i] if i < len(temp_min) else None,
            "precipitacion_suma": precip_sum[i] if i < len(precip_sum) else None,
            "precipitacion_prob_max": precip_prob[i] if i < len(precip_prob) else None,
            "humedad_relativa_max": humedad_max[i] if i < len(humedad_max) else None,
            "humedad_relativa_min": humedad_min[i] if i < len(humedad_min) else None,
            "evapotranspiracion": eto[i] if i < len(eto) else None,
            "viento_velocidad_max": viento_vel[i] if i < len(viento_vel) else None,
            "viento_direccion": viento_dir[i] if i < len(viento_dir) else None,
            "radiacion_solar": radiacion[i] if i < len(radiacion) else None,
            "uv_index_max": uv_max[i] if i < len(uv_max) else None,
            "sunrise": sunrise_dt.isoformat() if sunrise_dt else None,
            "sunset": sunset_dt.isoformat() if sunset_dt else None,
            "fuente": "open-meteo-directo",
            "municipio_nombre": None,
            "latitud": latitud,
            "longitud": longitud
        })
    
    # Obtener nombre del municipio si tenemos id_municipio
    municipio_nombre = None
    if id_municipio:
        m = _row(db, "SELECT nombre FROM shared.municipio WHERE id = :id", {"id": id_municipio})
        if m:
            municipio_nombre = m["nombre"]
            for r in registros:
                r["municipio_nombre"] = municipio_nombre
    
    return registros, municipio_nombre, fecha_hoy


def get_pronostico_todos_municipios_16dias(
    db: Session
) -> list:
    """
    Obtener pronóstico de TODOS los municipios × 16 días.
    
    Args:
        db: Sesión de base de datos
    
    Returns:
        Lista de pronósticos (343 municipios × 16 días = 5,488 registros)
    """
    fecha_hoy = _hoy_bolivia()
    fecha_fin = fecha_hoy + timedelta(days=HORIZONTE_DIAS - 1)

    rows = _rows(db, """
        SELECT 
            pdm.id, pdm.id_municipio, pdm.fecha,
            pdm.temp_max, pdm.temp_min,
            pdm.precipitacion_suma, pdm.precipitacion_prob_max,
            pdm.humedad_relativa_max, pdm.humedad_relativa_min,
            pdm.evapotranspiracion, pdm.viento_velocidad_max, pdm.viento_direccion,
            pdm.radiacion_solar, pdm.uv_index_max,
            m.nombre as municipio_nombre,
            m.id_departamento, m.id_provincia,
            ST_Y(ST_Centroid(m.geom)) as latitud,
            ST_X(ST_Centroid(m.geom)) as longitud
        FROM sinb.pronostico_diario_municipal pdm
        JOIN shared.municipio m ON m.id = pdm.id_municipio
        WHERE pdm.fecha BETWEEN :fecha_hoy AND :fecha_fin
        ORDER BY pdm.id_municipio ASC, pdm.fecha ASC
    """, {"fecha_hoy": fecha_hoy, "fecha_fin": fecha_fin})
    
    return _serialize(rows)


def get_pronostico_todos_municipios(
    db: Session,
    fecha: date
) -> list:
    """
    Obtener pronóstico de TODOS los municipios para una fecha específica.
    
    Args:
        db: Sesión de base de datos
        fecha: Fecha a consultar
    
    Returns:
        Lista de pronósticos (uno por municipio)
    """
    rows = _rows(db, """
        SELECT 
            pdm.id, pdm.id_municipio, pdm.fecha,
            pdm.temp_max, pdm.temp_min,
            pdm.precipitacion_suma, pdm.precipitacion_prob_max,
            pdm.humedad_relativa_max, pdm.humedad_relativa_min,
            pdm.evapotranspiracion, pdm.viento_velocidad_max, pdm.viento_direccion,
            pdm.radiacion_solar, pdm.uv_index_max,
            m.nombre as municipio_nombre,
            m.id_departamento, m.id_provincia,
            ST_Y(ST_Centroid(m.geom)) as latitud,
            ST_X(ST_Centroid(m.geom)) as longitud
        FROM sinb.pronostico_diario_municipal pdm
        JOIN shared.municipio m ON m.id = pdm.id_municipio
        WHERE pdm.fecha = :fecha
        ORDER BY pdm.id_municipio ASC
    """, {"fecha": fecha})
    
    # Si no hay datos para la fecha exacta, buscar la más cercana
    if not rows:
        rows = _rows(db, """
            SELECT 
                pdm.id, pdm.id_municipio, pdm.fecha,
                pdm.temp_max, pdm.temp_min,
                pdm.precipitacion_suma, pdm.precipitacion_prob_max,
                pdm.humedad_relativa_max, pdm.humedad_relativa_min,
                pdm.evapotranspiracion, pdm.viento_velocidad_max, pdm.viento_direccion,
                pdm.radiacion_solar, pdm.uv_index_max,
                m.nombre as municipio_nombre,
                m.id_departamento, m.id_provincia,
                ST_Y(ST_Centroid(m.geom)) as latitud,
                ST_X(ST_Centroid(m.geom)) as longitud
            FROM sinb.pronostico_diario_municipal pdm
            JOIN shared.municipio m ON m.id = pdm.id_municipio
            WHERE pdm.fecha >= :fecha
            ORDER BY pdm.fecha ASC, pdm.id_municipio ASC
            LIMIT 343
        """, {"fecha": fecha})
    
    return _serialize(rows)


def guardar_pronostico_hourly_cache(
    db: Session,
    latitud: float,
    longitud: float,
    datos: dict,
    id_municipio: int = None
) -> dict:
    """
    Guardar pronóstico hourly en caché (on-demand).
    
    Args:
        db: Sesión de base de datos
        latitud: Latitud del punto
        longitud: Longitud del punto
        datos: Datos crudos de Open-Meteo (hourly)
        id_municipio: ID de municipio (opcional)
    
    Returns:
        Cantidad de registros guardados
    """
    hourly = datos.get("hourly", {})
    fechas = hourly.get("time", [])
    
    # Mapa de variables disponibles
    variables_map = {
        "temperature_2m": ("Temperatura", "°C"),
        "precipitation_probability": ("Probabilidad Precipitación", "%"),
        "relative_humidity_2m": ("Humedad Relativa", "%"),
        "wind_speed_10m": ("Velocidad Viento", "km/h")
    }
    
    registros_guardados = 0
    
    for var_nombre, (var_desc, var_unidad) in variables_map.items():
        if var_nombre not in hourly:
            continue
        
        # Obtener o crear variable climática
        var_climatica = _row(db, """
            SELECT id FROM sinb.variable_climatica WHERE codigo = :codigo
        """, {"codigo": var_nombre})
        
        if not var_climatica:
            # Crear variable si no existe
            var_climatica = _row(db, """
                INSERT INTO sinb.variable_climatica (codigo, nombre, unidad, estado)
                VALUES (:codigo, :nombre, :unidad, 'ACTIVO')
                RETURNING id
            """, {
                "codigo": var_nombre,
                "nombre": var_desc,
                "unidad": var_unidad
            })
        
        id_variable = var_climatica["id"]
        valores = hourly[var_nombre]
        
        for i, fecha_hora_str in enumerate(fechas):
            fecha_hora = fecha_hora_str.replace("T", " ")
            valor = valores[i] if i < len(valores) else None
            
            # Upsert
            _execute(db, """
                INSERT INTO sinb.pronostico_hourly_punto
                (latitud, longitud, fecha_hora, id_variable_climatica, valor, unidad, id_municipio)
                VALUES (:lat, :lon, :fecha, :id_var, :valor, :unidad, :id_mun)
                ON CONFLICT (latitud, longitud, fecha_hora, id_variable_climatica)
                DO UPDATE SET valor = :valor, expira_en = now() + INTERVAL '24 hours'
            """, {
                "lat": latitud,
                "lon": longitud,
                "fecha": fecha_hora,
                "id_var": id_variable,
                "valor": valor,
                "unidad": var_unidad,
                "id_mun": id_municipio
            })
            
            registros_guardados += 1
    
    return {"registros_guardados": registros_guardados}


def get_pronostico_hourly_punto(
    db: Session,
    latitud: float,
    longitud: float,
    fecha_desde: datetime = None,
    fecha_hasta: datetime = None
) -> list:
    """Obtener pronóstico hourly por punto."""
    where = ["latitud = :lat AND longitud = :lon AND expira_en > now()"]
    params = {"lat": latitud, "lon": longitud}
    
    if fecha_desde:
        where.append("fecha_hora >= :fecha_desde")
        params["fecha_desde"] = fecha_desde
    
    if fecha_hasta:
        where.append("fecha_hora <= :fecha_hasta")
        params["fecha_hasta"] = fecha_hasta
    
    where_clause = " AND ".join(where)
    
    rows = _rows(db, f"""
        SELECT php.*, vc.nombre as variable_nombre
        FROM sinb.pronostico_hourly_punto php
        LEFT JOIN sinb.variable_climatica vc ON vc.id = php.id_variable_climatica
        WHERE {where_clause}
        ORDER BY php.fecha_hora
    """, params)
    
    return _serialize(rows)


def get_pronosticos_diarios_filtrados(
    db: Session,
    id_departamento: int = None,
    id_provincia: int = None,
    id_municipio: int = None,
    fecha_desde: date = None,
    fecha_hasta: date = None,
    skip: int = 0,
    limit: int = 100,
    todos: bool = False
) -> tuple:
    """
    Obtener pronósticos diarios con filtros geográficos.
    
    Args:
        db: Sesión de base de datos
        id_departamento: Filtrar por departamento
        id_provincia: Filtrar por provincia
        id_municipio: Filtrar por municipio
        fecha_desde: Fecha mínima
        fecha_hasta: Fecha máxima
        skip: Saltar registros (paginación)
        limit: Límite de registros
        todos: True = conjunto completo sin LIMIT/OFFSET
    
    Returns:
        Tupla (datos, total)
    """
    where = ["pdm.fecha >= CURRENT_DATE"]  # Solo pronósticos futuros
    params = {"skip": skip, "limit": limit}
    
    if id_departamento:
        where.append("d.id = :id_departamento")
        params["id_departamento"] = id_departamento
    
    if id_provincia:
        where.append("p.id = :id_provincia")
        params["id_provincia"] = id_provincia
    
    if id_municipio:
        where.append("m.id = :id_municipio")
        params["id_municipio"] = id_municipio
    
    if fecha_desde:
        where.append("pdm.fecha >= :fecha_desde")
        params["fecha_desde"] = fecha_desde
    
    if fecha_hasta:
        where.append("pdm.fecha <= :fecha_hasta")
        params["fecha_hasta"] = fecha_hasta
    else:
        # Sin fecha hasta: horizonte exacto de 16 días (hoy..hoy+15), para que el
        # "16 días" no dependa de cuántas filas dejó la última corrida del cron.
        where.append("pdm.fecha <= CURRENT_DATE + (:horizonte - 1) * interval '1 day'")
        params["horizonte"] = HORIZONTE_DIAS
    
    where_clause = " AND ".join(where)
    
    # cantidad → paginación; todos=True → sin LIMIT/OFFSET
    page = "" if todos else " LIMIT :limit OFFSET :skip"
    query_params = params if not todos else {
        k: v for k, v in params.items() if k not in ("limit", "skip")}

    # Consulta con joins geográficos
    rows = _rows(db, f"""
        SELECT pdm.*, 
               m.nombre as municipio_nombre,
               p.nombre as provincia_nombre,
               d.nombre as departamento_nombre
        FROM sinb.pronostico_diario_municipal pdm
        JOIN shared.municipio m ON m.id = pdm.id_municipio
        JOIN shared.provincia p ON p.id = m.id_provincia
        JOIN shared.departamento d ON d.id = m.id_departamento
        WHERE {where_clause}
        ORDER BY pdm.fecha DESC, pdm.id_municipio
        {page}
    """, query_params)
    
    # Total
    total = _row(db, f"""
        SELECT COUNT(DISTINCT pdm.id) as total
        FROM sinb.pronostico_diario_municipal pdm
        JOIN shared.municipio m ON m.id = pdm.id_municipio
        JOIN shared.provincia p ON p.id = m.id_provincia
        JOIN shared.departamento d ON d.id = m.id_departamento
        WHERE {where_clause}
    """, {k: v for k, v in params.items() if k not in ['limit', 'skip']})['total']
    
    return _serialize(rows), total


def get_pronosticos_por_departamento(
    db: Session,
    id_departamento: int,
    fecha: date = None
) -> list:
    """
    Obtener pronósticos agrupados por departamento.
    
    Args:
        db: Sesión de base de datos
        id_departamento: ID del departamento
        fecha: Fecha específica (hoy por defecto)
    
    Returns:
        Lista de pronósticos con promedios por municipio
    """
    from datetime import date as date_type
    if fecha is None:
        fecha = _hoy_bolivia()
    
    rows = _rows(db, """
        SELECT 
            d.id as id_departamento,
            d.nombre as departamento,
            m.id as id_municipio,
            m.nombre as municipio,
            AVG(pdm.temp_max) as temp_max_promedio,
            AVG(pdm.temp_min) as temp_min_promedio,
            SUM(pdm.precipitacion_suma) as precipitacion_total,
            AVG(pdm.precipitacion_prob_max) as prob_max_promedio,
            pdm.fecha
        FROM sinb.pronostico_diario_municipal pdm
        JOIN shared.municipio m ON m.id = pdm.id_municipio
        JOIN shared.provincia p ON p.id = m.id_provincia
        JOIN shared.departamento d ON d.id = m.id_departamento
        WHERE d.id = :id_departamento 
          AND pdm.fecha = :fecha
        GROUP BY d.id, d.nombre, m.id, m.nombre, pdm.fecha
        ORDER BY m.nombre
    """, {"id_departamento": id_departamento, "fecha": fecha})
    
    return _serialize(rows)


def get_centroide_municipio(db: Session, id_municipio: int) -> dict:
    """
    Obtener latitud/longitud del centroide de un municipio.
    
    Args:
        db: Sesión de base de datos
        id_municipio: ID del municipio
    
    Returns:
        Dict con latitud, longitud, nombre del municipio
    """
    result = _row(db, """
        SELECT 
            m.id,
            m.nombre,
            ST_Y(ST_Centroid(m.geom)) as latitud,
            ST_X(ST_Centroid(m.geom)) as longitud
        FROM shared.municipio m
        WHERE m.id = :id_municipio AND m.geom IS NOT NULL
    """, {"id_municipio": id_municipio})
    
    return _serialize(result)


def get_centroides_municipios_por_departamento(
    db: Session,
    id_departamento: int
) -> list:
    """
    Obtener centroides de todos los municipios de un departamento.
    
    Args:
        db: Sesión de base de datos
        id_departamento: ID del departamento
    
    Returns:
        Lista de municipios con sus centroides
    """
    rows = _rows(db, """
        SELECT 
            m.id,
            m.nombre,
            m.codigo_ine,
            ST_Y(ST_Centroid(m.geom)) as latitud,
            ST_X(ST_Centroid(m.geom)) as longitud
        FROM shared.municipio m
        WHERE m.id_departamento = :id_departamento 
          AND m.geom IS NOT NULL
        ORDER BY m.nombre
    """, {"id_departamento": id_departamento})
    
    return _serialize(rows)



# ============================================================================
# FOTOS DE INDICADOR NATURAL (1:N con sinb.indicador_natural)
# ============================================================================

_FOTO_SELECT = """
    SELECT f.id,
           f.id_indicador_natural,
           f.path_foto,
           f.path_foto as url_descarga,
           f.descripcion,
           f.id_usuario_subio,
           f.creado_en,
           f.actualizado_en,
           jsonb_build_object(
               'id', u.id_usuario,
               'nombre', u.nombre,
               'usuario', u.usuario,
               'id_rol', u.id_rol
           ) as usuario
    FROM sinb.indicador_foto f
    JOIN usuarios.usuario u ON u.id_usuario = f.id_usuario_subio
"""


def get_fotos_indicador(db: Session, id_indicador_natural: UUID,
                        limit: int | None = None, skip: int = 0, todos: bool = False) -> tuple[list, int]:
    """Listar fotos de un indicador natural, mas recientes primero.

    Devuelve (filas, total sin paginar).
    """
    total = _row(db, """
        SELECT COUNT(*) AS total FROM sinb.indicador_foto WHERE id_indicador_natural = :id
    """, {"id": id_indicador_natural})["total"]
    page, page_params = pagina_limit_offset(limit, skip, todos)
    rows = _rows(db, _FOTO_SELECT + """
        WHERE f.id_indicador_natural = :id
        ORDER BY f.creado_en DESC
    """ + page, {"id": id_indicador_natural, **page_params})
    return _serialize(rows), total


def get_foto_indicador(db: Session, id_foto: UUID):
    """Obtener una foto por su id (incluye usuario propietario)."""
    row = _row(db, _FOTO_SELECT + """
        WHERE f.id = :id
    """, {"id": id_foto})
    return dict(row) if row else None


def create_foto_indicador(db: Session, id_indicador_natural: UUID, path_foto: str,
                          descripcion: str, id_usuario_subio: int) -> dict:
    """Insertar una foto de indicador natural."""
    result = db.execute(text("""
        INSERT INTO sinb.indicador_foto
            (id_indicador_natural, path_foto, descripcion, id_usuario_subio)
        VALUES
            (:id_indicador_natural, :path_foto, :descripcion, :id_usuario_subio)
        RETURNING *
    """), {
        "id_indicador_natural": id_indicador_natural,
        "path_foto": path_foto,
        "descripcion": descripcion,
        "id_usuario_subio": id_usuario_subio,
    })
    db.commit()
    return dict(result.mappings().first())


def update_foto_indicador(db: Session, id_foto: UUID, descripcion: str) -> dict:
    """Actualizar la descripcion de una foto."""
    result = db.execute(text("""
        UPDATE sinb.indicador_foto
           SET descripcion = :descripcion,
               actualizado_en = now()
         WHERE id = :id
        RETURNING *
    """), {"id": id_foto, "descripcion": descripcion})
    db.commit()
    row = result.mappings().first()
    return dict(row) if row else None


def delete_foto_indicador(db: Session, id_foto: UUID, id_usuario: int | None = None) -> bool:
    """Eliminar fisicamente la fila de la foto (con tombstone; el archivo lo borra el router)."""
    fila = _row(db, "SELECT id, path_foto FROM sinb.indicador_foto WHERE id = :id", {"id": id_foto})
    if not fila:
        return False
    _registrar_borrado(db, "indicador_foto", fila, id_usuario)
    db.execute(text("DELETE FROM sinb.indicador_foto WHERE id = :id"), {"id": id_foto})
    db.commit()
    return True


def delete_aviso(db: Session, id: UUID, id_usuario: int | None = None):
    """Eliminar aviso definitivamente (borrado físico + registro de borrado)."""
    return _borrar_fisico(db, "avisos", id, id_usuario, "el aviso")


# ============================================================================
# AVISOS: DETALLE Y ACTUALIZACIÓN
# ============================================================================

def get_aviso(db: Session, id: UUID):
    """Obtener un aviso por ID con categoría, municipio y emisor."""
    return _row(db, """
        SELECT a.*, cp.nombre as categoria_nombre, m.nombre as municipio_nombre,
               u.nombre as emisor_nombre
        FROM sinb.avisos a
        LEFT JOIN sinb.categoria_pronostico cp ON cp.id = a.id_categoria
        LEFT JOIN shared.municipio m ON m.id = a.id_municipio
        LEFT JOIN usuarios.usuario u ON u.id_usuario = a.id_usuario_subio
        WHERE a.id = :id
    """, {"id": id})


def update_aviso(db: Session, id: UUID, data: dict):
    """Actualizar mensaje, vigencia o estado de un aviso.

    Si cambia `vigencia_horas` se recalcula `fecha_vencimiento` desde la
    fecha de emisión (constraint chk_vigencia exige vencimiento > emisión).
    """
    aviso = _row(db, "SELECT fecha_emision FROM sinb.avisos WHERE id = :id", {"id": id})
    if not aviso:
        return None

    params = {
        "id": id,
        "mensaje": data.get("mensaje"),
        "vigencia_horas": data.get("vigencia_horas"),
        "estado": data.get("estado"),
        "fecha_vencimiento": None,
    }
    if data.get("vigencia_horas") is not None and aviso["fecha_emision"]:
        params["fecha_vencimiento"] = aviso["fecha_emision"] + timedelta(hours=data["vigencia_horas"])

    result = db.execute(text("""
        UPDATE sinb.avisos SET
            mensaje = COALESCE(:mensaje, mensaje),
            vigencia_horas = COALESCE(:vigencia_horas, vigencia_horas),
            estado = COALESCE(:estado, estado),
            fecha_vencimiento = COALESCE(:fecha_vencimiento, fecha_vencimiento)
        WHERE id = :id
        RETURNING *
    """), params)
    db.commit()
    row = result.mappings().first()
    return dict(row) if row else None


# ============================================================================
# OBSERVADOR ÍNDICE: DETALLE, ACTUALIZACIÓN Y BORRADO
# ============================================================================

def get_observador_indice(db: Session, id: UUID):
    """Obtener un registro de observador índice por ID."""
    return _row(db, """
        SELECT oi.*, u.nombre as usuario_nombre,
               i.nombre_cientifico as indicador_nombre
        FROM sinb.observador_indice oi
        JOIN usuarios.usuario u ON u.id_usuario = oi.id_usuario
        LEFT JOIN sinb.indicador_natural i ON i.id = oi.id_indicador_natural
        WHERE oi.id = :id
    """, {"id": id})


def update_observador_indice(db: Session, id: UUID, data: dict):
    """Actualizar valor y fecha de cálculo de un índice."""
    result = db.execute(text("""
        UPDATE sinb.observador_indice SET
            valor = COALESCE(:valor, valor),
            fecha_calculo = COALESCE(:fecha_calculo, fecha_calculo)
        WHERE id = :id
        RETURNING *
    """), {
        "id": id,
        "valor": data.get("valor"),
        "fecha_calculo": data.get("fecha_calculo"),
    })
    db.commit()
    row = result.mappings().first()
    return dict(row) if row else None


def delete_observador_indice(db: Session, id: UUID, id_usuario: int | None = None) -> bool:
    """Eliminar un registro de observador índice (físico + tombstone)."""
    fila = _row(db, "SELECT id FROM sinb.observador_indice WHERE id = :id", {"id": id})
    if not fila:
        return False
    _registrar_borrado(db, "observador_indice", fila, id_usuario)
    db.execute(text("DELETE FROM sinb.observador_indice WHERE id = :id"), {"id": id})
    db.commit()
    return True


# ============================================================================
# PRONÓSTICO LARGO: ESCENARIOS Y OBSERVADORES
# ============================================================================

def update_escenario_en_pronostico(db: Session, id_pronostico: UUID, id_item: UUID,
                                   id_escenario: UUID, confianza: str | None = None):
    """Actualizar la confianza (ALTA|MEDIA|BAJA) de un escenario ya asignado a un bloque."""
    item = _item_pertenece_al_pronostico(db, id_pronostico, id_item)
    _validar_escenarios_de_item(
        db, item["id_categoria"], [{"id_escenario": id_escenario, "confianza": confianza}]
    )
    result = _row(db, """
        UPDATE sinb.escenario_estacional
           SET confianza = CAST(:confianza AS sinb.confianza_nivel)
         WHERE id_pronostico_largo_item = :id_item AND id_escenario = :id_escenario
        RETURNING *
    """, {"id_item": id_item, "id_escenario": id_escenario, "confianza": confianza})
    db.commit()
    return result


def get_observadores_de_pronostico(db: Session, id_pronostico: UUID, tipo_pronostico: str,
                                   limit: int | None = None, skip: int = 0, todos: bool = False):
    """Listar los observadores asignados a un pronóstico (estacional o temporal)."""
    tipo_pronostico = _norm_tipo_pronostico(tipo_pronostico)
    if tipo_pronostico == "largo":
        tabla_pron, tabla, columna = "sinb.pronostico_largo", "sinb.pronostico_largo_observador", "id_pronostico_largo"
    else:
        tabla_pron, tabla, columna = "sinb.pronostico_corto", "sinb.pronostico_corto_observador", "id_pronostico_corto"

    existe = _row(db, f"SELECT 1 FROM {tabla_pron} WHERE id = :id", {"id": id_pronostico})
    if not existe:
        raise HTTPException(status_code=404, detail="Pronóstico no encontrado")

    # El pronóstico largo no almacena confianza por observador → se devuelve NULL
    # para que la respuesta tenga la misma forma en estacional y temporal.
    # La confianza del temporal viene del enum; el id_observador_off sólo existe en
    # la tabla de largo → NULL en temporal, misma forma en ambos casos.
    select_confianza = "NULL::text" if tipo_pronostico == "largo" else "po.confianza"
    select_off = "po.id_observador_off" if tipo_pronostico == "largo" else "NULL::varchar"
    total = _row(db, f"""
        SELECT COUNT(*) AS total FROM {tabla} po WHERE po.{columna} = :id
    """, {"id": id_pronostico})["total"]
    page, page_params = pagina_limit_offset(limit, skip, todos)
    rows = _rows(db, f"""
        SELECT po.{columna} as id_pronostico, po.id_usuario,
               {select_confianza} as confianza,
               po.fecha_asignacion, {select_off} as id_observador_off,
               u.nombre as usuario_nombre, u.id_rol, u.id_municipio
        FROM {tabla} po
        JOIN usuarios.usuario u ON u.id_usuario = po.id_usuario
        WHERE po.{columna} = :id
        ORDER BY po.fecha_asignacion DESC
        {page}
    """, {"id": id_pronostico, **page_params})
    return rows, total


# ============================================================================
# REPORTE: PRONÓSTICOS CON ESTADO DE VERIFICACIÓN
# ============================================================================

def get_reporte_pronosticos_resumen(db: Session):
    """Reporte de pronósticos con estado de verificación.

    Devuelve totales por tipo (largo/corto), conteo por estado y el
    desglose de verificaciones (coinciden / no coinciden / pendientes).
    """
    # El borrado de pronósticos es físico (no existe el valor 'ELIMINADO' en el
    # enum sinb.estado_validacion), por eso se cuentan todas las filas.
    totales = _row(db, """
        SELECT
            (SELECT COUNT(*) FROM sinb.pronostico_largo) as total_largo,
            (SELECT COUNT(*) FROM sinb.pronostico_corto) as total_corto
    """, {}) or {"total_largo": 0, "total_corto": 0}

    por_estado = _rows(db, """
        SELECT estado, COUNT(*) as cantidad FROM (
            SELECT estado FROM sinb.pronostico_largo
            UNION ALL
            SELECT estado FROM sinb.pronostico_corto
        ) t
        GROUP BY estado
        ORDER BY cantidad DESC
    """, {})

    verificaciones = _row(db, """
        SELECT
            COUNT(*) FILTER (WHERE estado = 'COINCIDE') as coinciden,
            COUNT(*) FILTER (WHERE estado = 'NO_COINCIDE') as no_coinciden,
            COUNT(*) FILTER (WHERE estado IN ('PENDIENTE', 'EN_VERIFICACION',
                                              'SIN_DATOS', 'NO_VERIFICABLE')) as pendientes,
            COUNT(*) as total
        FROM sinb.verificacion_pronostico
    """, {}) or {"coinciden": 0, "no_coinciden": 0, "pendientes": 0, "total": 0}

    total_largo = int(totales["total_largo"])
    total_corto = int(totales["total_corto"])
    return {
        "total_pronosticos": total_largo + total_corto,
        "total_largo": total_largo,
        "total_corto": total_corto,
        "por_estado": por_estado,
        "verificaciones_total": int(verificaciones["total"]),
        "verificaciones_pendientes": int(verificaciones["pendientes"]),
        "verificaciones_coinciden": int(verificaciones["coinciden"]),
        "verificaciones_no_coinciden": int(verificaciones["no_coinciden"]),
    }
