from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..database import get_db
from ..dependencies import get_current_user
from . import service
from .schemas import *

router = APIRouter(prefix="/edan", tags=["EDAN"])


# ── CATÁLOGOS (antes de /{id} para evitar captura errónea) ──

def _add_catalog_routes(
    parent: APIRouter,
    path: str,
    crud,
    CreateSchema,
    UpdateSchema,
    ResponseSchema,
    label: str,
):
    get_all, get_one, create, update, delete = crud

    @parent.get(f"/{path}", response_model=list[ResponseSchema])
    def _list(db: Session = Depends(get_db), _user=Depends(get_current_user)):
        return get_all(db)

    @parent.get(f"/{path}/{{id}}", response_model=ResponseSchema)
    def _get(id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
        result = get_one(db, id)
        if not result:
            raise HTTPException(status_code=404, detail=f"{label} no encontrado")
        return result

    @parent.post(f"/{path}", response_model=ResponseSchema, status_code=201)
    def _create(data: CreateSchema, db: Session = Depends(get_db), _user=Depends(get_current_user)):
        try:
            id = create(db, data.model_dump())
            return get_one(db, id)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @parent.put(f"/{path}/{{id}}", response_model=ResponseSchema)
    def _update(id: int, data: UpdateSchema, db: Session = Depends(get_db), _user=Depends(get_current_user)):
        result = update(db, id, data.model_dump())
        if not result:
            raise HTTPException(status_code=404, detail=f"{label} no encontrado")
        return result

    @parent.delete(f"/{path}/{{id}}", response_model=MessageResponse)
    def _delete(id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
        if not delete(db, id):
            raise HTTPException(status_code=404, detail=f"{label} no encontrado")
        return MessageResponse(message=f"{label} eliminado")


_add_catalog_routes(router, "tipo-evento", service.tipo_evento_crud,
                    TipoEventoCreate, TipoEventoUpdate, TipoEventoResponse, "Tipo de evento")

_add_catalog_routes(router, "grupo-etario", service.grupo_etario_crud,
                    GrupoEtarioCreate, GrupoEtarioUpdate, GrupoEtarioResponse, "Grupo etario")

_add_catalog_routes(router, "servicio-basico", service.servicio_basico_cat_crud,
                    ServicioBasicoCreate, ServicioBasicoUpdate, ServicioBasicoResponse, "Servicio básico")

_add_catalog_routes(router, "categoria-proteccion", service.categoria_proteccion_cat_crud,
                    CategoriaProteccionCreate, CategoriaProteccionUpdate, CategoriaProteccionResponse,
                    "Categoría de protección")

_add_catalog_routes(router, "ayuda-humanitaria", service.ayuda_humanitaria_cat_crud,
                    AyudaHumanitariaCreate, AyudaHumanitariaUpdate, AyudaHumanitariaResponse,
                    "Ayuda humanitaria")


# ── SUB-TABLAS ──

def _add_subtable_routes(
    parent: APIRouter,
    path: str,
    crud,
    CreateSchema,
    ResponseSchema,
    label: str,
):
    get_all, get_one, create, update, delete, _delete_by_edan = crud

    @parent.get(f"/{{id_edan}}/{path}", response_model=list[ResponseSchema])
    def _list(id_edan: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
        return get_all(db, id_edan)

    @parent.post(f"/{{id_edan}}/{path}", response_model=ResponseSchema, status_code=201)
    def _create(id_edan: int, data: CreateSchema, db: Session = Depends(get_db), _user=Depends(get_current_user)):
        try:
            payload = data.model_dump()
            payload["id_edan"] = id_edan
            id = create(db, payload)
            return get_one(db, id)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @parent.put(f"/{path}/{{id}}", response_model=ResponseSchema)
    def _update(id: int, data: CreateSchema, db: Session = Depends(get_db), _user=Depends(get_current_user)):
        result = update(db, id, data.model_dump())
        if not result:
            raise HTTPException(status_code=404, detail=f"{label} no encontrado")
        return result

    @parent.delete(f"/{path}/{{id}}", response_model=MessageResponse)
    def _delete(id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
        if not delete(db, id):
            raise HTTPException(status_code=404, detail=f"{label} no encontrado")
        return MessageResponse(message=f"{label} eliminado")


_add_subtable_routes(router, "poblacion-grupo", service.poblacion_grupo_crud,
                     PoblacionGrupoCreate, PoblacionGrupoResponse, "Población por grupo etario")

_add_subtable_routes(router, "tipos-evento", service.edan_tipo_evento_crud,
                     EdanTipoEventoCreate, EdanTipoEventoResponse, "Tipo de evento EDAN")

_add_subtable_routes(router, "primera-respuesta", service.primera_respuesta_crud,
                     PrimeraRespuestaCreate, PrimeraRespuestaResponse, "Primera respuesta")

_add_subtable_routes(router, "salud-establecimientos", service.salud_establecimiento_crud,
                     SaludEstablecimientoCreate, SaludEstablecimientoResponse, "Establecimiento de salud")

_add_subtable_routes(router, "salud-necesidades", service.salud_necesidades_crud,
                     SaludNecesidadesCreate, SaludNecesidadesResponse, "Necesidades de salud")

_add_subtable_routes(router, "infraestructura-vial", service.infraestructura_vial_crud,
                     InfraestructuraVialCreate, InfraestructuraVialResponse, "Infraestructura vial")

_add_subtable_routes(router, "infraestructura-publica", service.infraestructura_publica_crud,
                     InfraestructuraPublicaCreate, InfraestructuraPublicaResponse, "Infraestructura pública")

_add_subtable_routes(router, "servicios-basicos", service.servicio_basico_edan_crud,
                     ServicioBasicoEdanCreate, ServicioBasicoEdanResponse, "Servicio básico EDAN")

_add_subtable_routes(router, "educacion-dano", service.educacion_dano_crud,
                     EducacionDanoCreate, EducacionDanoResponse, "Daño educativo")

_add_subtable_routes(router, "educacion-afectacion", service.educacion_afectacion_crud,
                     EducacionAfectacionCreate, EducacionAfectacionResponse, "Afectación educativa")

_add_subtable_routes(router, "vivienda", service.vivienda_crud,
                     ViviendaCreate, ViviendaResponse, "Vivienda")

_add_subtable_routes(router, "agricultura", service.agricultura_crud,
                     AgriculturaCreate, AgriculturaResponse, "Agricultura")

_add_subtable_routes(router, "pecuaria", service.pecuaria_crud,
                     PecuariaCreate, PecuariaResponse, "Pecuaria")

_add_subtable_routes(router, "infraestructura-productiva", service.infra_productiva_crud,
                     InfraProductivaCreate, InfraProductivaResponse, "Infraestructura productiva")

_add_subtable_routes(router, "proteccion", service.proteccion_crud,
                     ProteccionCreate, ProteccionResponse, "Protección")

_add_subtable_routes(router, "ayuda-humanitaria-edan", service.ayuda_humanitaria_edan_crud,
                     AyudaHumanitariaEdanCreate, AyudaHumanitariaEdanResponse, "Ayuda humanitaria EDAN")

_add_subtable_routes(router, "comunidades", service.comunidad_crud,
                     ComunidadCreate, ComunidadResponse, "Comunidad")


# ── EDAN PRINCIPAL (al final para que /{id} no capture rutas de catálogos/sub-tablas) ──

@router.get("/", response_model=list[EdanResponse])
def listar_edans(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    return service.get_edans(db, skip=skip, limit=limit)


@router.get("/{id}", response_model=EdanResponse)
def obtener_edan(id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    result = service.get_edan_completo(db, id)
    if not result:
        raise HTTPException(status_code=404, detail="EDAN no encontrado")
    return result


@router.post("/", response_model=EdanResponse, status_code=201)
def crear_edan(data: EdanCreate, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    try:
        id = service.create_edan(db, data.model_dump())
        return service.get_edan(db, id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{id}", response_model=EdanResponse)
def actualizar_edan(id: int, data: EdanUpdate, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    result = service.update_edan(db, id, data.model_dump())
    if not result:
        raise HTTPException(status_code=404, detail="EDAN no encontrado")
    return result


@router.delete("/{id}", response_model=MessageResponse)
def eliminar_edan(id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    if not service.delete_edan(db, id):
        raise HTTPException(status_code=404, detail="EDAN no encontrado")
    return MessageResponse(message="EDAN eliminado")
