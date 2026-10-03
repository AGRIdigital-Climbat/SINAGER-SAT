"""
SERVICIO SINB - Funciones completas para catálogos, observaciones, pronósticos, validación y reportes
"""
from datetime import date, datetime, timedelta
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from uuid import UUID


# ============================================================================
# CATÁLOGOS BIOCURALTURALES
# ============================================================================

def get_grupos(db: Session):
    """Obtener todos los grupos activos."""
    rows = _rows(db, "SELECT * FROM sinb.grupo WHERE estado = 'ACTIVO' ORDER BY codigo")
    return [dict(row) for row in rows]


def get_grupo(db: Session, id: UUID):
    """Obtener grupo por ID."""
    row = _row(db, "SELECT * FROM sinb.grupo WHERE id = :id AND estado = 'ACTIVO'", {"id": id})
    return dict(row) if row else None


def create_grupo(db: Session, data: dict):
    """Crear nuevo grupo."""
    result = db.execute(text("""
        INSERT INTO sinb.grupo (codigo, nombre, descripcion, estado)
        VALUES (:codigo, :nombre, :descripcion, 'ACTIVO')
        RETURNING *
    """), data)
    db.commit()
    return dict(result.mappings().first())


def update_grupo(db: Session, id: UUID, data: dict):
    """Actualizar grupo."""
    data["id"] = id
    result = db.execute(text("""
        UPDATE sinb.grupo SET
            codigo = COALESCE(:codigo, codigo),
            nombre = COALESCE(:nombre, nombre),
            descripcion = COALESCE(:descripcion, descripcion),
            actualizado_en = now()
        WHERE id = :id AND estado = 'ACTIVO'
        RETURNING *
    """), data)
    db.commit()
    return dict(result.mappings().first()) if result.rowcount > 0 else None


def delete_grupo(db: Session, id: UUID):
    """Eliminar lógico de grupo."""
    db.execute(text("UPDATE sinb.grupo SET estado = 'ELIMINADO', actualizado_en = now() WHERE id = :id"), {"id": id})
    db.commit()


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
    """Obtener indicador por ID con grupo anidado."""
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
    return _serialize(row) if row else None


def create_indicador_natural(db: Session, data: dict):
    """Crear indicador natural."""
    result = db.execute(text("""
        INSERT INTO sinb.indicador_natural 
        (codigo, nombre_cientifico, nombre_comun, id_grupo, descripcion, requiere_consentimiento, estado)
        VALUES (:codigo, :nombre_cientifico, :nombre_comun, :id_grupo, :descripcion, :requiere_consentimiento, 'ACTIVO')
        RETURNING *
    """), data)
    db.commit()
    return dict(result.mappings().first())


def update_indicador_natural(db: Session, id: UUID, data: dict):
    """Actualizar indicador."""
    data["id"] = id
    result = db.execute(text("""
        UPDATE sinb.indicador_natural SET
            codigo = COALESCE(:codigo, codigo),
            nombre_cientifico = COALESCE(:nombre_cientifico, nombre_cientifico),
            nombre_comun = COALESCE(:nombre_comun, nombre_comun),
            id_grupo = COALESCE(:id_grupo, id_grupo),
            descripcion = COALESCE(:descripcion, descripcion),
            requiere_consentimiento = COALESCE(:requiere_consentimiento, requiere_consentimiento),
            actualizado_en = now()
        WHERE id = :id AND estado = 'ACTIVO'
        RETURNING *
    """), data)
    db.commit()
    return dict(result.mappings().first()) if result.rowcount > 0 else None


def delete_indicador_natural(db: Session, id: UUID):
    """Eliminar lógico de indicador."""
    db.execute(text("UPDATE sinb.indicador_natural SET estado = 'ELIMINADO', actualizado_en = now() WHERE id = :id"), {"id": id})
    db.commit()


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
    data["id"] = id
    result = db.execute(text("""
        UPDATE sinb.caracteristica SET
            id_indicador_natural = COALESCE(:id_indicador_natural, id_indicador_natural),
            caracteristica = COALESCE(:caracteristica, caracteristica),
            estado = COALESCE(:estado, estado)
        WHERE id = :id
        RETURNING *
    """), data)
    db.commit()
    return dict(result.mappings().first()) if result.rowcount > 0 else None


def delete_caracteristica(db: Session, id: UUID):
    """Eliminar característica."""
    db.execute(text("UPDATE sinb.caracteristica SET estado = 'ELIMINADO' WHERE id = :id"), {"id": id})
    db.commit()


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
    data["id"] = id
    result = db.execute(text("""
        UPDATE sinb.comportamiento SET
            id_grupo = COALESCE(:id_grupo, id_grupo),
            id_caracteristica = COALESCE(:id_caracteristica, id_caracteristica),
            comportamiento = COALESCE(:comportamiento, comportamiento),
            estado = COALESCE(:estado, estado)
        WHERE id = :id
        RETURNING *
    """), data)
    db.commit()
    return dict(result.mappings().first()) if result.rowcount > 0 else None


def delete_comportamiento(db: Session, id: UUID):
    """Eliminar comportamiento."""
    db.execute(text("UPDATE sinb.comportamiento SET estado = 'ELIMINADO' WHERE id = :id"), {"id": id})
    db.commit()


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
    data["id"] = id
    result = db.execute(text("""
        UPDATE sinb.significado SET
            id_grupo = COALESCE(:id_grupo, id_grupo),
            id_comportamiento = COALESCE(:id_comportamiento, id_comportamiento),
            significado = COALESCE(:significado, significado),
            categoria = COALESCE(:categoria, categoria),
            estado = COALESCE(:estado, estado)
        WHERE id = :id
        RETURNING *
    """), data)
    db.commit()
    return dict(result.mappings().first()) if result.rowcount > 0 else None


def delete_significado(db: Session, id: UUID):
    """Eliminar significado."""
    db.execute(text("UPDATE sinb.significado SET estado = 'ELIMINADO' WHERE id = :id"), {"id": id})
    db.commit()


def get_zonas_geograficas(db: Session):
    """Obtener zonas geográficas."""
    rows = _rows(db, "SELECT * FROM sinb.zona_geografica WHERE estado = 'ACTIVO' ORDER BY nombre")
    return [dict(row) for row in rows]


def create_zona_geografica(db: Session, data: dict):
    """Crear zona geográfica."""
    result = db.execute(text("""
        INSERT INTO sinb.zona_geografica (codigo, nombre, descripcion, estado)
        VALUES (:codigo, :nombre, :descripcion, 'ACTIVO')
        RETURNING *
    """), data)
    db.commit()
    return dict(result.mappings().first())


def update_zona_geografica(db: Session, id: UUID, data: dict):
    """Actualizar zona."""
    data["id"] = id
    result = db.execute(text("""
        UPDATE sinb.zona_geografica SET
            codigo = COALESCE(:codigo, codigo),
            nombre = COALESCE(:nombre, nombre),
            descripcion = COALESCE(:descripcion, descripcion),
            estado = COALESCE(:estado, estado)
        WHERE id = :id
        RETURNING *
    """), data)
    db.commit()
    return dict(result.mappings().first()) if result.rowcount > 0 else None


def delete_zona_geografica(db: Session, id: UUID):
    """Eliminar zona."""
    db.execute(text("UPDATE sinb.zona_geografica SET estado = 'ELIMINADO' WHERE id = :id"), {"id": id})
    db.commit()


def get_campos_pronostico(db: Session):
    """Obtener campos de pronóstico."""
    rows = _rows(db, "SELECT * FROM sinb.campo_pronostico WHERE estado = 'ACTIVO' ORDER BY nombre")
    return [dict(row) for row in rows]


def create_campo_pronostico(db: Session, data: dict):
    """Crear campo de pronóstico."""
    result = db.execute(text("""
        INSERT INTO sinb.campo_pronostico (codigo, nombre, descripcion, estado)
        VALUES (:codigo, :nombre, :descripcion, 'ACTIVO')
        RETURNING *
    """), data)
    db.commit()
    return dict(result.mappings().first())


def update_campo_pronostico(db: Session, id: UUID, data: dict):
    """Actualizar campo."""
    data["id"] = id
    result = db.execute(text("""
        UPDATE sinb.campo_pronostico SET
            codigo = COALESCE(:codigo, codigo),
            nombre = COALESCE(:nombre, nombre),
            descripcion = COALESCE(:descripcion, descripcion),
            estado = COALESCE(:estado, estado)
        WHERE id = :id
        RETURNING *
    """), data)
    db.commit()
    return dict(result.mappings().first()) if result.rowcount > 0 else None


def delete_campo_pronostico(db: Session, id: UUID):
    """Eliminar campo."""
    db.execute(text("UPDATE sinb.campo_pronostico SET estado = 'ELIMINADO' WHERE id = :id"), {"id": id})
    db.commit()


def get_escenarios(db: Session, id_campo: UUID | None = None):
    """Obtener escenarios con campo_pronostico anidado."""
    where = ["e.estado = 'ACTIVO'"]
    params = {}
    if id_campo:
        where.append("e.id_campo_pronostico = :id_campo")
        params["id_campo"] = id_campo
    
    query = f"""
        SELECT e.*, 
               jsonb_build_object(
                   'id', c.id,
                   'nombre', c.nombre,
                   'tipo', c.tipo,
                   'unidad', c.unidad
               ) as campo_pronostico
        FROM sinb.escenario e
        LEFT JOIN sinb.campo_pronostico c ON c.id = e.id_campo_pronostico
        WHERE {' AND '.join(where)}
        ORDER BY COALESCE(c.nombre, ''), e.nombre
    """
    rows = _rows(db, query, params)
    return _serialize(rows)


def create_escenario(db: Session, data: dict):
    """Crear escenario."""
    result = db.execute(text("""
        INSERT INTO sinb.escenario (id_campo_pronostico, codigo, nombre, descripcion, estado)
        VALUES (:id_campo_pronostico, :codigo, :nombre, :descripcion, 'ACTIVO')
        RETURNING *
    """), data)
    db.commit()
    return dict(result.mappings().first())


def update_escenario(db: Session, id: UUID, data: dict):
    """Actualizar escenario."""
    data["id"] = id
    result = db.execute(text("""
        UPDATE sinb.escenario SET
            id_campo_pronostico = COALESCE(:id_campo_pronostico, id_campo_pronostico),
            codigo = COALESCE(:codigo, codigo),
            nombre = COALESCE(:nombre, nombre),
            descripcion = COALESCE(:descripcion, descripcion),
            estado = COALESCE(:estado, estado)
        WHERE id = :id
        RETURNING *
    """), data)
    db.commit()
    return dict(result.mappings().first()) if result.rowcount > 0 else None


def delete_escenario(db: Session, id: UUID):
    """Eliminar escenario."""
    db.execute(text("UPDATE sinb.escenario SET estado = 'ELIMINADO' WHERE id = :id"), {"id": id})
    db.commit()


def get_dimensiones_recomendacion(db: Session):
    """Obtener dimensiones de recomendación."""
    rows = _rows(db, "SELECT * FROM sinb.dimension_recomendacion WHERE estado = 'ACTIVO' ORDER BY nombre")
    return [dict(row) for row in rows]


def create_dimension_recomendacion(db: Session, data: dict):
    """Crear dimensión."""
    result = db.execute(text("""
        INSERT INTO sinb.dimension_recomendacion (nombre, descripcion, estado)
        VALUES (:nombre, :descripcion, 'ACTIVO')
        RETURNING *
    """), data)
    db.commit()
    return dict(result.mappings().first())


def update_dimension_recomendacion(db: Session, id: UUID, data: dict):
    """Actualizar dimensión."""
    data["id"] = id
    result = db.execute(text("""
        UPDATE sinb.dimension_recomendacion SET
            nombre = COALESCE(:nombre, nombre),
            descripcion = COALESCE(:descripcion, descripcion),
            estado = COALESCE(:estado, estado)
        WHERE id = :id
        RETURNING *
    """), data)
    db.commit()
    return dict(result.mappings().first()) if result.rowcount > 0 else None


def delete_dimension_recomendacion(db: Session, id: UUID):
    """Eliminar dimensión."""
    db.execute(text("UPDATE sinb.dimension_recomendacion SET estado = 'ELIMINADO' WHERE id = :id"), {"id": id})
    db.commit()


def get_categorias_comportamiento(db: Session):
    """Obtener categorías de comportamiento."""
    rows = _rows(db, "SELECT * FROM sinb.categoria_comportamiento WHERE estado = 'ACTIVO' ORDER BY nombre")
    return [dict(row) for row in rows]


def create_categoria_comportamiento(db: Session, data: dict):
    """Crear categoría."""
    result = db.execute(text("""
        INSERT INTO sinb.categoria_comportamiento (nombre, descripcion, estado)
        VALUES (:nombre, :descripcion, 'ACTIVO')
        RETURNING *
    """), data)
    db.commit()
    return dict(result.mappings().first())


def update_categoria_comportamiento(db: Session, id: UUID, data: dict):
    """Actualizar categoría."""
    data["id"] = id
    result = db.execute(text("""
        UPDATE sinb.categoria_comportamiento SET
            nombre = COALESCE(:nombre, nombre),
            descripcion = COALESCE(:descripcion, descripcion),
            estado = COALESCE(:estado, estado)
        WHERE id = :id
        RETURNING *
    """), data)
    db.commit()
    return dict(result.mappings().first()) if result.rowcount > 0 else None


def delete_categoria_comportamiento(db: Session, id: UUID):
    """Eliminar categoría."""
    db.execute(text("UPDATE sinb.categoria_comportamiento SET estado = 'ELIMINADO' WHERE id = :id"), {"id": id})
    db.commit()


# ============================================================================
# PRONÓSTICOS ESTACIONALES Y TEMPORALES
# ============================================================================

def get_pronosticos_estacionales(db: Session, skip: int = 0, limit: int = 15, 
                                  id_campo: UUID | None = None,
                                  fecha_emision_desde: date | None = None,
                                  fecha_emision_hasta: date | None = None,
                                  estado: str | None = None,
                                  id_usuario_elabora: int | None = None,
                                  id_departamento: int | None = None,
                                  id_municipio: int | None = None):
    """Obtener pronósticos estacionales con paginación y filtros."""
    params = {"limit": limit, "skip": skip}
    where = ["pe.estado IN ('EMITIDO', 'ACEPTADO', 'RECHAZADO', 'EN_REVISION')"]
    
    if id_campo:
        where.append("pe.id_campo_pronostico = :id_campo")
        params["id_campo"] = id_campo
    if fecha_emision_desde:
        where.append("pe.fecha_emision >= :fecha_emision_desde")
        params["fecha_emision_desde"] = fecha_emision_desde
    if fecha_emision_hasta:
        where.append("pe.fecha_emision <= :fecha_emision_hasta")
        params["fecha_emision_hasta"] = fecha_emision_hasta
    if estado:
        where.append("pe.estado = :estado")
        params["estado"] = estado
    if id_usuario_elabora:
        where.append("pe.id_usuario_elabora = :id_usuario_elabora")
        params["id_usuario_elabora"] = id_usuario_elabora
    
    where_clause = " AND ".join(where)
    
    rows = _rows(db, f"""
        SELECT pe.*, cp.nombre as campo_nombre, u.nombre as elaborador_nombre,
               ARRAY_AGG(DISTINCT jsonb_build_object(
                   'id_escenario', ee.id_escenario,
                   'nombre', e.nombre,
                   'probabilidad', ee.probabilidad
               )) FILTER (WHERE ee.id_escenario IS NOT NULL) as escenarios
        FROM sinb.pronostico_estacional pe
        LEFT JOIN sinb.campo_pronostico cp ON cp.id = pe.id_campo_pronostico
        LEFT JOIN usuarios.usuario u ON u.id_usuario = pe.id_usuario_elabora
        LEFT JOIN sinb.escenario_estacional ee ON ee.id_pronostico_estacional = pe.id
        LEFT JOIN sinb.escenario e ON e.id = ee.id_escenario
        WHERE {where_clause}
        GROUP BY pe.id, cp.nombre, u.nombre
        ORDER BY pe.fecha_emision DESC, pe.creado_en DESC
        LIMIT :limit OFFSET :skip
    """, params)
    
    total = _row(db, f"""
        SELECT COUNT(DISTINCT pe.id) as total
        FROM sinb.pronostico_estacional pe
        WHERE {where_clause}
    """, {k: v for k, v in params.items() if k not in ['limit', 'skip']})['total']
    
    return _serialize(rows), total


def get_pronostico_estacional(db: Session, id: UUID):
    """Obtener pronóstico estacional completo con escenarios y observadores asignados."""
    pe = _row(db, """
        SELECT pe.*, cp.*, u.nombre as elaborador_nombre
        FROM sinb.pronostico_estacional pe
        LEFT JOIN sinb.campo_pronostico cp ON cp.id = pe.id_campo_pronostico
        LEFT JOIN usuarios.usuario u ON u.id_usuario = pe.id_usuario_elabora
        WHERE pe.id = :id
    """, {"id": id})
    
    if pe:
        # Escenarios
        pe["escenarios"] = _rows(db, """
            SELECT ee.probabilidad, e.id as id_escenario, e.nombre, e.descripcion
            FROM sinb.escenario_estacional ee
            JOIN sinb.escenario e ON e.id = ee.id_escenario
            WHERE ee.id_pronostico_estacional = :id
        """, {"id": id})
        
        # Observadores asignados
        pe["observadores"] = _rows(db, """
            SELECT po.id_usuario, u.nombre, u.usuario, po.confianza, po.fecha_asignacion
            FROM sinb.pronostico_observador po
            JOIN usuarios.usuario u ON u.id_usuario = po.id_usuario
            WHERE po.id_pronostico_estacional = :id
        """, {"id": id})
    
    return pe


def create_pronostico_estacional(db: Session, data: dict, id_usuario: int | None = None):
    """Crear pronóstico estacional con escenarios y observadores opcionales."""
    if id_usuario and not data.get("id_usuario_elabora"):
        data["id_usuario_elabora"] = id_usuario
    
    # Generar código único
    data["codigo"] = f"PE-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    pe = _row(db, """
        INSERT INTO sinb.pronostico_estacional 
        (codigo, id_campo_pronostico, fecha_emision, periodo_inicio, periodo_fin,
         estado, id_usuario_elabora, notas)
        VALUES (:codigo, :id_campo_pronostico, :fecha_emision, :periodo_inicio, :periodo_fin,
                'EMITIDO', :id_usuario_elabora, :notas)
        RETURNING *
    """, data)
    
    if not pe:
        return None
    
    # Insertar escenarios si vienen
    escenarios = data.get("escenarios", [])
    for esc in escenarios:
        _execute(db, """
            INSERT INTO sinb.escenario_estacional 
            (id_pronostico_estacional, id_escenario, probabilidad)
            VALUES (:id_pronostico_estacional, :id_escenario, :probabilidad)
        """, {**esc, "id_pronostico_estacional": pe["id"]})
    
    # Insertar observadores asignados si vienen
    observadores = data.get("observadores", [])
    for obs in observadores:
        _execute(db, """
            INSERT INTO sinb.pronostico_observador 
            (id_pronostico_estacional, id_usuario, confianza)
            VALUES (:id_pronostico_estacional, :id_usuario, :confianza)
        """, {**obs, "id_pronostico_estacional": pe["id"]})
    
    db.commit()
    return get_pronostico_estacional(db, pe["id"])


def update_pronostico_estacional(db: Session, id: UUID, data: dict):
    """Actualizar pronóstico estacional."""
    data["id"] = id
    result = _row(db, """
        UPDATE sinb.pronostico_estacional SET
            id_campo_pronostico = COALESCE(:id_campo_pronostico, id_campo_pronostico),
            fecha_emision = COALESCE(:fecha_emision, fecha_emision),
            periodo_inicio = COALESCE(:periodo_inicio, periodo_inicio),
            periodo_fin = COALESCE(:periodo_fin, periodo_fin),
            estado = COALESCE(:estado, estado),
            id_usuario_elabora = COALESCE(:id_usuario_elabora, id_usuario_elabora),
            notas = COALESCE(:notas, notas),
            actualizado_en = now()
        WHERE id = :id
        RETURNING *
    """, data)
    db.commit()
    return result


def delete_pronostico_estacional(db: Session, id: UUID):
    """Eliminar pronóstico estacional."""
    _execute(db, """
        UPDATE sinb.pronostico_estacional SET estado = 'ELIMINADO', actualizado_en = now()
        WHERE id = :id
    """, {"id": id})
    db.commit()


def add_escenario_a_pronostico(db: Session, id_pronostico: UUID, id_escenario: UUID, probabilidad: float):
    """Agregar escenario a pronóstico estacional."""
    result = _row(db, """
        INSERT INTO sinb.escenario_estacional 
        (id_pronostico_estacional, id_escenario, probabilidad)
        VALUES (:id_pronostico_estacional, :id_escenario, :probabilidad)
        ON CONFLICT (id_pronostico_estacional, id_escenario) 
        DO UPDATE SET probabilidad = :probabilidad
        RETURNING *
    """, {"id_pronostico_estacional": id_pronostico, "id_escenario": id_escenario, "probabilidad": probabilidad})
    db.commit()
    return result


def remove_escenario_de_pronostico(db: Session, id_pronostico: UUID, id_escenario: UUID):
    """Remover escenario de pronóstico estacional."""
    _execute(db, """
        DELETE FROM sinb.escenario_estacional
        WHERE id_pronostico_estacional = :id_pronostico AND id_escenario = :id_escenario
    """, {"id_pronostico_estacional": id_pronostico, "id_escenario": id_escenario})
    db.commit()


# --- Pronósticos Temporales ---

def get_pronosticos_temporales(db: Session, skip: int = 0, limit: int = 15,
                                id_categoria: UUID | None = None,
                                id_campo: UUID | None = None,
                                fecha_emision_desde: date | None = None,
                                confianza: str | None = None,
                                estado: str | None = None):
    """Obtener pronósticos temporales con paginación."""
    params = {"limit": limit, "skip": skip}
    where = ["pt.estado IN ('EMITIDO', 'ACEPTADO', 'RECHAZADO', 'EN_REVISION')"]
    
    if id_categoria:
        where.append("pt.id_categoria = :id_categoria")
        params["id_categoria"] = id_categoria
    if id_campo:
        where.append("pt.id_campo_pronostico = :id_campo")
        params["id_campo"] = id_campo
    if fecha_emision_desde:
        where.append("pt.fecha_emision >= :fecha_emision_desde")
        params["fecha_emision_desde"] = fecha_emision_desde
    if confianza:
        where.append("pt.confianza = :confianza::sinb.confianza_nivel")
        params["confianza"] = confianza
    if estado:
        where.append("pt.estado = :estado")
        params["estado"] = estado
    
    where_clause = " AND ".join(where)
    
    rows = _rows(db, f"""
        SELECT pt.*, cat.nombre as categoria_nombre, cp.nombre as campo_nombre
        FROM sinb.pronostico_temporal pt
        LEFT JOIN sinb.categoria_pronostico_temporal cat ON cat.id = pt.id_categoria
        LEFT JOIN sinb.campo_pronostico cp ON cp.id = pt.id_campo_pronostico
        WHERE {where_clause}
        ORDER BY pt.fecha_emision DESC
        LIMIT :limit OFFSET :skip
    """, params)
    
    total = _row(db, f"""
        SELECT COUNT(*) as total
        FROM sinb.pronostico_temporal pt
        WHERE {where_clause}
    """, {k: v for k, v in params.items() if k not in ['limit', 'skip']})['total']
    
    return _serialize(rows), total


def create_pronostico_temporal(db: Session, data: dict):
    """Crear pronóstico temporal."""
    data["codigo"] = f"PT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    result = _row(db, """
        INSERT INTO sinb.pronostico_temporal 
        (codigo, id_categoria, id_campo_pronostico, fecha_emision, fecha_inicio, fecha_fin,
         valor_esperado, confianza, estado)
        VALUES (:codigo, :id_categoria, :id_campo_pronostico, :fecha_emision, :fecha_inicio, :fecha_fin,
                :valor_esperado, :confianza, :estado)
        RETURNING *
    """, data)
    db.commit()
    return result


def update_pronostico_temporal(db: Session, id: UUID, data: dict):
    """Actualizar pronóstico temporal."""
    data["id"] = id
    result = _row(db, """
        UPDATE sinb.pronostico_temporal SET
            id_categoria = COALESCE(:id_categoria, id_categoria),
            id_campo_pronostico = COALESCE(:id_campo_pronostico, id_campo_pronostico),
            fecha_emision = COALESCE(:fecha_emision, fecha_emision),
            fecha_inicio = COALESCE(:fecha_inicio, fecha_inicio),
            fecha_fin = COALESCE(:fecha_fin, fecha_fin),
            valor_esperado = COALESCE(:valor_esperado, valor_esperado),
            confianza = COALESCE(:confianza, confianza),
            estado = COALESCE(:estado, estado),
            actualizado_en = now()
        WHERE id = :id
        RETURNING *
    """, data)
    db.commit()
    return result


def delete_pronostico_temporal(db: Session, id: UUID):
    """Eliminar pronóstico temporal."""
    _execute(db, """
        UPDATE sinb.pronostico_temporal SET estado = 'ELIMINADO', actualizado_en = now()
        WHERE id = :id
    """, {"id": id})
    db.commit()


# ============================================================================
# ASIGNACIÓN DE OBSERVADORES A PRONÓSTICOS
# ============================================================================

def asignar_observadores_a_pronostico(db: Session, id_pronostico: UUID, tipo_pronostico: str,
                                       id_observadores: list[int], confianza: str | None = None,
                                       id_usuario_asigna: int | None = None):
    """
    Asignar 1..N observadores a un pronóstico (recolector → observadores del mismo municipio).
    Valida que todos los observadores sean del mismo municipio.
    """
    if not id_observadores:
        raise HTTPException(status_code=400, detail="Debe especificar al menos un observador")
    
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
    asignaciones = []
    tabla = "sinb.pronostico_observador" if tipo_pronostico == "estacional" else "sinb.pronostico_temporal_observador"
    columna = "id_pronostico_estacional" if tipo_pronostico == "estacional" else "id_pronostico_temporal"
    
    for id_obs in id_observadores:
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
    """Remover asignación de observador de un pronóstico."""
    tabla = "sinb.pronostico_observador" if tipo_pronostico == "estacional" else "sinb.pronostico_temporal_observador"
    columna = "id_pronostico_estacional" if tipo_pronostico == "estacional" else "id_pronostico_temporal"
    
    _execute(db, f"""
        DELETE FROM {tabla}
        WHERE {columna} = :id_pronostico AND id_usuario = :id_usuario
    """, {"id_pronostico": id_pronostico, "id_usuario": id_usuario})
    db.commit()


# ============================================================================
# VALIDACIÓN AUTOMÁTICA DE PRONÓSTICOS
# ============================================================================

def calcular_verificacion_automatica(db: Session, id_pronostico: UUID | None = None,
                                      tipo: str = "todos"):
    """
    Calcular automáticamente verificación de pronósticos vencidos.
    
    Reglas automáticas:
    1. Pronóstico vencido (fecha_fin < NOW()) → marca como PENDIENTE_VERIFICACION
    2. Si hay observación en ventana temporal → EN_VERIFICACION
    3. Si coincide evento → COINCIDE
    4. Si no hay datos → SIN_DATOS
    
    Retorna lista de verificaciones calculadas.
    """
    resultados = []
    
    # Pronósticos estacionales vencidos
    if tipo in ["estacional", "todos"]:
        vencidos_est = _rows(db, """
            SELECT pe.id, pe.fecha_fin, pe.id_campo_pronostico
            FROM sinb.pronostico_estacional pe
            WHERE pe.fecha_fin < CURRENT_DATE
            AND pe.estado = 'EMITIDO'
            AND NOT EXISTS (
                SELECT 1 FROM sinb.verificacion_pronostico vp
                WHERE vp.id_pronostico_estacional = pe.id
            )
        """, {})
        
        for pe in vencidos_est:
            resultado = _verificar_pronostico_individual(db, pe["id"], "estacional")
            resultados.append(resultado)
    
    # Pronósticos temporales vencidos
    if tipo in ["temporal", "todos"]:
        vencidos_temp = _rows(db, """
            SELECT pt.id, pt.fecha_fin, pt.id_campo_pronostico
            FROM sinb.pronostico_temporal pt
            WHERE pt.fecha_fin < CURRENT_DATE
            AND pt.estado = 'EMITIDO'
            AND NOT EXISTS (
                SELECT 1 FROM sinb.verificacion_pronostico vp
                WHERE vp.id_pronostico_temporal = pt.id
            )
        """, {})
        
        for pt in vencidos_temp:
            resultado = _verificar_pronostico_individual(db, pt["id"], "temporal")
            resultados.append(resultado)
    
    return resultados


def _verificar_pronostico_individual(db: Session, id_pronostico: UUID, tipo: str):
    """
    Verificar un pronóstico individualmente.
    
    Retorna dict con:
    - estado_calculo: COINCIDE, NO_COINCIDE, SIN_DATOS, EN_VERIFICACION
    - calificacion: 0-100 score
    - es_automatico: True
    - mensaje: descripción del cálculo
    """
    # Obtener pronóstico con datos
    if tipo == "estacional":
        pron = _row(db, """
            SELECT pe.*, cp.nombre as campo_nombre
            FROM sinb.pronostico_estacional pe
            JOIN sinb.campo_pronostico cp ON cp.id = pe.id_campo_pronostico
            WHERE pe.id = :id
        """, {"id": id_pronostico})
    else:
        pron = _row(db, """
            SELECT pt.*, cp.nombre as campo_nombre
            FROM sinb.pronostico_temporal pt
            JOIN sinb.campo_pronostico cp ON cp.id = pe.id_campo_pronostico
            WHERE pt.id = :id
        """, {"id": id_pronostico})
    
    if not pron:
        return {"error": "Pronóstico no encontrado"}
    
    # Buscar observaciones en ventana temporal
    observaciones = _rows(db, """
        SELECT o.*, orr.*
        FROM sinb.observacion o
        LEFT JOIN sinb.observacion_registro orr ON orr.id_observacion = o.id
        WHERE o.fecha_inicio BETWEEN :fecha_inicio AND :fecha_fin
        AND o.es_validada = true
    """, {"fecha_inicio": pron["periodo_inicio"], "fecha_fin": pron["fecha_fin"]})
    
    if not observaciones:
        # No hay datos → SIN_DATOS
        verif = _row(db, """
            INSERT INTO sinb.verificacion_pronostico
            (id_pronostico_estacional, id_pronostico_temporal, estado, es_automatico,
             fecha_verificacion, observacion)
            VALUES (:id_estacional, :id_temporal, 'SIN_DATOS', true, now(),
                    'No hay observaciones en la ventana temporal')
            RETURNING *
        """, {
            "id_estacional": id_pronostico if tipo == "estacional" else None,
            "id_temporal": id_pronostico if tipo == "temporal" else None
        })
        db.commit()
        
        return {
            "id_pronostico": id_pronostico,
            "tipo": tipo,
            "estado_calculo": "SIN_DATOS",
            "calificacion": None,
            "es_automatico": True,
            "mensaje": "No hay observaciones en la ventana temporal"
        }
    
    # Hay observaciones → EN_VERIFICACION (requiere validación manual)
    return {
        "id_pronostico": id_pronostico,
        "tipo": tipo,
        "estado_calculo": "EN_VERIFICACION",
        "calificacion": None,
        "es_automatico": True,
        "mensaje": f"Se encontraron {len(observaciones)} observaciones en la ventana. Requiere validación manual."
    }


def get_verificaciones_pendientes(db: Session):
    """Obtener lista de pronósticos pendientes de verificación."""
    return _rows(db, """
        SELECT 
            pe.id as id_pronostico_estacional,
            pt.id as id_pronostico_temporal,
            COALESCE(cp_est.nombre, cp_temp.nombre) as campo_nombre,
            pe.fecha_fin as fecha_fin_estacional,
            pt.fecha_fin as fecha_fin_temporal,
            dias_vencido
        FROM (
            SELECT id, fecha_fin, id_campo_pronostico,
                   CURRENT_DATE - fecha_fin as dias_vencido
            FROM sinb.pronostico_estacional
            WHERE fecha_fin < CURRENT_DATE
            AND estado IN ('EMITIDO', 'ACEPTADO')
            UNION ALL
            SELECT id, fecha_fin, id_campo_pronostico,
                   CURRENT_DATE - fecha_fin as dias_vencido
            FROM sinb.pronostico_temporal
            WHERE fecha_fin < CURRENT_DATE
            AND estado IN ('EMITIDO', 'ACEPTADO')
        ) p
        LEFT JOIN sinb.verificacion_pronostico vp 
            ON vp.id_pronostico_estacional = p.id 
            OR vp.id_pronostico_temporal = p.id
        LEFT JOIN sinb.campo_pronostico cp_est ON cp_est.id = p.id_campo_pronostico
        LEFT JOIN sinb.campo_pronostico cp_temp ON cp_temp.id = p.id_campo_pronostico
        WHERE vp.id IS NULL
        ORDER BY dias_vencido DESC
    """, {})


def validar_pronostico_manual(db: Session, id_pronostico: UUID, tipo: str,
                               estado: str, observacion: str,
                               calificacion: float | None = None,
                               id_usuario_verifica: int | None = None):
    """
    Validación MANUAL de pronóstico por usuario autorizado.
    Sobrescribe validación automática si existe.
    """
    if estado not in ["COINCIDE", "NO_COINCIDE"]:
        raise HTTPException(status_code=400, detail="Estado debe ser COINCIDE o NO_COINCIDE")
    
    id_est = id_pronostico if tipo == "estacional" else None
    id_temp = id_pronostico if tipo == "temporal" else None
    
    result = _row(db, """
        INSERT INTO sinb.verificacion_pronostico
        (id_pronostico_estacional, id_pronostico_temporal, estado, calificacion,
         observacion, es_automatico, id_usuario_verifica, fecha_verificacion)
        VALUES (:id_est, :id_temp, :estado, :calificacion, :observacion,
                false, :id_usuario, now())
        ON CONFLICT (id_pronostico_estacional, id_pronostico_temporal)
        DO UPDATE SET
            estado = :estado,
            calificacion = :calificacion,
            observacion = :observacion,
            es_automatico = false,
            id_usuario_verifica = :id_usuario,
            fecha_verificacion = now()
        RETURNING *
    """, {
        "id_est": id_est,
        "id_temp": id_temp,
        "estado": estado,
        "calificacion": calificacion,
        "observacion": observacion,
        "id_usuario": id_usuario_verifica
    })
    
    db.commit()
    return result


# ============================================================================
# CALENDARIO DE SIEMBRA Y RECOMENDACIONES
# ============================================================================

def get_calendario_siembra(db: Session, id_municipio: int | None = None,
                            fecha_desde: date | None = None,
                            fecha_hasta: date | None = None):
    """
    Obtener calendario de siembra consolidado por municipio.
    Muestra épocas de siembra recomendadas por cultivo.
    """
    params = {}
    where = ["rl.estado = 'ACTIVO'"]
    
    if id_municipio:
        where.append("rl.id_municipio = :id_municipio")
        params["id_municipio"] = id_municipio
    
    where_clause = " AND ".join(where)
    
    return _rows(db, f"""
        SELECT 
            rl.id,
            rl.texto as recomendacion,
            d.nombre as dimension,
            c.nombre as categoria,
            m.nombre as municipio,
            p.nombre as provincia,
            dep.nombre as departamento,
            rl.creado_en
        FROM sinb.recomendacion_local rl
        JOIN sinb.dimension_recomendacion d ON d.id = rl.id_dimension
        JOIN sinb.categoria_comportamiento c ON c.id = rl.id_categoria
        LEFT JOIN shared.municipio m ON m.id = rl.id_municipio
        LEFT JOIN shared.provincia p ON p.id = m.id_provincia
        LEFT JOIN shared.departamento dep ON dep.id = m.id_departamento
        WHERE {where_clause}
        ORDER BY rl.creado_en DESC
    """, params)


# ============================================================================
# REPORTES ENRIQUECIDOS
# ============================================================================

def get_reporte_observaciones_resumen(db: Session, filters: dict | None = None):
    """
    Reporte enriquecido de observaciones: totales, por comunidad, por indicador.
    """
    if filters is None:
        filters = {}
    
    # Totales
    totales = _row(db, """
        SELECT 
            COUNT(DISTINCT o.id) as total_observaciones,
            COUNT(DISTINCT orr.id) as total_registros
        FROM sinb.observacion o
        LEFT JOIN sinb.observacion_registro orr ON orr.id_observacion = o.id
        WHERE o.estado = 'ACTIVO'
    """, {})
    
    # Por comunidad
    por_comunidad = _rows(db, """
        SELECT 
            o.codigo_comunidad,
            c.nombre as comunidad_nombre,
            COUNT(*) as cantidad
        FROM sinb.observacion o
        LEFT JOIN shared.comunidades c ON c.codigo_ine = o.codigo_comunidad
        WHERE o.estado = 'ACTIVO'
        GROUP BY o.codigo_comunidad, c.nombre
        ORDER BY cantidad DESC
        LIMIT 20
    """, {})
    
    # Por indicador
    por_indicador = _rows(db, """
        SELECT 
            inat.id,
            inat.nombre_cientifico,
            COUNT(*) as cantidad
        FROM sinb.observacion_registro orr
        JOIN sinb.indicador_natural inat ON inat.id = orr.id_indicador_natural
        JOIN sinb.observacion o ON o.id = orr.id_observacion
        WHERE o.estado = 'ACTIVO' AND orr.id_indicador_natural IS NOT NULL
        GROUP BY inat.id, inat.nombre_cientifico
        ORDER BY cantidad DESC
        LIMIT 20
    """, {})
    
    # Por estado de validación
    por_estado = _rows(db, """
        SELECT 
            es_validada,
            COUNT(*) as cantidad
        FROM sinb.observacion
        WHERE estado = 'ACTIVO'
        GROUP BY es_validada
    """, {})
    
    return {
        "totales": totales,
        "por_comunidad": por_comunidad,
        "por_indicador": por_indicador,
        "por_estado_validacion": por_estado
    }


def get_reporte_pronosticos_resumen(db: Session):
    """
    Reporte de pronósticos con estado de verificación.
    """
    totales = _row(db, """
        SELECT 
            (SELECT COUNT(*) FROM sinb.pronostico_estacional WHERE estado != 'ELIMINADO') as total_estacional,
            (SELECT COUNT(*) FROM sinb.pronostico_temporal WHERE estado != 'ELIMINADO') as total_temporal
    """, {})
    
    por_estado = _rows(db, """
        SELECT estado, COUNT(*) as cantidad
        FROM sinb.pronostico_estacional
        WHERE estado != 'ELIMINADO'
        GROUP BY estado
        UNION ALL
        SELECT estado, COUNT(*) as cantidad
        FROM sinb.pronostico_temporal
        WHERE estado != 'ELIMINADO'
        GROUP BY estado
    """, {})
    
    verificaciones = _row(db, """
        SELECT 
            COUNT(*) FILTER (WHERE estado = 'COINCIDE') as coinciden,
            COUNT(*) FILTER (WHERE estado = 'NO_COINCIDE') as no_coinciden,
            COUNT(*) FILTER (WHERE estado IN ('PENDIENTE', 'EN_VERIFICACION', 'SIN_DATOS')) as pendientes
        FROM sinb.verificacion_pronostico
    """, {})
    
    return {
        "total_pronosticos": totales["total_estacional"] + totales["total_temporal"],
        "por_estado": por_estado,
        "verificaciones_pendientes": verificaciones["pendientes"],
        "verificaciones_coinciden": verificaciones["coinciden"],
        "verificaciones_no_coinciden": verificaciones["no_coinciden"]
    }


# ============================================================================
# FUNCIONES HELPER
# ============================================================================

def _rows(db: Session, query: str, params: dict = None):
    """Ejecutar query y retornar múltiples filas."""
    params = params or {}
    return db.execute(text(query), params).mappings().all()


def _row(db: Session, query: str, params: dict = None):
    """Ejecutar query y retornar una fila."""
    params = params or {}
    return db.execute(text(query), params).mappings().first()


def _execute(db: Session, query: str, params: dict = None):
    """Ejecutar query sin retorno."""
    params = params or {}
    return db.execute(text(query), params)


def _serialize(obj):
    """Serializar tipos especiales (UUID, datetime, date) a JSON-compatible."""
    if obj is None:
        return None
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serialize(item) for item in obj]
    return obj


# ============================================================================
# OBSERVACIONES
# ============================================================================

def get_observaciones(db: Session, skip: int = 0, limit: int = 15, filters: dict = None):
    """Obtener observaciones con paginación y filtros."""
    filters = filters or {}
    where = ["o.estado IN ('ACTIVO', 'INACTIVO')"]
    params = {"limit": limit, "skip": skip}
    
    if filters.get("id_municipio"):
        where.append("o.id_municipio = :id_municipio")
        params["id_municipio"] = filters["id_municipio"]
    if filters.get("id_departamento"):
        where.append("m.id_departamento = :id_departamento")
        params["id_departamento"] = filters["id_departamento"]
    if filters.get("codigo_comunidad"):
        where.append("o.codigo_comunidad = :codigo_comunidad")
        params["codigo_comunidad"] = filters["codigo_comunidad"]
    if filters.get("id_usuario_responsable"):
        where.append("o.id_usuario_responsable = :id_usuario_responsable")
        params["id_usuario_responsable"] = filters["id_usuario_responsable"]
    if filters.get("fecha_inicio_desde"):
        where.append("o.fecha_inicio >= :fecha_inicio_desde")
        params["fecha_inicio_desde"] = filters["fecha_inicio_desde"]
    if filters.get("fecha_inicio_hasta"):
        where.append("o.fecha_inicio <= :fecha_inicio_hasta")
        params["fecha_inicio_hasta"] = filters["fecha_inicio_hasta"]
    if filters.get("es_validada") is not None:
        where.append("o.es_validada = :es_validada")
        params["es_validada"] = filters["es_validada"]
    
    where_clause = " AND ".join(where)
    
    rows = _rows(db, f"""
        SELECT o.*, u.usuario as responsable_nombre,
               m.nombre as municipio_nombre,
               c.nombre as comunidad_nombre
        FROM sinb.observacion o
        LEFT JOIN usuarios.usuario u ON u.id_usuario = o.id_usuario_responsable
        LEFT JOIN shared.municipio m ON m.id = o.id_municipio
        LEFT JOIN shared.comunidades c ON c.codigo_ine = o.codigo_comunidad
        WHERE {where_clause}
        ORDER BY o.fecha_inicio DESC, o.creado_en DESC
        LIMIT :limit OFFSET :skip
    """, params)
    
    total = _row(db, f"""
        SELECT COUNT(DISTINCT o.id) as total
        FROM sinb.observacion o
        LEFT JOIN shared.municipio m ON m.id = o.id_municipio
        WHERE {where_clause}
    """, {k: v for k, v in params.items() if k not in ['limit', 'skip']})['total']
    
    return _serialize(rows), total


def get_observacion(db: Session, id: UUID):
    """Obtener observación completa con registros y anidados JSON."""
    obs = _row(db, """
        SELECT o.*, 
               jsonb_build_object(
                   'id_usuario', u.id_usuario,
                   'usuario', u.usuario,
                   'nombre', u.nombre,
                   'id_rol', u.id_rol
               ) as usuario_responsable,
               jsonb_build_object(
                   'id', m.id,
                   'nombre', m.nombre,
                   'codigo_ine', m.codigo_ine
               ) as municipio,
               jsonb_build_object(
                   'codigo_ine', c.codigo_ine,
                   'nombre', c.nombre,
                   'geom', ST_AsGeoJSON(c.geom)::jsonb
               ) as comunidad
        FROM sinb.observacion o
        LEFT JOIN usuarios.usuario u ON u.id_usuario = o.id_usuario_responsable
        LEFT JOIN shared.municipio m ON m.id = o.id_municipio
        LEFT JOIN shared.comunidades c ON c.codigo_ine = o.codigo_comunidad
        WHERE o.id = :id
    """, {"id": id})
    
    if obs:
        # Registros con anidados completos
        obs["observacion_registro"] = _rows(db, """
            SELECT orr.*,
                   jsonb_build_object(
                       'id', car.id,
                       'caracteristica', car.caracteristica,
                       'id_indicador_natural', car.id_indicador_natural
                   ) as caracteristica,
                   jsonb_build_object(
                       'id', com.id,
                       'comportamiento', com.comportamiento,
                       'id_caracteristica', com.id_caracteristica
                   ) as comportamiento,
                   jsonb_build_object(
                       'id', s.id,
                       'significado', s.significado,
                       'categoria', s.categoria,
                       'id_comportamiento', s.id_comportamiento
                   ) as significado,
                   jsonb_build_object(
                       'id', i.id,
                       'nombre_cientifico', i.nombre_cientifico,
                       'nombre_comun', i.nombre_comun,
                       'codigo', i.codigo
                   ) as indicador_natural
            FROM sinb.observacion_registro orr
            LEFT JOIN sinb.caracteristica car ON car.id = orr.id_caracteristica
            LEFT JOIN sinb.comportamiento com ON com.id = orr.id_comportamiento
            LEFT JOIN sinb.significado s ON s.id = orr.id_significado
            LEFT JOIN sinb.indicador_natural i ON i.id = orr.id_indicador_natural
            WHERE orr.id_observacion = :id
            ORDER BY orr.creado_en
        """, {"id": id})
    
    return _serialize(obs)


def create_observacion(db: Session, data: dict, id_usuario: int):
    """Crear observación con registros opcionales."""
    import uuid
    
    # Si no viene id_off, generar uno nuevo
    if not data.get("id_obs_off"):
        data["id_obs_off"] = str(uuid.uuid4())[:32]
    
    # Si no viene responsable, usar el usuario actual
    if not data.get("id_usuario_responsable"):
        data["id_usuario_responsable"] = id_usuario
    
    # Generar codigo_corto
    data["codigo_corto"] = f"OBS-{uuid.uuid4().hex[:8].upper()}"
    
    # Extraer registros si existen
    registros = data.pop("observacion_registro", [])
    
    # Insertar observación
    result = _row(db, """
        INSERT INTO sinb.observacion 
        (id_off, codigo_corto, codigo_comunidad, id_municipio, 
         id_usuario_responsable, fecha_inicio, fecha_fin, 
         hora_inicio, hora_fin, fecha_registro, clima_observado, estado)
        VALUES (:id_off, :codigo_corto, :codigo_comunidad, :id_municipio,
                :id_usuario_responsable, :fecha_inicio, :fecha_fin,
                :hora_inicio, :hora_fin, :fecha_registro, :clima_observado, 'ACTIVO')
        RETURNING *
    """, data)
    db.commit()
    
    if not result:
        raise HTTPException(status_code=500, detail="Error al crear observación")
    
    obs_id = result["id"]
    
    # Insertar registros si existen
    for reg in registros:
        if not reg.get("id_reg_off"):
            reg["id_reg_off"] = str(uuid.uuid4())[:32]
        reg["id_observacion"] = obs_id
        _row(db, """
            INSERT INTO sinb.observacion_registro
            (id_off, id_observacion, id_caracteristica, id_comportamiento,
             id_significado, id_indicador_natural, valor_observado, unidad)
            VALUES (:id_off, :id_observacion, :id_caracteristica, :id_comportamiento,
                    :id_significado, :id_indicador_natural, :valor_observado, :unidad)
            RETURNING *
        """, reg)
    
    db.commit()
    return _serialize(get_observacion(db, obs_id))


def update_observacion(db: Session, id: UUID, data: dict):
    """Actualizar observación."""
    data["id"] = id
    result = _row(db, """
        UPDATE sinb.observacion SET
            codigo_comunidad = COALESCE(:codigo_comunidad, codigo_comunidad),
            id_municipio = COALESCE(:id_municipio, id_municipio),
            fecha_inicio = COALESCE(:fecha_inicio, fecha_inicio),
            fecha_fin = COALESCE(:fecha_fin, fecha_fin),
            hora_inicio = COALESCE(:hora_inicio, hora_inicio),
            hora_fin = COALESCE(:hora_fin, hora_fin),
            fecha_registro = COALESCE(:fecha_registro, fecha_registro),
            clima_observado = COALESCE(:clima_observado, clima_observado),
            es_validada = COALESCE(:es_validada, es_validada),
            observacion_rechazada_motivo = COALESCE(:observacion_rechazada_motivo, observacion_rechazada_motivo),
            actualizado_en = now()
        WHERE id = :id
        RETURNING *
    """, data)
    db.commit()
    return _serialize(result)


def delete_observacion(db: Session, id: UUID):
    """Eliminar lógico de observación."""
    _execute(db, "UPDATE sinb.observacion SET estado = 'ELIMINADO', actualizado_en = now() WHERE id = :id", {"id": id})
    db.commit()


# ============================================================================
# PRONÓSTICOS DIGITALES (Open-Meteo Integration)
# ============================================================================

import httpx

OPEN_METEO_BASE = "https://api.open-meteo.com/v1"

def consultar_open_meteo(
    latitud: float,
    longitud: float,
    tipo: str = "daily",
    variables: list[str] = None,
    horizonte_dias: int = 7
) -> dict:
    """
    Consultar API de Open-Meteo.
    
    Args:
        latitud: Latitud del punto
        longitud: Longitud del punto
        tipo: "daily", "hourly", o "minutely_15"
        variables: Lista de variables a consultar
        horizonte_dias: Días de horizonte (1-16)
    
    Returns:
        Datos crudos de Open-Meteo
    """
    params = {
        "latitude": latitud,
        "longitude": longitud,
        "timezone": "America/La_Paz",
        "forecast_days": min(horizonte_dias, 16)
    }
    
    # Variables por defecto según tipo
    if tipo == "daily":
        params["daily"] = ",".join(variables or [
            "temperature_2m_max", "temperature_2m_min",
            "precipitation_sum", "precipitation_probability_max"
        ])
    elif tipo == "hourly":
        params["hourly"] = ",".join(variables or [
            "temperature_2m", "precipitation_probability", "relative_humidity_2m"
        ])
        params["forecast_hours"] = min(horizonte_dias * 24, 168)
    elif tipo == "minutely_15":
        params["minutely_15"] = ",".join(variables or [
            "precipitation", "temperature_2m"
        ])
    
    try:
        response = httpx.get(f"{OPEN_METEO_BASE}/forecast", params=params, timeout=10.0)
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
    fecha: date = None
) -> dict:
    """
    Guardar pronóstico diario para un municipio (uso automático cron).
    
    **Horario de referencia:** Los datos son del día COMPLETO en hora local
    (0:00 a 23:59 America/La_Paz, UTC-4).
    
    - temp_max: máxima del día (ocurre típicamente entre 12:00-15:00)
    - temp_min: mínima del día (ocurre típicamente entre 03:00-06:00)
    - sunrise: salida del sol (inicio del día solar, ~06:00-06:30)
    - sunset: puesta del sol (fin del día solar, ~18:00-19:00)
    
    Args:
        db: Sesión de base de datos
        id_municipio: ID del municipio
        latitud: Latitud del centroide del municipio
        longitud: Longitud del centroide del municipio
        fecha: Fecha a consultar (hoy por defecto)
    
    Returns:
        Datos guardados
    """
    from datetime import date as date_type, datetime as datetime_type
    
    if fecha is None:
        fecha = date_type.today()
    
    # Consultar Open-Meteo con sunrise/sunset
    datos = consultar_open_meteo(
        latitud, longitud, "daily", 
        variables=["temperature_2m_max", "temperature_2m_min", "precipitation_sum", 
                   "precipitation_probability_max", "sunrise", "sunset"],
        horizonte_dias=7
    )
    
    if "daily" not in datos:
        raise HTTPException(status_code=503, detail="Open-Meteo no devolvió datos diarios")
    
    daily = datos["daily"]
    fechas = daily.get("time", [])
    temp_max = daily.get("temperature_2m_max", [])
    temp_min = daily.get("temperature_2m_min", [])
    precip_sum = daily.get("precipitation_sum", [])
    precip_prob = daily.get("precipitation_probability_max", [])
    sunrise_list = daily.get("sunrise", [])
    sunset_list = daily.get("sunset", [])
    
    registros_guardados = []
    
    for i, fecha_str in enumerate(fechas):
        fecha_obj = date_type.fromisoformat(fecha_str)
        
        # Parsear sunrise/sunset si existen
        sunrise_dt = None
        sunset_dt = None
        if i < len(sunrise_list):
            try:
                sunrise_dt = datetime_type.fromisoformat(sunrise_list[i].replace("T", " "))
            except:
                pass
        if i < len(sunset_list):
            try:
                sunset_dt = datetime_type.fromisoformat(sunset_list[i].replace("T", " "))
            except:
                pass
        
        # Upsert: actualizar si existe, insertar si no
        existing = _row(db, """
            SELECT id FROM sinb.pronostico_diario_municipal
            WHERE id_municipio = :id_municipio AND fecha = :fecha
        """, {"id_municipio": id_municipio, "fecha": fecha_obj})
        
        if existing:
            # Actualizar
            _execute(db, """
                UPDATE sinb.pronostico_diario_municipal SET
                    temp_max = :temp_max,
                    temp_min = :temp_min,
                    precipitacion_suma = :precip_sum,
                    precipitacion_prob_max = :precip_prob,
                    sunrise = :sunrise,
                    sunset = :sunset,
                    actualizado_en = now()
                WHERE id_municipio = :id_municipio AND fecha = :fecha
            """, {
                "temp_max": temp_max[i] if i < len(temp_max) else None,
                "temp_min": temp_min[i] if i < len(temp_min) else None,
                "precip_sum": precip_sum[i] if i < len(precip_sum) else None,
                "precip_prob": precip_prob[i] if i < len(precip_prob) else None,
                "sunrise": sunrise_dt,
                "sunset": sunset_dt,
                "id_municipio": id_municipio,
                "fecha": fecha_obj
            })
        else:
            # Insertar
            _execute(db, """
                INSERT INTO sinb.pronostico_diario_municipal
                (id_municipio, fecha, temp_max, temp_min, precipitacion_suma, 
                 precipitacion_prob_max, sunrise, sunset)
                VALUES (:id_municipio, :fecha, :temp_max, :temp_min, :precip_sum, 
                        :precip_prob, :sunrise, :sunset)
            """, {
                "id_municipio": id_municipio,
                "fecha": fecha_obj,
                "temp_max": temp_max[i] if i < len(temp_max) else None,
                "temp_min": temp_min[i] if i < len(temp_min) else None,
                "precip_sum": precip_sum[i] if i < len(precip_sum) else None,
                "precip_prob": precip_prob[i] if i < len(precip_prob) else None,
                "sunrise": sunrise_dt,
                "sunset": sunset_dt
            })
        
        registros_guardados.append(fecha_str)
    
    return {
        "municipio_id": id_municipio,
        "registros_guardados": len(registros_guardados),
        "fechas": registros_guardados,
        "nota": "Datos del día completo (0:00-23:59 hora local America/La_Paz)"
    }


def get_pronostico_diario_municipal(
    db: Session,
    id_municipio: int,
    fecha_desde: date = None,
    fecha_hasta: date = None
) -> list:
    """Obtener pronóstico diario por municipio."""
    where = ["pdm.id_municipio = :id_municipio"]
    params = {"id_municipio": id_municipio}
    
    if fecha_desde:
        where.append("pdm.fecha >= :fecha_desde")
        params["fecha_desde"] = fecha_desde
    
    if fecha_hasta:
        where.append("pdm.fecha <= :fecha_hasta")
        params["fecha_hasta"] = fecha_hasta
    
    where_clause = " AND ".join(where)
    
    rows = _rows(db, f"""
        SELECT pdm.*, m.nombre as municipio_nombre
        FROM sinb.pronostico_diario_municipal pdm
        JOIN shared.municipio m ON m.id = pdm.id_municipio
        WHERE {where_clause}
        ORDER BY pdm.fecha DESC
    """, params)
    
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
    limit: int = 100
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
    
    where_clause = " AND ".join(where)
    
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
        LIMIT :limit OFFSET :skip
    """, params)
    
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
        fecha = date_type.today()
    
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
# GALERÍA DE EVIDENCIAS (Fotos/Audio de Bioindicadores)
# ============================================================================

def get_evidencias_galeria(
    db: Session,
    filtros: dict = None,
    skip: int = 0,
    limit: int = 100
) -> tuple:
    """
    Obtener galería de evidencias con filtros completos y anidados JSON.
    
    Args:
        db: Sesión de base de datos
        filtros: Diccionario con filtros (id_indicador, id_grupo, id_municipio, etc.)
        skip: Saltar registros
        limit: Límite de registros
    
    Returns:
        Tupla (lista de evidencias, total)
    """
    filtros = filtros or {}
    where = ["e.activo = true"]
    params = {"skip": skip, "limit": limit}
    
    if filtros.get("id_indicador_natural"):
        where.append("e.id_indicador_natural = :id_indicador_natural")
        params["id_indicador_natural"] = filtros["id_indicador_natural"]
    
    if filtros.get("id_grupo"):
        where.append("i.id_grupo = :id_grupo")
        params["id_grupo"] = filtros["id_grupo"]
    
    if filtros.get("id_municipio"):
        where.append("o.id_municipio = :id_municipio")
        params["id_municipio"] = filtros["id_municipio"]
    
    if filtros.get("codigo_comunidad"):
        where.append("o.codigo_comunidad = :codigo_comunidad")
        params["codigo_comunidad"] = filtros["codigo_comunidad"]
    
    if filtros.get("id_usuario_subio"):
        where.append("e.id_usuario_subio = :id_usuario_subio")
        params["id_usuario_subio"] = filtros["id_usuario_subio"]
    
    if filtros.get("formato"):
        where.append("e.formato = :formato")
        params["formato"] = filtros["formato"]
    
    if filtros.get("fecha_desde"):
        where.append("e.fecha_carga >= :fecha_desde")
        params["fecha_desde"] = filtros["fecha_desde"]
    
    if filtros.get("fecha_hasta"):
        where.append("e.fecha_carga <= :fecha_hasta")
        params["fecha_hasta"] = filtros["fecha_hasta"]
    
    if filtros.get("con_gps") is True:
        where.append("e.descripcion IS NOT NULL")  # Asumiendo que GPS se guarda en descripción o metadata
    elif filtros.get("con_gps") is False:
        where.append("e.descripcion IS NULL")
    
    where_clause = " AND ".join(where)
    
    # Consulta principal con anidados JSON
    query = f"""
        SELECT 
            e.id,
            e.id_indicador_natural,
            jsonb_build_object(
                'id', i.id,
                'nombre_cientifico', i.nombre_cientifico,
                'nombre_comun', i.nombre_comun,
                'codigo', i.codigo,
                'grupo', jsonb_build_object(
                    'id', g.id,
                    'nombre', g.nombre,
                    'codigo', g.codigo
                )
            ) as indicador,
            e.id_observacion_registro,
            jsonb_build_object(
                'id', orr.id,
                'id_observacion', orr.id_observacion,
                'valor_observado', orr.valor_observado
            ) as observacion_registro,
            e.id_usuario_subio,
            jsonb_build_object(
                'id_usuario', u.id_usuario,
                'usuario', u.usuario,
                'nombre', u.nombre,
                'id_rol', u.id_rol
            ) as usuario,
            e.path_archivo,
            e.descripcion,
            e.formato,
            e.tamano_bytes,
            e.hash_sha256,
            e.fecha_carga,
            e.activo,
            jsonb_build_object(
                'latitud', NULL,
                'longitud', NULL,
                'metadata', jsonb_build_object(
                    'formato', e.formato,
                    'tamano_mb', round(e.tamano_bytes / 1048576.0, 2)
                )
            ) as metadata
        FROM sinb.evidencia e
        LEFT JOIN sinb.indicador_natural i ON i.id = e.id_indicador_natural
        LEFT JOIN sinb.grupo g ON g.id = i.id_grupo
        LEFT JOIN sinb.observacion_registro orr ON orr.id = e.id_observacion_registro
        LEFT JOIN sinb.observacion o ON o.id = orr.id_observacion
        LEFT JOIN usuarios.usuario u ON u.id_usuario = e.id_usuario_subio
        WHERE {where_clause}
        ORDER BY e.fecha_carga DESC
        LIMIT :limit OFFSET :skip
    """
    
    rows = _rows(db, query, params)
    
    # Total
    total_query = f"""
        SELECT COUNT(DISTINCT e.id) as total
        FROM sinb.evidencia e
        LEFT JOIN sinb.indicador_natural i ON i.id = e.id_indicador_natural
        LEFT JOIN sinb.observacion o ON o.id = e.id_observacion_registro
        WHERE {where_clause}
    """
    total = _row(db, total_query, {k: v for k, v in params.items() if k not in ['limit', 'skip']})['total']
    
    return _serialize(rows), total


def get_indicadores_destacados_galeria(
    db: Session,
    id_grupo: UUID = None,
    limit: int = 10
) -> list:
    """
    Obtener indicadores con más evidencias (fotos) en la galería.
    
    Args:
        db: Sesión de base de datos
        id_grupo: Filtrar por grupo biocultural
        limit: Límite de resultados
    
    Returns:
        Lista de indicadores con conteo de fotos
    """
    where = ["e.activo = true", "e.id_indicador_natural IS NOT NULL"]
    params = {"limit": limit}
    
    if id_grupo:
        where.append("i.id_grupo = :id_grupo")
        params["id_grupo"] = id_grupo
    
    where_clause = " AND ".join(where)
    
    rows = _rows(db, f"""
        SELECT 
            i.id,
            i.nombre_cientifico,
            i.nombre_comun,
            i.codigo,
            g.id as id_grupo,
            g.nombre as grupo_nombre,
            COUNT(e.id) as cantidad_evidencias,
            jsonb_agg(
                jsonb_build_object(
                    'id', e.id,
                    'path_archivo', e.path_archivo,
                    'descripcion', e.descripcion,
                    'formato', e.formato
                ) ORDER BY e.fecha_carga DESC
            ) FILTER (WHERE e.id IS NOT NULL) as ultimas_fotos
        FROM sinb.indicador_natural i
        LEFT JOIN sinb.grupo g ON g.id = i.id_grupo
        LEFT JOIN sinb.evidencia e ON e.id_indicador_natural = i.id AND e.activo = true
        WHERE {where_clause}
        GROUP BY i.id, i.nombre_cientifico, i.nombre_comun, i.codigo, g.id, g.nombre
        ORDER BY cantidad_evidencias DESC
        LIMIT :limit
    """, params)
    
    return _serialize(rows)


def get_galeria_por_municipio(
    db: Session,
    id_municipio: int,
    limit: int = 50
) -> list:
    """
    Obtener galería de evidencias filtrada por municipio.
    
    Args:
        db: Sesión de base de datos
        id_municipio: ID del municipio
        limit: Límite de resultados
    
    Returns:
        Lista de evidencias con información del municipio
    """
    rows = _rows(db, """
        SELECT 
            e.id,
            e.path_archivo,
            e.descripcion,
            e.formato,
            e.fecha_carga,
            jsonb_build_object(
                'id', i.id,
                'nombre_cientifico', i.nombre_cientifico,
                'nombre_comun', i.nombre_comun
            ) as indicador,
            jsonb_build_object(
                'id', m.id,
                'nombre', m.nombre,
                'codigo_ine', m.codigo_ine
            ) as municipio,
            jsonb_build_object(
                'codigo_ine', c.codigo_ine,
                'nombre', c.nombre
            ) as comunidad,
            COUNT(*) OVER() as total_comunal
        FROM sinb.evidencia e
        LEFT JOIN sinb.indicador_natural i ON i.id = e.id_indicador_natural
        LEFT JOIN sinb.observacion_registro orr ON orr.id = e.id_observacion_registro
        LEFT JOIN sinb.observacion o ON o.id = orr.id_observacion
        LEFT JOIN shared.municipio m ON m.id = o.id_municipio
        LEFT JOIN shared.comunidades c ON c.codigo_ine = o.codigo_comunidad
        WHERE e.activo = true 
          AND m.id = :id_municipio
          AND e.id_indicador_natural IS NOT NULL
        ORDER BY e.fecha_carga DESC
        LIMIT :limit
    """, {"id_municipio": id_municipio, "limit": limit})
    
    return _serialize(rows)
