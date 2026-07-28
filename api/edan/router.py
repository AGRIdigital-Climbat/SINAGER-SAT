from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session
from ..database import get_db
from ..dependencies import get_current_user
from ..auth.permisos import module_permiso
from ..response import SuccessResponse, ErrorResponse, MessageResponse
from ..upload import save_upload_file
from . import service
from .schemas import *

router = APIRouter(prefix="/edan", dependencies=[Depends(module_permiso("EDAN"))])


# ──────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────

def _catalog_crud_routes(parent, path, crud, Create, Update, Response, label, tag):
    get_all, get_one, create, update, delete = crud

    @parent.get(f"/{path}", tags=[tag], responses={200: {"model": SuccessResponse}})
    def _list(db: Session = Depends(get_db), _user=Depends(get_current_user)):
        data = get_all(db)
        return SuccessResponse(message=f"{label} listados correctamente", data=data, total=len(data))

    @parent.get(f"/{path}/{{id}}", tags=[tag], responses={200: {"model": SuccessResponse}})
    def _get(id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
        result = get_one(db, id)
        if not result:
            raise HTTPException(status_code=404, detail=f"{label} no encontrado")
        return SuccessResponse(message=f"{label} obtenido correctamente", data=result)

    @parent.post(f"/{path}", status_code=201, tags=[tag], responses={201: {"model": SuccessResponse}})
    def _create(data: Create, db: Session = Depends(get_db), _user=Depends(get_current_user)):
        try:
            id = create(db, data.model_dump())
            result = get_one(db, id)
            return SuccessResponse(message=f"{label} creado correctamente", data=result)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @parent.put(f"/{path}/{{id}}", tags=[tag], responses={200: {"model": SuccessResponse}})
    def _update(id: int, data: Update, db: Session = Depends(get_db), _user=Depends(get_current_user)):
        result = update(db, id, data.model_dump())
        if not result:
            raise HTTPException(status_code=404, detail=f"{label} no encontrado")
        return SuccessResponse(message=f"{label} actualizado correctamente", data=result)

    @parent.delete(f"/{path}/{{id}}", tags=[tag], responses={200: {"model": MessageResponse}})
    def _delete(id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
        if not delete(db, id):
            raise HTTPException(status_code=404, detail=f"{label} no encontrado")
        return MessageResponse(message=f"{label} eliminado correctamente")


def _subtable_crud_routes(parent, path, crud, Create, Response, label, tag):
    get_all, get_one, create, update, delete, _delete_by_edan = crud

    @parent.get(f"/{{id_edan}}/{path}", tags=[tag], responses={200: {"model": SuccessResponse}})
    def _list(id_edan: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
        data = get_all(db, id_edan)
        return SuccessResponse(message=f"{label} listados correctamente", data=data, total=len(data))

    @parent.post(f"/{{id_edan}}/{path}", status_code=201, tags=[tag], responses={201: {"model": SuccessResponse}})
    def _create(id_edan: int, data: Create, db: Session = Depends(get_db), _user=Depends(get_current_user)):
        try:
            payload = data.model_dump()
            payload["id_edan"] = id_edan
            id = create(db, payload)
            result = get_one(db, id)
            return SuccessResponse(message=f"{label} creado correctamente", data=result)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @parent.put(f"/{path}/{{id}}", tags=[tag], responses={200: {"model": SuccessResponse}})
    def _update(id: int, data: Create, db: Session = Depends(get_db), _user=Depends(get_current_user)):
        result = update(db, id, data.model_dump())
        if not result:
            raise HTTPException(status_code=404, detail=f"{label} no encontrado")
        return SuccessResponse(message=f"{label} actualizado correctamente", data=result)

    @parent.delete(f"/{path}/{{id}}", tags=[tag], responses={200: {"model": MessageResponse}})
    def _delete(id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
        if not delete(db, id):
            raise HTTPException(status_code=404, detail=f"{label} no encontrado")
        return MessageResponse(message=f"{label} eliminado correctamente")


TAG_MAIN     = "EDAN > Formulario"
TAG_CATALOG  = "EDAN > Catálogos"
TAG_POBLAC   = "EDAN > Población"
TAG_SALUD    = "EDAN > Salud"
TAG_INFRA    = "EDAN > Infraestructura"
TAG_EDUC     = "EDAN > Educación"
TAG_PRODUCC  = "EDAN > Producción"
TAG_PROTECC  = "EDAN > Protección"


# ──────────────────────────────────────────────
#  CATÁLOGOS
# ──────────────────────────────────────────────

_catalog_crud_routes(router, "tipo-evento", service.tipo_evento_crud,
                     TipoEventoCreate, TipoEventoUpdate, TipoEventoResponse,
                     "Tipo de evento", TAG_CATALOG)

_catalog_crud_routes(router, "grupo-etario", service.grupo_etario_crud,
                     GrupoEtarioCreate, GrupoEtarioUpdate, GrupoEtarioResponse,
                     "Grupo etario", TAG_CATALOG)

_catalog_crud_routes(router, "servicio-basico", service.servicio_basico_cat_crud,
                     ServicioBasicoCreate, ServicioBasicoUpdate, ServicioBasicoResponse,
                     "Servicio básico", TAG_CATALOG)

_catalog_crud_routes(router, "categoria-proteccion", service.categoria_proteccion_cat_crud,
                     CategoriaProteccionCreate, CategoriaProteccionUpdate, CategoriaProteccionResponse,
                     "Categoría de protección", TAG_CATALOG)

_catalog_crud_routes(router, "ayuda-humanitaria", service.ayuda_humanitaria_cat_crud,
                     AyudaHumanitariaCreate, AyudaHumanitariaUpdate, AyudaHumanitariaResponse,
                     "Ayuda humanitaria", TAG_CATALOG)


# ──────────────────────────────────────────────
#  POBLACIÓN Y EVENTOS
# ──────────────────────────────────────────────

_subtable_crud_routes(router, "poblacion-grupo", service.poblacion_grupo_crud,
                      PoblacionGrupoCreate, PoblacionGrupoResponse,
                      "Población por grupo etario", TAG_POBLAC)

_subtable_crud_routes(router, "tipos-evento", service.edan_tipo_evento_crud,
                      EdanTipoEventoCreate, EdanTipoEventoResponse,
                      "Tipo de evento EDAN", TAG_POBLAC)


# ──────────────────────────────────────────────
#  SALUD
# ──────────────────────────────────────────────

_subtable_crud_routes(router, "primera-respuesta", service.primera_respuesta_crud,
                      PrimeraRespuestaCreate, PrimeraRespuestaResponse,
                      "Primera respuesta", TAG_SALUD)

_subtable_crud_routes(router, "salud-establecimientos", service.salud_establecimiento_crud,
                      SaludEstablecimientoCreate, SaludEstablecimientoResponse,
                      "Establecimiento de salud", TAG_SALUD)

_subtable_crud_routes(router, "salud-necesidades", service.salud_necesidades_crud,
                      SaludNecesidadesCreate, SaludNecesidadesResponse,
                      "Necesidades de salud", TAG_SALUD)


# ──────────────────────────────────────────────
#  INFRAESTRUCTURA
# ──────────────────────────────────────────────

_subtable_crud_routes(router, "infraestructura-vial", service.infraestructura_vial_crud,
                      InfraestructuraVialCreate, InfraestructuraVialResponse,
                      "Infraestructura vial", TAG_INFRA)

_subtable_crud_routes(router, "infraestructura-publica", service.infraestructura_publica_crud,
                      InfraestructuraPublicaCreate, InfraestructuraPublicaResponse,
                      "Infraestructura pública", TAG_INFRA)

_subtable_crud_routes(router, "servicios-basicos", service.servicio_basico_edan_crud,
                      ServicioBasicoEdanCreate, ServicioBasicoEdanResponse,
                      "Servicio básico EDAN", TAG_INFRA)


# ──────────────────────────────────────────────
#  EDUCACIÓN
# ──────────────────────────────────────────────

_subtable_crud_routes(router, "educacion-dano", service.educacion_dano_crud,
                      EducacionDanoCreate, EducacionDanoResponse,
                      "Daño educativo", TAG_EDUC)

_subtable_crud_routes(router, "educacion-afectacion", service.educacion_afectacion_crud,
                      EducacionAfectacionCreate, EducacionAfectacionResponse,
                      "Afectación educativa", TAG_EDUC)


# ──────────────────────────────────────────────
#  PRODUCCIÓN (Vivienda, Agro, Pecuaria)
# ──────────────────────────────────────────────

_subtable_crud_routes(router, "vivienda", service.vivienda_crud,
                      ViviendaCreate, ViviendaResponse,
                      "Vivienda", TAG_PRODUCC)

_subtable_crud_routes(router, "agricultura", service.agricultura_crud,
                      AgriculturaCreate, AgriculturaResponse,
                      "Agricultura", TAG_PRODUCC)

_subtable_crud_routes(router, "pecuaria", service.pecuaria_crud,
                      PecuariaCreate, PecuariaResponse,
                      "Pecuaria", TAG_PRODUCC)

_subtable_crud_routes(router, "infraestructura-productiva", service.infra_productiva_crud,
                      InfraProductivaCreate, InfraProductivaResponse,
                      "Infraestructura productiva", TAG_PRODUCC)


# ──────────────────────────────────────────────
#  PROTECCIÓN Y COMUNIDAD
# ──────────────────────────────────────────────

_subtable_crud_routes(router, "proteccion", service.proteccion_crud,
                      ProteccionCreate, ProteccionResponse,
                      "Protección", TAG_PROTECC)

_subtable_crud_routes(router, "ayuda-humanitaria-edan", service.ayuda_humanitaria_edan_crud,
                      AyudaHumanitariaEdanCreate, AyudaHumanitariaEdanResponse,
                      "Ayuda humanitaria EDAN", TAG_PROTECC)

_subtable_crud_routes(router, "comunidades", service.comunidad_crud,
                      ComunidadCreate, ComunidadResponse,
                      "Comunidad", TAG_PROTECC)


# ──────────────────────────────────────────────
#  EDAN PRINCIPAL (al final para no capturar /{id})
# ──────────────────────────────────────────────

@router.get("/", tags=[TAG_MAIN], responses={200: {"model": SuccessResponse}})
def listar_edans(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    data = service.get_edans(db, skip=skip, limit=limit)
    return SuccessResponse(message="EDANs listados correctamente", data=data, total=len(data))


@router.get("/{id}", tags=[TAG_MAIN], responses={200: {"model": SuccessResponse}})
def obtener_edan(id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    result = service.get_edan_completo(db, id)
    if not result:
        raise HTTPException(status_code=404, detail="EDAN no encontrado")
    return SuccessResponse(message="EDAN obtenido correctamente", data=result)


@router.post("/", status_code=201, tags=[TAG_MAIN], responses={201: {"model": SuccessResponse}})
def crear_edan(data: EdanCreate, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    try:
        id = service.create_edan(db, data.model_dump())
        result = service.get_edan(db, id)
        return SuccessResponse(message="EDAN creado correctamente", data=result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/con-foto", status_code=201, tags=[TAG_MAIN], responses={201: {"model": SuccessResponse}})
async def crear_edan_con_foto(
    file: UploadFile = File(...),
    codigo_edan: str | None = Form(None),
    id_departamento: int | None = Form(None),
    id_municipio: int | None = Form(None),
    nombre_alcalde: str | None = Form(None),
    telefono_alcalde: str | None = Form(None),
    fecha_llenado: str | None = Form(None),
    fecha_evento: str | None = Form(None),
    hora_evento: str | None = Form(None),
    localidades_afectadas: int = Form(0),
    total_poblacion_afectada: int = Form(0),
    total_familias_afectadas: int = Form(0),
    total_familias_damnificadas: int = Form(0),
    nombre_responsable: str | None = Form(None),
    cargo_responsable: str | None = Form(None),
    telefono_responsable: str | None = Form(None),
    email_responsable: str | None = Form(None),
    usuario_registro: int | None = Form(None),
    id_reporte_rea: int | None = Form(None),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        fotografia = await save_upload_file(file, db, id_municipio)

        data = {
            "codigo_edan": codigo_edan,
            "id_departamento": id_departamento,
            "id_municipio": id_municipio,
            "nombre_alcalde": nombre_alcalde,
            "telefono_alcalde": telefono_alcalde,
            "fecha_llenado": fecha_llenado,
            "fecha_evento": fecha_evento,
            "hora_evento": hora_evento,
            "localidades_afectadas": localidades_afectadas,
            "total_poblacion_afectada": total_poblacion_afectada,
            "total_familias_afectadas": total_familias_afectadas,
            "total_familias_damnificadas": total_familias_damnificadas,
            "nombre_responsable": nombre_responsable,
            "cargo_responsable": cargo_responsable,
            "telefono_responsable": telefono_responsable,
            "email_responsable": email_responsable,
            "usuario_registro": usuario_registro,
            "id_reporte_rea": id_reporte_rea,
            "fotografia": fotografia,
        }

        id = service.create_edan(db, data)
        result = service.get_edan(db, id)
        return SuccessResponse(message="EDAN creado correctamente", data=result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{id}", tags=[TAG_MAIN], responses={200: {"model": SuccessResponse}})
def actualizar_edan(id: int, data: EdanUpdate, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    result = service.update_edan(db, id, data.model_dump())
    if not result:
        raise HTTPException(status_code=404, detail="EDAN no encontrado")
    return SuccessResponse(message="EDAN actualizado correctamente", data=result)


@router.delete("/{id}", tags=[TAG_MAIN], responses={200: {"model": MessageResponse}})
def eliminar_edan(id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    if not service.delete_edan(db, id):
        raise HTTPException(status_code=404, detail="EDAN no encontrado")
    return MessageResponse(message="EDAN eliminado correctamente")
