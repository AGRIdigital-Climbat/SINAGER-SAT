from typing import Any
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text


def _row(db: Session, query: str, params: dict | None = None) -> dict | None:
    result = db.execute(text(query), params or {}).fetchone()
    if result is None:
        return None
    return dict(result._mapping)


def _rows(db: Session, query: str, params: dict | None = None) -> list[dict]:
    result = db.execute(text(query), params or {}).fetchall()
    return [dict(row._mapping) for row in result]


# ============================================================================
#  CATÁLOGOS - CATEGORÍAS
# ============================================================================

def listar_categorias(db: Session, solo_activos: bool = True,
                      skip: int = 0, limit: int = 500, todos: bool = False) -> tuple[list[dict], int]:
    where = "WHERE activo = TRUE" if solo_activos else ""
    count_sql = f"SELECT COUNT(*) FROM rida.cat_categoria_ayuda {where}"
    total = db.execute(text(count_sql)).scalar() or 0
    
    page = "" if todos else "LIMIT :limit OFFSET :skip"
    params: dict[str, Any] = {}
    if not todos:
        params["limit"] = limit
        params["skip"] = skip
    data_sql = f"""
        SELECT id_categoria_ayuda, codigo, nombre, descripcion, activo,
               (SELECT COUNT(*) FROM rida.cat_articulo a WHERE a.id_categoria_ayuda = c.id_categoria_ayuda AND a.activo = TRUE) as n_articulos
        FROM rida.cat_categoria_ayuda c
        {where}
        ORDER BY nombre
        {page}
    """
    data = _rows(db, data_sql, params)
    return data, total


def get_categoria(db: Session, id_categoria: int) -> dict | None:
    return _row(db, """
        SELECT id_categoria_ayuda, codigo, nombre, descripcion, activo,
               (SELECT COUNT(*) FROM rida.cat_articulo a WHERE a.id_categoria_ayuda = c.id_categoria_ayuda AND a.activo = TRUE) as n_articulos
        FROM rida.cat_categoria_ayuda c
        WHERE id_categoria_ayuda = :id
    """, {"id": id_categoria})


def get_categoria_con_articulos(db: Session, id_categoria: int) -> dict | None:
    cat = get_categoria(db, id_categoria)
    if not cat:
        return None
    articulos, _ = listar_articulos(db, {"id_categoria_ayuda": id_categoria, "activo": True}, todos=True)
    cat["articulos"] = articulos
    return cat


def crear_categoria(db: Session, data: dict) -> dict:
    result = _row(db, """
        INSERT INTO rida.cat_categoria_ayuda (codigo, nombre, descripcion, activo)
        VALUES (:codigo, :nombre, :descripcion, :activo)
        RETURNING id_categoria_ayuda
    """, {
        "codigo": data.get("codigo"),
        "nombre": data["nombre"],
        "descripcion": data.get("descripcion"),
        "activo": data.get("activo", True)
    })
    db.commit()
    return get_categoria(db, result["id_categoria_ayuda"])


def actualizar_categoria(db: Session, id_categoria: int, data: dict) -> dict | None:
    fields, params = [], {"id": id_categoria}
    for col in ("nombre", "descripcion", "activo"):
        if col in data and data[col] is not None:
            fields.append(f"{col} = :{col}")
            params[col] = data[col]
    if not fields:
        return get_categoria(db, id_categoria)
    db.execute(text(f"UPDATE rida.cat_categoria_ayuda SET {', '.join(fields)} WHERE id_categoria_ayuda = :id"), params)
    db.commit()
    return get_categoria(db, id_categoria)


def eliminar_categoria(db: Session, id_categoria: int) -> bool:
    row = _row(db, "SELECT 1 FROM rida.cat_categoria_ayuda WHERE id_categoria_ayuda = :id", {"id": id_categoria})
    if not row:
        return False
    db.execute(text("DELETE FROM rida.cat_categoria_ayuda WHERE id_categoria_ayuda = :id"), {"id": id_categoria})
    db.commit()
    return True


# ============================================================================
#  CATÁLOGOS - ARTÍCULOS
# ============================================================================

def listar_articulos(db: Session, filters: dict | None = None,
                     skip: int = 0, limit: int = 500, todos: bool = False) -> tuple[list[dict], int]:
    f = filters or {}
    conds = ["1=1"]
    count_params: dict[str, Any] = {}
    params: dict[str, Any] = {}
    
    if f.get("id_categoria_ayuda"):
        conds.append("a.id_categoria_ayuda = :id_categoria_ayuda")
        params["id_categoria_ayuda"] = f["id_categoria_ayuda"]
    if "activo" in f:
        conds.append("a.activo = :activo")
        params["activo"] = f["activo"]
    if f.get("q"):
        conds.append("a.nombre ILIKE :q")
        params["q"] = f"%{f['q']}%"
    
    where = " AND ".join(conds)
    total_sql = f"""
        SELECT COUNT(*) FROM rida.cat_articulo a
        JOIN rida.cat_categoria_ayuda c ON c.id_categoria_ayuda = a.id_categoria_ayuda
        WHERE {where}
    """
    total = db.execute(text(total_sql), params).scalar() or 0
    page = "" if todos else "LIMIT :limit OFFSET :skip"
    page_params: dict[str, Any] = {}
    if not todos:
        page_params = {"limit": limit, "skip": skip}
    sql = f"""
        SELECT a.id_articulo, a.id_categoria_ayuda, a.codigo, a.nombre, 
               a.unidad_de_medida, a.peso_unitario_kg, a.costo_referencia_bs, a.activo,
               c.nombre as categoria_nombre
        FROM rida.cat_articulo a
        JOIN rida.cat_categoria_ayuda c ON c.id_categoria_ayuda = a.id_categoria_ayuda
        WHERE {where}
        ORDER BY a.nombre
        {page}
    """
    return _rows(db, sql, params | page_params), total


def get_articulo(db: Session, id_articulo: int) -> dict | None:
    return _row(db, """
        SELECT a.id_articulo, a.id_categoria_ayuda, a.codigo, a.nombre, 
               a.unidad_de_medida, a.peso_unitario_kg, a.costo_referencia_bs, a.activo,
               c.nombre as categoria_nombre
        FROM rida.cat_articulo a
        JOIN rida.cat_categoria_ayuda c ON c.id_categoria_ayuda = a.id_categoria_ayuda
        WHERE a.id_articulo = :id
    """, {"id": id_articulo})


def crear_articulo(db: Session, data: dict) -> dict:
    result = _row(db, """
        INSERT INTO rida.cat_articulo (id_categoria_ayuda, codigo, nombre, peso_unitario_kg, costo_referencia_bs, activo)
        VALUES (:id_categoria_ayuda, :codigo, :nombre, :peso, :costo, :activo)
        RETURNING id_articulo
    """, {
        "id_categoria_ayuda": data["id_categoria_ayuda"],
        "codigo": data.get("codigo"),
        "nombre": data["nombre"],
        "peso": data.get("peso_unitario_kg"),
        "costo": data.get("costo_referencia_bs"),
        "activo": data.get("activo", True)
    })
    db.commit()
    return get_articulo(db, result["id_articulo"])


def actualizar_articulo(db: Session, id_articulo: int, data: dict) -> dict | None:
    fields, params = [], {"id": id_articulo}
    for col in ("id_categoria_ayuda", "nombre", "peso_unitario_kg", "costo_referencia_bs", "activo"):
        if col in data and data[col] is not None:
            fields.append(f"{col} = :{col}")
            params[col] = data[col]
    if not fields:
        return get_articulo(db, id_articulo)
    db.execute(text(f"UPDATE rida.cat_articulo SET {', '.join(fields)} WHERE id_articulo = :id"), params)
    db.commit()
    return get_articulo(db, id_articulo)


def eliminar_articulo(db: Session, id_articulo: int) -> bool:
    row = _row(db, "SELECT 1 FROM rida.cat_articulo WHERE id_articulo = :id", {"id": id_articulo})
    if not row:
        return False
    db.execute(text("DELETE FROM rida.cat_articulo WHERE id_articulo = :id"), {"id": id_articulo})
    db.commit()
    return True


# ============================================================================
#  VALIDACIONES
# ============================================================================

def validar_articulo_pertenece_categoria(db: Session, id_articulo: int, id_categoria: int) -> bool:
    row = _row(db, """
        SELECT 1 FROM rida.cat_articulo 
        WHERE id_articulo = :id AND id_categoria_ayuda = :cat
    """, {"id": id_articulo, "cat": id_categoria})
    return row is not None


def validar_categoria_existe(db: Session, id_categoria: int) -> bool:
    return _row(db, "SELECT 1 FROM rida.cat_categoria_ayuda WHERE id_categoria_ayuda = :id", {"id": id_categoria}) is not None


def validar_articulo_existe(db: Session, id_articulo: int) -> bool:
    return _row(db, "SELECT 1 FROM rida.cat_articulo WHERE id_articulo = :id", {"id": id_articulo}) is not None


# ============================================================================
#  NECESIDADES
# ============================================================================

def listar_necesidades(db: Session, filters: dict, skip: int = 0, limit: int = 500,
                       todos: bool = False) -> tuple[list[dict], int]:
    f = filters or {}
    conds = ["1=1"]
    params: dict[str, Any] = {}
    
    id_familia = f.get("id_familia")
    if id_familia is not None:
        conds.append("n.id_familia = :id_familia")
        params["id_familia"] = id_familia
    
    id_formulario = f.get("id_formulario")
    if id_formulario is not None:
        conds.append("n.id_formulario = :id_formulario")
        params["id_formulario"] = id_formulario
    
    if "estado" in f and f["estado"] is not None:
        conds.append("n.estado = :estado")
        params["estado"] = f["estado"]
    
    id_categoria = f.get("id_categoria_ayuda")
    if id_categoria is not None:
        conds.append("n.id_categoria_ayuda = :id_categoria_ayuda")
        params["id_categoria_ayuda"] = id_categoria
    
    # Filtros geográficos vía familia → formulario → localidad
    if f.get("id_municipio"):
        conds.append("el.id_municipio = :id_municipio")
        params["id_municipio"] = f["id_municipio"]
    if f.get("id_provincia"):
        conds.append("el.id_provincia = :id_provincia")
        params["id_provincia"] = f["id_provincia"]
    if f.get("id_departamento"):
        conds.append("el.id_departamento = :id_departamento")
        params["id_departamento"] = f["id_departamento"]
    
    where = " AND ".join(conds)
    
    # JOINs para filtros geográficos
    joins = """
    LEFT JOIN rida.familia fa ON fa.id_familia = n.id_familia
    LEFT JOIN edan.edan_localidades el ON el.id_edan_localidad = fa.id_edan_localidad
    """
    
    count_sql = f"SELECT COUNT(*) FROM rida.necesidad n {joins} WHERE {where}"
    total = db.execute(text(count_sql), params).scalar() or 0
    
    page = "" if todos else "LIMIT :limit OFFSET :skip"
    page_params: dict[str, Any] = {}
    if not todos:
        page_params = {"limit": limit, "skip": skip}
    data_sql = f"""
        SELECT n.id_necesidad, n.id_familia, n.id_formulario, n.id_necesidad_off,
               n.id_articulo, a.nombre as articulo_nombre, a.codigo as articulo_codigo,
               n.id_categoria_ayuda, c.nombre as categoria_nombre,
               a.unidad_de_medida, n.cantidad, n.prioridad, n.estado,
               n.fecha_creacion, n.fecha_modificacion
        FROM rida.necesidad n
        {joins}
        JOIN rida.cat_articulo a ON a.id_articulo = n.id_articulo
        JOIN rida.cat_categoria_ayuda c ON c.id_categoria_ayuda = n.id_categoria_ayuda
        WHERE {where}
        ORDER BY n.prioridad ASC, n.fecha_creacion DESC
        {page}
    """
    data = _rows(db, data_sql, params | page_params)
    return data, total


def get_necesidad(db: Session, id_necesidad: int) -> dict | None:
    return _row(db, """
        SELECT n.id_necesidad, n.id_familia, n.id_formulario, n.id_necesidad_off,
               n.id_articulo, a.nombre as articulo_nombre, a.codigo as articulo_codigo,
               n.id_categoria_ayuda, c.nombre as categoria_nombre,
               a.unidad_de_medida, n.cantidad, n.prioridad, n.estado,
               n.fecha_creacion, n.fecha_modificacion
        FROM rida.necesidad n
        JOIN rida.cat_articulo a ON a.id_articulo = n.id_articulo
        JOIN rida.cat_categoria_ayuda c ON c.id_categoria_ayuda = n.id_categoria_ayuda
        WHERE n.id_necesidad = :id
    """, {"id": id_necesidad})


def crear_necesidad(db: Session, data: dict, user_id: int | None = None) -> dict:
    id_articulo = data["id_articulo"]
    id_categoria = data["id_categoria_ayuda"]
    
    if not validar_articulo_existe(db, id_articulo):
        raise HTTPException(status_code=400, detail=f"El artículo {id_articulo} no existe")
    if not validar_categoria_existe(db, id_categoria):
        raise HTTPException(status_code=400, detail=f"La categoría {id_categoria} no existe")
    if not validar_articulo_pertenece_categoria(db, id_articulo, id_categoria):
        raise HTTPException(status_code=400, detail=f"El artículo {id_articulo} no pertenece a la categoría {id_categoria}")
    
    id_familia = data.get("id_familia")
    id_formulario = data.get("id_formulario")
    
    if not id_familia and not id_formulario:
        raise HTTPException(status_code=400, detail="Se requiere id_familia o id_formulario")
    
    if id_familia:
        fam = _row(db, "SELECT id_formulario FROM rida.familia WHERE id_familia = :id", {"id": id_familia})
        if not fam:
            raise HTTPException(status_code=404, detail=f"La familia {id_familia} no existe")
        id_formulario = fam["id_formulario"]
    else:
        frm = _row(db, "SELECT 1 FROM rida.formulario_rida WHERE id_formulario = :id", {"id": id_formulario})
        if not frm:
            raise HTTPException(status_code=404, detail=f"El formulario {id_formulario} no existe")
    
    result = _row(db, """
        INSERT INTO rida.necesidad 
            (id_familia, id_formulario, id_categoria_ayuda, id_articulo, cantidad, prioridad, estado, id_necesidad_off)
        VALUES 
            (:id_familia, :id_formulario, :id_categoria, :id_articulo, :cantidad, :prioridad, :estado, :id_off)
        RETURNING id_necesidad
    """, {
        "id_familia": id_familia,
        "id_formulario": id_formulario,
        "id_categoria": id_categoria,
        "id_articulo": id_articulo,
        "cantidad": data["cantidad"],
        "prioridad": data.get("prioridad", 3),
        "estado": data.get("estado", False),
        "id_off": data.get("id_necesidad_off")
    })
    db.commit()
    return get_necesidad(db, result["id_necesidad"])


def actualizar_necesidad(db: Session, id_necesidad: int, data: dict) -> dict | None:
    existente = get_necesidad(db, id_necesidad)
    if not existente:
        return None
    
    id_articulo = data.get("id_articulo")
    id_categoria = data.get("id_categoria_ayuda")
    
    if id_articulo is not None or id_categoria is not None:
        id_articulo = id_articulo or existente["id_articulo"]
        id_categoria = id_categoria or existente["id_categoria_ayuda"]
        if not validar_articulo_pertenece_categoria(db, id_articulo, id_categoria):
            raise HTTPException(status_code=400, detail=f"El artículo {id_articulo} no pertenece a la categoría {id_categoria}")
    
    fields, params = [], {"id": id_necesidad}
    for col in ("id_familia", "id_articulo", "id_categoria_ayuda", "cantidad", "prioridad", "estado"):
        if col in data and data[col] is not None:
            fields.append(f"{col} = :{col}")
            params[col] = data[col]
    
    if fields:
        fields.append("fecha_modificacion = NOW()")
        db.execute(text(f"UPDATE rida.necesidad SET {', '.join(fields)} WHERE id_necesidad = :id"), params)
        db.commit()
    
    return get_necesidad(db, id_necesidad)


def eliminar_necesidad(db: Session, id_necesidad: int) -> bool:
    row = _row(db, "SELECT 1 FROM rida.necesidad WHERE id_necesidad = :id", {"id": id_necesidad})
    if not row:
        return False
    db.execute(text("DELETE FROM rida.necesidad WHERE id_necesidad = :id"), {"id": id_necesidad})
    db.commit()
    return True


# ============================================================================
#  SYNC OFFLINE
# ============================================================================

def sync_necesidades(db: Session, batch: list[dict], user_id: int | None = None) -> dict:
    resultados = []
    errores = []
    
    for item in batch:
        try:
            id_familia = None
            id_formulario = item.get("id_formulario")
            
            if item.get("id_familia_off"):
                fam = _row(db, "SELECT id_familia, id_formulario FROM rida.familia WHERE id_familia_off = :off", {"off": item["id_familia_off"]})
                if fam:
                    id_familia = fam["id_familia"]
                    id_formulario = fam["id_formulario"]
                else:
                    raise HTTPException(status_code=400, detail=f"Familia offline '{item['id_familia_off']}' no encontrada")
            elif item.get("id_familia"):
                id_familia = item["id_familia"]
                fam = _row(db, "SELECT id_formulario FROM rida.familia WHERE id_familia = :id", {"id": id_familia})
                if fam:
                    id_formulario = fam["id_formulario"]
            
            if not id_formulario:
                raise HTTPException(status_code=400, detail="No se pudo resolver id_formulario")
            
            data = {
                "id_familia": id_familia,
                "id_formulario": id_formulario,
                "id_articulo": item.get("id_articulo"),
                "id_categoria_ayuda": item.get("id_categoria_ayuda"),
                "cantidad": item.get("cantidad"),
                "prioridad": item.get("prioridad", 3),
                "estado": item.get("estado", False),
                "id_necesidad_off": item.get("id_necesidad_off"),
            }
            
            if item.get("id_necesidad_off"):
                existente = _row(db, "SELECT id_necesidad FROM rida.necesidad WHERE id_necesidad_off = :off", {"off": item["id_necesidad_off"]})
                if existente:
                    data["id_articulo"] = item.get("id_articulo", data["id_articulo"])
                    data["id_categoria_ayuda"] = item.get("id_categoria_ayuda", data["id_categoria_ayuda"])
                    data["cantidad"] = item.get("cantidad", data["cantidad"])
                    data["prioridad"] = item.get("prioridad", data["prioridad"])
                    data["estado"] = item.get("estado", data["estado"])
                    
                    fields, params = [], {"id": existente["id_necesidad"]}
                    for col in ("id_familia", "id_formulario", "id_articulo", "id_categoria_ayuda", "cantidad", "prioridad", "estado"):
                        if data.get(col) is not None:
                            fields.append(f"{col} = :{col}")
                            params[col] = data[col]
                    if fields:
                        fields.append("fecha_modificacion = NOW()")
                        db.execute(text(f"UPDATE rida.necesidad SET {', '.join(fields)} WHERE id_necesidad = :id"), params)
                        db.commit()
                    
                    resultados.append({
                        "id_necesidad_off": item["id_necesidad_off"],
                        "id_necesidad": existente["id_necesidad"],
                        "aplicado": True,
                        "operacion": "UPDATE"
                    })
                    continue
            
            resultado = crear_necesidad(db, data, user_id)
            resultados.append({
                "id_necesidad_off": item.get("id_necesidad_off"),
                "id_necesidad": resultado["id_necesidad"],
                "aplicado": True,
                "operacion": "CREATE"
            })
            
        except HTTPException as e:
            errores.append({
                "id_necesidad_off": item.get("id_necesidad_off"),
                "error": str(e.detail),
                "aplicado": False
            })
        except Exception as e:
            errores.append({
                "id_necesidad_off": item.get("id_necesidad_off"),
                "error": str(e),
                "aplicado": False
            })
    
    return {"necesidades": resultados, "errores": errores}
