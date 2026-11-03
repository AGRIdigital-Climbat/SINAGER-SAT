import json
"""
Servicio NDVI Satelital - Funciones para consultas y procesamiento de NDVI desde Sentinel-2
"""
from datetime import date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import HTTPException
import random


def _row(db, query, params=None):
    """Helper para obtener una fila."""
    result = db.execute(text(query), params or {})
    return result.mappings().first()


def _rows(db, query, params=None):
    """Helper para obtener múltiples filas."""
    result = db.execute(text(query), params or {})
    return result.mappings().all()


def _execute(db, query, params=None):
    """Helper para ejecutar query sin retorno."""
    result = db.execute(text(query), params or {})
    return result.rowcount


def _serialize(obj):
    """Serializar tipos especiales a JSON-compatible."""
    from uuid import UUID
    from datetime import datetime, date
    from sqlalchemy.engine.row import RowMapping
    from decimal import Decimal
    
    if obj is None:
        return None
    if isinstance(obj, RowMapping):
        return dict(obj)
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serialize(item) for item in obj]
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    return obj



def get_ultimo_ndvi_comunidad(db: Session, codigo_comunidad: str | None = None):
    """
    Obtener último NDVI disponible por comunidad.
    
    Args:
        db: Sesión de base de datos
        codigo_comunidad: Filtro por código de comunidad (opcional)
    
    Returns:
        Lista de comunidades con último NDVI
    """
    params = {}
    where = "1=1"
    
    if codigo_comunidad:
        where = "codigo_comunidad = :codigo_comunidad"
        params["codigo_comunidad"] = codigo_comunidad
    
    rows = _rows(db, f"""
        SELECT * FROM sinb.vw_ultimo_ndvi_comunidad
        WHERE {where}
        ORDER BY ndvi_promedio ASC
    """, params)
    
    return _serialize(rows)


def get_evolucion_mensual_ndvi(
    db: Session,
    codigo_comunidad: str | None = None,
    meses: int = 12
):
    """
    Obtener evolución mensual de NDVI.
    
    Args:
        db: Sesión de base de datos
        codigo_comunidad: Filtro por comunidad
        meses: Número de meses hacia atrás
    
    Returns:
        Serie mensual de NDVI
    """
    params = {"meses": meses}
    where = "1=1"
    
    if codigo_comunidad:
        where = "codigo_comunidad = :codigo_comunidad"
        params["codigo_comunidad"] = codigo_comunidad
    
    rows = _rows(db, f"""
        SELECT * FROM sinb.vw_evolucion_mensual_ndvi
        WHERE {where}
        ORDER BY mes DESC
    """, params)
    
    return _serialize(rows)


def get_alertas_ndvi(
    db: Session,
    departamento: str | None = None,
    provincia: str | None = None,
    municipio: str | None = None
):
    """
    Obtener alertas activas de NDVI bajo.
    
    Args:
        db: Sesión de base de datos
        departamento: Filtro por departamento
        provincia: Filtro por provincia
        municipio: Filtro por municipio
    
    Returns:
        Lista de comunidades en alerta
    """
    rows = _rows(db, """
        SELECT * FROM sinb.vw_alertas_ndvi
        ORDER BY nivel_prioridad, ndvi_anomalia ASC
    """)
    
    # Filtrar en Python si hay filtros geográficos
    resultado = _serialize(rows)
    
    if departamento or provincia or municipio:
        resultado = [
            r for r in resultado
            if (not departamento or r.get('departamento', '').lower() == departamento.lower())
            and (not provincia or r.get('provincia', '').lower() == provincia.lower())
            and (not municipio or r.get('municipio', '').lower() == municipio.lower())
        ]
    
    return resultado


def get_series_ndvi(
    db: Session,
    codigo_comunidad: str,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    limit: int = 365
):
    """
    Obtener serie temporal de NDVI para una comunidad.
    
    Args:
        db: Sesión de base de datos
        codigo_comunidad: Código de comunidad (requerido)
        fecha_desde: Fecha de inicio
        fecha_hasta: Fecha fin
        limit: Límite de registros
    
    Returns:
        Serie temporal de NDVI
    """
    params = {"codigo_comunidad": codigo_comunidad, "limit": limit}
    where = ["s.codigo_comunidad = :codigo_comunidad"]
    
    if fecha_desde:
        where.append("s.fecha >= :fecha_desde")
        params["fecha_desde"] = fecha_desde
    
    if fecha_hasta:
        where.append("s.fecha <= :fecha_hasta")
        params["fecha_hasta"] = fecha_hasta
    
    where_clause = " AND ".join(where)
    
    rows = _rows(db, f"""
        SELECT 
            s.fecha,
            s.ndvi_promedio,
            s.ndvi_anomalia,
            s.estado_vegetacion,
            s.n_escenas
        FROM sinb.serie_ndvi_comunidad s
        WHERE {where_clause}
        ORDER BY s.fecha DESC
        LIMIT :limit
    """, params)
    
    return _serialize(rows)


def get_escenas_satelitales(
    db: Session,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    cobertura_nubes_max: float | None = None,
    skip: int = 0,
    limit: int = 100,
    todos: bool = False
):
    """
    Obtener escenas satelitales procesadas.
    
    Args:
        db: Sesión de base de datos
        fecha_desde: Fecha de inicio
        fecha_hasta: Fecha fin
        cobertura_nubes_max: Máxima cobertura de nubes (%)
        skip: Registros a saltar
        limit: Límite de resultados
        todos: True = conjunto completo sin LIMIT/OFFSET
    
    Returns:
        Lista de escenas satelitales
    """
    params = {}
    if not todos:
        params = {"skip": skip, "limit": limit}
    where = ["1=1"]
    
    if fecha_desde:
        where.append("fecha_adquisicion >= :fecha_desde")
        params["fecha_desde"] = fecha_desde
    
    if fecha_hasta:
        where.append("fecha_adquisicion <= :fecha_hasta")
        params["fecha_hasta"] = fecha_hasta
    
    if cobertura_nubes_max is not None:
        where.append("cobertura_nubes <= :cobertura_nubes_max")
        params["cobertura_nubes_max"] = cobertura_nubes_max
    
    where_clause = " AND ".join(where)
    
    # cantidad → paginación; todos=True → sin LIMIT/OFFSET
    page = "" if todos else " LIMIT :limit OFFSET :skip"

    rows = _rows(db, f"""
        SELECT 
            id,
            producto,
            escena_id,
            fecha_adquisicion,
            fecha_proceso,
            cobertura_nubes,
            ST_AsGeoJSON(huella) as huella,
            metadata
        FROM sinb.escena_satelital
        WHERE {where_clause}
        ORDER BY fecha_adquisicion DESC
        {page}
    """, params)
    
    # Convertir geometría de GeoJSON string a dict
    resultado = []
    for row in rows:
        d = dict(row)
        if d.get('huella'):
            import json
            d['huella'] = json.loads(d['huella'])
        resultado.append(d)
    
    # Obtener total
    total_row = _row(db, f"""
        SELECT COUNT(*) as total
        FROM sinb.escena_satelital
        WHERE {where_clause}
    """, {k: v for k, v in params.items() if k not in ['skip', 'limit']})
    
    return {"data": resultado, "total": total_row["total"] if total_row else 0}


def get_ndvi_por_rango_fechas(
    db: Session,
    codigo_comunidad: str,
    fecha_desde: date,
    fecha_hasta: date
):
    """
    Obtener NDVI promedio en rango de fechas.
    
    Args:
        db: Sesión de base de datos
        codigo_comunidad: Código de comunidad
        fecha_desde: Fecha de inicio
        fecha_hasta: Fecha fin
    
    Returns:
        Estadísticas de NDVI en el período
    """
    params = {
        "codigo_comunidad": codigo_comunidad,
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta
    }
    
    row = _row(db, """
        SELECT 
            avg(ndvi_promedio) as ndvi_promedio,
            min(ndvi_promedio) as ndvi_min,
            max(ndvi_promedio) as ndvi_max,
            avg(ndvi_anomalia) as anomalia_promedio,
            count(*) as n_dias
        FROM sinb.serie_ndvi_comunidad
        WHERE codigo_comunidad = :codigo_comunidad
          AND fecha BETWEEN :fecha_desde AND :fecha_hasta
    """, params)
    
    return dict(row) if row else None


def consultar_earthsearch(
    bbox: tuple,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    max_nubes: float = 20.0
):
    """
    Consultar EarthSearch STAC API por escenas Sentinel-2.
    
    Args:
        bbox: Tupla (min_lon, min_lat, max_lon, max_lat)
        fecha_desde: Fecha de inicio
        fecha_hasta: Fecha fin
        max_nubes: Máxima cobertura de nubes (%)
    
    Returns:
        Features de EarthSearch STAC
    """
    import requests
    from datetime import datetime
    
    # EarthSearch STAC API endpoint
    url = "https://earth-search.aws.element84.com/v1/search"
    
    # Construir query
    query = {
        "collections": ["sentinel-2-l2a"],
        "bbox": list(bbox),
        "limit": 100
    }
    
    # Filtro temporal
    if fecha_desde and fecha_hasta:
        query["datetime"] = f"{fecha_desde.isoformat()}T00:00:00Z/{fecha_hasta.isoformat()}T23:59:59Z"
    elif fecha_desde:
        query["datetime"] = f"{fecha_desde.isoformat()}T00:00:00Z/"
    else:
        # Últimos 5 días por defecto
        from datetime import timedelta
        fecha_hasta = date.today()
        fecha_desde = fecha_hasta - timedelta(days=5)
        query["datetime"] = f"{fecha_desde.isoformat()}T00:00:00Z/{fecha_hasta.isoformat()}T23:59:59Z"
    
    # Hacer request
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, json=query, headers=headers, timeout=30)
    
    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Error consultando EarthSearch: {response.status_code}"
        )
    
    data = response.json()
    features = data.get("features", [])
    
    # Filtrar por cobertura de nubes
    features_filtrados = [
        f for f in features
        if f.get("properties", {}).get("eo:cloud_cover", 100) <= max_nubes
    ]
    
    return features_filtrados


def procesar_escena_ndvi(
    db: Session,
    escena_feature: dict,
    codigo_comunidad: str,
    bbox: tuple
):
    """
    Procesar escena Sentinel-2 y calcular NDVI para una comunidad.
    
    NOTA: Implementación simplificada - en producción usar rasterio para
    cálculo real desde bandas. Aquí se simula con valor aleatorio para
    propósitos de demostración.
    
    Args:
        db: Sesión de base de datos
        escena_feature: Feature de EarthSearch
        codigo_comunidad: Código de comunidad
        bbox: Bounding box de la comunidad
    
    Returns:
        Diccionario con resultados del procesamiento
    """
    from datetime import date
    import random
    
    props = escena_feature.get("properties", {})
    escena_id = escena_feature.get("id", props.get("id"))
    fecha_adquisicion = props.get("datetime", "")[:10]
    cobertura_nubes = props.get("eo:cloud_cover", 0)
    
    # Registrar escena
    escena_row = _row(db, """
        INSERT INTO sinb.escena_satelital (escena_id, fecha_adquisicion, cobertura_nubes, metadata)
        VALUES (:escena_id, :fecha, :nubes, :metadata)
        ON CONFLICT (escena_id) DO UPDATE SET
            cobertura_nubes = EXCLUDED.cobertura_nubes,
            fecha_proceso = now()
        RETURNING id
    """, {
        "escena_id": escena_id,
        "fecha": fecha_adquisicion,
        "nubes": cobertura_nubes,
        "metadata": json.dumps(props)
    })
    
    if not escena_row:
        return None
    
    id_escena = escena_row["id"]
    
    # Calcular NDVI simulado (en producción: cálculo real con rasterio)
    # Valor entre 0.1 y 0.8, afectado por nubes
    base_ndvi = random.uniform(0.3, 0.7)
    ndvi = max(0.1, min(0.9, base_ndvi - (cobertura_nubes / 1000)))
    
    # Actualizar agregado por comunidad
    _row(db, """
        INSERT INTO sinb.agregado_satelital 
            (id_escena_satelital, codigo_comunidad, ndvi_promedio, pixeles_validos)
        VALUES (:id_escena, :codigo, :ndvi, :pixeles)
        ON CONFLICT (id_escena_satelital, codigo_comunidad) DO UPDATE SET
            ndvi_promedio = EXCLUDED.ndvi_promedio,
            pixeles_validos = EXCLUDED.pixeles_validos
        RETURNING id
    """, {
        "id_escena": id_escena,
        "codigo": codigo_comunidad,
        "ndvi": ndvi,
        "pixeles": random.randint(100, 10000)
    })
    
    # Actualizar serie temporal
    db.execute(text("""
        SELECT sinb.actualizar_serie_ndvi_comunidad(
            :codigo_comunidad, 
            :fecha, 
            :ndvi
        )
    """), {
        "codigo_comunidad": codigo_comunidad,
        "fecha": fecha_adquisicion,
        "ndvi": ndvi
    })
    db.commit()
    
    return {
        "escena_id": escena_id,
        "fecha": fecha_adquisicion,
        "ndvi": ndvi,
        "cobertura_nubes": cobertura_nubes
    }


def ingestar_ndvi_comunidades(
    db: Session,
    codigos_comunidades: list[str] | None = None,
    max_nubes: float = 20.0
):
    """
    Ingestar NDVI para comunidades desde EarthSearch.
    
    Args:
        db: Sesión de base de datos
        codigos_comunidades: Lista de códigos de comunidad (None = todas)
        max_nubes: Máxima cobertura de nubes (%)
    
    Returns:
        Resumen del procesamiento
    """
    from datetime import date, timedelta
    
    # Iniciar log de procesamiento
    log_id = db.execute(text("""
        INSERT INTO sinb.ndvi_procesamiento_log (fecha_proceso, estado)
        VALUES (:fecha, 'en_progreso')
        RETURNING id
    """), {"fecha": date.today()}).scalar()
    db.commit()
    
    resultados = {
        "escenas_consultadas": 0,
        "escenas_procesadas": 0,
        "comunidades_procesadas": 0,
        "errores": []
    }
    
    try:
        # Obtener comunidades a procesar
        if codigos_comunidades:
            codigos = codigos_comunidades
        else:
            # Obtener todas las comunidades
            rows = _rows(db, "SELECT codigo_ine, lat, lon FROM shared.comunidades")
            codigos = [dict(r)["codigo_ine"] for r in rows]
        
        # Bounding box de Bolivia (aproximado)
        bbox_bolivia = (-70.0, -23.0, -57.0, -9.0)
        
        # Consultar EarthSearch
        fecha_desde = date.today() - timedelta(days=5)
        features = consultar_earthsearch(bbox_bolivia, fecha_desde, date.today(), max_nubes)
        resultados["escenas_consultadas"] = len(features)
        
        # Procesar cada escena para cada comunidad
        for comunidad_codigo in codigos:  # TODAS las comunidades
            # Obtener bbox de comunidad
            com_row = _row(db, """
                SELECT lat, lon FROM shared.comunidades
                WHERE codigo_ine = :codigo
            """, {"codigo": comunidad_codigo})
            
            if not com_row:
                continue
            
            # Bbox pequeño alrededor de la comunidad (0.1 grados)
            lat, lon = float(com_row["lat"]), float(com_row["lon"])
            bbox_comunidad = (
                lon - 0.05, lat - 0.05,
                lon + 0.05, lat + 0.05
            )
            
            # Procesar escenas para esta comunidad
            for feature in features:  # TODAS las escenas
                try:
                    resultado = procesar_escena_ndvi(
                        db, feature, comunidad_codigo, bbox_comunidad
                    )
                    if resultado:
                        resultados["escenas_procesadas"] += 1
                except Exception as e:
                    resultados["errores"].append(str(e))
            
            resultados["comunidades_procesadas"] += 1
        
        # Actualizar log
        db.execute(text("""
            UPDATE sinb.ndvi_procesamiento_log
            SET hora_fin = now(),
                estado = 'completado',
                escenas_consultadas = :consultadas,
                escenas_descargadas = :procesadas,
                comunidades_procesadas = :comunidades
            WHERE id = :log_id
        """), {
            "consultadas": resultados["escenas_consultadas"],
            "procesadas": resultados["escenas_procesadas"],
            "comunidades": resultados["comunidades_procesadas"],
            "log_id": log_id
        })
        db.commit()
        
    except Exception as e:
        db.execute(text("""
            UPDATE sinb.ndvi_procesamiento_log
            SET hora_fin = now(),
                estado = 'error',
                error_mensaje = :error
            WHERE id = :log_id
        """), {"error": str(e), "log_id": log_id})
        db.commit()
        resultados["errores"].append(str(e))
    
    return resultados


def get_log_procesamiento_ndvi(
    db: Session,
    fecha_desde: date | None = None,
    limit: int = 30
):
    """
    Obtener log de procesamiento NDVI.
    
    Args:
        db: Sesión de base de datos
        fecha_desde: Fecha de inicio
        limit: Límite de registros
    
    Returns:
        Log de procesamiento
    """
    params = {"limit": limit}
    where = "1=1"
    
    if fecha_desde:
        where = "fecha_proceso >= :fecha_desde"
        params["fecha_desde"] = fecha_desde
    
    rows = _rows(db, f"""
        SELECT 
            fecha_proceso,
            hora_inicio,
            hora_fin,
            estado,
            escenas_consultadas,
            escenas_descargadas,
            comunidades_procesadas,
            error_mensaje
        FROM sinb.ndvi_procesamiento_log
        WHERE {where}
        ORDER BY fecha_proceso DESC
        LIMIT :limit
    """, params)
    
    return _serialize(rows)
