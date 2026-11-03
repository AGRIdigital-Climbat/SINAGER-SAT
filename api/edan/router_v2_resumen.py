"""APIs de resumen y gráficas EDAN (familia nueva, v2.60).

Cuatro GET de consulta AGREGADA (exentos de paginación por ser consulta
puntual — ver skill `api-get-listados`) bajo el mismo contrato uuid-first:

    GET /edan/resumen/formularios/contadores   tarjetas de localidad
    GET /edan/resumen/formularios/graficas     gráficas de localidad
    GET /edan/resumen/edan/contadores          tarjetas de EDAN padre
    GET /edan/resumen/edan/graficas            gráficas de EDAN padre

Decisiones (PLAN §21):
- **Sin scope por rol**: cualquier usuario autenticado (token + permiso READ
  EDAN) consulta; la geografía se abre/cierra por query.
- Filtros combinables con **AND**; cadena geográfica incoherente → **400**.
- **Cada gráfica obedece TODOS los filtros** y trae su `tabla` (agregado);
  con `incluir_detalle=true` trae además `tabla_registros` (filas crudas,
  paginadas con `detalle_limit`/`detalle_skip`).
- **Multi-tipo**: cada gráfica entrega `items` + `categorias` + `series` +
  `tipos[]`, así sirve para torta, donut, barras, apiladas o línea.
"""
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..auth.permisos import module_permiso
from ..database import get_db
from ..dependencies import get_current_user
from ..response import SuccessResponse
from . import service_v2_resumen as svc

router = APIRouter(prefix="/edan", dependencies=[Depends(module_permiso("EDAN"))])

TAG_RES = "EDAN > APIs nuevas > Resumen"

_IMP_14 = tuple(svc._IMP_14)
_GRUPOS_9 = tuple(svc._GRUPOS_9)

# ---------------------------------------------------------------------------
#  Presentación (compartida por los 4 endpoints)
# ---------------------------------------------------------------------------
_NIVEL = Query(None, description="Nivel de desagregación geográfica máxima: "
               "nacional (sin desglose geográfico), departamento, provincia, "
               "municipio. Las gráficas más finas que el nivel pedido se omiten")
_TOP = Query(15, ge=1, le=100, description="Tamaño de los rankings (top N)")
_GRAN = Query("mes", description="Granularidad de las series temporales")
_RELLENAR = Query(True, description="true = rellenar huecos de las series "
                   "temporales con ceros")
_INCLUIR = Query(None, description="Ids de gráficas a devolver, separados por "
                 "coma (por defecto: todas). Ej: estado_localidad,serie_llenado")
_DET = Query(False, description="true = cada gráfica agrega `tabla_registros` "
             "con las filas crudas filtradas (paginadas)")
_DLIM = Query(100, ge=1, le=1000, description="Filas de `tabla_registros`")
_DSKIP = Query(0, ge=0, description="Salto de filas de `tabla_registros`")


def _opts(nivel, top, granularidad, rellenar_vacios, incluir, incluir_detalle,
          detalle_limit, detalle_skip) -> dict:
    ids = [x.strip() for x in (incluir or "").split(",") if x.strip()]
    return {
        "nivel": nivel, "top": top, "granularidad": granularidad,
        "rellenar_vacios": rellenar_vacios, "incluir": ids or None,
        "incluir_detalle": incluir_detalle, "detalle_limit": detalle_limit,
        "detalle_skip": detalle_skip,
    }


# ---------------------------------------------------------------------------
#  Flags de grupos (9) y secciones (14): compartidos por los 4 endpoints
# ---------------------------------------------------------------------------
class FiltrosSecciones:
    """Filtros booleanos de grupos/secciones, combinados con **AND**.

    Ausente = sin filtro; `true` exige la sección; `false` la excluye.
    Llegan como query params de la misma query que los demás filtros."""
    def __init__(self,
    grup_poblacion: bool | None = Query(None, description='Alguna localidad con la sección grup_poblacion activa (false = ninguna la tiene)'),
    grup_salud: bool | None = Query(None, description='Alguna localidad con la sección grup_salud activa (false = ninguna la tiene)'),
    grup_infraestructura: bool | None = Query(None, description='Alguna localidad con la sección grup_infraestructura activa (false = ninguna la tiene)'),
    grup_servicios: bool | None = Query(None, description='Alguna localidad con la sección grup_servicios activa (false = ninguna la tiene)'),
    grup_educacion: bool | None = Query(None, description='Alguna localidad con la sección grup_educacion activa (false = ninguna la tiene)'),
    grup_vivienda: bool | None = Query(None, description='Alguna localidad con la sección grup_vivienda activa (false = ninguna la tiene)'),
    grup_agropecuario: bool | None = Query(None, description='Alguna localidad con la sección grup_agropecuario activa (false = ninguna la tiene)'),
    grup_proteccion: bool | None = Query(None, description='Alguna localidad con la sección grup_proteccion activa (false = ninguna la tiene)'),
    grup_necesidades: bool | None = Query(None, description='Alguna localidad con la sección grup_necesidades activa (false = ninguna la tiene)'),
    imp_impacto_poblacion: bool | None = Query(None, description='El formulario tiene la sección imp_impacto_poblacion activa (false = no la tiene)'),
    imp_primera_respuesta: bool | None = Query(None, description='El formulario tiene la sección imp_primera_respuesta activa (false = no la tiene)'),
    imp_salud_establecimientos: bool | None = Query(None, description='El formulario tiene la sección imp_salud_establecimientos activa (false = no la tiene)'),
    imp_necesidad_salud: bool | None = Query(None, description='El formulario tiene la sección imp_necesidad_salud activa (false = no la tiene)'),
    imp_danos_viales: bool | None = Query(None, description='El formulario tiene la sección imp_danos_viales activa (false = no la tiene)'),
    imp_danos_infra_publica: bool | None = Query(None, description='El formulario tiene la sección imp_danos_infra_publica activa (false = no la tiene)'),
    imp_servicios_basicos: bool | None = Query(None, description='El formulario tiene la sección imp_servicios_basicos activa (false = no la tiene)'),
    imp_unidades_educativas: bool | None = Query(None, description='El formulario tiene la sección imp_unidades_educativas activa (false = no la tiene)'),
    imp_danos_vivienda: bool | None = Query(None, description='El formulario tiene la sección imp_danos_vivienda activa (false = no la tiene)'),
    imp_danos_agricultura: bool | None = Query(None, description='El formulario tiene la sección imp_danos_agricultura activa (false = no la tiene)'),
    imp_danos_pecuarios: bool | None = Query(None, description='El formulario tiene la sección imp_danos_pecuarios activa (false = no la tiene)'),
    imp_infra_productiva: bool | None = Query(None, description='El formulario tiene la sección imp_infra_productiva activa (false = no la tiene)'),
    imp_proteccion: bool | None = Query(None, description='El formulario tiene la sección imp_proteccion activa (false = no la tiene)'),
    imp_necesidad_humanitaria: bool | None = Query(None, description='El formulario tiene la sección imp_necesidad_humanitaria activa (false = no la tiene)'),
        ):
        self.flags = {k: v for k, v in locals().items() if k != 'self'}


# ===========================================================================
#  Formularios (EDAN localidad)
# ===========================================================================
@router.get("/resumen/formularios/contadores", tags=[TAG_RES],
            summary="Tarjetas de resumen de formularios (totales, estados, "
                    "grupos y cobertura geográfica; sin scope por rol, filtros AND)")
def resumen_formularios_contadores(
    id_departamento: int | None = Query(None, description="Departamento (AND con los demás)"),
    id_provincia: int | None = Query(None, description="Provincia (AND con los demás)"),
    id_municipio: int | None = Query(None, description="Municipio (AND con los demás)"),
    id_tipo_evento: int | None = Query(None, description="Tipo de evento"),
    grupo_evento: str | None = Query(None, description="Grupo del evento (Hidrológico, Meteorológico, …)"),
    id_edan_localidad_estado: int | None = Query(None, description="Estado de la localidad (id)"),
    estado_localidad: str | None = Query(None, description="Estado de la localidad por nombre"),
    id_tipo_localidad: int | None = Query(None, description="Tipo de localidad (id)"),
    id_usuario: int | None = Query(None, description="Usuario capturista (id)"),
    solo_huerfanas: bool | None = Query(None, description="true = sólo localidades sin EDAN; false = sólo consolidadas"),
    q: str | None = Query(None, description="Búsqueda por nombre de localidad (ILIKE)"),
    procedencia: str | None = Query(None, description="sistema | excel_legacy | api_import"),
    pendiente_actualizacion: bool | None = Query(None, description="Filtrar por pendiente_actualizacion"),
    pendiente_eliminacion: bool | None = Query(None, description="Filtrar por pendiente_eliminacion"),
    con_foto: bool | None = Query(None, description="Sólo localidades con fotografía activa"),
    sin_foto: bool | None = Query(None, description="Sólo localidades sin fotografía activa"),
    grupo: str | None = Query(None, description="Grupo con sección activa (grup_poblacion, grup_salud, …)"),
    tiene_agricultura: bool | None = Query(None, description="Sólo con daños a agricultura"),
    tiene_pecuario: bool | None = Query(None, description="Sólo con daños pecuarios"),
    fecha_llenado_desde: datetime | None = Query(None, description="Fecha de llenado desde (ISO 8601)"),
    fecha_llenado_hasta: datetime | None = Query(None, description="Fecha de llenado hasta (ISO 8601)"),
    fecha_evento_desde: datetime | None = Query(None, description="Fecha de evento desde (ISO 8601)"),
    fecha_evento_hasta: datetime | None = Query(None, description="Fecha de evento hasta (ISO 8601)"),
    fecha_modificacion_desde: datetime | None = Query(None, description="Última modificación desde (ISO 8601)"),
    fecha_modificacion_hasta: datetime | None = Query(None, description="Última modificación hasta (ISO 8601)"),
    nivel: str | None = _NIVEL, top: int = _TOP,
    secciones: FiltrosSecciones = Depends(),
    db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Tarjetas de resumen de **EDAN localidad (formularios)** bajo los filtros:
    totales (total, huérfanas, consolidadas, aprobadas, pendientes, con foto,
    población/familias afectadas), cobertura geográfica, periodo observado y
    listas `por_estado`, `por_grupo` (9), `por_tipo_evento`, `por_departamento`
    y `por_municipio` — cada fila viene con `label`, `value`, `color` y
    `porcentaje` (listas para pintar sin cálculos en el cliente).

    **Sin scope por rol** (token obligatorio): la geografía se abre/cierra con
    los filtros de la query, combinados con **AND**; cadena incoherente
    (`id_municipio` que no pertenece a `id_provincia`, etc.) → **400**."""
    f = _filtros_formularios(locals())
    data = svc.contadores_formularios(db, f, {"nivel": nivel, "top": top})
    return SuccessResponse(message="Resumen de formularios calculado",
                           data=data, total=data["totales"]["total"])


@router.get("/resumen/formularios/graficas", tags=[TAG_RES],
            summary="Gráficas de formularios (multi-tipo: torta/donut/barras/serie + tabla de cada gráfica)")
def resumen_formularios_graficas(
    id_departamento: int | None = Query(None, description="Departamento (AND con los demás)"),
    id_provincia: int | None = Query(None, description="Provincia (AND con los demás)"),
    id_municipio: int | None = Query(None, description="Municipio (AND con los demás)"),
    id_tipo_evento: int | None = Query(None, description="Tipo de evento"),
    grupo_evento: str | None = Query(None, description="Grupo del evento"),
    id_edan_localidad_estado: int | None = Query(None, description="Estado de la localidad (id)"),
    estado_localidad: str | None = Query(None, description="Estado de la localidad por nombre"),
    id_tipo_localidad: int | None = Query(None, description="Tipo de localidad (id)"),
    id_usuario: int | None = Query(None, description="Usuario capturista (id)"),
    solo_huerfanas: bool | None = Query(None, description="true = sólo huérfanas; false = sólo consolidadas"),
    q: str | None = Query(None, description="Búsqueda por nombre de localidad (ILIKE)"),
    procedencia: str | None = Query(None, description="sistema | excel_legacy | api_import"),
    pendiente_actualizacion: bool | None = Query(None, description="Filtrar por pendiente_actualizacion"),
    pendiente_eliminacion: bool | None = Query(None, description="Filtrar por pendiente_eliminacion"),
    con_foto: bool | None = Query(None, description="Sólo con fotografía activa"),
    sin_foto: bool | None = Query(None, description="Sólo sin fotografía activa"),
    grupo: str | None = Query(None, description="Grupo con sección activa (grup_*)"),
    tiene_agricultura: bool | None = Query(None, description="Sólo con daños a agricultura"),
    tiene_pecuario: bool | None = Query(None, description="Sólo con daños pecuarios"),
    fecha_llenado_desde: datetime | None = Query(None, description="Fecha de llenado desde (ISO 8601)"),
    fecha_llenado_hasta: datetime | None = Query(None, description="Fecha de llenado hasta (ISO 8601)"),
    fecha_evento_desde: datetime | None = Query(None, description="Fecha de evento desde (ISO 8601)"),
    fecha_evento_hasta: datetime | None = Query(None, description="Fecha de evento hasta (ISO 8601)"),
    fecha_modificacion_desde: datetime | None = Query(None, description="Última modificación desde (ISO 8601)"),
    fecha_modificacion_hasta: datetime | None = Query(None, description="Última modificación hasta (ISO 8601)"),
    nivel: str | None = _NIVEL, top: int = _TOP, granularidad: str = _GRAN,
    rellenar_vacios: bool = _RELLENAR, incluir: str | None = _INCLUIR,
    incluir_detalle: bool = _DET, detalle_limit: int = _DLIM,
    detalle_skip: int = _DSKIP,
    secciones: FiltrosSecciones = Depends(),
    db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Catálogo de **gráficas de formularios** (estados, grupos y secciones,
    tipo/grupo/categoría de evento, geografía, series temporales, impacto de
    población, protección, vivienda, vías/infraestructura/servicios, educación,
    salud, agricultura/pecuario, primera respuesta, necesidades humanitarias,
    fotografías, usuarios e importaciones).

    Cada gráfica obedece **todos** los filtros del query y entrega:

    - `tipos[]`: tipos renderizables (torta, donut, barras,
      barras_horizontales, barras_apiladas, linea, area, treemap, …) y `tipo`
      sugerido — el mismo dato sirve para cualquier gráfica.
    - `items[{label,value,color,porcentaje}]`, `categorias[]`,
      `series[{label,color,datos[]}]` y **`tabla{columnas,filas}`** (el
      agregado que alimenta la gráfica, con `porcentaje` cuando hay una sola
      métrica).
    - `serie_temporal` en las series (granularidad, etiqueta del eje X, si se
      rellenaron huecos).
    - `tabla_registros` sólo con `incluir_detalle=true` (filas crudas
      filtradas, paginadas con `detalle_limit`/`detalle_skip`).

    Presentación: `nivel` (hasta dónde desagregar geográficamente; se omiten
    las desagregaciones degeneradas — p.ej. agrupar por municipio cuando ya
    filtraste municipio), `top` (rankings), `granularidad` (día, semana, mes,
    año) + `rellenar_vacios`, `incluir` (sólo esas gráficas por id)."""
    f = _filtros_formularios(locals())
    opts = _opts(nivel, top, granularidad, rellenar_vacios, incluir,
                 incluir_detalle, detalle_limit, detalle_skip)
    data = svc.graficas_formularios(db, f, opts)
    return SuccessResponse(message="Gráficas de formularios calculadas",
                           data=data, total=data["total_graficas"])


# ===========================================================================
#  EDAN padre (cabecera)
# ===========================================================================
@router.get("/resumen/edan/contadores", tags=[TAG_RES],
            summary="Tarjetas de resumen de EDAN padre (totales, estados, "
                    "aprobaciones e importaciones; sin scope por rol, filtros AND)")
def resumen_edan_contadores(
    id_departamento: int | None = Query(None, description="Departamento (AND con los demás)"),
    id_provincia: int | None = Query(None, description="Provincia (AND con los demás)"),
    id_municipio: int | None = Query(None, description="Municipio (AND con los demás)"),
    id_tipo_evento: int | None = Query(None, description="Tipo de evento"),
    grupo_evento: str | None = Query(None, description="Grupo del evento"),
    id_estado: int | None = Query(None, description="Estado del EDAN (id)"),
    estado: str | None = Query(None, description="Estado del EDAN por nombre"),
    id_usuario_ugr: int | None = Query(None, description="UGR responsable (id)"),
    id_usuario_alcalde: int | None = Query(None, description="Alcalde (id)"),
    id_importacion: int | None = Query(None, description="Importación que creó el EDAN (id)"),
    q: str | None = Query(None, description="Búsqueda por código de EDAN o localidad (ILIKE)"),
    procedencia: str | None = Query(None, description="sistema | excel_legacy | api_import"),
    pendiente_actualizacion: bool | None = Query(None, description="Filtrar por pendiente_actualizacion"),
    pendiente_eliminacion: bool | None = Query(None, description="Filtrar por pendiente_eliminacion"),
    con_foto: bool | None = Query(None, description="Sólo EDAN con alguna localidad con foto"),
    sin_foto: bool | None = Query(None, description="Sólo EDAN sin ninguna localidad con foto"),
    grupo: str | None = Query(None, description="Grupo con sección activa en alguna localidad (grup_*)"),
    tiene_agricultura: bool | None = Query(None, description="Sólo con daños a agricultura"),
    tiene_pecuario: bool | None = Query(None, description="Sólo con daños pecuarios"),
    fecha_llenado_desde: datetime | None = Query(None, description="Fecha de llenado desde (ISO 8601)"),
    fecha_llenado_hasta: datetime | None = Query(None, description="Fecha de llenado hasta (ISO 8601)"),
    fecha_evento_desde: datetime | None = Query(None, description="Fecha de evento desde (ISO 8601)"),
    fecha_evento_hasta: datetime | None = Query(None, description="Fecha de evento hasta (ISO 8601)"),
    fecha_creacion_desde: datetime | None = Query(None, description="Fecha de creación desde (ISO 8601)"),
    fecha_creacion_hasta: datetime | None = Query(None, description="Fecha de creación hasta (ISO 8601)"),
    fecha_modificacion_desde: datetime | None = Query(None, description="Última modificación desde (ISO 8601)"),
    fecha_modificacion_hasta: datetime | None = Query(None, description="Última modificación hasta (ISO 8601)"),
    nivel: str | None = _NIVEL, top: int = _TOP,
    secciones: FiltrosSecciones = Depends(),
    db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Tarjetas de resumen de **EDAN padre**: totales (EDAN, localidades,
    población/familias, pendientes, UGR/alcaldes, importaciones), cobertura
    geográfica, periodo observado, `por_estado`, `por_tipo_evento`,
    `por_departamento`, `por_municipio` y el bloque `aprobaciones`
    (`totales` y `por_nivel_estado`).

    Mismas reglas que el resto de la familia: **sin scope por rol**, filtros
    combinados con **AND**, cadena geográfica incoherente → **400**."""
    f = _filtros_edan(locals())
    data = svc.contadores_edan(db, f, {"nivel": nivel, "top": top})
    return SuccessResponse(message="Resumen de EDAN calculado",
                           data=data, total=data["totales"]["total"])


@router.get("/resumen/edan/graficas", tags=[TAG_RES],
            summary="Gráficas de EDAN padre (multi-tipo + aprobaciones e importaciones + tabla de cada gráfica)")
def resumen_edan_graficas(
    id_departamento: int | None = Query(None, description="Departamento (AND con los demás)"),
    id_provincia: int | None = Query(None, description="Provincia (AND con los demás)"),
    id_municipio: int | None = Query(None, description="Municipio (AND con los demás)"),
    id_tipo_evento: int | None = Query(None, description="Tipo de evento"),
    grupo_evento: str | None = Query(None, description="Grupo del evento"),
    id_estado: int | None = Query(None, description="Estado del EDAN (id)"),
    estado: str | None = Query(None, description="Estado del EDAN por nombre"),
    id_usuario_ugr: int | None = Query(None, description="UGR responsable (id)"),
    id_usuario_alcalde: int | None = Query(None, description="Alcalde (id)"),
    id_importacion: int | None = Query(None, description="Importación que creó el EDAN (id)"),
    q: str | None = Query(None, description="Búsqueda por código de EDAN o localidad (ILIKE)"),
    procedencia: str | None = Query(None, description="sistema | excel_legacy | api_import"),
    pendiente_actualizacion: bool | None = Query(None, description="Filtrar por pendiente_actualizacion"),
    pendiente_eliminacion: bool | None = Query(None, description="Filtrar por pendiente_eliminacion"),
    con_foto: bool | None = Query(None, description="Sólo con alguna localidad con foto"),
    sin_foto: bool | None = Query(None, description="Sólo sin ninguna localidad con foto"),
    grupo: str | None = Query(None, description="Grupo con sección activa en alguna localidad (grup_*)"),
    tiene_agricultura: bool | None = Query(None, description="Sólo con daños a agricultura"),
    tiene_pecuario: bool | None = Query(None, description="Sólo con daños pecuarios"),
    fecha_llenado_desde: datetime | None = Query(None, description="Fecha de llenado desde (ISO 8601)"),
    fecha_llenado_hasta: datetime | None = Query(None, description="Fecha de llenado hasta (ISO 8601)"),
    fecha_evento_desde: datetime | None = Query(None, description="Fecha de evento desde (ISO 8601)"),
    fecha_evento_hasta: datetime | None = Query(None, description="Fecha de evento hasta (ISO 8601)"),
    fecha_creacion_desde: datetime | None = Query(None, description="Fecha de creación desde (ISO 8601)"),
    fecha_creacion_hasta: datetime | None = Query(None, description="Fecha de creación hasta (ISO 8601)"),
    fecha_modificacion_desde: datetime | None = Query(None, description="Última modificación desde (ISO 8601)"),
    fecha_modificacion_hasta: datetime | None = Query(None, description="Última modificación hasta (ISO 8601)"),
    nivel: str | None = _NIVEL, top: int = _TOP, granularidad: str = _GRAN,
    rellenar_vacios: bool = _RELLENAR, incluir: str | None = _INCLUIR,
    incluir_detalle: bool = _DET, detalle_limit: int = _DLIM,
    detalle_skip: int = _DSKIP,
    secciones: FiltrosSecciones = Depends(),
    db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Catálogo de **gráficas de EDAN padre**: estados, tipo/grupo/categoría
    de evento, geografía (ranking y población/familias por nivel), series
    temporales (evento, llenado, creación, modificación), sincronización,
    usuarios (UGR/alcalde), **aprobaciones** (por estado, por nivel,
    nivel × estado, serie, observaciones/devoluciones, ranking por EDAN),
    **importaciones** (totales, por archivo, serie, por resultado) y las
    gráficas de las **localidades** de los EDAN filtrados (estados, grupos,
    población y fotografías).

    Misma construcción que el endpoint de formularios: multi-tipo +
    `items`/`categorias`/`series`/`tabla`, y `tabla_registros` opcional con
    `incluir_detalle=true`. Todos los filtros se aplican a TODAS las gráficas
    (los filtros sólo-localidad restringen los EDAN que las contienen)."""
    f = _filtros_edan(locals())
    opts = _opts(nivel, top, granularidad, rellenar_vacios, incluir,
                 incluir_detalle, detalle_limit, detalle_skip)
    data = svc.graficas_edan(db, f, opts)
    return SuccessResponse(message="Gráficas de EDAN calculadas",
                           data=data, total=data["total_graficas"])


# ---------------------------------------------------------------------------
#  Recolección de filtros (SIN presentación y SIN claves ajenas al endpoint)
# ---------------------------------------------------------------------------
_KEYS_FORM = (
    "id_departamento", "id_provincia", "id_municipio", "id_tipo_evento",
    "grupo_evento", "id_edan_localidad_estado", "estado_localidad",
    "id_tipo_localidad", "id_usuario", "solo_huerfanas", "q", "procedencia",
    "pendiente_actualizacion", "pendiente_eliminacion", "con_foto", "sin_foto",
    "grupo", "tiene_agricultura", "tiene_pecuario",
    "fecha_llenado_desde", "fecha_llenado_hasta", "fecha_evento_desde",
    "fecha_evento_hasta", "fecha_modificacion_desde", "fecha_modificacion_hasta",
    *_IMP_14, *_GRUPOS_9,
)
_KEYS_EDAN = (
    "id_departamento", "id_provincia", "id_municipio", "id_tipo_evento",
    "grupo_evento", "id_estado", "estado", "id_usuario_ugr",
    "id_usuario_alcalde", "id_importacion", "q", "procedencia",
    "pendiente_actualizacion", "pendiente_eliminacion", "con_foto", "sin_foto",
    "grupo", "tiene_agricultura", "tiene_pecuario",
    "fecha_llenado_desde", "fecha_llenado_hasta", "fecha_evento_desde",
    "fecha_evento_hasta", "fecha_creacion_desde", "fecha_creacion_hasta",
    "fecha_modificacion_desde", "fecha_modificacion_hasta",
    *_IMP_14, *_GRUPOS_9,
)


def _filtros_formularios(ns: dict) -> dict:
    f = {k: ns.get(k) for k in _KEYS_FORM}
    f.update(ns["secciones"].flags)
    return f


def _filtros_edan(ns: dict) -> dict:
    f = {k: ns.get(k) for k in _KEYS_EDAN}
    f.update(ns["secciones"].flags)
    return f
