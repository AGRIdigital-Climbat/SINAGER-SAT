"""
Router NDVI Satelital - Series históricas de vegetación desde Sentinel-2
"""
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from datetime import date
from typing import Optional

from ..database import get_db
from ..dependencies import get_current_user
from ..response import SuccessResponse
from . import service_ndvi as service
from .schemas import (
    NDVIComunidadResponse,
    NDVIEvolucionResponse,
    NDVIAlertaResponse,
    NDTVITemporalResponse,
    EscenaSatelitalResponse,
    NDVIProcesamientoLogResponse,
    NDVIIngestarRequest,
    NDVIIngestarResponse,
)


router = APIRouter(prefix="/ndvi", tags=["SINB > NDVI Satelital"])


def _row(db, query, params=None):
    """Helper para obtener una fila."""
    from sqlalchemy import text
    result = db.execute(text(query), params or {})
    return result.mappings().first()


def _rows(db, query, params=None):
    """Helper para obtener múltiples filas."""
    from sqlalchemy import text
    result = db.execute(text(query), params or {})
    return result.mappings().all()


# ============================================================================
# CONSULTAS DE NDVI
# ============================================================================

@router.get("/comunidad", response_model=SuccessResponse)
def get_ultimo_ndvi_comunidades(
    codigo_comunidad: Optional[str] = Query(None, description="Filtro por código de comunidad"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    **Último NDVI disponible por comunidad**.
    
    Muestra el valor más reciente de NDVI para cada comunidad,
    incluyendo anomalía vs. histórico y estado de alerta.
    
    **Útil para:**
    - Monitoreo rápido del estado de vegetación
    - Detección de comunidades con sequía
    - Dashboard nacional/departamental
    
    **Respuesta incluye:**
    - NDVI promedio (-1 a 1)
    - Anomalía (desviación del histórico)
    - Estado de vegetación (seco, bajo, normal, alto, muy_alto)
    - Estado de alerta (alerta_roja, alerta_amarilla, normal, muy_bien)
    """
    data = service.get_ultimo_ndvi_comunidad(db, codigo_comunidad)
    
    return SuccessResponse(
        message="Último NDVI por comunidad",
        data=data,
        total=len(data)
    )


@router.get("/comunidad/{codigo_comunidad}/evolucion", response_model=SuccessResponse)
def get_evolucion_comunidad(
    codigo_comunidad: str,
    meses: int = Query(12, ge=1, le=60, description="Meses hacia atrás"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    **Evolución mensual de NDVI para una comunidad**.
    
    Muestra la tendencia mensual de NDVI para análisis de largo plazo.
    
    **Útil para:**
    - Ver tendencia estacional
    - Comparar años diferentes
    - Detectar cambios de uso de suelo
    """
    data = service.get_evolucion_mensual_ndvi(db, codigo_comunidad, meses)
    
    return SuccessResponse(
        message=f"Evolución de {codigo_comunidad} ({len(data)} meses)",
        data=data
    )


@router.get("/comunidad/{codigo_comunidad}/serie", response_model=SuccessResponse)
def get_serie_temporal(
    codigo_comunidad: str,
    fecha_desde: Optional[date] = Query(None, description="Fecha de inicio"),
    fecha_hasta: Optional[date] = Query(None, description="Fecha fin"),
    limit: int = Query(365, ge=1, le=1000, description="Límite de registros"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    **Serie temporal completa de NDVI para una comunidad**.
    
    Datos diarios de NDVI con anomalías y estado de vegetación.
    
    **Útil para:**
    - Gráficos de series temporales
    - Análisis estadístico detallado
    - Validación con observaciones de campo
    """
    data = service.get_series_ndvi(
        db, codigo_comunidad, fecha_desde, fecha_hasta, limit
    )
    
    return SuccessResponse(
        message=f"Serie temporal de {codigo_comunidad} ({len(data)} registros)",
        data=data
    )


@router.get("/alertas", response_model=SuccessResponse)
def get_alertas_ndvi(
    departamento: Optional[str] = Query(None, description="Filtro por departamento"),
    provincia: Optional[str] = Query(None, description="Filtro por provincia"),
    municipio: Optional[str] = Query(None, description="Filtro por municipio"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    **Alertas activas de NDVI bajo**.
    
    Comunidades con NDVI por debajo de umbrales normales o con
    anomalía negativa significativa (últimos 7 días).
    
    **Niveles de prioridad:**
    1. sequia_extrema (NDVI < 0.2)
    2. sequia_moderada (NDVI < 0.3)
    3. anomalia_negativa_fuerte (< -0.15)
    4. anomalia_negativa_leve (< -0.05)
    5. normal
    
    **Útil para:**
    - Alertas tempranas de sequía
    - Priorización de asistencia
    - Monitoreo de emergencias
    """
    data = service.get_alertas_ndvi(db, departamento, provincia, municipio)
    
    return SuccessResponse(
        message=f"Alertas activas ({len(data)} comunidades)",
        data=data,
        total=len(data)
    )


# ============================================================================
# ESCENAS SATELITALES
# ============================================================================

@router.get("/escenas", response_model=SuccessResponse)
def get_escenas(
    fecha_desde: Optional[date] = Query(None, description="Fecha de inicio"),
    fecha_hasta: Optional[date] = Query(None, description="Fecha fin"),
    cobertura_nubes_max: Optional[float] = Query(20.0, ge=0, le=100, description="Máx nubes (%)"),
    skip: int = Query(0, ge=0, description="Saltar registros"),
    limit: int = Query(100, ge=1, le=500, description="Límite de resultados"),
    todos: bool = Query(False, description="true = devolver todos sin LIMIT/OFFSET"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    **Escenas satelitales procesadas**.
    
    Lista de escenas Sentinel-2 descargadas y procesadas.
    
    **Respuesta incluye:**
    - ID de escena (EarthSearch)
    - Fecha de adquisición
    - Cobertura de nubes
    - Huella geográfica (GeoJSON)
    - Metadatos completos
    """
    resultado = service.get_escenas_satelitales(
        db, fecha_desde, fecha_hasta, cobertura_nubes_max, skip, limit, todos=todos
    )
    
    return SuccessResponse(
        message=f"Escenas procesadas ({resultado['total']} totales)",
        data=resultado["data"],
        total=resultado["total"],
        skip=skip,
        limit=limit
    )


@router.get("/escenas/consultar", response_model=SuccessResponse)
def consultar_earthsearch_api(
    min_lon: float = Query(-70.0, description="Lon mínimo"),
    min_lat: float = Query(-23.0, description="Lat mínima"),
    max_lon: float = Query(-57.0, description="Lon máximo"),
    max_lat: float = Query(-9.0, description="Lat máximo"),
    fecha_desde: Optional[date] = Query(None, description="Fecha de inicio"),
    fecha_hasta: Optional[date] = Query(None, description="Fecha fin"),
    max_nubes: float = Query(20.0, ge=0, le=100, description="Máx nubes (%)"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    **Consultar EarthSearch STAC API en tiempo real**.
    
    Busca escenas Sentinel-2 disponibles en EarthSearch para
    un área geográfica específica.
    
    **Fuente:** EarthSearch AWS (element84.com)
    **Autenticación:** Ninguna requerida
    **Colección:** sentinel-2-l2a
    
    **Útil para:**
    - Ver escenas disponibles antes de descargar
    - Planificación de procesamiento
    - Debug/auditoría
    """
    bbox = (min_lon, min_lat, max_lon, max_lat)
    features = service.consultar_earthsearch(bbox, fecha_desde, fecha_hasta, max_nubes)
    
    return SuccessResponse(
        message=f"Escenas encontradas ({len(features)})",
        data=features
    )


# ============================================================================
# GEOJSON PARA MAPAS
# ============================================================================

@router.get("/geojson/mapa-calor", response_model=SuccessResponse)
def get_mapa_calor_geojson(
    departamento: Optional[str] = Query(None, description="Filtro por departamento"),
    provincia: Optional[str] = Query(None, description="Filtro por provincia"),
    municipio: Optional[str] = Query(None, description="Filtro por municipio"),
    nivel: str = Query("comunidad", description="Nivel geográfico: comunidad|municipio"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    **GeoJSON para mapa de calor de NDVI**.
    
    Genera un FeatureCollection GeoJSON con geometrías de comunidades/municipios
    y propiedades de NDVI para visualización en mapas web (Leaflet, Mapbox, OpenLayers).
    
    **Filtros geográficos:**
    - departamento: Nombre del departamento (ej: "La Paz")
    - provincia: Nombre de provincia (ej: "Murillo")
    - municipio: Nombre de municipio (ej: "Achacachi")
    
    **Propiedades de cada feature:**
    - codigo_ine: Código de la comunidad
    - nombre: Nombre de la comunidad/municipio
    - ndvi_promedio: Valor NDVI (-1 a 1)
    - ndvi_anomalia: Desviación del histórico
    - estado_vegetacion: Clasificación (seco, bajo, normal, alto, muy_alto)
    - estado_alerta: alerta_roja, alerta_amarilla, normal, muy_bien
    - color: Color hex para visualización (calculado por NDVI)
    
    **Útil para:**
    - Mapas de calor departamentales/nacionales
    - Visualización web de alertas
    - Dashboard geoespacial
    """
    # Construir cláusulas WHERE para filtros geográficos
    where_clauses = ["1=1"]
    params = {}
    
    if departamento:
        where_clauses.append("c.id_departamento = (SELECT id FROM shared.departamento WHERE nombre ILIKE :depto)")
        params["depto"] = f"%{departamento}%"
    
    if provincia:
        where_clauses.append("c.id_provincia = (SELECT id FROM shared.provincia WHERE nombre ILIKE :prov)")
        params["prov"] = f"%{provincia}%"
    
    if municipio:
        where_clauses.append("c.id_municipio = (SELECT id FROM shared.municipio WHERE nombre ILIKE :muni)")
        params["muni"] = f"%{municipio}%"
    
    where_clause = " AND ".join(where_clauses)
    
    rows = _rows(db, f"""
        SELECT 
            c.codigo_ine,
            c.nombre,
            s.ndvi_promedio,
            s.ndvi_anomalia,
            s.estado_vegetacion,
            CASE 
                WHEN s.ndvi_anomalia < -0.15 THEN 'alerta_roja'
                WHEN s.ndvi_anomalia < -0.05 THEN 'alerta_amarilla'
                WHEN s.ndvi_anomalia > 0.10 THEN 'muy_bien'
                ELSE 'normal'
            END as estado_alerta,
            ST_AsGeoJSON(c.geom) as geojson
        FROM shared.comunidades c
        LEFT JOIN LATERAL (
            SELECT ndvi_promedio, ndvi_anomalia, estado_vegetacion
            FROM sinb.serie_ndvi_comunidad
            WHERE codigo_comunidad = c.codigo_ine
            ORDER BY fecha DESC
            LIMIT 1
        ) s ON true
        WHERE {where_clause}
    """, params)
    
    # Construir FeatureCollection
    features = []
    for row in rows:
        if row.get("geojson"):
            import json
            geom = json.loads(row["geojson"])
            
            # Calcular color basado en NDVI
            ndvi = row.get("ndvi_promedio")
            if ndvi is not None:
                if ndvi < 0.1:
                    color = "#8B4513"  # Suelo desnudo (marrón)
                elif ndvi < 0.2:
                    color = "#DAA520"  # Seco (dorado)
                elif ndvi < 0.3:
                    color = "#FFD700"  # Bajo (amarillo)
                elif ndvi < 0.5:
                    color = "#9ACD32"  # Normal (verde claro)
                elif ndvi < 0.7:
                    color = "#32CD32"  # Alto (verde)
                else:
                    color = "#006400"  # Muy alto (verde oscuro)
            else:
                color = "#CCCCCC"  # Sin datos (gris)
            
            feature = {
                "type": "Feature",
                "geometry": geom,
                "properties": {
                    "codigo_ine": row["codigo_ine"],
                    "nombre": row["nombre"],
                    "ndvi_promedio": float(row["ndvi_promedio"]) if row["ndvi_promedio"] else None,
                    "ndvi_anomalia": float(row["ndvi_anomalia"]) if row["ndvi_anomalia"] else None,
                    "estado_vegetacion": row["estado_vegetacion"],
                    "estado_alerta": row["estado_alerta"],
                    "color": color
                }
            }
            features.append(feature)
    
    geojson = {
        "type": "FeatureCollection",
        "features": features
    }
    
    return SuccessResponse(
        message=f"GeoJSON generado ({len(features)} features)",
        data=geojson
    )


@router.get("/geojson/bbox", response_model=SuccessResponse)
def get_ndvi_bbox_geojson(
    min_lon: float = Query(..., description="Lon mínimo del bbox"),
    min_lat: float = Query(..., description="Lat mínima del bbox"),
    max_lon: float = Query(..., description="Lon máximo del bbox"),
    max_lat: float = Query(..., description="Lat máxima del bbox"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    **GeoJSON de NDVI filtrado por bounding box**.
    
    Obtiene comunidades dentro de un rectángulo geográfico con
    sus valores de NDVI para visualización en mapas interactivos.
    
    **Útil para:**
    - Zoom a región específica en mapa web
    - Consultas espaciales dinámicas
    - Exportar área de interés
    """
    bbox_wkt = f"POLYGON(({min_lon} {min_lat}, {max_lon} {min_lat}, {max_lon} {max_lat}, {min_lon} {max_lat}, {min_lon} {min_lat}))"
    
    rows = _rows(db, """
        SELECT 
            c.codigo_ine,
            c.nombre,
            s.ndvi_promedio,
            s.ndvi_anomalia,
            s.estado_vegetacion,
            CASE 
                WHEN s.ndvi_anomalia < -0.15 THEN 'alerta_roja'
                WHEN s.ndvi_anomalia < -0.05 THEN 'alerta_amarilla'
                WHEN s.ndvi_anomalia > 0.10 THEN 'muy_bien'
                ELSE 'normal'
            END as estado_alerta,
            ST_AsGeoJSON(c.geom) as geojson
        FROM shared.comunidades c
        LEFT JOIN LATERAL (
            SELECT ndvi_promedio, ndvi_anomalia, estado_vegetacion
            FROM sinb.serie_ndvi_comunidad
            WHERE codigo_comunidad = c.codigo_ine
            ORDER BY fecha DESC
            LIMIT 1
        ) s ON true
        WHERE ST_Intersects(c.geom, ST_GeomFromText(:bbox, 4326))
    """, {"bbox": bbox_wkt})
    
    # Construir FeatureCollection
    features = []
    for row in rows:
        if row.get("geojson"):
            import json
            geom = json.loads(row["geojson"])
            
            ndvi = row.get("ndvi_promedio")
            if ndvi is not None:
                if ndvi < 0.2:
                    color = "#FF0000"  # Alerta (rojo)
                elif ndvi < 0.3:
                    color = "#FFA500"  # Moderado (naranja)
                elif ndvi < 0.5:
                    color = "#FFFF00"  # Normal (amarillo)
                else:
                    color = "#00FF00"  # Bueno (verde)
            else:
                color = "#CCCCCC"
            
            feature = {
                "type": "Feature",
                "geometry": geom,
                "properties": {
                    "codigo_ine": row["codigo_ine"],
                    "nombre": row["nombre"],
                    "ndvi_promedio": float(ndvi) if ndvi else None,
                    "ndvi_anomalia": float(row["ndvi_anomalia"]) if row["ndvi_anomalia"] else None,
                    "estado_vegetacion": row["estado_vegetacion"],
                    "estado_alerta": row["estado_alerta"],
                    "color": color
                }
            }
            features.append(feature)
    
    geojson = {
        "type": "FeatureCollection",
        "features": features
    }
    
    return SuccessResponse(
        message=f"GeoJSON de bbox ({len(features)} comunidades)",
        data=geojson
    )


# ============================================================================
# INGESTIÓN Y PROCESAMIENTO
# ============================================================================

@router.post("/ingestar", response_model=SuccessResponse)
def ingestar_ndvi(
    request: NDVIIngestarRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    **Ingestar NDVI desde EarthSearch**.
    
    Procesa escenas Sentinel-2 y calcula NDVI para comunidades.
    Requiere rol admin.
    
    **Proceso:**
    1. Consulta EarthSearch STAC API
    2. Filtra escenas por cobertura de nubes
    3. Descarga bandas NIR, Red, SCL
    4. Calcula NDVI = (NIR - Red) / (NIR + Red)
    5. Agrega por comunidad
    6. Actualiza series temporales
    
    **Tiempo estimado:** 1-2 horas para 343 municipios
    
    **Nota:** En producción, ejecutar vía CRON diario (06:00)
    """
    # Verificar rol admin
    if current_user.get("rol") not in ["admin", "Admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol admin para ingestar NDVI"
        )
    
    resultado = service.ingestar_ndvi_comunidades(
        db,
        request.codigos_comunidades,
        request.max_nubes
    )
    
    return SuccessResponse(
        message="Ingestión NDVI completada",
        data=resultado
    )


@router.get("/procesamiento/log", response_model=SuccessResponse)
def get_log_procesamiento(
    fecha_desde: Optional[date] = Query(None, description="Fecha de inicio"),
    limit: int = Query(30, ge=1, le=100, description="Límite de registros"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    **Log de procesamiento de ingestión NDVI**.
    
    Historial de ejecuciones de la tarea de ingesta,
    incluyendo errores y métricas de procesamiento.
    
    **Útil para:**
    - Monitoreo de tareas CRON
    - Debug de fallos
    - Auditoría de procesamiento
    """
    data = service.get_log_procesamiento_ndvi(db, fecha_desde, limit)
    
    return SuccessResponse(
        message=f"Log de procesamiento ({len(data)} registros)",
        data=data
    )


# ============================================================================
# ESTADÍSTICAS Y REPORTES
# ============================================================================

@router.get("/estadisticas/resumen", response_model=SuccessResponse)
def get_estadisticas_resumen(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    **Resumen estadístico de NDVI**.
    
    Métricas globales de la base de datos NDVI.
    
    **Incluye:**
    - Total de escenas procesadas
    - Total de comunidades con datos
    - Rango de fechas cubiertas
    - Promedio nacional de NDVI
    - Comunidades con alerta activa
    """
    # Escenas totales
    escenas_row = _row(db, "SELECT COUNT(*) as total FROM sinb.escena_satelital")
    
    # Comunidades con datos
    comunidades_row = _row(db, """
        SELECT COUNT(DISTINCT codigo_comunidad) as total
        FROM sinb.serie_ndvi_comunidad
    """)
    
    # Fecha más antigua y reciente
    fechas_row = _row(db, """
        SELECT MIN(fecha) as minima, MAX(fecha) as maxima
        FROM sinb.serie_ndvi_comunidad
    """)
    
    # Promedio nacional
    promedio_row = _row(db, """
        SELECT AVG(ndvi_promedio) as promedio
        FROM sinb.serie_ndvi_comunidad
        WHERE fecha >= (CURRENT_DATE - INTERVAL '30 days')
    """)
    
    # Alertas activas
    alertas_row = _row(db, "SELECT COUNT(*) as total FROM sinb.vw_alertas_ndvi")
    
    data = {
        "escenas_procesadas": escenas_row["total"] if escenas_row else 0,
        "comunidades_con_datos": comunidades_row["total"] if comunidades_row else 0,
        "fecha_minima": str(fechas_row["minima"]) if fechas_row and fechas_row["minima"] else None,
        "fecha_maxima": str(fechas_row["maxima"]) if fechas_row and fechas_row["maxima"] else None,
        "ndvi_promedio_30dias": round(promedio_row["promedio"], 4) if promedio_row and promedio_row["promedio"] else None,
        "alertas_activas": alertas_row["total"] if alertas_row else 0
    }
    
    return SuccessResponse(
        message="Resumen estadístico de NDVI",
        data=data
    )
