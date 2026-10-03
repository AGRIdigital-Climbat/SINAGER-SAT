from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ...database import get_db
from ...dependencies import get_current_user
from ...response import SuccessResponse, MessageResponse, DataListResponse, DataItemResponse
from ...auth.permisos import module_permiso
from ...edan.utils import require_rol, db_error
from . import service
from .schemas import (
    CatCategoriaAyudaResponse, CatCategoriaAyudaCreate, CatCategoriaAyudaUpdate, CatCategoriaAyudaDetailResponse,
    CatArticuloResponse, CatArticuloCreate, CatArticuloUpdate,
    NecesidadCreate, NecesidadUpdate, NecesidadResponse,
    SyncNecesidadesIn,
)

router = APIRouter(
    prefix="/rida/necesidades",
    dependencies=[Depends(module_permiso("RIDA"))],
)

TAG_EMPADRONAMIENTO = "RIDA > Empadronamiento"
TAG_HIJOS = "RIDA > Hijos"
TAG_SYNC = "RIDA > Sync"

ROLES_ESCRITURA = (1, 2, 6, 7)


# ============================================================================
#  CATÁLOGOS - CATEGORÍAS (CRUD)
# ============================================================================

@router.get("/cat-categorias", tags=[TAG_EMPADRONAMIENTO], response_model=DataListResponse[CatCategoriaAyudaResponse],
            summary="Categorías de ayuda humanitaria",
            description="Catálogo de categorías de ayuda humanitaria. Sin paginación (trae todas).")
def listar_categorias(
    solo_activos: bool = Query(True),
    db: Session = Depends(get_db),
):
    data, total = service.listar_categorias(db, solo_activos, todos=True)
    return SuccessResponse(message="Categorías listadas correctamente", data=data, total=total)


@router.get("/cat-categorias/{id_categoria}", tags=[TAG_EMPADRONAMIENTO], response_model=DataItemResponse[CatCategoriaAyudaDetailResponse],
            summary="Categoría con artículos",
            description="Detalle de categoría incluyendo sus artículos.")
def obtener_categoria(
    id_categoria: int,
    db: Session = Depends(get_db),
):
    result = service.get_categoria_con_articulos(db, id_categoria)
    if not result:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    return SuccessResponse(message="Categoría obtenida correctamente", data=result)


@router.post("/cat-categorias", tags=[TAG_EMPADRONAMIENTO], status_code=201,
             response_model=DataItemResponse[CatCategoriaAyudaResponse],
             dependencies=[Depends(require_rol(*ROLES_ESCRITURA))],
             summary="Crear categoría",
             description="Crea una nueva categoría de ayuda humanitaria.")
def crear_categoria(
    data: CatCategoriaAyudaCreate,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        result = service.crear_categoria(db, data.model_dump())
        return SuccessResponse(message="Categoría creada correctamente", data=result)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise db_error(e)


@router.put("/cat-categorias/{id_categoria}", tags=[TAG_EMPADRONAMIENTO],
            response_model=DataItemResponse[CatCategoriaAyudaResponse],
            dependencies=[Depends(require_rol(*ROLES_ESCRITURA))],
            summary="Actualizar categoría",
            description="Actualiza los datos de una categoría existente.")
def actualizar_categoria(
    id_categoria: int,
    data: CatCategoriaAyudaUpdate,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        result = service.actualizar_categoria(db, id_categoria, data.model_dump())
        if not result:
            raise HTTPException(status_code=404, detail="Categoría no encontrada")
        return SuccessResponse(message="Categoría actualizada correctamente", data=result)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise db_error(e)


@router.delete("/cat-categorias/{id_categoria}", tags=[TAG_EMPADRONAMIENTO],
               response_model=MessageResponse,
               dependencies=[Depends(require_rol(*ROLES_ESCRITURA))],
               summary="Eliminar categoría",
               description="Elimina una categoría de ayuda humanitaria existente.")
def eliminar_categoria(
    id_categoria: int,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        if not service.eliminar_categoria(db, id_categoria):
            raise HTTPException(status_code=404, detail="Categoría no encontrada")
        return MessageResponse(message="Categoría eliminada correctamente", id=id_categoria)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise db_error(e)


# ============================================================================
#  CATÁLOGOS - ARTÍCULOS (CRUD)
# ============================================================================

@router.get("/cat-articulos", tags=[TAG_EMPADRONAMIENTO], response_model=DataListResponse[CatArticuloResponse],
            summary="Artículos de ayuda humanitaria",
            description="Catálogo de artículos con filtros. Sin paginación (trae todos).")
def listar_articulos(
    id_categoria_ayuda: int | None = Query(None),
    activo: bool | None = Query(None),
    q: str | None = Query(None, description="Búsqueda por nombre"),
    db: Session = Depends(get_db),
):
    filters = {k: v for k, v in {"id_categoria_ayuda": id_categoria_ayuda, "activo": activo, "q": q}.items() if v is not None}
    data, total = service.listar_articulos(db, filters, todos=True)
    return SuccessResponse(message="Artículos listados correctamente", data=data, total=total)


@router.get("/cat-articulos/{id_articulo}", tags=[TAG_EMPADRONAMIENTO], response_model=DataItemResponse[CatArticuloResponse],
            summary="Artículo",
            description="Obtiene un artículo específico de ayuda humanitaria.",
            )
def obtener_articulo(
    id_articulo: int,
    db: Session = Depends(get_db),
):
    result = service.get_articulo(db, id_articulo)
    if not result:
        raise HTTPException(status_code=404, detail="Artículo no encontrado")
    return SuccessResponse(message="Artículo obtenido correctamente", data=result)


@router.post("/cat-articulos", tags=[TAG_EMPADRONAMIENTO], status_code=201,
             response_model=DataItemResponse[CatArticuloResponse],
             dependencies=[Depends(require_rol(*ROLES_ESCRITURA))],
             summary="Crear artículo",
             description="Operación de API.",
             )
def crear_articulo(
    data: CatArticuloCreate,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        result = service.crear_articulo(db, data.model_dump())
        return SuccessResponse(message="Artículo creado correctamente", data=result)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise db_error(e)


@router.put("/cat-articulos/{id_articulo}", tags=[TAG_EMPADRONAMIENTO],
            response_model=DataItemResponse[CatArticuloResponse],
            dependencies=[Depends(require_rol(*ROLES_ESCRITURA))],
            summary="Actualizar artículo",
            description="Operación de API.",
             )
def actualizar_articulo(
    id_articulo: int,
    data: CatArticuloUpdate,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        result = service.actualizar_articulo(db, id_articulo, data.model_dump())
        if not result:
            raise HTTPException(status_code=404, detail="Artículo no encontrado")
        return SuccessResponse(message="Artículo actualizado correctamente", data=result)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise db_error(e)


@router.delete("/cat-articulos/{id_articulo}", tags=[TAG_EMPADRONAMIENTO],
               response_model=MessageResponse,
               dependencies=[Depends(require_rol(*ROLES_ESCRITURA))],
               summary="Eliminar artículo",
               description="Operación de API.",
             )
def eliminar_articulo(
    id_articulo: int,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        if not service.eliminar_articulo(db, id_articulo):
            raise HTTPException(status_code=404, detail="Artículo no encontrado")
        return MessageResponse(message="Artículo eliminado correctamente", id=id_articulo)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise db_error(e)


# ============================================================================
#  NECESIDADES (CRUD)
# ============================================================================

@router.get("/formularios/{id_formulario}/necesidades", tags=[TAG_HIJOS],
            response_model=DataListResponse[NecesidadResponse],
            summary="Necesidades de un formulario (hijos)",
            description="Necesidades del formulario. Paginada; `todos=true` devuelve todas.")
def listar_necesidades_formulario(
    id_formulario: int,
    id_departamento: int | None = Query(None, description="Filtrar por departamento"),
    id_provincia: int | None = Query(None, description="Filtrar por provincia"),
    id_municipio: int | None = Query(None, description="Filtrar por municipio"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    todos: bool = Query(False, description="Devolver todas las necesidades sin paginar"),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    filters = {
        "id_formulario": id_formulario,
        "id_departamento": id_departamento,
        "id_provincia": id_provincia,
        "id_municipio": id_municipio,
    }
    data, total = service.listar_necesidades(db, filters, skip=skip, limit=limit, todos=todos)
    return SuccessResponse(message="Necesidades listadas correctamente", data=data, total=total)


@router.get("/familias/{id_familia}/necesidades", tags=[TAG_HIJOS],
            response_model=DataListResponse[NecesidadResponse],
            summary="Necesidades de una familia (hijos)",
            description="Necesidades de la familia. Paginada; `todos=true` devuelve todas.")
def listar_necesidades_familia(
    id_familia: int,
    id_departamento: int | None = Query(None, description="Filtrar por departamento"),
    id_provincia: int | None = Query(None, description="Filtrar por provincia"),
    id_municipio: int | None = Query(None, description="Filtrar por municipio"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    todos: bool = Query(False, description="Devolver todas las necesidades sin paginar"),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    filters = {
        "id_familia": id_familia,
        "id_departamento": id_departamento,
        "id_provincia": id_provincia,
        "id_municipio": id_municipio,
    }
    data, total = service.listar_necesidades(db, filters, skip=skip, limit=limit, todos=todos)
    return SuccessResponse(message="Necesidades listadas correctamente", data=data, total=total)


@router.get("/necesidades/{id_necesidad}", tags=[TAG_HIJOS],
            response_model=DataItemResponse[NecesidadResponse],
            summary="Necesidad (hijo)",
            description="Operación de API.",
             )
def obtener_necesidad(
    id_necesidad: int,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    result = service.get_necesidad(db, id_necesidad)
    if not result:
        raise HTTPException(status_code=404, detail="Necesidad no encontrada")
    return SuccessResponse(message="Necesidad obtenida correctamente", data=result)


@router.post("/formularios/{id_formulario}/necesidades", tags=[TAG_HIJOS], status_code=201,
             response_model=DataItemResponse[NecesidadResponse],
             dependencies=[Depends(require_rol(*ROLES_ESCRITURA))],
             summary="Crear necesidad en formulario (hijo)",
             description="Operación de API.",
             )
def crear_necesidad_formulario(
    id_formulario: int,
    data: NecesidadCreate,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        payload = data.model_dump()
        payload["id_formulario"] = id_formulario
        result = service.crear_necesidad(db, payload, _user.get("id_usuario"))
        return SuccessResponse(message="Necesidad creada correctamente", data=result)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise db_error(e)


@router.post("/familias/{id_familia}/necesidades", tags=[TAG_HIJOS], status_code=201,
             response_model=DataItemResponse[NecesidadResponse],
             dependencies=[Depends(require_rol(*ROLES_ESCRITURA))],
             summary="Crear necesidad en familia (hijo)",
             description="Operación de API.",
             )
def crear_necesidad_familia(
    id_familia: int,
    data: NecesidadCreate,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        payload = data.model_dump()
        payload["id_familia"] = id_familia
        result = service.crear_necesidad(db, payload, _user.get("id_usuario"))
        return SuccessResponse(message="Necesidad creada correctamente", data=result)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise db_error(e)


@router.put("/necesidades/{id_necesidad}", tags=[TAG_HIJOS],
            response_model=DataItemResponse[NecesidadResponse],
            dependencies=[Depends(require_rol(*ROLES_ESCRITURA))],
            summary="Actualizar necesidad (hijo)",
            description="Operación de API.",
             )
def actualizar_necesidad(
    id_necesidad: int,
    data: NecesidadUpdate,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        result = service.actualizar_necesidad(db, id_necesidad, data.model_dump())
        if not result:
            raise HTTPException(status_code=404, detail="Necesidad no encontrada")
        return SuccessResponse(message="Necesidad actualizada correctamente", data=result)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise db_error(e)


@router.delete("/necesidades/{id_necesidad}", tags=[TAG_HIJOS],
               response_model=MessageResponse,
               dependencies=[Depends(require_rol(*ROLES_ESCRITURA))],
               summary="Eliminar necesidad (hijo)",
               description="Operación de API.",
             )
def eliminar_necesidad(
    id_necesidad: int,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        if not service.eliminar_necesidad(db, id_necesidad):
            raise HTTPException(status_code=404, detail="Necesidad no encontrada")
        return MessageResponse(message="Necesidad eliminada correctamente", id=id_necesidad)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise db_error(e)


# ============================================================================
#  SYNC OFFLINE
# ============================================================================

@router.post("/sync", tags=[TAG_EMPADRONAMIENTO],
             response_model=DataListResponse,
             dependencies=[Depends(require_rol(*ROLES_ESCRITURA))],
             summary="Sincronizar necesidades (batch offline)",
             description="Recibe lote de necesidades offline. Resuelve vínculos por *_off y devuelve mapeos.")
def sincronizar_necesidades(
    batch: SyncNecesidadesIn,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        resultado = service.sync_necesidades(db, batch.necesidades, _user.get("id_usuario"))
        return SuccessResponse(
            message="Sincronización completada",
            data=[resultado],
            total=len(resultado["necesidades"])
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise db_error(e)
