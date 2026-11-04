from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from typing import Optional
from ...response import SuccessResponse
from ..db.queries import (
    listar_tipos_documento,
    listar_tipos_documento_todos,
    obtener_tipo_documento,
    crear_tipo_documento,
    actualizar_tipo_documento,
    eliminar_tipo_documento,
    contar_documentos_por_tipo,
)
from ..security import _validar_token_api

router = APIRouter(prefix="/tipos-documento", tags=["MotorIA > Tipos de documento"])


class TipoCreate(BaseModel):
    nombre: str = Field(..., description="Nombre del tipo de norma. Ej: 'Ley Nacional'.")
    prioridad: int = Field(..., description="Prioridad de la jerarquia: menor numero = mayor prioridad.")


class TipoUpdate(BaseModel):
    nombre: Optional[str] = Field(None, description="Nuevo nombre del tipo.")
    prioridad: Optional[int] = Field(None, description="Nueva prioridad de jerarquia.")
    activo: Optional[bool] = Field(None, description="Activar (true) o desactivar (false).")


@router.get("")
def tipos(todos: bool = Query(False, description="true = incluye tipos desactivados")):
    """Lista los tipos de norma (catálogo completo, sin paginación)."""
    if todos:
        tipos_documento = listar_tipos_documento_todos()
    else:
        tipos_documento = listar_tipos_documento()
    return SuccessResponse(message="Tipos listados", data=tipos_documento, total=len(tipos_documento))


@router.post("", dependencies=[Depends(_validar_token_api)])
def crear_tipo(req: TipoCreate):
    """Crea un nuevo tipo de norma."""
    if not req.nombre.strip():
        raise HTTPException(status_code=400, detail="El nombre no puede estar vacio")
    tipo_id = crear_tipo_documento(req.nombre.strip(), req.prioridad)
    return {"mensaje": "Tipo creado correctamente", "tipo_id": tipo_id}


@router.put("/{tipo_id}", dependencies=[Depends(_validar_token_api)])
def editar_tipo(tipo_id: int, req: TipoUpdate):
    """Edita nombre, prioridad o estado activo de un tipo."""
    tipo = obtener_tipo_documento(tipo_id)
    if not tipo:
        raise HTTPException(status_code=404, detail="Tipo no encontrado")

    if req.nombre is not None and not req.nombre.strip():
        raise HTTPException(status_code=400, detail="El nombre no puede estar vacio")

    nombre = req.nombre.strip() if req.nombre is not None else tipo["nombre"]
    prioridad = req.prioridad if req.prioridad is not None else tipo["prioridad"]
    activo = req.activo if req.activo is not None else tipo["activo"]

    actualizar_tipo_documento(tipo_id, nombre, prioridad, activo)
    return {"mensaje": "Tipo actualizado correctamente"}


@router.delete("/{tipo_id}", dependencies=[Depends(_validar_token_api)])
def borrar_tipo(tipo_id: int):
    """Elimina un tipo; si tiene documentos asociados se desactiva en su lugar."""
    tipo = obtener_tipo_documento(tipo_id)
    if not tipo:
        raise HTTPException(status_code=404, detail="Tipo no encontrado")

    documentos = contar_documentos_por_tipo(tipo_id)
    if documentos > 0:
        actualizar_tipo_documento(tipo_id, tipo["nombre"], tipo["prioridad"], False)
        return {
            "mensaje": "El tipo tiene documentos asociados, se desactivo en vez de eliminar",
            "desactivado": True,
        }

    eliminar_tipo_documento(tipo_id)
    return {"mensaje": "Tipo eliminado correctamente", "desactivado": False}
