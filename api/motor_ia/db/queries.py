from .connection import execute_query, get_connection
from psycopg2.extras import RealDictCursor


def crear_documento(titulo, tipo_id, fecha_publicacion, archivo_path, contenido_completo, num_paginas=None, metadatos=None):
    import json
    if metadatos is not None:
        metadatos = json.dumps(metadatos, ensure_ascii=False)
    query = """
        INSERT INTO documentos (titulo, tipo_id, fecha_publicacion, archivo_path, contenido_completo, num_paginas, metadatos)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    result = execute_query(query, (titulo, tipo_id, fecha_publicacion, archivo_path, contenido_completo, num_paginas, metadatos), fetch=True)
    return result[0]["id"]


def eliminar_documento(documento_id):
    execute_query("DELETE FROM documentos WHERE id = %s", (documento_id,), fetch=False)


def listar_documentos():
    query = """
        SELECT d.id, d.titulo, d.tipo_id, t.nombre as tipo_nombre, t.prioridad,
               d.fecha_publicacion, d.num_paginas, d.creado_en,
               (SELECT COUNT(*) FROM chunks c WHERE c.documento_id = d.id) as total_chunks
        FROM documentos d
        JOIN tipos_documento t ON d.tipo_id = t.id
        ORDER BY d.creado_en DESC
    """
    return execute_query(query)


def listar_documentos_filtrados(
    tipo_id=None,
    q=None,
    orden="creado_en",
    direccion="desc",
    limit=100,
    skip=0,
    todos=False,
    creado_desde=None,
    creado_hasta=None,
):
    order_map = {
        "titulo": "d.titulo",
        "fecha": "d.fecha_publicacion",
        "creado_en": "d.creado_en",
        "chunks": "total_chunks",
        "prioridad": "t.prioridad",
    }
    direction = "ASC" if str(direccion).lower() == "asc" else "DESC"
    order_by = order_map.get(orden, "d.creado_en")

    query = """
        SELECT d.id, d.titulo, d.tipo_id, t.nombre as tipo_nombre, t.prioridad,
               d.fecha_publicacion, d.num_paginas, d.creado_en,
               (SELECT COUNT(*) FROM chunks c WHERE c.documento_id = d.id) as total_chunks
        FROM documentos d
        JOIN tipos_documento t ON d.tipo_id = t.id
    """
    clauses = []
    params = []

    if tipo_id:
        clauses.append("d.tipo_id = %s")
        params.append(tipo_id)

    if q:
        clauses.append("LOWER(d.titulo) LIKE %s")
        params.append(f"%{q.strip().lower()}%")

    if creado_desde:
        clauses.append("d.creado_en >= %s")
        params.append(creado_desde)

    if creado_hasta:
        clauses.append("d.creado_en < %s::date + interval '1 day'")
        params.append(creado_hasta)

    if clauses:
        where = " WHERE " + " AND ".join(clauses)
        query += where
        count_query = """
            SELECT COUNT(*) as total
            FROM documentos d
            JOIN tipos_documento t ON d.tipo_id = t.id
        """ + where
    else:
        count_query = "SELECT COUNT(*) as total FROM documentos"

    query += f" ORDER BY {order_by} {direction}, d.id DESC"
    if not todos:
        query += " LIMIT %s OFFSET %s"
        params_page = tuple(params + [limit, skip])
    else:
        params_page = tuple(params) if params else None

    docs = execute_query(query, params_page)
    total = execute_query(count_query, tuple(params) if params else None)[0]["total"]
    return docs, total


def listar_contenidos_documentos():
    query = """
        SELECT d.id, d.titulo, d.tipo_id, t.nombre as tipo_nombre, t.prioridad,
               d.contenido_completo
        FROM documentos d
        JOIN tipos_documento t ON d.tipo_id = t.id
        ORDER BY d.creado_en DESC
    """
    return execute_query(query)


def obtener_documento(documento_id):
    query = "SELECT * FROM documentos WHERE id = %s"
    result = execute_query(query, (documento_id,))
    return result[0] if result else None


def insertar_chunk(documento_id, contenido, numeral, orden, embedding):
    import numpy as np
    embedding_str = "[" + ",".join(str(float(x)) for x in embedding) + "]"
    query = """
        INSERT INTO chunks (documento_id, contenido, numeral, orden, embedding)
        VALUES (%s, %s, %s, %s, %s::vector)
        RETURNING id
    """
    result = execute_query(query, (documento_id, contenido, numeral, orden, embedding_str), fetch=True)
    return result[0]["id"]


def buscar_chunks_similares(embedding, limite=10, tipo_id=None):
    import numpy as np
    embedding_str = "[" + ",".join(str(float(x)) for x in embedding) + "]"

    if tipo_id:
        query = """
            SELECT c.id, c.documento_id, c.contenido, c.numeral, c.orden,
                   d.titulo, d.tipo_id, t.nombre as tipo_nombre, t.prioridad,
                   1 - (c.embedding <=> %s::vector) as similitud
            FROM chunks c
            JOIN documentos d ON c.documento_id = d.id
            JOIN tipos_documento t ON d.tipo_id = t.id
            WHERE d.tipo_id = %s
            ORDER BY c.embedding <=> %s::vector
            LIMIT %s
        """
        return execute_query(query, (embedding_str, tipo_id, embedding_str, limite))
    else:
        query = """
            SELECT c.id, c.documento_id, c.contenido, c.numeral, c.orden,
                   d.titulo, d.tipo_id, t.nombre as tipo_nombre, t.prioridad,
                   1 - (c.embedding <=> %s::vector) as similitud
            FROM chunks c
            JOIN documentos d ON c.documento_id = d.id
            JOIN tipos_documento t ON d.tipo_id = t.id
            ORDER BY c.embedding <=> %s::vector
            LIMIT %s
        """
        return execute_query(query, (embedding_str, embedding_str, limite))


_ACCENT_FROM = "áéíóúüñàèìòùâêîôûäëïöç"
_ACCENT_TO = "aeiouunaeiouaeiouaeioc"


def _accent_folded(expr):
    return f"translate(LOWER({expr}), '{_ACCENT_FROM}', '{_ACCENT_TO}')"


def _normalizar_ids_documento(documento_id, documento_ids):
    """Combina documento_id y documento_ids en una lista unica (deduplicada)."""
    ids = list(documento_ids) if documento_ids else []
    if documento_id and documento_id not in ids:
        ids.append(documento_id)
    return ids or None


def buscar_por_texto(keywords, limite=15, tipo_id=None, documento_id=None, documento_ids=None, chunk_ids=None):
    keywords = [k for k in keywords if k]
    if not keywords:
        return []

    condiciones = " OR ".join(
        _accent_folded("c.contenido") + " LIKE %s" for _ in keywords
    )
    sumas = " + ".join(
        f"(CASE WHEN {_accent_folded('c.contenido')} LIKE %s THEN 1 ELSE 0 END)"
        for _ in keywords
    )

    query = f"""
        SELECT c.id, c.documento_id, c.contenido, c.numeral, c.orden,
               d.titulo, d.tipo_id, t.nombre as tipo_nombre, t.prioridad,
               ({sumas})::float / {len(keywords)} as similitud
        FROM chunks c
        JOIN documentos d ON c.documento_id = d.id
        JOIN tipos_documento t ON d.tipo_id = t.id
        WHERE ({condiciones})
    """
    params = [f"%{k}%" for k in keywords]

    ids = _normalizar_ids_documento(documento_id, documento_ids)
    if ids:
        query += " AND c.documento_id = ANY(%s)"
        params.append(ids)
    elif tipo_id:
        query += " AND d.tipo_id = %s"
        params.append(tipo_id)

    if chunk_ids:
        query += " AND c.id = ANY(%s)"
        params.append(list(chunk_ids))

    query += " ORDER BY similitud DESC, c.orden ASC LIMIT %s"
    params.append(limite)

    patrones = [f"%{k}%" for k in keywords]
    params = patrones + patrones + params[len(patrones):]

    return execute_query(query, tuple(params))


def buscar_chunks_por_termino(keywords, documento_ids, limite=50, exigir_todos=True):
    """Chunks de una seccion dentro de un conjunto de documentos.

    Se usa para acotar la busqueda a la seccion EDAN actual (el campo `termino`
    de /chat). Con `exigir_todos=True` exige que el chunk contenga TODAS las
    palabras del termino (preciso); con `exigir_todos=False` exige al menos la
    mitad (tolerante a variaciones de redaccion).
    """
    keywords = [k for k in keywords if k]
    if not keywords or not documento_ids:
        return []

    ids_param = [list(documento_ids)]
    patrones = [f"%{k}%" for k in keywords]

    if exigir_todos:
        condicion = " AND ".join(_accent_folded("c.contenido") + " LIKE %s" for _ in keywords)
        params = ids_param + patrones + [limite]
    else:
        sumas = " + ".join(
            f"(CASE WHEN {_accent_folded('c.contenido')} LIKE %s THEN 1 ELSE 0 END)"
            for _ in keywords
        )
        minimo = max(1, (len(keywords) + 1) // 2)
        condicion = f"({sumas}) >= %s"
        params = ids_param + patrones + [minimo, limite]

    query = f"""
        SELECT c.id, c.documento_id, c.contenido, c.numeral, c.orden,
               d.titulo, d.tipo_id, t.nombre as tipo_nombre, t.prioridad
        FROM chunks c
        JOIN documentos d ON c.documento_id = d.id
        JOIN tipos_documento t ON d.tipo_id = t.id
        WHERE c.documento_id = ANY(%s)
          AND {condicion}
        ORDER BY c.orden
        LIMIT %s
    """
    return execute_query(query, tuple(params))


def buscar_por_tipo(embedding_str, tipo_id, umbral=0.75, documento_id=None, documento_ids=None, chunk_ids=None):
    query = """
        SELECT c.id, c.documento_id, c.contenido, c.numeral, c.orden,
               d.titulo, d.tipo_id, t.nombre as tipo_nombre, t.prioridad,
               1 - (c.embedding <=> %s::vector) as similitud
        FROM chunks c
        JOIN documentos d ON c.documento_id = d.id
        JOIN tipos_documento t ON d.tipo_id = t.id
        WHERE d.tipo_id = %s
          AND (1 - (c.embedding <=> %s::vector)) > %s
    """
    params = [embedding_str, tipo_id, embedding_str, umbral]
    ids = _normalizar_ids_documento(documento_id, documento_ids)
    if ids:
        query += " AND c.documento_id = ANY(%s)"
        params.append(ids)
    if chunk_ids:
        query += " AND c.id = ANY(%s)"
        params.append(list(chunk_ids))
    query += " ORDER BY similitud DESC"
    return execute_query(query, tuple(params))


def listar_tipos_por_documentos(documento_ids):
    """Tipos (distintos) de un conjunto de documentos, para buscar por vector."""
    ids = list(documento_ids) if documento_ids else []
    if not ids:
        return []
    query = "SELECT DISTINCT tipo_id FROM documentos WHERE id = ANY(%s)"
    result = execute_query(query, (ids,))
    return [r["tipo_id"] for r in result]


def listar_tipos_documento():
    query = "SELECT id, nombre, prioridad FROM tipos_documento WHERE activo = TRUE ORDER BY prioridad"
    return execute_query(query)


def listar_tipos_documento_todos():
    query = "SELECT id, nombre, prioridad, activo FROM tipos_documento ORDER BY prioridad"
    return execute_query(query)


def obtener_tipo_documento(tipo_id):
    query = "SELECT * FROM tipos_documento WHERE id = %s"
    result = execute_query(query, (tipo_id,))
    return result[0] if result else None


def crear_tipo_documento(nombre, prioridad):
    query = """
        INSERT INTO tipos_documento (nombre, prioridad)
        VALUES (%s, %s)
        RETURNING id
    """
    result = execute_query(query, (nombre, prioridad), fetch=True)
    return result[0]["id"]


def actualizar_tipo_documento(tipo_id, nombre, prioridad, activo):
    query = """
        UPDATE tipos_documento SET nombre = %s, prioridad = %s, activo = %s
        WHERE id = %s
    """
    execute_query(query, (nombre, prioridad, activo, tipo_id), fetch=False)


def eliminar_tipo_documento(tipo_id):
    execute_query("DELETE FROM tipos_documento WHERE id = %s", (tipo_id,), fetch=False)


def contar_documentos_por_tipo(tipo_id):
    query = "SELECT COUNT(*) as total FROM documentos WHERE tipo_id = %s"
    result = execute_query(query, (tipo_id,))
    return result[0]["total"] if result else 0


def actualizar_documento(documento_id, titulo, tipo_id, fecha_publicacion):
    query = """
        UPDATE documentos SET titulo = %s, tipo_id = %s, fecha_publicacion = %s
        WHERE id = %s
    """
    execute_query(query, (titulo, tipo_id, fecha_publicacion, documento_id), fetch=False)


def listar_chunks_documento(documento_id):
    query = """
        SELECT c.id, c.numeral, c.orden, c.contenido
        FROM chunks c
        WHERE c.documento_id = %s
        ORDER BY c.orden
    """
    return execute_query(query, (documento_id,))


def listar_chunks_documento_paginado(documento_id, q=None, limit=100, skip=0, todos=False):
    select = """
        SELECT c.id, c.documento_id, c.numeral, c.orden, c.contenido
        FROM chunks c
        WHERE c.documento_id = %s
    """
    params = [documento_id]

    if q:
        select += " AND LOWER(c.contenido) LIKE %s"
        params.append(f"%{q.strip().lower()}%")

    count_select = "SELECT COUNT(*) as total FROM chunks c WHERE c.documento_id = %s"
    count_params = [documento_id]
    if q:
        count_select += " AND LOWER(c.contenido) LIKE %s"
        count_params.append(f"%{q.strip().lower()}%")

    select += " ORDER BY c.orden ASC, c.id ASC"
    if not todos:
        select += " LIMIT %s OFFSET %s"
        params.extend([limit, skip])

    rows = execute_query(select, tuple(params))
    total = execute_query(count_select, tuple(count_params))[0]["total"]
    return rows, total


def contar_chunks_documento(documento_id):
    query = "SELECT COUNT(*) as total FROM chunks WHERE documento_id = %s"
    result = execute_query(query, (documento_id,))
    return result[0]["total"] if result else 0


def borrar_chunks_documento(documento_id):
    """Elimina todos los chunks de un documento (para re-chunking)."""
    execute_query("DELETE FROM chunks WHERE documento_id = %s", (documento_id,), fetch=False)


# --- Proveedores de LLM externos ---


def listar_proveedores_llm(q=None, estado_manual=None, estado_modelo=None, limit=100, skip=0, todos=False):
    select = """
        SELECT id, nombre, base_url, modelo_base, razonamiento_tokens,
               estado_manual, estado_modelo, ultima_verificacion, fecha_creacion,
               (apikey IS NOT NULL AND apikey != '') AS apikey_configurada
        FROM proveedores_llm
    """
    clauses = []
    params = []

    if q:
        like = f"%{q.strip().lower()}%"
        clauses.append("(LOWER(nombre) LIKE %s OR LOWER(base_url) LIKE %s OR LOWER(modelo_base) LIKE %s)")
        params.extend([like, like, like])

    if estado_manual is not None:
        clauses.append("estado_manual = %s")
        params.append(estado_manual)

    if estado_modelo is not None:
        clauses.append("estado_modelo = %s")
        params.append(estado_modelo)

    count_select = "SELECT COUNT(*) as total FROM proveedores_llm"
    if clauses:
        where = " WHERE " + " AND ".join(clauses)
        select += where
        count_select += where

    select += " ORDER BY fecha_creacion DESC, id DESC"
    if not todos:
        select += " LIMIT %s OFFSET %s"
        rows = execute_query(select, tuple(params + [limit, skip]))
    else:
        rows = execute_query(select, tuple(params) if params else None)

    total = execute_query(count_select, tuple(params) if params else None)[0]["total"]
    return rows, total


def obtener_proveedor_llm(proveedor_id):
    query = """
        SELECT id, nombre, base_url, modelo_base, razonamiento_tokens,
               estado_manual, estado_modelo, ultima_verificacion, fecha_creacion,
               (apikey IS NOT NULL AND apikey != '') AS apikey_configurada
        FROM proveedores_llm WHERE id = %s
    """
    result = execute_query(query, (proveedor_id,))
    return result[0] if result else None


def obtener_proveedores_internos():
    """Proveedores con apikey cifrada (solo para core/llm y scripts internos)."""
    query = """
        SELECT id, nombre, base_url, apikey, modelo_base, razonamiento_tokens,
               estado_manual, estado_modelo, ultima_verificacion
        FROM proveedores_llm
        WHERE apikey IS NOT NULL AND apikey != ''
        ORDER BY id
    """
    return execute_query(query)


def crear_proveedor_llm(nombre, base_url, apikey_cifrado, modelo_base, estado_manual=True):
    query = """
        INSERT INTO proveedores_llm (nombre, base_url, apikey, modelo_base, estado_manual)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
    """
    result = execute_query(query, (nombre, base_url, apikey_cifrado, modelo_base, estado_manual), fetch=True)
    return result[0]["id"]


def actualizar_proveedor_llm(proveedor_id, nombre, base_url, apikey_cifrado, modelo_base, estado_manual):
    query = """
        UPDATE proveedores_llm
        SET nombre = %s, base_url = %s, apikey = %s, modelo_base = %s, estado_manual = %s
        WHERE id = %s
    """
    execute_query(query, (nombre, base_url, apikey_cifrado, modelo_base, estado_manual, proveedor_id), fetch=False)


def actualizar_razonamiento_tokens_proveedor(proveedor_id, tokens):
    """Guarda el margen de razonamiento calibrado (EMA) para un proveedor."""
    query = """
        UPDATE proveedores_llm
        SET razonamiento_tokens = %s
        WHERE id = %s
    """
    execute_query(query, (tokens, proveedor_id), fetch=False)


def actualizar_estado_modelo_proveedor(proveedor_id, estado_modelo):
    query = """
        UPDATE proveedores_llm
        SET estado_modelo = %s, ultima_verificacion = NOW()
        WHERE id = %s
    """
    execute_query(query, (estado_modelo, proveedor_id), fetch=False)


def eliminar_proveedor_llm(proveedor_id):
    execute_query("DELETE FROM proveedores_llm WHERE id = %s", (proveedor_id,), fetch=False)


# --- Registro de uso del motor de IA ---


def registrar_uso_llm(tipo="chat", proveedor_id=None, proveedor_nombre=None, modelo=None,
                      tokens_prompt=0, tokens_completados=0, tokens_total=None, exitoso=True):
    try:
        if tokens_total is None:
            tokens_total = tokens_prompt + tokens_completados
        query = """
            INSERT INTO uso_llm
                (tipo, proveedor_id, proveedor_nombre, modelo,
                 tokens_prompt, tokens_completados, tokens_total, exitoso)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        execute_query(
            query,
            (tipo, proveedor_id, proveedor_nombre, modelo,
             tokens_prompt, tokens_completados, tokens_total, exitoso),
            fetch=False,
        )
    except Exception:
        pass


def iniciar_uso_llm(tipo="chat"):
    """Inserta una fila de uso (exitoso=false, sin tokens) y devuelve su id.

    La fila se actualiza al final con `finalizar_uso_llm`; si la llamada falla
    o el stream se corta, queda registrada como llamada sin exito.
    """
    try:
        query = """
            INSERT INTO uso_llm
                (tipo, proveedor_id, proveedor_nombre, modelo,
                 tokens_prompt, tokens_completados, tokens_total, exitoso)
            VALUES (%s, NULL, NULL, NULL, 0, 0, 0, FALSE)
            RETURNING id
        """
        result = execute_query(query, (tipo,))
        return result[0]["id"]
    except Exception:
        return None


def finalizar_uso_llm(uso_id=None, exitoso=False, proveedor_id=None, proveedor_nombre=None,
                      modelo=None, tokens_prompt=0, tokens_completados=0, tokens_total=None):
    """Actualiza una fila de uso creada con `iniciar_uso_llm`."""
    if uso_id is None:
        return
    try:
        if tokens_total is None:
            tokens_total = tokens_prompt + tokens_completados
        query = """
            UPDATE uso_llm SET
                exitoso = %s,
                proveedor_id = %s,
                proveedor_nombre = %s,
                modelo = %s,
                tokens_prompt = %s,
                tokens_completados = %s,
                tokens_total = %s
            WHERE id = %s
        """
        execute_query(
            query,
            (exitoso, proveedor_id, proveedor_nombre, modelo,
             tokens_prompt, tokens_completados, tokens_total, uso_id),
            fetch=False,
        )
    except Exception:
        pass


def eliminar_uso_llm(uso_id=None):
    """Elimina una fila de uso (p.ej. una llamada a /chat que no uso el LLM)."""
    if uso_id is None:
        return
    try:
        execute_query("DELETE FROM uso_llm WHERE id = %s", (uso_id,), fetch=False)
    except Exception:
        pass


# --- Grupos de documentos ---


def listar_grupos(q=None, limit=100, skip=0, todos=False):
    base_select = """
        SELECT g.id, g.nombre, g.descripcion, g.creado_en,
               COUNT(gi.documento_id) AS total_documentos,
               COALESCE(ARRAY_AGG(gi.documento_id ORDER BY gi.documento_id) FILTER (WHERE gi.documento_id IS NOT NULL), ARRAY[]::integer[]) AS documento_ids
        FROM grupo_documentos g
        LEFT JOIN grupo_documentos_items gi ON gi.grupo_id = g.id
    """
    clauses = []
    params = []

    if q:
        like = f"%{q.strip().lower()}%"
        clauses.append("(LOWER(g.nombre) LIKE %s OR LOWER(COALESCE(g.descripcion, '')) LIKE %s)")
        params.extend([like, like])

    query = base_select
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
        count_query = "SELECT COUNT(*) as total FROM grupo_documentos g WHERE " + " AND ".join(clauses)
    else:
        count_query = "SELECT COUNT(*) as total FROM grupo_documentos"

    query += " GROUP BY g.id ORDER BY g.creado_en DESC, g.id DESC"
    if not todos:
        query += " LIMIT %s OFFSET %s"
        rows = execute_query(query, tuple(params + [limit, skip]))
    else:
        rows = execute_query(query, tuple(params) if params else None)

    total = execute_query(count_query, tuple(params) if params else None)[0]["total"]
    return rows, total


def listar_grupos_solo_ids(grupo_id):
    """Ids de documentos de un grupo (para busqueda)."""
    query = """
        SELECT documento_id FROM grupo_documentos_items
        WHERE grupo_id = %s
        ORDER BY documento_id
    """
    result = execute_query(query, (grupo_id,))
    return [r["documento_id"] for r in result]


def obtener_grupo(grupo_id):
    """Detalle de un grupo con sus documento_ids."""
    query = """
        SELECT g.id, g.nombre, g.descripcion, g.creado_en,
               COALESCE(ARRAY_AGG(gi.documento_id ORDER BY gi.documento_id) FILTER (WHERE gi.documento_id IS NOT NULL), ARRAY[]::integer[]) AS documento_ids
        FROM grupo_documentos g
        LEFT JOIN grupo_documentos_items gi ON gi.grupo_id = g.id
        WHERE g.id = %s
        GROUP BY g.id
    """
    result = execute_query(query, (grupo_id,))
    return result[0] if result else None


def _existe_grupo_nombre(nombre, excluir_id=None):
    query = "SELECT id FROM grupo_documentos WHERE LOWER(nombre) = LOWER(%s)"
    params = [nombre]
    if excluir_id is not None:
        query += " AND id != %s"
        params.append(excluir_id)
    return bool(execute_query(query, tuple(params)))


def _reemplazar_items_grupo(conn, grupo_id, documento_ids):
    cur = conn.cursor()
    cur.execute("DELETE FROM grupo_documentos_items WHERE grupo_id = %s", (grupo_id,))
    for doc_id in documento_ids:
        cur.execute(
            "INSERT INTO grupo_documentos_items (grupo_id, documento_id) VALUES (%s, %s) "
            "ON CONFLICT (grupo_id, documento_id) DO NOTHING",
            (grupo_id, doc_id),
        )


def _validar_documentos_ignorando_faltantes(conn, documento_ids):
    """Devuelve la lista de ids validos existentes en `documentos`."""
    if not documento_ids:
        return []
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        "SELECT id FROM documentos WHERE id = ANY(%s)",
        (documento_ids,),
    )
    return [r["id"] for r in cur.fetchall()]


def crear_grupo(nombre, descripcion=None, documento_ids=None):
    """Crea un grupo y sus items en una transaccion. Valida que los docs existan."""
    if _existe_grupo_nombre(nombre):
        raise ValueError("nombre_duplicado")
    documento_ids = list(dict.fromkeys(documento_ids or []))
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            "INSERT INTO grupo_documentos (nombre, descripcion) VALUES (%s, %s) RETURNING id",
            (nombre, descripcion),
        )
        grupo_id = cur.fetchone()["id"]
        if documento_ids:
            validos = _validar_documentos_ignorando_faltantes(conn, documento_ids)
            _reemplazar_items_grupo(conn, grupo_id, validos)
        conn.commit()
        return grupo_id
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def actualizar_grupo(grupo_id, nombre, descripcion, documento_ids):
    """Actualiza el grupo y reemplaza su lista de documentos en una transaccion."""
    if _existe_grupo_nombre(nombre, excluir_id=grupo_id):
        raise ValueError("nombre_duplicado")
    documento_ids = list(dict.fromkeys(documento_ids or []))
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            "UPDATE grupo_documentos SET nombre = %s, descripcion = %s WHERE id = %s",
            (nombre, descripcion, grupo_id),
        )
        if cur.rowcount == 0:
            conn.rollback()
            return None
        if documento_ids:
            documento_ids = _validar_documentos_ignorando_faltantes(conn, documento_ids)
        _reemplazar_items_grupo(conn, grupo_id, documento_ids)
        conn.commit()
        return grupo_id
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def eliminar_grupo(grupo_id):
    """Elimina un grupo (los items se borran por ON DELETE CASCADE)."""
    execute_query("DELETE FROM grupo_documentos WHERE id = %s", (grupo_id,), fetch=False)


def resumen_uso_llm(desde=None, hasta=None, tipos=("chat",)):
    """Resumen de uso del motor IA, filtra por rango de fechas y tipos.

    Si `desde`/`hasta` son None no aplica filtro de fecha.
    Por defecto solo considera llamadas de tipo `chat` (las de `voz` se
    registran en `uso_llm` pero no aparecen aqui).

    Devuelve {desde, hasta, resumen_total, por_proveedor, por_modelo} con
    llamadas exitosas / sin exito y tokens (prompt, completados, total):
      - resumen_total: agregacion del rango completo.
      - por_proveedor: por fila de `proveedores_llm` (id, nombre y modelo);
        el modelo local (fuera de la tabla) sale como `proveedor_id: null`
        con etiqueta "Local (Qwen2.5-3B)"; llamadas que no se pudieron atribuir
        (fallo antes de elegir proveedor) salen como "Sin proveedor asignado".
      - por_modelo: por modelo usado (agrupa el mismo modelo aunque se use en
        varios proveedores); fallos sin proveedor elegido caen en "sin modelo".
    """
    condicion = "WHERE tipo = ANY(%s)"
    params = [list(tipos)]
    if desde:
        condicion += " AND fecha >= %s::date"
        params.append(desde)
    if hasta:
        condicion += " AND fecha < (%s::date + INTERVAL '1 day')"
        params.append(hasta)

    columnas_conteo = (
        "COUNT(*) AS llamadas, "
        "COUNT(*) FILTER (WHERE exitoso) AS llamadas_exitosas, "
        "COUNT(*) FILTER (WHERE NOT exitoso) AS llamadas_sin_exito, "
        "COALESCE(SUM(tokens_prompt), 0) AS tokens_prompt, "
        "COALESCE(SUM(tokens_completados), 0) AS tokens_completados, "
        "COALESCE(SUM(tokens_total), 0) AS tokens_total"
    )

    resumen_total = execute_query(
        f"SELECT {columnas_conteo} FROM uso_llm {condicion}",
        tuple(params),
    )[0]

    por_proveedor = execute_query(
        f"""
        SELECT u.proveedor_id,
               CASE
                   WHEN u.proveedor_id IS NOT NULL THEN p.nombre
                   WHEN u.proveedor_nombre IS NOT NULL THEN u.proveedor_nombre
                   WHEN u.modelo ~ '^local/' THEN 'Local (Qwen2.5-3B)'
                   ELSE 'Sin proveedor asignado'
               END AS proveedor,
               COALESCE(p.modelo_base, u.modelo) AS modelo,
               {columnas_conteo}
        FROM uso_llm u
        LEFT JOIN proveedores_llm p ON u.proveedor_id = p.id
        {condicion}
        AND NOT (u.proveedor_id IS NULL AND u.modelo IS NULL)
        GROUP BY u.proveedor_id, u.proveedor_nombre, u.modelo, p.nombre, p.modelo_base
        ORDER BY SUM(tokens_total) DESC NULLS LAST
        """,
        tuple(params),
    )

    por_modelo = execute_query(
        f"""
        SELECT COALESCE(modelo, 'sin modelo') AS modelo,
               {columnas_conteo}
        FROM uso_llm {condicion}
        AND modelo IS NOT NULL
        GROUP BY modelo ORDER BY SUM(tokens_total) DESC NULLS LAST
        """,
        tuple(params),
    )

    for bloque in (resumen_total, *por_proveedor, *por_modelo):
        for clave in ("llamadas", "llamadas_exitosas", "llamadas_sin_exito"):
            bloque[clave] = int(bloque[clave])

    return {
        "desde": desde,
        "hasta": hasta,
        "resumen_total": resumen_total,
        "por_proveedor": por_proveedor,
        "por_modelo": por_modelo,
    }


# --- Metricas de uso de embeddings ---


def registrar_uso_embeddings(proveedor="google", modelo="", tipo="query", textos=0,
                             tokens_prompt=0, tokens_total=None, dimension=None,
                             exitoso=True, tokens_estimados=False, error=None):
    try:
        if tokens_total is None:
            tokens_total = tokens_prompt
        query = """
            INSERT INTO uso_embeddings
                (proveedor, modelo, tipo, textos, tokens_prompt, tokens_total,
                 dimension, exitoso, tokens_estimados, error)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        execute_query(
            query,
            (proveedor, modelo, tipo, int(textos or 0), int(tokens_prompt or 0),
             int(tokens_total or 0), dimension, bool(exitoso), bool(tokens_estimados),
             (error[:500] if error else None)),
            fetch=False,
        )
    except Exception:
        pass


def resumen_uso_embeddings(desde=None, hasta=None):
    condicion = "WHERE TRUE"
    params = []
    if desde:
        condicion += " AND fecha >= %s::date"
        params.append(desde)
    if hasta:
        condicion += " AND fecha < (%s::date + INTERVAL '1 day')"
        params.append(hasta)

    columnas_conteo = (
        "COUNT(*) AS llamadas, "
        "COUNT(*) FILTER (WHERE exitoso) AS llamadas_exitosas, "
        "COUNT(*) FILTER (WHERE NOT exitoso) AS llamadas_sin_exito, "
        "COUNT(*) FILTER (WHERE exitoso AND tokens_estimados) AS llamadas_con_tokens_estimados, "
        "COALESCE(SUM(textos), 0) AS textos, "
        "COALESCE(SUM(tokens_prompt), 0) AS tokens_prompt, "
        "COALESCE(SUM(tokens_total), 0) AS tokens_total"
    )

    resumen_total = execute_query(
        f"SELECT {columnas_conteo} FROM uso_embeddings {condicion}",
        tuple(params),
    )[0]

    por_proveedor = execute_query(
        f"""
        SELECT proveedor, COALESCE(MAX(modelo), 'sin modelo') AS modelo,
               MAX(dimension) AS dimension,
               {columnas_conteo}
        FROM uso_embeddings {condicion}
        GROUP BY proveedor
        ORDER BY SUM(tokens_total) DESC NULLS LAST
        """,
        tuple(params),
    )

    por_modelo = execute_query(
        f"""
        SELECT COALESCE(modelo, 'sin modelo') AS modelo, proveedor,
               MAX(dimension) AS dimension,
               {columnas_conteo}
        FROM uso_embeddings {condicion}
        GROUP BY modelo, proveedor
        ORDER BY SUM(tokens_total) DESC NULLS LAST
        """,
        tuple(params),
    )

    por_tipo = execute_query(
        f"""
        SELECT COALESCE(tipo, 'sin tipo') AS tipo,
               {columnas_conteo}
        FROM uso_embeddings {condicion}
        GROUP BY tipo
        ORDER BY SUM(tokens_total) DESC NULLS LAST
        """,
        tuple(params),
    )

    for bloque in [resumen_total, *por_proveedor, *por_modelo, *por_tipo]:
        for clave in (
            "llamadas", "llamadas_exitosas", "llamadas_sin_exito",
            "llamadas_con_tokens_estimados", "textos", "tokens_prompt", "tokens_total",
        ):
            bloque[clave] = int(bloque[clave])

    return {
        "desde": desde,
        "hasta": hasta,
        "resumen_total": resumen_total,
        "por_proveedor": por_proveedor,
        "por_modelo": por_modelo,
        "por_tipo": por_tipo,
    }
