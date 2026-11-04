from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from ...response import SuccessResponse
from ..db.queries import (
    listar_grupos,
    obtener_grupo,
    crear_grupo,
    actualizar_grupo,
    eliminar_grupo,
    listar_grupos_solo_ids,
)
from ..security import _validar_token_api

router = APIRouter(prefix="/grupos", tags=["MotorIA > Grupos"])


class GrupoCreate(BaseModel):
    nombre: str = Field(..., description="Nombre del grupo. Debe ser unico (no distingue mayusculas).")
    descripcion: Optional[str] = Field(None, description="Descripcion opcional del grupo.")
    documento_ids: List[int] = Field(
        default_factory=list,
        description="Ids de documentos (de /documentos) que forman el grupo. Los ids inexistentes se ignoran.",
    )


class GrupoUpdate(BaseModel):
    nombre: Optional[str] = Field(None, description="Nuevo nombre del grupo.")
    descripcion: Optional[str] = Field(None, description="Nueva descripcion.")
    documento_ids: Optional[List[int]] = Field(
        None,
        description="Nueva lista de documentos (reemplaza la actual). Lista vacia deja el grupo sin documentos.",
    )


@router.get("")
def grupos(
    limit: int = Query(100, ge=1, le=500, description="Cantidad a devolver (los más recientes primero)"),
    skip: int = Query(0, ge=0, description="Saltar registros (paginación, sólo con limit)"),
    todos: bool = Query(False, description="Devolver todos los grupos sin paginar"),
    q: Optional[str] = Query(None, description="Filtro por nombre o descripción."),
):
    """Lista los grupos con su numero de documentos y los ids incluidos."""
    grupos, total = listar_grupos(q=q, limit=limit, skip=skip, todos=todos)
    return SuccessResponse(message="Grupos listados", data=grupos, total=total)


@router.get("/{grupo_id}")
def ver_grupo(grupo_id: int):
    """Detalle de un grupo con sus `documento_ids`."""
    grupo = obtener_grupo(grupo_id)
    if not grupo:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")
    return grupo


@router.get("/{grupo_id}/documentos")
def documentos_del_grupo(grupo_id: int):
    """Ids de documentos que pertenecen al grupo (uso directo en /chat)."""
    grupo = obtener_grupo(grupo_id)
    if not grupo:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")
    return {"grupo_id": grupo_id, "documento_ids": listar_grupos_solo_ids(grupo_id)}


@router.post("", status_code=201, dependencies=[Depends(_validar_token_api)])
def crear(req: GrupoCreate):
    """Crea un grupo de documentos. Endpoint publico (sin token)."""
    nombre = req.nombre.strip()
    if not nombre:
        raise HTTPException(status_code=400, detail="El nombre no puede estar vacio")
    try:
        grupo_id = crear_grupo(nombre, req.descripcion, req.documento_ids)
    except ValueError:
        raise HTTPException(status_code=409, detail=f"Ya existe un grupo con el nombre '{nombre}'")
    except Exception as e:
        if "grupo_documentos_nombre_key" in str(e):
            raise HTTPException(status_code=409, detail=f"Ya existe un grupo con el nombre '{nombre}'")
        raise
    return {"mensaje": "Grupo creado correctamente", "grupo_id": grupo_id}


@router.put("/{grupo_id}", dependencies=[Depends(_validar_token_api)])
def editar(grupo_id: int, req: GrupoUpdate):
    """Actualiza nombre, descripcion y/o documentos de un grupo."""
    grupo = obtener_grupo(grupo_id)
    if not grupo:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")

    if req.nombre is not None and not req.nombre.strip():
        raise HTTPException(status_code=400, detail="El nombre no puede estar vacio")

    nombre = req.nombre.strip() if req.nombre is not None else grupo["nombre"]
    descripcion = req.descripcion if req.descripcion is not None else grupo["descripcion"]
    documento_ids = req.documento_ids if req.documento_ids is not None else grupo["documento_ids"]

    try:
        actualizar_grupo(grupo_id, nombre, descripcion, documento_ids)
    except ValueError:
        raise HTTPException(status_code=409, detail=f"Ya existe un grupo con el nombre '{nombre}'")
    except Exception as e:
        if "grupo_documentos_nombre_key" in str(e):
            raise HTTPException(status_code=409, detail=f"Ya existe un grupo con el nombre '{nombre}'")
        raise
    return {"mensaje": "Grupo actualizado correctamente", "grupo_id": grupo_id}


@router.delete("/{grupo_id}", dependencies=[Depends(_validar_token_api)])
def borrar(grupo_id: int):
    """Elimina un grupo (no elimina los documentos, solo la agrupacion)."""
    grupo = obtener_grupo(grupo_id)
    if not grupo:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")
    eliminar_grupo(grupo_id)
    return {"mensaje": "Grupo eliminado correctamente"}
