from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from ..core.rag import busqueda_hibrida

router = APIRouter(prefix="/busqueda", tags=["MotorIA > Búsqueda"])


class BusquedaRequest(BaseModel):
    pregunta: str = Field(..., description="Consulta de busqueda. Ej: 'unidad de gestion de riesgos'.")
    limite: int = Field(15, ge=1, le=100, description="Maximo de fragmentos a devolver (1-100).")
    umbral: float = Field(0.30, ge=0, le=1, description="Similitud minima (0-1) para incluir un fragmento.")
    tipo_id: Optional[int] = Field(None, description="Filtrar por tipo de norma (id de /tipos-documento).")
    documento_id: Optional[int] = Field(None, description="Filtrar por documento especifico (id de /documentos).")
    documento_ids: Optional[List[int]] = Field(None, description="Filtrar por varios documentos (ids de /documentos). Se unen con documento_id (deduplicados).")


def _normalizar_tipo_id(tipo_id):
    if tipo_id in (None, 0):
        return None
    return tipo_id


def _buscar(pregunta, limite, umbral, tipo_id, documento_id=None, documento_ids=None):
    pregunta = (pregunta or "").strip()
    if not pregunta:
        raise HTTPException(status_code=400, detail="La consulta no puede estar vacia")
    if limite < 1 or limite > 100:
        raise HTTPException(status_code=400, detail="El limite debe estar entre 1 y 100")
    if umbral < 0 or umbral > 1:
        raise HTTPException(status_code=400, detail="El umbral debe estar entre 0 y 1")

    resultados, intencion = busqueda_hibrida(
        pregunta=pregunta,
        limite=limite,
        umbral=umbral,
        tipo_id=_normalizar_tipo_id(tipo_id),
        documento_id=documento_id,
        documento_ids=documento_ids,
    )

    return {
        "consulta": pregunta,
        "intencion": intencion,
        "total_resultados": len(resultados),
        "resultados": resultados,
    }


@router.get("")
def buscar_get(
    q: str = Query(..., description="Texto a buscar"),
    limite: int = Query(15, ge=1, le=100, description="Maximo de resultados (1-100)."),
    umbral: float = Query(0.30, ge=0, le=1, description="Similitud minima (0-1)."),
    tipo_id: Optional[int] = Query(None, description="Filtrar por tipo de norma."),
    documento_id: Optional[int] = Query(None, description="Filtrar por documento especifico."),
    documento_ids: Optional[List[int]] = Query(None, description="Filtrar por varios documentos (repetir el parametro o usar comas: ?documento_ids=15&documento_ids=17)."),
):
    """Busqueda hibrida por GET (parametros en query string)."""
    return _buscar(q, limite, umbral, tipo_id, documento_id=documento_id, documento_ids=documento_ids)


@router.post("")
def buscar(req: BusquedaRequest):
    """Busqueda hibrida por POST (sin generar texto, solo fragmentos).

    Combina similitud semantica (embeddings), coincidencia textual e intencion
    de la consulta. Devuelve `intencion`, `total_resultados` y los fragmentos
    con su `documento_id`, `titulo`, `contenido`, `numeral` y `similitud`.
    """
    return _buscar(req.pregunta, req.limite, req.umbral, req.tipo_id, documento_id=req.documento_id, documento_ids=req.documento_ids)
