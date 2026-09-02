from typing import Literal

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..auth.permisos import module_permiso
from ..dependencies import get_current_user
from ..database import get_db
from ..response import SuccessResponse, MessageResponse
from . import service
from .schemas import (
    LocalidadCabeceraCreate, LocalidadEstadoUpdateV2,
    ImpactoPoblacion, EstablecimientoSalud, DanoVial, DanoInfraPublica,
    ServicioBasicoDetalle, UnidadEducativa, DanoVivienda, DanoAgricultura,
    DanoPecuario, InfraProductiva, GrupoVulnerable,
)
from .utils import require_rol, db_error

# ============================================================================
#  V2 — SYNC INCREMENTAL POR SECCIONES
#  Ruta de escritura por segmentos: cabecera primero, luego cada sección
#  como recurso independiente (UPSERT por id_seccion). NO destructivo:
#  lo que no viene, no se toca. Montado en /api/v2/edan (v1 queda intacto).
#
#  Los tags usan ">" para que swagger-ui-plugin-hierarchical-tags anide
#  cada sección como TERCER NIVEL dentro de EDAN_LOCALIDADES en /docs.
# ============================================================================

router = APIRouter(prefix="/edan", dependencies=[Depends(module_permiso("EDAN"))])

TAG_EDAN_LOCALIDADES = "EDAN_LOCALIDADES"
TAG_CABECERA = "EDAN_LOCALIDADES > Cabecera"
TAG_IMPACTO_POBLACION = "EDAN_LOCALIDADES > Impacto Poblacion"
TAG_PRIMERA_RESPUESTA = "EDAN_LOCALIDADES > Primera Respuesta"
TAG_SALUD_ESTABLECIMIENTOS = "EDAN_LOCALIDADES > Salud Establecimientos"
TAG_NECESIDAD_SALUD = "EDAN_LOCALIDADES > Necesidad Salud"
TAG_DANOS_VIALES = "EDAN_LOCALIDADES > Danos Viales"
TAG_DANOS_INFRA_PUBLICA = "EDAN_LOCALIDADES > Danos Infra Publica"
TAG_SERVICIOS_BASICOS = "EDAN_LOCALIDADES > Servicios Basicos"
TAG_UNIDADES_EDUCATIVAS = "EDAN_LOCALIDADES > Unidades Educativas"
TAG_DANOS_VIVIENDA = "EDAN_LOCALIDADES > Danos Vivienda"
TAG_DANOS_AGRICULTURA = "EDAN_LOCALIDADES > Danos Agricultura"
TAG_DANOS_PECUARIOS = "EDAN_LOCALIDADES > Danos Pecuario"
TAG_INFRA_PRODUCTIVA = "EDAN_LOCALIDADES > Infra Productiva"
TAG_PROTECCION = "EDAN_LOCALIDADES > Proteccion"
TAG_NECESIDAD_HUMANITARIA = "EDAN_LOCALIDADES > Necesidades Humanitarias"

ROLES_LOCALES = (6, 7)  # UGR municipio + Responsable local

PATH_TO_SCHEMA = {
    "impacto-poblacion": ImpactoPoblacion,
    "salud-establecimientos": EstablecimientoSalud,
    "danos-viales": DanoVial,
    "danos-infra-publica": DanoInfraPublica,
    "servicios-basicos": ServicioBasicoDetalle,
    "unidades-educativas": UnidadEducativa,
    "danos-vivienda": DanoVivienda,
    "danos-agricultura": DanoAgricultura,
    "danos-pecuarios": DanoPecuario,
    "infra-productiva": InfraProductiva,
    "proteccion": GrupoVulnerable,
}


# ----------------------------------------------------------------------------
#  0) LISTADO / RESUMEN / ESTADOS LIGEROS (para la web)
#  Refresco de lista: mis-estados (ligero, sin secciones) + mis-resumen.
#  Carga completa de UN ítem: GET /localidades/{id_localidad} (todas las secciones).
# ----------------------------------------------------------------------------

@router.get("/localidades/mis-reportes", tags=[TAG_EDAN_LOCALIDADES, TAG_CABECERA],
            summary="Listar mis localidades (completo o comprimido, todas las secciones)",
            description="Devuelve TODAS las localidades del usuario autenticado.\n\n"
                        "- `modo=completo` (default): estructura completa anidada (las 14 secciones, "
                        "tengan datos o no).\n"
                        "- `modo=comprimido`: cabecera + los 22 flags `imp_*` + SOLO las secciones que "
                        "tienen datos (payload mínimo; los flags indican qué secciones habilitar).\n\n"
                        "**Roles con scope propio:** 6 (UGR municipio), 7 (Responsable local) — solo ven las propias.\n"
                        "Otros roles (1-5, 8, 9) pueden consultar por `id_usuario`.")
def mis_reportes_localidades(
    id_usuario: int | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    solo_huerfanas: bool | None = Query(None, description="True=huérfanas, False=consolidadas, None=todas"),
    modo: Literal["completo", "comprimido"] = Query("completo",
                                                    description="completo=todas las secciones, comprimido=solo las que tienen datos"),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    uid = _user["id_usuario"] if _user["id_rol"] in ROLES_LOCALES else (id_usuario or _user["id_usuario"])
    data, total = service.get_mis_localidades(db, uid, skip=skip, limit=limit,
                                              solo_huerfanas=solo_huerfanas,
                                              solo_con_datos=(modo == "comprimido"))
    return SuccessResponse(message="Mis localidades listadas correctamente", data=data, total=total)


@router.get("/localidades/mis-resumen", tags=[TAG_EDAN_LOCALIDADES, TAG_CABECERA],
            summary="Resumen de mis localidades (totales + por estado)",
            description="Totales agregados de las localidades del usuario y desglose `por_estado[]` "
                        "con `id_edan_localidad_estado` + `nombre` + `cantidad` para refrescar badges.")
def mis_resumen_localidades(
    id_usuario: int | None = Query(None),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    uid = _user["id_usuario"] if _user["id_rol"] in ROLES_LOCALES else (id_usuario or _user["id_usuario"])
    return SuccessResponse(message="Resumen de mis localidades generado correctamente",
                           data=service.get_mis_localidades_resumen(db, uid) or {})


@router.get("/localidades/mis-estados", tags=[TAG_EDAN_LOCALIDADES, TAG_CABECERA],
            summary="Listado ligero de mis localidades (solo estado, sin secciones)",
            description="Lista ligera para refrescar badges de `id_edan_localidad_estado`: "
                        "cabecera + estado + flags de sync, SIN secciones (payload mínimo).")
def mis_estados_localidades(
    id_usuario: int | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    uid = _user["id_usuario"] if _user["id_rol"] in ROLES_LOCALES else (id_usuario or _user["id_usuario"])
    data, total = service.list_mis_localidades_estados(db, uid, skip=skip, limit=limit)
    return SuccessResponse(message="Estados de mis localidades listados correctamente", data=data, total=total)


@router.get("/localidades/{id_localidad}", tags=[TAG_EDAN_LOCALIDADES, TAG_CABECERA],
            summary="Obtener UNA localidad completa (todas las secciones)",
            description="Devuelve una sola localidad con TODAS sus secciones anidadas (`_build_localidad`).\n\n"
                        "- `modo=completo` (default): las 14 secciones.\n"
                        "- `modo=comprimido`: cabecera + los 22 flags `imp_*` + SOLO las secciones con datos.\n\n"
                        "**Modo offline:** `id_localidad` puede ser `id_local` (UUID) o `id_edan_localidad` (int).\n"
                        "**Uso web:** al hacer clic en un ítem de la lista, esta API carga todo el contenido.")
def obtener_localidad_completa(id_localidad: str,
                               modo: Literal["completo", "comprimido"] = Query("completo",
                                                                                description="completo=todas las secciones, comprimido=solo las que tienen datos"),
                               db: Session = Depends(get_db),
                               _user=Depends(get_current_user)):
    id_edan = service._resolve_localidad_id(db, id_localidad)
    result = service._build_localidad(db, id_edan, solo_con_datos=(modo == "comprimido"))
    if not result:
        raise HTTPException(status_code=404, detail=f"Localidad {id_localidad} no encontrada")
    return SuccessResponse(message="Localidad obtenida correctamente", data=result)


# ----------------------------------------------------------------------------
#  1) CABECERA — 1er paso del flujo (crea/actualiza solo la cabecera)
# ----------------------------------------------------------------------------

@router.post("/localidades/cabecera", status_code=201, tags=[TAG_EDAN_LOCALIDADES, TAG_CABECERA],
             dependencies=[Depends(require_rol(*ROLES_LOCALES))],
             summary="Crear/actualizar cabecera de localidad (1er paso del sync por secciones)",
             description="Crea o actualiza SOLO la cabecera de `edan.edan_localidades` usando `id_local` "
                         "(UUID offline) como clave de dedupe. NUNCA toca secciones.\n\n"
                         "Devuelve `id_edan_localidad` para poder enviar las secciones después.\n\n"
                         "**Roles permitidos:** 6 (UGR municipio), 7 (Responsable local).")
def upsert_cabecera(data: LocalidadCabeceraCreate, db: Session = Depends(get_db),
                    _user=Depends(get_current_user)):
    try:
        payload = data.model_dump()
        if payload.get("id_usuario") is None:
            payload["id_usuario"] = _user["id_usuario"]
        result = service.upsert_cabecera(db, payload)
    except Exception as e:
        db.rollback()
        raise db_error(e)
    return SuccessResponse(message="Cabecera guardada correctamente", data=result)


@router.get("/localidades/por-id-local/{id_local}", tags=[TAG_EDAN_LOCALIDADES, TAG_CABECERA],
            summary="Mapear id_local del móvil al id_edan_localidad del servidor")
def mapear_por_id_local(id_local: str, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    result = service._map_localidad_by_id_local(db, id_local)
    if not result:
        raise HTTPException(status_code=404, detail=f"No existe localidad con id_local={id_local}")
    return SuccessResponse(message="Localidad mapeada correctamente", data=result)


# ----------------------------------------------------------------------------
#  EJEMPLOS JSON POR SECCIÓN (para Swagger /docs/v2)
#  Muestran la estructura exacta que acepta cada POST de sección, tanto en
#  modo ONLINE (id_edan_localidad en el path) como OFFLINE (id_local UUID).
#  El `id_seccion` lo genera el cliente UNA vez y se REUSA en cada edición.
# ----------------------------------------------------------------------------

def _ejemplo_con_foto(updates: dict) -> dict:
    base = {
        "id_seccion": "1a0357323cb-659d0c9c3d415",
        "fotografia": "/uploads/reports/70101/abc123.png",
        "coordenada_lat": -17.3934,
        "coordenada_lon": -66.1574,
    }
    base.update(updates)
    return base


def _ejemplo_sin_foto(updates: dict) -> dict:
    base = {
        "id_seccion": "1a0357323cb-659d0c9c3d415",
    }
    base.update(updates)
    return base


BODY_EXAMPLES_SECCIONES: dict[str, dict] = {
    "impacto-poblacion": {
        "Objeto único": {"value": _ejemplo_sin_foto({"id_grupo_etario": 3, "fallecidos": 2, "heridos": 8, "desaparecidos": 0})},
        "Grupo (array)": {"value": [
            _ejemplo_sin_foto({"id_seccion": "sec_imp_01", "id_grupo_etario": 1, "fallecidos": 0, "heridos": 3}),
            _ejemplo_sin_foto({"id_seccion": "sec_imp_02", "id_grupo_etario": 4, "fallecidos": 1, "heridos": 2}),
        ]},
        "Compat v1 (string legacy)": {"value": _ejemplo_sin_foto({"rango": "Adulto de 19-60 años", "fallecidos": 2, "heridos": 8})},
    },
    "salud-establecimientos": {
        "Objeto único": {"value": _ejemplo_con_foto({
            "nombre_establecimiento": "Centro de Salud 15 de Agosto", "comunidad": "Nuevo Amanecer",
            "nivel_atencion": "2do Nivel", "dano_parcial": True, "dano_total": False,
            "medicos_afectados": 1, "enfermeras_afectadas": 2, "otros_afectados": 1})},
        "Grupo (array)": {"value": [
            _ejemplo_con_foto({"id_seccion": "sec_salud_01", "nombre_establecimiento": "Centro Salud 15 de Agosto", "comunidad": "Nuevo Amanecer", "nivel_atencion": "2do Nivel", "dano_parcial": True, "medicos_afectados": 1}),
            _ejemplo_con_foto({"id_seccion": "sec_salud_02", "nombre_establecimiento": "Posta San Juan", "comunidad": "San Juan", "nivel_atencion": "1er Nivel", "dano_total": True}),
        ]},
    },
    "danos-viales": {
        "Online + GPS": {"value": _ejemplo_con_foto({
            "via": True, "puente": False, "tramo": "Carretera al norte km 5", "dano_parcial": True,
            "dano_total": False, "km_danio": 3.5, "necesidades_inmediatas": "Reposición de señalética",
            "observaciones": "Tramo con derrumbe"})},
        "Grupo (array)": {"value": [
            _ejemplo_con_foto({"id_seccion": "sec_vial_01", "via": True, "puente": False, "tramo": "Carretera norte km 5", "dano_parcial": True, "km_danio": 3.5}),
            _ejemplo_con_foto({"id_seccion": "sec_vial_02", "via": False, "puente": True, "tramo": "Puente sobre río Tarija", "dano_total": True, "km_danio": 0}),
        ]},
    },
    "danos-infra-publica": {
        "Objeto único": {"value": _ejemplo_con_foto({
            "comunidad": "Nuevo Amanecer", "tipo_estructura": "Puente peatonal", "dano_parcial": False,
            "dano_total": True, "observaciones": "Estructura colapsada"})},
        "Grupo (array)": {"value": [
            _ejemplo_con_foto({"id_seccion": "sec_infra_01", "comunidad": "Nuevo Amanecer", "tipo_estructura": "Puente peatonal", "dano_total": True}),
            _ejemplo_con_foto({"id_seccion": "sec_infra_02", "comunidad": "San Juan", "tipo_estructura": "Alcaldía", "dano_parcial": True}),
        ]},
    },
    "servicios-basicos": {
        "Objeto único": {"value": _ejemplo_con_foto({
            "tipo": "energia_electrica", "dano_parcial": False, "dano_total": True,
            "necesidades_inmediatas": "Generador eléctrico", "observaciones": "Poste caído en red primaria"})},
        "Grupo (array)": {"value": [
            _ejemplo_con_foto({"id_seccion": "sec_sb_01", "tipo": "energia_electrica", "dano_total": True, "necesidades_inmediatas": "Generador"}),
            _ejemplo_con_foto({"id_seccion": "sec_sb_02", "tipo": "agua_potable", "dano_parcial": True, "necesidades_inmediatas": "Bombas de repuesto"}),
        ]},
    },
    "unidades-educativas": {
        "Objeto único": {"value": _ejemplo_con_foto({
            "nombre_establecimiento": "Escuela Nuevo Amanecer", "comunidad": "Nuevo Amanecer",
            "dano_parcial": True, "dano_total": False, "suspension_clases": True,
            "perdida_material": True, "funciona_albergue": False,
            "estudiantes": 120, "profesores": 5, "administrativos": 2,
            "observaciones": "Daños en techos"})},
        "Grupo (array)": {"value": [
            _ejemplo_con_foto({"id_seccion": "sec_ue_01", "nombre_establecimiento": "Escuela Nuevo Amanecer", "comunidad": "Nuevo Amanecer", "dano_parcial": True, "suspension_clases": True, "estudiantes": 120}),
            _ejemplo_con_foto({"id_seccion": "sec_ue_02", "nombre_establecimiento": "Colegio San Martín", "comunidad": "San Martín", "dano_total": True, "estudiantes": 200}),
        ]},
    },
    "danos-vivienda": {
        "Objeto único": {"value": _ejemplo_con_foto({
            "comunidad": "Nuevo Amanecer", "dano_parcial": 15, "dano_total": 4,
            "necesidades_inmediatas": "Carpas", "observaciones": "Viviendas de adobe"})},
        "Grupo (array)": {"value": [
            _ejemplo_con_foto({"id_seccion": "sec_viv_01", "comunidad": "Nuevo Amanecer", "dano_parcial": 15, "dano_total": 4, "necesidades_inmediatas": "Carpas"}),
            _ejemplo_con_foto({"id_seccion": "sec_viv_02", "comunidad": "San Juan", "dano_parcial": 8, "dano_total": 2}),
        ]},
    },
    "danos-agricultura": {
        "Objeto único": {"value": _ejemplo_con_foto({
            "tipo_cultivo": "Maíz", "id_cultivo": 12, "hectareas_afectadas": 5,
            "hectareas_perdidas": 2, "necesidades_inmediatas": "Semillas", "observaciones": "Cultivo en floración"})},
        "Grupo (array)": {"value": [
            _ejemplo_con_foto({"id_seccion": "sec_agri_01", "tipo_cultivo": "Maíz", "id_cultivo": 12, "hectareas_afectadas": 5, "hectareas_perdidas": 2, "necesidades_inmediatas": "Semillas"}),
            _ejemplo_con_foto({"id_seccion": "sec_agri_02", "tipo_cultivo": "Trigo", "id_cultivo": 15, "hectareas_afectadas": 3, "hectareas_perdidas": 1}),
        ]},
    },
    "danos-pecuarios": {
        "Objeto único": {"value": _ejemplo_con_foto({
            "especie": "Ganado vacuno", "id_especie": 3, "raza": "Cebuíno", "animales_afectados": 20,
            "animales_muertos": 6, "necesidades_inmediatas": "Forraje"})},
        "Grupo (array)": {"value": [
            _ejemplo_con_foto({"id_seccion": "sec_pec_01", "especie": "Ganado vacuno", "id_especie": 3, "animales_afectados": 20, "animales_muertos": 6}),
            _ejemplo_con_foto({"id_seccion": "sec_pec_02", "especie": "Ovinos", "id_especie": 8, "animales_afectados": 15, "animales_muertos": 3}),
        ]},
    },
    "infra-productiva": {
        "Objeto único": {"value": _ejemplo_con_foto({"tipo": "Almacén", "dano_parcial": 0, "dano_total": 1})},
        "Grupo (array)": {"value": [
            _ejemplo_con_foto({"id_seccion": "sec_infp_01", "tipo": "Almacén", "dano_parcial": 0, "dano_total": 1}),
            _ejemplo_con_foto({"id_seccion": "sec_infp_02", "tipo": "Molino", "dano_parcial": 1, "dano_total": 0}),
        ]},
    },
    "proteccion": {
        "Objeto único": {"value": _ejemplo_sin_foto({
            "id_grupo_vulnerable_catalogo": 2, "mujeres": 10, "hombres": 8,
            "apoyo_psicologico": True, "reposicion_documentos": False, "observaciones": "Niños y niñas"})},
        "Grupo (array)": {"value": [
            _ejemplo_sin_foto({"id_seccion": "sec_prot_01", "id_grupo_vulnerable_catalogo": 2, "mujeres": 10, "hombres": 8, "apoyo_psicologico": True}),
            _ejemplo_sin_foto({"id_seccion": "sec_prot_02", "id_grupo_vulnerable_catalogo": 5, "mujeres": 5, "hombres": 3, "observaciones": "Adultos mayores"}),
        ]},
    },
    "primera-respuesta": {
        "Objeto único": {"value": _ejemplo_sin_foto({"busqueda": True, "salvamento": False, "evacuacion": True, "observaciones": "Evacuación preventiva"})},
    },
    "necesidad-salud": {
        "Objeto único": {"value": _ejemplo_sin_foto({"numero_personas": 40, "otras_necesidades": "medicinas", "observaciones": "Falta insumos de primeros auxilios"})},
    },
    "necesidad-humanitaria": {
        "Objeto único": {"value": _ejemplo_sin_foto({"alimentos": True, "ropa_cama": True, "obs_alimentos": "Ración diaria", "obs_ropa_cama": "Frazadas y colchonetas"})},
    },
}


# ----------------------------------------------------------------------------
#  2) SECCIONES 1:N — grupo JSON (objeto único o array), UPSERT por id_seccion
# ----------------------------------------------------------------------------

SECCIONES_1N = [
    ("impacto-poblacion", TAG_IMPACTO_POBLACION, "Impacto en población",
     "edan_localidades_impacto_poblacion", service.create_impacto_poblacion, "id_impacto_poblacion"),
    ("salud-establecimientos", TAG_SALUD_ESTABLECIMIENTOS, "Establecimientos de salud",
     "edan_localidades_salud_establecimientos", service.create_establecimiento_salud, "id_establecimiento_salud"),
    ("danos-viales", TAG_DANOS_VIALES, "Daños viales",
     "edan_localidades_danos_viales", service.create_dano_vial, "id_dano_vial"),
    ("danos-infra-publica", TAG_DANOS_INFRA_PUBLICA, "Daños a infraestructura pública",
     "edan_localidades_danos_infra_publica", service.create_dano_infra_publica, "id_dano_infra"),
    ("servicios-basicos", TAG_SERVICIOS_BASICOS, "Servicios básicos",
     "edan_localidades_servicios_basicos", service.create_servicio_basico, "id_servicio_basico"),
    ("unidades-educativas", TAG_UNIDADES_EDUCATIVAS, "Unidades educativas",
     "edan_localidades_unidades_educativas", service.create_unidad_educativa, "id_unidad_educativa"),
    ("danos-vivienda", TAG_DANOS_VIVIENDA, "Daños a vivienda",
     "edan_localidades_danos_vivienda", service.create_dano_vivienda, "id_dano_vivienda"),
    ("danos-agricultura", TAG_DANOS_AGRICULTURA, "Daños a agricultura",
     "edan_localidades_danos_agricultura", service.create_dano_agricultura, "id_dano_agricultura"),
    ("danos-pecuarios", TAG_DANOS_PECUARIOS, "Daños pecuarios",
     "edan_localidades_danos_pecuario", service.create_dano_pecuario, "id_dano_pecuario"),
    ("infra-productiva", TAG_INFRA_PRODUCTIVA, "Infraestructura productiva",
     "edan_localidades_infra_productiva", service.create_infra_productiva, "id_infra_productiva"),
    ("proteccion", TAG_PROTECCION, "Grupos vulnerables (protección)",
     "edan_localidades_proteccion", service.create_proteccion, "id_grupo_vulnerable"),
]


def _registrar_seccion_1n(path, tag, label, tabla, create_fn, pk_col):
    @router.get(f"/localidades/{{id_localidad}}/{path}", tags=[TAG_EDAN_LOCALIDADES, tag],
                summary=f"Listar {label} de una localidad")
    def _list(id_localidad: str, skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=1000),
              db: Session = Depends(get_db), _user=Depends(get_current_user)):
        id_edan = service._resolve_localidad_id(db, id_localidad)
        params = {"id": id_edan, "limit": limit, "skip": skip}
        rows = service._rows(db, f"""
            SELECT * FROM edan.{tabla} WHERE id_edan_localidad = :id
            ORDER BY {pk_col} DESC LIMIT :limit OFFSET :skip
        """, params)
        total = service._row(db, f"SELECT COUNT(*) AS c FROM edan.{tabla} WHERE id_edan_localidad = :id",
                             {"id": id_edan})["c"]
        return SuccessResponse(message=f"{label} listados", data=[dict(r) for r in rows], total=total)

    schema_cls = PATH_TO_SCHEMA[path]

    @router.post(f"/localidades/{{id_localidad}}/{path}", status_code=201,
                 tags=[TAG_EDAN_LOCALIDADES, tag],
                 dependencies=[Depends(require_rol(*ROLES_LOCALES))],
                 summary=f"Crear/actualizar {label} (grupo JSON sin-foto)",
                 description="Acepta un objeto único o un array de objetos de la MISMA sección.\n"
                             "Cada fila se guarda con UPSERT por su `id_seccion` y los errores se "
                             "aíslan por fila: si un ítem falla, los demás se guardan igual.\n\n"
                             "**Modo offline:** `id_localidad` puede ser `id_local` (UUID) o `id_edan_localidad` (int).\n"
                             "Si usas `id_local`, el servidor resuelve automáticamente.\n\n"
                             "**Roles permitidos:** 6 (UGR municipio), 7 (Responsable local).")
    def _post(id_localidad: str, payload: schema_cls | list[schema_cls] = Body(...,
              openapi_examples=BODY_EXAMPLES_SECCIONES.get(path)),
              db: Session = Depends(get_db), _user=Depends(get_current_user)):
        id_edan = service._resolve_localidad_id(db, id_localidad)
        out = service.upsert_seccion_batch(db, id_edan, create_fn, payload)
        if out["results"]:
            return SuccessResponse(message=f"{label} sincronizados correctamente", data=out)
        raise HTTPException(status_code=400, detail={"message": "Ninguna fila pudo guardarse", "errors": out["errors"]})

    @router.delete(f"/localidades/{{id_localidad}}/{path}/seccion/{{id_seccion}}",
                   tags=[TAG_EDAN_LOCALIDADES, tag],
                   dependencies=[Depends(require_rol(*ROLES_LOCALES))],
                   responses={200: {"model": MessageResponse}},
                   summary=f"Eliminar un ítem de {label} por id_seccion")
    def _delete_item(id_localidad: str, id_seccion: str,
                     db: Session = Depends(get_db), _user=Depends(get_current_user)):
        id_edan = service._resolve_localidad_id(db, id_localidad)
        ok = service.delete_seccion_item(db, tabla, id_edan, id_seccion)
        if not ok:
            raise HTTPException(status_code=404, detail="Ítem con ese id_seccion no encontrado")
        return MessageResponse(message=f"{label}: ítem eliminado correctamente")

    @router.delete(f"/localidades/{{id_localidad}}/{path}",
                   tags=[TAG_EDAN_LOCALIDADES, tag],
                   dependencies=[Depends(require_rol(*ROLES_LOCALES))],
                   responses={200: {"model": MessageResponse}},
                   summary=f"Vaciar toda la sección {label} de una localidad")
    def _delete_all(id_localidad: str, db: Session = Depends(get_db), _user=Depends(get_current_user)):
        id_edan = service._resolve_localidad_id(db, id_localidad)
        n = service.delete_seccion_todo(db, tabla, id_edan)
        return MessageResponse(message=f"{label}: {n} registro(s) eliminado(s)")


for _reg in SECCIONES_1N:
    _registrar_seccion_1n(*_reg)


# ----------------------------------------------------------------------------
#  3) SECCIONES 1:1 — objeto único, UPSERT por id_seccion o id_edan_localidad
# ----------------------------------------------------------------------------

SECCIONES_1TO1 = [
    ("primera-respuesta", TAG_PRIMERA_RESPUESTA, "Primera respuesta",
     "edan_localidades_primera_respuesta", service.create_primera_respuesta),
    ("necesidad-salud", TAG_NECESIDAD_SALUD, "Necesidades de salud",
     "edan_localidades_salud_necesidades", service.create_necesidad_salud),
    ("necesidad-humanitaria", TAG_NECESIDAD_HUMANITARIA, "Necesidades humanitarias",
     "edan_localidades_necesidades_humanitarias", service.create_necesidad_humanitaria),
]


def _registrar_seccion_1to1(path, tag, label, tabla, create_fn):
    @router.get(f"/localidades/{{id_localidad}}/{path}", tags=[TAG_EDAN_LOCALIDADES, tag],
                summary=f"Obtener {label} (sección 1:1)")
    def _get(id_localidad: str, db: Session = Depends(get_db), _user=Depends(get_current_user)):
        id_edan = service._resolve_localidad_id(db, id_localidad)
        row = service._row(db, f"SELECT * FROM edan.{tabla} WHERE id_edan_localidad = :id",
                           {"id": id_edan})
        if not row:
            raise HTTPException(status_code=404, detail=f"{label} no registrada para esta localidad")
        return SuccessResponse(message=f"{label} obtenida", data=dict(row))

    @router.post(f"/localidades/{{id_localidad}}/{path}", status_code=201,
                 tags=[TAG_EDAN_LOCALIDADES, tag],
                 dependencies=[Depends(require_rol(*ROLES_LOCALES))],
                 summary=f"Crear/actualizar {label} (sección 1:1, UPSERT sin foto)",
                 description="UPSERT por `id_seccion` con fallback por `id_edan_localidad` cuando "
                             "no se envía `id_seccion` (nunca duplica).\n\n"
                             "**Modo offline:** `id_localidad` puede ser `id_local` (UUID) o `id_edan_localidad` (int).\n\n"
                             "**Roles permitidos:** 6 (UGR municipio), 7 (Responsable local).")
    def _post(id_localidad: str, payload: dict = Body(...,
            openapi_examples=BODY_EXAMPLES_SECCIONES.get(path)),
              db: Session = Depends(get_db), _user=Depends(get_current_user)):
        id_edan = service._resolve_localidad_id(db, id_localidad)
        try:
            row = create_fn(db, id_edan, {"_id": id_edan, **dict(payload)})
        except Exception as e:
            db.rollback()
            raise db_error(e)
        service._bump_localidad_fecha(db, id_edan)
        db.commit()
        return SuccessResponse(message=f"{label} guardada correctamente", data=row)

    @router.delete(f"/localidades/{{id_localidad}}/{path}",
                   tags=[TAG_EDAN_LOCALIDADES, tag],
                   dependencies=[Depends(require_rol(*ROLES_LOCALES))],
                   responses={200: {"model": MessageResponse}},
                   summary=f"Eliminar {label} de una localidad (sección 1:1)")
    def _delete(id_localidad: str, db: Session = Depends(get_db), _user=Depends(get_current_user)):
        id_edan = service._resolve_localidad_id(db, id_localidad)
        n = service.delete_seccion_todo(db, tabla, id_edan)
        if not n:
            raise HTTPException(status_code=404, detail=f"{label} no registrada para esta localidad")
        return MessageResponse(message=f"{label} eliminada correctamente")


for _reg in SECCIONES_1TO1:
    _registrar_seccion_1to1(*_reg)


# ----------------------------------------------------------------------------
#  CAMBIO DE ESTADO DE LOCALIDAD (por id_local)
# ----------------------------------------------------------------------------

@router.put("/localidades/estado", tags=[TAG_EDAN_LOCALIDADES],
            dependencies=[Depends(require_rol(*ROLES_LOCALES))],
            summary="Cambiar estado de localidad (V2, por id_local)",
            description="Actualiza `id_edan_localidad_estado` de una localidad usando su `id_local` (UUID offline).\n\n"
                        "**Estados disponibles:**\n"
                        "- 1: Borrador\n"
                        "- 2: Enviado UGR\n"
                        "- 3: Aprobado UGR\n"
                        "- 4: Rechazado UGR\n"
                        "- 5: Aprobado Ajuste UGR\n"
                        "- 6: En revisión UGR\n\n"
                        "**Roles permitidos:** 6 (UGR municipio), 7 (Responsable local).")
def cambiar_estado_localidad(data: LocalidadEstadoUpdateV2, db: Session = Depends(get_db),
                              _user=Depends(get_current_user)):
    try:
        result = service.cambiar_estado_localidad_por_id_local(db, data.id_local, data.id_edan_localidad_estado)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise db_error(e)
    if not result:
        raise HTTPException(status_code=404, detail=f"Localidad con id_local={data.id_local} no encontrada")
    return SuccessResponse(message="Estado de localidad actualizado correctamente", data=result)
