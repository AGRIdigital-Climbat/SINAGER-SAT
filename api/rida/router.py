from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user
from ..response import SuccessResponse, MessageResponse, DataListResponse, DataItemResponse
from ..auth.permisos import module_permiso
from ..edan.utils import require_rol, db_error
from . import service
from .schemas import (
    CatTipoAlbergueResponse, CatEstadoFormularioResponse,
    CatParentescoResponse, CatTipoDiscapacidadResponse,
    FormularioRidaCreate, FormularioRidaUpdate, FormularioRidaResponse,
    FamiliaCreate, FamiliaUpdate, FamiliaResponse,
    IntegranteCreate, IntegranteUpdate, IntegranteResponse,
    UbicacionFamiliaCreate, UbicacionFamiliaUpdate, UbicacionFamiliaResponse,
    EmpadronamientoSyncIn,
)

router = APIRouter(
    prefix="/rida/empadronamiento",
    dependencies=[Depends(module_permiso("RIDA"))],
)

TAG_EMPADRONAMIENTO = "RIDA > Empadronamiento"
TAG_HIJOS = "RIDA > Hijos"
TAG_SYNC = "RIDA > Sync"

ROLES_ESCRITURA = (1, 2, 6, 7)


# ============================================================================
#  CATÁLOGOS
# ============================================================================

@router.get("/cat-tipo-albergue", tags=[TAG_EMPADRONAMIENTO], response_model=DataListResponse[CatTipoAlbergueResponse],
            summary="Tipos de albergue",
            description="Catálogo rida.cat_tipo_albergue (id_cat_tipo_albergue, nombre).")
def listar_cat_tipo_albergue(db: Session = Depends(get_db)):
    data = service.catalogo_albergues(db)
    return SuccessResponse(message="Tipos de albergue listados correctamente", data=data, total=len(data))


@router.get("/cat-estado-formulario", tags=[TAG_EMPADRONAMIENTO], response_model=DataListResponse[CatEstadoFormularioResponse],
            summary="Estados de formulario",
            description="Catálogo rida.cat_estado_formulario: PENDIENTE(1), EN_PROCESO(2), CERRADO(3).")
def listar_cat_estado_formulario(db: Session = Depends(get_db)):
    data = service.catalogo_estados_formulario(db)
    return SuccessResponse(message="Estados de formulario listados correctamente", data=data, total=len(data))


@router.get("/cat-parentesco", tags=[TAG_EMPADRONAMIENTO], response_model=DataListResponse[CatParentescoResponse],
            summary="Parentescos",
            description="Catálogo rida.cat_parentesco (activos).")
def listar_cat_parentesco(db: Session = Depends(get_db)):
    data = service.catalogo_parentescos(db)
    return SuccessResponse(message="Parentescos listados correctamente", data=data, total=len(data))


@router.get("/cat-tipo-discapacidad", tags=[TAG_EMPADRONAMIENTO], response_model=DataListResponse[CatTipoDiscapacidadResponse],
            summary="Tipos de discapacidad",
            description="Catálogo rida.cat_tipo_discapacidad (activos).")
def listar_cat_tipo_discapacidad(db: Session = Depends(get_db)):
    data = service.catalogo_discapacidades(db)
    return SuccessResponse(message="Tipos de discapacidad listados correctamente", data=data, total=len(data))


# ============================================================================
#  FORMULARIO RIDA
# ============================================================================

@router.get("/formularios", tags=[TAG_EMPADRONAMIENTO], response_model=DataListResponse[FormularioRidaResponse],
            summary="Listar formularios de empadronamiento",
            description="Lista paginada de formularios con filtros. Scope geográfico forzado:\n"
                        "- Roles 6/7 (UGR/Responsable): solo sus propios formularios.\n"
                        "- Rol 8 (Alcalde): solo su municipio.\n"
                        "- Roles 5/9 (DGR/VIDECI Deptal.): solo su departamento.\n"
                        "- Roles 1-4 (nacional): todo el país, honra filtros de geo/query.")
def listar_formularios(
    id_edan: int | None = Query(None, description="Filtrar por EDAN"),
    id_edan_localidad: int | None = Query(None),
    id_estado: int | None = Query(None, description="1=PENDIENTE, 2=EN_PROCESO, 3=CERRADO"),
    id_usuario: int | None = Query(None),
    id_departamento: int | None = Query(None, description="Filtrar por departamento"),
    id_provincia: int | None = Query(None, description="Filtrar por provincia"),
    id_municipio: int | None = Query(None, description="Filtrar por municipio"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    todos: bool = Query(False, description="Devolver todos sin paginar"),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        data, total = service.listar_formularios(db, _user, {
            "id_edan": id_edan, "id_edan_localidad": id_edan_localidad,
            "id_estado": id_estado, "id_usuario": id_usuario,
            "id_departamento": id_departamento, "id_provincia": id_provincia,
            "id_municipio": id_municipio,
        }, skip=skip, limit=limit, todos=todos)
        return SuccessResponse(message="Formularios listados correctamente", data=data, total=total)
    except Exception as e:
        raise db_error(e)


@router.get("/formularios/mis", tags=[TAG_EMPADRONAMIENTO], response_model=DataListResponse[FormularioRidaResponse],
            summary="Mis formularios",
            description="6/7 → propios; 8 → municipio forzado; 5/9 → departamento forzado; 1-4 → todo el país.")
def mis_formularios(
    id_estado: int | None = Query(None),
    id_usuario: int | None = Query(None),
    id_departamento: int | None = Query(None, description="Filtrar por departamento"),
    id_provincia: int | None = Query(None, description="Filtrar por provincia"),
    id_municipio: int | None = Query(None, description="Filtrar por municipio"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    todos: bool = Query(False, description="Devolver todos sin paginar"),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        data, total = service.mis_formularios(db, _user, {
            "id_estado": id_estado, "id_usuario": id_usuario,
            "id_departamento": id_departamento, "id_provincia": id_provincia,
            "id_municipio": id_municipio,
        }, skip=skip, limit=limit, todos=todos)
        return SuccessResponse(message="Formularios listados correctamente", data=data, total=total)
    except Exception as e:
        raise db_error(e)


@router.get("/formularios/{id_formulario}", tags=[TAG_EMPADRONAMIENTO], response_model=DataItemResponse[FormularioRidaResponse],
            summary="Formulario con familias (árbol completo)",
            description="Formulario + familias con sus integrantes y ubicaciones GPS.")
def obtener_formulario(
    id_formulario: int,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    service._validar_scope_formulario(db, _user, id_formulario)
    result = service.get_formulario(db, id_formulario)
    if not result:
        raise HTTPException(status_code=404, detail="Formulario no encontrado")
    return SuccessResponse(message="Formulario obtenido correctamente", data=result)


@router.post("/formularios", tags=[TAG_EMPADRONAMIENTO], status_code=201,
             response_model=DataItemResponse[FormularioRidaResponse],
             dependencies=[Depends(require_rol(*ROLES_ESCRITURA))],
             summary="Crear formulario de empadronamiento",
             description="Crea el empadronamiento de una localidad (1:1).\n\n"
                         "Regla de negocio: el **EDAN debe estar aprobado** (estado 3 ó 5).\n"
                         "Si no se envía `id_edan`, se toma el del EDAN de la localidad.\n"
                         "Error 400 si la localidad ya tiene un formulario.")
def crear_formulario(
    data: FormularioRidaCreate,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        result = service.crear_formulario(db, data.model_dump(), _user["id_usuario"])
        return SuccessResponse(message="Formulario creado correctamente", data=result)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise db_error(e)


@router.put("/formularios/{id_formulario}", tags=[TAG_EMPADRONAMIENTO],
            response_model=DataItemResponse[FormularioRidaResponse],
            dependencies=[Depends(require_rol(*ROLES_ESCRITURA))],
            summary="Actualizar formulario",
            description="Actualiza id_edan y/o id_estado del formulario.")
def actualizar_formulario(
    id_formulario: int,
    data: FormularioRidaUpdate,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        service._validar_scope_formulario(db, _user, id_formulario)
        result = service.actualizar_formulario(db, id_formulario, data.model_dump())
        if not result:
            raise HTTPException(status_code=404, detail="Formulario no encontrado")
        return SuccessResponse(message="Formulario actualizado correctamente", data=result)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise db_error(e)


@router.delete("/formularios/{id_formulario}", tags=[TAG_EMPADRONAMIENTO],
               response_model=MessageResponse,
               dependencies=[Depends(require_rol(*ROLES_ESCRITURA))],
               summary="Eliminar formulario",
               description="Elimina el formulario con sus familias, integrantes y ubicaciones.\n"
                           "Roles 6/7 solo pueden eliminar formularios propios; admin/nacional todo.")
def eliminar_formulario(
    id_formulario: int,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        service._validar_scope_formulario(db, _user, id_formulario)
        if not service.eliminar_formulario(db, id_formulario, _user):
            raise HTTPException(status_code=404, detail="Formulario no encontrado")
        return MessageResponse(message="Formulario eliminado correctamente", id=id_formulario)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise db_error(e)


# ============================================================================
#  FAMILIA
# ============================================================================

@router.get("/formularios/{id_formulario}/familias", tags=[TAG_HIJOS],
            response_model=DataListResponse[FamiliaResponse],
            summary="Familias de un formulario (hijos)",
            description="Lista las familias del formulario (con integrantes y ubicaciones). "
                        "Paginada; `todos=true` devuelve todas.")
def listar_familias_formulario(
    id_formulario: int,
    id_departamento: int | None = Query(None, description="Filtrar por departamento"),
    id_provincia: int | None = Query(None, description="Filtrar por provincia"),
    id_municipio: int | None = Query(None, description="Filtrar por municipio"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    todos: bool = Query(False, description="Devolver todas las familias sin paginar"),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    service._validar_scope_formulario(db, _user, id_formulario)
    if not service._row(db, "SELECT 1 FROM rida.formulario_rida WHERE id_formulario = :id",
                        {"id": id_formulario}):
        raise HTTPException(status_code=404, detail="Formulario no encontrado")
    geo_filtros = {
        "id_departamento": id_departamento,
        "id_provincia": id_provincia,
        "id_municipio": id_municipio,
    }
    data, total = service.list_familias_paginado(db, id_formulario, geo_filtros=geo_filtros, skip=skip, limit=limit, todos=todos)
    return SuccessResponse(message="Familias listadas correctamente", data=data, total=total)


@router.get("/familias/{id_familia}", tags=[TAG_HIJOS],
            response_model=DataItemResponse[FamiliaResponse],
            summary="Familia con integrantes y ubicaciones (hijo)",
            description="Obtiene una familia específica con sus integrantes y ubicaciones anidadas.")
def obtener_familia(
    id_familia: int,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    service._validar_scope_familia(db, _user, id_familia)
    result = service.get_familia(db, id_familia)
    if not result:
        raise HTTPException(status_code=404, detail="Familia no encontrada")
    return SuccessResponse(message="Familia obtenida correctamente", data=result)


@router.post("/formularios/{id_formulario}/familias", tags=[TAG_HIJOS], status_code=201,
             response_model=DataItemResponse[FamiliaResponse],
             dependencies=[Depends(require_rol(*ROLES_ESCRITURA))],
             summary="Crear familia (hijo)",
             description="Crea una familia dentro del formulario. Si `id_familia_off` ya existe, "
                         "actualiza (UPSERT idempotente para sync móvil).")
def crear_familia(
    id_formulario: int,
    data: FamiliaCreate,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        service._validar_scope_formulario(db, _user, id_formulario)
        payload = data.model_dump()
        payload["id_formulario"] = id_formulario
        result = service.crear_familia(db, payload, _user["id_usuario"])
        return SuccessResponse(message="Familia creada correctamente", data=result)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise db_error(e)


@router.put("/familias/{id_familia}", tags=[TAG_HIJOS],
            response_model=DataItemResponse[FamiliaResponse],
            dependencies=[Depends(require_rol(*ROLES_ESCRITURA))],
            summary="Actualizar familia (hijo)",
            description="Actualiza los datos de una familia existente.")
def actualizar_familia(
    id_familia: int,
    data: FamiliaUpdate,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        service._validar_scope_familia(db, _user, id_familia)
        result = service.actualizar_familia(db, id_familia, data.model_dump())
        if not result:
            raise HTTPException(status_code=404, detail="Familia no encontrada")
        return SuccessResponse(message="Familia actualizada correctamente", data=result)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise db_error(e)


@router.delete("/familias/{id_familia}", tags=[TAG_HIJOS],
               response_model=MessageResponse,
               dependencies=[Depends(require_rol(*ROLES_ESCRITURA))],
               summary="Eliminar familia (hijo)",
               description="Elimina la familia con sus integrantes y ubicaciones.")
def eliminar_familia(
    id_familia: int,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        service._validar_scope_familia(db, _user, id_familia)
        if not service.eliminar_familia(db, id_familia):
            raise HTTPException(status_code=404, detail="Familia no encontrada")
        return MessageResponse(message="Familia eliminada correctamente", id=id_familia)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise db_error(e)


# ============================================================================
#  INTEGRANTE
# ============================================================================

@router.get("/familias/{id_familia}/integrantes", tags=[TAG_HIJOS],
            response_model=DataListResponse[IntegranteResponse],
            summary="Integrantes de una familia (hijos)",
            description="Lista los integrantes de la familia. Paginada; `todos=true` devuelve todos.")
def listar_integrantes_familia(
    id_familia: int,
    id_departamento: int | None = Query(None, description="Filtrar por departamento"),
    id_provincia: int | None = Query(None, description="Filtrar por provincia"),
    id_municipio: int | None = Query(None, description="Filtrar por municipio"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    todos: bool = Query(False, description="Devolver todos los integrantes sin paginar"),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    service._validar_scope_familia(db, _user, id_familia)
    geo_filtros = {
        "id_departamento": id_departamento,
        "id_provincia": id_provincia,
        "id_municipio": id_municipio,
    }
    data, total = service.list_integrantes_paginado(db, id_familia, geo_filtros=geo_filtros, skip=skip, limit=limit, todos=todos)
    return SuccessResponse(message="Integrantes listados correctamente", data=data, total=total)


@router.get("/integrantes/{id_integrante}", tags=[TAG_HIJOS],
            response_model=DataItemResponse[IntegranteResponse],
            summary="Integrante (hijo)",
            description="Obtiene un integrante específico de una familia.")
def obtener_integrante(
    id_integrante: int,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    service._validar_scope_integrante(db, _user, id_integrante)
    result = service.get_integrante(db, id_integrante)
    if not result:
        raise HTTPException(status_code=404, detail="Integrante no encontrado")
    return SuccessResponse(message="Integrante obtenido correctamente", data=result)


@router.post("/familias/{id_familia}/integrantes", tags=[TAG_HIJOS], status_code=201,
             response_model=DataItemResponse[IntegranteResponse],
             dependencies=[Depends(require_rol(*ROLES_ESCRITURA))],
             summary="Crear integrante (hijo)",
             description="Crea un integrante en la familia. Si `id_integrante_off` ya existe, "
                         "actualiza (UPSERT idempotente). Solo un `es_jefe=true` por familia.")
def crear_integrante(
    id_familia: int,
    data: IntegranteCreate,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        service._validar_scope_familia(db, _user, id_familia)
        payload = data.model_dump()
        payload["id_familia"] = id_familia
        result = service.crear_integrante(db, payload)
        return SuccessResponse(message="Integrante creado correctamente", data=result)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise db_error(e)


@router.put("/integrantes/{id_integrante}", tags=[TAG_HIJOS],
            response_model=DataItemResponse[IntegranteResponse],
            dependencies=[Depends(require_rol(*ROLES_ESCRITURA))],
            summary="Actualizar integrante (hijo)",
            description="Actualiza los datos de un integrante existente.")
def actualizar_integrante(
    id_integrante: int,
    data: IntegranteUpdate,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        service._validar_scope_integrante(db, _user, id_integrante)
        result = service.actualizar_integrante(db, id_integrante, data.model_dump())
        if not result:
            raise HTTPException(status_code=404, detail="Integrante no encontrado")
        return SuccessResponse(message="Integrante actualizado correctamente", data=result)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise db_error(e)


@router.delete("/integrantes/{id_integrante}", tags=[TAG_HIJOS],
               response_model=MessageResponse,
               dependencies=[Depends(require_rol(*ROLES_ESCRITURA))],
               summary="Eliminar integrante (hijo)",
               description="Elimina un integrante y sus datos asociados.")
def eliminar_integrante(
    id_integrante: int,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        service._validar_scope_integrante(db, _user, id_integrante)
        if not service.eliminar_integrante(db, id_integrante):
            raise HTTPException(status_code=404, detail="Integrante no encontrado")
        return MessageResponse(message="Integrante eliminado correctamente", id=id_integrante)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise db_error(e)


# ============================================================================
#  UBICACIÓN FAMILIA
# ============================================================================

@router.get("/familias/{id_familia}/ubicaciones", tags=[TAG_HIJOS],
            response_model=DataListResponse[UbicacionFamiliaResponse],
            summary="Ubicaciones de una familia (hijos)",
            description="Coordenadas GPS y tipo de albergue de la familia. Paginada; `todos=true` devuelve todas.")
def listar_ubicaciones_familia(
    id_familia: int,
    id_departamento: int | None = Query(None, description="Filtrar por departamento"),
    id_provincia: int | None = Query(None, description="Filtrar por provincia"),
    id_municipio: int | None = Query(None, description="Filtrar por municipio"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    todos: bool = Query(False, description="Devolver todas las ubicaciones sin paginar"),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    service._validar_scope_familia(db, _user, id_familia)
    geo_filtros = {
        "id_departamento": id_departamento,
        "id_provincia": id_provincia,
        "id_municipio": id_municipio,
    }
    data, total = service.list_ubicaciones_paginado(db, id_familia, geo_filtros=geo_filtros, skip=skip, limit=limit, todos=todos)
    return SuccessResponse(message="Ubicaciones listadas correctamente", data=data, total=total)


@router.get("/ubicaciones/{id_ubicacion}", tags=[TAG_HIJOS],
            response_model=DataItemResponse[UbicacionFamiliaResponse],
            summary="Ubicación (hijo)",
            description="Obtiene una ubicación específica de una familia.")
def obtener_ubicacion(
    id_ubicacion: int,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    service._validar_scope_ubicacion(db, _user, id_ubicacion)
    result = service.get_ubicacion(db, id_ubicacion)
    if not result:
        raise HTTPException(status_code=404, detail="Ubicación no encontrada")
    return SuccessResponse(message="Ubicación obtenida correctamente", data=result)


@router.post("/familias/{id_familia}/ubicaciones", tags=[TAG_HIJOS], status_code=201,
             response_model=DataItemResponse[UbicacionFamiliaResponse],
             dependencies=[Depends(require_rol(*ROLES_ESCRITURA))],
             summary="Crear ubicación (hijo)",
             description="Registra las coordenadas GPS y tipo de albergue de la familia. "
                         "Si `id_ubicacion_off` ya existe, actualiza (UPSERT idempotente).")
def crear_ubicacion(
    id_familia: int,
    data: UbicacionFamiliaCreate,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        service._validar_scope_familia(db, _user, id_familia)
        payload = data.model_dump()
        payload["id_familia"] = id_familia
        result = service.crear_ubicacion(db, payload)
        return SuccessResponse(message="Ubicación creada correctamente", data=result)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise db_error(e)


@router.put("/ubicaciones/{id_ubicacion}", tags=[TAG_HIJOS],
            response_model=DataItemResponse[UbicacionFamiliaResponse],
            dependencies=[Depends(require_rol(*ROLES_ESCRITURA))],
            summary="Actualizar ubicación (hijo)",
            description="Actualiza las coordenadas GPS y tipo de albergue de una familia.")
def actualizar_ubicacion(
    id_ubicacion: int,
    data: UbicacionFamiliaUpdate,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        service._validar_scope_ubicacion(db, _user, id_ubicacion)
        result = service.actualizar_ubicacion(db, id_ubicacion, data.model_dump())
        if not result:
            raise HTTPException(status_code=404, detail="Ubicación no encontrada")
        return SuccessResponse(message="Ubicación actualizada correctamente", data=result)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise db_error(e)


@router.delete("/ubicaciones/{id_ubicacion}", tags=[TAG_HIJOS],
               response_model=MessageResponse,
               dependencies=[Depends(require_rol(*ROLES_ESCRITURA))],
               summary="Eliminar ubicación (hijo)",
               description="Desvincula la ubicación de la familia y la elimina.")
def eliminar_ubicacion(
    id_ubicacion: int,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        service._validar_scope_ubicacion(db, _user, id_ubicacion)
        if not service.eliminar_ubicacion(db, id_ubicacion):
            raise HTTPException(status_code=404, detail="Ubicación no encontrada")
        return MessageResponse(message="Ubicación eliminada correctamente", id=id_ubicacion)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise db_error(e)


# ============================================================================
#  SYNC OFFLINE (batch)
# ============================================================================

@router.post("/sync", tags=[TAG_SYNC], responses={200: {"model": SuccessResponse}},
             dependencies=[Depends(require_rol(*ROLES_ESCRITURA))],
             summary="Sincronizar empadronamiento (batch offline-first)",
             description="Push de un lote de formularios/familias/integrantes/ubicaciones.\n\n"
                         "- El **formulario** se identifica por `id_edan_localidad` (UNIQUE).\n"
                         "- **Familia/Integrante/Ubicación** se identifican por su `*_off`.\n"
                         "- Los vínculos offline (`id_familia_off`) resuelven los `id` del servidor.\n"
                         "- El lote nunca falla completo: los errores van en `errores[]`.\n"
                         "- Devuelve los mapeos `off → server` para que el dispositivo reenlace.")
def sync_empadronamiento(
    data: EmpadronamientoSyncIn,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    payload = data.model_dump()
    result = service.sync_empadronamiento(db, payload, _user["id_usuario"])
    return SuccessResponse(message="Empadronamiento sincronizado correctamente", data=result)

@router.get("/personas/buscar", tags=["RIDA > Búsqueda"],
            response_model=DataListResponse[dict],
            summary="Búsqueda potente de personas (integrantes)",
            description="Busca personas por múltiples criterios:\n"
                        "- **busqueda**: texto libre (nombre, apellido, documento)\n"
                        "- **nombre**: nombre específico\n"
                        "- **apellido**: apellido específico\n"
                        "- **numero_documento**: carnet o certificado\n"
                        "- **fecha_nacimiento**: fecha exacta (YYYY-MM-DD)\n"
                        "- **tipo_documento**: CARNET o CERTIFICADO\n"
                        "- **sexo**: M o F\n"
                        "- **id_departamento/provincia/municipio**: ubicación\n"
                        "- **es_jefe**: True/False\n"
                        "\nRetorna: id, nombre, apellido, fecha_nacimiento, tipo_documento, "
                        "numero_documento, sexo, localidad, municipio, departamento, familia.")
def buscar_personas(
    busqueda: str | None = Query(None, description="Búsqueda libre (nombre, apellido, documento)"),
    nombre: str | None = Query(None, description="Filtrar por nombre"),
    apellido: str | None = Query(None, description="Filtrar por apellido"),
    numero_documento: str | None = Query(None, description="Número de documento exacto"),
    fecha_nacimiento: str | None = Query(None, description="Fecha de nacimiento (YYYY-MM-DD)"),
    tipo_documento: str | None = Query(None, description="CARNET o CERTIFICADO"),
    sexo: str | None = Query(None, description="M o F"),
    id_departamento: int | None = Query(None, description="Filtrar por departamento"),
    id_provincia: int | None = Query(None, description="Filtrar por provincia"),
    id_municipio: int | None = Query(None, description="Filtrar por municipio"),
    id_parentesco: int | None = Query(None, description="Filtrar por parentesco"),
    es_jefe: bool | None = Query(None, description="Filtrar por jefe de familia"),
    skip: int = Query(0, ge=0, description="Offset para paginación"),
    limit: int = Query(50, ge=1, le=200, description="Límite de resultados"),
    todos: bool = Query(False, description="Devolver todos sin paginar"),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    filters = {k: v for k, v in {
        "busqueda": busqueda, "nombre": nombre, "apellido": apellido,
        "numero_documento": numero_documento, "fecha_nacimiento": fecha_nacimiento,
        "tipo_documento": tipo_documento, "sexo": sexo,
        "id_departamento": id_departamento, "id_provincia": id_provincia,
        "id_municipio": id_municipio, "id_parentesco": id_parentesco,
        "es_jefe": es_jefe,
    }.items() if v is not None}
    
    try:
        data, total = service.buscar_personas(db, filters, skip=skip, limit=limit, todos=todos)
        return SuccessResponse(
            message="Búsqueda completada correctamente",
            data=data, total=total
        )
    except Exception as e:
        raise db_error(e)
