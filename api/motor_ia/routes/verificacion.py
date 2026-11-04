from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from ..core.verificacion import verificar_sistema
from ..security import _validar_token_api

router = APIRouter(prefix="/verificacion", tags=["MotorIA > Verificación"])


class EvalRequest(BaseModel):
    num_preguntas: int = Field(20, ge=5, le=40, description="Cantidad de consultas de prueba por documento/seccion.")
    probar_respuestas: bool = Field(True, description="Si es true, el LLM genera respuestas reales y se verifica que citen sus fuentes (lento en CPU).")
    num_respuestas: int = Field(4, ge=0, le=10, description="Cuantas respuestas reales generar si probar_respuestas=true.")


@router.post("/general", dependencies=[Depends(_validar_token_api)])
def evaluar_general(req: EvalRequest):
    """Evaluacion general de la calidad de la busqueda en toda la plataforma.

    Genera consultas al azar de todos los documentos y mide en que posicion
    aparece el fragmento correcto (`precision_at_1/3/5`), desglosado por
    intencion y tipo de norma, con `indice_general` (0-1). Con
    `probar_respuestas: true` ademas valida respuestas reales del LLM.
    """
    num_preguntas = max(5, min(40, req.num_preguntas))
    num_llm = req.num_respuestas if req.probar_respuestas else 0
    return verificar_sistema(
        num_preguntas=num_preguntas,
        num_respuestas_llm=num_llm,
    )
