from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List
from ..core.rag import buscar_hibrido_inteligente, deduplicar_fuentes
from ..core.llm import generar_respuesta_stream, seleccionar_chunks_contexto, _guia_para, _limpiar_formato
from ..db.queries import iniciar_uso_llm, finalizar_uso_llm, eliminar_uso_llm, obtener_grupo
import json

router = APIRouter(prefix="/chat", tags=["MotorIA > Chat"])


class ChatRequest(BaseModel):
    pregunta: str = Field(..., description="Pregunta juridica. Ej: 'Que dice la Ley 602 sobre gestion de riesgos?'")
    limite: int = Field(15, description="Maximo de fuentes a citar en la respuesta.")
    umbral: float = Field(0.30, description="Similitud minima (0-1) para incluir un fragmento.")
    tipo_id: Optional[int] = Field(None, description="Filtrar por tipo de norma (id de /tipos-documento).")
    documento_id: Optional[int] = Field(None, description="Filtrar por documento especifico (id de /documentos).")
    documento_ids: Optional[List[int]] = Field(None, description="Filtrar por varios documentos (ids de /documentos). Se unen con documento_id (deduplicados).")
    grupo_id: Optional[int] = Field(
        None,
        description=(
            "Filtrar por un grupo de documentos (id de /grupos). Se combina con "
            "documento_id y documento_ids (todos deduplicados). Si el grupo no "
            "tiene documentos se responde con error 400."
        ),
    )
    termino: Optional[str] = Field(
        None,
        description=(
            "Solo se aplica cuando tambien se envia `grupo_id` (pensado para el "
            "formulario EDAN). Es el nombre de la seccion/pantalla actual; el "
            "buscador acota primero a los fragmentos de esa seccion dentro del "
            "grupo y dentro de ellos busca la `pregunta`. Si la seccion no se "
            "encuentra, cae a la busqueda normal del grupo (no falla)."
        ),
    )
    llm_externo: Optional[bool] = Field(
        None,
        description=(
            "Modelo de lenguaje a usar en esta peticion: "
            "true = modelo externo (OpenAI-compatible, ej. Groq), "
            "false = modelo local (Qwen2.5-3B), "
            "ausente (null) = usa el LLM_MODE de .env (default local)."
        ),
    )
    max_tokens: Optional[int] = Field(
        None,
        description=(
            "Tope MAXIMO de tokens de la respuesta de SALIDA (visible); no es "
            "una meta, el modelo responde mas corto de forma natural. Si el "
            "modelo razona, el margen interno para razonamiento se calibra "
            "automaticamente y no consume este limite. Ausente (null) usa "
            "LLM_MAX_TOKENS de .env (default 512). Ej: 100 para respuestas "
            "muy cortas."
        ),
    )


@router.post("")
def chat(req: ChatRequest):
    """Chat RAG con respuesta en streaming (Server-Sent Events).

    Realiza la busqueda hibrida (embeddings + texto + intencion) sobre los
    documentos indexados y genera una respuesta citando fuentes.

    Selecciona el modelo de lenguaje con el campo `llm_externo`:
      - `true`:  usa el LLM externo configurado en `.env` (LLM_API_BASE/KEY/MODEL).
      - `false`: usa el LLM local Qwen2.5-3B (modelos/qwen.gguf).
      - omision: usa `LLM_MODE` de `.env` (default `local`).

    Filtros de busqueda:
      - `tipo_id`: limita a un tipo de norma.
      - `documento_id`: limita a un documento especifico (requiere menos tokens
        de contexto y respuestas mas precisas sobre ese documento).
      - `documento_ids`: limita a varios documentos; se combina con
        `documento_id` (ambos se deduplican).
      - `grupo_id`: limita a los documentos de un grupo (ver `/grupos`);
        se combina con `documento_id`/`documento_ids`.
      - `termino`: nombre de seccion/pantalla (solo con `grupo_id`, pensado para
        el EDAN). Acota la busqueda a los fragmentos de esa seccion dentro del
        grupo y ahi busca la `pregunta`; si no la encuentra, busca normal.

    El cuerpo del endpoint activa la busqueda semantica por embeddings,
    coincidencia textual y deteccion de la intencion de la consulta; solo el
    paso de generacion de texto es el que cambia segun `llm_externo`.

    El campo opcional `max_tokens` limita la longitud maxima de la respuesta de
    salida (visible; no es una meta; solo corte de seguridad). El margen interno
    para modelos que razonan se ajusta automaticamente segun el uso real del
    proveedor y no consume este limite. Si se omite se usa `LLM_MAX_TOKENS` de
    `.env` (default 512).
    """
    if not req.pregunta.strip():
        return {"error": "La pregunta no puede estar vacia"}

    documento_ids_filtro = list(req.documento_ids) if req.documento_ids else []
    if req.grupo_id is not None:
        grupo = obtener_grupo(req.grupo_id)
        if not grupo:
            raise HTTPException(status_code=404, detail="Grupo no encontrado")
        ids_grupo = grupo["documento_ids"] or []
        if not ids_grupo:
            raise HTTPException(status_code=400, detail="El grupo no tiene documentos")
        for doc_id in ids_grupo:
            if doc_id not in documento_ids_filtro:
                documento_ids_filtro.append(doc_id)
    documento_ids_filtro = documento_ids_filtro or None

    # La busqueda por termino (seccion/pantalla) solo se aplica cuando viene
    # `grupo_id`; en el resto de busquedas `termino` se ignora.
    termino_efectivo = None
    if req.grupo_id is not None and req.termino and req.termino.strip():
        termino_efectivo = req.termino.strip()

    def event_stream():
        fuentes = []
        intencion = "general"
        contexto_uso = {}
        uso_id = iniciar_uso_llm(tipo="chat")
        finalizado = False

        def cerrar(exitoso):
            nonlocal finalizado
            if finalizado or uso_id is None:
                return
            finalizado = True
            finalizar_uso_llm(uso_id, exitoso=exitoso, **contexto_uso)

        try:
            yield f"data: {json.dumps({'type': 'token', 'content': ''})}\n\n"

            todos_chunks, intencion = buscar_hibrido_inteligente(
                req.pregunta,
                umbral=req.umbral,
                limite=req.limite * 3,
                tipo_id=req.tipo_id,
                documento_id=req.documento_id,
                documento_ids=documento_ids_filtro,
                termino=termino_efectivo,
            )
            guia = _guia_para(intencion)

            if not todos_chunks:
                finalizado = True
                eliminar_uso_llm(uso_id)
                yield f"data: {json.dumps({'type': 'token', 'content': 'No encontre documentos relevantes para su pregunta.'})}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'pregunta': req.pregunta, 'tokens': 0, 'fuentes': []})}\n\n"
                return

            fuentes = deduplicar_fuentes(todos_chunks)[:req.limite]

            doc_ids = {f["documento_id"] for f in fuentes}
            chunks_filtrados = [
                c for c in todos_chunks
                if c.get("documento_id") in doc_ids
            ]
            chunks_para_llm = seleccionar_chunks_contexto(chunks_filtrados, req.pregunta, guia=guia)

            citas = {str(i): {"documento_id": c.get("documento_id"), "titulo": c.get("titulo",""), "numeral": c.get("numeral","")}
                     for i, c in enumerate(chunks_para_llm, 1)}

            estado_formato = {}
            for token in generar_respuesta_stream(req.pregunta, chunks_para_llm, guia=guia, max_tokens=req.max_tokens, llm_externo=req.llm_externo, contexto_uso=contexto_uso):
                token = _limpiar_formato(token, estado_formato)
                if token:
                    yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
            token_final = _limpiar_formato("", estado_formato)
            if token_final:
                yield f"data: {json.dumps({'type': 'token', 'content': token_final})}\n\n"
            cerrar(True)

        except GeneratorExit:
            cerrar(False)
            raise
        except Exception as e:
            cerrar(False)
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
        finally:
            cerrar(False)

        yield f"data: {json.dumps({'type': 'done', 'pregunta': req.pregunta, 'tokens': 0, 'fuentes': fuentes, 'intencion': intencion, 'citas': citas})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
