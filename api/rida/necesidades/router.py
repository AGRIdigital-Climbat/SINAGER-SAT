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
    CatUnidadMedidaResponse, CatUnidadMedidaCreate, CatUnidadMedidaUpdate,
    CatArticuloResponse, CatArticuloCreate, CatArticuloUpdate,
    NecesidadCreate, NecesidadUpdate, NecesidadResponse,
    SyncNecesidadesIn,
    CatTipoRehabilitacionResponse, CatTipoRehabilitacionCreate, CatTipoRehabilitacionUpdate, CatTipoRehabilitacionDetailResponse,
    CatInsumoRehabilitacionResponse, CatInsumoRehabilitacionCreate, CatInsumoRehabilitacionUpdate,
    NecesidadRehabilitacionCreate,
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
#  CATÁLOGOS - UNIDADES DE MEDIDA (CRUD)
# ============================================================================

@router.get("/cat-unidades-medida", tags=[TAG_EMPADRONAMIENTO], response_model=DataListResponse[CatUnidadMedidaResponse],
            summary="Unidades de medida",
            description="Catálogo de unidades de medida de los artículos. Sin paginación (trae todas).")
def listar_unidades(
    solo_activos: bool = Query(True),
    db: Session = Depends(get_db),
):
    data, total = service.listar_unidades(db, solo_activos, todos=True)
    return SuccessResponse(message="Unidades de medida listadas correctamente", data=data, total=total)


@router.get("/cat-unidades-medida/{id_unidad}", tags=[TAG_EMPADRONAMIENTO], response_model=DataItemResponse[CatUnidadMedidaResponse],
            summary="Unidad de medida",
            description="Obtiene una unidad de medida específica.")
def obtener_unidad(
    id_unidad: int,
    db: Session = Depends(get_db),
):
    result = service.get_unidad(db, id_unidad)
    if not result:
        raise HTTPException(status_code=404, detail="Unidad de medida no encontrada")
    return SuccessResponse(message="Unidad de medida obtenida correctamente", data=result)


@router.post("/cat-unidades-medida", tags=[TAG_EMPADRONAMIENTO], status_code=201,
             response_model=DataItemResponse[CatUnidadMedidaResponse],
             dependencies=[Depends(require_rol(*ROLES_ESCRITURA))],
             summary="Crear unidad de medida",
             description="Crea una nueva unidad de medida (codigo se autoderiva del nombre si no se envía).")
def crear_unidad(
    data: CatUnidadMedidaCreate,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        result = service.crear_unidad(db, data.model_dump())
        return SuccessResponse(message="Unidad de medida creada correctamente", data=result)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise db_error(e)


@router.put("/cat-unidades-medida/{id_unidad}", tags=[TAG_EMPADRONAMIENTO],
            response_model=DataItemResponse[CatUnidadMedidaResponse],
            dependencies=[Depends(require_rol(*ROLES_ESCRITURA))],
            summary="Actualizar unidad de medida",
            description="Actualiza los datos de una unidad de medida existente (el cambio de codigo se propaga a los artículos).")
def actualizar_unidad(
    id_unidad: int,
    data: CatUnidadMedidaUpdate,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        result = service.actualizar_unidad(db, id_unidad, data.model_dump())
        if not result:
            raise HTTPException(status_code=404, detail="Unidad de medida no encontrada")
        return SuccessResponse(message="Unidad de medida actualizada correctamente", data=result)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise db_error(e)


@router.delete("/cat-unidades-medida/{id_unidad}", tags=[TAG_EMPADRONAMIENTO],
               response_model=MessageResponse,
               dependencies=[Depends(require_rol(*ROLES_ESCRITURA))],
               summary="Eliminar unidad de medida",
               description="Elimina una unidad de medida (409 si hay artículos que la referencian).")
def eliminar_unidad(
    id_unidad: int,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        unid = service.get_unidad(db, id_unidad)
        if not unid:
            raise HTTPException(status_code=404, detail="Unidad de medida no encontrada")
        if unid.get("n_articulos", 0) > 0:
            raise HTTPException(status_code=409,
                                detail="Unidad de medida en uso por artículos; no se puede eliminar")
        if not service.eliminar_unidad(db, id_unidad):
            raise HTTPException(status_code=404, detail="Unidad de medida no encontrada")
        return MessageResponse(message="Unidad de medida eliminada correctamente", id=id_unidad)
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
    fuente: str | None = Query(None, description="manual | motor"),
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
        "fuente": fuente,
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
    fuente: str | None = Query(None, description="manual | motor"),
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
        "fuente": fuente,
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
             description="Crea una necesidad que **debe pertenecer a una familia** (`id_familia` "
                         "obligatorio en el body; el formulario se deriva de ella vía "
                         "`familia.id_formulario`). Si el body incluye `id_formulario`, se valida "
                         "que la familia pertenezca a ese formulario. `id_formulario` en la ruta "
                         "sirve de referencia: la necesidad no guarda columna propia de formulario "
                         "(v2.47.0).",
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
             description="Crea una necesidad de la familia. La necesidad se vincula SOLO a la "
                         "familia (`rida.necesidad.id_familia`); el `id_formulario` de la "
                         "respuesta se deriva de `familia.id_formulario` (no es columna propia "
                         "desde v2.47.0). Devuelve también `id_edan_localidad`, `localidad_nombre` "
                         "e `id_tipo_localidad`/`tipo_localidad_nombre` para rastreo.",
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
        result = service.actualizar_necesidad(db, id_necesidad, data.model_dump(exclude_unset=True))
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


# ============================================================================
#  CATÁLOGOS - REHABILITACIÓN (NUEVO)
# ============================================================================

TAG_REHABILITACION = "RIDA > Rehabilitación"


@router.get("/cat-tipos-rehabilitacion", tags=[TAG_REHABILITACION], response_model=DataListResponse[CatTipoRehabilitacionResponse],
            summary="Tipos de rehabilitación",
            description="Catálogo de tipos de rehabilitación (defensivos, pecuario, sistemas de agua, vías/taludes, cubiertas).")
def listar_tipos_rehabilitacion(
    solo_activos: bool = Query(True),
    db: Session = Depends(get_db),
):
    data, total = service.listar_tipos_rehabilitacion(db, solo_activos, todos=True)
    return SuccessResponse(message="Tipos de rehabilitación listados correctamente", data=data, total=total)


@router.get("/cat-tipos-rehabilitacion/{id_tipo}", tags=[TAG_REHABILITACION], response_model=DataItemResponse[CatTipoRehabilitacionDetailResponse],
            summary="Tipo de rehabilitación con insumos",
            description="Detalle de tipo de rehabilitación incluyendo sus insumos/artículos.")
def obtener_tipo_rehabilitacion(
    id_tipo: int,
    db: Session = Depends(get_db),
):
    data = service.get_tipo_con_insumos(db, id_tipo)
    if not data:
        raise HTTPException(status_code=404, detail="Tipo de rehabilitación no encontrado")
    return SuccessResponse(message="Tipo de rehabilitación obtenido correctamente", data=data)


@router.post("/cat-tipos-rehabilitacion", tags=[TAG_REHABILITACION], status_code=201,
             response_model=DataItemResponse[CatTipoRehabilitacionResponse],
             summary="Crear tipo de rehabilitación",
             dependencies=[Depends(require_rol(*ROLES_ESCRITURA))])
def crear_tipo_rehabilitacion(
    body: CatTipoRehabilitacionCreate,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    from datetime import datetime
    data = body.model_dump()
    if not data.get("codigo"):
        data["codigo"] = f"TR-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    try:
        id_tipo = service.create_tipo_rehabilitacion(db, data)
        return SuccessResponse(message="Tipo de rehabilitación creado correctamente", data={"id_tipo_rehabilitacion": id_tipo})
    except Exception as e:
        db.rollback()
        raise db_error(e)


@router.put("/cat-tipos-rehabilitacion/{id_tipo}", tags=[TAG_REHABILITACION], response_model=DataItemResponse[CatTipoRehabilitacionResponse],
            summary="Actualizar tipo de rehabilitación",
            dependencies=[Depends(require_rol(*ROLES_ESCRITURA))])
def actualizar_tipo_rehabilitacion(
    id_tipo: int,
    body: CatTipoRehabilitacionUpdate,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    if not data:
        raise HTTPException(status_code=400, detail="No hay datos para actualizar")
    try:
        service.update_tipo_rehabilitacion(db, id_tipo, data)
        return SuccessResponse(message="Tipo de rehabilitación actualizado correctamente", data={"id_tipo_rehabilitacion": id_tipo})
    except Exception as e:
        db.rollback()
        raise db_error(e)


@router.delete("/cat-tipos-rehabilitacion/{id_tipo}", tags=[TAG_REHABILITACION], response_model=MessageResponse,
               summary="Eliminar tipo de rehabilitación (soft delete)",
               dependencies=[Depends(require_rol(*ROLES_ESCRITURA))])
def eliminar_tipo_rehabilitacion(
    id_tipo: int,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        service.delete_tipo_rehabilitacion(db, id_tipo, hard=False)
        return {"message": "Tipo de rehabilitación eliminado correctamente", "id": id_tipo}
    except Exception as e:
        db.rollback()
        raise db_error(e)


# ============================================================================
#  INSUMOS DE REHABILITACIÓN
# ============================================================================

@router.get("/cat-insumos-rehabilitacion", tags=[TAG_REHABILITACION], response_model=DataListResponse[CatInsumoRehabilitacionResponse],
            summary="Insumos de rehabilitación",
            description="Catálogo: lista SIEMPRE completa (sin paginación), igual que el resto de catálogos. "
                        "Filtros: id_tipo_rehabilitacion, activo.")
def listar_insumos_rehabilitacion(
    id_tipo_rehabilitacion: int | None = Query(None),
    activo: bool | None = Query(None),
    db: Session = Depends(get_db),
):
    filtros = {}
    if id_tipo_rehabilitacion:
        filtros["id_tipo_rehabilitacion"] = id_tipo_rehabilitacion
    if activo is not None:
        filtros["activo"] = activo
    data, total = service.listar_insumos_rehabilitacion(db, filtros, todos=True)
    return SuccessResponse(message="Insumos de rehabilitación listados correctamente", data=data, total=total)


@router.get("/cat-insumos-rehabilitacion/{id_insumo}", tags=[TAG_REHABILITACION], response_model=DataItemResponse[CatInsumoRehabilitacionResponse],
            summary="Insumo de rehabilitación",
            description="Detalle de un insumo de rehabilitación.")
def obtener_insumo_rehabilitacion(
    id_insumo: int,
    db: Session = Depends(get_db),
):
    data = service.get_insumo_rehabilitacion(db, id_insumo)
    if not data:
        raise HTTPException(status_code=404, detail="Insumo de rehabilitación no encontrado")
    return SuccessResponse(message="Insumo obtenido correctamente", data=data)


@router.post("/cat-insumos-rehabilitacion", tags=[TAG_REHABILITACION], status_code=201,
             response_model=DataItemResponse[CatInsumoRehabilitacionResponse],
             summary="Crear insumo de rehabilitación",
             dependencies=[Depends(require_rol(*ROLES_ESCRITURA))])
def crear_insumo_rehabilitacion(
    body: CatInsumoRehabilitacionCreate,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    from datetime import datetime
    data = body.model_dump()
    if not data.get("codigo"):
        data["codigo"] = f"INS-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    try:
        id_insumo = service.create_insumo_rehabilitacion(db, data)
        return SuccessResponse(message="Insumo de rehabilitación creado correctamente", data={"id_insumo": id_insumo})
    except Exception as e:
        db.rollback()
        raise db_error(e)


@router.put("/cat-insumos-rehabilitacion/{id_insumo}", tags=[TAG_REHABILITACION], response_model=DataItemResponse[CatInsumoRehabilitacionResponse],
            summary="Actualizar insumo de rehabilitación",
            dependencies=[Depends(require_rol(*ROLES_ESCRITURA))])
def actualizar_insumo_rehabilitacion(
    id_insumo: int,
    body: CatInsumoRehabilitacionUpdate,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    if not data:
        raise HTTPException(status_code=400, detail="No hay datos para actualizar")
    try:
        service.update_insumo_rehabilitacion(db, id_insumo, data)
        return SuccessResponse(message="Insumo actualizado correctamente", data={"id_insumo": id_insumo})
    except Exception as e:
        db.rollback()
        raise db_error(e)


@router.delete("/cat-insumos-rehabilitacion/{id_insumo}", tags=[TAG_REHABILITACION], response_model=MessageResponse,
               summary="Eliminar insumo de rehabilitación (soft delete)",
               dependencies=[Depends(require_rol(*ROLES_ESCRITURA))])
def eliminar_insumo_rehabilitacion(
    id_insumo: int,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        service.delete_insumo_rehabilitacion(db, id_insumo, hard=False)
        return {"message": "Insumo de rehabilitación eliminado correctamente", "id": id_insumo}
    except Exception as e:
        db.rollback()
        raise db_error(e)
