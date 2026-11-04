from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
import os
import tempfile
import json
from ..core.stt import transcribir_audio
from ..core.rag import buscar_cascada, deduplicar_fuentes
from ..core.embeddings import generar_embedding
from ..core.llm import generar_respuesta_stream, seleccionar_chunks_contexto
from ..db.queries import registrar_uso_llm

router = APIRouter(prefix="/voz", tags=["MotorIA > Voz"])


@router.post("")
def voz_a_chat(audio: UploadFile = File(..., description="Archivo de audio (wav/mp3/ogg) con la pregunta hablada.")):
    """Audio a respuesta: transcribe con Whisper y responde con el chat RAG.

    Devuelve un stream SSE con los eventos `token`, `error` y `done` (el `done`
    incluye `texto_transcrito` y `fuentes`). Usa el modo global del LLM
    (`/llm/modo` o `LLM_MODE` de `.env`).
    """
    if not audio.filename:
        raise HTTPException(status_code=400, detail="No se recibio archivo de audio")

    suffix = os.path.splitext(audio.filename)[1] or ".wav"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = audio.file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        texto = transcribir_audio(tmp_path)
    finally:
        os.unlink(tmp_path)

    if not texto.strip():
        raise HTTPException(status_code=400, detail="No se pudo transcribir el audio")

    embedding_pregunta = generar_embedding(texto)
    chunks = buscar_cascada(embedding_pregunta, umbral=0.30, limite=45)

    if not chunks:
        return {
            "texto_transcrito": texto,
            "respuesta": "No encontre documentos relevantes para su pregunta.",
            "tokens": 0,
            "fuentes": [],
        }

    fuentes = deduplicar_fuentes(chunks)
    chunks_para_llm = seleccionar_chunks_contexto(chunks, texto)

    def event_stream():
        try:
            contexto_uso = {}
            for token in generar_respuesta_stream(texto, chunks_para_llm, contexto_uso=contexto_uso):
                if token:
                    yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
            if contexto_uso:
                registrar_uso_llm(tipo="voz", exitoso=True, **contexto_uso)
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

        final = json.dumps({
            "type": "done",
            "texto_transcrito": texto,
            "tokens": 0,
            "fuentes": fuentes,
        })
        yield f"data: {final}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
