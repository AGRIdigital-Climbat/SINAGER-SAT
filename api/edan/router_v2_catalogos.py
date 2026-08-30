from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..response import SuccessResponse, MessageResponse
from . import service
from .schemas import (
    TipoEventoCreate, TipoEventoUpdate,
    EstadoEdanCreate, EstadoEdanUpdate,
    TipoLocalidadCreate, TipoLocalidadUpdate,
    EdanLocalidadEstadoCreate, EdanLocalidadEstadoUpdate,
    GrupoVulnerableCreate, GrupoVulnerableUpdate,
    GrupoEtarioCreate, GrupoEtarioUpdate,
)
from ..auth.permisos import module_permiso

router = APIRouter(prefix="/edan", dependencies=[Depends(module_permiso("EDAN"))])

TAG = "EDAN > Catálogos"


def _db_error(exc: Exception) -> HTTPException:
    try:
        code = getattr(exc.orig, "sqlstate", None) or getattr(exc.orig, "pgcode", None)
    except AttributeError:
        code = None
    if code == "23503":
        return HTTPException(status_code=400, detail="El registro referenciado no existe (violación de clave foránea)")
    if code == "23505":
        return HTTPException(status_code=400, detail="Ya existe un registro con el mismo valor (violación de unicidad)")
    return HTTPException(status_code=400, detail="Error al procesar la solicitud")


def _catalog_crud_routes(parent, path, crud, Create, Update, label, tag):
    get_all, get_one, create, update, delete = crud
    s = path.replace("-", "_")

    @parent.get(f"/{path}", name=f"listar_{s}", tags=[tag], responses={200: {"model": SuccessResponse}})
    def _list(db: Session = Depends(get_db)):
        data = get_all(db)
        return SuccessResponse(message=f"{label} listados correctamente", data=data, total=len(data))

    @parent.get(f"/{path}/{{id}}", name=f"obtener_{s}", tags=[tag], responses={200: {"model": SuccessResponse}})
    def _get(id: int, db: Session = Depends(get_db)):
        result = get_one(db, id)
        if not result:
            raise HTTPException(status_code=404, detail=f"{label} no encontrado")
        return SuccessResponse(message=f"{label} obtenido correctamente", data=result)

    @parent.post(f"/{path}", name=f"crear_{s}", status_code=201, tags=[tag], responses={201: {"model": SuccessResponse}})
    def _create(data: Create, db: Session = Depends(get_db)):
        try:
            id = create(db, data.model_dump())
            result = get_one(db, id)
            return SuccessResponse(message=f"{label} creado correctamente", data=result)
        except Exception as e:
            raise _db_error(e)

    @parent.put(f"/{path}/{{id}}", name=f"actualizar_{s}", tags=[tag], responses={200: {"model": SuccessResponse}})
    def _update(id: int, data: Update, db: Session = Depends(get_db)):
        result = update(db, id, data.model_dump())
        if not result:
            raise HTTPException(status_code=404, detail=f"{label} no encontrado")
        return SuccessResponse(message=f"{label} actualizado correctamente", data=result)

    @parent.delete(f"/{path}/{{id}}", name=f"eliminar_{s}", tags=[tag], responses={200: {"model": MessageResponse}})
    def _delete(id: int, db: Session = Depends(get_db)):
        if not delete(db, id):
            raise HTTPException(status_code=404, detail=f"{label} no encontrado")
        return MessageResponse(message=f"{label} eliminado correctamente")


_catalog_crud_routes(router, "tipo-evento", service.tipo_evento_crud,
                     TipoEventoCreate, TipoEventoUpdate, "Tipo de evento", TAG)

_catalog_crud_routes(router, "estados", service.estado_edan_crud,
                     EstadoEdanCreate, EstadoEdanUpdate, "Estado EDAN", TAG)

_catalog_crud_routes(router, "tipo-localidad", service.tipo_localidad_crud,
                     TipoLocalidadCreate, TipoLocalidadUpdate, "Tipo de localidad", TAG)

_catalog_crud_routes(router, "localidades-estado", service.edan_localidades_estado_crud,
                     EdanLocalidadEstadoCreate, EdanLocalidadEstadoUpdate, "Estado localidad", TAG)

_catalog_crud_routes(router, "grupo-vulnerable", service.grupo_vulnerable_crud,
                     GrupoVulnerableCreate, GrupoVulnerableUpdate, "Grupo vulnerable", TAG)

_catalog_crud_routes(router, "grupo-etario", service.grupo_etario_crud,
                     GrupoEtarioCreate, GrupoEtarioUpdate, "Grupo etario", TAG)
